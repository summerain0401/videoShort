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
    python scripts/tts.py <text_file|text> <output_dir> [--engine auto|azure|edge] [--voice zh-CN-YunxiNeural] [--rate +20%]

语速默认 +20%（1.2x，工程标准 1.15x~1.25x），可用 TTS_RATE 环境变量覆盖；
Azure 路径额外支持 TTS_PITCH（默认 +1st）与句读微停顿（情感节奏）。
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

# ---------------------------------------------------------------- 多音字纠正

# 发音纠正字典：词 -> sapi 拼音（数字声调）
# 命中词在 SSML 中包裹 <phoneme alphabet="sapi" ph="...">，只改发音不改文本，
# 因此 WordBoundary 事件的 evt.text 不变，build-timeline.py 对齐不受影响。
# 词条按「最易误读」的财经/生活高频词收录，可随口播稿风险词持续扩充。
#
# ⚠ 2026-08-21 实测结论：当前可用的两个引擎均不支持 <phoneme>——
#   · Azure Speech SDK（region=eastasia，zh-CN 全音色 + sapi/ipa/ups alphabet）→ 全部 Canceled
#   · edge-tts 消费端点（speech.platform.bing.com）→ NoAudioReceived，且 <break>/<say-as>
#     会被当正文朗读
# 因此本功能默认关闭（ENABLE_PHONEME=1 才注入），多音字预防以
# scripts/check-pronunciation.py 预检 + 口播稿改写（文案规避）为主。
PRONUNCIATION_OVERRIDES: dict[str, str] = {
    # 财经高频
    "便宜": "pian2 yi5",        # 易读 biànyí
    "花呗": "hua1 bei1",        # 易读 huābèi
    "公积金": "gong1 ji1 jin1",
    "个税": "ge4 shui4",
    "还了": "huan2 le5",        # 易读 hái
    "先花后还": "xian1 hua1 hou4 huan2",
    "涨": "zhang3",             # 涨价/上涨
    "挣钱": "zheng4 qian2",     # 易读 zhēng
    "省": "sheng3",             # 省钱/节省
    # 生活口语
    "干等": "gan4 deng3",       # 易读 gān
    "干活": "gan4 huo2",
    "藏着": "cang2 zhe5",       # 易读 zàng
    "空儿": "kong4 r5",
}


def apply_phoneme_overrides(text: str) -> str:
    """把命中的多音字词包裹为 SSML phoneme 标签，其余文本保持 XML 转义。

    词按长度降序匹配（长词优先，避免「藏」吞掉「藏着」），
    文本本体不变 → 合成结果字符与输入一致 → 时间轴对齐不受影响。

    默认关闭：仅当所用引擎确认支持 SSML phoneme 时设 ENABLE_PHONEME=1 开启。
    当前 Azure/edge 均不支持（见上注释），设了也不生效、且会让 Azure 合成失败。
    """
    if os.environ.get("ENABLE_PHONEME") != "1" or not PRONUNCIATION_OVERRIDES:
        return escape_xml(text)

    # 按词长降序排序，保证长词先匹配
    words = sorted(PRONUNCIATION_OVERRIDES.keys(), key=len, reverse=True)
    pattern = re.compile("|".join(re.escape(w) for w in words))

    def _replace(match: re.Match) -> str:
        word = match.group(0)
        ph = PRONUNCIATION_OVERRIDES[word]
        return f'<phoneme alphabet="sapi" ph="{ph}">{escape_xml(word)}</phoneme>'

    return pattern.sub(_replace, escape_xml(text))


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


# ---------------------------------------------------------------- 情感停顿

# 句读 → 停顿时长：解说节奏感（提升语调丰富度，避免机械平铺）
# ⚠ 仅 Azure SSML 路径可用：edge-tts 消费端点会把 <break> 当正文朗读（2026-08 实测）
# 时长已压缩（140→100ms / 60→40ms）：语速提到 1.2x 后停顿过长会拖节奏（用户反馈）
PAUSE_BREAKS = [
    (re.compile(r"([。！？；])"), r"\1<break time=\"100ms\"/>"),
    (re.compile(r"([，、：])"), r"\1<break time=\"40ms\"/>"),
]


def inject_pauses(text: str) -> str:
    """在句读标点后插入微停顿（SSML <break>），提升解说节奏。

    输入应为已 XML 转义的文本；标点不含 XML 特殊字符，安全。
    文本本体不变 → 合成结果字符与输入一致 → 时间轴对齐不受影响
    （WordBoundary 事件的 evt.text 不含标签，仅 offset 顺延，边界仍精确）。
    """
    for pat, repl in PAUSE_BREAKS:
        text = pat.sub(repl, text)
    return text


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

    # edge-tts 消费端点实测不支持 SSML phoneme（2026-08）：显式开启时提示纠正不会生效
    if os.environ.get("ENABLE_PHONEME") == "1":
        hit = [w for w in PRONUNCIATION_OVERRIDES if w in text]
        if hit:
            print(f"[warn] edge-tts 不支持 phoneme 发音纠正，以下词可能误读: {', '.join(hit)}", file=sys.stderr)
            print(f"[hint]  建议 --engine azure（需 .env 配置 AZURE_SPEECH_KEY）或改写口播稿规避多音字", file=sys.stderr)

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
        f'<prosody rate="{normalize_rate(rate)}" pitch="{os.environ.get("TTS_PITCH", "+1st")}">'
        f'{inject_pauses(apply_phoneme_overrides(text))}'
        "</prosody></voice></speak>"
    )
    result = synthesizer.speak_ssml_async(ssml).get()

    if result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
        # 新版 SDK 的 SpeechSynthesisResult 已无 error_details 属性，用 getattr 兜底
        details = getattr(result, "error_details", "") or ""
        raise RuntimeError(
            f"Azure TTS 合成失败: {result.reason} | {details}"
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
    parser.add_argument("--rate", default=os.environ.get("TTS_RATE", "+20%"),
                        help="语速，如 +10% / -5%（默认 +20%，可用环境变量 TTS_RATE 覆盖，建议 1.15x~1.25x）")
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
