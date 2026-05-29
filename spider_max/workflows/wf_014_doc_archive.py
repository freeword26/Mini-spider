#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wf_014_doc_archive.py — 文档归档工作流 v2
对接 data_lifecycle_engine.py 统一规则引擎

变化：
- 旧逻辑（scan→classify→compress→move）→ 替换为 engine.scan() + engine.archive()
- 归档只做 zip 备份，不删除源文件
- 受保护文件/目录/项目自动跳过
- Cron: 每周六 22:00（低峰期）
"""

import asyncio
import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path

try:
    from ..models import Workflow, TaskDefinition, TriggerConfig, ScheduleConfig, TriggerType
except (ImportError, SystemError):
    from models import Workflow, TaskDefinition, TriggerConfig, ScheduleConfig, TriggerType

logger = logging.getLogger(__name__)


import os
from pathlib import Path

# 向上追溯到根目录 E:\软件工程\
_SCRIPT_DIR = Path(__file__).resolve().parent.parent.parent.parent  # E:\软件开发
ENGINE_SCRIPT = _SCRIPT_DIR / "scripts" / "data_lifecycle_engine.py"


class DocArchiveWorkflow:
    workflow_id = "WF-014"
    name = "文档归档"
    description = "基于统一规则的文档归档备份（不删除源文件）"

    @staticmethod
    def get_definition() -> Workflow:
        return Workflow(
            workflow_id=DocArchiveWorkflow.workflow_id,
            name=DocArchiveWorkflow.name,
            description=DocArchiveWorkflow.description,
            trigger=TriggerConfig(
                trigger_type=TriggerType.CRON,
                cron_expression="0 22 * * 6"
            ),
            schedule=ScheduleConfig(enabled=True),
            tasks=[
                TaskDefinition(
                    task_id="lifecycle_archive",
                    name="归档备份扫描",
                    description="调用 data_lifecycle_engine 执行归档备份（dry-run）",
                    agent_id="learning-hacker",
                ),
            ],
            dependencies={"lifecycle_archive": []},
            assigned_agents=["learning-hacker"],
        )

    @staticmethod
    async def execute(executor, context: dict) -> dict:
        dry_run = context.get("dry_run", True)
        project = context.get("project", None)

        cmd = [sys.executable, str(ENGINE_SCRIPT), "--archive"]
        if dry_run:
            cmd.append("--dry-run")
        else:
            cmd.append("--execute")
        if project:
            cmd.extend(["--project", project])

        logger.info(f"[WF-014] 归档启动: {'dry-run' if dry_run else 'execute'}, project={project}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True, text=True, timeout=600,
                cwd=str(ENGINE_SCRIPT.parent),
                env={**__import__("os").environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"},
            )
            stdout = result.stdout.strip()
            stderr = result.stderr.strip()
            logger.info(f"[WF-014] 归档完成: rc={result.returncode}")
            if stdout:
                logger.info(f"[WF-014] stdout: {stdout[:500]}")
            if stderr:
                logger.warning(f"[WF-014] stderr: {stderr[:300]}")

            return {
                "status": "completed" if result.returncode == 0 else "failed",
                "returncode": result.returncode,
                "stdout": stdout[-2000:],
                "stderr": stderr[-500:],
                "engine": "data_lifecycle_engine.v2",
                "dry_run": dry_run,
            }
        except subprocess.TimeoutExpired:
            logger.error("[WF-014] 归档超时")
            return {"status": "timeout", "engine": "data_lifecycle_engine.v2"}
        except Exception as e:
            logger.error(f"[WF-014] 归档异常: {e}")
            return {"status": "error", "error": str(e), "engine": "data_lifecycle_engine.v2"}
