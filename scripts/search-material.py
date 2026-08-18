#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
素材语义检索：CLIP 编码 + FAISS 向量检索
==========================================
用法：
  python scripts/search-material.py build [--force]    # 扫描素材库建索引
  python scripts/search-material.py search "思考的小布丁" [--type character|background|prop] [--emotion shocked] [--topk 5] [--image <path>] [--json]
  python scripts/search-material.py info               # 查看索引信息

说明：
  - 只索引 material-library.json 中 status=active 的素材
  - 双路索引：图片视觉 embedding + 元数据增强文本 embedding，检索时加权融合
  - 查询精确命中 id/名称/描述/标签时自动置顶（兼容旧版关键词检索）
  - 后端优先 FAISS(IndexFlatIP)，未安装时自动降级 numpy 点积（结果一致）
  - 索引产物存 shared/.clip-index/（不入库，可随时重建）
"""
import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIBRARY = ROOT / "shared" / "material-library.json"
INDEX_DIR = ROOT / "shared" / ".clip-index"
MODEL_NAME = "OFA-Sys/chinese-clip-vit-large-patch14"
EMBED_DIM = 768
TEXT_WEIGHT = 0.6   # 文本查询时：文本相似度权重
IMAGE_WEIGHT = 0.4  # 文本查询时：视觉相似度权重

# 情绪同义词：文本查询命中时，对对应情绪角色素材做加成（兜底 CLIP 对中文情绪词区分弱）
EMOTION_SYNONYMS = {
    "smile": ["微笑", "笑", "开心", "高兴", "友好"],
    "thinking": ["思考", "想", "琢磨", "托下巴", "冥思"],
    "explaining": ["讲解", "解释", "说明", "讲课", "手势", "教学"],
    "serious": ["严肃", "认真", "正经", "皱眉"],
    "worried": ["担心", "担忧", "焦虑", "不安", "紧张"],
    "shocked": ["惊讶", "震惊", "吃惊", "吓", "呆住", "嘴巴张"],
    "confused": ["困惑", "疑惑", "迷茫", "挠头", "不解", "问号"],
}

USE_FAISS = False
try:
    import faiss
    USE_FAISS = True
except ImportError:
    pass


# ---------------- 模型加载（惰性） ----------------
_model = None
_processor = None


def get_model():
    global _model, _processor
    if _model is None:
        import torch
        # macOS CPU 推理多线程偶发 segfault，固定单线程规避
        torch.set_num_threads(1)
        from transformers import ChineseCLIPModel, ChineseCLIPProcessor
        print(f"[clip] 加载模型 {MODEL_NAME} ...", file=sys.stderr)
        _model = ChineseCLIPModel.from_pretrained(MODEL_NAME)
        _processor = ChineseCLIPProcessor.from_pretrained(MODEL_NAME)
        _model.eval()
    return _model, _processor


# ---------------- 素材收集 ----------------
def load_active_assets():
    if not LIBRARY.exists():
        sys.exit(f"素材库不存在: {LIBRARY}")
    data = json.loads(LIBRARY.read_text(encoding="utf-8"))
    assets = []
    for group in ("characters", "backgrounds", "props"):
        for item in data.get(group, []):
            if item.get("status") != "active":
                continue
            fp = ROOT / item["filePath"]
            if not fp.exists():
                print(f"[skip] 文件缺失: {item['filePath']}", file=sys.stderr)
                continue
            assets.append({
                "id": item["id"],
                "type": item["type"],
                "name": item.get("name", ""),
                "emotion": item.get("emotion") or "",
                "action": item.get("action") or "",
                "filePath": item["filePath"],
                "contentDescription": item.get("contentDescription", ""),
                "tags": item.get("tags", []),
            })
    assets.sort(key=lambda a: a["id"])
    return assets


def enhance_text(a):
    """把素材元数据拼成供 CLIP 检索的增强文本"""
    parts = [a["name"], a["contentDescription"]]
    if a["tags"]:
        parts.append("标签：" + "、".join(a["tags"]))
    return "，".join(p for p in parts if p)


def open_rgb(path):
    from PIL import Image
    img = Image.open(path)
    if img.mode == "RGBA":
        bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
        bg.alpha_composite(img)
        img = bg.convert("RGB")
    else:
        img = img.convert("RGB")
    return img


# ---------------- 编码 ----------------
def encode_texts(model, processor, texts):
    import torch
    inputs = processor(text=list(texts), return_tensors="pt", padding=True)
    kwargs = {k: inputs[k] for k in ("input_ids", "attention_mask", "token_type_ids") if k in inputs}
    with torch.no_grad():
        feats = model.get_text_features(**kwargs)
    # transformers 5.x: 返回 BaseModelOutputWithPooling，pooler_output 即投影后向量
    if hasattr(feats, "pooler_output"):
        feats = feats.pooler_output
    return torch.nn.functional.normalize(feats, dim=-1).numpy()


def encode_images(model, processor, paths):
    import torch
    imgs = [open_rgb(p) for p in paths]
    inputs = processor(images=imgs, return_tensors="pt")
    with torch.no_grad():
        feats = model.get_image_features(pixel_values=inputs["pixel_values"])
    if hasattr(feats, "pooler_output"):
        feats = feats.pooler_output
    return torch.nn.functional.normalize(feats, dim=-1).numpy()


# ---------------- 索引读写 ----------------
def _index_path(tag):
    return INDEX_DIR / f"{tag}.index" if USE_FAISS else INDEX_DIR / f"{tag}.npy"


def save_index(tag, mat):
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    p = _index_path(tag)
    if USE_FAISS:
        idx = faiss.IndexFlatIP(mat.shape[1])
        idx.add(mat.astype("float32"))
        faiss.write_index(idx, str(p))
    else:
        import numpy as np
        np.save(p, mat)
    return p


def load_index(tag):
    p = _index_path(tag)
    if USE_FAISS:
        if not p.exists():
            return None
        idx = faiss.read_index(str(p))
        return idx.reconstruct_n(0, idx.ntotal)
    import numpy as np
    if not p.exists():
        return None
    return np.load(p)


def build(args):
    assets = load_active_assets()
    if not assets:
        sys.exit("没有可索引的 active 素材")
    model, processor = get_model()

    print(f"[build] 共 {len(assets)} 个素材，编码图片 embedding ...")
    img_emb = encode_images(model, processor, [ROOT / a["filePath"] for a in assets])
    print(f"[build] 编码增强文本 embedding ...")
    txt_emb = encode_texts(model, processor, [enhance_text(a) for a in assets])

    save_index("img", img_emb)
    save_index("txt", txt_emb)
    meta = {
        "model": MODEL_NAME,
        "backend": "faiss" if USE_FAISS else "numpy",
        "dim": EMBED_DIM,
        "count": len(assets),
        "assets": assets,
        "builtAt": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
    }
    (INDEX_DIR / "metadata.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"[build] 完成: {INDEX_DIR}/  (backend={meta['backend']}, count={meta['count']})")


def _load_meta():
    p = INDEX_DIR / "metadata.json"
    if not p.exists():
        sys.exit("索引不存在，请先运行: python scripts/search-material.py build")
    return json.loads(p.read_text(encoding="utf-8"))


def _fuse(txt_scores, img_scores, txt_w, img_w):
    """把两路 top-k 分数融合成统一的 (asset, score) 列表"""
    txt_map = {i: s for i, s in txt_scores}
    img_map = {i: s for i, s in img_scores}
    all_idx = set(txt_map) | set(img_map)
    out = []
    for i in all_idx:
        s = txt_w * txt_map.get(i, 0.0) + img_w * img_map.get(i, 0.0)
        out.append((i, s))
    out.sort(key=lambda x: -x[1])
    return out


def exact_match(query, assets):
    """旧版关键词匹配能力：id/名称/描述/动作/标签 包含查询即命中（语义检索前置兜底）"""
    hits = []
    for i, a in enumerate(assets):
        hay = " ".join([a["id"], a["name"], a["emotion"], a["action"],
                        a["contentDescription"], " ".join(a["tags"])])
        if query and query in hay:
            hits.append(i)
    return hits


def query_boost(query, assets):
    """查询关键词命中加成：名称直配 + 情绪同义词，返回 {idx: delta}"""
    boosts = {}
    for i, a in enumerate(assets):
        delta = 0.0
        if a["name"] and a["name"] in query:
            delta += 0.12
        for syn in EMOTION_SYNONYMS.get(a["emotion"] or "", []):
            if syn in query:
                delta += 0.15
                break
        if delta:
            boosts[i] = delta
    return boosts


def search(args):
    meta = _load_meta()
    assets = meta["assets"]
    model, processor = get_model()

    img_emb = load_index("img")
    txt_emb = load_index("txt")
    if img_emb is None or txt_emb is None:
        sys.exit("索引缺失，请重新运行 build")

    import numpy as np
    if args.image:
        query_emb = encode_images(model, processor, [args.image])[0]
        txt_w, img_w = 0.3, 0.7  # 图搜图：视觉权重更高
        mode = f"图搜图: {args.image}"
        boosts = {}
    else:
        query_emb = encode_texts(model, processor, [args.query])[0]
        txt_w, img_w = TEXT_WEIGHT, IMAGE_WEIGHT
        mode = f"文本检索: {args.query}"
        boosts = query_boost(args.query, assets)
        for i in exact_match(args.query, assets):  # 精确命中直接置顶
            boosts[i] = boosts.get(i, 0.0) + 0.25

    txt_scores = [(int(i), float(s)) for i, s in enumerate(txt_emb @ query_emb)]
    img_scores = [(int(i), float(s)) for i, s in enumerate(img_emb @ query_emb)]

    fused = _fuse(txt_scores, img_scores, txt_w, img_w)
    if boosts:
        fused = [(i, s + boosts.get(i, 0.0)) for i, s in fused]
        fused.sort(key=lambda x: -x[1])
    filtered = [x for x in fused if not args.type or assets[x[0]]["type"] == args.type]
    if args.emotion:
        filtered = [x for x in filtered if assets[x[0]]["emotion"] == args.emotion]
    results = filtered[: args.topk]

    rows = []
    for i, s in results:
        a = assets[i]
        rows.append({
            "rank": len(rows) + 1,
            "score": round(float(s), 4),
            "id": a["id"],
            "type": a["type"],
            "name": a["name"],
            "emotion": a["emotion"],
            "filePath": a["filePath"],
        })
    if args.json:
        print(json.dumps({"mode": mode, "results": rows}, ensure_ascii=False, indent=2))
        return
    print(f"== {mode} (top {len(rows)}) ==")
    for r in rows:
        print(f"  #{r['rank']} [{r['score']:.3f}] {r['type']}/{r['name']}"
              f"{('·' + r['emotion']) if r['emotion'] else ''}  ->  {r['filePath']}")


def info(args):
    meta = _load_meta()
    print(f"模型: {meta['model']}")
    print(f"后端: {meta['backend']}")
    print(f"素材数: {meta['count']}")
    print(f"索引路径: {INDEX_DIR}/")
    from collections import Counter
    c = Counter(a["type"] for a in meta["assets"])
    print("类型分布:", dict(c))


def main():
    ap = argparse.ArgumentParser(description="素材语义检索（CLIP + FAISS）")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="扫描素材库建立索引")
    b.add_argument("--force", action="store_true", help="强制重建（默认已存在则跳过）")
    b.set_defaults(func=build)
    s = sub.add_parser("search", help="检索素材")
    s.add_argument("query", nargs="?", default=None, help="中文描述，如「思考的小布丁」；精确命中 id/名称/标签会置顶")
    s.add_argument("--type", choices=["character", "background", "prop"], default=None)
    s.add_argument("--emotion", default=None, help="按情绪过滤，如 shocked / thinking")
    s.add_argument("--topk", type=int, default=5)
    s.add_argument("--image", default=None, help="图搜图：传入图片路径")
    s.add_argument("--json", action="store_true", help="输出 JSON")
    s.set_defaults(func=search)
    i = sub.add_parser("info", help="索引信息")
    i.set_defaults(func=info)
    args = ap.parse_args()

    if args.cmd == "build" and not args.force and (INDEX_DIR / "metadata.json").exists():
        print(f"索引已存在（{INDEX_DIR}/），如需重建请加 --force")
        return
    args.func(args)


if __name__ == "__main__":
    main()
