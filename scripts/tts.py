#!/usr/bin/env python3
"""
tts.py — 配音生成脚本

支持两种引擎:
  azure  Azure Speech SDK（推荐，需环境变量 AZURE_SPEECH_KEY / AZURE_SPEECH_REGION）
  edge   edge-tts（免费兜底，无需配置）

统一输出:
  <output_dir>/voice.mp3   # 配音音频
  <output_dir>/voice.json  # 音频信息 + 句子级时间戳（wordBoundaries，100ns tick）

Azure 引擎的词级 WordBoundary 事件会按中文标点聚合为句子边界，
与 edge-tts 的 SentenceBoundary 输出格式保持一致，build-timeline.py 无需改动。

用法:
    python scripts/tts.py <text_file|text> <output_dir> [--engine auto|azure|edge] [--voice zh-CN-YunxiNeural] [--rate +0%]
"""
import argparse
import asyncio
import datetime
import json
import os
import re
import sys
from pathlib import Path

DEFAULT_VOICE = "zh-CN-YunxiNeural"  # 云希男声，适合解说
VOICE_POOL = [
    "zh-CN-YunxiNeural",   # 云希（男，推荐解说）
    "zh-CN-YunjianNeural", # 云健（男，沉稳）
    "zh-CN-XiaoxiaoNeural",# 晓晓（女，亲切）
    "zh-CN-YunyangNeural", # 云扬（男，新闻感）
]
TICK_TO_SEC = 10_000_000  # 100ns tick


# ---------------------------------------------------------------- 通用工具

def escape_xml(text: str) -> str:
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
    )


def normalize_rate(rate: str) -> str:
    """把 edge 风格语速 '+10%' 归一化为 SSML 风格 '+10.00%'"""
    rate = rate.strip()
    if rate.endswith("%") and "." not in rate:
        sign = "+" if rate.startswith("+") else "-" if rate.startswith("-") else ""
        num = rate.strip("+-%")
        if num.isdigit():
            return f"{sign}{num}.00%"
    return rate if rate else "+0.00%"


def _norm(s: str) -> str:
    """去标点空白，用于文本比对"""
    return re.sub(r"[\s，。！？、,.!?；;：:\"'“”‘’（）()【】\-]", "", s)


def split_paragraphs(text: str) -> list:
    """按空行切分口播稿段落（约定：一段 = 一个场景）。无空行时视为整段。"""
    parts = [p.strip() for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]
    return parts if len(parts) >= 2 else [text.strip()]


def group_to_paragraphs(paragraphs: list, boundaries: list) -> list:
    """把原子边界（edge 的句子边界 或 azure 的词边界）按文本顺序贪心聚合到段落。

    每段取首边界 offset 为起点、末边界 offset+duration 为终点，
    输出段落级边界（word 字段=整段文本），保证 段落数 == 边界数，
    build-timeline.py 可精确对齐，口播内可自由使用句号/问号。
    """
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


# ---------------------------------------------------------------- edge 引擎

async def edge_generate_tts(text: str, output_path: Path, voice: str, rate: str) -> dict:
    import edge_tts

    communicate = edge_tts.Communicate(text, voice, rate=rate)
    audio_bytes = b""
    word_offsets = []

    # 新版 edge-tts 返回 SentenceBoundary 事件（句子级时间戳）
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


# ---------------------------------------------------------------- azure 引擎

