#!/usr/bin/env python3
"""
check-pronunciation.py — 多音字风险预检脚本

扫描口播稿文本，命中内置的高/中/低风险多音字词表时，
输出「词 | 所在句 | 建议读音 | 常见误读 | 风险等级」清单，
供人工确认：改写口播稿换词，或把词加入 tts.py 的 PRONUNCIATION_OVERRIDES。

用法:
    python scripts/check-pronunciation.py <text_file> [--json out.json]
    python scripts/check-pronunciation.py <text_file> --project 02_项目/C008_小包装更贵

输出:
    qa/pronunciation-report.json（默认输出到 <text_file> 同级的 qa/ 下）
"""
import argparse
import json
import re
import sys
from pathlib import Path

# 多音字风险词表：word 词、correct 建议读音、wrong 常见误读、
# level 风险等级（high=极可能误读 / medium=语境相关 / low=参考）、
# note 语境说明。可随实际口播稿持续扩充。
PRONUNCIATION_RISK_WORDS = [
    # ---- 高风险：极易误读 ----
    {"word": "便宜", "correct": "piányi", "wrong": "biànyí", "level": "high", "note": "价格低（易按『方便』读 biànyí）"},
    {"word": "花呗", "correct": "huābēi", "wrong": "huābèi", "level": "high", "note": "支付宝产品名，呗读 bēi"},
    {"word": "干等", "correct": "gànděng", "wrong": "gānděng", "level": "high", "note": "干=做义读 gàn，易误读 gān"},
    {"word": "干活", "correct": "gànhuó", "wrong": "gānhuó", "level": "high", "note": "干=做义读 gàn"},
    {"word": "干着急", "correct": "gānzháojí", "wrong": "gànzháojí", "level": "high", "note": "干=空/徒然义读 gān"},
    {"word": "藏着", "correct": "cángzhe", "wrong": "zàngzhe", "level": "high", "note": "藏=隐藏义读 cáng"},
    {"word": "挣钱", "correct": "zhèngqián", "wrong": "zhēngqián", "level": "high", "note": "挣=获取义读 zhèng（挣扎才读 zhēng）"},
    {"word": "省", "correct": "shěng", "wrong": "xǐng", "level": "high", "note": "节省/省份读 shěng（反省读 xǐng）"},
    {"word": "涨", "correct": "zhǎng", "wrong": "zhàng", "level": "high", "note": "上涨/涨价读 zhǎng（涨红脸才读 zhàng）"},
    {"word": "得", "correct": "děi/de/dé", "wrong": "", "level": "high", "note": "『得加把劲』读 děi，『跑得快』读 de，『得到』读 dé，需语境判断"},
    # ---- 中风险：语境相关 ----
    {"word": "银行", "correct": "yínháng", "wrong": "yínxíng", "level": "medium", "note": "行=机构义读 háng"},
    {"word": "供给", "correct": "gōngjǐ", "wrong": "gōnggěi", "level": "medium", "note": "供=供应义读 gōng；给=供给义读 jǐ"},
    {"word": "供应", "correct": "gōngyìng", "wrong": "gòngyìng", "level": "medium", "note": "供=提供义读 gōng（供奉读 gòng）"},
    {"word": "处理", "correct": "chǔlǐ", "wrong": "chùlǐ", "level": "medium", "note": "处=办理义读 chǔ"},
    {"word": "相处", "correct": "xiāngchǔ", "wrong": "xiāngchù", "level": "medium", "note": "处=交往义读 chǔ"},
    {"word": "重复", "correct": "chóngfù", "wrong": "zhòngfù", "level": "medium", "note": "重=再义读 chóng"},
    {"word": "重要", "correct": "zhòngyào", "wrong": "chóngyào", "level": "medium", "note": "重=紧要义读 zhòng"},
    {"word": "长期", "correct": "chángqī", "wrong": "zhǎngqī", "level": "medium", "note": "长=时长义读 cháng（长工资读 zhǎng）"},
    {"word": "数钱", "correct": "shǔqián", "wrong": "shùqián", "level": "medium", "note": "数=清点义读 shǔ"},
    {"word": "数量", "correct": "shùliàng", "wrong": "shǔliàng", "level": "medium", "note": "数=数目义读 shù"},
    {"word": "利率", "correct": "lìlǜ", "wrong": "lìshuài", "level": "medium", "note": "率=比率义读 lǜ（率领读 shuài）"},
    {"word": "概率", "correct": "gàilǜ", "wrong": "gàishuài", "level": "medium", "note": "率=比率义读 lǜ"},
    {"word": "调整", "correct": "tiáozhěng", "wrong": "diàozhěng", "level": "medium", "note": "调=整理义读 tiáo（调动读 diào）"},
    {"word": "调查", "correct": "diàochá", "wrong": "tiáochá", "level": "medium", "note": "调=查究义读 diào"},
    {"word": "觉着", "correct": "juézhe", "wrong": "jiàozhe", "level": "medium", "note": "觉=感受义读 jué（睡觉读 jiào）"},
    {"word": "高高兴兴", "correct": "gāogāoxìngxìng", "wrong": "gāogāoxīngxīng", "level": "medium", "note": "兴=喜悦义读 xìng（兴旺读 xīng）"},
    {"word": "有空", "correct": "yǒukòng", "wrong": "yǒukōng", "level": "medium", "note": "空=闲暇义读 kòng"},
    {"word": "空隙", "correct": "kòngxì", "wrong": "kōngxì", "level": "medium", "note": "空=间隙义读 kòng"},
    # ---- 低风险：语境较清晰，供参考 ----
    {"word": "着急", "correct": "zháojí", "wrong": "zhāojí", "level": "low", "note": "着=急切义读 zháo"},
    {"word": "着凉", "correct": "zháoliáng", "wrong": "zheliáng", "level": "low", "note": "着=感受义读 zháo"},
    {"word": "贝壳", "correct": "bèiké", "wrong": "bèiqiào", "level": "low", "note": "壳=坚硬外皮义读 ké（地壳读 qiào）"},
    {"word": "流血", "correct": "liúxuè", "wrong": "liúxiě", "level": "low", "note": "血=书面语读 xuè（口语 xiě 少用）"},
]


