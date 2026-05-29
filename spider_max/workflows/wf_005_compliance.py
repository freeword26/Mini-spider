#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工作流5: 合规检查
检查数据合规性
"""

try:
    from ..models import Workflow, TaskDefinition, TriggerConfig, ScheduleConfig, TriggerType
except (ImportError, SystemError):
    from models import Workflow, TaskDefinition, TriggerConfig, ScheduleConfig, TriggerType


class ComplianceWorkflow:
    workflow_id = "WF-005"
    name = "合规检查"
    description = "检查数据处理是否符合合规要求"

    @staticmethod
    def get_definition() -> Workflow:
        task1 = TaskDefinition(
            task_id="scan_data",
            name="扫描数据",
            description="扫描敏感数据",
            agent_id="expert-biz-doctor"
        )

        task2 = TaskDefinition(
            task_id="check_rules",
            name="检查规则",
            description="检查合规规则",
            agent_id="expert-biz-doctor",
            dependencies=["scan_data"]
        )

        task3 = TaskDefinition(
            task_id="generate_report",
            name="生成报告",
            description="生成合规报告",
            agent_id="expert-biz-doctor",
            dependencies=["check_rules"]
        )

        return Workflow(
            workflow_id=ComplianceWorkflow.workflow_id,
            name=ComplianceWorkflow.name,
            description=ComplianceWorkflow.description,
            trigger=TriggerConfig(
                trigger_type=TriggerType.EVENT,
                event_name="data_processed"
            ),
            schedule=ScheduleConfig(enabled=True),
            tasks=[task1, task2, task3],
            dependencies={
                "scan_data": [],
                "check_rules": ["scan_data"],
                "generate_report": ["check_rules"]
            },
            assigned_agents=["expert-biz-doctor"]
        )
