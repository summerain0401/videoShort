#!/usr/bin/env python3
import os
import unittest
from unittest.mock import patch
from shared.llm_router import LLMRouter, TaskTier

class TestLLMRouter(unittest.TestCase):
    def test_routing_tiers_default(self):
        with patch.dict(os.environ, {
            "ANTHROPIC_API_KEY": "sk-ant-test-key",
            "GEMINI_API_KEY": "gemini-test-key",
        }, clear=True):
            router = LLMRouter()
            # 1. 深度思考与设计 -> 自动分配给 Claude Opus
            design_cfg = router.get_provider_config(TaskTier.REASONING_DESIGN)
            self.assertEqual(design_cfg["provider"], "anthropic")
            self.assertIn("opus", design_cfg["model"])

            # 2. 日常与执行 -> 自动分配给 Gemini 3.7 Flash
            routine_cfg = router.get_provider_config(TaskTier.ROUTINE_EXECUTION)
            self.assertEqual(routine_cfg["provider"], "gemini")
            self.assertIn("flash", routine_cfg["model"])

    def test_custom_model_env_override(self):
        with patch.dict(os.environ, {
            "ANTHROPIC_API_KEY": "sk-ant-test-key",
            "CLAUDE_MODEL": "claude-3-7-sonnet-20250219",
            "GEMINI_API_KEY": "gemini-test-key",
            "GEMINI_MODEL": "gemini-3.7-flash",
        }, clear=True):
            router = LLMRouter()
            design_cfg = router.get_provider_config(TaskTier.REASONING_DESIGN)
            self.assertEqual(design_cfg["model"], "claude-3-7-sonnet-20250219")

            routine_cfg = router.get_provider_config(TaskTier.ROUTINE_EXECUTION)
            self.assertEqual(routine_cfg["model"], "gemini-3.7-flash")

if __name__ == "__main__":
    unittest.main()
