#!/usr/bin/env python3
"""
quality-check.py - 项目级质量门禁

统一执行技术检查与语义对齐检查，并生成：
  <project>/qa/quality-report.json

门禁规则：
  - 技术检查存在 error，或必需文件缺失：不通过
  - 语义检查 warning：记录但默认不阻断
  - 语义检查 error：不通过

用法：
  python scripts/quality-check.py 02_项目/C006_第二件半价
"""
import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYTHON = sys.executable


def run_json(command: list[str]) -> tuple[dict, str | None]:
    result = subprocess.run(command, cwd=str(ROOT), capture_output=True, text=True)
    raw = result.stdout.strip()
    if not raw:
        return {}, result.stderr.strip() or f"检查器退出码 {result.returncode}"
    try:
        return json.loads(raw), None
    except json.JSONDecodeError as exc:
        return {}, f"检查器输出不是有效 JSON: {exc}"


def resolve_project(value: str) -> Path:
    project = Path(value)
    if not project.is_absolute():
        project = ROOT / project
    return project


def main() -> int:
    parser = argparse.ArgumentParser(description="项目级统一质量检查与门禁")
    parser.add_argument("project_dir", help="单条视频项目目录")
    parser.add_argument("--strict-warnings", action="store_true", help="将语义 warning 也视为不通过")
    args = parser.parse_args()

    project = resolve_project(args.project_dir)
    if not project.is_dir():
        print(f"[error] 项目目录不存在: {project}", file=sys.stderr)
        return 1

    video_id = project.name.split("_", 1)[0]
    scene_config_path = project / "data" / "scene-config.json"
    timeline_path = project / "data" / "timeline.json"
    audio_path = project / "audio" / "voice.mp3"
    deliverables = project / "deliverables"
    mp4_files = sorted(deliverables.glob("*.mp4"))

    required = {
        "sceneConfig": scene_config_path,
        "timeline": timeline_path,
        "audio": audio_path,
        "video": mp4_files[0] if mp4_files else deliverables / f"{video_id}_成片.mp4",
    }
    missing = [
        {"name": name, "path": str(path.relative_to(ROOT) if path.is_relative_to(ROOT) else path)}
        for name, path in required.items()
        if not path.exists() or path.stat().st_size == 0
    ]

    report: dict = {
        "videoId": video_id,
        "project": str(project.relative_to(ROOT) if project.is_relative_to(ROOT) else project),
        "checkedAt": datetime.now(timezone.utc).isoformat(),
        "gate": {"strictWarnings": args.strict_warnings},
        "requiredFiles": {
            name: str(path.relative_to(ROOT) if path.is_relative_to(ROOT) else path)
            for name, path in required.items()
        },
        "missingFiles": missing,
        "technical": {},
        "semantic": {},
        "pronunciation": {},
        "issues": [],
    }

    for item in missing:
        report["issues"].append({
            "level": "error",
            "type": "missing_file",
            "message": f"缺少必需文件: {item['path']}",
        })

    video_path = required["video"]
    if video_path.exists() and audio_path.exists():
        technical, technical_error = run_json([
            PYTHON,
            str(ROOT / "scripts" / "tech-check.py"),
            str(video_path),
            "--audio",
            str(audio_path),
            "--timeline",
            str(timeline_path),
        ])
        report["technical"] = technical
        if technical_error:
            report["issues"].append({"level": "error", "type": "technical_runner", "message": technical_error})
        for issue in technical.get("issues", []):
            report["issues"].append({"source": "technical", **issue})

    if timeline_path.exists():
        semantic_result = subprocess.run(
            [PYTHON, str(ROOT / "scripts" / "semantic-check.py"), str(project)],
            cwd=str(ROOT), capture_output=True, text=True,
        )
        semantic_report_path = project / "qa" / "semantic-alignment-report.json"
        semantic = {}
        if semantic_report_path.exists():
            try:
                semantic = json.loads(semantic_report_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                report["issues"].append({"level": "error", "type": "semantic_report", "message": f"语义报告不是有效 JSON: {exc}"})
        report["semantic"] = semantic
        if semantic_result.returncode != 0:
            report["issues"].append({
                "level": "error",
                "type": "semantic_runner",
                "message": semantic_result.stderr.strip() or f"语义检查退出码 {semantic_result.returncode}",
            })
        for scene in semantic.get("scenes", []):
            for issue in scene.get("issues", []):
                report["issues"].append({"source": "semantic", "sceneId": scene.get("sceneId"), **issue})

    # 发音预检报告（qa/pronunciation-report.json，由 check-pronunciation.py 生成）
    pronunciation_report_path = project / "qa" / "pronunciation-report.json"
    if pronunciation_report_path.exists():
        try:
            pron = json.loads(pronunciation_report_path.read_text(encoding="utf-8"))
            report["pronunciation"] = pron
            for hit in pron.get("hits", []):
                report["issues"].append({
                    "level": "warning",
                    "source": "pronunciation",
                    "type": "polyphonic_word",
                    "word": hit.get("word"),
                    "message": (
                        f"多音字风险「{hit.get('word')}」建议读 {hit.get('correct')}"
                        f"（常见误读 {hit.get('wrong') or '-'}，{hit.get('note') or ''}）："
                        f"{hit.get('sentence', '')[:40]}"
                    ),
                })
        except json.JSONDecodeError as exc:
            report["issues"].append({
                "level": "error",
                "type": "pronunciation_report",
                "message": f"发音报告不是有效 JSON: {exc}",
            })

    errors = [issue for issue in report["issues"] if issue.get("level") == "error"]
    warnings = [issue for issue in report["issues"] if issue.get("level") == "warning"]
    report["summary"] = {
        "errors": len(errors),
        "warnings": len(warnings),
        "technicalPass": report["technical"].get("pass", False) if report["technical"] else False,
        "semanticWarnings": report["semantic"].get("warnings", 0) if report["semantic"] else 0,
        "pronunciationWarnings": report["pronunciation"].get("total", 0) if report["pronunciation"] else 0,
    }
    report["pass"] = not errors and (not args.strict_warnings or not warnings)

    out_dir = project / "qa"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "quality-report.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    state = "通过" if report["pass"] else "不通过"
    print(f"[quality] {video_id}: {state}")
    print(f"[quality] 报告: {out_path}")
    print(f"[quality] errors={len(errors)} warnings={len(warnings)} strict={args.strict_warnings}")
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
