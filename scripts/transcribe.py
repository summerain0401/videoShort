#!/usr/bin/env python3
"""
transcribe.py — 音频转写脚本
将音频文件转为带词语时间戳的转写结果（JSON + 纯文本）。

用法:
    python scripts/transcribe.py <audio_file> [--model small] [--lang zh]

输出:
    <audio_dir>/transcript.json   # 完整转写（含词语级时间戳）
    <audio_dir>/transcript.txt    # 纯文本（校对用）
"""
import argparse
import json
import sys
from pathlib import Path


def transcribe(audio_path: Path, model_size: str = "small", language: str = "zh") -> dict:
    from faster_whisper import WhisperModel

    print(f"[transcribe] 加载模型 {model_size} ...", file=sys.stderr)
    model = WhisperModel(model_size, device="cpu", compute_type="int8")

    print(f"[transcribe] 转写 {audio_path} ...", file=sys.stderr)
    segments, info = model.transcribe(
        str(audio_path),
        language=language,
        word_timestamps=True,
        vad_filter=True,
    )

    words = []
    segment_list = []
    for seg in segments:
        seg_words = []
        for w in seg.words:
            seg_words.append({
                "word": w.word.strip(),
                "start": round(w.start, 3),
                "end": round(w.end, 3),
            })
        words.extend(seg_words)
        segment_list.append({
            "text": seg.text.strip(),
            "start": round(seg.start, 3),
            "end": round(seg.end, 3),
            "words": seg_words,
        })

    result = {
        "audioFile": str(audio_path),
        "language": info.language,
        "languageProbability": round(info.language_probability, 4),
        "duration": round(info.duration, 3) if info.duration else None,
        "segments": segment_list,
        "words": words,
    }
    return result


def main():
    parser = argparse.ArgumentParser(description="音频转写（带词语时间戳）")
    parser.add_argument("audio", help="音频文件路径 (mp3/wav/m4a)")
    parser.add_argument("--model", default="small", help="whisper 模型大小: tiny/base/small/medium/large-v3")
    parser.add_argument("--lang", default="zh", help="语言代码，默认 zh")
    args = parser.parse_args()

    audio_path = Path(args.audio)
    if not audio_path.exists():
        print(f"[error] 文件不存在: {audio_path}", file=sys.stderr)
        sys.exit(1)

    result = transcribe(audio_path, args.model, args.lang)

    out_dir = audio_path.parent
    json_path = out_dir / "transcript.json"
    txt_path = out_dir / "transcript.txt"

    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    txt_path.write_text("\n".join(s["text"] for s in result["segments"]), encoding="utf-8")

    print(f"[ok] 转写完成: {json_path}")
    print(f"[ok] 纯文本: {txt_path}")
    print(f"[info] 共 {len(result['segments'])} 段, {len(result['words'])} 词, 时长 {result['duration']}s")


if __name__ == "__main__":
    main()
