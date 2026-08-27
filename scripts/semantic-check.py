#!/usr/bin/env python3
"""
semantic-check.py — 语义对齐检查脚本
逐句对照口播与画面素材描述，检查「嘴里说的」和「画面放的」是否一致。
支持规则基础检查，以及调用 LLMRouter (TaskTier.ROUTINE_EXECUTION -> Gemini 3.7 Flash) 进行智能语义校对。

用法:
    python scripts/semantic-check.py <project_dir> [--llm]
"""
import argparse
import json
import sys
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from shared.llm_router import router, TaskTier

# 常见关键对象检查：口播提到概念词时，画面需要对应的关键道具
CONCEPT_PROP_MAP = {
    "钱": ["钱袋", "钞票", "金币"],
    "账本": ["账本", "账册"],
    "合同": ["合同", "协议"],
    "股票": ["股票", "K线", "证券"],
    "餐厅": ["餐厅", "桌子", "吧台"],
    "珍珠": ["珍珠", "贝壳"],
    "巧克比": ["巧克比", "零食"],
    "工资": ["工资条", "钱袋"],
    "半价": ["第二件半价牌", "巧克比"],
}

def check_scene(scene: dict) -> dict:
    narration = scene.get("subtitle", {}).get("text", "") or scene.get("narrationSegment", "")
    issues = []

    # 1. 关键概念 vs 道具
    for concept, expected_props in CONCEPT_PROP_MAP.items():
        if concept in narration:
            props_in_scene = [e["name"] for e in scene.get("elements", []) if e.get("type") == "prop"]
            matched = [p for p in expected_props if p in " ".join(props_in_scene)]
            if not matched:
                issues.append({
                    "level": "warning",
                    "type": "missing_prop",
                    "message": f"口播提到「{concept}」，但场景中没有对应道具（{expected_props}）",
                })

    # 2. 角色与口播主体
    characters = [e["name"] for e in scene.get("elements", []) if e.get("type") == "character"]
    if not characters and narration:
        issues.append({
            "level": "warning",
            "type": "no_character",
            "message": "口播存在但没有角色出现在画面中",
        })

    return {
        "sceneId": scene.get("sceneId", "S00"),
        "narration": narration,
        "characters": characters,
        "props": [e["name"] for e in scene.get("elements", []) if e.get("type") == "prop"],
        "issues": issues,
        "pass": len([i for i in issues if i["level"] == "error"]) == 0,
    }

def check_with_llm(scenes_summary: list) -> list:
    """使用极速执行模型 (Gemini 3.7 Flash) 进行画面与口播语义冲突审核"""
    try:
        cfg = router.get_provider_config(TaskTier.ROUTINE_EXECUTION)
        if cfg.get("provider") == "none":
            return []
        
        prompt = f"""
请作为短视频质检员，快速检查以下各分镜的「口播文案」与「背景/角色/道具」是否存在严重语义违和或矛盾。
场景数据：
{json.dumps(scenes_summary, ensure_ascii=False, indent=2)}

若有明显违和，返回 JSON 数组；若无问题返回空数组 []。格式：
[
  {{"sceneId": "S01", "level": "warning", "message": "违和原因"}}
]
"""
        resp = router.call(
            prompt,
            system_prompt="你是一个高效率短视频 QA 审核助手，只输出合法 JSON 数组。",
            tier=TaskTier.ROUTINE_EXECUTION,
            json_mode=True
        )
        clean_resp = re.sub(r"^```json\s*|\s*```$", "", resp.strip(), flags=re.MULTILINE)
        return json.loads(clean_resp)
    except Exception as e:
        print(f"[info] LLM 语义检查略过 ({e})")
        return []

def main():
    parser = argparse.ArgumentParser(description="语义对齐检查")
    parser.add_argument("project_dir", help="单条视频的项目目录")
    parser.add_argument("--llm", action="store_true", help="启用 Gemini 3.7 Flash 智能语义质检")
    args = parser.parse_args()

    project = Path(args.project_dir)
    timeline_path = project / "data" / "timeline.json"
    scene_config_path = project / "data" / "scene-config.json"
    
    if timeline_path.exists():
        data_source = json.loads(timeline_path.read_text(encoding="utf-8"))
        scenes = data_source.get("scenes", [])
        title = data_source.get("title", "")
        vid = data_source.get("videoId", "")
    elif scene_config_path.exists():
        data_source = json.loads(scene_config_path.read_text(encoding="utf-8"))
        scenes = data_source.get("scenes", [])
        title = data_source.get("title", "")
        vid = data_source.get("videoId", "")
    else:
        print(f"[error] 缺少 timeline.json 或 scene-config.json: {project / 'data'}", file=sys.stderr)
        sys.exit(1)

    scene_reports = [check_scene(s) for s in scenes]

    if args.llm:
        print("[info] 正在调用 Gemini 3.7 Flash 进行智能语义校对...")
        llm_issues = check_with_llm([{
            "sceneId": s.get("sceneId"),
            "narration": s.get("subtitle", {}).get("text", "") or s.get("narrationSegment", ""),
            "background": s.get("background", ""),
            "elements": [e.get("name") for e in s.get("elements", [])]
        } for s in scenes])
        
        for issue in llm_issues:
            target = next((r for r in scene_reports if r["sceneId"] == issue.get("sceneId")), None)
            if target:
                target["issues"].append({
                    "level": issue.get("level", "warning"),
                    "type": "llm_check",
                    "message": issue.get("message", "")
                })

    report = {
        "videoId": vid,
        "title": title,
        "scenes": scene_reports,
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
