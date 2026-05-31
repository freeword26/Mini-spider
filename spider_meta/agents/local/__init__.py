"""
本地 AI 智能体执行器

通过 Ollama 本地推理运行：
  - Qwen 2.5 Coder (代码工程师)
  - Qwen 2.5 (文档处理员 / 数据分析师)

Fallback: 如果 Ollama 不可用，自动切回 _simulate 模式。
"""

import json
import logging
from typing import Any, Dict

from spider_meta.agents.agent_router import AgentRole, AGENT_ROLES, AgentTier

logger = logging.getLogger("spider_meta.agents.local")


class LocalAgent:
    """本地 Ollama Agent 执行器"""

    def __init__(self, role_name: str, ollama_url: str = "http://localhost:11434"):
        self.role: AgentRole = AGENT_ROLES[role_name]
        self.ollama_url = ollama_url
        self._available = None  # 延迟检测

    @property
    def is_available(self) -> bool:
        if self._available is None:
            self._available = self._check_ollama()
        return self._available

    def _check_ollama(self) -> bool:
        try:
            import httpx
            r = httpx.get(f"{self.ollama_url}/api/tags", timeout=3)
            return r.status_code == 200
        except Exception:
            logger.warning("Ollama 不可用，本地 Agent 将使用模拟模式")
            return False

    async def execute(self, task: str, tools: list = None) -> dict:
        """执行本地推理任务"""
        if not self.is_available:
            return self._fallback(task)

        try:
            import httpx
            payload = {
                "model": self.role.model,
                "messages": [
                    {"role": "system", "content": self.role.system_prompt},
                    {"role": "user", "content": task},
                ],
                "stream": False,
                "options": {
                    "temperature": self.role.temperature,
                    "num_predict": self.role.max_tokens,
                },
            }
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.ollama_url}/api/chat",
                    json=payload, timeout=120,
                )
                resp.raise_for_status()
                data = resp.json()
                content = data.get("message", {}).get("content", "")

            return {
                "status": "ok",
                "role": self.role.name,
                "model": self.role.model,
                "tier": "local",
                "cost_rmb": 0.0,
                "result": content,
            }
        except Exception as e:
            logger.error(f"本地推理失败 [{self.role.name}]: {e}")
            return self._fallback(task)

    def _fallback(self, task: str) -> dict:
        """Ollama 不可用时的降级返回"""
        return {
            "status": "fallback",
            "role": self.role.name,
            "model": "simulation",
            "tier": "local",
            "cost_rmb": 0.0,
            "result": f"[模拟模式] {self.role.name}: 任务已接收但 Ollama 不可用。任务摘要: {task[:200]}",
        }


# ---- 工厂函数 ----

def get_local_agent(role_name: str, ollama_url: str = None) -> LocalAgent:
    """获取本地 Agent 实例"""
    url = ollama_url or "http://localhost:11434"
    return LocalAgent(role_name, url)
