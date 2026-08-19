#!/usr/bin/env python3
"""
封面模板生成器
===============
基于项目 scene-config.json 与素材库，自动生成 1080×1440 3:4 竖版封面。

用法：
  python scripts/generate-cover.py --project 02_项目/C003_工资与物价
  python scripts/generate-cover.py --project 02_项目/C003_工资与物价 \
      --title "工资" --subtitle "为什么总涨不过物价？" \
      --tags "经济学 生活常识 看懂购买力" \
      --layout split --character serious --background 超市内部

输出：
  <project>/deliverables/<videoId>_封面.jpg

版式：
  - split（默认）：角色完整站在右侧，左侧标题卡片，适合突出 IP
  - center：角色底部居中半身，底部大标题，适合信息流强标题
"""
import argparse
import json
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
MATERIAL_LIBRARY = ROOT / "shared/material-library.json"
DEFAULT_FONT = "/System/Library/Fonts/STHeiti Medium.ttc"

LAYOUTS = ["split", "center"]


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def find_font():
    candidates = [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
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


def find_assets(assets, type_=None, name=None, emotion=None, limit=1):
    """按类型/名称/情绪模糊匹配素材"""
    results = []
    for a in assets:
        if a.get("status") != "active":
            continue
        if type_ and a.get("type") != type_:
            continue
        hay = " ".join(
            str(x).lower()
            for x in [a.get("name", ""), a.get("emotion", ""), a.get("contentDescription", ""), " ".join(a.get("tags", []))]
        )
        score = 0
        if name and name.lower() in hay:
            score += 10
            if a.get("name", "").lower() == name.lower():
                score += 10
        if emotion and emotion.lower() in hay:
            score += 8
            if a.get("emotion", "").lower() == emotion.lower():
                score += 8
        if score > 0:
            results.append((score, a))
    results.sort(key=lambda x: -x[0])
    return [a for _, a in results[:limit]]


def resolve_asset_path(asset):
    return ROOT / asset["filePath"]


def add_drop_shadow(canvas, img, offset=(8, 8), blur=8, opacity=80):
    alpha = img.split()[-1]
    shadow = Image.new("RGBA", img.size, (60, 50, 40, 0))
    mask = alpha.point(lambda a: min(a, opacity))
    shadow.putalpha(mask)
    shadow = shadow.filter(ImageFilter.GaussianBlur(blur))
    ox, oy = offset
    canvas.paste(shadow, (ox, oy), shadow)


def draw_brand_bar(canvas, brand, slogan, font_path=None):
    W = canvas.width
    brand_h = 78
    brand_y = 50
    brand_pad = 36
    brand_w = W - brand_pad * 2
    layer = Image.new("RGBA", (W, brand_h), (0, 0, 0, 0))
    bd = ImageDraw.Draw(layer)
    bd.rounded_rectangle((brand_pad, 0, brand_pad + brand_w, brand_h), radius=40, fill=(255, 255, 255, 225))
    bd.ellipse((brand_pad + 16, brand_h // 2 - 26, brand_pad + 16 + 52, brand_h // 2 + 26), fill=(255, 200, 120, 255))
    f_title = load_font(30, font_path)
    f_slogan = load_font(18, font_path)
    bd.text((brand_pad + 78, 14), brand, font=f_title, fill=(80, 55, 40, 255))
    bd.text((brand_pad + 80, 48), slogan, font=f_slogan, fill=(120, 100, 90, 255))
    canvas.paste(layer, (0, brand_y), layer)


def build_split_cover(
    bg_path,
    char_path,
    prop_path,
    title,
    subtitle,
    tags,
    brand,
    slogan,
    font_path=None,
    output=None,
):
    W, H = 1080, 1440
    canvas = Image.new("RGBA", (W, H), (255, 255, 255, 255))

    # 背景
    bg = Image.open(bg_path).convert("RGBA").resize((W, H), Image.LANCZOS)
    overlay = Image.new("RGBA", (W, H), (255, 255, 255, 0))
    d = ImageDraw.Draw(overlay)
    for i in range(200):
        alpha = int(90 * (1 - i / 200))
        d.line([(0, i), (W, i)], fill=(255, 248, 235, alpha))
    canvas.paste(Image.alpha_composite(bg, overlay), (0, 0))

    draw_brand_bar(canvas, brand, slogan, font_path)

    # 道具
    if prop_path:
        prop = Image.open(prop_path).convert("RGBA")
        prop = prop.resize((240, int(prop.height * 240 / prop.width)), Image.LANCZOS)
        add_drop_shadow(canvas, prop, offset=(10, 14), blur=12)
        canvas.paste(prop, (W - 300, 320), prop)

    # 角色
    char = Image.open(char_path).convert("RGBA")
    char = char.resize((600, int(char.height * 600 / char.width)), Image.LANCZOS)
    add_drop_shadow(canvas, char, offset=(12, 16), blur=14)
    canvas.paste(char, (W // 2 - 60, H - 760), char)

    # 左侧标题卡片
    title_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    td = ImageDraw.Draw(title_layer)
    card_x, card_y, card_w, card_h = 56, 340, 520, 400
    # 卡片阴影
    shadow = Image.new("RGBA", (card_w + 28, card_h + 28), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle((8, 8, card_w + 20, card_h + 20), radius=36, fill=(50, 40, 35, 75))
    shadow = shadow.filter(ImageFilter.GaussianBlur(12))
    title_layer.paste(shadow, (card_x - 8, card_y - 8), shadow)
    td.rounded_rectangle((card_x, card_y, card_x + card_w, card_y + card_h), radius=30, fill=(255, 252, 245, 230))
    canvas = Image.alpha_composite(canvas, title_layer)

    draw = ImageDraw.Draw(canvas)
    f_kw = load_font(100, font_path)
    f_sub = load_font(46, font_path)
    f_tag = load_font(24, font_path)

    draw.text((card_x + 44, card_y + 44), title, font=f_kw, fill=(80, 50, 30, 255))

    # 副标题自动换行
    lines = []
    words = list(subtitle)
    buf = ""
    for w in words:
        test = buf + w
        bbox = draw.textbbox((0, 0), test, font=f_sub)
        if (bbox[2] - bbox[0]) > card_w - 80 and buf:
            lines.append(buf)
            buf = w
        else:
            buf = test
    lines.append(buf)
    # 避免最后一行只剩标点
    if len(lines) > 1 and len(lines[-1]) <= 2 and not any(c.isalnum() for c in lines[-1]):
        lines[-2] += lines[-1]
        lines.pop()
    y = card_y + 170
    for line in lines:
        draw.text((card_x + 44, y), line, font=f_sub, fill=(70, 65, 85, 255))
        y += 64

    if tags:
        tag_text = " ".join(f"#{t}" for t in tags.split())
        bbox = draw.textbbox((0, 0), tag_text, font=f_tag)
        tag_w = bbox[2] - bbox[0]
        tag_h = 46
        tag_y = card_y + card_h - 84
        draw.rounded_rectangle((card_x + 44, tag_y, card_x + 44 + tag_w + 28, tag_y + tag_h), radius=23, fill=(255, 200, 120, 235))
        draw.text((card_x + 58, tag_y + 8), tag_text, font=f_tag, fill=(80, 50, 30, 255))

    final = canvas.convert("RGB")
    if output:
        final.save(output, "JPEG", quality=95)
        print(f"Saved: {output}")
    return final


def build_center_cover(
    bg_path,
    char_path,
    prop_path,
    title,
    subtitle,
    tags,
    brand,
    slogan,
    font_path=None,
    output=None,
):
    W, H = 1080, 1440
    canvas = Image.new("RGBA", (W, H), (255, 255, 255, 255))

    bg = Image.open(bg_path).convert("RGBA").resize((W, H), Image.LANCZOS)
    overlay = Image.new("RGBA", (W, H), (255, 255, 255, 0))
    d = ImageDraw.Draw(overlay)
    for i in range(220):
        alpha = int(60 * (1 - i / 220))
        d.line([(0, i), (W, i)], fill=(255, 248, 235, alpha))
    canvas.paste(Image.alpha_composite(bg, overlay), (0, 0))

    draw_brand_bar(canvas, brand, slogan, font_path)

    if prop_path:
        prop = Image.open(prop_path).convert("RGBA")
        prop = prop.resize((240, int(prop.height * 240 / prop.width)), Image.LANCZOS)
        add_drop_shadow(canvas, prop, offset=(10, 14), blur=12)
        canvas.paste(prop, (W - 280, 280), prop)

    card_h = 720
    card_y = H - card_h
    card = Image.new("RGBA", (W, card_h), (0, 0, 0, 0))
    cd = ImageDraw.Draw(card)
    for i in range(card_h):
        alpha = int(205 * (i / card_h))
        cd.line([(0, card_h - 1 - i), (W, card_h - 1 - i)], fill=(45, 40, 60, alpha))
    canvas.paste(card, (0, card_y), card)

    char = Image.open(char_path).convert("RGBA")
    char = char.resize((560, int(char.height * 560 / char.width)), Image.LANCZOS)
    add_drop_shadow(canvas, char, offset=(12, 16), blur=14)
    canvas.paste(char, (W // 2 - 280, H - 360), char)

    draw = ImageDraw.Draw(canvas)
    f_kw = load_font(108, font_path)
    f_sub = load_font(50, font_path)
    f_tag = load_font(26, font_path)

    bbox = draw.textbbox((0, 0), title, font=f_kw)
    kw_w = bbox[2] - bbox[0]
    kw_x = (W - kw_w) // 2
    kw_y = card_y + 90
    draw.text((kw_x + 3, kw_y + 3), title, font=f_kw, fill=(0, 0, 0, 120))
    draw.text((kw_x, kw_y), title, font=f_kw, fill=(255, 225, 110, 255))

    bbox = draw.textbbox((0, 0), subtitle, font=f_sub)
    sub_w = bbox[2] - bbox[0]
    draw.text(((W - sub_w) // 2, card_y + 235), subtitle, font=f_sub, fill=(255, 255, 255, 255))

    if tags:
        tag_text = " ".join(f"#{t}" for t in tags.split())
        bbox = draw.textbbox((0, 0), tag_text, font=f_tag)
        tag_w = bbox[2] - bbox[0]
        tag_pad = 18
        tag_h = 50
        tag_x = (W - tag_w) // 2
        tag_y = card_y + 350
        draw.rounded_rectangle((tag_x - tag_pad, tag_y, tag_x + tag_w + tag_pad, tag_y + tag_h), radius=25, fill=(255, 200, 120, 235))
        draw.text((tag_x + 1, tag_y + 10), tag_text, font=f_tag, fill=(80, 50, 30, 255))

    final = canvas.convert("RGB")
    if output:
        final.save(output, "JPEG", quality=95)
        print(f"Saved: {output}")
    return final


def split_title(title):
    """把长标题拆成短主标题 + 可读副标题，避免主标题在卡片内溢出。"""
    title = title.strip()
    if title.startswith("为什么") and len(title) > 4:
        keyword = title[3:5]
        rest = "为什么" + title[5:]
        if not rest.endswith(("？", "?", "。", ".")):
            rest += "？"
        return keyword, rest
    if "第二件半价" in title:
        return "半价", "第二件真的省钱吗？"
    if len(title) > 6:
        keyword = title[:3]
        rest = title[3:]
        if not rest.endswith(("？", "?", "。", ".")):
            rest += "？"
        return keyword, rest
    return title, ""


def main():
    parser = argparse.ArgumentParser(description="生成布丁经济学竖版封面")
    parser.add_argument("--project", required=True, help="项目目录，如 02_项目/C003_工资与物价")
    parser.add_argument("--title", default=None, help="主标题")
    parser.add_argument("--subtitle", default=None, help="副标题")
    parser.add_argument("--tags", default="经济学 生活常识", help="标签，空格分隔")
    parser.add_argument("--layout", choices=LAYOUTS, default="split", help="版式")
    parser.add_argument("--background", default=None, help="背景名称，如「小镇街道」「超市内部」")
    parser.add_argument("--character", default=None, help="角色情绪，如 thinking/serious/explaining")
    parser.add_argument("--props", default=None, help="道具名称，逗号分隔，最多取 1 个")
    parser.add_argument("--brand", default="布丁经济学", help="账号名")
    parser.add_argument("--slogan", default="用治愈的卡通，讲清生活的经济学", help="账号 slogan")
    parser.add_argument("--font", default=None, help="中文字体路径")
    parser.add_argument("--output", default=None, help="输出路径，默认 <project>/deliverables/<videoId>_封面.jpg")
    args = parser.parse_args()

    project_dir = ROOT / args.project
    if not project_dir.exists():
        sys.exit(f"项目目录不存在：{project_dir}")

    scene_config = load_json(project_dir / "data/scene-config.json")
    video_id = scene_config.get("videoId", project_dir.name)
    default_title = scene_config.get("title", "")

    title = args.title or default_title
    subtitle = args.subtitle or ""
    if not args.subtitle and not args.title and default_title:
        title, subtitle = split_title(default_title)

    tags = args.tags

    # 加载素材库（合并 characters/backgrounds/props）
    library = load_json(MATERIAL_LIBRARY)
    assets = []
    for section in ["characters", "backgrounds", "props"]:
        assets.extend(library.get(section, []))

    # 背景
    bg_name = args.background
    if not bg_name:
        # 从第一场景取背景名
        scenes = scene_config.get("scenes", [])
        if scenes:
            bg_name = scenes[0].get("background")
    bg_assets = find_assets(assets, type_="background", name=bg_name, limit=1)
    if not bg_assets:
        bg_assets = find_assets(assets, type_="background", limit=1)
    if not bg_assets:
        sys.exit("素材库中没有可用背景")
    bg_path = resolve_asset_path(bg_assets[0])

    # 角色情绪：封面优先使用讲解/正面识别度更高的姿态，除非用户显式指定。
    char_emotion = args.character
    if not char_emotion:
        char_emotion = "explaining"
    char_assets = find_assets(assets, type_="character", emotion=char_emotion, name="小布丁", limit=1)
    if not char_assets:
        char_assets = find_assets(assets, type_="character", emotion=char_emotion, limit=1)
    if not char_assets:
        char_assets = find_assets(assets, type_="character", name="小布丁", limit=1)
    if not char_assets:
        char_assets = find_assets(assets, type_="character", limit=1)
    char_path = resolve_asset_path(char_assets[0])

    # 道具
    prop_path = None
    prop_names = [p.strip() for p in (args.props or "").split(",") if p.strip()]
    if not prop_names:
        # 从场景配置取第一个道具
        scenes = scene_config.get("scenes", [])
        for s in scenes:
            for e in s.get("elements", []):
                if e.get("type") == "prop" and e.get("name"):
                    prop_names.append(e["name"])
                    break
            if prop_names:
                break
    if prop_names:
        prop_assets = find_assets(assets, type_="prop", name=prop_names[0], limit=1)
        if prop_assets:
            prop_path = resolve_asset_path(prop_assets[0])

    # 输出路径
    if args.output:
        output = ROOT / args.output
    else:
        output = project_dir / "deliverables" / f"{video_id}_封面.jpg"
    output.parent.mkdir(parents=True, exist_ok=True)

    # 生成
    if args.layout == "split":
        build_split_cover(
            bg_path=bg_path,
            char_path=char_path,
            prop_path=prop_path,
            title=title,
            subtitle=subtitle,
            tags=tags,
            brand=args.brand,
            slogan=args.slogan,
            font_path=args.font,
            output=output,
        )
    else:
        build_center_cover(
            bg_path=bg_path,
            char_path=char_path,
            prop_path=prop_path,
            title=title,
            subtitle=subtitle,
            tags=tags,
            brand=args.brand,
            slogan=args.slogan,
            font_path=args.font,
            output=output,
        )


if __name__ == "__main__":
    main()
