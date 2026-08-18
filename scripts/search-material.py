#!/usr/bin/env python3
"""
search-material.py — 素材库检索脚本
在 material-library.json 中按标签/类型/名称检索可用素材（status=active）。

用法:
    python scripts/search-material.py "蟹老板" --type character --emotion happy

输出:
    JSON 格式的匹配素材列表（stdout）
"""
import argparse
import json
import sys
from pathlib import Path

SHARED_LIB = Path(__file__).resolve().parent.parent / "shared" / "material-library.json"


def search(query: str, type_: str = None, emotion: str = None, tags: list = None,
           lib_path: Path = SHARED_LIB) -> list:
    if not lib_path.exists():
        print(f"[error] 素材库不存在: {lib_path}", file=sys.stderr)
        return []

    lib = json.loads(lib_path.read_text(encoding="utf-8"))
    results = []

    for category in ("characters", "backgrounds", "props"):
        for item in lib.get(category, []):
            if item.get("status") != "active":
                continue
            if type_ and item.get("type") != type_:
                continue
            if emotion and item.get("emotion") != emotion:
                continue

            # 名称 / 描述 / 标签 匹配
            haystack = " ".join([
                item.get("name", ""),
                item.get("contentDescription", ""),
                item.get("action", ""),
                " ".join(item.get("tags", [])),
            ])
            if query and query not in haystack:
                continue
            if tags:
                item_tags = set(item.get("tags", []))
                if not item_tags.issuperset(tags):
                    continue

            results.append(item)

    return results


def main():
    parser = argparse.ArgumentParser(description="素材库检索")
    parser.add_argument("query", nargs="?", default="", help="检索关键词（名称/描述/标签）")
    parser.add_argument("--type", choices=["character", "background", "prop"], help="素材类型")
    parser.add_argument("--emotion", help="角色情绪（如 happy/nervous）")
    parser.add_argument("--tag", action="append", help="标签过滤（可多次指定）")
    args = parser.parse_args()

    results = search(args.query, args.type, args.emotion, args.tag)
    print(json.dumps(results, ensure_ascii=False, indent=2))
    print(f"\n[info] 找到 {len(results)} 条可用素材", file=sys.stderr)


if __name__ == "__main__":
    main()