def split_sentences(text: str) -> list[str]:
    """按中文句读标点切句，返回非空句子列表"""
    parts = re.split(r"[。！？；\n]+", text)
    return [p.strip() for p in parts if p.strip()]


def scan_text(text: str) -> list[dict]:
    """扫描文本，返回命中清单（按词长降序匹配，长词优先避免被短词吞并）"""
    hits = []
    words_by_len = sorted(PRONUNCIATION_RISK_WORDS, key=lambda w: len(w["word"]), reverse=True)
    for sentence in split_sentences(text):
        for entry in words_by_len:
            word = entry["word"]
            if word in sentence:
                hits.append({
                    "word": word,
                    "sentence": sentence,
                    "correct": entry["correct"],
                    "wrong": entry["wrong"],
                    "level": entry["level"],
                    "note": entry["note"],
                })
    return hits


def main() -> int:
    parser = argparse.ArgumentParser(description="多音字风险预检")
    parser.add_argument("input", help="口播稿文本文件路径（如 script/口播稿.txt）")
    parser.add_argument("--json", default=None, help="JSON 报告输出路径（默认写到 <input 同级 qa>/pronunciation-report.json）")
    parser.add_argument("--project", default=None, help="项目目录（快捷方式，等价于 --json <project>/qa/pronunciation-report.json）")
    args = parser.parse_args()

    text_path = Path(args.input)
    if not text_path.exists():
        print(f"[error] 文件不存在: {text_path}", file=sys.stderr)
        return 1
    text = text_path.read_text(encoding="utf-8")

    hits = scan_text(text)

    # 按风险等级排序：high > medium > low
    level_order = {"high": 0, "medium": 1, "low": 2}
    hits.sort(key=lambda h: level_order.get(h["level"], 9))

    # 控制台输出
    print(f"[pronunciation] 扫描 {text_path}，命中 {len(hits)} 处多音字风险\n")
    if hits:
        print(f"{'词':<8} {'等级':<6} {'建议读音':<14} {'常见误读':<10} 所在句")
        print("-" * 90)
        for h in hits:
            sentence = h["sentence"] if len(h["sentence"]) <= 26 else h["sentence"][:26] + "…"
            print(f"{h['word']:<8} {h['level']:<6} {h['correct']:<14} {h['wrong'] or '-':<10} {sentence}")
        print("\n处理建议：")
        print("  1) 改写口播稿换词规避；或")
        print("  2) 把风险词加入 scripts/tts.py 的 PRONUNCIATION_OVERRIDES（Azure 引擎生效）")
    else:
        print("未命中风险词，发音安全。")

    # JSON 报告
    out_path = None
    if args.json:
        out_path = Path(args.json)
    elif args.project:
        out_path = Path(args.project) / "qa" / "pronunciation-report.json"
    else:
        out_path = text_path.parent / "qa" / "pronunciation-report.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    report = {
        "source": str(text_path),
        "checkedAt": None,  # 占位，见下
        "total": len(hits),
        "byLevel": {lv: sum(1 for h in hits if h["level"] == lv) for lv in ("high", "medium", "low")},
        "hits": hits,
    }
    import datetime
    report["checkedAt"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[ok] 报告: {out_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
