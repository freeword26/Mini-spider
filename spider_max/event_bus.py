#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
事件总线 - EventBus
整合消息总线、死信队列、发布订阅机制
"""

import uuid
import logging
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Callable, Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class AgentMessage:
    sender_id: str
    receiver_id: str
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    message_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    priority: int = 1
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    payload: Dict[str, Any] = field(default_factory=dict)
    trace_id: str = ""
    error: Optional[Dict] = None

    def is_broadcast(self) -> bool:
        return self.receiver_id == "*"

    def to_dict(self) -> Dict:
        return {
            "sender_id": self.sender_id,
            "receiver_id": self.receiver_id,
            "session_id": self.session_id,
            "message_id": self.message_id,
            "priority": self.priority,
            "timestamp": self.timestamp,
            "payload": self.payload,
            "trace_id": self.trace_id,
            "error": self.error
        }


@dataclass
class ErrorEvent:
    agent_id: str
    task_id: str
    error_type: str
    stack_trace: str
    trace_id: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_message(self) -> AgentMessage:
        return AgentMessage(
            sender_id=self.agent_id,
            receiver_id="*",
            priority=5,
            trace_id=self.trace_id,
            error={
                "agent_id": self.agent_id,
                "task_id": self.task_id,
                "error_type": self.error_type,
                "stack_trace": self.stack_trace,
                "timestamp": self.timestamp
            }
        )


class EventBus:
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self._subscribers: Dict[str, List[Callable]] = {}
        self._dead_letter_queue: List[AgentMessage] = []
        self._message_history: List[AgentMessage] = []
        self._max_history_size = self.config.get("max_history_size", 1000)
        self._dead_letter_threshold = self.config.get("dead_letter_threshold", 10)

    async def publish(self, message: AgentMessage) -> None:
        self._message_history.append(message)
        if len(self._message_history) > self._max_history_size:
            self._message_history.pop(0)

        logger.info(f"Publishing message: {message.message_id} from {message.sender_id} to {message.receiver_id}")

        handlers = []
        if message.receiver_id in self._subscribers:
            handlers.extend(self._subscribers[message.receiver_id])
        if "*" in self._subscribers:
            handlers.extend(self._subscribers["*"])

        if not handlers:
            logger.debug(f"No subscribers for message: {message.message_id}")
            return

        tasks = []
        for handler in handlers:
            tasks.append(self._safe_handle(message, handler))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def subscribe(self, topic: str, handler: Callable) -> None:
        if topic not in self._subscribers:
            self._subscribers[topic] = []
        self._subscribers[topic].append(handler)
        logger.info(f"Subscribed handler to topic: {topic}")

    def unsubscribe(self, topic: str, handler: Callable) -> None:
        if topic in self._subscribers:
            try:
                self._subscribers[topic].remove(handler)
                logger.info(f"Unsubscribed handler from topic: {topic}")
            except ValueError:
                pass

    async def _safe_handle(self, message: AgentMessage, handler: Callable) -> None:
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler(message)
            else:
                handler(message)
        except Exception as e:
            logger.error(f"Error handling message {message.message_id}: {e}")
            self._handle_failure(message, e)

    def _handle_failure(self, message: AgentMessage, error: Exception) -> None:
        message.error = {
            "error": str(error),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self._dead_letter_queue.append(message)

        if len(self._dead_letter_queue) >= self._dead_letter_threshold:
            self._trigger_dead_letter_alert()

    def _trigger_dead_letter_alert(self) -> None:
        logger.critical(f"Dead letter queue threshold reached: {len(self._dead_letter_queue)} messages")
        alert_message = AgentMessage(
            sender_id="event_bus",
            receiver_id="system-manager",
            priority=5,
            payload={
                "type": "dead_letter_alert",
                "count": len(self._dead_letter_queue),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        self._message_history.append(alert_message)

    async def request_reply(
        self,
        message: AgentMessage,
        timeout: float = 30.0
    ) -> Optional[AgentMessage]:
        future: asyncio.Future = asyncio.Future()
        reply_id = f"reply_to_{message.message_id}"

        def reply_handler(msg: AgentMessage) -> None:
            if msg.payload.get("reply_to") == message.message_id:
                if not future.done():
                    future.set_result(msg)

        self.subscribe(reply_id, reply_handler)

        try:
            await asyncio.wait_for(future, timeout=timeout)
            return future.result()
        except asyncio.TimeoutError:
            return None
        finally:
            self.unsubscribe(reply_id, reply_handler)

    def get_dead_letter_messages(self) -> List[AgentMessage]:
        return self._dead_letter_queue.copy()

    def get_message_history(
        self,
        sender_id: Optional[str] = None,
        receiver_id: Optional[str] = None,
        limit: int = 100
    ) -> List[AgentMessage]:
        messages = self._message_history

        if sender_id:
            messages = [m for m in messages if m.sender_id == sender_id]
        if receiver_id:
            messages = [m for m in messages if m.receiver_id == receiver_id]

        return messages[-limit:]

    def get_subscriber_count(self) -> int:
        return sum(len(handlers) for handlers in self._subscribers.values())

    def clear_dead_letter_queue(self) -> int:
        count = len(self._dead_letter_queue)
        self._dead_letter_queue.clear()
        return count

    def make_error_event(
        self,
        agent_id: str,
        task_id: str,
        error_type: str,
        stack_trace: str,
        trace_id: str = ""
    ) -> AgentMessage:
        return ErrorEvent(
            agent_id=agent_id,
            task_id=task_id,
            error_type=error_type,
            stack_trace=stack_trace,
            trace_id=trace_id
        ).to_message()


class RabbitMQEventBus(EventBus):
    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.rabbitmq_url = self.config.get("rabbitmq_url", "amqp://admin:admin123@localhost:5672/")
        self.exchange_name = self.config.get("exchange_name", "project.events")
        self.exchange_type = self.config.get("exchange_type", "topic")
        self.reconnect_interval = self.config.get("reconnect_interval", 5)
        self._connection = None
        self._channel = None
        self._connect()

    def _connect(self):
        try:
            import pika
            params = pika.URLParameters(self.rabbitmq_url)
            params.heartbeat = 600
            params.blocked_connection_timeout = 300
            self._connection = pika.BlockingConnection(params)
            self._channel = self._connection.channel()
            self._channel.exchange_declare(
                exchange=self.exchange_name,
                exchange_type=self.exchange_type,
                durable=True
            )
            logger.info(f"RabbitMQEventBus connected: {self.rabbitmq_url}, exchange={self.exchange_name}")
        except Exception as e:
            logger.warning(f"RabbitMQ connection failed ({e}), falling back to memory EventBus")
            self._connection = None
            self._channel = None

    def _ensure_channel(self):
        if self._channel is None or self._channel.is_closed:
            self._connect()

    async def publish(self, message: AgentMessage) -> None:
        await super().publish(message)
        if self._channel and not self._channel.is_closed:
            try:
                import json
                import pika
                routing_key = self._derive_routing_key(message)
                body = json.dumps(message.to_dict(), ensure_ascii=False)
                self._channel.basic_publish(
                    exchange=self.exchange_name,
                    routing_key=routing_key,
                    body=body.encode("utf-8"),
                    properties=pika.BasicProperties(
                        delivery_mode=2,
                        content_type="application/json",
                        message_id=message.message_id,
                        headers={"trace_id": message.trace_id or ""},
                    ),
                )
                logger.debug(f"Published to RabbitMQ: {routing_key}")
            except Exception as e:
                logger.error(f"RabbitMQ publish failed: {e}")

    def _derive_routing_key(self, message: AgentMessage) -> str:
        event_type = message.payload.get("event_type", "task")
        receiver = message.receiver_id if message.receiver_id != "*" else "broadcast"
        return f"{event_type}.{receiver}"

    def close(self):
        if self._connection and not self._connection.is_closed:
            self._connection.close()
            logger.info("RabbitMQEventBus connection closed")


def create_event_bus(config: Optional[Dict] = None) -> EventBus:
    config = config or {}
    mode = config.get("mode", "memory")
    if mode == "rabbitmq":
        return RabbitMQEventBus(config)
    return EventBus(config)
