#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AstrBot 网关适配器 — 三层闭环架构冲突#4解决方案
AstrBot 仅做意图识别+用户授权，不包含调度/执行逻辑
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class IntentType(str, Enum):
    TASK_QUERY = "task_query"
    TASK_ASSIGN = "task_assign"
    STATUS_CHECK = "status_check"
    AUTHORIZATION = "authorization"
    CONFIG_CHANGE = "config_change"
    REPORT_REQUEST = "report_request"
    PROJECT_QUERY = "project_query"
    GENERAL = "general"


@dataclass
class RecognizedIntent:
    intent_type: IntentType
    confidence: float
    parameters: Dict
    raw_text: str
    timestamp: str = ""


@dataclass
class GatewayEvent:
    event_id: str
    event_type: str
    payload: Dict
    source: str = "astrbot_gateway"


class AstrBotGatewayAdapter:
    """AstrBot 网关适配器 — AstrBot仅做意图识别+用户授权"""

    def __init__(self, event_bus=None, auth_manager=None):
        self.event_bus = event_bus
        self.auth_manager = auth_manager
        self._intent_handlers = {
            IntentType.TASK_QUERY: self._handle_task_query,
            IntentType.TASK_ASSIGN: self._handle_task_assign,
            IntentType.STATUS_CHECK: self._handle_status_check,
            IntentType.AUTHORIZATION: self._handle_authorization,
            IntentType.CONFIG_CHANGE: self._handle_config_change,
            IntentType.REPORT_REQUEST: self._handle_report_request,
            IntentType.PROJECT_QUERY: self._handle_project_query,
            IntentType.GENERAL: self._handle_general,
        }

    def recognize_intent(self, user_input: str) -> RecognizedIntent:
        text = user_input.lower().strip()

        if any(kw in text for kw in ["分配任务", "assign task", "下达任务"]):
            return RecognizedIntent(
                intent_type=IntentType.TASK_ASSIGN,
                confidence=0.9,
                parameters=self._extract_task_params(text),
                raw_text=user_input,
            )
        if any(kw in text for kw in ["状态", "进度", "status", "progress"]):
            return RecognizedIntent(
                intent_type=IntentType.STATUS_CHECK,
                confidence=0.85,
                parameters={"query": text},
                raw_text=user_input,
            )
        if any(kw in text for kw in ["确认", "同意", "approve", "确认授权"]):
            return RecognizedIntent(
                intent_type=IntentType.AUTHORIZATION,
                confidence=0.95,
                parameters=self._extract_auth_params(text),
                raw_text=user_input,
            )
        if any(kw in text for kw in ["配置", "修改设置", "config"]):
            return RecognizedIntent(
                intent_type=IntentType.CONFIG_CHANGE,
                confidence=0.8,
                parameters=self._extract_config_params(text),
                raw_text=user_input,
            )
        if any(kw in text for kw in ["报告", "汇报", "日报", "report"]):
            return RecognizedIntent(
                intent_type=IntentType.REPORT_REQUEST,
                confidence=0.85,
                parameters=self._extract_report_params(text),
                raw_text=user_input,
            )
        if any(kw in text for kw in ["项目", "project"]):
            return RecognizedIntent(
                intent_type=IntentType.PROJECT_QUERY,
                confidence=0.8,
                parameters=self._extract_project_params(text),
                raw_text=user_input,
            )

        return RecognizedIntent(
            intent_type=IntentType.GENERAL,
            confidence=0.5,
            parameters={"query": text},
            raw_text=user_input,
        )

    async def process_user_input(self, user_input: str) -> Dict:
        intent = self.recognize_intent(user_input)
        handler = self._intent_handlers.get(intent.intent_type, self._handle_general)
        event = await handler(intent)
        if event and self.event_bus:
            await self._publish_event(event)
        return {
            "intent_type": intent.intent_type.value,
            "confidence": intent.confidence,
            "event_type": event.event_type if event else None,
            "processed_at": datetime.now(timezone.utc).isoformat(),
        }

    async def _handle_task_query(self, intent: RecognizedIntent) -> GatewayEvent:
        return GatewayEvent(
            event_id=f"evt_task_query_{int(datetime.now().timestamp())}",
            event_type="task_query",
            payload={"query": intent.parameters.get("query", intent.raw_text)},
        )

    async def _handle_task_assign(self, intent: RecognizedIntent) -> GatewayEvent:
        return GatewayEvent(
            event_id=f"evt_task_assign_{int(datetime.now().timestamp())}",
            event_type="task_assign",
            payload={
                "task_id": intent.parameters.get("task_id"),
                "agent_id": intent.parameters.get("agent_id"),
                "description": intent.parameters.get("description"),
            },
        )

    async def _handle_status_check(self, intent: RecognizedIntent) -> GatewayEvent:
        return GatewayEvent(
            event_id=f"evt_status_{int(datetime.now().timestamp())}",
            event_type="status_check",
            payload={"query": intent.parameters.get("query", intent.raw_text)},
        )

    async def _handle_authorization(self, intent: RecognizedIntent) -> GatewayEvent:
        request_id = intent.parameters.get("request_id", "")
        approved = intent.parameters.get("approved", True)
        return GatewayEvent(
            event_id=f"evt_auth_{int(datetime.now().timestamp())}",
            event_type="authorization_response",
            payload={
                "request_id": request_id,
                "approved": approved,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    async def _handle_config_change(self, intent: RecognizedIntent) -> GatewayEvent:
        return GatewayEvent(
            event_id=f"evt_config_{int(datetime.now().timestamp())}",
            event_type="config_change_request",
            payload={
                "config_key": intent.parameters.get("key"),
                "config_value": intent.parameters.get("value"),
            },
        )

    async def _handle_report_request(self, intent: RecognizedIntent) -> GatewayEvent:
        return GatewayEvent(
            event_id=f"evt_report_{int(datetime.now().timestamp())}",
            event_type="report_request",
            payload={
                "report_type": intent.parameters.get("report_type", "daily"),
            },
        )

    async def _handle_project_query(self, intent: RecognizedIntent) -> GatewayEvent:
        return GatewayEvent(
            event_id=f"evt_project_{int(datetime.now().timestamp())}",
            event_type="project_query",
            payload={
                "project_id": intent.parameters.get("project_id"),
                "query": intent.raw_text,
            },
        )

    async def _handle_general(self, intent: RecognizedIntent) -> GatewayEvent:
        return GatewayEvent(
            event_id=f"evt_general_{int(datetime.now().timestamp())}",
            event_type="general_query",
            payload={"query": intent.raw_text},
        )

    async def _publish_event(self, event: GatewayEvent):
        if not self.event_bus:
            return
        try:
            from .event_bus import AgentMessage
        except (ImportError, SystemError):
            from event_bus import AgentMessage

        try:
            message = AgentMessage(
                sender_id="astrbot_gateway",
                receiver_id="*",
                priority=3,
                payload={
                    "event_type": event.event_type,
                    "event_id": event.event_id,
                    **event.payload,
                },
            )

            import asyncio
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self.event_bus.publish(message))
            except RuntimeError:
                asyncio.run(self.event_bus.publish(message))
        except Exception as e:
            logger.error(f"Error publishing gateway event: {e}")

    def _extract_task_params(self, text: str) -> Dict:
        return {"raw": text}

    def _extract_auth_params(self, text: str) -> Dict:
        approved = not any(kw in text for kw in ["拒绝", "deny", "不同意", "取消"])
        return {"approved": approved}

    def _extract_config_params(self, text: str) -> Dict:
        return {"raw": text}

    def _extract_report_params(self, text: str) -> Dict:
        if "周报" in text or "weekly" in text:
            report_type = "weekly"
        elif "月报" in text or "monthly" in text:
            report_type = "monthly"
        else:
            report_type = "daily"
        return {"report_type": report_type}

    def _extract_project_params(self, text: str) -> Dict:
        import re
        match = re.search(r'P\d+', text.upper())
        return {"project_id": match.group() if match else None}
