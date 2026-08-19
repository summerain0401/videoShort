#!/usr/bin/env python3
"""
material-register.py - register a human-reviewed generated material as active.

Registration is explicit and requires --approve. The source file must live in
shared/_generate/ or already be in the target shared asset directory.
"""
import argparse
import json
import shutil
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIBRARY = ROOT / "shared" / "material-library.json"


def load_library() -> dict:
    return json.loads(LIBRARY.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description="将人工审核通过的生成素材登记为 active")
    ap.add_argument("--source", required=True, help="素材文件路径")
    ap.add_argument("--id", required=True, help="唯一素材 ID")
    ap.add_argument("--type", required=True, choices=["background", "character", "prop"])
    ap.add_argument("--name", required=True, help="素材名称")
    ap.add_argument("--description", required=True, help="素材内容描述")
    ap.add_argument("--tags", default="", help="空格分隔标签")
    ap.add_argument("--emotion", default="", help="角色情绪，可选")
    ap.add_argument("--approve", action="store_true", help="确认已完成人工检查")
    args = ap.parse_args()

    if not args.approve:
        print("必须显式提供 --approve，素材不会自动进入 active。", file=sys.stderr)
        return 2

    source = Path(args.source)
    if not source.is_absolute():
        source = ROOT / source
    if not source.exists():
        print(f"素材文件不存在: {source}", file=sys.stderr)
        return 2
    try:
        source.relative_to(ROOT / "shared")
    except ValueError:
        print("为避免误登记，素材必须位于 shared/ 目录内。", file=sys.stderr)
        return 2

    library = load_library()
    all_items = [item for key in ("characters", "backgrounds", "props") for item in library.get(key, [])]
    if any(item.get("id") == args.id for item in all_items):
        print(f"素材 ID 已存在: {args.id}", file=sys.stderr)
        return 2

    category = {"character": "characters", "background": "backgrounds", "prop": "props"}[args.type]
    target_dir = ROOT / "shared" / {"character": "characters", "background": "backgrounds", "prop": "props"}[args.type]
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / source.name
    if source.resolve() != target.resolve():
        shutil.copy2(source, target)

    item = {
        "id": args.id,
        "type": args.type,
        "name": args.name,
        "emotion": args.emotion or None,
        "action": None,
        "filePath": str(target.relative_to(ROOT)),
        "status": "active",
        "contentDescription": args.description,
        "tags": [x for x in args.tags.split() if x],
        "createdAt": date.today().isoformat(),
        "usageCount": 0,
    }
    library.setdefault(category, []).append(item)
    library["lastUpdated"] = date.today().isoformat()
    LIBRARY.write_text(json.dumps(library, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"已登记 active 素材: {item['filePath']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
