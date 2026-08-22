#!/usr/bin/env python3
"""
generate-story.py — 剧本生成器（阶段 2：内容脚本化）
输入一个主题，自动生成故事计划 project-plan.json + 渲染前场景配置 scene-config.json
+ 人读的 故事脚本.md + 纯口播稿 口播稿.txt。

三种模式（--mode）:
  llm          调用 LLM API 生成（需环境变量中有 API key，见下方列表）
  from-script  从已有口播稿生成（--input-file，按空行或「场景N/Sxx/###」切分）
  template     内置叙事模板生成骨架（默认；口播含【待润色】标记，由确认阶段打磨）

LLM API 自动检测（按优先级）:
  OPENAI_API_KEY   -> https://api.openai.com/v1      (gpt-4o-mini)
  DEEPSEEK_API_KEY -> https://api.deepseek.com/v1    (deepseek-chat)
  MOONSHOT_API_KEY -> https://api.moonshot.cn/v1     (moonshot-v1-8k)
  DASHSCOPE_API_KEY-> https://dashscope.aliyuncs.com/compatible-mode/v1 (qwen-plus)
  ZHIPU_API_KEY    -> https://open.bigmodel.cn/api/paas/v4 (glm-4-flash)
  可用 --api-base / --model 覆盖

用法:
    python scripts/generate-story.py "主题" <project_dir> [--mode auto|llm|from-script|template]
        [--video-id C002] [--input-file 稿子.txt] [--api-base URL] [--model NAME] [--overwrite]

示例:
    # 有 key 时：主题直接生成完整剧本
    python scripts/generate-story.py "为什么商品会涨价" "02_项目/C002_商品涨价" --mode llm --video-id C002

    # 无 key 时：人先写口播稿（每段空行分隔），脚本拆场景
    python scripts/generate-story.py "为什么商品会涨价" "02_项目/C002_商品涨价" --mode from-script --input-file my_script.txt --video-id C002

    # 无 key 且没有稿子：模板骨架，人工确认阶段再打磨
    python scripts/generate-story.py "为什么商品会涨价" "02_项目/C002_商品涨价" --mode template --video-id C002
"""
import argparse
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIBRARY_PATH = ROOT / "shared" / "material-library.json"

# ---------------------------------------------------------------- 常量

FPS = 30
CHARS_PER_SEC = 4.5          # 中文口播约 4.5 字/秒
TARGET_SECONDS = 60          # 目标成片时长（不含片头片尾，正文约 25-35s）
N_SCENES_TARGET = (4, 6)     # 场景数范围

DEFAULT_CHARACTER = "小布丁"  # 品牌手册唯一主角（ACCOUNT_BRAND.md 定版）

# 情绪序列：按叙事节奏分配（钩子→定义→拆解→拆解→影响→总结）
EMOTION_SEQUENCE = ["thinking", "explaining", "serious", "confused", "worried", "smile", "shocked"]

# 主题关键词 → 建议道具（从素材库按 name 匹配）
THEME_PROP_MAP = [
    (["钱", "价格", "通胀", "通货膨胀", "工资", "物价", "涨价", "货币", "贬值", "经济"],
     ["钱袋", "物价牌", "工资条"]),
    (["超市", "购物", "商品", "市场", "消费", "商场", "商店"],
     ["超市货架", "钱袋"]),
]
FALLBACK_PROPS = ["钱袋", "工资条"]

# 数字/计算/对比 语句 → 动态视觉子模板（节点3：不依赖生图，纯文本图层由 Remotion 渲染）
VS_KEYWORDS = ("对比", "更贵", "更省", "更划算", "更便宜", "哪个", "还是", "vs", "VS", "不如", "差", "比")
# 数字+单位（可含口语尾数，如 "12块8" = 12.8 元）
NUM_UNIT_RE = re.compile(r"\d+(?:\.\d+)?\s*(?:%|元|块|折|倍|克|斤|分|毫升|ml|ML|L)\d*")
UNIT_CHARS = "元块克斤折倍分%毫升mlML"


