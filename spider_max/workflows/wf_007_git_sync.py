#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""WF-07: GitHub自动同步与备份"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any

try:
    from ..models import Workflow, TaskDefinition, TriggerConfig, ScheduleConfig, TriggerType
    from ..workflow_executor import WorkflowExecutor
except (ImportError, SystemError):
    from models import Workflow, TaskDefinition, TriggerConfig, ScheduleConfig, TriggerType
    from workflow_executor import WorkflowExecutor

logger = logging.getLogger(__name__)


class GitHubSyncWorkflow:
    workflow_id = "WF-007"
    name = "GitHub自动同步与备份"
    description = "每日自动同步代码并通过git push备份到GitHub"

    @staticmethod
    def get_definition() -> Workflow:
        tasks = [
            TaskDefinition(task_id="git_status", name="检查Git状态",
                          description="检查本地仓库变更状态", agent_id="devops"),
            TaskDefinition(task_id="git_add", name="暂存变更",
                          description="git add 所有变更文件", agent_id="devops",
                          dependencies=["git_status"]),
            TaskDefinition(task_id="git_commit", name="提交变更",
                          description="自动提交变更并附带时间戳", agent_id="devops",
                          dependencies=["git_add"]),
            TaskDefinition(task_id="git_push", name="推送至GitHub",
                          description="git push 到远程仓库", agent_id="devops",
                          dependencies=["git_commit"]),
            TaskDefinition(task_id="backup_verify", name="验证备份",
                          description="确认GitHub仓库更新成功", agent_id="devops",
                          dependencies=["git_push"]),
        ]
        return Workflow(
            workflow_id=GitHubSyncWorkflow.workflow_id, name=GitHubSyncWorkflow.name,
            description=GitHubSyncWorkflow.description,
            trigger=TriggerConfig(trigger_type=TriggerType.CRON, cron_expression="0 0 * * *"),
            schedule=ScheduleConfig(enabled=True, timezone="Asia/Shanghai"),
            tasks=tasks,
            dependencies={"git_status": [], "git_add": ["git_status"],
                         "git_commit": ["git_add"], "git_push": ["git_commit"],
                         "backup_verify": ["git_push"]},
            assigned_agents=["devops"]
        )

    @staticmethod
    async def execute(executor, context):
        import subprocess, os
        workflow = GitHubSyncWorkflow.get_definition()
        results = {}
        base_path = context.get("base_path", ".")
        try:
            os.chdir(base_path)
            r = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, timeout=30)
            results["status"] = r.stdout.strip()
            r = subprocess.run(["git", "add", "."], capture_output=True, text=True, timeout=30)
            results["add"] = "ok" if r.returncode == 0 else r.stderr
            ts = datetime.now().strftime("%Y-%m-%d %H:%M")
            r = subprocess.run(["git", "commit", "-m", f"auto backup {ts}"],
                               capture_output=True, text=True, timeout=30)
            results["commit"] = "ok" if r.returncode == 0 else r.stderr
            r = subprocess.run(["git", "push"], capture_output=True, text=True, timeout=60)
            results["push"] = "ok" if r.returncode == 0 else r.stderr
        except Exception as e:
            results["error"] = str(e)
        return results
