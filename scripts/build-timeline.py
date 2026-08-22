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
ZH_SPEECH_RATE = 4.5     # 中文参考语速（字/秒），用于分镜细分与估算
MAX_SHOT_DURATION = 4.0  # 节点3：分镜切分密度上限（2.5~4s 一个画面）
SHOT_CHUNK_CHARS = 18    # 每镜头字幕最多字数（4s × 4.5字/s）
SUBTITLE_SEG_MIN = 6     # 节点5：字幕断句最少字数
SUBTITLE_SEG_MAX = 10    # 节点5：字幕断句最多字数


# ---------------------------------------------------------------- 分镜细分

def chunk_by_chars(text: str, max_chars: int = SHOT_CHUNK_CHARS) -> list[str]:
    """把口播文本切成 <= max_chars 的镜头字幕片：优先在句读断，其次逗号，最后硬切。

    断点优先级：。！？； > ，、 > 词边界硬切。
    """
    text = text.strip()
    if len(text) <= max_chars:
        return [text] if text else []
    # 1. 强标点断
    strong = re.split(r"(?<=[。！？；])", text)
    chunks: list[str] = []
    buf = ""
    for part in strong:
        if not part:
            continue
        if len(buf + part) <= max_chars:
            buf += part
        else:
            if buf:
                chunks.append(buf)
                buf = ""  # 关键：append 后必须清空，否则残留片段被二次 append
            # 2. 超长段内按逗号再切
            if len(part) > max_chars:
                for sub in re.split(r"(?<=[，、])", part):
                    if not sub:
                        continue
                    if len(buf + sub) <= max_chars:
                        buf += sub
                    else:
                        if buf:
                            chunks.append(buf)
                        buf = sub
                        # 3. 仍超长则硬切
                        while len(buf) > max_chars:
                            chunks.append(buf[:max_chars])
                            buf = buf[max_chars:]
            else:
                buf = part
    if buf:
        chunks.append(buf)
    # 合并过短片（< 4 字）到前一片，避免碎字幕
    merged: list[str] = []
    for c in chunks:
        if merged and len(c) < 4:
            merged[-1] += c
        else:
            merged.append(c)
    return merged or [text]


def subdivide_scenes(scenes: list, max_dur: float = MAX_SHOT_DURATION) -> list:
    """节点3：把超长场景按 2.5~4s 密度细分为多镜头（shot）。

    父场景 [start,end] 按子字幕字数比例分配；sceneId 加后缀（S01 → S01a/S01b）；
    每个镜头分配递增 shotIndex（渲染端据此差异化 Ken Burns 方向）。
    场景数由配音边界锁定，细分仅发生在对齐之后的展示层，不破坏精确对齐。
    """
    out: list = []
    shot_idx = 0
    for scene in scenes:
        dur = scene["end"] - scene["start"]
        text = scene.get("subtitle", {}).get("text", "")
        if dur <= max_dur or len(text) <= SHOT_CHUNK_CHARS:
            scene["shotIndex"] = shot_idx
            out.append(scene)
            shot_idx += 1
            continue
        # 按实际语速（字/秒）推算每片最大字数：4s × 语速，至少 10 字避免过碎
        speech_rate = max(len(text) / max(dur, 1.0), 2.0)
        chunk_chars = max(int(4.0 * speech_rate), 10)
        chunks = chunk_by_chars(text, max_chars=chunk_chars)
        total_len = max(sum(len(c) for c in chunks), 1)
        cursor = scene["start"]
        base_id = scene.get("sceneId", f"S{len(out)+1:02d}")
        for i, c in enumerate(chunks):
            frac = len(c) / total_len
            end = scene["end"] if i == len(chunks) - 1 else round(cursor + frac * dur, 3)
            sub = json.loads(json.dumps(scene))  # 深拷贝
            sub["sceneId"] = f"{base_id}{chr(97 + i)}" if len(chunks) > 1 else base_id
            sub["start"] = round(cursor, 3)
            sub["end"] = end
            sub["shotIndex"] = shot_idx
            # overlay 只在第一个子片出现一次，避免同一价格卡全程重复挂屏
            if i > 0:
                sub["overlays"] = []
            sub["subtitle"] = {
                **scene.get("subtitle", {}),
                "text": c,
                "start": round(cursor, 3),
                "end": round(max(end - 0.2, cursor + 0.1), 3),
            }
            for el in sub.get("elements", []):
                el["duration"] = [round(cursor, 3), round(end, 3)]
            out.append(sub)
            shot_idx += 1
            cursor = end
    return merge_short_shots(out)