def detect_overlays(seg: str) -> list:
    """在数字/计算/对比语句上触发特定子模板：价格标签 / 算式 / 对比卡。

    返回 scene-config 的 overlay 元素列表（Remotion 端纯文本渲染，无需素材图）。
    触发规则：
      · 价格对（N元/N块 ×2）+ 对比词 → vs-card（如 "9.9块 vs 7.5块"）
      · 对比词 + ≥2 个带单位数字 → vs-card（如 "100克 vs 9.9块" 退化形态）
      · 单个带单位数字 → price-tag（优先取价格，如 "5.5块"）
      · 计算语义（除以/单价/每克）→ equation（如 "总价 ÷ 重量 = 单价"）
      可同时返回 vs-card/price-tag + equation 多个 overlay。
    """
    nums = [m.group(0).strip() for m in NUM_UNIT_RE.finditer(seg)]
    nums = [n for n in nums if re.search(r"\d", n)][:4]
    if not nums:
        return []
    units = [n for n in nums if re.search(f"[{re.escape(UNIT_CHARS)}]", n)]
    has_vs = any(k in seg for k in VS_KEYWORDS)
    # 价格对优先：形如 "9.9块"/"7.5元" 的成对价格
    price_pairs = re.findall(r"\d+(?:\.\d+)?\s*(?:元|块)", seg)
    overlays = []
    if has_vs and len(price_pairs) >= 2:
        overlays.append({
            "type": "overlay", "kind": "vs-card",
            "text": f"{price_pairs[0].strip()} vs {price_pairs[1].strip()}",
            "title": "对比一下", "position": "top",
        })
    elif has_vs and len(units) >= 2:
        overlays.append({
            "type": "overlay", "kind": "vs-card",
            "text": f"{units[0]} vs {units[1]}",
            "title": "对比一下", "position": "top",
        })
    elif units:
        # price-tag 优先展示价格（如 "5.5块"），其次带单位数字（如 "50克"）
        pick = price_pairs[0].strip() if price_pairs else units[0]
        overlays.append({
            "type": "overlay", "kind": "price-tag",
            "text": pick, "title": "关键数字", "position": "top",
        })
    else:
        overlays.append({
            "type": "overlay", "kind": "equation",
            "text": nums[0], "title": "关键数字", "position": "top",
        })
    # 计算语义 → 追加算式卡（价格/重量换算讲解处）
    if re.search(r"除以|除一下|单价|每\d*\.?\d*\s*克|折合成", seg):
        overlays.append({
            "type": "overlay", "kind": "equation",
            "text": "总价 ÷ 重量 = 单价", "title": "算一算", "position": "bottom",
        })
    return overlays

# LLM 配置
LLM_PROVIDERS = [
    {"key": "OPENAI_API_KEY",       "base": "https://api.openai.com/v1",                "model": "gpt-4o-mini"},
    {"key": "DEEPSEEK_API_KEY",     "base": "https://api.deepseek.com/v1",              "model": "deepseek-chat"},
    {"key": "MOONSHOT_API_KEY",     "base": "https://api.moonshot.cn/v1",               "model": "moonshot-v1-8k"},
    {"key": "DASHSCOPE_API_KEY",    "base": "https://dashscope.aliyuncs.com/compatible-mode/v1", "model": "qwen-plus"},
    {"key": "ZHIPU_API_KEY",        "base": "https://open.bigmodel.cn/api/paas/v4",     "model": "glm-4-flash"},
]


# ---------------------------------------------------------------- 素材库

def load_library() -> dict:
    if not LIBRARY_PATH.exists():
        return {"characters": [], "backgrounds": [], "props": []}
    return json.loads(LIBRARY_PATH.read_text(encoding="utf-8"))


def active_items(lib: dict, category: str) -> list:
    return [i for i in lib.get(category, []) if i.get("status") == "active"]


def library_summary(lib: dict) -> str:
    """给 LLM 看的素材库清单"""
    lines = []
    for cat, label in (("characters", "角色"), ("backgrounds", "背景"), ("props", "道具")):
        items = active_items(lib, cat)
        if not items:
            continue
        lines.append(f"{label}({cat}):")
        for i in items:
            names = [i["name"], i.get("emotion") or "", " ".join(i.get("tags", []))]
            lines.append(f"  - {i['name']} | 情绪:{i.get('emotion') or '无'} | 描述:{i.get('contentDescription', '')}")
    return "\n".join(lines) or "(素材库为空)"


