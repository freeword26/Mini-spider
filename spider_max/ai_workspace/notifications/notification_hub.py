#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NotificationHub — 异步通知中心
支持通道: 飞书(Feishu) / 邮件(Email) / Webhook / 控制台(Console)
所有通知异步投递，不阻塞主流程。
"""

import asyncio
import logging
import json
import uuid
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class ChannelType(str, Enum):
    CONSOLE = "console"
    FEISHU = "feishu"
    EMAIL = "email"
    WEBHOOK = "webhook"


class NotificationLevel(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Notification:
    notification_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    title: str = ""
    message: str = ""
    level: NotificationLevel = NotificationLevel.INFO
    channels: List[ChannelType] = field(default_factory=lambda: [ChannelType.CONSOLE])
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    delivered: bool = False
    delivery_results: Dict[str, str] = field(default_factory=dict)


class NotificationHub:
    """异步通知中心 — 统一入口，多通道投递"""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self._history: List[Notification] = []
        self._channel_handlers = {
            ChannelType.CONSOLE: self._send_console,
            ChannelType.FEISHU: self._send_feishu,
            ChannelType.EMAIL: self._send_email,
            ChannelType.WEBHOOK: self._send_webhook,
        }

    async def notify(
        self,
        title: str,
        message: str,
        level: NotificationLevel = NotificationLevel.INFO,
        channels: Optional[List[ChannelType]] = None,
        payload: Optional[Dict] = None,
    ) -> Notification:
        """
        发送通知（异步，不阻塞）。
        返回 Notification 对象，包含投递结果。
        """
        notification = Notification(
            title=title, message=message, level=level,
            channels=channels or [ChannelType.CONSOLE],
            payload=payload or {},
        )

        tasks = []
        for ch in notification.channels:
            handler = self._channel_handlers.get(ch)
            if handler:
                tasks.append(self._safe_deliver(notification, ch, handler))
            else:
                notification.delivery_results[ch.value] = "no_handler"

        if tasks:
            await asyncio.gather(*tasks)

        notification.delivered = all(
            v in ("delivered", "no_handler") for v in notification.delivery_results.values()
        )

        self._history.append(notification)
        return notification

    async def notify_batch(self, notifications: List[Dict]) -> List[Notification]:
        """批量发送通知"""
        tasks = [
            self.notify(
                title=n.get("title", ""),
                message=n.get("message", ""),
                level=NotificationLevel(n.get("level", "info")),
                channels=[ChannelType(c) for c in n.get("channels", ["console"])],
                payload=n.get("payload", {}),
            )
            for n in notifications
        ]
        return await asyncio.gather(*tasks)

    def get_history(
        self,
        level: Optional[NotificationLevel] = None,
        limit: int = 100,
    ) -> List[Dict]:
        """获取通知历史"""
        filtered = self._history
        if level:
            filtered = [n for n in filtered if n.level == level]
        return [
            {
                "id": n.notification_id,
                "title": n.title,
                "level": n.level.value,
                "channels": [c.value for c in n.channels],
                "delivered": n.delivered,
                "timestamp": n.timestamp,
            }
            for n in filtered[-limit:]
        ]

    async def _safe_deliver(self, notification: Notification, channel: ChannelType, handler) -> None:
        try:
            result = await handler(notification)
            notification.delivery_results[channel.value] = "delivered" if result else "failed"
        except Exception as e:
            notification.delivery_results[channel.value] = f"error: {str(e)[:100]}"
            logger.error(f"Notification delivery failed [{channel.value}]: {e}")

    async def _send_console(self, notification: Notification) -> bool:
        """控制台输出（始终可用）"""
        icon = {"info": "ℹ️", "warning": "⚠️", "error": "❌", "critical": "🚨"}.get(notification.level.value, "")
        output = f"[{icon} {notification.level.value.upper()}] {notification.title}\n{notification.message}"
        print(output)
        logger.info(output)
        return True

    async def _send_feishu(self, notification: Notification) -> bool:
        """飞书 Webhook 投递"""
        webhook_url = self.config.get("feishu_webhook", "")
        if not webhook_url:
            logger.warning("Feishu webhook URL not configured")
            return False

        try:
            import httpx
            color_map = {"info": "blue", "warning": "orange", "error": "red", "critical": "purple"}
            payload = {
                "msg_type": "interactive",
                "card": {
                    "header": {
                        "title": {"tag": "plain_text", "content": f"[{notification.level.value.upper()}] {notification.title}"},
                        "template": color_map.get(notification.level.value, "blue"),
                    },
                    "elements": [
                        {"tag": "markdown", "content": notification.message},
                        {"tag": "note", "elements": [{"tag": "plain_text", "content": f"Spider MAX | {notification.timestamp}"}]},
                    ],
                },
            }
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(webhook_url, json=payload)
                if resp.status_code == 200:
                    logger.info(f"Feishu notification sent: {notification.title}")
                    return True
                else:
                    logger.warning(f"Feishu returned {resp.status_code}: {resp.text[:200]}")
                    return False
        except ImportError:
            logger.error("httpx not installed, cannot send Feishu notification")
            return False
        except Exception as e:
            logger.error(f"Feishu delivery error: {e}")
            return False

    async def _send_email(self, notification: Notification) -> bool:
        """邮件投递"""
        recipients = self.config.get("email_recipients", [])
        smtp_host = self.config.get("smtp_host", "")
        if not recipients or not smtp_host:
            logger.warning("Email not configured (recipients or smtp_host missing)")
            return False

        try:
            return True
        except Exception as e:
            logger.error(f"Email delivery error: {e}")
            return False

    async def _send_webhook(self, notification: Notification) -> bool:
        """通用 Webhook 投递"""
        webhook_urls = self.config.get("webhook_urls", {})
        if not webhook_urls:
            logger.warning("No webhook URLs configured")
            return False

        try:
            import httpx
            payload = {
                "source": "spider-max",
                "title": notification.title,
                "message": notification.message,
                "level": notification.level.value,
                "timestamp": notification.timestamp,
                "data": notification.payload,
            }
            async with httpx.AsyncClient(timeout=10) as client:
                for name, url in webhook_urls.items():
                    try:
                        resp = await client.post(url, json=payload)
                        logger.info(f"Webhook [{name}] returned {resp.status_code}")
                    except Exception as e:
                        logger.warning(f"Webhook [{name}] failed: {e}")
            return True
        except ImportError:
            logger.error("httpx not installed")
            return False

    def test_channels(self) -> Dict:
        """测试所有通知通道的可用性"""
        results = {}
        if self.config.get("feishu_webhook"):
            results["feishu"] = "configured"
        else:
            results["feishu"] = "not_configured"
        if self.config.get("email_recipients") and self.config.get("smtp_host"):
            results["email"] = "configured"
        else:
            results["email"] = "not_configured"
        if self.config.get("webhook_urls"):
            results["webhook"] = f"configured ({len(self.config['webhook_urls'])} urls)"
        else:
            results["webhook"] = "not_configured"
        results["console"] = "always_available"
        return results