def _base_id(scene_id: str) -> str:
    """S02d → S02（去掉分镜后缀字母）"""
    return re.sub(r"[a-z]$", "", scene_id or "")


def merge_short_shots(shots: list, min_dur: float = 1.7) -> list:
    """合并过短镜头（< min_dur）到下一镜头，避免字幕闪屏（节点3 节奏优化）。

    仅向后合并，且不跨父场景（sceneId 前缀相同才允许合并），
    保证每个语义场景至少保留一个镜头。
    """
    if len(shots) < 2:
        return shots
    out: list = []
    i = 0
    while i < len(shots):
        cur = json.loads(json.dumps(shots[i]))
        # 向后合并过短片（同父场景内）
        while (cur["end"] - cur["start"]) < min_dur and i + 1 < len(shots):
            nxt = shots[i + 1]
            if _base_id(cur.get("sceneId", "")) != _base_id(nxt.get("sceneId", "")):
                break  # 不跨父场景合并
            cur["end"] = nxt["end"]
            cur["subtitle"]["text"] = cur["subtitle"]["text"] + nxt["subtitle"]["text"]
            cur["subtitle"]["end"] = nxt["subtitle"]["end"]
            for el in cur.get("elements", []):
                el["duration"] = [cur["start"], cur["end"]]
            i += 1
        out.append(cur)
        i += 1
    return out


# ---------------------------------------------------------------- 高亮/动态图层

def auto_highlights(text: str) -> list[str]:
    """节点3/5：无人工指定时自动提取高亮词 —— 数字+单位、价格、对比词（最多 4 个）"""
    found: list[str] = []
    for m in re.finditer(r"\d+(?:\.\d+)?\s*(?:%|元|块|折|倍|克|斤|毫升|ml|ML|L)", text):
        w = m.group(0).strip()
        if w and w not in found:
            found.append(w)
    for m in re.finditer(r"\d+(?:\.\d+)?", text):
        w = m.group(0)
        if w not in found:
            found.append(w)
    for kw in ("大包", "小包", "单价", "对比", "价格", "划算", "更贵", "更省"):
        if kw in text and kw not in found:
            found.append(kw)
    return found[:4]


def auto_overlays(text: str) -> list:
    """节点（信息可视化兜底）：scene-config 未生成 overlay 时，按 对比/计算/数字 语义自动补视觉图层。

    返回 overlay 元素列表（Remotion InfoOverlay 纯文本渲染），最多 2 个：
      · 对比词 + ≥2 个带单位数字 → vs-card（如「12块8 vs 5块5」）
      · 算式词（除以/单价/重量/成本等）→ equation（算式块，如「总价 ÷ 重量」）
      · 单个带单位数字 → price-tag（价格贴纸）
    """
    nums = [
        m.group(0).strip()
        for m in re.finditer(r"\d+(?:\.\d+)?\s*(?:%|元|块|折|倍|克|斤|毫升|ml|ML|L)", text)
    ]
    nums = [n for n in nums if re.search(r"\d", n)][:2]
    # 无具体数字时不兜底：纯文本「大包装 vs 小包装」「总价 ÷ 重量」在讲解段是噪音，
    # 信息可视化必须基于真实数字（价格/克重对比），否则宁可不出卡
    if not nums:
        return []
    vs_words = ("大包", "小包", "更贵", "更省", "划算", "对比", "单价", "包装")
    eq_words = ("除以", "单价", "重量", "克", "斤", "毫升", "ml", "ML", "成本", "总价", "平均")
    has_vs = any(k in text for k in vs_words)
    has_eq = any(k in text for k in eq_words)
    out: list = []
    if has_vs and len(nums) >= 2:
        out.append({"kind": "vs-card", "text": f"{nums[0]} vs {nums[1]}", "title": "对比一下", "position": "top"})
    elif nums:
        unit = next((n for n in nums if re.search(r"[%元块折倍克斤毫升mlML]", n)), None)
        if unit:
            out.append({"kind": "price-tag", "text": unit, "title": "关键数字", "position": "top"})
        else:
            out.append({"kind": "equation", "text": nums[0], "title": "关键数字", "position": "top"})
    if not out and has_eq:
        out.append({"kind": "equation", "text": "总价 ÷ 重量", "title": "怎么算", "position": "top"})
    elif not out and has_vs:
        out.append({"kind": "vs-card", "text": "大包装 vs 小包装", "title": "对比一下", "position": "top"})
    return out[:2]


