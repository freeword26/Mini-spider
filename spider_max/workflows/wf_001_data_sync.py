#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工作流1: 数据同步
从飞书等数据源同步数据
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any

try:
    from ..models import Workflow, TaskDefinition, TriggerConfig, ScheduleConfig, TriggerType
    from ..workflow_executor import WorkflowExecutor
    from ..event_bus import EventBus
except (ImportError, SystemError):
    from models import Workflow, TaskDefinition, TriggerConfig, ScheduleConfig, TriggerType
    from workflow_executor import WorkflowExecutor
    from event_bus import EventBus

logger = logging.getLogger(__name__)


class DataSyncWorkflow:
    workflow_id = "WF-001"
    name = "数据同步"
    description = "从飞书等数据源同步数据到本地"

    @staticmethod
    def get_definition() -> Workflow:
        task1 = TaskDefinition(
            task_id="fetch_data",
            name="获取远程数据",
            description="从飞书API获取最新数据",
            agent_id="data-scientist"
        )

        task2 = TaskDefinition(
            task_id="transform_data",
            name="数据转换",
            description="将数据转换为目标格式",
            agent_id="data-scientist",
            dependencies=["fetch_data"]
        )

        task3 = TaskDefinition(
            task_id="save_data",
            name="保存数据",
            description="保存到本地存储",
            agent_id="data-scientist",
            dependencies=["transform_data"]
        )

        task4 = TaskDefinition(
            task_id="update_index",
            name="更新索引",
            description="更新数据索引",
            agent_id="data-scientist",
            dependencies=["save_data"]
        )

        return Workflow(
            workflow_id=DataSyncWorkflow.workflow_id,
            name=DataSyncWorkflow.name,
            description=DataSyncWorkflow.description,
            trigger=TriggerConfig(
                trigger_type=TriggerType.INTERVAL,
                interval_seconds=1800
            ),
            schedule=ScheduleConfig(enabled=True),
            tasks=[task1, task2, task3, task4],
            dependencies={
                "fetch_data": [],
                "transform_data": ["fetch_data"],
                "save_data": ["transform_data"],
                "update_index": ["save_data"]
            },
            assigned_agents=["data-scientist"]
        )

    @staticmethod
    async def execute(executor: WorkflowExecutor, context: Dict[str, Any]) -> Dict[str, Any]:
        workflow = DataSyncWorkflow.get_definition()
        execution = await executor.execute(workflow, context)
        return {
            "execution_id": execution.execution_id,
            "status": execution.status.value if hasattr(execution.status, 'value') else execution.status
        }
