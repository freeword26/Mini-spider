"""
云端 AI 智能体执行器

通过云端 API 运行：
  - DeepSeek (情报收集员 / 社交媒体写手)
  - GPT-4o-mini (创意策划师)

集成 cost_guard 自动成本控制。
"""

import json
import logging
from typing import Dict

from spider_meta.agents.agent_router import AGENT_ROLES, AgentTier
from spider_meta.cost_guard import budget_mgr, PRICING

logger = logging.getLogger("spider_meta.agents.cloud")


# ---- API 配置 ----

CLOUD_APIS = {
    "deepseek-chat": {
        "base_url": "https://api.deepseek.com",
        "price_per_million": 0.14,   # ¥0.14/1M tokens
    },
    "gpt-4o-mini": {
        "base_url": "https://openrouter.ai/api/v1",
        "price_per_million": 0.11,
    },
}


class CloudAgent:
    """云端 API Agent 执行器"""

    def __init__(self, role_name: str, api_key: str = None):
        from spider_meta.config import load_settings
        settings = load_settings()
        self.role = AGENT_ROLES[role_name]
        self.api_key = api_key or settings.llm_api_key
        self.api_url = CLOUD_APIS.get(
            self.role.model,
            {"base_url": settings.llm_api_url or "https://openrouter.ai/api/v1"}
        )["base_url"]

    async def execute(self, task: str) -> dict:
        """执行云端 API 调用，自动追踪成本"""
        if not self.api_key:
            return self._fallback("无 API Key")

        # 预算检查
        decision = budget_mgr.resolve_mode(self.role.model)
        if decision["mode"] == "fallback_simulation":
            return self._fallback(decision["reason"])

        try:
            import httpx
            payload = {
                "model": self.role.model,
                "messages": [
                    {"role": "system", "content": self.role.system_prompt},
                    {"role": "user", "content": task},
                ],
                "temperature": self.role.temperature,
                "max_tokens": self.role.max_tokens,
            }
            headers = {"Authorization": f"Bearer {self.api_key}"}
            url = f"{self.api_url}/chat/completions"

            async with httpx.AsyncClient() as client:
                resp = await client.post(url, json=payload, headers=headers, timeout=120)
                resp.raise_for_status()
                data = resp.json()

            # 记录成本
            usage = data.get("usage", {})
            in_tok = usage.get("prompt_tokens", 0)
            out_tok = usage.get("completion_tokens", 0)
            cost = budget_mgr.record_call(in_tok, out_tok, self.role.model)
            logger.info(
                f"[云端] {self.role.name} | {self.role.model} | "
                f"in={in_tok} out={out_tok} cost=¥{cost.cost_rmb:.6f}"
            )

            return {
                "status": "ok",
                "role": self.role.name,
                "model": self.role.model,
                "tier": "cloud",
                "cost_rmb": cost.cost_rmb,
                "tokens_in": in_tok,
                "tokens_out": out_tok,
                "result": data["choices"][0]["message"]["content"],
            }
        except Exception as e:
            logger.error(f"云端推理失败 [{self.role.name}]: {e}")
            return self._fallback(str(e))

    def _fallback(self, reason: str) -> dict:
        return {
            "status": "fallback",
            "role": self.role.name,
            "model": "simulation",
            "tier": "cloud",
            "cost_rmb": 0.0,
            "result": f"[降级] {self.role.name}: {reason}。任务已标记待重试。",
        }


def get_cloud_agent(role_name: str, api_key: str = None) -> CloudAgent:
    return CloudAgent(role_name, api_key)
