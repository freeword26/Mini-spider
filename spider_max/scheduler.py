#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工作流调度中心 - WorkflowScheduler
支持Cron、Interval、Event、OneTime四种触发模式
整合原有scheduler.py功能
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from croniter import croniter
import uuid

try:
    from .models import (
        Workflow, Execution, TriggerType, ScheduleConfig, TriggerConfig
    )
    from .workflow_executor import WorkflowExecutor
    from .event_bus import EventBus, AgentMessage
except ImportError:
    from models import (
        Workflow, Execution, TriggerType, ScheduleConfig, TriggerConfig
    )
    from workflow_executor import WorkflowExecutor
    from event_bus import EventBus, AgentMessage

logger = logging.getLogger(__name__)


class BaseTrigger:
    def should_fire(self) -> bool:
        raise NotImplementedError

    def get_next_fire_time(self) -> Optional[datetime]:
        raise NotImplementedError


class CronTrigger(BaseTrigger):
    def __init__(self, cron_expression: str, timezone: str = "Asia/Shanghai"):
        self.cron_expression = cron_expression
        self.timezone = timezone
        self._iter = croniter(cron_expression, datetime.now())

    def should_fire(self) -> bool:
        now = datetime.now()
        self._iter = croniter(self.cron_expression, now - timedelta(seconds=1))
        next_time = self._iter.get_next()
        return abs((next_time - now).total_seconds()) < 60

    def get_next_fire_time(self) -> Optional[datetime]:
        try:
            self._iter = croniter(self.cron_expression, datetime.now())
            return self._iter.get_next()
        except Exception:
            return None


class IntervalTrigger(BaseTrigger):
    def __init__(self, interval_seconds: int):
        self.interval_seconds = interval_seconds
        self.last_fire_time: Optional[float] = None

    def should_fire(self) -> bool:
        now = time.time()
        if self.last_fire_time is None:
            self.last_fire_time = now
            return True
        if now - self.last_fire_time >= self.interval_seconds:
            self.last_fire_time = now
            return True
        return False

    def get_next_fire_time(self) -> Optional[datetime]:
        if self.last_fire_time:
            return datetime.fromtimestamp(self.last_fire_time + self.interval_seconds)
        return datetime.now()


class OneTimeTrigger(BaseTrigger):
    def __init__(self, fire_time: datetime):
        self.fire_time = fire_time
        self.fired = False

    def should_fire(self) -> bool:
        if not self.fired and datetime.now() >= self.fire_time:
            self.fired = True
            return True
        return False

    def get_next_fire_time(self) -> Optional[datetime]:
        return None if self.fired else self.fire_time


class EventTrigger(BaseTrigger):
    def __init__(self, event_name: str, event_bus: EventBus):
        self.event_name = event_name
        self.event_bus = event_bus
        self._pending_events: List[Dict] = []
        event_bus.subscribe(event_name, self._handle_event)

    def _handle_event(self, message: AgentMessage) -> None:
        if message.payload.get("event") == self.event_name:
            self._pending_events.append(message.payload)

    def should_fire(self) -> bool:
        if self._pending_events:
            self._pending_events.pop(0)
            return True
        return False

    def get_next_fire_time(self) -> Optional[datetime]:
        return datetime.now() if self._pending_events else None


