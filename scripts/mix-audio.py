#!/usr/bin/env python3
"""
mix-audio.py — 成片音频混音（配音 + BGM Ducking + 转场音效自动对齐）

节点2/节点4 音频管道：在渲染前把三路声音合成一轨：
  1. 配音 voice.mp3            —— 主干（音画对齐主时钟）
  2. BGM（可选）               —— 响度自动避让（sidechaincompress Ducking）：
     配音响起时 BGM 压低（threshold 0.02 / ratio 10 / attack 15ms / release 350ms）
  3. 转场音效（程序合成）       —— 由 sfx-gen.py 生成 pop/whoosh 整轨，
     标记点从 timeline.json 的场景边界自动推导（相对成片全局时间）：
       · 片头→正文 3.0s        → whoosh
       · 场景间切换点          → pop
       · 正文→片尾             → whoosh

BGM 来源（按优先级）：
  <project>/audio/bgm.mp3  →  <project>/assets/bgm.mp3  →  <root>/assets/bgm/*.mp3（第一个）

用法:
  python scripts/mix-audio.py <project_dir> [--no-bgm]

输出:
  <project>/audio/mixed.mp3（render.mjs 优先使用；无 BGM 时同样输出，含转场音效）
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INTRO_DURATION = 3.0   # 与 remotion/src/lib/constants.ts INTRO_DURATION 保持一致
OUTRO_DURATION = 5.0   # 与 OUTRO_DURATION 保持一致
TICK_TO_SEC = 10_000_000


def resolve_bgm(project: Path, no_bgm: bool) -> Path | None:
    if no_bgm:
        return None
    candidates = [
        project / "audio" / "bgm.mp3",
        project / "assets" / "bgm.mp3",
        project / "audio" / "bgm.wav",
        project / "assets" / "bgm.wav",
    ]
    for c in candidates:
        if c.exists():
            return c
    # 根级共享 BGM 目录
    root_bgms = sorted((ROOT / "assets" / "bgm").glob("*.[mw][ap][3v]")) if (ROOT / "assets" / "bgm").is_dir() else []
    if root_bgms:
        return root_bgms[0]
    return None


def build_sfx_marks(timeline: dict) -> list[tuple[float, str]]:
    """从时间轴场景边界推导转场音效标记（相对成片全局时间）"""
    marks: list[tuple[float, str]] = [(INTRO_DURATION, "whoosh")]
    body_total = float(timeline.get("totalDuration") or 0.0)
    for scene in timeline.get("scenes", []):
        start = float(scene.get("start", 0.0))
        if start > 0.05:
            marks.append((INTRO_DURATION + start, "pop"))
    marks.append((INTRO_DURATION + body_total, "whoosh"))
    marks.sort(key=lambda m: m[0])
    return marks


def run(cmd: list[str]) -> None:
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-1500:], file=sys.stderr)
        raise SystemExit(f"[error] ffmpeg 失败: {' '.join(cmd[:4])}…")


def mix(project: Path, timeline: dict, bgm: Path | None) -> Path:
    audio_dir = project / "audio"
    voice = audio_dir / "voice.mp3"
    if not voice.exists():
        raise SystemExit(f"[error] 缺少配音 {voice}，请先运行 tts.py")

    # 1. 转场音效轨（程序合成）
    total = INTRO_DURATION + float(timeline.get("totalDuration") or 0.0) + OUTRO_DURATION
    marks = build_sfx_marks(timeline)
    sfx_wav = audio_dir / "_sfx.wav"
    marks_arg = ",".join(f"{t:.3f}:{k}" for t, k in marks)
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "sfx-gen.py"),
         "--marks", marks_arg, "--duration", f"{total:.2f}", "--out", str(sfx_wav)],
        check=True,
    )

    out = audio_dir / "mixed.mp3"

    # 2. 混音：有 BGM 用 sidechaincompress Ducking；无 BGM 只叠加音效
    if bgm:
        print(f"[mix] BGM: {bgm}（sidechaincompress Ducking）")
        filter_graph = (
            "[0:a]asplit=2[vm][vs];"
            "[1:a][vs]sidechaincompress=threshold=0.02:ratio=10:attack=15:release=350[bgmd];"
            "[vm][bgmd][2:a]amix=inputs=3:duration=first:normalize=0[out]"
        )
        inputs = ["-i", str(voice), "-i", str(bgm), "-i", str(sfx_wav)]
    else:
        print("[mix] 未找到 BGM，仅混入转场音效（可将音频放到 audio/bgm.mp3 或 assets/bgm/）")
        filter_graph = "[0:a]anull[vo];[vo][1:a]amix=inputs=2:duration=first:normalize=0[out]"
        inputs = ["-i", str(voice), "-i", str(sfx_wav)]

    run([
        "ffmpeg", "-y", "-loglevel", "error",
        *inputs,
        "-filter_complex", filter_graph,
        "-map", "[out]",
        "-b:a", "192k",
        str(out),
    ])
    sfx_wav.unlink(missing_ok=True)
    print(f"[mix] 混音完成: {out}（{len(marks)} 个转场音效）")
    return out


def main():
    ap = argparse.ArgumentParser(description="成片音频混音：配音 + BGM Ducking + 转场音效")
    ap.add_argument("project_dir", help="单条视频项目目录")
    ap.add_argument("--no-bgm", action="store_true", help="强制不使用 BGM")
    args = ap.parse_args()

    project = Path(args.project_dir)
    if not project.is_absolute():
        project = ROOT / project
    timeline_path = project / "data" / "timeline.json"
    if not timeline_path.exists():
        print(f"[warn] 缺少 {timeline_path}，跳过混音（渲染将使用纯配音）")
        sys.exit(0)

    timeline = json.loads(timeline_path.read_text(encoding="utf-8"))
    bgm = resolve_bgm(project, args.no_bgm)
    mix(project, timeline, bgm)


if __name__ == "__main__":
    main()
