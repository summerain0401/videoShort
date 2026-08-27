#!/usr/bin/env python3
"""
generate-cover.py — 爆款短视频高点击率（CTR）封面生成器 2.1
=========================================================
专为抖音/小红书/B站短视频打造：
- 黄金 3 秒高饱和度视觉冲击（黑黄警示胶带风、红白爆破风、深色霓虹风）
- 夸张情绪角色放大（占据封面 50%~60% 黄金视觉区）
- 倾斜大字痛点标题（带强描边、投影与高亮色块打底）
- 爆款悬念贴纸与利益点标签
"""
import argparse
import json
import math
import os
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
MATERIAL_LIBRARY = ROOT / "shared/material-library.json"

def find_font():
    candidates = [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
    ]
    for c in candidates:
        if Path(c).exists():
            return c
    return None

def load_font(size, font_path=None):
    path = font_path or find_font()
    if path:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()

def add_drop_shadow(canvas, img, offset=(12, 16), blur=16, opacity=120, shadow_color=(20, 15, 10)):
    alpha = img.split()[-1]
    shadow = Image.new("RGBA", img.size, (*shadow_color, 0))
    mask = alpha.point(lambda a: int(a * (opacity / 255)))
    shadow.putalpha(mask)
    shadow = shadow.filter(ImageFilter.GaussianBlur(blur))
    ox, oy = offset
    canvas.paste(shadow, (ox, oy), shadow)

def draw_stroked_text(draw, pos, text, font, text_color, stroke_color, stroke_width=6):
    """绘制带粗描边的醒目大字"""
    x, y = pos
    # 绘制描边
    for dx in range(-stroke_width, stroke_width + 1):
        for dy in range(-stroke_width, stroke_width + 1):
            if dx * dx + dy * dy <= stroke_width * stroke_width:
                draw.text((x + dx, y + dy), text, font=font, fill=stroke_color)
    # 绘制正文字
    draw.text((x, y), text, font=font, fill=text_color)

