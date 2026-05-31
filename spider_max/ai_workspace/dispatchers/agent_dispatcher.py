#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AgentDispatcher — 多智能体异步任务编排器
拆分复杂任务为子任务，派发给多个Agent并行执行，收集结果合并输出。

核心流程:
  1. TaskSplitter 分析任务 → 拆分为独立子任务
  2. AgentDispatcher 派发子任务 → 多个Agent并行执行
  3. ResultCollector 收集结果 → 合并输出
"""

import asyncio
import logging
import uuid
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class AgentRole(str, Enum):
    RECOVERY = "recovery_agent"
    MONITORING = "monitoring_agent"
    DOCUMENTATION = "doc_agent"
    NOTIFICATION = "notification_agent"
    DEPLOYMENT = "deployment_agent"


@dataclass
class SubTask:
    task_id: str
    title: str
    description: str
    agent_role: AgentRole
    priority: int = 1
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Dict] = None
    error: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    timeout_seconds: int = 300
    dependencies: List[str] = field(default_factory=list)


@dataclass
class TaskResult:
    task_id: str
    title: str
    status: TaskStatus
    result: Dict[str, Any]
    duration_seconds: float
    agent_role: AgentRole
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class TaskSplitter:
    """分析复杂任务，拆分为可独立执行的子任务"""

    @staticmethod
    def split_task(task_description: str, context: Optional[Dict] = None) -> List[SubTask]:
        """
        根据任务描述自动拆分。当前支持的任务类型：
        - "disaster_recovery": 灾难恢复（备份+回滚+告警+重建+文档）
        - "deployment": 部署升级（构建+测试+验证+通知）
        - "monitoring_setup": 监控配置（采集+告警+通知+报告）
        - 默认：返回单一子任务
        """
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        context = context or {}

        task_type = context.get("type", "generic")

        if task_type == "disaster_recovery":
            return [
                SubTask(task_id=f"{task_id}_backup", title="数据库备份",
                        description="自动备份数据库到指定目录，保留最近7天",
                        agent_role=AgentRole.RECOVERY, priority=1),
                SubTask(task_id=f"{task_id}_config", title="配置快照管理",
                        description="配置变更时自动保存快照，支持10秒内回滚",
                        agent_role=AgentRole.RECOVERY, priority=2),
                SubTask(task_id=f"{task_id}_config_dep", title="部署回滚验证",
                        description="错误配置后自动回滚到上一可用版本",
                        agent_role=AgentRole.RECOVERY, priority=3,
                        dependencies=[f"{task_id}_config"]),
                SubTask(task_id=f"{task_id}_monitor", title="系统监控告警",
                        description="CPU/内存/磁盘监控，超阈值自动发送告警通知",
                        agent_role=AgentRole.MONITORING, priority=2),
                SubTask(task_id=f"{task_id}_alert", title="异步通知投递",
                        description="告警通知通过飞书/邮件/Webhook异步投递",
                        agent_role=AgentRole.NOTIFICATION, priority=3,
                        dependencies=[f"{task_id}_monitor"]),
                SubTask(task_id=f"{task_id}_rebuild", title="一键重建脚本",
                        description="从Git仓库一键重建完整运行环境，目标<5分钟",
                        agent_role=AgentRole.DEPLOYMENT, priority=2),
                SubTask(task_id=f"{task_id}_docs", title="运维文档生成",
                        description="运行手册/故障排查/成本报告/升级流程/联系人清单",
                        agent_role=AgentRole.DOCUMENTATION, priority=3),
            ]

        if task_type == "deployment":
            return [
                SubTask(task_id=f"{task_id}_build", title="构建Docker镜像",
                        description="自动构建Spider MAX Docker镜像",
                        agent_role=AgentRole.DEPLOYMENT, priority=1),
                SubTask(task_id=f"{task_id}_test", title="运行测试验证",
                        description="运行单元测试和集成测试",
                        agent_role=AgentRole.DEPLOYMENT, priority=2,
                        dependencies=[f"{task_id}_build"]),
                SubTask(task_id=f"{task_id}_push", title="推送GitHub",
                        description="自动提交并推送到GitHub仓库",
                        agent_role=AgentRole.DEPLOYMENT, priority=3,
                        dependencies=[f"{task_id}_test"]),
                SubTask(task_id=f"{task_id}_notify", title="通知团队",
                        description="推送部署通知到飞书/邮件",
                        agent_role=AgentRole.NOTIFICATION, priority=4,
                        dependencies=[f"{task_id}_push"]),
            ]

        if task_type == "monitoring_setup":
            return [
                SubTask(task_id=f"{task_id}_collect", title="指标采集配置",
                        description="配置CPU/内存/磁盘/工作流指标采集",
                        agent_role=AgentRole.MONITORING, priority=1),
                SubTask(task_id=f"{task_id}_alert", title="告警规则配置",
                        description="配置阈值告警规则",
                        agent_role=AgentRole.MONITORING, priority=2,
                        dependencies=[f"{task_id}_collect"]),
                SubTask(task_id=f"{task_id}_channel", title="通知通道配置",
                        description="配置飞书/邮件/Webhook通知通道",
                        agent_role=AgentRole.NOTIFICATION, priority=2),
                SubTask(task_id=f"{task_id}_report", title="报告模板配置",
                        description="配置日报/周报自动生成",
                        agent_role=AgentRole.DOCUMENTATION, priority=3),
            ]

        return [
            SubTask(task_id=task_id, title="通用任务",
                    description=task_description, agent_role=AgentRole.DEPLOYMENT)
        ]


class AgentDispatcher:
    """多智能体任务派发器 — 并行执行子任务，合并结果"""

    def __init__(self, max_concurrent: int = 5):
        self.max_concurrent = max_concurrent
        self._task_history: List[TaskResult] = []

    async def execute_parallel(
        self,
        sub_tasks: List[SubTask],
        agent_handlers: Optional[Dict[AgentRole, Callable]] = None,
    ) -> List[TaskResult]:
        """
        并行执行所有子任务（考虑依赖关系）：
        1. 找出无依赖的任务 → 立即并行执行
        2. 找出依赖已完成的任务 → 继续并行执行
        3. 收集所有结果
        """
        if agent_handlers is None:
            agent_handlers = self._default_handlers()

        results: Dict[str, TaskResult] = {}
        pending = {t.task_id: t for t in sub_tasks}
        completed = set()
        failed = set()

        while pending:
            ready = [
                t for t in pending.values()
                if all(d in completed for d in t.dependencies)
                and t.status == TaskStatus.PENDING
            ]

            if not ready and pending:
                stuck = [t for t in pending.values() if t.status == TaskStatus.PENDING]
                for t in stuck:
                    t.status = TaskStatus.FAILED
                    t.error = f"依赖无法满足: {t.dependencies}"
                    failed.add(t.task_id)
                    logger.error(f"Task {t.task_id} stuck: dependencies not met")
                for fid in failed:
                    if fid in pending:
                        del pending[fid]
                break

            semaphore = asyncio.Semaphore(self.max_concurrent)

            async def _execute_one(task: SubTask):
                async with semaphore:
                    handler = agent_handlers.get(task.agent_role)
                    if not handler:
                        return TaskResult(
                            task_id=task.task_id, title=task.title,
                            status=TaskStatus.FAILED,
                            result={"error": f"No handler for role: {task.agent_role}"},
                            duration_seconds=0, agent_role=task.agent_role,
                        )

                    task.status = TaskStatus.RUNNING
                    task.start_time = datetime.now().isoformat()
                    start = time.time()

                    try:
                        result = await asyncio.wait_for(
                            handler(task), timeout=task.timeout_seconds
                        )
                        task.status = TaskStatus.COMPLETED
                        task.result = result
                    except asyncio.TimeoutError:
                        task.status = TaskStatus.TIMEOUT
                        task.error = f"超时 {task.timeout_seconds}s"
                        result = {"error": task.error}
                    except Exception as e:
                        task.status = TaskStatus.FAILED
                        task.error = str(e)
                        result = {"error": str(e)}

                    task.end_time = datetime.now().isoformat()
                    duration = time.time() - start

                    task_result = TaskResult(
                        task_id=task.task_id, title=task.title,
                        status=task.status, result=result,
                        duration_seconds=round(duration, 2),
                        agent_role=task.agent_role,
                    )

                    if task.status == TaskStatus.COMPLETED:
                        completed.add(task.task_id)
                    else:
                        failed.add(task.task_id)

                    return task_result

            batch_results = await asyncio.gather(
                *[_execute_one(t) for t in ready], return_exceptions=True
            )

            for res in batch_results:
                if isinstance(res, TaskResult):
                    results[res.task_id] = res
                    self._task_history.append(res)
                    if res.task_id in pending:
                        del pending[res.task_id]

        return list(results.values())

    def get_summary(self, results: List[TaskResult]) -> Dict:
        total = len(results)
        completed = sum(1 for r in results if r.status == TaskStatus.COMPLETED)
        failed = sum(1 for r in results if r.status == TaskStatus.FAILED)
        total_time = sum(r.duration_seconds for r in results)

        return {
            "total_tasks": total,
            "completed": completed,
            "failed": failed,
            "success_rate": f"{completed/max(total,1)*100:.0f}%",
            "total_duration_seconds": round(total_time, 2),
            "tasks": [
                {
                    "task_id": r.task_id,
                    "title": r.title,
                    "status": r.status.value,
                    "agent": r.agent_role.value,
                    "duration": f"{r.duration_seconds}s",
                    "result": r.result,
                }
                for r in results
            ],
        }

    def _default_handlers(self) -> Dict[AgentRole, Callable]:
        """默认Agent处理函数占位（具体实现由子模块提供）"""
        async def _placeholder(task: SubTask) -> Dict:
            logger.info(f"[{task.agent_role.value}] Executing: {task.title}")
            await asyncio.sleep(0.2)
            return {"status": "placeholder", "task": task.title}

        return {role: _placeholder for role in AgentRole}