def azure_generate_tts(text: str, output_path: Path, voice: str, rate: str,
                       key: str, region: str) -> dict:
    import azure.cognitiveservices.speech as speechsdk

    speech_config = speechsdk.SpeechConfig(subscription=key, region=region)
    # 48kHz / 192kbps 单声道 MP3，音质优于 edge-tts 的 24kHz
    speech_config.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Audio48Khz192KBitRateMonoMp3
    )
    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)

    word_boundaries = []

    def on_word_boundary(evt):
        dur = evt.duration
        # SDK >= 1.4x 的 duration 为 datetime.timedelta，统一转 100ns tick
        if isinstance(dur, datetime.timedelta):
            dur = int(dur.total_seconds() * TICK_TO_SEC)
        word_boundaries.append({
            "word": evt.text,
            "offset": evt.audio_offset,          # 100ns tick，与 edge-tts 一致
            "duration": dur or 0,
        })

    # SDK >= 1.4x 事件名为 synthesis_word_boundary（旧版为 word_boundary）
    synthesizer.synthesis_word_boundary.connect(on_word_boundary)

    ssml = (
        '<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="zh-CN">'
        f'<voice name="{voice}">'
        f'<prosody rate="{normalize_rate(rate)}">{escape_xml(text)}</prosody>'
        "</voice></speak>"
    )
    result = synthesizer.speak_ssml_async(ssml).get()

    if result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
        raise RuntimeError(
            f"Azure TTS 合成失败: {result.reason} | {result.error_details or ''}"
        )
    output_path.write_bytes(result.audio_data)

    # 返回词级边界（由调用方按口播稿段落聚合为段落级）
    return word_boundaries


def detect_azure() -> tuple | None:
    key = os.environ.get("AZURE_SPEECH_KEY", "").strip()
    region = os.environ.get("AZURE_SPEECH_REGION", "").strip()
    if key and region:
        return key, region
    return None


# ---------------------------------------------------------------- 公共

def probe_duration(output_path: Path) -> float | None:
    import subprocess
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "json", str(output_path)],
            capture_output=True, text=True,
        )
        if r.returncode == 0:
            return float(json.loads(r.stdout)["format"]["duration"])
    except Exception:
        pass
    return None


def main():
    parser = argparse.ArgumentParser(description="配音生成：Azure TTS / edge-tts")
    parser.add_argument("input", help="文本内容或文本文件路径")
    parser.add_argument("output_dir", help="输出目录")
    parser.add_argument("--engine", default="auto", choices=["auto", "azure", "edge"],
                        help="合成引擎（auto=有 Azure key 用 azure，否则 edge）")
    parser.add_argument("--voice", default=None,
                        help="音色（默认取环境变量 AZURE_VOICE，再回退 zh-CN-YunxiNeural）")
    parser.add_argument("--rate", default="+0%", help="语速，如 +10% / -5%")
    args = parser.parse_args()

    # 音色优先级：--voice 参数 > AZURE_VOICE 环境变量 > 默认
    voice = args.voice or os.environ.get("AZURE_VOICE", "").strip() or DEFAULT_VOICE

    input_arg = Path(args.input)
    text = input_arg.read_text(encoding="utf-8") if input_arg.exists() else args.input

    engine = args.engine
    if engine == "auto":
        engine = "azure" if detect_azure() else "edge"
    if engine == "azure" and not detect_azure():
        print("[error] --engine azure 需要环境变量 AZURE_SPEECH_KEY 和 AZURE_SPEECH_REGION",
              file=sys.stderr)
        print("[hint]  可在项目根 .env 中配置（pipeline.sh 会自动加载）", file=sys.stderr)
        sys.exit(1)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    voice_path = out_dir / "voice.mp3"
    meta_path = out_dir / "voice.json"

    print(f"[tts] 引擎: {engine}, 音色: {voice}, 语速: {args.rate}, "
          f"文本 {len(text)} 字, {len(split_paragraphs(text))} 个段落(场景)")
    if engine == "azure":
        key, region = detect_azure()
        raw = azure_generate_tts(text, voice_path, voice, args.rate, key, region)
    else:
        raw = asyncio.run(edge_generate_tts(text, voice_path, voice, args.rate))

    # 原子边界 → 段落级边界（段落数 == 边界数，build-timeline 精确对齐）
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
    print(f"[info] 段落边界: {len(result['wordBoundaries'])} 个")


if __name__ == "__main__":
    main()
