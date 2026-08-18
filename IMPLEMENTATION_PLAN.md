# AI 科普短视频自动化生产流水线 — 实施计划

> 来源：[@zq4495 榴莲](https://x.com/zq4495/status/2088111639879163946) 的「海绵宝宝经济学」实战复盘
> 战绩：新号 4 天 3 万曝光，6 条视频，纯自然流，入选抖音精选

---

## 一、原推文核心信息总结

### 1.1 这套流程做了什么

用 AI 自动化生产 **60 秒左右的科普解说视频**，核心特点是：
- 借用熟悉 IP 角色（如海绵宝宝、蟹老板）讲知识概念（如「什么是洗钱」）
- 画面、旁白、字幕严格同步——旁白说蟹老板倒卖珍珠，画面里就同时出现蟹老板、交易状态和珍珠
- 输入一个主题或一条参考视频，自动走完从脚本到成片的全流程

### 1.2 核心设计原则（原文反复强调）

| 原则 | 说明 |
|------|------|
| **单一信息源** | 口播稿是源文件，字幕、时间轴、画面描述全部从它派生。改一个地方，下游全部自动重新生成 |
| **先审画面再做配音** | 静态融合预览通过后才生成声音，避免改画面导致配音返工 |
| **按语义拆画面，不按秒数** | 新人物出现、动作改变、关键对象更换时才切画面，不是每 5 秒切一刀 |
| **先查素材库再生图** | 共享素材库只维护一份正式素材，复用优先，缺了才补 |
| **声音决定时间** | 配音返回词语时间戳，字幕和画面动画都跟着音频走 |
| **渲染后四遍检查** | 技术检查 + 语义审片 + 构图抽查 + 时间对齐 |

### 1.3 关键数据点

- 成片规格：1080×1920（竖屏 9:16）/ 30fps / H.264，时长约 65.75 秒
- 一条 65 秒视频涉及 66 次素材引用，去重后 26 项独立素材
- 新号 6 条视频累计播放破 3 万，零投流

---

## 二、12 步流水线详解

### Phase 1: 搭建与拆解

#### 00 — 工作台目录结构

```
videoShort/
├── 01_教程资料/              # 制作规范和参考案例
├── 02_项目/                  # 每条视频一个子目录
│   └── C005_什么是洗钱/
│       ├── data/             # 机器读的 JSON（source of truth）
│       │   ├── reference-analysis.json   # 参考视频分析结果
│       │   ├── project-plan.json         # 故事计划（口播+画面任务+素材预览）
│       │   ├── scene-config.json         # 场景配置（渲染前）
│       │   └── timeline.json             # 时间轴（声音合入后生成）
│       ├── script/            # 人读的 markdown
│       │   ├── 视觉设计说明.md
│       │   └── 故事脚本与画面审核稿.md
│       ├── audio/            # 配音 + 字幕草稿
│       ├── qa/               # 质检产物
│       │   ├── story-review/  # 融合预览图
│       │   ├── final-frames/  # 抽帧
│       │   └── semantic-alignment-report.json
│       └── deliverables/     # 最终成片 + 封面
├── shared/                   # 共享素材库
│   ├── characters/           # 角色（透明底 PNG）
│   ├── backgrounds/          # 背景
│   ├── props/                # 道具
│   ├── _generate/            # 待审素材
│   ├── _retired/             # 淘汰素材
│   └── material-library.json # 素材索引（路径+标签+内容描述+状态）
├── scripts/                  # 处理脚本（转写/编译/素材/质检）
├── remotion/                 # Remotion 渲染组件
├── assets/                   # 通用模板与字体
└── tests/                    # 测试（时间/字幕/素材/片尾规则）
```

**关键规则**：
- 同一份信息只出现在一个源文件里，其余文件都从它派生
- 素材先进入 `_generate/`，检查通过后登记到 `material-library.json` 才算正式
- 水印、绿边、错误角色进入 `_retired/`，后续项目检索不到

#### 01 — 参考视频拆解

**输入**：一条参考视频 或 一个主题

**流程**：
1. 提取音频 → 转写文字（Whisper 本地部署 / Paraformer 中文更优）
2. 第一轮只做校对，还原声音里的真实内容，不改稿
3. 保留四类信息：原句、人物、具体例子、信息节奏
4. 产物：`reference-analysis.json`（一页纸：开场方法、故事冲突、解释顺序、结尾记忆点）

**如果只输入主题**：Codex 先判断题目大小，收成一条视频能讲清的问题

---

### Phase 2: 内容创作

#### 02 — 一条视频只回答一个问题

**三条检查**：
1. **因果链检查**：把关键词（如「洗钱」）拿掉，读者还能复述故事吗？能 = 因果写顺了
2. **事实检查**：涉及法律/金融/科学的内容，定义和行为边界不能跟着剧情随便变
3. **口语化检查**：完整念一遍，卡住的地方说明不够口语；删掉字幕后声音本身也能讲明白故事

**产物**：`project-plan.json` → 生成 `script/故事脚本.md`（口播 + 画面任务 + 素材预览排在一起，方便一次审完）

#### 03 — 按新信息拆画面

**分镜写法对比**：

| 错误写法（人能看懂，程序不知道找什么图） | 正确写法（明确当前人物/动作/对象/状态） |
|---|---|
| 蟹老板出现、展示黑钱、展示账本 | 画面1: 蟹老板(紧张) + 黑钱袋(桌上) + 状态=交易中 |

**拆分原则**：
- 不按固定秒数切，而是按信息变化切：新人物出现、动作改变、关键对象更换、因果推进
- 口播继续解释同一件事时，画面可以多停一会儿
- 好处：文案改动后可以快速定位受影响的画面，不用全部重做

---

### Phase 3: 素材生产

#### 04 — 先查素材库，再决定要不要生图

**检索策略**（两层）：
1. 精确标签匹配（名字 + 动作 + 情绪）
2. 多模态相似度（找文字描述不一致的近义素材）

**素材状态流转**：
```
found → checked → registered → in-use
                                ↓
                           retired（淘汰）
```

**关键**：一张错误的旧图会让整段故事失去连贯性，复用率不是目标，准确才是

#### 05 — 角色 / 背景 / 道具分开处理

| 类型 | 推荐工具 | 要点 |
|------|----------|------|
| 熟悉角色（海绵宝宝等） | 参考图生成 / 规范角色库 | 同一段故事里造型必须一致 |
| 背景 | GPT Image / Flux | 不抠图，只交代地点和气氛 |
| 道具 | GPT Image / Flux | 需要透明底，补上"独立道具、主体完整、边缘清楚" |

**抠图工具对比**：
- rembg：接入批处理快
- BiRefNet：复杂轮廓与细线更好
- 卡通角色常见问题：手指间空洞、睫毛、白色边缘 → 抠图后还要再查遮罩

**素材交付**：原图 + 透明图 + 用途说明 互相能找到

---

### Phase 4: 画面与审稿

#### 06 — 先摆静态画面，再加动画

**画面四层结构**：
1. 背景层（地点/气氛）
2. 角色层（叙事主体）
3. 道具层（关键对象）
4. 字幕层（文字辅助）

**常用布局（三种够用）**：
- 左右构图：人物一边，道具另一边，中间留空隙
- 中心聚焦：单一视觉重点
- 对比构图：左右两组道具做因果对比

**动画原则**：
- 关掉字幕后能看出当前在讲什么 → 静态画面通过
- 角色的脸、手、关键道具没被遮挡 → 通过后才加动画
- 动画服务信息顺序：角色先出现（认人）→ 道具后进入（补因果）→ 旧对象退出后新对象才占位
- 不要堆满动作，持续旋转/缩放/摇晃会抢走注意力

#### 07 — 先审融合画面，再做配音

**为什么**：单独看脚本和素材，很多构图问题发现不了

**做法**：
1. 每个语义画面生成一张融合预览（背景 + 角色 + 道具 + 字幕位置）
2. 预览图集中放在 `qa/story-review/`
3. 逐张检查：口播说的是否和画面内容匹配
4. 通过后再看全片联系表：检查背景用太久、表情连续重复、道具颜色太接近

**审稿不通过时的处理**：
- 口播不清楚 → 回故事稿改
- 素材内容不准 → 重新检索/生成
- 只有构图问题 → 在画面里调位置
- 不要把所有问题都交给排版解决

---

### Phase 5: 声音与交付

#### 08 — 让声音决定字幕和画面时间

**配音工具对比**：
| 工具 | 优势 | 适用 |
|------|------|------|
| 云 TTS | 省部署，中文音色丰富 | 快速上手 |
| CosyVoice | 本地控制，可继续调试 | 需要定制 |

**时间信息传递链**：
```
voice.mp3 → 词语时间戳 → timeline.json → 字幕时间 + 画面动画时间
```

**字幕规则**：
- 只显示当前短句，自然断句时上一块消失、下一块出现
- 标点负责声音停顿，不占画面
- 配音改动后，旧字幕和画面时间全部失效，从新音频重新生成

#### 09 — 用 Remotion 统一画面、字幕和声音

**为什么不用 FFmpeg 直接合成**：
- 画面有大量 React 组件、动态字幕、图层动画时，Remotion 调试更直观
- 可以在浏览器里逐帧查看
- FFmpeg 适合转码和规则清楚的媒体操作

**时间轴只保留一套**：旁白、字幕、背景音乐、音效、画面元素都进入同一个 composition

**场景配置**：
```json
{
  "sceneId": "S06",
  "background": " underwater_restaurant.png",
  "elements": [
    { "type": "character", "name": "蟹老板", "emotion": "nervous", 
      "enterFrom": "left", "duration": [2.5, 8.3], "zIndex": 2 },
    { "type": "prop", "name": "账本", 
      "enterFrom": "right", "duration": [4.0, 8.3], "zIndex": 3 }
  ],
  "subtitle": { "text": "蟹老板开始伪造账本", "style": "bottom-center" }
}
```

#### 10 — 片头、片尾和封面分别处理

| 部分 | 作用 | 内容 |
|------|------|------|
| 片头 | 告诉观众时长和主题 | 不急着塞角色，先认清主题 |
| 片尾 | 问答复习 | 提出概括全文的问题 → 显示答案 → 旁白念完 → 黑板停留到最后一帧 |
| 封面 | 信息流点击 | 可共用字体/角色/色彩，构图独立制作 |

#### 11 — 渲染成功后做四遍检查

| 检查 | 内容 | 产物 |
|------|------|------|
| 技术检查 | 时长、音频、首末帧 | 自动报告表 + `qa/final-frames/` |
| 语义审片 | 逐句对照口播和画面内容 | `qa/semantic-alignment-report.json` |
| 构图抽查 | 遮挡、边缘、字幕覆盖 | 人工 |
| 时间对齐 | 声音结束 vs 画面结束、动作 vs 口播 | 人工 |

---

## 三、工具栈一览

| 层 | 工具 | 用途 | 替代方案 |
|----|------|------|----------|
| 编排 | Codex / Claude Code | 脚本生成 + 任务调度 + 事实检查 | 任何能读写文件的 AI coding agent |
| 转写 | Whisper (本地) / Paraformer | 音频→文字 + 时间戳 | faster-whisper |
| 生图 | WorkBuddy ImageGen | 角色 / 背景 / 道具 / 封面底图 | Midjourney / Flux |
| 抠图 | rembg / BiRefNet | 透明底素材 | remove.bg API |
| 配音 | Azure TTS / Edge-TTS | 旁白 + 句子级时间戳（100ns tick） | 云 TTS / CosyVoice |
| 渲染 | Remotion (React) | 画面+字幕+声音合成 | FFmpeg + Python 脚本 |
| 转码 | FFmpeg | 格式转换 + 封装 | 无替代 |
| 素材检索 | 精确标签 + 多模态相似度 | 复用已有素材 | CLIP + FAISS |

---

## 四、实施路线图

### 阶段 0：环境搭建（1-2 天）

**目标**：跑通最小可用骨架

- [ ] 初始化项目目录结构（按 00 步的模板）
- [ ] 安装 Node.js + Remotion，创建空 composition
- [ ] 安装 Python 环境 + faster-whisper
- [ ] 准备一个 TTS 方案（先用免费的 Edge-TTS 跑通）
- [ ] 安装 rembg（pip install rembg）
- [ ] 创建 `material-library.json` 空文件

**验证**：Remotion 能渲染一个静态文字 + 背景色的 5 秒视频

### 阶段 1：单条视频跑通（3-5 天）

**目标**：手动走完 12 步，产出第一条 60 秒视频

**选题建议**：选一个你熟悉的概念，不要太复杂。例如「什么是通货膨胀」「为什么会有通货膨胀」

- [ ] **02 脚本**：手写一份 60 秒口播稿（约 180 字），确保因果链清晰
- [ ] **03 分镜**：手动拆成 8-12 个语义画面，每个写清人物/动作/对象/状态
- [ ] **04-05 素材**：用 GPT Image 生成 5-8 个角色和道具 PNG，rembg 抠图
- [ ] **06 静态画面**：在 Remotion 里摆好每个场景的静态构图
- [ ] **07 预览**：用 Remotion 的 `stillFrame` 导出每个场景的静态预览图
- [ ] **08 配音**：Edge-TTS 生成音频 + Whisper 提取词语时间
- [ ] **09 合成**：时间轴合入 Remotion，加字幕和简单动画
- [ ] **10 片头片尾**：加标题卡和结尾问答
- [ ] **11 检查**：手动过四遍检查

**验证**：一条 1080×1920 / 30fps 的 MP4 成片

### 阶段 2：脚本化处理链（5-7 天）

**目标**：把手动步骤变成可复用的脚本

- [ ] 写 `scripts/transcribe.py`：音频→文字+时间戳
- [ ] 写 `scripts/generate-story.py`：主题→project-plan.json（用 AI API）
- [ ] 写 `scripts/search-material.py`：标签+多模态检索素材库
- [ ] 写 `scripts/generate-preview.py`：批量导出场景静态预览图
- [ ] 写 `scripts/build-timeline.py`：音频时间→timeline.json
- [ ] 写 `scripts/semantic-check.py`：口播 vs 画面对齐检查
- [ ] Remotion 组件库：片头/正文场景/片尾/字幕条 封装成可复用组件

**验证**：输入主题 → 自动生成 project-plan.json → 手动确认后 → 一键渲染

### 阶段 3：素材库积累与自动化（持续）

**目标**：第二条视频开始复用第一条的素材

- [ ] 完善素材检索：CLIP 向量 + FAISS 索引
- [ ] 角色一致性：建立规范角色库（同一角色的多情绪/多动作版本）
- [ ] 批量生产：一次生成一周的脚本，逐条审核后批量渲染
- [ ] 封面模板：根据标题自动生成 3:4 抖音封面
- [ ] 质检自动化：渲染后自动跑技术检查 + 语义检查，生成报告

**验证**：第二条视频的素材复用率 > 40%，生产时间从 3 天缩短到 1 天

---

## 五、技术选型建议（针对你的情况）

### 推荐起步方案（零成本快速验证）

| 步骤 | 工具 | 理由 |
|------|------|------|
| 编排 | WorkBuddy / Claude Code | 直接在当前项目里用 |
| 转写 | faster-whisper (small 模型) | 本地跑，免费 |
| 生图 | GPT Image (通过 API) 或 Flux 本地 | 质量好，可控 |
| 抠图 | rembg | 一行命令 |
| 配音 | Edge-TTS (免费) → 后续换 CosyVoice | 零成本起步 |
| 渲染 | Remotion | 原文验证过，浏览器可预览 |
| 转码 | FFmpeg | Remotion 自带调用 |

### 关于 IP 版权

原文也提到了：**使用现有 IP 做公开发布和商业化时，要确认素材来源、平台规定和授权范围。**

建议：
1. 起步阶段用原创角色（AI 生成的卡通形象），降低版权风险
2. 流程跑通后再考虑是否使用熟悉 IP
3. 发布到抖音/B站时注意平台对 AI 生成内容的标注要求

---

## 六、关键文件格式参考

### project-plan.json（故事计划，source of truth）

```json
{
  "videoId": "C005",
  "title": "什么是洗钱",
  "duration": 65.75,
  "narration": "蟹老板赚了一笔来路不明的钱...",
  "scenes": [
    {
      "sceneId": "S01",
      "narrationSegment": "蟹老板赚了一笔来路不明的钱",
      "characters": [{"name": "蟹老板", "emotion": "happy"}],
      "props": [{"name": "钱袋", "state": "full"}],
      "background": "蟹堡王餐厅内部",
      "layout": "center-focus"
    }
  ]
}
```

### material-library.json（素材索引）

```json
[
  {
    "id": "char_crabby_happy_01",
    "type": "character",
    "name": "蟹老板",
    "emotion": "happy",
    "action": "standing",
    "filePath": "shared/characters/crabby_happy_01.png",
    "status": "active",
    "contentDescription": "蟹老板开心站立，双手举起"
  }
]
```

### timeline.json（时间轴，配音后生成）

```json
{
  "totalDuration": 65.75,
  "audioFile": "audio/voice.mp3",
  "scenes": [
    {
      "sceneId": "S01",
      "start": 0.0,
      "end": 5.3,
      "subtitle": {"text": "蟹老板赚了一笔来路不明的钱", "start": 0.2, "end": 5.1}
    }
  ]
}
```

---

## 七、风险与注意事项

| 风险 | 对策 |
|------|------|
| 同一信息出现在多个文件里 | 严格单一源文件原则，下游文件检测到上游变化就重新生成 |
| 角色造型不一致 | 维护规范角色库，同一段故事只用同一套参考图 |
| 字幕和声音不同步 | 必须用词语时间戳，不能用总时长平均分配 |
| AI 生成图片有水印/绿边 | 进入 `_retired/` 淘汰，不登记到素材库 |
| 口播和画面语义不匹配 | 渲染后做语义审片，逐句对照 |
| 片尾声音还没结束画面就消失 | 检查最后一帧状态，黑板停留到最后一帧 |

---

## 八、阶段一执行记录（已跑通）

### 8.1 已交付成果

- 示例项目：`02_项目/C001_示例项目/`
- 成片：`02_项目/C001_示例项目/deliverables/C001_成片.mp4`
  - 规格：1080×1920 / 30fps / H.264
  - 时长：33.7 秒（片头 3s + 正文 25.6s + 片尾 5s）
- 技术检查：✅ 通过（ffprobe 验证时长/编码/分辨率/帧率/音轨）
- 语义检查：⚠️ 2 条 warning（S02/S03 口播提到「钱」但场景未配置钱袋/钞票/金币道具），不影响渲染

### 8.2 关键踩坑与修复

| 问题 | 根因 | 修复方式 |
|------|------|----------|
| 渲染时静态文件 404 | Remotion 4 渲染时 `remotion_staticBase = "./public"`，`staticFile()` 会自动拼成 `/public/test.png`；组件直接写 `/test.png` 会指向 bundle 根目录而文件实际在 `outDir/public/` | 所有 `Img` / `Audio` 路径统一用 `staticFile()` / 自定义 `staticPath()` 包裹 |
| 片尾凭空出现，正文被拉长 | `registerRoot()` 注册的根组件**不会**直接收到程序化渲染传入的 `inputProps`，`props.timeline` 始终 fallback 到空时间轴 | 在 `Root.tsx` 中用 `getInputProps()` 读取外部输入 |
| 嵌套 Sequence 时间基准错误 | 嵌套 `Sequence` 的 `from` 是相对父 `Sequence` 的起始帧；`NarrationScene` 内 `useCurrentFrame()` 返回的是**场景 Sequence 内的相对帧**，但 `sceneOpacity` / `Character` / `Prop` 动画仍按绝对秒数 `scene.start*fps` 计算，导致 S02/S03/S04 等场景的透明度与动画全部失效 | 子场景 `from` 改为 `scene.start * fps`（相对正文 Sequence）；`NarrationScene` 内所有动画改用场景相对帧：`sceneOpacity` 关键帧改为 `[0, fps*0.2, sceneDurationFrames-fps*0.2, sceneDurationFrames]`；`Character` / `Prop` 的 `duration` 传入 `[0, scene.end-scene.start]` |
| 浏览器打包失败 | 素材解析代码在组件里用了 Node `fs`，webpack 无法打包 | 把素材解析拆到 Node 渲染脚本 `render.mjs`，解析结果内嵌进 `timeline.json` |

### 8.3 已验证命令

```bash
# 生成配音
python scripts/tts.py "02_项目/C001_示例项目/script/口播稿.txt" "02_项目/C001_示例项目/audio"

# 构建时间轴
python scripts/build-timeline.py "02_项目/C001_示例项目"

# 生成占位素材
python scripts/gen-placeholder.py

# 渲染完整视频
node scripts/render.mjs "02_项目/C001_示例项目"

# 检查
python scripts/tech-check.py "02_项目/C001_示例项目/deliverables/C001_成片.mp4"
python scripts/semantic-check.py "02_项目/C001_示例项目"
```

---

## 九、阶段二执行记录（已跑通）

### 9.1 目标

输入主题 → 自动生成 `project-plan.json` → 手动确认口播稿后 → 一键渲染成片。

### 9.2 新增脚本与优化

| 脚本 | 作用 |
|------|------|
| `scripts/generate-story.py` | 主题/已有口播稿 → `project-plan.json` + `scene-config.json` + `script/故事脚本.md` + `script/口播稿.txt` |
| `scripts/generate-preview.py` | 批量导出 `qa/story-review/` 场景静态预览图 |
| `scripts/pipeline.sh` | 一键流水线：`new/script/voice/timeline/preview/render/check/all/list` |
| `scripts/build-timeline.py` | 优化为**句子边界精确对齐**：edge-tts 的 `wordBoundaries` 作为 SentenceBoundary，直接用于场景起止时间 |

### 9.3 验证流程

```bash
# 1) 创建新项目（模板模式：先生成骨架，再人工打磨）
./scripts/pipeline.sh new "为什么超市里的东西总是越来越贵"

# 2) 打磨 script/口播稿.txt（或把写好的稿子通过 from-script 模式反生成场景）
python scripts/generate-story.py \
  "为什么超市里的东西总是越来越贵" \
  "02_项目/C002_超市涨价" \
  --mode from-script --input-file my_script.txt --video-id C002 --overwrite

# 3) 一键成片：配音 → 时间轴 → 渲染 → 检查
./scripts/pipeline.sh all "02_项目/C002_超市涨价"
```

### 9.4 C002 验证结果

- 成片：`02_项目/C002_超市涨价/deliverables/C002_成片.mp4`
  - 规格：1080×1920 / 30fps / H.264
  - 时长：43.0 秒（片头 3s + 正文 34.9s + 片尾 5s）
- 5 个场景、175 字口播、句子边界精确对齐（总时长 34.944s 与配音完全一致）
- 技术检查：✅ 通过
- 语义检查：⚠️ 1 条 warning（S01 提到「十块钱」但场景道具为「超市货架」，可微调）
- 预览图：`qa/story-review/S01_start.png` … `S05_start.png`

### 9.5 视觉升级（治愈卡通插画风格）

为改善此前占位图导致的"demo 感"，对 C002 进行了第一轮视觉升级：

- **AI 生成素材**：
  - 背景：`bg_town.png`（小镇街道）、`bg_market.png`（超市内部）
  - 角色：`char_小明_smile.png`（Q 版小男孩，rembg 抠图）
  - 道具：`prop_钱袋.png`、`prop_超市货架.png`、`prop_工资条.png`
- **素材同步**：将 `public/shared` 改为符号链接指向 `shared/`，新素材生成后自动对渲染可见，避免 404
- **组件升级**：
  - 字幕：描边大字 + 渐变胶囊底 + 柔和阴影
  - 片头：小镇背景 + 暖色遮罩 + 标题卡片 + 频道/时长标签
  - 片尾：暖橙渐变 + 白色问答卡片
  - 正文：上下渐变遮罩替代生硬黑压层；角色/道具改为绝对定位 + 柔和投影
- **构图稳定**：角色默认居左、道具默认居右，形成固定左右构图

### 9.6 关键改进

- **句子级时间对齐**：edge-tts 7.x 返回 `SentenceBoundary`，其 `offset/duration` 以 100ns 为单位；当场景数与句子边界数一致且文本前 6 字匹配时，场景起止直接使用配音时间，彻底消除字数估算带来的尾部空白。
- **双模式剧本生成**：LLM 模式（API key）+ `from-script` 模式（人写稿）+ `template` 模式（骨架占位），兼容有/无 API key 两种环境。
- **静态预览图审稿**：每个场景在正文 Sequence 内的起始帧生成预览，支持先审画面再做配音流程（`preview` 命令可单独跑）。

## 十、生态内化与 C003 跑通（已完成）

### 10.1 技术路线最终确定

根据用户要求，整条流水线已调整为**全部在 WorkBuddy 生态内完成**，仅在配音环节允许外部 Azure 资源兜底：

| 环节 | 方案 | 说明 |
|------|------|------|
| **文案 / 口播稿** | WorkBuddy（当前 Agent） | 我直接产出 `project-plan.json` + `scene-config.json` + `口播稿.txt` + `故事脚本.md`；无需 OPENAI / DEEPSEEK 等外部 LLM API key |
| **图片素材** | WorkBuddy ImageGen | 角色 / 背景 / 道具全部生态内生图 |
| **封面图** | WorkBuddy ImageGen + Pillow | 先生成 3:4 封面底图，再叠加标题 / 标签文字 |
| **语音合成** | Azure Speech SDK（推荐）| `scripts/tts.py` 新增 `--engine azure`：SSML + WordBoundary 词级边界 → 段落聚合为句子级，与 build-timeline 精确对齐；需 `AZURE_SPEECH_KEY` + `AZURE_SPEECH_REGION` |
| **语音兜底** | edge-tts | 无 Azure key 时 `auto` 模式自动回退，仍保持段落级对齐 |
| **渲染 / 质检** | Remotion + 自研脚本 | 完全本地 |

### 10.2 关键改动

1. **`scripts/tts.py` 双引擎化**
   - `--engine auto|azure|edge`；`auto` 检测到 `AZURE_SPEECH_KEY` + `AZURE_SPEECH_REGION` 就用 Azure
   - Azure 输出 `Audio48Khz192KBitRateMonoMp3`，音质优于 edge-tts
   - **段落聚合**：tts.py 按口播稿空行分段（一段 = 一个场景），将词级/句子级边界聚合为段落级边界，彻底解决了口播中问句导致边界数 > 场景数、精确对齐失败的问题

2. **`scripts/pipeline.sh` 加载 `.env` + 引擎参数**
   - `voice` 命令：`pipeline.sh voice <项目> [engine] [音色]`
   - 自动 `source .env`，Azure key/region 走环境变量

3. **配置驱动的画面元素**
   - `scene-config.json` 的 `scenes[].background` 决定背景（`build-timeline.py` → `timeline.json` → `render.mjs` 解析）
   - `scenes[].subtitle.highlights` 决定每句字幕的关键词高亮，`NarrationScene.tsx` 已移除硬编码

4. **C003 项目：WorkBuddy 产稿示例**
   - 目录：`02_项目/C003_工资与物价/`
   - 主题：为什么工资总涨不过物价
   - 5 场景 / 261 字 / 配音 53.1s / 成片 61.2s
   - 角色情绪：thinking → explaining → serious → worried → explaining
   - 道具：钱袋 → 物价牌 → 超市货架 → 工资条 → 钱袋
   - 背景：小镇 → 超市 → 超市 → 小镇 → 小镇
   - 字幕关键词高亮按场景配置：工资/一百块、物价/购买力、成本/商品价格、加薪/慢半拍、让钱生钱/长期办法

### 10.3 C003 验证结果

- 成片：`02_项目/C003_工资与物价/deliverables/C003_成片.mp4`
- 封面：`02_项目/C003_工资与物价/deliverables/C003_封面.jpg`
- 规格：1080×1920 / 30fps / H.264 / 61.184s
- 配音引擎：edge（当前未配置 Azure key）
- 技术检查：✅ 通过
- 语义检查：✅ 5 场景，0 条告警
- 黑屏检测：✅ 无黑屏
- 时间轴对齐：✅ aligned（5 段落边界 = 5 场景）

### 10.4 新增/改动文件

```text
.env.example                          # Azure 配置模板
scripts/tts.py                        # Azure + Edge 双引擎 + 段落聚合
scripts/pipeline.sh                   # 加载 .env，voice 命令支持 engine 参数
scripts/build-timeline.py             # 透传 backgroundName 与 subtitle.highlights
remotion/src/lib/types.ts             # TimelineScene 新增 backgroundName / highlights
remotion/src/scenes/NarrationScene.tsx# 删除硬编码 highlights，改读场景配置
02_项目/C003_工资与物价/data/*        # WorkBuddy 产出的项目文件
02_项目/C003_工资与物价/script/*
02_项目/C003_工资与物价/deliverables/*
```

### 10.5 切换到 Azure TTS

1. 复制配置模板并填入 Azure 语音服务 key/region：
   ```bash
   cp .env.example .env
   # 编辑 .env：AZURE_SPEECH_KEY=xxx  AZURE_SPEECH_REGION=eastasia
   ```
2. 执行时显式指定引擎，或让 `auto` 自动检测：
   ```bash
   ./scripts/pipeline.sh all "02_项目/C003_工资与物价" azure
   ```

---

## 十一、下一步行动

1. **阶段 3 — 素材库积累与自动化**：建立规范角色库、用 CLIP+FAISS 做向量检索、角色一致性流程
2. **阶段 4 — 封面与批量**：自动生成 3:4 抖音封面、一次生成多条脚本批量渲染
3. **阶段 5 — 多选题迭代**：用 3-5 个选题跑通，沉淀标准化 prompt 和素材风格

> 这套流程的核心价值不在单条视频的生产速度，而在于**素材库的积累和流程的可复用性**。第一条视频最慢，从第二条开始加速。
