#!/usr/bin/env python3
"""
shared/llm_router.py — 统一多模型智能路由器
分流原则：
1. 默认优先依赖 IDE 智能体自带的模型调度（Pro / Flash Subagent），无需外部 API。
2. 仅在开发者显式于 .env 中配置了 API Key 时，独立运行的 Python 脚本才会发起外部 API 请求。
- 思考与设计类任务 (REASONING_DESIGN)：配置 API 时路由至 Claude Opus
- 日常与执行类任务 (ROUTINE_EXECUTION)：配置 API 时路由至 Gemini 3.7 Flash
"""
import os
import json
import urllib.request
import urllib.error
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any, List

ROOT = Path(__file__).resolve().parent.parent

def load_dotenv():
    """轻量级加载项目根目录 .env 文件（不强依赖 python-dotenv）"""
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip().strip("'\"")
        if key and key not in os.environ:
            os.environ[key] = val

load_dotenv()

class TaskTier(str, Enum):
    REASONING_DESIGN = "reasoning_design"   # 深度思考、剧本构思、分镜创意、架构规划
    ROUTINE_EXECUTION = "routine_execution" # 日常批处理、格式清洗、语义校验、发音检查

class LLMRouter:
    def __init__(self):
        load_dotenv()

    def has_api(self, tier: TaskTier) -> bool:
        """检查当前任务级别是否配置了外部 API"""
        cfg = self.get_provider_config(tier)
        return cfg.get("provider") not in ["none", None]

    def get_provider_config(self, tier: TaskTier) -> Dict[str, Any]:
        """根据任务级别解析优先级模型配置（仅在有配置 API 时生效）"""
        if tier == TaskTier.REASONING_DESIGN:
            # 1. 优先检查 Claude Opus / Anthropic
            anthropic_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_API_KEY")
            if anthropic_key:
                return {
                    "provider": "anthropic",
                    "api_key": anthropic_key,
                    "base_url": os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com/v1"),
                    "model": os.getenv("CLAUDE_MODEL", "claude-3-opus-20240229"),
                    "tier": tier.value
                }
            # 2. 备选推理模型
            if os.getenv("DEEPSEEK_API_KEY"):
                return {
                    "provider": "openai_compatible",
                    "api_key": os.getenv("DEEPSEEK_API_KEY"),
                    "base_url": os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
                    "model": os.getenv("DEEPSEEK_REASONER_MODEL", "deepseek-reasoner"),
                    "tier": tier.value
                }
            if os.getenv("OPENAI_API_KEY"):
                return {
                    "provider": "openai_compatible",
                    "api_key": os.getenv("OPENAI_API_KEY"),
                    "base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
                    "model": os.getenv("OPENAI_DESIGN_MODEL", "gpt-4o"),
                    "tier": tier.value
                }

        # 默认为日常执行或降级：ROUTINE_EXECUTION
        # 1. 优先检查 Gemini 3.7 Flash
        gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if gemini_key:
            return {
                "provider": "gemini",
                "api_key": gemini_key,
                "base_url": os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta"),
                "model": os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
                "tier": tier.value
            }

        # 2. 其他极速日常模型备选
        if os.getenv("OPENAI_API_KEY"):
            return {
                "provider": "openai_compatible",
                "api_key": os.getenv("OPENAI_API_KEY"),
                "base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
                "model": os.getenv("OPENAI_ROUTINE_MODEL", "gpt-4o-mini"),
                "tier": tier.value
            }
        if os.getenv("DEEPSEEK_API_KEY"):
            return {
                "provider": "openai_compatible",
                "api_key": os.getenv("DEEPSEEK_API_KEY"),
                "base_url": os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
                "model": "deepseek-chat",
                "tier": tier.value
            }
        if os.getenv("DASHSCOPE_API_KEY"):
            return {
                "provider": "openai_compatible",
                "api_key": os.getenv("DASHSCOPE_API_KEY"),
                "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
                "model": "qwen-turbo",
                "tier": tier.value
            }
        if os.getenv("ZHIPU_API_KEY"):
            return {
                "provider": "openai_compatible",
                "api_key": os.getenv("ZHIPU_API_KEY"),
                "base_url": "https://open.bigmodel.cn/api/paas/v4",
                "model": "glm-4-flash",
                "tier": tier.value
            }

        # 未配置 API
        return {
            "provider": "none",
            "model": "none",
            "tier": tier.value
        }

    def call(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        tier: TaskTier = TaskTier.ROUTINE_EXECUTION,
        json_mode: bool = False,
        temperature: float = 0.7
    ) -> str:
        """统一发送 LLM 请求（未配置 API 时会抛出明确提示）"""
        config = self.get_provider_config(tier)
        provider = config.get("provider")

        if provider == "anthropic":
            return self._call_anthropic(config, prompt, system_prompt, json_mode, temperature)
        elif provider == "gemini":
            return self._call_gemini(config, prompt, system_prompt, json_mode, temperature)
        elif provider == "openai_compatible":
            return self._call_openai_compatible(config, prompt, system_prompt, json_mode, temperature)
        else:
            raise RuntimeError(
                f"[LLMRouter] 未检测到 {tier.value} 对应的 API 配置。建议直接使用 IDE 内置模型协作，或在 .env 中设置 API Key。"
            )

    def _call_anthropic(
        self, config: dict, prompt: str, system_prompt: Optional[str], json_mode: bool, temperature: float
    ) -> str:
        url = f"{config['base_url'].rstrip('/')}/messages"
        headers = {
            "x-api-key": config["api_key"],
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        payload: Dict[str, Any] = {
            "model": config["model"],
            "max_tokens": 4096,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}]
        }
        if system_prompt:
            payload["system"] = system_prompt
        if json_mode:
            payload["messages"][0]["content"] += "\n\n请直接输出纯 JSON 格式内容，不要附带任何 markdown 标识或额外解释。"

        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["content"][0]["text"].strip()

    def _call_gemini(
        self, config: dict, prompt: str, system_prompt: Optional[str], json_mode: bool, temperature: float
    ) -> str:
        model = config["model"]
        url = f"{config['base_url'].rstrip('/')}/models/{model}:generateContent?key={config['api_key']}"
        headers = {"content-type": "application/json"}
        
        contents = []
        if system_prompt:
            contents.append({"role": "user", "parts": [{"text": f"System Instruction: {system_prompt}"}]})
            contents.append({"role": "model", "parts": [{"text": "Understood."}]})
        contents.append({"role": "user", "parts": [{"text": prompt}]})

        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": 4096
            }
        }
        if json_mode:
            payload["generationConfig"]["responseMimeType"] = "application/json"

        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=45) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            candidates = data.get("candidates", [])
            if not candidates:
                raise RuntimeError(f"Gemini API returned no candidates: {data}")
            return candidates[0]["content"]["parts"][0]["text"].strip()

    def _call_openai_compatible(
        self, config: dict, prompt: str, system_prompt: Optional[str], json_mode: bool, temperature: float
    ) -> str:
        url = f"{config['base_url'].rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json"
        }
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload: Dict[str, Any] = {
            "model": config["model"],
            "messages": messages,
            "temperature": temperature
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"].strip()

# 全局单例
router = LLMRouter()
