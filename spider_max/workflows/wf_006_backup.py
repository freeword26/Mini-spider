#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工作流6: 数据库备份
自动备份数据库
"""

try:
    from ..models import Workflow, TaskDefinition, TriggerConfig, ScheduleConfig, TriggerType
except (ImportError, SystemError):
    from models import Workflow, TaskDefinition, TriggerConfig, ScheduleConfig, TriggerType


class BackupWorkflow:
    workflow_id = "WF-006"
    name = "数据库备份"
    description = "定期备份数据库到备份存储"

    @staticmethod
    def get_definition() -> Workflow:
        task1 = TaskDefinition(
            task_id="create_snapshot",
            name="创建快照",
            description="创建数据库快照",
            agent_id="tech-expert"
        )

        task2 = TaskDefinition(
            task_id="transfer_data",
            name="传输数据",
            description="传输备份数据到存储",
            agent_id="tech-expert",
            dependencies=["create_snapshot"]
        )

        task3 = TaskDefinition(
            task_id="verify_backup",
            name="验证备份",
            description="验证备份完整性",
            agent_id="tech-expert",
            dependencies=["transfer_data"]
        )

        task4 = TaskDefinition(
            task_id="cleanup_old",
            name="清理旧备份",
            description="清理过期的备份",
            agent_id="tech-expert",
            dependencies=["verify_backup"]
        )

        return Workflow(
            workflow_id=BackupWorkflow.workflow_id,
            name=BackupWorkflow.name,
            description=BackupWorkflow.description,
            trigger=TriggerConfig(
                trigger_type=TriggerType.CRON,
                cron_expression="0 2 * * *"
            ),
            schedule=ScheduleConfig(enabled=True),
            tasks=[task1, task2, task3, task4],
            dependencies={
                "create_snapshot": [],
                "transfer_data": ["create_snapshot"],
                "verify_backup": ["transfer_data"],
                "cleanup_old": ["verify_backup"]
            },
            assigned_agents=["tech-expert"]
        )
