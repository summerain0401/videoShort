"""
布丁经济学账号头像派生版生成
============================
基于规范角色 char_小布丁_explaining.png 生成 3 版头像：

  1. avatar_circle.png     - 圆形版（视频号/小红书/抖音头像裁切用，径向渐变蜜桃粉→奶油白）
  2. avatar_rounded.png    - 圆角方形版（公众号/官网用，对角渐变）
  3. avatar_original.png   - 透明原图（其他平台直接上传用）

设计要点：
  - 1024×1024 高清（满足 4K 显示与多端压缩）
  - 主体上移居中（安全裁切区，头部不被切）
  - 品牌色径向渐变（温暖、治愈）
  - 不绘制文字（避免后期乱码）
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
CHAR_PATH = ROOT / "shared/characters/char_小布丁_explaining.png"
OUT_DIR = ROOT / "shared/avatars"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SIZE = 1024

# 品牌色（与 ACCOUNT_BRAND.md 第 4 节保持一致）
CREAM = (255, 248, 239, 255)     # 奶油白 #FFF8EF
PEACH = (255, 227, 216, 255)     # 蜜桃粉 #FFE3D8
APRICOT = (255, 217, 179, 255)   # 浅橙 #FFD9B3


def radial_gradient(size: int, inner: tuple, outer: tuple, center: tuple | None = None) -> Image.Image:
    """生成径向渐变底图（中心 → 边缘）。"""
    if center is None:
        center = (size // 2, int(size * 0.45))  # 中心略上，配合主体位置
    cx, cy = center
    max_r = ((size - cx) ** 2 + (size - cy) ** 2) ** 0.5
    img = Image.new("RGBA", (size, size), outer)
    px = img.load()
    for y in range(size):
        for x in range(size):
            d = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
            t = min(1.0, d / max_r)
            # 线性插值
            r = int(inner[0] * (1 - t) + outer[0] * t)
            g = int(inner[1] * (1 - t) + outer[1] * t)
            b = int(inner[2] * (1 - t) + outer[2] * t)
            px[x, y] = (r, g, b, 255)
    return img


def diagonal_gradient(size: int, c1: tuple, c2: tuple) -> Image.Image:
    """对角渐变（左上 → 右下）。"""
    img = Image.new("RGBA", (size, size), c1)
    px = img.load()
    for y in range(size):
        for x in range(size):
            t = (x + y) / (2 * size)
            r = int(c1[0] * (1 - t) + c2[0] * t)
            g = int(c1[1] * (1 - t) + c2[1] * t)
            b = int(c1[2] * (1 - t) + c2[2] * t)
            px[x, y] = (r, g, b, 255)
    return img


def render_circle() -> Image.Image:
    """圆形头像：径向渐变 + 主体居中偏上。"""
    # 圆形渐变底：中心亮奶油白 → 边缘蜜桃粉（更明显对比）
    bg = radial_gradient(SIZE, inner=CREAM, outer=PEACH, center=(SIZE // 2, int(SIZE * 0.45)))
    canvas = bg.copy()

    # 主体
    char = Image.open(CHAR_PATH).convert("RGBA")
    # 缩放到 80% 高度（确保头部在圆形裁切安全区）
    target_h = int(SIZE * 0.80)
    scale = target_h / char.height
    new_w = int(char.width * scale)
    char = char.resize((new_w, target_h), Image.LANCZOS)

    # 居中偏上
    cx = SIZE // 2
    char_x = cx - new_w // 2
    char_y = int(SIZE * 0.10)  # 顶部留 10%，脚部留 10%

    # 直接贴角色（不加柔光，避免盖住细节）
    canvas.paste(char, (char_x, char_y), char)

    # 应用圆形蒙版（确保输出就是圆形 RGBA）
    mask = Image.new("L", (SIZE, SIZE), 0)
    md = ImageDraw.Draw(mask)
    md.ellipse((0, 0, SIZE, SIZE), fill=255)
    canvas.putalpha(mask)
    return canvas


def render_rounded() -> Image.Image:
    """圆角方形头像：对角渐变 + 圆角蒙版。"""
    bg = diagonal_gradient(SIZE, PEACH, APRICOT)
    canvas = bg.copy()

    char = Image.open(CHAR_PATH).convert("RGBA")
    target_h = int(SIZE * 0.82)
    scale = target_h / char.height
    new_w = int(char.width * scale)
    char = char.resize((new_w, target_h), Image.LANCZOS)

    cx = SIZE // 2
    char_x = cx - new_w // 2
    char_y = int(SIZE * 0.08)

    canvas.paste(char, (char_x, char_y), char)

    # 圆角蒙版
    mask = Image.new("L", (SIZE, SIZE), 0)
    md = ImageDraw.Draw(mask)
    radius = 220
    md.rounded_rectangle((0, 0, SIZE, SIZE), radius=radius, fill=255)
    canvas.putalpha(mask)
    return canvas


def render_original() -> Image.Image:
    """透明原图：直接复制。"""
    char = Image.open(CHAR_PATH).convert("RGBA")
    # 缩放到 1024 高度等比
    scale = SIZE / char.height
    new_w = int(char.width * scale)
    return char.resize((new_w, SIZE), Image.LANCZOS)


def main():
    print(f"[avatar] 加载角色：{CHAR_PATH.name}")
    if not CHAR_PATH.exists():
        sys.exit(f"角色文件不存在：{CHAR_PATH}")

    circle = render_circle()
    circle.save(OUT_DIR / "avatar_circle.png", "PNG", optimize=True)
    print(f"[avatar] 圆形版 → {OUT_DIR / 'avatar_circle.png'}")

    rounded = render_rounded()
    rounded.save(OUT_DIR / "avatar_rounded.png", "PNG", optimize=True)
    print(f"[avatar] 圆角方形版 → {OUT_DIR / 'avatar_rounded.png'}")

    original = render_original()
    original.save(OUT_DIR / "avatar_original.png", "PNG", optimize=True)
    print(f"[avatar] 透明原图版 → {OUT_DIR / 'avatar_original.png'}")

    print("[avatar] 三版头像生成完毕。")


if __name__ == "__main__":
    main()
