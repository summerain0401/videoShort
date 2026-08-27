# VideoShort 项目智能体协同与模型自动分配规范

本项目遵循「**默认使用当前开发工具自带的模型切换，仅在配置了外部 API Key 时才通过 API 调用**」的核心准则：
- **思考与设计**：交由高阶推理模型 (**Claude Opus / Pro**)
- **日常与执行**：交由极速响应模型 (**Gemini 3.7 Flash**)

---

## 1. 默认机制：当前工具内置模型切换（零 API 成本）

日常在 Antigravity 环境下开发和运行项目时，**默认不依赖任何外部 API 密钥**：

| 工作类型 | 触发场景 | 负责模型 / 代理 | 执行机制 |
| :--- | :--- | :--- | :--- |
| **深度思考与设计** | • 视频流水线系统级架构设计与重构<br>• 复杂情景剧创意构思与剧本剧情编排<br>• 视觉分镜、角色表情与道具调度体系设计<br>• 疑难 Bug 根因分析（并发渲染、内存溢出） | **Claude Opus / Pro Subagents** | 遇到此类任务时，主智能体自动派发 `invoke_subagent` 并指定 `Model: 'pro'`（Claude Opus），由工具内部自动完成高阶推理与方案设计 |
| **日常开发与执行** | • 代码编写、Bug 修复、重构落地<br>• Remotion 视频渲染与组件调整<br>• TTS 配音、音频混音与时间轴对齐脚本运行<br>• 语义检查、发音检查、文件读写与常规答疑 | **Gemini 3.7 Flash** | 由主智能体直接极速执行，追求秒级响应与高执行力 |

---

## 2. API 增强机制（仅在配置了 API 时生效）

对于脱离 IDE 环境独立运行的底层 Python 脚本（如 `python scripts/generate-story.py --mode llm`）：

1. **已配置 API 时**：
   - 脚本通过 `shared/llm_router.py` 自动分流：
     - 剧本创作等思考任务（`TaskTier.REASONING_DESIGN`）自动调用 `ANTHROPIC_API_KEY` (Claude Opus)。
     - 质检与数据提取等任务（`TaskTier.ROUTINE_EXECUTION`）自动调用 `GEMINI_API_KEY` (Gemini 3.7 Flash)。
2. **未配置 API 时（默认）**：
   - 脚本自动跳过网络请求，优雅回退到本地模板/规则处理；
   - 复杂设计与创意剧本直接由当前 IDE 智能体基于 Pro 模型自动生成 JSON 写入项目，无需用户花钱购买 API。
