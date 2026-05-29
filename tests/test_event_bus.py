#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
事件总线单元测试
"""

import unittest
import asyncio
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from event_bus import EventBus, AgentMessage, ErrorEvent


class TestAgentMessage(unittest.TestCase):
    def test_create_message(self):
        msg = AgentMessage(
            sender_id="agent1",
            receiver_id="agent2",
            payload={"type": "test"}
        )
        self.assertEqual(msg.sender_id, "agent1")
        self.assertEqual(msg.receiver_id, "agent2")
        self.assertFalse(msg.is_broadcast())

    def test_broadcast_message(self):
        msg = AgentMessage(
            sender_id="agent1",
            receiver_id="*"
        )
        self.assertTrue(msg.is_broadcast())

    def test_message_to_dict(self):
        msg = AgentMessage(
            sender_id="agent1",
            receiver_id="agent2",
            payload={"key": "value"}
        )
        data = msg.to_dict()
        self.assertIn("message_id", data)
        self.assertIn("timestamp", data)


class TestErrorEvent(unittest.TestCase):
    def test_create_error_event(self):
        error = ErrorEvent(
            agent_id="agent1",
            task_id="task1",
            error_type="ValueError",
            stack_trace="line 1..."
        )
        self.assertEqual(error.agent_id, "agent1")
        self.assertEqual(error.error_type, "ValueError")

    def test_error_event_to_message(self):
        error = ErrorEvent(
            agent_id="agent1",
            task_id="task1",
            error_type="TimeoutError",
            stack_trace="timeout"
        )
        msg = error.to_message()
        self.assertEqual(msg.sender_id, "agent1")
        self.assertEqual(msg.receiver_id, "*")
        self.assertEqual(msg.priority, 5)
        self.assertIsNotNone(msg.error)


class TestEventBus(unittest.TestCase):
    def setUp(self):
        self.event_bus = EventBus()

    def test_create_event_bus(self):
        self.assertIsNotNone(self.event_bus)
        self.assertEqual(len(self.event_bus._subscribers), 0)

    def test_subscribe(self):
        handler_called = []

        def handler(msg):
            handler_called.append(msg)

        self.event_bus.subscribe("test_topic", handler)
        self.assertEqual(self.event_bus.get_subscriber_count(), 1)

    def test_unsubscribe(self):
        def handler(msg):
            pass

        self.event_bus.subscribe("test_topic", handler)
        self.event_bus.unsubscribe("test_topic", handler)
        self.assertEqual(self.event_bus.get_subscriber_count(), 0)

    def test_get_dead_letter_messages(self):
        messages = self.event_bus.get_dead_letter_messages()
        self.assertIsInstance(messages, list)

    def test_get_message_history(self):
        history = self.event_bus.get_message_history()
        self.assertIsInstance(history, list)

    def test_clear_dead_letter_queue(self):
        count = self.event_bus.clear_dead_letter_queue()
        self.assertEqual(count, 0)

    def test_make_error_event(self):
        msg = self.event_bus.make_error_event(
            agent_id="agent1",
            task_id="task1",
            error_type="ValueError",
            stack_trace="error stack"
        )
        self.assertEqual(msg.sender_id, "agent1")
        self.assertEqual(msg.priority, 5)


class TestEventBusAsync(unittest.TestCase):
    def setUp(self):
        self.event_bus = EventBus()

    def test_publish_message(self):
        async def test():
            msg = AgentMessage(
                sender_id="agent1",
                receiver_id="agent2",
                payload={"type": "test"}
            )
            await self.event_bus.publish(msg)

        asyncio.run(test())

    def test_subscribe_and_publish(self):
        async def test():
            received = []

            async def handler(msg):
                received.append(msg)

            self.event_bus.subscribe("test_topic", handler)

            msg = AgentMessage(
                sender_id="agent1",
                receiver_id="test_topic",
                payload={"data": "test_data"}
            )
            await self.event_bus.publish(msg)

            await asyncio.sleep(0.1)

        asyncio.run(test())


if __name__ == "__main__":
    unittest.main()