class WorkflowScheduler:
    def __init__(
        self,
        executor: WorkflowExecutor,
        event_bus: EventBus,
        config: Optional[Dict] = None
    ):
        self.executor = executor
        self.event_bus = event_bus
        self.config = config or {}

        self._workflows: Dict[str, Workflow] = {}
        self._triggers: Dict[str, BaseTrigger] = {}
        self._running = False
        self._poll_interval = self.config.get("poll_interval", 1)

    def register_workflow(self, workflow: Workflow) -> None:
        self._workflows[workflow.workflow_id] = workflow
        self._create_trigger(workflow)
        logger.info(f"Registered workflow: {workflow.workflow_id}")

    def unregister_workflow(self, workflow_id: str) -> None:
        if workflow_id in self._workflows:
            del self._workflows[workflow_id]
        if workflow_id in self._triggers:
            del self._triggers[workflow_id]
        logger.info(f"Unregistered workflow: {workflow_id}")

    def _create_trigger(self, workflow: Workflow) -> None:
        trigger_config = workflow.trigger if isinstance(workflow.trigger, TriggerConfig) else TriggerConfig(**workflow.trigger)
        schedule_config = workflow.schedule if isinstance(workflow.schedule, ScheduleConfig) else ScheduleConfig(**workflow.schedule) if isinstance(workflow.schedule, dict) else ScheduleConfig()

        if not schedule_config.enabled:
            return

        trigger_type = trigger_config.trigger_type if isinstance(trigger_config.trigger_type, TriggerType) else TriggerType(trigger_config.trigger_type)

        if trigger_type == TriggerType.CRON:
            self._triggers[workflow.workflow_id] = CronTrigger(
                trigger_config.cron_expression or "0 * * * *",
                schedule_config.timezone
            )
        elif trigger_type == TriggerType.INTERVAL:
            self._triggers[workflow.workflow_id] = IntervalTrigger(
                trigger_config.interval_seconds or 3600
            )
        elif trigger_type == TriggerType.ONE_TIME:
            self._triggers[workflow.workflow_id] = OneTimeTrigger(
                datetime.now() + timedelta(seconds=10)
            )
        elif trigger_type == TriggerType.EVENT:
            self._triggers[workflow.workflow_id] = EventTrigger(
                trigger_config.event_name or "default",
                self.event_bus
            )

    async def trigger_workflow(
        self,
        workflow_id: str,
        context: Optional[Dict] = None,
        trigger_type: str = "manual",
        trigger_source: str = ""
    ) -> Optional[Execution]:
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            logger.error(f"Workflow not found: {workflow_id}")
            return None

        if not workflow.enabled:
            logger.warning(f"Workflow is disabled: {workflow_id}")
            return None

        logger.info(f"Triggering workflow: {workflow_id} (type: {trigger_type})")

        execution = await self.executor.execute(
            workflow,
            context,
            trigger_type=trigger_type,
            trigger_source=trigger_source
        )

        await self.event_bus.publish(AgentMessage(
            sender_id="scheduler",
            receiver_id="*",
            payload={
                "type": "workflow_executed",
                "workflow_id": workflow_id,
                "execution_id": execution.execution_id,
                "status": execution.status.value if hasattr(execution.status, 'value') else execution.status
            }
        ))

        return execution

    async def run(self) -> None:
        self._running = True
        logger.info("Workflow scheduler started")

        while self._running:
            try:
                for workflow_id, trigger in self._triggers.items():
                    workflow = self._workflows.get(workflow_id)
                    if not workflow or not workflow.enabled:
                        continue

                    if trigger.should_fire():
                        asyncio.create_task(
                            self.trigger_workflow(
                                workflow_id,
                                trigger_type="scheduled",
                                trigger_source=f"trigger:{trigger.__class__.__name__}"
                            )
                        )

                await asyncio.sleep(self._poll_interval)

            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(self._poll_interval * 5)

    def stop(self) -> None:
        self._running = False
        logger.info("Workflow scheduler stopped")

    def get_next_scheduled_time(self, workflow_id: str) -> Optional[datetime]:
        trigger = self._triggers.get(workflow_id)
        if trigger:
            return trigger.get_next_fire_time()
        return None

    def list_scheduled_workflows(self) -> List[Dict]:
        result = []
        for workflow_id, trigger in self._triggers.items():
            workflow = self._workflows.get(workflow_id)
            if workflow:
                result.append({
                    "workflow_id": workflow_id,
                    "name": workflow.name,
                    "enabled": workflow.enabled,
                    "trigger_type": workflow.trigger.trigger_type.value if hasattr(workflow.trigger, 'trigger_type') else str(workflow.trigger.trigger_type),
                    "next_fire_time": self.get_next_scheduled_time(workflow_id)
                })
        return result

    def pause_workflow(self, workflow_id: str) -> bool:
        if workflow_id in self._workflows:
            self._workflows[workflow_id].enabled = False
            logger.info(f"Paused workflow: {workflow_id}")
            return True
        return False

    def resume_workflow(self, workflow_id: str) -> bool:
        if workflow_id in self._workflows:
            self._workflows[workflow_id].enabled = True
            logger.info(f"Resumed workflow: {workflow_id}")
            return True
        return False

    def get_workflow_status(self, workflow_id: str) -> Optional[Dict]:
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return None

        executions = self.executor.list_executions(workflow_id)
        recent_executions = sorted(executions, key=lambda x: x.start_time or "", reverse=True)[:5]

        return {
            "workflow_id": workflow_id,
            "name": workflow.name,
            "enabled": workflow.enabled,
            "total_executions": len(executions),
            "recent_executions": [
                {
                    "execution_id": e.execution_id,
                    "status": e.status.value if hasattr(e.status, 'value') else e.status,
                    "start_time": e.start_time,
                    "duration_seconds": e.duration_seconds
                }
                for e in recent_executions
            ],
            "circuit_breaker": self.executor.get_circuit_breaker_status()
        }
