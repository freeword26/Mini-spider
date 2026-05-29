#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工作流11: 文档切片
每日智能文档切片自动执行
"""

try:
    from ..models import Workflow, TaskDefinition, TriggerConfig, ScheduleConfig, TriggerType
except (ImportError, SystemError):
    from models import Workflow, TaskDefinition, TriggerConfig, ScheduleConfig, TriggerType


class DocSliceWorkflow:
    workflow_id = "WF-011"
    name = "文档切片"
    description = "每日智能文档切片自动执行"

    @staticmethod
    def get_definition() -> Workflow:
        task1 = TaskDefinition(
            task_id="scan_documents",
            name="扫描文档",
            description="扫描目标目录中的文档",
            agent_id="learning-hacker"
        )

        task2 = TaskDefinition(
            task_id="analyze_length",
            name="分析长度",
            description="分析字段字节长度",
            agent_id="learning-hacker",
            dependencies=["scan_documents"]
        )

        task3 = TaskDefinition(
            task_id="select_strategy",
            name="选择策略",
            description="选择最优切片策略",
            agent_id="learning-hacker",
            dependencies=["analyze_length"]
        )

        task4 = TaskDefinition(
            task_id="execute_slice",
            name="执行切片",
            description="执行UTF-8安全切片",
            agent_id="learning-hacker",
            dependencies=["select_strategy"]
        )

        task5 = TaskDefinition(
            task_id="verify_result",
            name="验证结果",
            description="验证切片结果",
            agent_id="learning-hacker",
            dependencies=["execute_slice"]
        )

        task6 = TaskDefinition(
            task_id="update_storage",
            name="更新存储",
            description="更新原始文档存储",
            agent_id="learning-hacker",
            dependencies=["verify_result"]
        )

        task7 = TaskDefinition(
            task_id="generate_report",
            name="生成报告",
            description="生成执行报告",
            agent_id="learning-hacker",
            dependencies=["update_storage"]
        )

        return Workflow(
            workflow_id=DocSliceWorkflow.workflow_id,
            name=DocSliceWorkflow.name,
            description=DocSliceWorkflow.description,
            trigger=TriggerConfig(
                trigger_type=TriggerType.CRON,
                cron_expression="0 20 * * *"
            ),
            schedule=ScheduleConfig(enabled=True),
            tasks=[task1, task2, task3, task4, task5, task6, task7],
            dependencies={
                "scan_documents": [],
                "analyze_length": ["scan_documents"],
                "select_strategy": ["analyze_length"],
                "execute_slice": ["select_strategy"],
                "verify_result": ["execute_slice"],
                "update_storage": ["verify_result"],
                "generate_report": ["update_storage"]
            },
            assigned_agents=["learning-hacker"]
        )