def match_props(lib: dict, theme: str, scene_idx: int, total: int) -> list:
    """从素材库挑道具：先按主题关键词，再用兜底道具。scene_idx 从 1 开始。"""
    props = active_items(lib, "props")
    picked = []
    for kws, names in THEME_PROP_MAP:
        if any(kw in theme for kw in kws):
            for n in names:
                if any(p["name"] == n for p in props) and n not in picked:
                    picked.append(n)
    for n in FALLBACK_PROPS:
        if any(p["name"] == n for p in props) and n not in picked:
            picked.append(n)
    if not picked:
        return []
    # 开头放第一个道具，结尾放最后一个，中间轮换
    if scene_idx == 1:
        return [picked[0]]
    if scene_idx == total:
        return [picked[-1]]
    return [picked[1 % len(picked)]] if len(picked) > 2 else [picked[0]]


# ---------------------------------------------------------------- 场景构建

def build_scenes(narration_segments: list, lib: dict, theme: str) -> list:
    """从口播段落列表构建 scene-config 的 scenes[]（不带 preferredStart，由调用方填充）"""
    total = len(narration_segments)
    scenes = []
    for idx, seg in enumerate(narration_segments, start=1):
        seg = seg.strip()
        if not seg:
            continue
        emotion = EMOTION_SEQUENCE[(idx - 1) % len(EMOTION_SEQUENCE)]
        elements = [{"type": "character", "name": DEFAULT_CHARACTER, "emotion": emotion,
                     "enterFrom": "none" if idx > 1 else "left", "zIndex": 2}]
        for prop_name in match_props(lib, theme, idx, total):
            elements.append({"type": "prop", "name": prop_name,
                             "enterFrom": "right" if idx % 2 == 1 else "left", "zIndex": 3})
        # 数字/计算/对比语句 → 动态视觉子模板（价格标签/算式/对比卡）
        elements.extend(detect_overlays(seg))
        scenes.append({
            "sceneId": f"S{idx:02d}",
            "narrationSegment": seg,
            "elements": elements,
        })
    return scenes


def fill_preferred_start(scenes: list) -> list:
    """按字数估算每个场景的开始时间（精确对齐由 build-timeline 用配音时间完成）"""
    cursor = 0.0
    for s in scenes:
        s["preferredStart"] = round(cursor, 3)
        dur = len(s["narrationSegment"]) / CHARS_PER_SEC
        cursor += dur + 0.15
    return scenes


def split_script(text: str) -> list:
    """把口播稿切成语义段落：优先按「场景N / Sxx / ###」标记，其次按空行。"""
    text = text.strip()
    # 1. 显式场景标记
    marker = re.split(r"(?:^|\n)\s*(?:场景\s*\d+|S\d{2}|###\s*\d+|#+\s*场景)", text, flags=re.M)
    segs = [m.strip() for m in marker if m.strip()]
    if len(segs) >= 2:
        return segs
    # 2. 空行分段
    segs = [m.strip() for m in re.split(r"\n\s*\n", text) if m.strip()]
    if len(segs) >= 2:
        return segs
    # 3. 整段（单场景）
    return [text]


# 前 3 秒 / 结尾互动 钩子校验词表
PADDING_OPENERS = ("今天", "大家好", "接下来", "这是一期", "我们来聊", "让我们", "先来看看", "本期", "欢迎")
INTERACTIVE_ENDERS = ("评论", "你更", "你觉", "投票", "选择", "聊聊", "怎么看", "站队", "扣1", "扣一", "告诉我")
QUESTION_HINTS = ("？", "?", "吗", "呢", "为什么", "怎么", "居然", "竟然", "其实", "差距", "差别")


