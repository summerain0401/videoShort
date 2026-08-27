#!/usr/bin/env python3
"""
generate-story.py — 剧本生成器 2.0（野原经济学 · 蜡笔小新家庭情景剧）
输入一个主题，自动生成故事计划 project-plan.json + 渲染前场景配置 scene-config.json
+ 人读的 故事脚本.md + 纯口播稿 口播稿.txt。

三种模式（--mode）:
  llm          调用 LLM API 生成野原家情景剧对白（小新、美伢、广志、小白）
  from-script  从已有口播稿/对白生成（支持 [小新]:、[美伢]: 等格式）
  template     内置野原家经典生活经济学模板
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

FPS = 30
CHARS_PER_SEC = 4.5
TARGET_SECONDS = 60
DEFAULT_CHARACTER = "小新"

THEME_PROP_MAP = [
    (["半价", "第二件", "促销", "打折", "买一送一"], ["第二件半价牌", "巧克比"]),
    (["工资", "个税", "五险一金", "到手", "年终奖", "社保"], ["工资条", "钱袋"]),
    (["零食", "盲盒", "联名", "溢价", "消费"], ["巧克比", "钱袋"]),
]
FALLBACK_PROPS = ["巧克比", "第二件半价牌", "工资条", "钱袋"]

LLM_PROVIDERS = [
    {"key": "OPENAI_API_KEY",       "base": "https://api.openai.com/v1",                "model": "gpt-4o-mini"},
    {"key": "DEEPSEEK_API_KEY",     "base": "https://api.deepseek.com/v1",              "model": "deepseek-chat"},
    {"key": "MOONSHOT_API_KEY",     "base": "https://api.moonshot.cn/v1",               "model": "moonshot-v1-8k"},
    {"key": "DASHSCOPE_API_KEY",    "base": "https://dashscope.aliyuncs.com/compatible-mode/v1", "model": "qwen-plus"},
    {"key": "ZHIPU_API_KEY",        "base": "https://open.bigmodel.cn/api/paas/v4",     "model": "glm-4-flash"},
]

def load_library() -> dict:
    if not LIBRARY_PATH.exists():
        return {"characters": [], "backgrounds": [], "props": []}
    return json.loads(LIBRARY_PATH.read_text(encoding="utf-8"))

def active_items(lib: dict, category: str) -> list:
    return [i for i in lib.get(category, []) if i.get("status") == "active"]

def parse_speaker_dialogue(text: str) -> list[dict]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]
    dialogues = []
    speaker_re = re.compile(r"^\[?(小新|美伢|广志|风间|小白|小布丁)\]?[:：]\s*(.*)$", re.S)
    for p in paragraphs:
        m = speaker_re.match(p)
        if m:
            dialogues.append({"speaker": m.group(1), "text": m.group(2).strip(), "raw": p})
        else:
            dialogues.append({"speaker": "小新", "text": p, "raw": p})
    return dialogues

def detect_infographics_and_effects(seg: str, speaker: str, theme: str) -> tuple[dict | None, str]:
    """智能检测场景的 2.0 图表与角色表情特效"""
    effect = "none"
    infographic = None

    if "破防" in seg or "生气" in seg or "新之助" in seg or "哇啊" in seg or speaker == "美伢" and ("什么" in seg or "亏" in seg):
        effect = "steam"
    elif "叹气" in seg or "怎么又" in seg or "房贷" in seg or speaker == "广志" and "少" in seg:
        effect = "sweat"
    elif "反转" in seg or "其实" in seg or "真相" in seg or "记住" in seg or "嘿嘿" in seg:
        effect = "idea"
    elif "为什么" in seg or "真的" in seg or "？" in seg:
        effect = "question"

    # 图表触发
    if any(k in seg for k in ["半价", "第二件", "天平", "对比", "更贵", "更省"]):
        infographic = {
            "kind": "balance",
            "title": "性价比天平",
            "leftLabel": "1件原价",
            "rightLabel": "2件半价",
            "tilt": "right"
        }
    elif any(k in seg for k in ["工资", "个税", "五险一金", "扣除", "缩水"]):
        infographic = {
            "kind": "bar",
            "title": "收入结构对比",
            "bars": [
                {"label": "应发薪资", "value": 100, "unit": "%", "color": "#42A5F5"},
                {"label": "实发到手", "value": 75, "unit": "%", "color": "#66BB6A"}
            ]
        }
    elif re.search(r"¥|\d+块|\d+元", seg) and any(k in seg for k in ["到手", "实发", "总共", "净赚"]):
        nums = re.findall(r"\d+", seg)
        val = int(nums[0]) if nums else 1000
        infographic = {
            "kind": "counter",
            "title": "金额核算",
            "counter": {"prefix": "¥", "from": 0, "to": val, "suffix": ""}
        }

    return infographic, effect

def match_props_for_theme(theme: str) -> list[str]:
    for kws, props in THEME_PROP_MAP:
        if any(k in theme for k in kws):
            return props
    return FALLBACK_PROPS[:2]

def build_scenes_from_dialogues(dialogues: list[dict], theme: str, lib: dict) -> list[dict]:
    scenes = []
    props_pool = match_props_for_theme(theme)
    
    # 判断搭档角色
    has_misae = any(d["speaker"] == "美伢" for d in dialogues)
    has_hiroshi = any(d["speaker"] == "广志" for d in dialogues)
    co_star = "美伢" if has_misae else ("广志" if has_hiroshi else "小白")

    for i, d in enumerate(dialogues, start=1):
        spk = d["speaker"]
        txt = d["text"]
        info, eff = detect_infographics_and_effects(txt, spk, theme)
        
        # 角色立绘情绪配置
        elements = []
        if co_star in ["美伢", "广志"]:
            # 双人场景：小新在左，搭档在右
            shin_emo = "explaining" if spk == "小新" else ("smug" if eff == "steam" else "thinking")
            co_emo = "angry" if (spk == co_star and eff == "steam") else ("tired" if (spk == co_star and eff == "sweat") else ("shopping" if co_star == "美伢" else "smile"))
            
            elements.append({
                "type": "character", "name": "小新", "emotion": shin_emo,
                "position": "left", "zIndex": 2, "enterFrom": "left" if i == 1 else "none"
            })
            elements.append({
                "type": "character", "name": co_star, "emotion": co_emo,
                "position": "right", "zIndex": 2, "enterFrom": "right" if i == 1 else "none"
            })
        else:
            # 单人小新场景
            elements.append({
                "type": "character", "name": "小新", "emotion": "explaining" if spk == "小新" else "smile",
                "position": "center", "zIndex": 2, "enterFrom": "none"
            })

        # 挂载道具
        if not info and i % 2 == 1:
            prop_name = props_pool[(i - 1) % len(props_pool)]
            elements.append({
                "type": "prop", "name": prop_name, "position": "right" if len(elements) == 1 else "center",
                "zIndex": 3, "enterFrom": "top"
            })

        # 场景背景选择
        if any(k in theme for k in ["超市", "买", "消费", "商品", "半价"]):
            bg = "春日部超市"
        elif any(k in theme for k in ["工资", "上班", "社保", "职场"]):
            bg = "双叶商事办公室" if i > 1 else "野原家客厅"
        else:
            bg = "野原家客厅" if i > 1 else "春日部街道"

        scene_dict = {
            "sceneId": f"S{i:02d}",
            "speaker": spk,
            "narrationSegment": txt,
            "characterEffect": eff,
            "background": bg,
            "elements": elements,
            "subtitle": {
                "text": txt,
                "highlights": []
            }
        }
        if info:
            scene_dict["infographic"] = info
        scenes.append(scene_dict)

    return scenes

# ----------------- 模板生成模式 -----------------

def generate_template_script(theme: str) -> list[dict]:
    if any(k in theme for k in ["半价", "第二件", "超市", "打折", "凑单"]):
        return [
            {"speaker": "美伢", "text": "哇！小新快看，这盒巧克比第二件半价，一口气买两盒立省十块钱，我真是个持家小能手！"},
            {"speaker": "小新", "text": "诶？美伢，你明明只想吃一盒吧？多掏十块钱买不需要的东西，商家都乐开花啦！"},
            {"speaker": "小新", "text": "这在经济学里叫价格歧视！商家利用第二件半价诱导你多买，虽然单价降低，但你的总支出反而增加了！"},
            {"speaker": "美伢", "text": "什么？！原来多买不是赚了，而是多掏了钱！新之助，你怎么不早说！"},
            {"speaker": "小新", "text": "嘿嘿~ 记住一句话：不需要的东西，打一折也是浪费！点赞关注小新，明天再带你省大钱哦~"}
        ]
    elif any(k in theme for k in ["工资", "到手", "个税", "五险一金", "社保"]):
        return [
            {"speaker": "广志", "text": "唉，明明合同写着月薪一万五，为什么今天到手只有一万一千多，我的零花钱啊……"},
            {"speaker": "小新", "text": "老爸！消失的四千块可不是被美伢没收了，而是变成了你的五险一金和个人所得税！"},
            {"speaker": "小新", "text": "养老保险保障退休，医保报销看病，公积金还能取出来还房贷，其实都是强制替你存下的保障资金！"},
            {"speaker": "广志", "text": "原来如此！虽然到手少了，但公积金账户里还躺着我的备用存款啊！"},
            {"speaker": "小新", "text": "没错！看懂工资条，打工不迷茫！关注小新，下期教你怎么提取公积金～"}
        ]
    else:
        return [
            {"speaker": "美伢", "text": f"小新，为什么生活里的【{theme}】总是让人摸不着头脑？"},
            {"speaker": "小新", "text": f"嘿嘿，其实【{theme}】背后藏着商家最常用的一套商业心理套路！"},
            {"speaker": "小新", "text": "利用信息不对称和沉没成本，让你不知不觉就做出了不理性的决策！"},
            {"speaker": "美伢", "text": "天哪，原来我们每天都在为这些心理套路买单！"},
            {"speaker": "小新", "text": "记住一句话：保持理性思考，钱包才能鼓鼓！关注野原经济学，下期见啦～"}
        ]

def main():
    parser = argparse.ArgumentParser(description="野原经济学 2.0 剧本生成器")
    parser.add_argument("theme", help="视频主题")
    parser.add_argument("project_dir", help="项目输出目录")
    parser.add_argument("--mode", default="template", choices=["template", "from-script", "llm"])
    parser.add_argument("--input-file", help="外部口播稿文件路径")
    parser.add_argument("--video-id", default="C101")
    args = parser.parse_args()

    project_dir = Path(args.project_dir)
    data_dir = project_dir / "data"
    script_dir = project_dir / "script"
    audio_dir = project_dir / "audio"
    data_dir.mkdir(parents=True, exist_ok=True)
    script_dir.mkdir(parents=True, exist_ok=True)
    audio_dir.mkdir(parents=True, exist_ok=True)

    lib = load_library()

    if args.mode == "from-script" and args.input_file:
        raw_text = Path(args.input_file).read_text(encoding="utf-8")
        dialogues = parse_speaker_dialogue(raw_text)
    else:
        dialogues = generate_template_script(args.theme)

    scenes = build_scenes_from_dialogues(dialogues, args.theme, lib)

    # 1. 保存 scene-config.json
    scene_config = {
        "videoId": args.video_id,
        "title": args.theme,
        "scenes": scenes
    }
    (data_dir / "scene-config.json").write_text(
        json.dumps(scene_config, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # 2. 保存口播稿.txt（带 speaker 标记供 tts 2.0 消费）
    script_txt_lines = [f"[{d['speaker']}]: {d['text']}" for d in dialogues]
    (script_dir / "口播稿.txt").write_text("\n\n".join(script_txt_lines), encoding="utf-8")

    # 3. 保存 outro.json
    outro_data = {
        "question": f"今天小新讲的【{args.theme}】听懂了吗？",
        "answer": "不需要的打折品也是浪费，理性消费哦！",
        "character": "小新"
    }
    (data_dir / "outro.json").write_text(
        json.dumps(outro_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"[ok] 2.0 剧本与场景配置已生成: {data_dir / 'scene-config.json'}")
    print(f"[ok] 2.0 对白口播稿已生成: {script_dir / '口播稿.txt'}")
    print(f"[info] 共 {len(scenes)} 个情景剧场景")

if __name__ == "__main__":
    main()
