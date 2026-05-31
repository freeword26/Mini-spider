"""
LLM 服务 — 集成 cost_guard 自动成本控制

四种推理模式（按优先级）：
  1. 本地 Ollama（零成本）：http://localhost:11434
  2. API 调用（付费）：OpenRouter / OpenAI
  3. 模拟模式（零成本）：无 API Key 或预算耗尽时降级
"""

import json
import logging
from typing import Any, Dict, List, Optional

import httpx

from spider_meta.config import load_settings
from spider_meta.cost_guard import budget_mgr, PRICING

logger = logging.getLogger("meta-agent.llm")


class LLMService:

    def __init__(self, settings=None, http_client=None):
        self.settings = settings or load_settings()
        self._http_client = http_client

    def _get_client(self):
        if self._http_client:
            return self._http_client
        self._http_client = httpx.AsyncClient(timeout=60)
        return self._http_client

    async def generate(
        self,
        messages: List[Dict[str, str]],
        context: Dict[str, Any] = None,
    ) -> str:
        """根据 budget_mgr.resolve_mode() 自动选择推理路径。"""
        # 注入知识
        if context and context.get("knowledge"):
            messages = self._inject_knowledge(messages, context["knowledge"])

        # 解析模式
        decision = budget_mgr.resolve_mode(self.settings.llm_model)
        mode = decision["mode"]
        model = decision["model"]

        logger.info(f"[LLM] mode={mode}, model={model}, reason={decision['reason']}")

        if mode == "fallback_simulation":
            budget_mgr.record_fallback(decision["reason"])
            return self._simulate_response(messages)

        if mode == "fallback_local":
            try:
                result = await self._call_ollama(messages)
                budget_mgr.record_fallback(decision["reason"])
                return result
            except Exception as e:
                logger.warning(f"[LLM] Ollama 调用失败，降级到模拟: {e}")
                budget_mgr.record_fallback(f"Ollama 失败: {e}")
                return self._simulate_response(messages)

        # 正常 API 模式
        if not self.settings.llm_api_key:
            budget_mgr.record_fallback("无 API Key，降级到模拟")
            return self._simulate_response(messages)

        try:
            result = await self._call_api(messages, model)
            return result
        except Exception as e:
            logger.error(f"[LLM] API 调用失败: {e}，降级到模拟")
            budget_mgr.record_fallback(f"API 失败: {e}")
            return self._simulate_response(messages)

    # ---- API 调用 ----

    async def _call_api(self, messages: List[Dict[str, str]], model: str) -> str:
        client = self._get_client()
        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": self.settings.llm_max_tokens,
        }
        headers = {"Authorization": f"Bearer {self.settings.llm_api_key}"}
        url = f"{self.settings.llm_api_url}/chat/completions"

        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()

        # 记录 token 消耗
        usage = data.get("usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
        cost = budget_mgr.record_call(input_tokens, output_tokens, model)
        logger.info(
            f"[LLM] {model} | in={input_tokens} out={output_tokens} "
            f"cost=¥{cost.cost_rmb:.6f}"
        )

        return data["choices"][0]["message"]["content"]

    # ---- 本地 Ollama ----

    async def _call_ollama(self, messages: List[Dict[str, str]]) -> str:
        client = self._get_client()
        payload = {
            "model": "llama3",
            "messages": messages,
            "stream": False,
            "options": {"temperature": 0.1},
        }
        resp = await client.post(
            "http://localhost:11434/api/chat",
            json=payload,
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["message"]["content"]

    # ---- 知识注入 ----

    def _inject_knowledge(
        self,
        messages: List[Dict[str, str]],
        knowledge: List[Any],
    ) -> List[Dict[str, str]]:
        if not knowledge:
            return messages

        knowledge_text = "\n\n## Relevant Knowledge:\n"
        for i, doc in enumerate(knowledge):
            if isinstance(doc, dict):
                content = doc.get("content", str(doc))
                source = doc.get("source", "unknown")
            else:
                content = getattr(doc, "content", str(doc))
                source = getattr(doc, "source", "unknown")
            knowledge_text += f"\n[{i+1}] (source: {source})\n{content}\n"

        new_messages = []
        injected = False
        for msg in messages:
            if msg["role"] == "system" and not injected:
                new_messages.append({
                    "role": "system",
                    "content": msg["content"] + knowledge_text,
                })
                injected = True
            else:
                new_messages.append(msg)

        if not injected:
            new_messages.insert(0, {"role": "system", "content": knowledge_text.strip()})

        return new_messages

    # ---- 模拟模式 ----

    def _simulate_response(self, messages: List[Dict[str, str]]) -> str:
        last_user = next(
            (m["content"] for m in reversed(messages) if m["role"] == "user"),
            "",
        )
        if "Observation:" in last_user:
            obs = last_user.replace("Observation:", "").strip()
            return json.dumps({
                "thought": "Analyzing observation results",
                "action": "finish",
                "final_answer": f"Task completed with observations: {obs[:500]}",
            })

        step_num = sum(1 for m in messages if m["role"] == "assistant")
        return json.dumps({
            "thought": f"Step {step_num}: Analyzing current state",
            "action": "finish",
            "final_answer": f"Simulated completion after {step_num} steps",
        })

    # ---- 工具方法 ----

    def supports_knowledge_retrieval(self) -> bool:
        return self.settings.enable_knowledge_retrieval

    async def close(self):
        if self._http_client:
            await self._http_client.aclose()
