#!/usr/bin/env python3
"""
register-material.py — 素材登记脚本
将 _generate/ 中检查通过的素材移动到正式目录，并登记到 material-library.json。

用法:
    python scripts/register-material.py <source_file> --type character --name 蟹老板 --emotion happy --desc "描述" --tag 海洋 --tag 动画

说明:
    移动文件到 shared/{characters|backgrounds|props}/ 并登记索引。
    淘汰素材请移动到 shared/_retired/（手动或脚本均可），
    并在库中将对应项 status 改为 retired。
"""
import argparse
import json
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHARED = ROOT / "shared"
LIB_PATH = SHARED / "material-library.json"

TYPE_DIRS = {"character": "characters", "background": "backgrounds", "prop": "props"}


def register(source: Path, type_: str, name: str, desc: str, emotion: str = None,
             action: str = None, tags: list = None) -> dict:
    if type_ not in TYPE_DIRS:
        print(f"[error] 未知类型: {type_}", file=sys.stderr)
        sys.exit(1)
    if not source.exists():
        print(f"[error] 源文件不存在: {source}", file=sys.stderr)
        sys.exit(1)

    lib = json.loads(LIB_PATH.read_text(encoding="utf-8"))
    target_dir = SHARED / TYPE_DIRS[type_]
    target_dir.mkdir(parents=True, exist_ok=True)

    # 生成唯一 ID 和文件名
    stem = f"{type_[:4]}_{name}_{emotion or 'default'}_{int(time.time()) % 10000}"
    suffix = source.suffix.lower() or ".png"
    target = target_dir / f"{stem}{suffix}"

    # 避免覆盖
    counter = 1
    while target.exists():
        target = target_dir / f"{stem}_{counter}{suffix}"
        counter += 1

    shutil.move(str(source), str(target))

    item = {
        "id": stem,
        "type": type_,
        "name": name,
        "emotion": emotion,
        "action": action,
        "filePath": str(target.relative_to(ROOT)),
        "status": "active",
        "contentDescription": desc,
        "tags": tags or [],
        "createdAt": time.strftime("%Y-%m-%d"),
        "usageCount": 0,
    }

    category = TYPE_DIRS[type_]
    lib[category].append(item)
    lib["lastUpdated"] = time.strftime("%Y-%m-%d")
    LIB_PATH.write_text(json.dumps(lib, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[ok] 素材已登记: {target.relative_to(ROOT)}")
    print(f"[ok] ID: {item['id']}")
    return item


def main():
    parser = argparse.ArgumentParser(description="登记素材到共享库")
    parser.add_argument("source", help="素材源文件（通常位于 shared/_generate/）")
    parser.add_argument("--type", required=True, choices=["character", "background", "prop"])
    parser.add_argument("--name", required=True, help="角色/对象名")
    parser.add_argument("--desc", required=True, help="内容描述（检索依据）")
    parser.add_argument("--emotion", help="情绪（角色）")
    parser.add_argument("--action", help="动作描述")
    parser.add_argument("--tag", action="append", help="标签（可多次）")
    args = parser.parse_args()

    register(Path(args.source), args.type, args.name, args.desc,
             args.emotion, args.action, args.tag)


if __name__ == "__main__":
    main()