def build_viral_cover(
    bg_path,
    char_path,
    prop_path,
    title,
    subtitle,
    tags,
    brand="野原经济学",
    slogan="看懂生活底层套路",
    font_path=None,
    output=None,
    sticker_text="⚠️ 惊人内幕"
):
    """爆款高点击率封面 (Viral 3:4 竖屏 1080x1440)"""
    W, H = 1080, 1440
    canvas = Image.new("RGBA", (W, H), (20, 20, 25, 255))

    # 1. 强化背景质感（高斯模糊 + 暖黑渐变遮罩，凸显前景人物与大字）
    if bg_path and Path(bg_path).exists():
        bg = Image.open(bg_path).convert("RGBA").resize((W, H), Image.LANCZOS)
        bg = bg.filter(ImageFilter.GaussianBlur(6)) # 轻微模糊增加景深
    else:
        bg = Image.new("RGBA", (W, H), (30, 25, 40, 255))

    # 叠加暗角与高对比度渐变层
    dark_overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dd = ImageDraw.Draw(dark_overlay)
    for y in range(H):
        # 顶部暗以衬托标题，底部暗以衬托人物
        if y < 600:
            alpha = int(180 * (1 - y / 600 * 0.4))
        else:
            alpha = int(130 + 100 * ((y - 600) / (H - 600)))
        dd.line([(0, y), (W, y)], fill=(15, 12, 22, alpha))
    bg = Image.alpha_composite(bg, dark_overlay)
    canvas.paste(bg, (0, 0))

    draw = ImageDraw.Draw(canvas)

    # 2. 顶部爆款 IP 标识条 (黑金胶囊)
    brand_w, brand_h = 420, 58
    brand_x, brand_y = (W - brand_w) // 2, 45
    draw.rounded_rectangle(
        [brand_x, brand_y, brand_x + brand_w, brand_y + brand_h],
        radius=29,
        fill=(255, 215, 0, 240),
        outline=(255, 255, 255, 200),
        width=3
    )
    f_brand = load_font(28, font_path)
    brand_label = f"【{brand}】 {slogan}"
    bbox = draw.textbbox((0, 0), brand_label, font=f_brand)
    bw = bbox[2] - bbox[0]
    draw.text((brand_x + (brand_w - bw) // 2, brand_y + 12), brand_label, font=f_brand, fill=(20, 20, 20, 255))

    # 3. 巨幅爆款痛点主标题（倾斜黄色胶带/黑底爆破风格）
    f_title = load_font(110, font_path)
    f_sub = load_font(52, font_path)

    # 主标题背景胶带倾斜层
    title_text = title if title else "为什么总没钱？"
    title_box = draw.textbbox((0, 0), title_text, font=f_title)
    tw = title_box[2] - title_box[0]
    th = title_box[3] - title_box[1]

    tape_w = tw + 90
    tape_h = th + 45
    tape_x = (W - tape_w) // 2
    tape_y = 145

    # 绘制高亮黄色斜切底块
    tape_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    td = ImageDraw.Draw(tape_layer)
    # 黄色警示底色
    td.polygon([
        (tape_x, tape_y + 12),
        (tape_x + tape_w, tape_y - 6),
        (tape_x + tape_w - 15, tape_y + tape_h - 4),
        (tape_x - 15, tape_y + tape_h + 14)
    ], fill=(255, 220, 0, 255), outline=(255, 255, 255, 255))
    
    # 投影
    tape_shadow = tape_layer.filter(ImageFilter.GaussianBlur(15))
    canvas.paste(tape_shadow, (6, 10), tape_shadow)
    canvas.paste(tape_layer, (0, 0), tape_layer)

    # 绘制主标题文字（黑字 + 极具张力）
    draw_stroked_text(
        draw,
        (tape_x + 35, tape_y + 12),
        title_text,
        font=f_title,
        text_color=(15, 15, 18, 255),
        stroke_color=(255, 255, 255, 255),
        stroke_width=2
    )

    # 4. 悬念副标题（纯白大字 + 红色强调框）
    if subtitle:
        sub_y = tape_y + tape_h + 30
        sub_box = draw.textbbox((0, 0), subtitle, font=f_sub)
        sw = sub_box[2] - sub_box[0]
        sub_x = (W - sw) // 2
        
        # 黑色半透明底条衬托副标题
        draw.rounded_rectangle(
            [sub_x - 30, sub_y - 8, sub_x + sw + 30, sub_y + 68],
            radius=16,
            fill=(0, 0, 0, 190),
            outline=(255, 60, 60, 220),
            width=3
        )
        draw.text((sub_x, sub_y), subtitle, font=f_sub, fill=(255, 255, 255, 255))

    # 5. 醒目悬念贴纸（右侧倾斜红色爆炸贴纸）
    sticker_w, sticker_h = 240, 64
    st_x, st_y = W - sticker_w - 40, tape_y + tape_h + 105
    st_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    std = ImageDraw.Draw(st_layer)
    std.rounded_rectangle([st_x, st_y, st_x + sticker_w, st_y + sticker_h], radius=16, fill=(255, 45, 85, 245), outline=(255, 255, 255, 255), width=3)
    f_st = load_font(32, font_path)
    std.text((st_x + 22, st_y + 12), sticker_text, font=f_st, fill=(255, 255, 255, 255))
    canvas.paste(st_layer, (0, 0), st_layer)

    # 6. 大幅角色情绪立绘（占据下半部 60%，带来视觉生命力）
    if char_path and Path(char_path).exists():
        char = Image.open(char_path).convert("RGBA")
        target_h = 820
        target_w = int(char.width * (target_h / char.height))
        char = char.resize((target_w, target_h), Image.LANCZOS)
        
        # 人物白色发光描边/光晕 + 立体深阴影
        char_x = (W - target_w) // 2 + 30
        char_y = H - target_h - 20
        add_drop_shadow(canvas, char, offset=(char_x + 8, char_y + 16), blur=24, opacity=160, shadow_color=(0, 0, 0))
        canvas.paste(char, (char_x, char_y), char)

    # 7. 挂载关键道具（左侧放大悬浮）
    if prop_path and Path(prop_path).exists():
        prop = Image.open(prop_path).convert("RGBA")
        pw = 280
        ph = int(prop.height * (pw / prop.width))
        prop = prop.resize((pw, ph), Image.LANCZOS)
        add_drop_shadow(canvas, prop, offset=(45, H - ph - 160), blur=20, opacity=180)
        canvas.paste(prop, (45, H - ph - 160), prop)

    # 8. 底部热门标签（#野原经济学 #打工人必看）
    if tags:
        f_tag = load_font(26, font_path)
        tag_str = "  ".join(f"#{t.strip('#')}" for t in tags.split())
        draw.text((50, H - 65), tag_str, font=f_tag, fill=(255, 220, 100, 230))

    final = canvas.convert("RGB")
    if output:
        out_path = Path(output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        final.save(out_path, "JPEG", quality=96)
        print(f"[ok] 2.1 爆款高点击率封面已生成: {out_path}")
    return final

def main():
    parser = argparse.ArgumentParser(description="2.1 爆款短视频封面生成器")
    parser.add_argument("--project", required=True, help="视频项目路径 (如 02_项目/C002_超市涨价)")
    parser.add_argument("--title", help="封面大标题")
    parser.add_argument("--subtitle", help="封面副标题/痛点提问")
    parser.add_argument("--tags", help="标签 (空格分隔)")
    parser.add_argument("--character", help="指定角色图片路径")
    parser.add_argument("--background", help="指定背景图片路径")
    parser.add_argument("--prop", help="指定道具图片路径")
    parser.add_argument("--sticker", default="[ 揭秘真相 ]", help="悬念标签文字")
    parser.add_argument("--output", help="输出文件路径")
    args = parser.parse_args()

    project = Path(args.project)
    scene_config_path = project / "data" / "scene-config.json"
    
    title = args.title
    subtitle = args.subtitle or "生活里的套路到底有多深？"
    vid = "C000"

    if scene_config_path.exists():
        sc = json.loads(scene_config_path.read_text(encoding="utf-8"))
        title = title or sc.get("title", "野原经济学")
        vid = sc.get("videoId", "C000")

    # 自动定位素材
    char_path = args.character or (ROOT / "shared/characters/char_小新_explaining.png")
    bg_path = args.background or (ROOT / "shared/backgrounds/bg_market.png")
    prop_path = args.prop or (ROOT / "shared/props/prop_巧克比.png")

    out_file = args.output or (project / "deliverables" / f"{vid}_爆款封面.jpg")

    build_viral_cover(
        bg_path=str(bg_path) if Path(bg_path).exists() else None,
        char_path=str(char_path) if Path(char_path).exists() else None,
        prop_path=str(prop_path) if Path(prop_path).exists() else None,
        title=title,
        subtitle=subtitle,
        tags=args.tags or "野原经济学 生活常识 避坑指南",
        sticker_text=args.sticker,
        output=str(out_file)
    )

if __name__ == "__main__":
    main()
