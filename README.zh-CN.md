# videoShort · 布丁经济学短视频工作流

[English](README.md) | [简体中文](README.zh-CN.md)

使用原创角色「小布丁」和共享素材，制作生活经济学竖屏短视频。Python 脚本负责剧本、配音、时间轴、素材与质检，React / Remotion 负责画面与合成。品牌与内容边界见 [ACCOUNT_BRAND.md](ACCOUNT_BRAND.md)。

## 当前能力

已有项目脚本、场景配置、时间轴、封面和共享角色 / 背景 / 道具。默认出片目标为 1080×1920、30 fps；具体时长由配音与时间轴决定。设计来源文档中的海绵宝宝案例不是当前主角或已交付能力。

生产前必须人工检查剧本与素材，填写每个项目的 `qa/review.json`；检查器不会代为批准。干净克隆中的历史项目不一定包含审核记录和配音文件，因此不能保证一条命令重建所有历史成片。

## 环境准备

需要 Node.js / npm、支持当前 Remotion 的浏览器、Python 3.10+ 和 FFmpeg / ffprobe。基础 Python 依赖可在独立环境中准备：

```bash
npm ci
python3 -m venv .venv
source .venv/bin/activate
pip install edge-tts Pillow
bash scripts/pipeline.sh help
bash scripts/pipeline.sh list
```

仓库没有完整锁定的 Python 依赖清单。Azure 配音需额外安装 `azure-cognitiveservices-speech` 并配置 [环境变量示例](.env.example)；语义素材检索还需要 PyTorch、Transformers、FAISS、NumPy，并在首次使用时下载模型。上述可选能力不是基础安装的一部分。

## 生产入口

从仓库根目录运行，使用自己的新项目编号：

```bash
bash scripts/pipeline.sh new "生活经济学主题" C100_新选题
# 修改剧本，补齐素材，人工完成 qa/review.json 后：
bash scripts/pipeline.sh voice 02_项目/C100_新选题 edge
bash scripts/pipeline.sh timeline 02_项目/C100_新选题
bash scripts/pipeline.sh render 02_项目/C100_新选题
bash scripts/pipeline.sh check 02_项目/C100_新选题
```

配音需要联网，所选服务可能有费用。`new` 使用模板模式，生成的是待编辑起稿，不代表经过研究或审核的事实内容；不传 `edge` 时，配音选择逻辑还可能使用配置的 Azure。

## 输入与输出

- `02_项目/`：每期的 `script/`、`data/`、`audio/`、`qa/` 和 `deliverables/`。
- `shared/`：素材、索引与账号头像，见 [共享素材说明](shared/README.md)。`public/shared` 为指向该目录的相对符号链接，迁移时需保留。
- `scripts/`：生产与检查入口；`remotion/`：视频组件。
- `batch-plans/`：批量选题；`tests/` 目前没有实际测试用例。

技术和语义检查不能替代人工审片。本次文档整理只做无外部副作用的入口核对，没有配音、付费调用或整片渲染。

## 许可
当前默认分支未提供项目级许可证文件；公开可见不等于授予复用许可。第三方依赖及素材保留各自条款。
