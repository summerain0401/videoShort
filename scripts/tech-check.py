#!/usr/bin/env python3
"""
tech-check.py — 技术检查脚本
渲染完成后自动检查视频时长、音频时长、首末帧、中间黑帧等基础指标。

用法:
    python scripts/tech-check.py <video_file> [--audio voice.mp3] [--timeline timeline.json]

输出:
    JSON 格式技术检查报告

黑帧规则:
    - 片头(<0.5s)/片尾(>duration-0.5s)的黑帧视为淡入淡出，仅记录不报错
    - 内容区(中间)黑帧 >= black_min_duration 记为 error，需返回修复
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


def detect_black_frames(video: Path, min_duration: float = 0.5, pix_threshold: float = 0.10) -> list:
    """用 ffmpeg blackdetect 滤镜扫描黑帧。

    返回 [{start, end, duration}, ...]，按 start 升序。
    黑帧 = 亮度低于 pix_threshold(默认10%) 且持续 >= min_duration 的片段。
    """
    r = subprocess.run(
        ["ffmpeg", "-v", "info", "-i", str(video),
         "-vf", f"blackdetect=d={min_duration}:pix_th={pix_threshold}",
         "-an", "-f", "null", "-"],
        capture_output=True, text=True,
    )
    blacks = []
    # 输出行格式: [blackdetect @ 0x...] black_start:0 black_end:1.5 black_duration:1.5
    for line in r.stderr.splitlines():
        if "black_start:" not in line:
            continue
        parts = {}
        for token in line.split():
            if ":" in token:
                k, _, v = token.partition(":")
                parts[k] = v
        if "black_start" in parts:
            blacks.append({
                "start": round(float(parts.get("black_start", 0)), 3),
                "end": round(float(parts.get("black_end", 0)), 3),
                "duration": round(float(parts.get("black_duration", 0)), 3),
            })
    return blacks


def main():
    parser = argparse.ArgumentParser(description="成片技术检查")
    parser.add_argument("video", help="渲染完成的 MP4 路径")
    parser.add_argument("--audio", help="参考音频路径（对比时长）")
    parser.add_argument("--timeline", help="时间轴 JSON 路径；用于把片头/片尾包装时长计入预期时长")
    parser.add_argument("--packaging-duration", type=float, default=8.0, help="片头+片尾预期包装时长，默认 8 秒")
    parser.add_argument("--black-min-duration", type=float, default=0.5,
                        help="黑帧判定最短时长(秒)，默认 0.5")
    parser.add_argument("--black-pix-threshold", type=float, default=0.10,
                        help="黑帧亮度阈值(0-1)，默认 0.10（亮度低于10%视为黑）")
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

        # ── 黑帧检测（只把内容区黑帧算问题，首尾淡入淡出黑帧仅记录） ──
        try:
            blacks = detect_black_frames(video, args.black_min_duration, args.black_pix_threshold)
            report["blackFrames"] = blacks
            mid_black = [b for b in blacks
                         if b["start"] >= 0.5 and b["end"] <= duration - 0.5]
            for b in mid_black:
                report["issues"].append({
                    "level": "error",
                    "message": (f"内容区黑帧 {b['start']:.2f}s-{b['end']:.2f}s "
                                f"(持续 {b['duration']:.2f}s)，可能因空背景/转场淡黑导致，需修复"),
                })
            if not mid_black and blacks:
                report["notes"] = report.get("notes", []) + [
                    f"检测到 {len(blacks)} 处黑帧，均位于首尾淡入淡出区（正常）"
                ]
        except FileNotFoundError:
            report["issues"].append({
                "level": "warning",
                "message": "未找到 ffmpeg，跳过黑帧检测",
            })

    if args.audio:
        audio_path = Path(args.audio)
        if audio_path.exists():
            ainfo = ffprobe(audio_path)
            a_dur = float(ainfo.get("format", {}).get("duration", 0))
            report["audioDuration"] = round(a_dur, 3)
            expected_duration = a_dur + args.packaging_duration
            if args.timeline and Path(args.timeline).exists():
                try:
                    timeline = json.loads(Path(args.timeline).read_text(encoding="utf-8"))
                    timeline_duration = float(timeline.get("totalDuration", a_dur))
                    expected_duration = timeline_duration + args.packaging_duration
                    report["timelineDuration"] = round(timeline_duration, 3)
                except (OSError, ValueError, json.JSONDecodeError):
                    report["issues"].append({
                        "level": "warning",
                        "message": "无法读取 timeline.json，已回退到音频时长校验",
                    })
            report["expectedDuration"] = round(expected_duration, 3)
            diff = abs(duration - expected_duration)
            if diff > 1.0:
                report["issues"].append({
                    "level": "error",
                    "message": f"视频时长 {duration:.2f}s 与预期时长 {expected_duration:.2f}s 差异过大 ({diff:.2f}s)",
                })

    report["pass"] = not any(i["level"] == "error" for i in report["issues"])
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
