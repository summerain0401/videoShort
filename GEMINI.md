# VideoShort 工作区规则 (GEMINI.md)

## 模型分配与协作规则

- **默认模式（基于当前工具内置模型切换，无需 API Key）**：
  - **日常与执行层 (Gemini 3.7 Flash)**：代码编写、脚本调试、TTS 配音与音频混音、Remotion 视频渲染流水线、代码检查、单元测试、数据格式转换。由主智能体直接高效处理。
  - **思考与设计层 (Claude Opus / Pro Subagents)**：系统架构规划、复杂情景剧创意剧本构思、视觉与分镜方案设计、疑难并发/算法优化。遇复杂设计需求时，主智能体自动通过 `invoke_subagent` 设置 `Model: 'pro'` 调用高阶模型完成设计后，再由 Gemini 3.7 Flash 落地执行。

- **脚本独立 API 模式（按需可选，仅在配置了对应 Key 时生效）**：
  - 仅当在 `.env` 中显式配置了 `ANTHROPIC_API_KEY` 或 `GEMINI_API_KEY` 时，独立命令行脚本才发起外部 API 调用；未配置时自动回退为本地模板与本地规则，或由 IDE 智能体直接生成项目所需数据。
