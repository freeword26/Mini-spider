#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工作流13: Agent对话收集存储
全Agents对话收集存储
"""

try:
    from ..models import Workflow, TaskDefinition, TriggerConfig, ScheduleConfig, TriggerType
except (ImportError, SystemError):
    from models import Workflow, TaskDefinition, TriggerConfig, ScheduleConfig, TriggerType


class AgentCollectWorkflow:
    workflow_id = "WF-013"
    name = "Agent对话收集"
    description = "全Agents对话收集存储"

    @staticmethod
    def get_definition() -> Workflow:
        task1 = TaskDefinition(
            task_id="scan_agent_logs",
            name="扫描Agent日志",
            description="扫描各Agent对话日志源",
            agent_id="learning-hacker"
        )

        task2 = TaskDefinition(
            task_id="capture_messages",
            name="捕获消息",
            description="捕获新对话消息",
            agent_id="learning-hacker",
            dependencies=["scan_agent_logs"]
        )

        task3 = TaskDefinition(
            task_id="parse_structure",
            name="解析结构",
            description="解析消息结构",
            agent_id="learning-hacker",
            dependencies=["capture_messages"]
        )

        task4 = TaskDefinition(
            task_id="extract_info",
            name="提取信息",
            description="提取关键信息",
            agent_id="learning-hacker",
            dependencies=["parse_structure"]
        )

        task5 = TaskDefinition(
            task_id="store_hot_layer",
            name="存储热层",
            description="存储到热层目录",
            agent_id="learning-hacker",
            dependencies=["extract_info"]
        )

        task6 = TaskDefinition(
            task_id="check_lifecycle",
            name="检查生命周期",
            description="检查生命周期",
            agent_id="learning-hacker",
            dependencies=["store_hot_layer"]
        )

        task7 = TaskDefinition(
            task_id="update_index",
            name="更新索引",
            description="更新索引",
            agent_id="learning-hacker",
            dependencies=["check_lifecycle"]
        )

        task8 = TaskDefinition(
            task_id="generate_report",
            name="生成报告",
            description="生成收集报告",
            agent_id="learning-hacker",
            dependencies=["update_index"]
        )

        return Workflow(
            workflow_id=AgentCollectWorkflow.workflow_id,
            name=AgentCollectWorkflow.name,
            description=AgentCollectWorkflow.description,
            trigger=TriggerConfig(
                trigger_type=TriggerType.INTERVAL,
                interval_seconds=21600
            ),
            schedule=ScheduleConfig(enabled=True),
            tasks=[task1, task2, task3, task4, task5, task6, task7, task8],
            dependencies={
                "scan_agent_logs": [],
                "capture_messages": ["scan_agent_logs"],
                "parse_structure": ["capture_messages"],
                "extract_info": ["parse_structure"],
                "store_hot_layer": ["extract_info"],
                "check_lifecycle": ["store_hot_layer"],
                "update_index": ["check_lifecycle"],
                "generate_report": ["update_index"]
            },
            assigned_agents=["learning-hacker"]
        )
