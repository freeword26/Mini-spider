#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""WF-08: 系统日志自动分析"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any
from pathlib import Path

try:
    from ..models import Workflow, TaskDefinition, TriggerConfig, ScheduleConfig, TriggerType
    from ..workflow_executor import WorkflowExecutor
except (ImportError, SystemError):
    from models import Workflow, TaskDefinition, TriggerConfig, ScheduleConfig, TriggerType
    from workflow_executor import WorkflowExecutor

logger = logging.getLogger(__name__)


class LogAnalysisWorkflow:
    workflow_id = "WF-008"
    name = "系统日志自动分析"
    description = "每小时分析系统日志，检测异常并生成告警"

    @staticmethod
    def get_definition() -> Workflow:
        tasks = [
            TaskDefinition(task_id="collect_logs", name="收集日志",
                          description="收集各模块日志文件", agent_id="system-manager"),
            TaskDefinition(task_id="analyze_errors", name="分析错误",
                          description="检测ERROR/WARN级别日志", agent_id="system-manager",
                          dependencies=["collect_logs"]),
            TaskDefinition(task_id="detect_anomalies", name="异常检测",
                          description="识别异常模式并统计", agent_id="system-manager",
                          dependencies=["analyze_errors"]),
            TaskDefinition(task_id="generate_report", name="生成报告",
                          description="生成日志分析报告", agent_id="system-manager",
                          dependencies=["detect_anomalies"]),
        ]
        return Workflow(
            workflow_id=LogAnalysisWorkflow.workflow_id, name=LogAnalysisWorkflow.name,
            description=LogAnalysisWorkflow.description,
            trigger=TriggerConfig(trigger_type=TriggerType.CRON, cron_expression="0 * * * *"),
            schedule=ScheduleConfig(enabled=True, timezone="Asia/Shanghai"),
            tasks=tasks,
            dependencies={"collect_logs": [], "analyze_errors": ["collect_logs"],
                         "detect_anomalies": ["analyze_errors"],
                         "generate_report": ["detect_anomalies"]},
            assigned_agents=["system-manager"]
        )

    @staticmethod
    async def execute(executor, context):
        workflow = LogAnalysisWorkflow.get_definition()
        execution = await executor.execute(workflow, context)
        log_dir = Path(context.get("log_dir", "logs"))
        report = {
            "timestamp": datetime.now().isoformat(),
            "log_dir": str(log_dir),
            "status": "analyzed",
            "errors_found": 0,
            "warnings_found": 0,
        }
        if log_dir.exists():
            error_count = 0
            warn_count = 0
            for log_file in log_dir.glob("*.log"):
                try:
                    content = log_file.read_text(encoding="utf-8", errors="ignore")
                    error_count += content.lower().count("error")
                    warn_count += content.lower().count("warn")
                except Exception:
                    pass
            report["errors_found"] = error_count
            report["warnings_found"] = warn_count
            report["log_files"] = len(list(log_dir.glob("*.log")))
        return report
