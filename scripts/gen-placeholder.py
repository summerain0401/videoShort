#!/usr/bin/env python3
"""
gen-placeholder.py — 生成示例占位素材
为示例项目生成简单的占位图（背景/角色/道具），用于验证渲染链路。
正式项目中应使用 GPT Image / Flux 生成真实素材。

用法:
    python scripts/gen-placeholder.py
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
SHARED = ROOT / "shared"
W, H = 1080, 1920


def get_font(size: int):
    for name in ["PingFang.ttc", "Hiragino Sans GB.ttc", "Arial Unicode.ttf"]:
        try:
            return ImageFont.truetype(f"/System/Library/Fonts/{name}", size)
        except Exception:
            continue
    return ImageFont.load_default()


def gen_background(name: str, color: str):
    img = Image.new("RGB", (W, H), color)
    d = ImageDraw.Draw(img)
    # 简单装饰：底部色带 + 文字
    d.rectangle([0, H - 280, W, H], fill=(20, 30, 50))
    d.text((60, H - 200), f"BG · {name}", font=get_font(56), fill=(255, 255, 255))
    path = SHARED / "backgrounds" / f"bg_{name}.png"
    img.save(path)
    print(f"[ok] 背景: {path.relative_to(ROOT)}")


def gen_transparent(name: str, label: str, color: tuple, w=500, h=700, kind: str = "char"):
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # 圆形主体 + 文字标签
    d.ellipse([w//4, h//6, 3*w//4, 5*h//6], fill=color)
    d.rectangle([0, h-90, w, h], fill=(0, 0, 0, 160))
    d.text((w//2, h-45), label, font=get_font(40), fill=(255, 255, 255), anchor="mm")
    path = SHARED / ("characters" if kind == "char" else "props") / f"{kind[:4]}_{name}.png"
    img.save(path)
    print(f"[ok] {'角色' if kind=='char' else '道具'}: {path.relative_to(ROOT)}")


def main():
    gen_background("town", "#0e7490")
    gen_background("market", "#1e3a5f")

    gen_transparent("小明", "小明", (240, 150, 60), kind="char")
    gen_transparent("钱袋", "钱袋", (200, 180, 90), w=360, h=360, kind="prop")
    gen_transparent("物价牌", "物价牌", (230, 120, 120), w=320, h=420, kind="prop")
    gen_transparent("超市货架", "货架", (120, 200, 160), w=420, h=520, kind="prop")
    gen_transparent("工资条", "工资条", (180, 180, 220), w=340, h=400, kind="prop")

    print("\n[ok] 占位素材生成完毕（共 7 张）")
    print("提示: 这些是占位图，正式项目请用 GPT Image / Flux 生成真实素材")


if __name__ == "__main__":
    main()
