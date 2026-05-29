#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工作流执行器单元测试
"""

import unittest
import asyncio
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import (
    Workflow, TaskDefinition, Execution, ExecutionStatus,
    RetryConfig, CircuitBreakerConfig, TriggerConfig, ScheduleConfig
)
from workflow_executor import WorkflowExecutor, CircuitBreaker


class TestCircuitBreaker(unittest.TestCase):
    def setUp(self):
        self.cb = CircuitBreaker(
            config=CircuitBreakerConfig(
                failure_threshold=3,
                success_threshold=2,
                timeout=1
            )
        )

    def test_initial_state(self):
        self.assertEqual(self.cb.state, "closed")
        self.assertFalse(self.cb.is_open())

    def test_record_success(self):
        self.cb.record_success()
        self.assertEqual(self.cb.success_count, 1)
        self.assertEqual(self.cb.failure_count, 0)

    def test_record_failure(self):
        self.cb.record_failure()
        self.assertEqual(self.cb.failure_count, 1)

    def test_circuit_opens_after_threshold(self):
        for _ in range(3):
            self.cb.record_failure()
        self.assertEqual(self.cb.state, "open")
        self.assertTrue(self.cb.is_open())

    def test_circuit_half_open_after_timeout(self):
        for _ in range(3):
            self.cb.record_failure()

        self.cb.last_failure_time = 0
        self.assertFalse(self.cb.is_open())
        self.assertEqual(self.cb.state, "half_open")

    def test_can_execute(self):
        self.assertTrue(self.cb.can_execute())
        for _ in range(3):
            self.cb.record_failure()
        self.assertFalse(self.cb.can_execute())


class TestWorkflowExecutor(unittest.TestCase):
    def setUp(self):
        self.executor = WorkflowExecutor()

    def test_create_executor(self):
        self.assertIsNotNone(self.executor)
        self.assertIsNotNone(self.executor.circuit_breaker)

    def test_get_circuit_breaker_status(self):
        status = self.executor.get_circuit_breaker_status()
        self.assertIn("state", status)
        self.assertIn("failure_count", status)
        self.assertIn("is_open", status)

    def test_list_executions_empty(self):
        executions = self.executor.list_executions()
        self.assertEqual(len(executions), 0)

    def test_get_execution_not_found(self):
        result = self.executor.get_execution("nonexistent")
        self.assertIsNone(result)


class TestWorkflow(unittest.TestCase):
    def test_workflow_to_dict(self):
        workflow = Workflow(
            workflow_id="WF-TEST-001",
            name="测试工作流",
            description="测试描述"
        )
        data = workflow.to_dict()
        self.assertEqual(data["workflow_id"], "WF-TEST-001")
        self.assertEqual(data["name"], "测试工作流")

    def test_workflow_from_dict(self):
        data = {
            "workflow_id": "WF-TEST-002",
            "name": "测试工作流2",
            "description": "测试描述2",
            "version": "1.0.0",
            "enabled": True,
            "trigger": {"trigger_type": "manual"},
            "schedule": {"enabled": True},
            "retry": {"max_attempts": 3},
            "circuit_breaker": {"failure_threshold": 5},
            "tasks": [],
            "dependencies": {},
            "assigned_agents": [],
            "priority": 3,
            "created_at": "2026-05-18T00:00:00",
            "updated_at": "2026-05-18T00:00:00",
            "created_by": "test"
        }
        workflow = Workflow.from_dict(data)
        self.assertEqual(workflow.workflow_id, "WF-TEST-002")
        self.assertEqual(workflow.name, "测试工作流2")


class TestTaskDefinition(unittest.TestCase):
    def test_task_to_dict(self):
        task = TaskDefinition(
            task_id="task-1",
            name="测试任务",
            description="测试任务描述",
            agent_id="test-agent"
        )
        data = task.to_dict()
        self.assertEqual(data["task_id"], "task-1")
        self.assertEqual(data["agent_id"], "test-agent")

    def test_task_from_dict(self):
        data = {
            "task_id": "task-2",
            "name": "测试任务2",
            "description": "描述",
            "agent_id": "agent-2",
            "dependencies": [],
            "input_mapping": {},
            "output_mapping": {},
            "timeout": 300,
            "retry": {"max_attempts": 3},
            "continue_on_failure": False
        }
        task = TaskDefinition.from_dict(data)
        self.assertEqual(task.task_id, "task-2")
        self.assertEqual(task.retry.max_attempts, 3)


class TestExecution(unittest.TestCase):
    def test_execution_to_dict(self):
        execution = Execution(
            execution_id="exec-001",
            workflow_id="WF-001",
            status=ExecutionStatus.COMPLETED
        )
        data = execution.to_dict()
        self.assertEqual(data["execution_id"], "exec-001")
        self.assertEqual(data["status"], "completed")

    def test_execution_from_dict(self):
        data = {
            "execution_id": "exec-002",
            "workflow_id": "WF-002",
            "status": "failed",
            "task_executions": [],
            "retry_count": 0,
            "max_retries": 3,
            "trigger_type": "manual"
        }
        execution = Execution.from_dict(data)
        self.assertEqual(execution.execution_id, "exec-002")
        self.assertEqual(execution.status, ExecutionStatus.FAILED)


if __name__ == "__main__":
    unittest.main()
