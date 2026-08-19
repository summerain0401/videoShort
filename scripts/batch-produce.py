#!/usr/bin/env python3
"""
batch-produce.py — 批量生产编排脚本（阶段 3：批量生产新选题）

读取 batch-plan.json，对每个选题执行检查 / 配音 / 时间轴 / 渲染 / 检查。
支持选择性执行和全链路一键生产。

用法:
    # 列出批量计划中的所有选题及状态
    python scripts/batch-produce.py batch-plans/W001_第一周.json --list

    # 检查所有选题的脚本是否就绪
    python scripts/batch-produce.py batch-plans/W001_第一周.json --check

    # 全链路生产所有选题（配音→时间轴→渲染→检查）
    python scripts/batch-produce.py batch-plans/W001_第一周.json --all

    # 只生产指定选题
    python scripts/batch-produce.py batch-plans/W001_第一周.json --all --only C004

    # 只生成封面
    python scripts/batch-produce.py batch-plans/W001_第一周.json --cover

    # 自定义流水线步骤
    python scripts/batch-produce.py batch-plans/W001_第一周.json --steps voice,timeline,render,check,cover

环境变量:
    AZURE_SPEECH_KEY / AZURE_SPEECH_REGION  — Azure TTS（可选，无则用 edge）
    AZURE_VOICE                             — Azure 音色（可选）
"""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# 状态颜色（ANSI）
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
CYAN = "\033[36m"
BOLD = "\033[1m"
RESET = "\033[0m"

# Python 解释器（优先项目 .venv）
if (ROOT / ".venv" / "bin" / "python").exists():
    PY = str(ROOT / ".venv" / "bin" / "python")
else:
    PY = "python3"

# Node 解释器
NODE = os.environ.get("NODE_BIN", "node")


def info(msg):
    print(f"{CYAN}[batch]{RESET} {msg}")

def ok(msg):
    print(f"{GREEN}✓{RESET} {msg}")

def warn(msg):
    print(f"{YELLOW}⚠{RESET} {msg}")

def err(msg):
    print(f"{RED}✗{RESET} {msg}", file=sys.stderr)

def bold(msg):
    return f"{BOLD}{msg}{RESET}"


# ---------------------------------------------------------------- 加载

def load_plan(plan_path: str) -> dict:
    p = Path(plan_path)
    if not p.is_absolute():
        p = ROOT / p
    if not p.exists():
        err(f"批量计划文件不存在: {p}")
        sys.exit(1)
    return json.loads(p.read_text(encoding="utf-8"))


def load_env():
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


# ---------------------------------------------------------------- 状态检查

def ensure_material_gap(topic: dict) -> dict:
    """每次检查前扫描场景素材，只允许 active 素材通过。"""
    proj = topic["projectDir"]
    result = subprocess.run(
        [PY, "scripts/material-gap.py", proj, "--json"],
        cwd=str(ROOT), capture_output=True, text=True, timeout=120,
    )
    report_path = ROOT / proj / "qa" / "material-gap-report.json"
    if report_path.exists():
        return json.loads(report_path.read_text(encoding="utf-8"))
    return {"pass": False, "missingCount": "?", "error": result.stderr.strip() or "素材扫描失败"}


def check_topic_ready(topic: dict) -> tuple:
    """检查剧本文件和素材状态，返回 (ready, 缺失文件列表)。"""
    proj = ROOT / topic["projectDir"]
    required = [
        proj / "script" / "口播稿.txt",
        proj / "data" / "scene-config.json",
    ]
    missing = [str(f.relative_to(ROOT)) for f in required if not f.exists()]
    if not missing:
        gap = ensure_material_gap(topic)
        if not gap.get("pass", False):
            missing.append(f"素材缺口未清零: {gap.get('missingCount', '?')} 项")
    return (len(missing) == 0, missing)


def review_gate_ready(topic: dict) -> tuple:
    """人工审核闸门：计划字段和项目 qa/review.json 都必须明确批准。"""
    review = topic.get("review", {})
    project_review_path = ROOT / topic["projectDir"] / "qa" / "review.json"
    if project_review_path.exists():
        try:
            project_review = json.loads(project_review_path.read_text(encoding="utf-8"))
            review = {**review, **project_review}
        except json.JSONDecodeError:
            return False, ["qa/review.json 格式错误"]
    approved = review.get("scriptApproved") is True
    material_approved = review.get("materialsApproved") is True
    missing = []
    if not approved:
        missing.append("scriptApproved=true")
    if not material_approved:
        missing.append("materialsApproved=true")
    return approved and material_approved, missing


def get_status_emoji(topic: dict) -> str:
    status = topic.get("status", "planned")
    mapping = {
        "planned": "📋",
        "scripts_ready": "📝",
        "voiced": "🎙️",
        "rendered": "🎬",
        "delivered": "✅",
    }
    return mapping.get(status, "📋")


