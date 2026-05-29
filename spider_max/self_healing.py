#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自愈模块 — 三层闭环架构冲突#5解决方案
自动重启失败工作流、重新分配超时任务、告警通知
"""

import time
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class HealingAction(str, Enum):
    RESTART = "restart"
    REASSIGN = "reassign"
    ROLLBACK = "rollback"
    ALERT = "alert"
    ESCALATE = "escalate"


@dataclass
class HealingRecord:
    record_id: str
    action: HealingAction
    target_workflow: str
    target_task: str
    reason: str
    status: str = "initiated"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = None
    result: Optional[str] = None


THRESHOLDS = {
    "workflow_success_rate_warning": 0.95,
    "workflow_success_rate_critical": 0.90,
    "task_timeout_seconds": 600,
    "task_stuck_seconds": 1800,
    "max_restarts_per_workflow": 3,
    "restart_window_seconds": 3600,
}


class SelfHealing:
    """系统自愈能力 — 自动检测异常并执行修复"""

    def __init__(
        self,
        event_bus=None,
        scheduler=None,
        alert_callback: Optional[Callable] = None,
    ):
        self.event_bus = event_bus
        self.scheduler = scheduler
        self.alert_callback = alert_callback
        self._healing_history: List[HealingRecord] = []
        self._restart_counts: Dict[str, List[float]] = {}
        self._running = False

    async def check_and_heal(self) -> List[HealingRecord]:
        actions = []
        actions.extend(await self._check_failed_workflows())
        actions.extend(await self._check_stuck_tasks())
        actions.extend(await self._check_service_health())
        for record in actions:
            self._healing_history.append(record)
            await self._record_healing_event(record)
        return actions

    async def _check_failed_workflows(self) -> List[HealingRecord]:
        actions = []
        if not self.scheduler:
            return actions

        for workflow_id, trigger in self.scheduler._triggers.items():
            executions = self.scheduler.executor.list_executions(workflow_id)
            recent = [e for e in executions if e.status.value == "failed"][-5:]
            if len(recent) >= THRESHOLDS["max_restarts_per_workflow"]:
                record = HealingRecord(
                    record_id=f"heal_{int(time.time())}_{workflow_id}",
                    action=HealingAction.ALERT,
                    target_workflow=workflow_id,
                    target_task="multiple",
                    reason=f"Workflow {workflow_id} has {len(recent)} recent failures",
                )
                record.status = "escalated"
                actions.append(record)

            failure_rate = self._calculate_failure_rate(workflow_id, executions)
            if failure_rate < THRESHOLDS["workflow_success_rate_critical"]:
                can_restart = self._can_restart(workflow_id)
                if can_restart:
                    record = await self._restart_workflow(workflow_id)
                    actions.append(record)
                else:
                    record = HealingRecord(
                        record_id=f"heal_{int(time.time())}_{workflow_id}",
                        action=HealingAction.ESCALATE,
                        target_workflow=workflow_id,
                        target_task="all",
                        reason=f"Failure rate {failure_rate:.1%}, max restarts reached",
                    )
                    actions.append(record)
                    self._escalate(
                        f"Workflow {workflow_id} failure rate {failure_rate:.1%} "
                        f"exceeds critical threshold, requires manual intervention"
                    )

        return actions

    async def _check_stuck_tasks(self) -> List[HealingRecord]:
        actions = []
        if not self.scheduler:
            return actions

        now = time.time()
        for workflow_id, trigger in self.scheduler._triggers.items():
            executions = self.scheduler.executor.list_executions(workflow_id)
            running = [e for e in executions if e.status.value == "running"]
            for exec_obj in running:
                if exec_obj.start_time:
                    try:
                        start = datetime.fromisoformat(exec_obj.start_time)
                        elapsed = (datetime.now() - start).total_seconds()
                        if elapsed > THRESHOLDS["task_stuck_seconds"]:
                            record = await self._reassign_task(
                                workflow_id, exec_obj.execution_id, elapsed
                            )
                            actions.append(record)
                    except (ValueError, TypeError):
                        continue
        return actions

    async def _check_service_health(self) -> List[HealingRecord]:
        actions = []
        if self.event_bus:
            try:
                if hasattr(self.event_bus, '_channel') and (
                    not self.event_bus._channel or self.event_bus._channel.is_closed
                ):
                    record = HealingRecord(
                        record_id=f"heal_{int(time.time())}_rabbitmq",
                        action=HealingAction.RESTART,
                        target_workflow="event_bus",
                        target_task="rabbitmq_connection",
                        reason="RabbitMQ channel is closed",
                    )
                    try:
                        if hasattr(self.event_bus, '_connect'):
                            self.event_bus._connect()
                            record.status = "completed"
                            record.result = "RabbitMQ reconnected"
                    except Exception as e:
                        record.status = "failed"
                        record.result = str(e)
                    actions.append(record)
            except Exception:
                pass
        return actions

    async def _restart_workflow(self, workflow_id: str) -> HealingRecord:
        record = HealingRecord(
            record_id=f"heal_{int(time.time())}_{workflow_id}",
            action=HealingAction.RESTART,
            target_workflow=workflow_id,
            target_task="all",
            reason=f"Critical failure rate detected",
        )
        try:
            if self.scheduler:
                self.scheduler._triggers.pop(workflow_id, None)
                if workflow_id in self.scheduler._workflows:
                    workflow = self.scheduler._workflows[workflow_id]
                    self.scheduler.register_workflow(workflow)
                    self._track_restart(workflow_id)
                    now = datetime.now(timezone.utc).isoformat()
                    record.completed_at = now
                    record.status = "completed"
                    record.result = f"Workflow {workflow_id} restarted successfully"
                    logger.info(record.result)
        except Exception as e:
            record.status = "failed"
            record.result = str(e)
            logger.error(f"Failed to restart workflow {workflow_id}: {e}")
        return record

    async def _reassign_task(
        self, workflow_id: str, execution_id: str, stuck_seconds: float
    ) -> HealingRecord:
        record = HealingRecord(
            record_id=f"heal_{int(time.time())}_{execution_id}",
            action=HealingAction.REASSIGN,
            target_workflow=workflow_id,
            target_task=execution_id,
            reason=f"Task stuck for {stuck_seconds:.0f}s (threshold: {THRESHOLDS['task_stuck_seconds']}s)",
        )
        try:
            now = datetime.now(timezone.utc).isoformat()
            record.completed_at = now
            record.status = "completed"
            record.result = f"Task {execution_id} flagged for reassignment after {stuck_seconds:.0f}s"
            logger.info(record.result)
        except Exception as e:
            record.status = "failed"
            record.result = str(e)
        return record

    def _calculate_failure_rate(
        self, workflow_id: str, executions: list
    ) -> float:
        completed = [e for e in executions if e.status.value in ("completed", "failed")]
        if not completed:
            return 1.0
        failures = [e for e in completed if e.status.value == "failed"]
        return 1.0 - len(failures) / len(completed)

    def _can_restart(self, workflow_id: str) -> bool:
        if workflow_id not in self._restart_counts:
            return True
        now = time.time()
        window = THRESHOLDS["restart_window_seconds"]
        recent = [t for t in self._restart_counts[workflow_id] if now - t < window]
        self._restart_counts[workflow_id] = recent
        return len(recent) < THRESHOLDS["max_restarts_per_workflow"]

    def _track_restart(self, workflow_id: str):
        if workflow_id not in self._restart_counts:
            self._restart_counts[workflow_id] = []
        self._restart_counts[workflow_id].append(time.time())

    def _escalate(self, message: str):
        logger.critical(f"ESCALATION: {message}")
        if self.alert_callback:
            try:
                self.alert_callback(message)
            except Exception as e:
                logger.error(f"Alert callback failed: {e}")

    async def _record_healing_event(self, record: HealingRecord):
        if self.event_bus:
            try:
                from .event_bus import AgentMessage
            except (ImportError, SystemError):
                from event_bus import AgentMessage

            try:
                import asyncio

                message = AgentMessage(
                    sender_id="self_healing",
                    receiver_id="system-manager",
                    priority=5,
                    payload={
                        "type": "healing_action",
                        "record_id": record.record_id,
                        "action": record.action.value,
                        "target_workflow": record.target_workflow,
                        "target_task": record.target_task,
                        "reason": record.reason,
                        "status": record.status,
                    },
                )
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(self.event_bus.publish(message))
                except RuntimeError:
                    asyncio.run(self.event_bus.publish(message))
            except Exception as e:
                logger.error(f"Error publishing healing event: {e}")

    def get_healing_stats(self) -> Dict:
        total = len(self._healing_history)
        by_action = {}
        for record in self._healing_history:
            action = record.action.value
            by_action[action] = by_action.get(action, 0) + 1
        recent = [
            r for r in self._healing_history
            if (datetime.now() - datetime.fromisoformat(r.created_at)).total_seconds() < 86400
        ]
        return {
            "total_healing_actions": total,
            "last_24h": len(recent),
            "by_action": by_action,
            "restart_counts": {
                k: len(v) for k, v in self._restart_counts.items()
            },
        }
