#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调度中心单元测试
"""

import unittest
import asyncio
from datetime import datetime, timedelta

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import (
    Workflow, TaskDefinition, TriggerConfig, ScheduleConfig,
    TriggerType, ExecutionStatus
)
from workflow_executor import WorkflowExecutor
from event_bus import EventBus
from scheduler import (
    WorkflowScheduler, CronTrigger, IntervalTrigger, OneTimeTrigger
)


class TestCronTrigger(unittest.TestCase):
    def test_cron_trigger_creation(self):
        trigger = CronTrigger("0 * * * *")
        self.assertIsNotNone(trigger)
        self.assertEqual(trigger.cron_expression, "0 * * * *")

    def test_get_next_fire_time(self):
        trigger = CronTrigger("0 2 * * *")
        next_time = trigger.get_next_fire_time()
        self.assertIsNotNone(next_time)
        self.assertIsInstance(next_time, datetime)


class TestIntervalTrigger(unittest.TestCase):
    def test_interval_trigger_creation(self):
        trigger = IntervalTrigger(3600)
        self.assertEqual(trigger.interval_seconds, 3600)

    def test_should_fire_first_time(self):
        trigger = IntervalTrigger(3600)
        self.assertTrue(trigger.should_fire())

    def test_should_not_fire_immediately(self):
        trigger = IntervalTrigger(3600)
        trigger.last_fire_time = datetime.now().timestamp()
        self.assertFalse(trigger.should_fire())

    def test_get_next_fire_time(self):
        trigger = IntervalTrigger(3600)
        next_time = trigger.get_next_fire_time()
        self.assertIsNotNone(next_time)


class TestOneTimeTrigger(unittest.TestCase):
    def test_one_time_trigger_future(self):
        future_time = datetime.now() + timedelta(hours=1)
        trigger = OneTimeTrigger(future_time)
        self.assertFalse(trigger.should_fire())
        self.assertIsNotNone(trigger.get_next_fire_time())

    def test_one_time_trigger_past(self):
        past_time = datetime.now() - timedelta(hours=1)
        trigger = OneTimeTrigger(past_time)
        self.assertTrue(trigger.should_fire())
        self.assertIsNone(trigger.get_next_fire_time())


class TestWorkflowScheduler(unittest.TestCase):
    def setUp(self):
        self.event_bus = EventBus()
        self.executor = WorkflowExecutor()
        self.scheduler = WorkflowScheduler(self.executor, self.event_bus)

    def test_create_scheduler(self):
        self.assertIsNotNone(self.scheduler)
        self.assertEqual(len(self.scheduler._workflows), 0)
        self.assertEqual(len(self.scheduler._triggers), 0)

    def test_register_workflow(self):
        workflow = Workflow(
            workflow_id="WF-TEST-001",
            name="测试工作流",
            trigger=TriggerConfig(trigger_type=TriggerType.CRON, cron_expression="0 * * * *"),
            schedule=ScheduleConfig(enabled=True),
            tasks=[]
        )
        self.scheduler.register_workflow(workflow)
        self.assertEqual(len(self.scheduler._workflows), 1)
        self.assertIn("WF-TEST-001", self.scheduler._triggers)

    def test_unregister_workflow(self):
        workflow = Workflow(
            workflow_id="WF-TEST-002",
            name="测试工作流2",
            trigger=TriggerConfig(trigger_type=TriggerType.MANUAL),
            schedule=ScheduleConfig(enabled=True),
            tasks=[]
        )
        self.scheduler.register_workflow(workflow)
        self.scheduler.unregister_workflow("WF-TEST-002")
        self.assertEqual(len(self.scheduler._workflows), 0)

    def test_pause_workflow(self):
        workflow = Workflow(
            workflow_id="WF-TEST-003",
            name="测试工作流3",
            enabled=True,
            tasks=[]
        )
        self.scheduler.register_workflow(workflow)
        result = self.scheduler.pause_workflow("WF-TEST-003")
        self.assertTrue(result)
        self.assertFalse(self.scheduler._workflows["WF-TEST-003"].enabled)

    def test_resume_workflow(self):
        workflow = Workflow(
            workflow_id="WF-TEST-004",
            name="测试工作流4",
            enabled=False,
            tasks=[]
        )
        self.scheduler.register_workflow(workflow)
        result = self.scheduler.resume_workflow("WF-TEST-004")
        self.assertTrue(result)
        self.assertTrue(self.scheduler._workflows["WF-TEST-004"].enabled)

    def test_list_scheduled_workflows(self):
        workflow = Workflow(
            workflow_id="WF-TEST-005",
            name="测试工作流5",
            trigger=TriggerConfig(trigger_type=TriggerType.CRON, cron_expression="0 * * * *"),
            schedule=ScheduleConfig(enabled=True),
            tasks=[]
        )
        self.scheduler.register_workflow(workflow)
        workflows = self.scheduler.list_scheduled_workflows()
        self.assertEqual(len(workflows), 1)
        self.assertEqual(workflows[0]["workflow_id"], "WF-TEST-005")


class TestWorkflowSchedulerAsync(unittest.TestCase):
    def setUp(self):
        self.event_bus = EventBus()
        self.executor = WorkflowExecutor()
        self.scheduler = WorkflowScheduler(self.executor, self.event_bus)

    def test_trigger_workflow_manual(self):
        async def test():
            task = TaskDefinition(
                task_id="task-1",
                name="测试任务",
                agent_id="test-agent"
            )
            workflow = Workflow(
                workflow_id="WF-ASYNC-001",
                name="异步测试工作流",
                tasks=[task]
            )
            self.scheduler.register_workflow(workflow)

            execution = await self.scheduler.trigger_workflow(
                "WF-ASYNC-001",
                trigger_type="manual",
                trigger_source="test"
            )
            self.assertIsNotNone(execution)
            self.assertEqual(execution.workflow_id, "WF-ASYNC-001")

        asyncio.run(test())

    def test_trigger_nonexistent_workflow(self):
        async def test():
            execution = await self.scheduler.trigger_workflow("nonexistent")
            self.assertIsNone(execution)

        asyncio.run(test())

    def test_stop_scheduler(self):
        self.scheduler.stop()
        self.assertFalse(self.scheduler._running)


if __name__ == "__main__":
    unittest.main()
