#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wf_lifecycle_scan.py — 统一数据生命周期扫描工作流

调度策略：
  - 每日 02:00：--scan（仅扫描报告）
  - 每周日 03:00：--archive --execute（归档备份，真实执行）
  - 每周日 04:00：--dedup --execute（冗余清理，真实执行）

所有操作遵守 archive_rules.yaml / dedup_rules.yaml 中的保护规则：
  - 根目录文件/目录不碰
  - 活跃项目（spider_diary、spidermax_room 等）不碰
  - 归档只做备份，不删除源文件
"""

import asyncio
import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

try:
    from ..models import Workflow, TaskDefinition, TriggerConfig, ScheduleConfig, TriggerType
except (ImportError, SystemError):
    from models import Workflow, TaskDefinition, TriggerConfig, ScheduleConfig, TriggerType

logger = logging.getLogger(__name__)

_SCRIPT_DIR = Path(__file__).resolve().parent.parent.parent.parent  # E:\软件开发
_ENGINE = _SCRIPT_DIR / "scripts" / "data_lifecycle_engine.py"


# ── 每日扫描（仅报告）────────────────────────────────────────────────────────

class LifecycleDailyScanWorkflow:
    workflow_id = "WF-LIFECYCLE-DAILY"
    name = "每日生命周期扫描"
    description = "扫描归档候选 + 冗余数据，生成报告（不执行删除）"

    @staticmethod
    def get_definition() -> Workflow:
        return Workflow(
            workflow_id=LifecycleDailyScanWorkflow.workflow_id,
            name=LifecycleDailyScanWorkflow.name,
            description=LifecycleDailyScanWorkflow.description,
            trigger=TriggerConfig(
                trigger_type=TriggerType.CRON,
                cron_expression="0 2 * * *"
            ),
            schedule=ScheduleConfig(enabled=True, timezone="Asia/Shanghai"),
            tasks=[
                TaskDefinition(
                    task_id="lifecycle_scan",
                    name="生命周期扫描",
                    description="调用 engine --scan 生成报告",
                    agent_id="janitor-agent",
                ),
            ],
            dependencies={"lifecycle_scan": []},
            assigned_agents=["janitor-agent"],
        )

    @staticmethod
    async def execute(executor, context: dict) -> dict:
        return _run_engine("--scan", context)


# ── 每周归档备份（真实执行）──────────────────────────────────────────────────

class LifecycleWeeklyArchiveWorkflow:
    workflow_id = "WF-LIFECYCLE-ARCHIVE"
    name = "每周归档备份"
    description = "执行归档备份（zip 备份，不删除源文件）"

    @staticmethod
    def get_definition() -> Workflow:
        return Workflow(
            workflow_id=LifecycleWeeklyArchiveWorkflow.workflow_id,
            name=LifecycleWeeklyArchiveWorkflow.name,
            description=LifecycleWeeklyArchiveWorkflow.description,
            trigger=TriggerConfig(
                trigger_type=TriggerType.CRON,
                cron_expression="0 3 * * 0"
            ),
            schedule=ScheduleConfig(enabled=True, timezone="Asia/Shanghai"),
            tasks=[
                TaskDefinition(
                    task_id="lifecycle_archive",
                    name="归档备份执行",
                    description="调用 engine --archive --execute",
                    agent_id="janitor-agent",
                ),
            ],
            dependencies={"lifecycle_archive": []},
            assigned_agents=["janitor-agent"],
        )

    @staticmethod
    async def execute(executor, context: dict) -> dict:
        return _run_engine("--archive --execute", context)


# ── 每周冗余清理（真实执行）──────────────────────────────────────────────────

class LifecycleWeeklyDedupWorkflow:
    workflow_id = "WF-LIFECYCLE-DEDUP"
    name = "每周冗余清理"
    description = "清理重复文件、Python 缓存、临时文件（遵守保护规则）"

    @staticmethod
    def get_definition() -> Workflow:
        return Workflow(
            workflow_id=LifecycleWeeklyDedupWorkflow.workflow_id,
            name=LifecycleWeeklyDedupWorkflow.name,
            description=LifecycleWeeklyDedupWorkflow.description,
            trigger=TriggerConfig(
                trigger_type=TriggerType.CRON,
                cron_expression="0 4 * * 0"
            ),
            schedule=ScheduleConfig(enabled=True, timezone="Asia/Shanghai"),
            tasks=[
                TaskDefinition(
                    task_id="lifecycle_dedup",
                    name="冗余清理执行",
                    description="调用 engine --dedup --execute",
                    agent_id="janitor-agent",
                ),
            ],
            dependencies={"lifecycle_dedup": []},
            assigned_agents=["janitor-agent"],
        )

    @staticmethod
    async def execute(executor, context: dict) -> dict:
        return _run_engine("--dedup --execute", context)


# ── 公共执行器 ────────────────────────────────────────────────────────────────

def _run_engine(args_str: str, context: dict) -> dict:
    if not _ENGINE.exists():
        logger.error(f"[LIFECYCLE] engine not found: {_ENGINE}")
        return {"status": "error", "reason": "engine_not_found"}

    cmd = [sys.executable, str(_ENGINE)] + args_str.split()
    logger.info(f"[LIFECYCLE] 启动: {' '.join(cmd)}")

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True, text=True, timeout=900,
            cwd=str(_ENGINE.parent),
            env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"},
        )
        stdout = proc.stdout.strip()
        stderr = proc.stderr.strip()

        # 提取报告路径
        report_path = ""
        for line in stdout.splitlines():
            if "REPORT" in line or "report" in line.lower() or ".md" in line:
                report_path = line.strip()
                break

        ok = proc.returncode == 0
        logger.info(f"[LIFECYCLE] 完成: rc={proc.returncode}, report={report_path}")

        return {
            "status": "completed" if ok else "failed",
            "returncode": proc.returncode,
            "report_path": report_path,
            "stdout_tail": stdout[-1000:],
            "stderr_tail": stderr[-500:],
        }
    except subprocess.TimeoutExpired:
        logger.error("[LIFECYCLE] 超时")
        return {"status": "timeout"}
    except Exception as e:
        logger.error(f"[LIFECYCLE] 异常: {e}")
        return {"status": "error", "error": str(e)}
