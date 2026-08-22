#!/usr/bin/env python3
"""
sfx-gen.py — 程序化转场音效合成器（不依赖任何外部音频素材）

两种音效：
  pop    短促低频"啵"声：500→180Hz 指数扫频 + 快速衰减，约 60ms（适合场景间切换）
  whoosh 气流"嗖"声：白噪声经扫频带通（state-variable filter 400→1800Hz）
          + 升-降幅度包络，约 320ms（适合大段落转场：片头/片尾）

按时间标记生成一整条音效轨（未标记处为静音），长度 = --duration。

用法:
  python scripts/sfx-gen.py --marks "0.0:whoosh,3.5:pop,8.2:pop" --duration 60 --out sfx.wav

输出:
  16bit / 48kHz 单声道 WAV（与 Azure 48kHz 输出对齐，混音无需重采样）
"""
import argparse
import math
import random
import struct
import wave

SAMPLE_RATE = 48000


def _clamp(v: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def synth_pop(duration: float = 0.06) -> list[float]:
    """短促低频啵声：500→180Hz 指数扫频 + 指数衰减"""
    n = int(duration * SAMPLE_RATE)
    out = []
    for i in range(n):
        t = i / SAMPLE_RATE
        prog = t / duration
        freq = 500 * (180 / 500) ** prog
        phase = 2 * math.pi * freq * t
        amp = math.exp(-t / 0.018) * (1 - prog) ** 0.5
        out.append(_clamp(math.sin(phase) * amp * 0.9))
    return out


def synth_whoosh(duration: float = 0.32) -> list[float]:
    """气流嗖声：白噪声 → 扫频带通（SVF 400→1800Hz，Q=2）→ 升-降包络"""
    n = int(duration * SAMPLE_RATE)
    rng = random.Random(42)  # 固定种子，输出可复现
    noise = [rng.uniform(-1, 1) for _ in range(n)]

    # state-variable filter（带通输出）：freq 线性扫频
    out = []
    lp = hp = bp = 0.0
    for i in range(n):
        t = i / SAMPLE_RATE
        prog = t / duration
        freq = 400 + (1800 - 400) * prog
        q = 2.0
        f = 2 * math.sin(math.pi * min(freq, SAMPLE_RATE * 0.45) / SAMPLE_RATE)
        lp += f * bp
        hp = noise[i] - lp - q * bp
        bp += f * hp
        # 升-降包络：前 60ms 爬升，后 260ms 释放
        env = min(t / 0.06, 1.0) * (1 - max(0.0, (t - 0.06) / (duration - 0.06)))
        out.append(_clamp(bp * env * 0.85))
    return out


SYNTH = {"pop": synth_pop, "whoosh": synth_whoosh}


def render_track(marks: list[tuple[float, str]], duration: float) -> list[float]:
    """把多个音效叠加到一条全长轨道上（时间点重叠时线性叠加）"""
    total = int(duration * SAMPLE_RATE)
    track = [0.0] * total
    for t_sec, kind in marks:
        samples = SYNTH[kind]()
        start = int(t_sec * SAMPLE_RATE)
        for i, s in enumerate(samples):
            idx = start + i
            if idx < total:
                track[idx] += s
    return track


def write_wav(path, samples: list[float]) -> None:
    n = len(samples)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        frames = bytearray()
        for s in samples:
            frames += struct.pack("<h", int(_clamp(s) * 32767))
        w.writeframes(bytes(frames))
    print(f"[sfx] 已生成: {path} ({n / SAMPLE_RATE:.1f}s)")


def main():
    ap = argparse.ArgumentParser(description="程序化转场音效合成")
    ap.add_argument("--marks", required=True,
                    help="音效标记列表，格式 '时间秒:类型,时间秒:类型'，如 '0:whoosh,3.5:pop'")
    ap.add_argument("--duration", type=float, required=True, help="音效轨总时长（秒）")
    ap.add_argument("--out", default="sfx.wav", help="输出 WAV 路径")
    args = ap.parse_args()

    marks = []
    for m in args.marks.split(","):
        m = m.strip()
        if not m:
            continue
        t_str, kind = m.split(":", 1)
        kind = kind.strip().lower()
        if kind not in SYNTH:
            raise SystemExit(f"[error] 未知音效类型: {kind}（可选 pop/whoosh）")
        marks.append((max(0.0, float(t_str)), kind))

    track = render_track(marks, args.duration)
    write_wav(args.out, track)


if __name__ == "__main__":
    main()
