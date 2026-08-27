#!/usr/bin/env python3
"""
tts.py — 配音生成脚本 2.0（支持单人解说与多角色情景剧多音色合成）

支持两种引擎:
  azure  Azure Speech SDK（推荐，需环境变量 AZURE_SPEECH_KEY / AZURE_SPEECH_REGION）
  edge   edge-tts（免费兜底，无需配置）

2.0 多角色支持（野原经济学）:
  口播稿中支持形如 `[小新]: ...`、`[美伢]: ...`、`[广志]: ...` 的角色标注，
  系统会自动按角色分派专属音色、语速与音调合成，并生成统一拼接的 voice.mp3 与 voice.json。

统一输出:
  <output_dir>/voice.mp3   # 配音音频
  <output_dir>/voice.json  # 音频信息 + 句子级时间戳（wordBoundaries，100ns tick）
"""
import argparse
import asyncio
import datetime
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

DEFAULT_VOICE = "zh-CN-YunxiNeural"
TICK_TO_SEC = 10_000_000  # 100ns tick

SPEAKER_VOICE_CONFIG = {
    "小新": {"voice": "zh-CN-XiaoyiNeural", "rate": "+25%", "pitch": "+3st"},
    "美伢": {"voice": "zh-CN-XiaoxiaoNeural", "rate": "+20%", "pitch": "+1st"},
    "广志": {"voice": "zh-CN-YunyangNeural", "rate": "+15%", "pitch": "-1st"},
    "风间": {"voice": "zh-CN-YunxiNeural", "rate": "+20%", "pitch": "+2st"},
    "小白": {"voice": "zh-CN-XiaoyiNeural", "rate": "+15%", "pitch": "+4st"},
    "小布丁": {"voice": "zh-CN-YunxiNeural", "rate": "+20%", "pitch": "+1st"},
}

PRONUNCIATION_OVERRIDES: dict[str, str] = {
    "便宜": "pian2 yi5",
    "花呗": "hua1 bei1",
    "公积金": "gong1 ji1 jin1",
    "个税": "ge4 shui4",
    "还了": "huan2 le5",
    "先花后还": "xian1 hua1 hou4 huan2",
    "涨": "zhang3",
    "挣钱": "zheng4 qian2",
    "省": "sheng3",
    "干等": "gan4 deng3",
    "干活": "gan4 huo2",
    "藏着": "cang2 zhe5",
    "空儿": "kong4 r5",
}

def escape_xml(text: str) -> str:
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
    )

def normalize_rate(rate: str) -> str:
    rate = rate.strip()
    if rate.endswith("%") and "." not in rate:
        sign = "+" if rate.startswith("+") else "-" if rate.startswith("-") else ""
        num = rate.strip("+-%")
        if num.isdigit():
            return f"{sign}{num}.00%"
    return rate if rate else "+0.00%"

PAUSE_BREAKS = [
    (re.compile(r"([。！？；])"), r"\1<break time=\"100ms\"/>"),
    (re.compile(r"([，、：])"), r"\1<break time=\"40ms\"/>"),
]

def inject_pauses(text: str) -> str:
    for pat, repl in PAUSE_BREAKS:
        text = pat.sub(repl, text)
    return text

def apply_phoneme_overrides(text: str) -> str:
    if os.environ.get("ENABLE_PHONEME") != "1" or not PRONUNCIATION_OVERRIDES:
        return escape_xml(text)
    words = sorted(PRONUNCIATION_OVERRIDES.keys(), key=len, reverse=True)
    pattern = re.compile("|".join(re.escape(w) for w in words))
    def _replace(match: re.Match) -> str:
        word = match.group(0)
        ph = PRONUNCIATION_OVERRIDES[word]
        return f'<phoneme alphabet="sapi" ph="{ph}">{escape_xml(word)}</phoneme>'
    return pattern.sub(_replace, escape_xml(text))

def _norm(s: str) -> str:
    return re.sub(r"[\s，。！？、,.!?；;：:\"'“”‘’（）()【】\-]", "", s)

def split_paragraphs(text: str) -> list[str]:
    parts = [p.strip() for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]
    return parts if len(parts) >= 2 else [text.strip()]