def split_subtitle_segments(text: str, start: float, end: float) -> list[dict]:
    """节点5：把一句字幕切成 6~10 字的短句段，按字数比例分配展示时间。

    断点优先级：。！？； > ，、/空格 > 硬切；尾段过短(<6字)且并入后不超
    SUBTITLE_SEG_MAX+2 时并入前段，避免碎字幕。返回 [{text, start, end}]。
    """
    t = (text or "").strip()
    if not t or len(t) <= SUBTITLE_SEG_MAX:
        return [{"text": t, "start": round(start, 3), "end": round(max(end, start + 0.1), 3)}]
    # 1. 强句读粗切
    parts = re.split(r"(?<=[。！？；])", t)
    pieces: list[str] = []
    buf = ""
    for p in parts:
        if not p:
            continue
        if len(buf + p) <= SUBTITLE_SEG_MAX:
            buf += p
            continue
        if buf:
            pieces.append(buf)
            buf = ""
        if len(p) <= SUBTITLE_SEG_MAX:
            buf = p
            continue
        # 2. 长段内按逗号/空格细分
        for sub in re.split(r"(?<=[，、])|\s+", p):
            if not sub:
                continue
            if len(buf + sub) <= SUBTITLE_SEG_MAX:
                buf += sub
            else:
                if buf:
                    pieces.append(buf)
                buf = sub
                # 3. 仍超长则硬切
                while len(buf) > SUBTITLE_SEG_MAX:
                    pieces.append(buf[:SUBTITLE_SEG_MAX])
                    buf = buf[SUBTITLE_SEG_MAX:]
    if buf:
        pieces.append(buf)
    # 4. 尾段过短并入前段（总长不超过 MAX+2，避免单行过挤）
    merged: list[str] = []
    for c in pieces:
        if merged and len(c) < SUBTITLE_SEG_MIN and len(merged[-1]) + len(c) <= SUBTITLE_SEG_MAX + 2:
            merged[-1] += c
        else:
            merged.append(c)
    # 5. 按字数比例分配时间
    total = max(sum(len(c) for c in merged), 1)
    span = max(end - start, 0.1)
    segs: list[dict] = []
    cursor = start
    for i, c in enumerate(merged):
        frac = len(c) / total
        seg_end = end if i == len(merged) - 1 else cursor + frac * span
        segs.append({
            "text": c,
            "start": round(cursor, 3),
            "end": round(max(seg_end, cursor + 0.05), 3),
        })
        cursor = seg_end
    return segs


def build_shot_transitions(scenes: list) -> list[dict]:
    """为每个镜头生成转场描述（供渲染端/质检端消费）"""
    return [
        {"sceneId": s.get("sceneId"), "start": s.get("start"), "end": s.get("end")}
        for s in scenes
    ]


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
        overlays = []
        for el in scene.get("elements", []):
            if el.get("type") == "overlay":
                # 动态视觉图层（价格标签/算式/对比卡）：纯文本渲染，无需素材
                overlays.append({
                    "kind": el.get("kind", "price-tag"),
                    "text": el.get("text", ""),
                    "title": el.get("title", ""),
                    "position": el.get("position", "top"),
                })
                continue
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
            "overlays": overlays,
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
            est_dur = len(narration) / ZH_SPEECH_RATE if narration else 3.0
            end = start + est_dur
            elements = []
            overlays = []
            for el in scene.get("elements", []):
                if el.get("type") == "overlay":
                    overlays.append({
                        "kind": el.get("kind", "price-tag"),
                        "text": el.get("text", ""),
                        "title": el.get("title", ""),
                        "position": el.get("position", "top"),
                    })
                    continue
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
                "overlays": overlays,
            })
            cursor = end + MIN_SEGMENT_GAP
        mode = "estimated"

    # 3. 节点3：overlay 兜底（父场景层，必须在细分之前：细分后子片继承、只留第一片，
    #    避免每个子片对局部文本重复检测出内容各异的卡）
    for s in timeline_scenes:
        if not s.get("overlays"):
            s["overlays"] = auto_overlays(s["subtitle"]["text"])

    # 3. 节点3：分镜细分（每镜头 2.5~4s）+ 高亮自动提取
    timeline_scenes = subdivide_scenes(timeline_scenes)
    for s in timeline_scenes:
        hl = s.get("subtitle", {}).get("highlights") or []
        if not hl:
            s["subtitle"]["highlights"] = auto_highlights(s["subtitle"]["text"])

    # 4. 节点5：6~10 字断句 —— 在细分/合并之后统一生成字幕段（对齐与估算路径共用）
    for s in timeline_scenes:
        sub = s.get("subtitle", {})
        sub["segments"] = split_subtitle_segments(
            sub.get("text", ""),
            sub.get("start", s.get("start", 0.0)),
            sub.get("end", s.get("end", 0.0)),
        )

    # 4. 整片时长：取配音时长（声音是主时钟）
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