def list_topics(plan: dict):
    """列出批量计划中的所有选题"""
    print(f"\n{bold(f'批量计划: {plan["batchName"]}')}")
    print(f"  Batch ID: {plan['batchId']}  |  创建: {plan.get('createdAt', '-')}")
    print(f"  排期: {' / '.join(plan.get('schedule', []))}")
    print(f"  账号: {plan.get('account', '-')}  |  更新: {plan.get('cadence', 'daily')}  |  每批: {plan.get('batchSize', len(plan.get('topics', [])))} 条")
    print(f"\n  {'序号':<4} {'视频ID':<6} {'栏目':<12} {'标题':<20} {'状态':<14} {'审核':<12} {'就绪'}")
    print(f"  {'─'*4} {'─'*6} {'─'*12} {'─'*20} {'─'*14} {'─'*12} {'─'*6}")

    for i, topic in enumerate(plan["topics"], 1):
        ready, missing = check_topic_ready(topic)
        ready_str = f"{GREEN}✓{RESET}" if ready else f"{RED}✗{RESET}"
        status_display = f"{get_status_emoji(topic)} {topic.get('status', 'planned')}"
        review = topic.get("review", {})
        review_display = "已审核" if review.get("scriptApproved") and review.get("materialsApproved") else "待审核"
        print(f"  {i:<4} {topic['videoId']:<6} {topic.get('column',''):<12} "
              f"{topic['title']:<20} {status_display:<20} {review_display:<12} {ready_str}")
        if not ready:
            print(f"       {RED}缺失: {', '.join(missing)}{RESET}")
    print()


# ---------------------------------------------------------------- 执行步骤

def run_step(cmd: list, topic_id: str, step_name: str) -> bool:
    """执行一个步骤，返回是否成功"""
    info(f"[{topic_id}] {step_name}...")
    try:
        result = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            err(f"[{topic_id}] {step_name} 失败")
            if result.stderr:
                print(result.stderr[-500:], file=sys.stderr)
            return False
        if result.stdout:
            # 只打印最后几行
            lines = result.stdout.strip().splitlines()
            for line in lines[-3:]:
                print(f"  {line}")
        ok(f"[{topic_id}] {step_name} 完成")
        return True
    except subprocess.TimeoutExpired:
        err(f"[{topic_id}] {step_name} 超时（5 分钟）")
        return False
    except Exception as e:
        err(f"[{topic_id}] {step_name} 异常: {e}")
        return False


def step_voice(topic: dict, engine: str = "auto", voice: str = "") -> bool:
    proj = topic["projectDir"]
    script_file = f"{proj}/script/口播稿.txt"
    cmd = [PY, "scripts/tts.py", script_file, f"{proj}/audio", "--engine", engine]
    if voice:
        cmd += ["--voice", voice]
    return run_step(cmd, topic["videoId"], "配音")


def step_timeline(topic: dict) -> bool:
    proj = topic["projectDir"]
    cmd = [PY, "scripts/build-timeline.py", proj]
    return run_step(cmd, topic["videoId"], "时间轴")


def step_render(topic: dict) -> bool:
    proj = topic["projectDir"]
    cmd = [NODE, "scripts/render.mjs", proj]
    return run_step(cmd, topic["videoId"], "渲染")


def step_check(topic: dict) -> bool:
    proj = topic["projectDir"]
    deliverables = ROOT / proj / "deliverables"
    mp4_files = list(deliverables.glob("*.mp4"))
    if not mp4_files:
        err(f"[{topic['videoId']}] 未找到成片")
        return False
    return run_step([PY, "scripts/quality-check.py", proj], topic["videoId"], "统一质检")


def step_cover(topic: dict) -> bool:
    proj = topic["projectDir"]
    cmd = [PY, "scripts/generate-cover.py", "--project", proj]
    return run_step(cmd, topic["videoId"], "封面")


def step_preview(topic: dict) -> bool:
    proj = topic["projectDir"]
    cmd = [PY, "scripts/generate-preview.py", proj]
    return run_step(cmd, topic["videoId"], "预览图")


# ---------------------------------------------------------------- 主流程

STEP_MAP = {
    "voice": step_voice,
    "timeline": step_timeline,
    "preview": step_preview,
    "render": step_render,
    "check": step_check,
    "cover": step_cover,
}

ALL_STEPS = ["voice", "timeline", "render", "check", "cover"]


