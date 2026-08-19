#!/usr/bin/env bash
# ============================================================================
# pipeline.sh — 短视频生产一键流水线（阶段 2：脚本化处理链）
#
# 用法:
#   ./scripts/pipeline.sh new "主题" [项目目录]      # 生成新项目剧本（模板模式）
#   ./scripts/pipeline.sh script "主题" <项目目录>   # 重新生成剧本
#   ./scripts/pipeline.sh voice <项目目录> [engine] [音色]  # 配音 (azure/edge/auto)
#   ./scripts/pipeline.sh timeline <项目目录>        # 构建时间轴
#   ./scripts/pipeline.sh preview <项目目录>         # 批量场景预览图
#   ./scripts/pipeline.sh render <项目目录> [--still N]  # 渲染成片/单帧
#   ./scripts/pipeline.sh check <项目目录>           # 统一质检门禁（技术+语义）
#   ./scripts/pipeline.sh all <项目目录>             # voice→timeline→render→check
#   ./scripts/pipeline.sh materials <项目目录>       # 扫描选题素材缺口并生成任务清单
#   ./scripts/pipeline.sh review <项目目录> [--init] # 查看/初始化人工审核文件
#   ./scripts/pipeline.sh list                      # 列出所有项目
#   ./scripts/pipeline.sh batch <plan.json> --list   # 列出批量计划选题
#   ./scripts/pipeline.sh batch <plan.json> --check  # 检查批量脚本就绪
#   ./scripts/pipeline.sh batch <plan.json> --all [--only C004]  # 批量全链生产
#   ./scripts/pipeline.sh batch <plan.json> --steps voice,render [--only C004,C005]
#
# 前置: python3 + edge-tts + ffmpeg/ffprobe, node + remotion
# ============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# 优先使用项目 .venv（装有 edge-tts / azure sdk 等），否则退回系统 python3
if [ -x "$ROOT/.venv/bin/python" ]; then
  PY="${PYTHON:-$ROOT/.venv/bin/python}"
else
  PY="${PYTHON:-python3}"
fi
CMD="${1:-help}"
shift || true

# ---------------------------------------------------------------------------
# 环境变量：自动加载项目根 .env（Azure TTS key 等）
# ---------------------------------------------------------------------------
load_env() {
  [ -f "$ROOT/.env" ] || return 0
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env"
  set +a
  # 兼容旧变量名：AZURE_REGION → AZURE_SPEECH_REGION
  if [ -z "${AZURE_SPEECH_REGION:-}" ] && [ -n "${AZURE_REGION:-}" ]; then
    export AZURE_SPEECH_REGION="$AZURE_REGION"
    warn ".env 使用旧变量名 AZURE_REGION，已自动映射为 AZURE_SPEECH_REGION"
  fi
  info "已加载 $ROOT/.env"
}

# ---------------------------------------------------------------------------
# 辅助
# ---------------------------------------------------------------------------
info()  { printf '\033[36m[%s]\033[0m %s\n' "$(basename "$0")" "$*"; }
ok()    { printf '\033[32m✓\033[0m %s\n' "$*"; }
warn()  { printf '\033[33m⚠\033[0m %s\n' "$*"; }
err()   { printf '\033[31m✗\033[0m %s\n' "$*" >&2; exit 1; }

require_project() {
  [ -n "${1:-}" ] || err "缺少项目目录参数"
  [ -d "$ROOT/$1" ] || err "项目目录不存在: $1"
}

production_gate() {
  local dir="$1"
  "$PY" "$ROOT/scripts/project-review-gate.py" "$dir"
  "$PY" "$ROOT/scripts/material-gap.py" "$dir" >/dev/null
}

