#!/usr/bin/env python3
"""
material-gap.py — 选题驱动的素材缺口扫描器

扫描 scene-config.json 中引用的背景、角色和道具，只把 active 素材视为可生产素材。
缺失或仍处于 pending_review 的素材会生成：
- 项目 qa/material-gap-report.json
- shared/_generate/material-tasks/<videoId>.json

本脚本不会自动把素材登记为 active，也不会绕过人工审核。
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_json(path: Path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def prompt_for(item: dict) -> str:
    kind = item["type"]
    name = item["name"]
    emotion = item.get("emotion") or ""
    if kind == "background":
        return f"治愈卡通插画，竖屏9:16，适合叠加小布丁角色和字幕的{name}场景，暖色调，柔和描边，小清新手绘质感，无人物、无文字、无字母、无数字、无水印"
    if kind == "character":
        return f"小布丁角色，{emotion}情绪，圆脸、奶油色皮肤、蜜桃粉腮红、浅黄色贝雷帽、暖黄卫衣、浅蓝短裤，治愈卡通暖色调，透明底，无文字、无水印"
    return f"治愈卡通透明底道具：{name}，暖色调，圆润造型，柔和描边，小清新手绘质感，无文字、无字母、无数字、无水印"


def scan(project: Path) -> dict:
    scene_path = project / "data" / "scene-config.json"
    report_path = project / "qa" / "material-gap-report.json"
    scene_config = load_json(scene_path, {}) or {}
    library = load_json(ROOT / "shared" / "material-library.json", {}) or {}
    by_key = {}
    for category in ("backgrounds", "characters", "props"):
        for item in library.get(category, []):
            key = (item.get("type"), item.get("name"), item.get("emotion"))
            by_key[key] = item

    requested = []
    for scene in scene_config.get("scenes", []):
        background = scene.get("background") or scene.get("backgroundName")
        if background:
            requested.append({"sceneId": scene.get("sceneId"), "type": "background", "name": background})
        for element in scene.get("elements", []):
            if element.get("type") in ("character", "prop") and element.get("name"):
                requested.append({
                    "sceneId": scene.get("sceneId"),
                    "type": element["type"],
                    "name": element["name"],
                    "emotion": element.get("emotion"),
                })

    unique = {}
    for item in requested:
        key = (item["type"], item["name"], item.get("emotion"))
        unique.setdefault(key, item)

    missing = []
    for key, item in unique.items():
        found = by_key.get(key)
        if found is None and item["type"] == "character":
            found = by_key.get(("character", item["name"], None))
        if found is None:
            reason = "not_registered"
        elif found.get("status") != "active":
            reason = found.get("status", "not_active")
        else:
            continue
        missing.append({
            **item,
            "reason": reason,
            "suggestedPrompt": prompt_for(item),
            "nextAction": "generate_then_review_then_register_active",
        })

    video_id = scene_config.get("videoId") or project.name.split("_", 1)[0]
    task_path = ROOT / "shared" / "_generate" / "material-tasks" / f"{video_id}.json"
    task_path.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    report = {
        "videoId": video_id,
        "projectDir": rel(project),
        "generatedAt": now,
        "pass": not missing,
        "requestedCount": len(unique),
        "missingCount": len(missing),
        "missing": missing,
        "taskFile": rel(task_path),
        "nextAction": "素材已齐，可进入人工剧本审核" if not missing else "先生成缺失素材，人工审核通过并登记为 active 后再进入视频生产",
    }
    project.joinpath("qa").mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    task_path.write_text(json.dumps({"videoId": video_id, "createdAt": now, "tasks": missing}, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main():
    ap = argparse.ArgumentParser(description="扫描选题场景配置的素材缺口并生成待办清单")
    ap.add_argument("project", help="项目目录，例如 02_项目/C010_新选题")
    ap.add_argument("--json", action="store_true", help="只输出 JSON 报告")
    args = ap.parse_args()
    project = Path(args.project)
    if not project.is_absolute():
        project = ROOT / project
    if not (project / "data" / "scene-config.json").exists():
        print(f"缺少 scene-config.json: {project}", file=sys.stderr)
        return 2
    report = scan(project)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif report["pass"]:
        print(f"[materials] {report['videoId']}: 素材齐全，可进入人工剧本审核")
    else:
        print(f"[materials] {report['videoId']}: 缺少/待审核素材 {report['missingCount']} 项")
        for item in report["missing"]:
            emotion = f"/{item['emotion']}" if item.get("emotion") else ""
            print(f"  - {item['type']} {item['name']}{emotion} [{item['reason']}]")
        print(f"  任务清单: {report['taskFile']}")
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
