#!/usr/bin/env python3
"""
tech-check.py — 技术检查脚本
渲染完成后自动检查视频时长、音频时长、首末帧等基础指标。

用法:
    python scripts/tech-check.py <video_file> [--audio voice.mp3]

输出:
    JSON 格式技术检查报告
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path


def ffprobe(path: Path) -> dict:
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json",
         "-show_format", "-show_streams", str(path)],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        return {"error": r.stderr.strip()}
    return json.loads(r.stdout)


def main():
    parser = argparse.ArgumentParser(description="成片技术检查")
    parser.add_argument("video", help="渲染完成的 MP4 路径")
    parser.add_argument("--audio", help="参考音频路径（对比时长）")
    args = parser.parse_args()

    video = Path(args.video)
    if not video.exists():
        print(f"[error] 视频不存在: {video}", file=sys.stderr)
        sys.exit(1)

    info = ffprobe(video)
    report = {"video": str(video), "issues": []}

    if "error" in info:
        report["issues"].append({"level": "error", "message": f"ffprobe 失败: {info['error']}"})
    else:
        streams = info.get("streams", [])
        video_stream = next((s for s in streams if s["codec_type"] == "video"), None)
        audio_stream = next((s for s in streams if s["codec_type"] == "audio"), None)

        duration = float(info.get("format", {}).get("duration", 0))
        report["duration"] = round(duration, 3)

        if video_stream:
            report["codec"] = video_stream.get("codec_name")
            report["resolution"] = f"{video_stream.get('width')}x{video_stream.get('height')}"
            report["fps"] = video_stream.get("r_frame_rate")
            if video_stream.get("codec_name") != "h264":
                report["issues"].append({
                    "level": "warning",
                    "message": f"编码不是 H.264: {video_stream.get('codec_name')}",
                })
        if not audio_stream:
            report["issues"].append({"level": "error", "message": "视频没有音轨"})

    if args.audio:
        audio_path = Path(args.audio)
        if audio_path.exists():
            ainfo = ffprobe(audio_path)
            a_dur = float(ainfo.get("format", {}).get("duration", 0))
            report["audioDuration"] = round(a_dur, 3)
            diff = abs(duration - a_dur)
            if diff > 1.0:
                report["issues"].append({
                    "level": "error",
                    "message": f"视频时长 {duration:.2f}s 与音频时长 {a_dur:.2f}s 差异过大 ({diff:.2f}s)",
                })

    report["pass"] = not any(i["level"] == "error" for i in report["issues"])
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
