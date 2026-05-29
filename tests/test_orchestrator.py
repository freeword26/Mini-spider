#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
编排调度器单元测试
"""

import unittest
import asyncio

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Workflow, TaskDefinition, ExecutionStatus
from workflow_executor import WorkflowExecutor
from event_bus import EventBus
from orchestrator import Orchestrator, CollaborationMode


class TestOrchestrator(unittest.TestCase):
    def setUp(self):
        self.event_bus = EventBus()
        self.executor = WorkflowExecutor()
        self.orchestrator = Orchestrator(self.event_bus, self.executor)

    def test_create_orchestrator(self):
        self.assertIsNotNone(self.orchestrator)
        self.assertIn("pmo", self.orchestrator.get_supported_modes())
        self.assertIn("dag", self.orchestrator.get_supported_modes())
        self.assertIn("sop", self.orchestrator.get_supported_modes())
        self.assertIn("blackboard", self.orchestrator.get_supported_modes())
        self.assertIn("meta", self.orchestrator.get_supported_modes())

    def test_set_default_mode(self):
        result = self.orchestrator.set_default_mode("pmo")
        self.assertTrue(result)
        self.assertEqual(self.orchestrator._default_mode, CollaborationMode.PMO)

    def test_set_invalid_mode(self):
        result = self.orchestrator.set_default_mode("invalid_mode")
        self.assertFalse(result)


class TestOrchestratorAsync(unittest.TestCase):
    def setUp(self):
        self.event_bus = EventBus()
        self.executor = WorkflowExecutor()
        self.orchestrator = Orchestrator(self.event_bus, self.executor)

    def test_execute_workflow_dag_mode(self):
        async def test():
            tasks = [
                TaskDefinition(
                    task_id="task-1",
                    name="任务1",
                    agent_id="agent-1"
                ),
                TaskDefinition(
                    task_id="task-2",
                    name="任务2",
                    agent_id="agent-2",
                    dependencies=["task-1"]
                )
            ]

            workflow = Workflow(
                workflow_id="WF-ORCH-001",
                name="编排测试工作流",
                tasks=tasks,
                dependencies={"task-1": [], "task-2": ["task-1"]}
            )

            result = await self.orchestrator.execute_workflow(
                workflow,
                mode="dag"
            )

            self.assertIsNotNone(result)
            self.assertEqual(result["workflow_id"], "WF-ORCH-001")
            self.assertEqual(result["mode"], "dag")

        asyncio.run(test())

    def test_execute_workflow_pmo_mode(self):
        async def test():
            tasks = [
                TaskDefinition(
                    task_id="plan",
                    name="规划",
                    agent_id="pmo-agent"
                ),
                TaskDefinition(
                    task_id="execute",
                    name="执行",
                    agent_id="exec-agent"
                )
            ]

            workflow = Workflow(
                workflow_id="WF-PMO-001",
                name="PMO测试",
                tasks=tasks
            )

            result = await self.orchestrator.execute_workflow(
                workflow,
                mode="pmo"
            )

            self.assertEqual(result["mode"], "pmo")

        asyncio.run(test())

    def test_execute_workflow_sop_mode(self):
        async def test():
            tasks = [
                TaskDefinition(
                    task_id="step1",
                    name="步骤1",
                    agent_id="sop-agent"
                ),
                TaskDefinition(
                    task_id="step2",
                    name="步骤2",
                    agent_id="sop-agent"
                )
            ]

            workflow = Workflow(
                workflow_id="WF-SOP-001",
                name="SOP测试",
                tasks=tasks
            )

            result = await self.orchestrator.execute_workflow(
                workflow,
                mode="sop"
            )

            self.assertEqual(result["mode"], "sop")

        asyncio.run(test())


if __name__ == "__main__":
    unittest.main()