# ---------------------------------------------------------------------------
# new / script — 生成剧本
# ---------------------------------------------------------------------------
cmd_new() {
  local theme="$1"
  local dir="${2:-}"
  [ -n "$theme" ] || err "用法: pipeline.sh new \"主题\" [项目目录]"
  if [ -z "$dir" ]; then
    # 自动生成项目目录名：Cxxx_主题缩写
    local next
    next=$(cd "$ROOT/02_项目" 2>/dev/null && ls -d C* 2>/dev/null | sort | tail -1 || echo "C000")
    local num=$(( ${next#C} + 1 ))
    dir=$(printf "C%03d_%s" "$num" "$(echo "$theme" | tr -cd 'a-zA-Z0-9\u4e00-\u9fff' | head -c 8)")
  fi
  "$PY" "$ROOT/scripts/generate-story.py" "$theme" "$ROOT/02_项目/$dir" --mode template
  "$PY" "$ROOT/scripts/project-review-gate.py" "02_项目/$dir" --init
  ok "项目已创建: 02_项目/$dir"
  info "下一步: 编辑 script/口播稿.txt，补齐素材并完成人工审核，然后再进入生产"
}

cmd_script() {
  local theme="$1" dir="$2"
  require_project "$dir"
  "$PY" "$ROOT/scripts/generate-story.py" "$theme" "$ROOT/$dir" --overwrite
  "$PY" "$ROOT/scripts/project-review-gate.py" "$dir" --init
}

# ---------------------------------------------------------------------------
# voice — 配音
# ---------------------------------------------------------------------------
cmd_voice() {
  local dir="$1" engine="${2:-auto}" voice="${3:-}"
  require_project "$dir"
  production_gate "$dir"
  local script_file="$ROOT/$dir/script/口播稿.txt"
  [ -f "$script_file" ] || err "缺少口播稿: $script_file"
  load_env
  info "生成配音: $script_file -> $dir/audio/ (引擎: $engine)"
  # 未显式指定音色时不传 --voice，由 tts.py 读取 AZURE_VOICE（回退默认云希）
  if [ -n "$voice" ]; then
    "$PY" "$ROOT/scripts/tts.py" "$script_file" "$ROOT/$dir/audio" --engine "$engine" --voice "$voice"
  else
    "$PY" "$ROOT/scripts/tts.py" "$script_file" "$ROOT/$dir/audio" --engine "$engine"
  fi
  ok "配音完成"
}

# ---------------------------------------------------------------------------
# timeline — 时间轴
# ---------------------------------------------------------------------------
cmd_timeline() {
  local dir="$1"
  require_project "$dir"
  production_gate "$dir"
  [ -f "$ROOT/$dir/audio/voice.json" ] || err "缺少 audio/voice.json，请先: pipeline.sh voice $dir"
  "$PY" "$ROOT/scripts/build-timeline.py" "$dir"
  ok "时间轴完成"
}

# ---------------------------------------------------------------------------
# preview — 场景预览图
# ---------------------------------------------------------------------------
cmd_preview() {
  local dir="$1"
  require_project "$dir"
  "$PY" "$ROOT/scripts/generate-preview.py" "$dir"
  ok "预览图已导出到 $dir/qa/story-review/"
}

# ---------------------------------------------------------------------------
# render — 渲染
# ---------------------------------------------------------------------------
cmd_render() {
  local dir="$1" extra="${2:-}"
  require_project "$dir"
  production_gate "$dir"
  [ -f "$ROOT/$dir/data/timeline.json" ] || err "缺少 timeline.json，请先: pipeline.sh timeline $dir"
  info "渲染: node scripts/render.mjs $dir $extra"
  node "$ROOT/scripts/render.mjs" "$dir" $extra
  ok "渲染完成"
}

# ---------------------------------------------------------------------------
# check — 检查
# ---------------------------------------------------------------------------
cmd_check() {
  local dir="$1"
  require_project "$dir"
  production_gate "$dir"
  local mp4
  mp4=$(ls "$ROOT/$dir/deliverables/"*.mp4 2>/dev/null | head -1 || true)
  [ -n "$mp4" ] || err "未找到成片，请先: pipeline.sh render $dir"
  info "统一质检门禁: $dir"
  "$PY" "$ROOT/scripts/quality-check.py" "$dir"
  ok "质检通过，报告在 $dir/qa/quality-report.json"
}

# ---------------------------------------------------------------------------
# all — 全链
# ---------------------------------------------------------------------------
cmd_all() {
  local dir="$1" engine="${2:-auto}"
  require_project "$dir"
  cmd_voice "$dir" "$engine"
  cmd_timeline "$dir"
  cmd_render "$dir"
  cmd_check "$dir"
  info "全流程完成 ✅ 成片在 $dir/deliverables/"
}

# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------
cmd_list() {
  cd "$ROOT/02_项目" 2>/dev/null || err "尚无项目目录"
  for d in C*; do
    [ -d "$d" ] || continue
    local mp4=$(ls "$d/deliverables/"*.mp4 2>/dev/null | head -1)
    local status="未渲染"
    [ -n "$mp4" ] && status="✅ $(basename "$mp4")"
    printf '  %-28s %s\n' "$d" "$status"
  done
}

# ---------------------------------------------------------------------------
# batch — 批量生产
# ---------------------------------------------------------------------------
cmd_batch() {
  local plan="$1"
  [ -n "$plan" ] || err "用法: pipeline.sh batch <plan.json> [--list|--check|--all|--steps ...]"
  shift
  load_env
  "$PY" "$ROOT/scripts/batch-produce.py" "$plan" "$@"
}

cmd_materials() {
  local dir="$1"
  require_project "$dir"
  "$PY" "$ROOT/scripts/material-gap.py" "$dir"
}

cmd_review() {
  local dir="$1"
  require_project "$dir"
  "$PY" "$ROOT/scripts/project-review-gate.py" "$dir" "${2:-}"
}

# ---------------------------------------------------------------------------
help() {
  sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'
}

case "$CMD" in
  new)      cmd_new "$@" ;;
  script)   cmd_script "$@" ;;
  voice)    cmd_voice "$@" ;;
  timeline) cmd_timeline "$@" ;;
  preview)  cmd_preview "$@" ;;
  render)   cmd_render "$@" ;;
  check)    cmd_check "$@" ;;
  all)      cmd_all "$@" ;;
  list)     cmd_list "$@" ;;
  batch)    cmd_batch "$@" ;;
  materials) cmd_materials "$@" ;;
  review)  cmd_review "$@" ;;
  help|-h|--help) help ;;
  *) help; exit 1 ;;
esac