def parse_speaker_dialogue(text: str) -> list[dict]:
    """解析对话文本中的角色与台词。
    支持格式：[小新]: 台词 或 小新：台词
    """
    paragraphs = split_paragraphs(text)
    dialogues = []
    speaker_re = re.compile(r"^\[?(小新|美伢|广志|风间|小白|小布丁)\]?[:：]\s*(.*)$", re.S)
    for p in paragraphs:
        m = speaker_re.match(p)
        if m:
            dialogues.append({
                "speaker": m.group(1),
                "text": m.group(2).strip(),
                "raw": p
            })
        else:
            dialogues.append({
                "speaker": "小新",
                "text": p,
                "raw": p
            })
    return dialogues

def group_to_paragraphs(paragraphs: list, boundaries: list) -> list:
    grouped = []
    bi = 0
    total = len(boundaries)
    for para in paragraphs:
        target_len = len(_norm(para))
        acc_len = 0
        items = []
        guard = 0
        while bi < total and acc_len < target_len and guard < 500:
            items.append(boundaries[bi])
            acc_len += len(_norm(boundaries[bi].get("word", "")))
            bi += 1
            guard += 1
            if acc_len >= target_len:
                break
        if items:
            start = items[0]["offset"]
            last = items[-1]
            end = last["offset"] + (last.get("duration") or 0)
            grouped.append({"word": para, "offset": start, "duration": max(end - start, 0)})
        else:
            grouped.append({"word": para, "offset": 0, "duration": 0})
    return grouped

# ----------------- 单段合成 -----------------

async def edge_generate_single(text: str, output_path: Path, voice: str, rate: str) -> list:
    import edge_tts
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    audio_bytes = b""
    word_offsets = []
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_bytes += chunk["data"]
        elif chunk["type"] in ("WordBoundary", "SentenceBoundary"):
            word_offsets.append({
                "word": chunk["text"],
                "offset": chunk["offset"],
                "duration": chunk["duration"],
            })
    output_path.write_bytes(audio_bytes)
    return word_offsets

def azure_generate_single(text: str, output_path: Path, voice: str, rate: str, pitch: str,
                          key: str, region: str) -> list:
    import azure.cognitiveservices.speech as speechsdk
    speech_config = speechsdk.SpeechConfig(subscription=key, region=region)
    speech_config.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Audio48Khz192KBitRateMonoMp3
    )
    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)
    word_boundaries = []

    def on_word_boundary(evt):
        dur = evt.duration
        if isinstance(dur, datetime.timedelta):
            dur = int(dur.total_seconds() * TICK_TO_SEC)
        word_boundaries.append({
            "word": evt.text,
            "offset": evt.audio_offset,
            "duration": dur or 0,
        })

    synthesizer.synthesis_word_boundary.connect(on_word_boundary)
    ssml = (
        '<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="zh-CN">'
        f'<voice name="{voice}">'
        f'<prosody rate="{normalize_rate(rate)}" pitch="{pitch}">'
        f'{inject_pauses(apply_phoneme_overrides(text))}'
        "</prosody></voice></speak>"
    )
    result = synthesizer.speak_ssml_async(ssml).get()
    if result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
        details = getattr(result, "error_details", "") or ""
        raise RuntimeError(f"Azure TTS 合成失败: {result.reason} | {details}")
    output_path.write_bytes(result.audio_data)
    return word_boundaries

def probe_duration(path: Path) -> float:
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "json", str(path)],
            capture_output=True, text=True,
        )
        if r.returncode == 0:
            return float(json.loads(r.stdout)["format"]["duration"])
    except Exception:
        pass
    return 0.0

def detect_azure() -> tuple | None:
    key = os.environ.get("AZURE_SPEECH_KEY", "").strip()
    region = os.environ.get("AZURE_SPEECH_REGION", "").strip()
    if key and region:
        return key, region
    return None

# ----------------- 多角色拼接合成 -----------------

