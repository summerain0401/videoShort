#!/usr/bin/env python3
"""
处理 AI 生成素材：rembg 抠图 + 裁切右下角/底部水印 + 入库
用法:
  scripts/process-generated-assets.py
"""
import io
import json
import os
from pathlib import Path

from PIL import Image
from rembg import remove

ROOT = Path(__file__).resolve().parent.parent
SHARED = ROOT / "shared"
GENERATE = SHARED / "_generate"
LIB_PATH = SHARED / "material-library.json"

# 源文件 → (目标目录, 文件名, 名称, 类型, 情绪, 描述)
ASSETS = [
    ("char_小明_thinking_raw.png", "characters", "char_小明_thinking.png", "小明", "character", "thinking", "思考表情"),
    ("char_小明_explaining_raw.png", "characters", "char_小明_explaining.png", "小明", "character", "explaining", "讲解手势表情"),
    ("char_小明_serious_raw.png", "characters", "char_小明_serious.png", "小明", "character", "serious", "严肃表情"),
    ("char_小明_worried_raw.png", "characters", "char_小明_worried.png", "小明", "character", "worried", "担忧表情"),
    ("Cute_healing_cartoon_style_pro_2026-08-18T02-24-43.png", "props", "prop_零食袋.png", "零食袋", "prop", None, "一大袋零食，糖果饼干薯片"),
    ("Cute_healing_cartoon_style_gam_2026-08-18T02-27-57.png", "props", "prop_饮料瓶.png", "饮料瓶", "prop", None, "一瓶饮料"),
]


def remove_watermark_area(img: Image.Image) -> Image.Image:
    """裁掉底部约 8% 区域以去除右下角水印，同时保持主体完整。"""
    w, h = img.size
    crop_h = max(40, int(h * 0.08))
    return img.crop((0, 0, w, h - crop_h))


def process_image(src: Path, dst: Path) -> None:
    with open(src, "rb") as f:
        data = f.read()
    no_bg = remove(data)
    img = Image.open(io.BytesIO(no_bg)).convert("RGBA")
    img = remove_watermark_area(img)
    # 清理边缘：去除完全透明的边框
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)
    dst.parent.mkdir(parents=True, exist_ok=True)
    img.save(dst, "PNG")
    print(f"  {src.name} -> {dst.relative_to(ROOT)}")


def update_library():
    lib = json.loads(LIB_PATH.read_text(encoding="utf-8"))

    # 保留现有 active 微笑角色，新增变体
    existing_char_ids = {i["id"] for i in lib["characters"]}
    for raw, folder, filename, name, kind, emotion, desc in ASSETS:
        if kind != "character":
            continue
        file_path = f"shared/{folder}/{filename}"
        item_id = f"char_小明_{emotion}"
        if item_id in existing_char_ids:
            # 更新路径
            for item in lib["characters"]:
                if item["id"] == item_id:
                    item["filePath"] = file_path
                    item["status"] = "active"
                    item["lastUpdated"] = "2026-08-18"
        else:
            lib["characters"].append({
                "id": item_id,
                "type": "character",
                "name": name,
                "emotion": emotion,
                "action": "standing",
                "filePath": file_path,
                "status": "active",
                "contentDescription": f"治愈系卡通Q版小男孩，橙色T恤+蓝色背带裤，{desc}",
                "tags": ["角色", "小明", "治愈卡通", "Q版"],
                "createdAt": "2026-08-18",
                "usageCount": 0,
            })

    existing_prop_ids = {i["id"] for i in lib["props"]}
    for raw, folder, filename, name, kind, emotion, desc in ASSETS:
        if kind != "prop":
            continue
        file_path = f"shared/{folder}/{filename}"
        item_id = f"prop_{name}"
        if item_id in existing_prop_ids:
            for item in lib["props"]:
                if item["id"] == item_id:
                    item["filePath"] = file_path
                    item["status"] = "active"
                    item["lastUpdated"] = "2026-08-18"
        else:
            lib["props"].append({
                "id": item_id,
                "type": "prop",
                "name": name,
                "emotion": None,
                "action": None,
                "filePath": file_path,
                "status": "active",
                "contentDescription": f"治愈系卡通{name}道具，{desc}",
                "tags": ["道具", name, "治愈卡通"],
                "createdAt": "2026-08-18",
                "usageCount": 0,
            })

    lib["lastUpdated"] = "2026-08-18"
    LIB_PATH.write_text(json.dumps(lib, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[ok] 已更新 {LIB_PATH.relative_to(ROOT)}")


def main():
    print("[process] 开始处理生成素材...")
    for raw, folder, filename, *_ in ASSETS:
        src = GENERATE / raw
        dst = SHARED / folder / filename
        if not src.exists():
            print(f"  [skip] 源文件不存在: {raw}")
            continue
        process_image(src, dst)
    update_library()


if __name__ == "__main__":
    main()
