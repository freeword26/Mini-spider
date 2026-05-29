#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工作流3: 逾期预警
检测并通知逾期任务
"""

try:
    from ..models import Workflow, TaskDefinition, TriggerConfig, ScheduleConfig, TriggerType
except (ImportError, SystemError):
    from models import Workflow, TaskDefinition, TriggerConfig, ScheduleConfig, TriggerType


class OverdueAlertWorkflow:
    workflow_id = "WF-003"
    name = "逾期预警"
    description = "检测逾期任务并发送预警通知"

    @staticmethod
    def get_definition() -> Workflow:
        task1 = TaskDefinition(
            task_id="check_overdue",
            name="检查逾期任务",
            description="检查所有逾期任务",
            agent_id="system-manager"
        )

        task2 = TaskDefinition(
            task_id="generate_alert",
            name="生成预警",
            description="生成预警信息",
            agent_id="system-manager",
            dependencies=["check_overdue"]
        )

        task3 = TaskDefinition(
            task_id="send_notification",
            name="发送通知",
            description="通过飞书发送预警",
            agent_id="system-manager",
            dependencies=["generate_alert"]
        )

        return Workflow(
            workflow_id=OverdueAlertWorkflow.workflow_id,
            name=OverdueAlertWorkflow.name,
            description=OverdueAlertWorkflow.description,
            trigger=TriggerConfig(
                trigger_type=TriggerType.CRON,
                cron_expression="0 9 * * *"
            ),
            schedule=ScheduleConfig(enabled=True),
            tasks=[task1, task2, task3],
            dependencies={
                "check_overdue": [],
                "generate_alert": ["check_overdue"],
                "send_notification": ["generate_alert"]
            },
            assigned_agents=["system-manager"]
        )
