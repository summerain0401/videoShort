#!/usr/bin/env python3
"""
project-review-gate.py - project-level human review gate.

The file qa/review.json is intentionally human-authored. This checker never
marks a project approved automatically.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DEFAULT_REVIEW = {
    "scriptApproved": False,
    "materialsApproved": False,
    "reviewer": "",
    "reviewedAt": "",
    "notes": "",
}


def review_path(project: Path) -> Path:
    return project / "qa" / "review.json"


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def load_review(project: Path) -> dict:
    path = review_path(project)
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"_error": f"review.json 格式错误: {exc}"}
    return data if isinstance(data, dict) else {"_error": "review.json 必须是 JSON 对象"}


def init_review(project: Path) -> Path:
    path = review_path(project)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(json.dumps(DEFAULT_REVIEW, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def check(project: Path) -> tuple[bool, list[str]]:
    review = load_review(project)
    missing = []
    if review.get("_error"):
        return False, [review["_error"]]
    if review.get("scriptApproved") is not True:
        missing.append("scriptApproved=true")
    if review.get("materialsApproved") is not True:
        missing.append("materialsApproved=true")
    return not missing, missing


def main() -> int:
    ap = argparse.ArgumentParser(description="检查项目是否完成剧本和素材人工审核")
    ap.add_argument("project", help="项目目录，例如 02_项目/C010_新选题")
    ap.add_argument("--init", action="store_true", help="创建未批准的 qa/review.json 模板")
    args = ap.parse_args()

    project = Path(args.project)
    if not project.is_absolute():
        project = ROOT / project
    if not project.is_dir():
        print(f"项目目录不存在: {project}", file=sys.stderr)
        return 2

    if args.init:
        path = init_review(project)
        print(f"审核文件已准备: {display_path(path)}")
        print("请人工检查剧本和素材后，将 scriptApproved/materialsApproved 改为 true。")
        return 0

    ready, missing = check(project)
    if ready:
        print(f"[review] {project.name}: 剧本与素材人工审核均已通过")
        return 0
    print(f"[review] {project.name}: 未通过人工审核", file=sys.stderr)
    print(f"  缺少: {', '.join(missing)}", file=sys.stderr)
    print(f"  文件: {display_path(review_path(project))}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