def validate_hook_rules(narration_full: str, segs: list) -> list:
    """对已写好的口播稿做钩子规则校验，返回 [(rule, ok, hint), ...]，不阻断生成。

    规则：
      R1 0 秒入戏：首句不得是「今天/大家好/接下来…」等静态垫片开场
      R2 前 3 秒 Hook：首句应含 疑问/数字/反差 元素
      R3 结尾互动：末句应含 投票/选择/评论 引导词
    """
    first = segs[0].strip() if segs else narration_full.strip()
    last = segs[-1].strip() if segs else narration_full.strip()
    checks = []
    # R1
    if any(first.startswith(p) for p in PADDING_OPENERS):
        checks.append(("R1 0秒入戏", False,
                       "首句疑似垫片开场，请改为直接抛钩子（反常识提问/数字对比），0 秒入戏"))
    else:
        checks.append(("R1 0秒入戏", True, "首句无垫片开场"))
    # R2
    has_hook = any(h in first for h in QUESTION_HINTS) or bool(re.search(r"\d", first))
    if not has_hook:
        checks.append(("R2 前3秒Hook", False,
                       "首句缺少 疑问/数字/反差 元素，建议用「你知道吗，XX 其实…」或数字对比句式"))
    else:
        checks.append(("R2 前3秒Hook", True, "首句含钩子元素"))
    # R3
    if not any(e in last for e in INTERACTIVE_ENDERS):
        checks.append(("R3 结尾互动", False,
                       "末句缺少互动引导，建议追加投票式提问：如「你更倾向 A 还是 B？评论区站队」"))
    else:
        checks.append(("R3 结尾互动", True, "末句含互动引导词"))
    return checks


# ---------------------------------------------------------------- LLM

def detect_llm(api_base: str | None, model: str | None) -> tuple:
    for p in LLM_PROVIDERS:
        if os.environ.get(p["key"]):
            return api_base or p["base"], model or p["model"], os.environ[p["key"]]
    raise RuntimeError(
        "未检测到 LLM API key。可设置 OPENAI_API_KEY / DEEPSEEK_API_KEY / "
        "MOONSHOT_API_KEY / DASHSCOPE_API_KEY / ZHIPU_API_KEY，或改用 --mode from-script / template"
    )


def llm_chat(base: str, api_key: str, model: str, messages: list) -> str:
    body = json.dumps({
        "model": model,
        "messages": messages,
        "temperature": 0.7,
        "response_format": {"type": "json_object"},
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{base.rstrip('/')}/chat/completions",
        data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]


def llm_generate_story(theme: str, lib_summary: str, video_id: str, title: str,
                       api_base: str, model: str, api_key: str) -> dict:
    sys_prompt = f"""你是短视频科普解说编剧。为「{theme}」写一条 60 秒左右的解说视频剧本。

要求：
1. 口播全文 180~230 字，纯口语化，念起来顺（可以默读验证），一条因果链讲到底
2. 黄金开篇（硬性，前 3 秒必须入戏）：
   · 第 1 句就是钩子，禁止任何静态前置垫片——「今天我们来聊聊…」「大家好…」「这是一个关于…的视频」「接下来讲…」一律禁止
   · 首选「反常识提问」句式：如"你知道吗，XX 其实是个陷阱？""为什么越贵的东西反而越好卖？"
   · 或「数字对比套路」：如"3 块钱和 30 块钱的矿泉水，差别居然只有…"
   · 第 1 句必须包含 悬念 / 冲突 / 数字 三要素中的至少一个
3. 结构：黄金钩子 → 一句话定义 → 通俗拆解（1-2 层因果）→ 生活中的例子 → 金句总结
4. 结尾互动钩子（硬性）：最后一句必须是投票/选择式提问，引导评论区互动，如：
   "你更倾向 A 还是 B？评论区站队！""如果是你，你会怎么选？评论区聊聊你的答案"
5. 按「新信息切画面」拆成 4~6 个语义场景：新人物/动作/对象/状态变化才切，不按固定秒数
6. 每个场景的 narrationSegment 是整句口播，拼接起来 = 全文口播
7. 画面元素只从下面的素材库清单里选，没有合适道具就只放角色；背景按场景给建议名
8. 角色统一用「{DEFAULT_CHARACTER}」，情绪从 [thinking, explaining, serious, worried, smile, shocked, confused] 选
9. 涉及数字/克重/价格/对比的句子（如"大包 vs 小包""每克单价"），在对应场景的 props 里尽量给出 商品道具 或 价格标签 类道具名（素材库里有就选，没有就用最接近的）

可用素材库：
{lib_summary}

只输出一个 JSON 对象，不要任何其他文字，格式：
{{
  "narration": "全文口播（所有场景拼接）",
  "scenes": [
    {{
      "sceneId": "S01",
      "narrationSegment": "该场景口播整句",
        "characters": [{{"name": "小布丁", "emotion": "thinking"}}],
      "props": [{{"name": "钱袋"}}],
      "background": "小镇街道",
      "layout": "center-focus"
    }}
  ]
}}"""
    content = llm_chat(api_base, api_key, model, [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": "请生成剧本 JSON。"},
    ])
    # 容错：LLM 偶尔会包 ```json``` 代码块
    content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip(), flags=re.M)
    data = json.loads(content)
    if "narration" not in data or not data.get("scenes"):
        raise RuntimeError(f"LLM 返回结构异常: {json.dumps(data, ensure_ascii=False)[:300]}")
    return data


