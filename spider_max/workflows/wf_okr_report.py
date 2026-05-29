#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日 OKR Pulse 报告生成工作流
每天 20:00 自动生成人类可读的 OKR 进度报告
"""

import asyncio
import logging
from typing import Dict, Any

try:
    from ..models import Workflow, TaskDefinition, TriggerConfig, ScheduleConfig, TriggerType
    from ..workflow_executor import WorkflowExecutor
except (ImportError, SystemError):
    from models import Workflow, TaskDefinition, TriggerConfig, ScheduleConfig, TriggerType
    from workflow_executor import WorkflowExecutor

logger = logging.getLogger(__name__)


class OKRReportWorkflow:
    """每日报告生成 (人类专属 + OKR)"""
    workflow_id = "WF-OKR-REPORT"
    name = "每日报告"
    description = "每天20:00自动生成: 项目总览 + OKR Pulse报告"

    @staticmethod
    def get_definition() -> Workflow:
        return Workflow(
            workflow_id=OKRReportWorkflow.workflow_id,
            name=OKRReportWorkflow.name,
            description=OKRReportWorkflow.description,
            trigger=TriggerConfig(
                trigger_type=TriggerType.CRON,
                cron_expression="0 20 * * *"
            ),
            schedule=ScheduleConfig(enabled=True),
            tasks=[
                TaskDefinition(
                    task_id="fetch_db",
                    name="读取数据库",
                    description="读取项目和任务数据",
                    agent_id="system-manager"
                ),
                TaskDefinition(
                    task_id="generate_project_overview",
                    name="生成项目总览",
                    description="生成 项目总览.md (人类专属)",
                    agent_id="system-manager",
                    dependencies=["fetch_db"]
                ),
                TaskDefinition(
                    task_id="generate_okr_report",
                    name="生成OKR报告",
                    description="生成 Daily_OKR_Pulse.md (人类专属)",
                    agent_id="system-manager",
                    dependencies=["fetch_db"]
                ),
            ],
            dependencies={
                "fetch_db": [],
                "generate_project_overview": ["fetch_db"],
                "generate_okr_report": ["fetch_db"],
            },
            assigned_agents=["system-manager"]
        )

    @staticmethod
    async def execute(executor: WorkflowExecutor, context: Dict[str, Any]) -> Dict[str, Any]:
        workflow = OKRReportWorkflow.get_definition()
        execution = await executor.execute(workflow, context)
        return {
            "execution_id": execution.execution_id,
            "status": execution.status.value if hasattr(execution.status, 'value') else execution.status
        }