def synthesize_dialogues(dialogues: list[dict], engine: str, out_dir: Path, default_voice: str) -> tuple[Path, list]:
    temp_files = []
    combined_boundaries = []
    current_time_offset_tick = 0

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        for i, d in enumerate(dialogues):
            spk = d["speaker"]
            line_text = d["text"]
            cfg = SPEAKER_VOICE_CONFIG.get(spk, {"voice": default_voice, "rate": "+20%", "pitch": "+1st"})
            seg_file = tmp_path / f"seg_{i:03d}.mp3"
            
            if engine == "azure":
                key, region = detect_azure()
                raw_bounds = azure_generate_single(line_text, seg_file, cfg["voice"], cfg["rate"], cfg["pitch"], key, region)
            else:
                raw_bounds = asyncio.run(edge_generate_single(line_text, seg_file, cfg["voice"], cfg["rate"]))

            seg_dur = probe_duration(seg_file)
            seg_dur_tick = int(seg_dur * TICK_TO_SEC)

            # 记录段落边界（带 speaker 标注）
            combined_boundaries.append({
                "word": line_text,
                "speaker": spk,
                "offset": current_time_offset_tick,
                "duration": seg_dur_tick
            })
            current_time_offset_tick += seg_dur_tick
            temp_files.append(seg_file)

        # 用 ffmpeg concat 合并所有音频片段
        final_mp3 = out_dir / "voice.mp3"
        concat_list = tmp_path / "concat.txt"
        concat_list.write_text("\n".join(f"file '{p.resolve()}'" for p in temp_files), encoding="utf-8")
        
        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list),
             "-c:a", "libmp3lame", "-q:a", "2", str(final_mp3)],
            check=True, capture_output=True
        )

    return final_mp3, combined_boundaries

def main():
    parser = argparse.ArgumentParser(description="配音生成 2.0：支持单人与野原家多角色情景剧合成")
    parser.add_argument("input", help="文本内容或文本文件路径")
    parser.add_argument("output_dir", help="输出目录")
    parser.add_argument("--engine", default="auto", choices=["auto", "azure", "edge"],
                        help="合成引擎（auto=有 Azure key 用 azure，否则 edge）")
    parser.add_argument("--voice", default=None, help="默认音色")
    parser.add_argument("--rate", default=os.environ.get("TTS_RATE", "+20%"), help="默认语速")
    args = parser.parse_args()

    voice = args.voice or os.environ.get("AZURE_VOICE", "").strip() or DEFAULT_VOICE
    input_arg = Path(args.input)
    text = input_arg.read_text(encoding="utf-8") if input_arg.exists() else args.input

    engine = args.engine
    if engine == "auto":
        engine = "azure" if detect_azure() else "edge"
    if engine == "azure" and not detect_azure():
        print("[error] --engine azure 需要环境变量 AZURE_SPEECH_KEY 和 AZURE_SPEECH_REGION", file=sys.stderr)
        sys.exit(1)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    voice_path = out_dir / "voice.mp3"
    meta_path = out_dir / "voice.json"

    # 判断是否为多角色对话
    has_speaker_tags = bool(re.search(r"\[?(小新|美伢|广志|风间|小白|小布丁)\]?[:：]", text))
    
    if has_speaker_tags:
        dialogues = parse_speaker_dialogue(text)
        print(f"[tts 2.0] 检测到多角色情景对白模式，共 {len(dialogues)} 句对白")
        for d in dialogues:
            print(f"  [{d['speaker']}]: {d['text']}")
        final_mp3, word_offsets = synthesize_dialogues(dialogues, engine, out_dir, voice)
    else:
        print(f"[tts] 引擎: {engine}, 音色: {voice}, 语速: {args.rate}, 文本 {len(text)} 字")
        if engine == "azure":
            key, region = detect_azure()
            raw = azure_generate_single(text, voice_path, voice, args.rate, os.environ.get("TTS_PITCH", "+1st"), key, region)
        else:
            raw = asyncio.run(edge_generate_single(text, voice_path, voice, args.rate))
        paragraphs = split_paragraphs(text)
        word_offsets = group_to_paragraphs(paragraphs, raw)

    duration = probe_duration(voice_path)

    result = {
        "engine": engine,
        "voice": voice,
        "rate": args.rate,
        "text": text,
        "audioFile": str(voice_path),
        "duration": round(duration, 3) if duration else None,
        "wordBoundaries": word_offsets,
    }
    meta_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[ok] 配音: {voice_path} ({result['duration']}s)")
    print(f"[ok] 元数据: {meta_path}")
    print(f"[info] 段落/对白边界: {len(result['wordBoundaries'])} 个")

if __name__ == "__main__":
    main()
