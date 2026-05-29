#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工作流12: 上下文追踪
对话上下文自动记录与切片
"""

try:
    from ..models import Workflow, TaskDefinition, TriggerConfig, ScheduleConfig, TriggerType
except (ImportError, SystemError):
    from models import Workflow, TaskDefinition, TriggerConfig, ScheduleConfig, TriggerType


class ContextTrackWorkflow:
    workflow_id = "WF-012"
    name = "上下文追踪"
    description = "对话上下文自动记录与切片"

    @staticmethod
    def get_definition() -> Workflow:
        task1 = TaskDefinition(
            task_id="record_message",
            name="记录消息",
            description="记录每条消息到上下文",
            agent_id="learning-hacker"
        )

        task2 = TaskDefinition(
            task_id="calculate_bytes",
            name="计算字节",
            description="计算上下文字节数",
            agent_id="learning-hacker",
            dependencies=["record_message"]
        )

        task3 = TaskDefinition(
            task_id="extract_info",
            name="提取信息",
            description="提取关键信息",
            agent_id="learning-hacker",
            dependencies=["calculate_bytes"]
        )

        task4 = TaskDefinition(
            task_id="check_threshold",
            name="检查阈值",
            description="检查字节阈值",
            agent_id="learning-hacker",
            dependencies=["extract_info"]
        )

        task5 = TaskDefinition(
            task_id="slice_if_needed",
            name="必要切片",
            description="超限时自动切片存档",
            agent_id="learning-hacker",
            dependencies=["check_threshold"]
        )

        return Workflow(
            workflow_id=ContextTrackWorkflow.workflow_id,
            name=ContextTrackWorkflow.name,
            description=ContextTrackWorkflow.description,
            trigger=TriggerConfig(
                trigger_type=TriggerType.EVENT,
                event_name="message_received"
            ),
            schedule=ScheduleConfig(enabled=True),
            tasks=[task1, task2, task3, task4, task5],
            dependencies={
                "record_message": [],
                "calculate_bytes": ["record_message"],
                "extract_info": ["calculate_bytes"],
                "check_threshold": ["extract_info"],
                "slice_if_needed": ["check_threshold"]
            },
            assigned_agents=["learning-hacker"]
        )