def _current_key() -> str:
    for p in LLM_PROVIDERS:
        if os.environ.get(p["key"]):
            return os.environ[p["key"]]
    return ""


# ---------------------------------------------------------------- 模板模式

def template_story(theme: str, lib_summary: str) -> dict:
    """内置 6 场景叙事模板。口播含【待润色】标记，确认阶段打磨后改 from-script 重新生成。"""
    scenes = [
        ("你有没有发现，【围绕“{t}”抛一个反常识提问或数字对比，如“XX竟然比XX更X/3块的XX和30块的XX”，25-35字】？", ["thinking"], ["钱袋"]),
        ("简单说，{t}就是【用一句大白话下定义，20-30字】。", ["explaining"], ["物价牌"]),
        ("为什么会这样？因为【讲第一层因果：机制/原理，40-50字】。", ["serious"], ["超市货架"]),
        ("更关键的是，【讲第二层因果或对比：谁受影响/会怎样发展，40-50字】。", ["explaining"], ["钱袋"]),
        ("打个比方，【一个具体生活场景例子，30-40字】。", ["worried"], ["工资条"]),
        ("所以记住，【金句总结，15-25字】。你更倾向【围绕{t}给两个对立选项，如“大包装还是小包装”】？评论区聊聊你的选择。", ["happy"], ["钱袋"]),
    ]
    out_scenes = []
    narration_parts = []
    for idx, (tpl, emotions, props) in enumerate(scenes, start=1):
        seg = tpl.format(t=theme)
        elements = [{"type": "character", "name": DEFAULT_CHARACTER,
                     "emotion": emotions[0],
                     "enterFrom": "none" if idx > 1 else "left", "zIndex": 2}]
        for p in props:
            elements.append({"type": "prop", "name": p,
                             "enterFrom": "right" if idx % 2 == 1 else "left", "zIndex": 3})
        out_scenes.append({
            "sceneId": f"S{idx:02d}",
            "narrationSegment": seg,
            "characters": [{"name": DEFAULT_CHARACTER, "emotion": emotions[0]}],
            "props": [{"name": p} for p in props],
            "background": "小镇街道" if idx <= 2 else "超市内部",
            "layout": "center-focus",
        })
        narration_parts.append(seg)
    return {"narration": "\n".join(narration_parts), "scenes": out_scenes}


# ---------------------------------------------------------------- 写文件