def produce_topic(topic: dict, steps: list, engine: str = "auto", voice: str = "") -> bool:
    """对单个选题执行指定步骤"""
    vid = topic["videoId"]
    print(f"\n{'='*60}")
    print(f"{bold(f'▶ {vid} — {topic["title"]}')}")
    print(f"  栏目: {topic.get('column', '-')}  |  主题: {topic.get('theme', '-')}")
    print(f"{'='*60}")

    review_ready, review_missing = review_gate_ready(topic)
    if not review_ready:
        err(f"[{vid}] 人工审核闸门未通过: {', '.join(review_missing)}")
        err(f"[{vid}] 请人工确认剧本与素材后，在批量计划中将对应 review 字段设为 true")
        return False

    ready, missing = check_topic_ready(topic)
    if not ready:
        err(f"[{vid}] 生产前检查未通过: {', '.join(missing)}")
        return False

    all_ok = True
    for step in steps:
        if step == "voice":
            success = step_voice(topic, engine, voice)
        else:
            success = STEP_MAP[step](topic)
        if not success:
            all_ok = False
            warn(f"[{vid}] 步骤 {step} 失败，跳过后续步骤")
            break

    if all_ok:
        ok(f"[{vid}] 全部步骤完成 ✅")
    return all_ok


def main():
    ap = argparse.ArgumentParser(
        description="批量生产编排：从 batch-plan.json 批量执行配音→渲染→检查",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("plan", help="批量计划 JSON 文件路径")
    ap.add_argument("--list", action="store_true", help="列出所有选题及状态")
    ap.add_argument("--check", action="store_true", help="检查脚本是否就绪")
    ap.add_argument("--all", action="store_true", help="全链路生产（voice→timeline→render→check→cover）")
    ap.add_argument("--steps", default="", help="自定义步骤，逗号分隔: voice,timeline,preview,render,check,cover")
    ap.add_argument("--only", default="", help="只生产指定 videoId（逗号分隔多个）")
    ap.add_argument("--engine", default="auto", help="TTS 引擎: auto/azure/edge")
    ap.add_argument("--voice", default="", help="TTS 音色（覆盖 AZURE_VOICE）")
    args = ap.parse_args()

    load_env()
    plan = load_plan(args.plan)

    # 列出模式
    if args.list:
        list_topics(plan)
        return

    # 检查模式
    if args.check:
        print(f"\n{bold(f'检查批量计划: {plan["batchName"]}')}")
        all_ready = True
        for topic in plan["topics"]:
            ready, missing = check_topic_ready(topic)
            review_ready, review_missing = review_gate_ready(topic)
            if ready and review_ready:
                ok(f"[{topic['videoId']}] {topic['title']} — 脚本、素材和人工审核均就绪")
            else:
                details = missing + [f"人工审核: {', '.join(review_missing)}"] if review_missing else missing
                err(f"[{topic['videoId']}] {topic['title']} — {'; '.join(details)}")
                all_ready = False
        print()
        if all_ready:
            ok("所有选题脚本就绪，可以开始生产")
        else:
            warn("部分选题脚本未就绪，请先产出脚本")
        return

    # 生产模式
    if not args.all and not args.steps:
        ap.print_help()
        return

    steps = ALL_STEPS if args.all else [s.strip() for s in args.steps.split(",") if s.strip()]
    # 验证步骤名
    for s in steps:
        if s not in STEP_MAP:
            err(f"未知步骤: {s}，可选: {', '.join(STEP_MAP.keys())}")
            sys.exit(1)

    # 筛选选题
    only_ids = [x.strip() for x in args.only.split(",") if x.strip()] if args.only else []
    topics = plan["topics"]
    if only_ids:
        topics = [t for t in topics if t["videoId"] in only_ids]
        if not topics:
            err(f"未找到匹配的选题: {args.only}")
            sys.exit(1)

    print(f"\n{bold(f'批量生产: {plan["batchName"]}')}")
    print(f"  选题数: {len(topics)}  |  步骤: {' → '.join(steps)}  |  引擎: {args.engine}")
    if args.voice:
        print(f"  音色: {args.voice}")

    # 执行
    results = {}
    start = time.time()
    for topic in topics:
        success = produce_topic(topic, steps, args.engine, args.voice)
        results[topic["videoId"]] = success
        # 更新计划文件中的状态
        if success:
            if "cover" in steps:
                topic["status"] = "delivered"
            elif "render" in steps:
                topic["status"] = "rendered"
            elif "voice" in steps:
                topic["status"] = "voiced"

    # 写回计划文件
    plan_path = Path(args.plan)
    if not plan_path.is_absolute():
        plan_path = ROOT / args.plan
    plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")

    # 汇总
    elapsed = time.time() - start
    success_count = sum(1 for v in results.values() if v)
    fail_count = len(results) - success_count
    print(f"\n{'='*60}")
    print(f"{bold('批量生产汇总')}")
    print(f"{'='*60}")
    print(f"  总计: {len(results)}  |  成功: {GREEN}{success_count}{RESET}  |  失败: {RED}{fail_count}{RESET}  |  耗时: {elapsed:.0f}s")
    for vid, success in results.items():
        status = f"{GREEN}✅ 成功{RESET}" if success else f"{RED}❌ 失败{RESET}"
        print(f"  {vid}: {status}")
    print()


if __name__ == "__main__":
    main()
