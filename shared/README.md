# 共享素材库使用规范

## 目录职责

| 目录 | 用途 |
|------|------|
| `characters/` | 角色素材（透明底 PNG），只存放通过检查的正式素材 |
| `backgrounds/` | 背景素材（不抠图，仅交代地点和气氛） |
| `props/` | 道具素材（透明底 PNG） |
| `_generate/` | 新生成待检查的素材，检查通过后移动到正式目录并登记 |
| `_retired/` | 淘汰素材（水印、绿边、错误角色/内容），永久不可检索 |

## 素材状态流转

```
生成 → _generate/ (generating)
  → 人工检查
      ├─ 通过 → characters|backgrounds|props/ (active) + 登记 material-library.json
      └─ 不合格 → _retired/ (retired) ← 后续项目检索不到
```

## material-library.json 登记规范

每项素材必须登记以下字段：

```json
{
  "id": "唯一ID，如 char_crabby_happy_01",
  "type": "character | background | prop",
  "name": "角色/对象名，如 蟹老板",
  "emotion": "情绪（角色）如 happy / nervous",
  "action": "动作描述，如 standing / pointing",
  "filePath": "相对 shared/ 的路径",
  "status": "active | generating | pending_review | retired",
  "contentDescription": "图片实际内容的描述（人物是谁、在做什么、画面里有什么）",
  "tags": ["标签1", "标签2"],
  "createdAt": "2026-08-17",
  "usageCount": 0
}
```

## 命名规范

- 角色：`char_{角色名}_{情绪}_{序号}.png`
- 背景：`bg_{场景名}_{序号}.png`
- 道具：`prop_{道具名}_{序号}.png`

## 语义检索（CLIP + FAISS）

素材库支持语义检索（中文自然语言/图片找图），由 `scripts/search-material.py` 提供：

```bash
# 1. 建索引（素材增删后需重建）
./.venv/bin/python scripts/search-material.py build

# 2. 文本检索（中文描述，语义匹配）
./.venv/bin/python scripts/search-material.py search "思考中的小布丁"
./.venv/bin/python scripts/search-material.py search "惊讶的表情" --type character
./.venv/bin/python scripts/search-material.py search "超市" --topk 3 --json

# 3. 图搜图（视觉相似素材）
./.venv/bin/python scripts/search-material.py search "图" --image shared/props/prop_零食袋.png

# 4. 查看索引信息
./.venv/bin/python scripts/search-material.py info
```

要点：

- 只检索 `status=active` 的素材，`retired` 永远搜不到
- 模型：`OFA-Sys/chinese-clip-vit-large-patch14`（首次自动下载，约 1.2GB 到 HF 缓存）
- 双路索引：图片视觉 embedding + 元数据增强文本 embedding 加权融合
- 查询精确命中 id/名称/标签时自动置顶（兼容旧版关键词检索）
- 索引产物在 `shared/.clip-index/`（不入库，随时可重建）；素材入库后记得重新 `build`

## 关键规则

1. 文件名只能帮助人快速浏览，**内容描述字段才是检索依据**
2. 素材被替换后，必须更新 `material-library.json` 中的描述和时间轴引用
3. 同一角色跨剧情转折不能复用同一张图（如开心蟹老板不能继续充当害怕的蟹老板）
4. 复用率不是目标，**语义准确才是**——一张错误的旧图会毁掉整段故事
