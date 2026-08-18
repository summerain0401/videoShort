#!/usr/bin/env python3
"""
semantic-check.py — 语义对齐检查脚本
逐句对照口播与画面素材描述，检查「嘴里说的」和「画面放的」是否一致。

用法:
    python scripts/semantic-check.py <project_dir>

输入:
    <project_dir>/data/timeline.json       # 时间轴（含每句口播）
    <project_dir>/data/scene-config.json   # 场景配置（含素材引用）

输出:
    <project_dir>/qa/semantic-alignment-report.json
"""
import argparse
import json
import sys
from pathlib import Path

# 常见关键对象检查：口播提到概念词时，画面需要对应的关键道具
CONCEPT_PROP_MAP = {
    "钱": ["钱袋", "钞票", "金币"],
    "账本": ["账本", "账册"],
    "合同": ["合同", "协议"],
    "股票": ["股票", "K线", "证券"],
    "餐厅": ["餐厅", "桌子", "吧台"],
    "珍珠": ["珍珠", "贝壳"],
}


def check_scene(scene: dict) -> dict:
    narration = scene["subtitle"]["text"]
    issues = []

    # 1. 关键概念 vs 道具
    for concept, expected_props in CONCEPT_PROP_MAP.items():
        if concept in narration:
            props_in_scene = [e["name"] for e in scene.get("elements", []) if e["type"] == "prop"]
            matched = [p for p in expected_props if p in " ".join(props_in_scene)]
            if not matched:
                issues.append({
                    "level": "warning",
                    "type": "missing_prop",
                    "message": f"口播提到「{concept}」，但场景中没有对应道具（{expected_props}）",
                })

    # 2. 角色与口播主体
    characters = [e["name"] for e in scene.get("elements", []) if e["type"] == "character"]
    if not characters and narration:
        issues.append({
            "level": "warning",
            "type": "no_character",
            "message": "口播存在但没有角色出现在画面中",
        })

    return {
        "sceneId": scene["sceneId"],
        "narration": narration,
        "characters": characters,
        "props": [e["name"] for e in scene.get("elements", []) if e["type"] == "prop"],
        "issues": issues,
        "pass": len([i for i in issues if i["level"] == "error"]) == 0,
    }


def main():
    parser = argparse.ArgumentParser(description="语义对齐检查")
    parser.add_argument("project_dir", help="单条视频的项目目录")
    args = parser.parse_args()

    project = Path(args.project_dir)
    timeline_path = project / "data" / "timeline.json"
    if not timeline_path.exists():
        print(f"[error] 缺少 timeline.json: {timeline_path}", file=sys.stderr)
        sys.exit(1)

    timeline = json.loads(timeline_path.read_text(encoding="utf-8"))
    report = {
        "videoId": timeline["videoId"],
        "title": timeline["title"],
        "scenes": [check_scene(s) for s in timeline["scenes"]],
    }
    report["warnings"] = sum(len(s["issues"]) for s in report["scenes"])

    out_dir = project / "qa"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "semantic-alignment-report.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[ok] 语义检查报告: {out_path}")
    print(f"[info] {len(report['scenes'])} 个场景, {report['warnings']} 条告警")
    if report["warnings"]:
        for scene in report["scenes"]:
            for issue in scene["issues"]:
                print(f"  [warn] {scene['sceneId']}: {issue['message']}")


if __name__ == "__main__":
    main()