def write_outputs(project_dir: Path, video_id: str, title: str, theme: str,
                  plan_scenes: list, narration_full: str, gen_mode: str) -> None:
    """写 project-plan.json / scene-config.json / 口播稿.txt / 故事脚本.md"""
    (project_dir / "data").mkdir(parents=True, exist_ok=True)
    (project_dir / "script").mkdir(parents=True, exist_ok=True)
    (project_dir / "audio").mkdir(parents=True, exist_ok=True)
    (project_dir / "qa" / "story-review").mkdir(parents=True, exist_ok=True)
    (project_dir / "qa" / "final-frames").mkdir(parents=True, exist_ok=True)
    (project_dir / "deliverables").mkdir(parents=True, exist_ok=True)

    # project-plan.json（故事计划，source of truth）
    plan = {
        "videoId": video_id,
        "title": title,
        "theme": theme,
        "duration": round(len(narration_full) / CHARS_PER_SEC + 8, 1),  # 正文 + 片头片尾
        "generatedBy": f"generate-story.py ({gen_mode})",
        "narration": narration_full,
        "scenes": plan_scenes,
    }
    plan_path = project_dir / "data" / "project-plan.json"
    plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")

    # scene-config.json（渲染前配置：只用计划里的场景精简版）
    scene_config = {
        "videoId": video_id,
        "title": title,
        "scenes": [],
    }
    for ps in plan_scenes:
        scene_config["scenes"].append({
            "sceneId": ps["sceneId"],
            "narrationSegment": ps["narrationSegment"],
            "elements": [
                {"type": "character", "name": c["name"], "emotion": c.get("emotion"),
                 "enterFrom": "none" if ps["sceneId"] != "S01" else "left", "zIndex": 2}
                for c in ps.get("characters", [])
            ] + [
                {"type": "prop", "name": p["name"],
                 "enterFrom": "right" if int(ps["sceneId"][1:]) % 2 == 1 else "left", "zIndex": 3}
                for p in ps.get("props", [])
            ] + list(ps.get("overlays", [])),
        })
    fill_preferred_start(scene_config["scenes"])
    scene_path = project_dir / "data" / "scene-config.json"
    scene_path.write_text(json.dumps(scene_config, ensure_ascii=False, indent=2), encoding="utf-8")

    # 口播稿.txt（纯文本，供 tts.py 按空行切分场景；必须用 \n\n 分隔段落）
    script_txt = "\n\n".join(ps["narrationSegment"].strip() for ps in plan_scenes)
    if gen_mode == "template":
        script_txt += ("\n\n【提示】本稿为模板骨架，含【待润色】标记。请人工/LLM 打磨后，"
                       "用 --mode from-script 重新生成 scene-config，或直接在确认环节编辑本文件。")
    (project_dir / "script" / "口播稿.txt").write_text(script_txt, encoding="utf-8")

    # 故事脚本.md（人读：口播 + 画面任务 + 素材预览排在一起）
    md_lines = [
        f"# {title}（{video_id}）",
        "",
        f"> 主题：{theme} ｜ 生成方式：generate-story.py ({gen_mode})",
        "",
        "## 口播稿（源文件）",
        "",
        narration_full,
        "",
        "## 分镜",
        "",
    ]
    for ps in plan_scenes:
        chars = "、".join(f"{c['name']}({c.get('emotion','-')})" for c in ps.get("characters", []))
        props = "、".join(p["name"] for p in ps.get("props", [])) or "无"
        md_lines += [
            f"### {ps['sceneId']} {ps['narrationSegment']}",
            f"- 角色：{chars or '-'}",
            f"- 道具：{props}",
            f"- 背景：{ps.get('background','自动')}",
            f"- 布局：{ps.get('layout','center-focus')}",
            "",
        ]
    md_lines += [
        "## 待确认事项",
        "",
        "1. 口播是否口语、因果链是否清晰（念一遍验证）",
        "2. 画面元素是否都能从素材库找到（render 时会自动解析，找不到的元素会被跳过）",
        "3. 场景数量是否符合叙事节奏（4-6 个）",
        "",
    ]
    (project_dir / "script" / "故事脚本.md").write_text("\n".join(md_lines), encoding="utf-8")

    print(f"[ok] 项目目录: {project_dir}")
    print(f"[ok] project-plan.json : {plan_path}")
    print(f"[ok] scene-config.json : {scene_path}")
    print(f"[ok] 口播稿.txt        : {project_dir / 'script' / '口播稿.txt'}")
    print(f"[ok] 故事脚本.md       : {project_dir / 'script' / '故事脚本.md'}")
    print(f"[info] {len(plan_scenes)} 个场景 | 口播 {len(narration_full)} 字 | "
          f"预计正文 {round(len(narration_full)/CHARS_PER_SEC,1)}s")


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description="剧本生成器：主题 → project-plan.json + scene-config.json")
    ap.add_argument("theme", help="视频主题")
    ap.add_argument("project_dir", help="项目目录（不存在则创建）")
    ap.add_argument("--mode", default="auto", choices=["auto", "llm", "from-script", "template"],
                    help="生成模式（auto=有 key 用 llm，否则 template）")
    ap.add_argument("--video-id", default=None, help="项目编号，如 C002（默认从目录名推断）")
    ap.add_argument("--input-file", default=None, help="from-script 模式的已有口播稿")
    ap.add_argument("--api-base", default=None, help="LLM API 地址")
    ap.add_argument("--model", default=None, help="LLM 模型名")
    ap.add_argument("--overwrite", action="store_true", help="覆盖已存在的 scene-config.json")
    args = ap.parse_args()

    project_dir = Path(args.project_dir)
    video_id = args.video_id or re.sub(r"[^A-Za-z0-9]", "", project_dir.name)[:4].upper() or "C000"

    scene_path = project_dir / "data" / "scene-config.json"
    if scene_path.exists() and not args.overwrite:
        print(f"[warn] 已存在 {scene_path}，跳过（用 --overwrite 强制重新生成）")
        sys.exit(0)

    lib = load_library()
    lib_summary = library_summary(lib)

    # 决定模式
    mode = args.mode
    if mode == "auto":
        try:
            detect_llm(args.api_base, args.model)
            mode = "llm"
        except RuntimeError:
            mode = "template"

    if mode == "llm":
        try:
            base, model, api_key = detect_llm(args.api_base, args.model)
        except RuntimeError as e:
            print(f"[error] {e}", file=sys.stderr)
            sys.exit(1)
        print(f"[llm] 使用 {base} / {model} 生成剧本…")
        plan = llm_generate_story(args.theme, lib_summary, video_id, args.theme, base, model, api_key)
        narration_full = plan["narration"]
        plan_scenes = plan["scenes"]
        # 校验场景拼接
        joined = "".join(s["narrationSegment"] for s in plan_scenes)
        if abs(len(joined) - len(narration_full.replace("\n", ""))) > max(20, len(joined) * 0.3):
            print(f"[warn] 场景拼接与全文长度差异较大，以全文为准（{len(joined)} vs {len(narration_full)}字）")
    elif mode == "from-script":
        if not args.input_file or not Path(args.input_file).exists():
            print("[error] --mode from-script 需要 --input-file 指向已有口播稿", file=sys.stderr)
            sys.exit(1)
        text = Path(args.input_file).read_text(encoding="utf-8")
        segments = split_script(text)
        narration_full = "\n".join(segments)
        # 钩子规则校验（0秒入戏 / 前3秒Hook / 结尾互动），只提示不阻断
        for rule, ok, hint in validate_hook_rules(narration_full, segments):
            if ok:
                print(f"[hook] ✓ {rule}: {hint}")
            else:
                print(f"[hook] ⚠ {rule}: {hint}")
        scenes = build_scenes(segments, lib, args.theme)
        plan_scenes = []
        for idx, s in enumerate(scenes, start=1):
            plan_scenes.append({
                "sceneId": s["sceneId"],
                "narrationSegment": s["narrationSegment"],
                "characters": [{"name": e["name"], "emotion": e.get("emotion")}
                               for e in s["elements"] if e["type"] == "character"],
                "props": [{"name": e["name"]} for e in s["elements"] if e["type"] == "prop"],
                "overlays": [e for e in s["elements"] if e["type"] == "overlay"],
                "background": "小镇街道" if idx <= 2 else "超市内部",
                "layout": "center-focus",
            })
    else:  # template
        plan = template_story(args.theme, lib_summary)
        narration_full = plan["narration"]
        plan_scenes = plan["scenes"]

    write_outputs(project_dir, video_id, args.theme, args.theme,
                  plan_scenes, narration_full, mode)
    print("\n下一步:")
    print("  1. 编辑 script/口播稿.txt 打磨口播")
    print("  2. python scripts/build-timeline.py 前置步骤: python scripts/tts.py script/口播稿.txt audio/")
    print("  3. node scripts/render.mjs <project_dir>")
    print("  或直接跑 ./scripts/pipeline.sh all <project_dir>")


if __name__ == "__main__":
    main()
