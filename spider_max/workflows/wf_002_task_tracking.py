#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工作流2: 任务跟踪
跟踪任务状态，更新进度
"""

try:
    from ..models import Workflow, TaskDefinition, TriggerConfig, ScheduleConfig, TriggerType
except (ImportError, SystemError):
    from models import Workflow, TaskDefinition, TriggerConfig, ScheduleConfig, TriggerType


class TaskTrackingWorkflow:
    workflow_id = "WF-002"
    name = "任务跟踪"
    description = "自动跟踪任务状态，检测逾期任务"

    @staticmethod
    def get_definition() -> Workflow:
        task1 = TaskDefinition(
            task_id="scan_tasks",
            name="扫描任务",
            description="扫描所有任务状态",
            agent_id="skill-manager"
        )

        task2 = TaskDefinition(
            task_id="detect_overdue",
            name="检测逾期",
            description="识别逾期任务",
            agent_id="skill-manager",
            dependencies=["scan_tasks"]
        )

        task3 = TaskDefinition(
            task_id="update_status",
            name="更新状态",
            description="更新任务状态",
            agent_id="skill-manager",
            dependencies=["detect_overdue"]
        )

        return Workflow(
            workflow_id=TaskTrackingWorkflow.workflow_id,
            name=TaskTrackingWorkflow.name,
            description=TaskTrackingWorkflow.description,
            trigger=TriggerConfig(
                trigger_type=TriggerType.CRON,
                cron_expression="0 */2 * * *"
            ),
            schedule=ScheduleConfig(enabled=True),
            tasks=[task1, task2, task3],
            dependencies={
                "scan_tasks": [],
                "detect_overdue": ["scan_tasks"],
                "update_status": ["detect_overdue"]
            },
            assigned_agents=["skill-manager"]
        )
