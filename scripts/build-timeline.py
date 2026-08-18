#!/usr/bin/env python3
"""
build-timeline.py — 时间轴构建脚本
将 scene-config.json（画面配置）与 voice.json（配音时间信息）合成为 timeline.json。
字幕时间完全由配音的句子边界决定，画面元素区间按语义段切分。

对齐策略（阶段 2 优化）：
  1. 精确对齐：场景数与配音句子边界数一致，且边界文本与旁白前几个字匹配时，
     场景起止时间直接采用句子边界的 offset/duration（100ns tick → 秒）。
  2. 估算回退：不满足对齐条件时，按字数估算（约 4.5 字/秒）。

用法:
    python scripts/build-timeline.py <project_dir>

输入:
    <project_dir>/data/scene-config.json    # 场景配置（渲染前）
    <project_dir>/audio/voice.json          # 配音元数据（含句子边界）

输出:
    <project_dir>/data/timeline.json        # 最终时间轴（Remotion 消费）
"""
import argparse
import json
import re
import sys
from pathlib import Path

MIN_SEGMENT_GAP = 0.15  # 语义段之间最小间隔
TICK_TO_SEC = 10_000_000  # edge-tts 边界时间单位是 100ns


def _norm(s: str) -> str:
    """去标点空白，用于文本比对"""
    return re.sub(r"[\s，。！？、,.!?；;：:\"'“”‘’（）()【】\-]", "", s)


def align_by_sentence(scene_config: dict, word_boundaries: list) -> tuple[list | None, str]:
    """尝试用句子边界精确对齐场景。成功返回 (scenes, 'aligned')，失败返回 (None, 原因)。"""
    scenes_in = scene_config["scenes"]
    if len(scenes_in) != len(word_boundaries):
        return None, f"场景数({len(scenes_in)})与句子边界数({len(word_boundaries)})不一致"

    for scene, wb in zip(scenes_in, word_boundaries):
        nseg = _norm(scene.get("narrationSegment", ""))[:6]
        nwb = _norm(wb.get("word", ""))[:6]
        if nseg != nwb:
            return None, f"边界文本与旁白不匹配: {scene['narrationSegment'][:14]}… vs {wb.get('word','')[:14]}…"

    scenes = []
    for scene, wb in zip(scenes_in, word_boundaries):
        start = wb["offset"] / TICK_TO_SEC
        end = (wb["offset"] + wb["duration"]) / TICK_TO_SEC
        elements = []
        for el in scene.get("elements", []):
            elements.append({
                "type": el["type"],
                "name": el["name"],
                "emotion": el.get("emotion"),
                "enterFrom": el.get("enterFrom", "none"),
                "position": el.get("position"),
                "zIndex": el.get("zIndex", 1),
                "duration": [round(start, 3), round(end, 3)],
            })
        scenes.append({
            "sceneId": scene.get("sceneId", f"S{len(scenes)+1:02d}"),
            "start": round(start, 3),
            "end": round(end, 3),
            "backgroundName": scene.get("background"),
            "subtitle": {
                "text": scene.get("narrationSegment", ""),
                "start": round(start, 3),
                "end": round(max(end - 0.2, start + 0.1), 3),
                "highlights": scene.get("subtitle", {}).get("highlights", []),
            },
            "elements": elements,
        })
    return scenes, "aligned"


def build_timeline(project_dir: Path) -> dict:
    scene_config_path = project_dir / "data" / "scene-config.json"
    voice_path = project_dir / "audio" / "voice.json"

    if not scene_config_path.exists():
        print(f"[error] 缺少 scene-config.json: {scene_config_path}", file=sys.stderr)
        sys.exit(1)
    if not voice_path.exists():
        print(f"[error] 缺少 voice.json（请先运行 tts.py）: {voice_path}", file=sys.stderr)
        sys.exit(1)

    scene_config = json.loads(scene_config_path.read_text(encoding="utf-8"))
    voice = json.loads(voice_path.read_text(encoding="utf-8"))

    total_duration = voice.get("duration") or 0.0
    word_boundaries = voice.get("wordBoundaries", [])

    # 1. 尝试精确对齐（句子边界）
    timeline_scenes, mode = align_by_sentence(scene_config, word_boundaries)
    if timeline_scenes is None:
        # 2. 回退：按字数估算
        print(f"[warn] 精确对齐不可用（{mode}），使用字数估算")
        timeline_scenes = []
        cursor = 0.0
        for idx, scene in enumerate(scene_config["scenes"]):
            narration = scene.get("narrationSegment", "").strip()
            start = scene.get("preferredStart") or cursor
            est_dur = len(narration) / 4.5 if narration else 3.0
            end = start + est_dur
            elements = []
            for el in scene.get("elements", []):
                elements.append({
                    "type": el["type"],
                    "name": el["name"],
                    "emotion": el.get("emotion"),
                    "enterFrom": el.get("enterFrom", "none"),
                    "position": el.get("position"),
                    "zIndex": el.get("zIndex", 1),
                    "duration": [round(start, 3), round(end, 3)],
                })
            timeline_scenes.append({
                "sceneId": scene.get("sceneId", f"S{idx+1:02d}"),
                "start": round(start, 3),
                "end": round(end, 3),
                "backgroundName": scene.get("background"),
                "subtitle": {
                    "text": narration,
                    "start": round(start, 3),
                    "end": round(end - 0.2, 3) if end - start > 0.3 else round(end, 3),
                    "highlights": scene.get("subtitle", {}).get("highlights", []),
                },
                "elements": elements,
            })
            cursor = end + MIN_SEGMENT_GAP
        mode = "estimated"

    # 3. 整片时长：取配音时长（声音是主时钟）
    last_end = max((s["end"] for s in timeline_scenes), default=0.0)
    total = round(max(total_duration, last_end), 3)

    timeline = {
        "videoId": scene_config.get("videoId", "UNKNOWN"),
        "title": scene_config.get("title", ""),
        "totalDuration": total,
        "audioFile": voice.get("audioFile"),
        "scenes": timeline_scenes,
    }

    out_path = project_dir / "data" / "timeline.json"
    out_path.write_text(json.dumps(timeline, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[ok] 时间轴已生成: {out_path}  (对齐方式: {mode})")
    print(f"[info] {len(timeline_scenes)} 个场景, 总时长 {total}s (配音 {round(total_duration,2)}s)")
    return timeline


def main():
    parser = argparse.ArgumentParser(description="构建时间轴")
    parser.add_argument("project_dir", help="单条视频的项目目录")
    args = parser.parse_args()
    build_timeline(Path(args.project_dir))


if __name__ == "__main__":
    main()
