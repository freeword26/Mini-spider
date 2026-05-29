#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据模型定义
无人值守工作流系统的核心数据类型
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


class TriggerType(str, Enum):
    CRON = "cron"
    INTERVAL = "interval"
    EVENT = "event"
    ONE_TIME = "one_time"
    MANUAL = "manual"


class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class AgentStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ON_LEAVE = "on_leave"
    OFFLINE = "offline"


class ScheduleType(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    ON_DEMAND = "on_demand"


@dataclass
class RetryConfig:
    max_attempts: int = 3
    retry_interval: int = 300
    exponential_backoff: bool = True
    max_interval: int = 3600
    retryable_errors: List[str] = field(default_factory=lambda: [
        "TimeoutError", "ConnectionError", "ServiceUnavailable"
    ])


@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5
    success_threshold: int = 3
    timeout: int = 3600
    half_open_max_calls: int = 1


@dataclass
class TriggerConfig:
    trigger_type: TriggerType = TriggerType.MANUAL
    cron_expression: Optional[str] = None
    interval_seconds: Optional[int] = None
    event_name: Optional[str] = None


@dataclass
class ScheduleConfig:
    enabled: bool = True
    timezone: str = "Asia/Shanghai"
    max_concurrent: int = 1


@dataclass
class TaskDefinition:
    task_id: str
    name: str
    description: str
    agent_id: str
    dependencies: List[str] = field(default_factory=list)
    input_mapping: Dict[str, str] = field(default_factory=dict)
    output_mapping: Dict[str, str] = field(default_factory=dict)
    timeout: int = 300
    retry: RetryConfig = field(default_factory=RetryConfig)
    continue_on_failure: bool = False

    def to_dict(self) -> Dict:
        return {
            "task_id": self.task_id,
            "name": self.name,
            "description": self.description,
            "agent_id": self.agent_id,
            "dependencies": self.dependencies,
            "input_mapping": self.input_mapping,
            "output_mapping": self.output_mapping,
            "timeout": self.timeout,
            "retry": asdict(self.retry) if isinstance(self.retry, RetryConfig) else self.retry,
            "continue_on_failure": self.continue_on_failure
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "TaskDefinition":
        retry_data = data.get("retry", {})
        if isinstance(retry_data, dict):
            retry = RetryConfig(**retry_data)
        else:
            retry = retry_data
        return cls(
            task_id=data["task_id"],
            name=data["name"],
            description=data.get("description", ""),
            agent_id=data["agent_id"],
            dependencies=data.get("dependencies", []),
            input_mapping=data.get("input_mapping", {}),
            output_mapping=data.get("output_mapping", {}),
            timeout=data.get("timeout", 300),
            retry=retry,
            continue_on_failure=data.get("continue_on_failure", False)
        )


@dataclass
class Workflow:
    workflow_id: str
    name: str
    description: str = ""
    version: str = "1.0.0"
    enabled: bool = True

    trigger: TriggerConfig = field(default_factory=TriggerConfig)
    schedule: ScheduleConfig = field(default_factory=ScheduleConfig)
    retry: RetryConfig = field(default_factory=RetryConfig)
    circuit_breaker: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)

    tasks: List[TaskDefinition] = field(default_factory=list)
    dependencies: Dict[str, List[str]] = field(default_factory=dict)

    assigned_agents: List[str] = field(default_factory=list)
    priority: int = 3

    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    created_by: str = "system"

    def to_dict(self) -> Dict:
        return {
            "workflow_id": self.workflow_id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "enabled": self.enabled,
            "trigger": asdict(self.trigger) if isinstance(self.trigger, TriggerConfig) else self.trigger,
            "schedule": asdict(self.schedule) if isinstance(self.schedule, ScheduleConfig) else self.schedule,
            "retry": asdict(self.retry) if isinstance(self.retry, RetryConfig) else self.retry,
            "circuit_breaker": asdict(self.circuit_breaker) if isinstance(self.circuit_breaker, CircuitBreakerConfig) else self.circuit_breaker,
            "tasks": [t.to_dict() if isinstance(t, TaskDefinition) else t for t in self.tasks],
            "dependencies": self.dependencies,
            "assigned_agents": self.assigned_agents,
            "priority": self.priority,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "created_by": self.created_by
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Workflow":
        trigger_data = data.get("trigger", {})
        if isinstance(trigger_data, dict):
            trigger = TriggerConfig(**trigger_data)
        else:
            trigger = trigger_data

        schedule_data = data.get("schedule", {})
        if isinstance(schedule_data, dict):
            schedule = ScheduleConfig(**schedule_data)
        else:
            schedule = schedule_data

        retry_data = data.get("retry", {})
        if isinstance(retry_data, dict):
            retry = RetryConfig(**retry_data)
        else:
            retry = retry_data

        cb_data = data.get("circuit_breaker", {})
        if isinstance(cb_data, dict):
            cb = CircuitBreakerConfig(**cb_data)
        else:
            cb = cb_data

        tasks = [TaskDefinition.from_dict(t) if isinstance(t, dict) else t for t in data.get("tasks", [])]

        return cls(
            workflow_id=data["workflow_id"],
            name=data["name"],
            description=data.get("description", ""),
            version=data.get("version", "1.0.0"),
            enabled=data.get("enabled", True),
            trigger=trigger,
            schedule=schedule,
            retry=retry,
            circuit_breaker=cb,
            tasks=tasks,
            dependencies=data.get("dependencies", {}),
            assigned_agents=data.get("assigned_agents", []),
            priority=data.get("priority", 3),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
            created_by=data.get("created_by", "system")
        )


@dataclass
class ErrorInfo:
    error_type: str
    message: str
    stack_trace: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class TaskExecution:
    task_id: str
    status: ExecutionStatus = ExecutionStatus.PENDING
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration_seconds: float = 0.0
    output: Optional[Dict] = None
    error: Optional[ErrorInfo] = None
    retry_count: int = 0


@dataclass
class Execution:
    execution_id: str = field(default_factory=lambda: f"exec_{uuid.uuid4().hex[:12]}")
    workflow_id: str = ""
    workflow_version: str = "1.0.0"

    status: ExecutionStatus = ExecutionStatus.PENDING
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration_seconds: float = 0.0

    task_executions: List[TaskExecution] = field(default_factory=list)

    error: Optional[ErrorInfo] = None

    retry_count: int = 0
    max_retries: int = 3

    failure_count: int = 0
    failure_cases: List[str] = field(default_factory=list)

    trigger_type: str = "manual"
    trigger_source: str = ""

    executed_by: str = ""

    def to_dict(self) -> Dict:
        return {
            "execution_id": self.execution_id,
            "workflow_id": self.workflow_id,
            "workflow_version": self.workflow_version,
            "status": self.status.value if isinstance(self.status, ExecutionStatus) else self.status,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_seconds": self.duration_seconds,
            "task_executions": [
                {
                    "task_id": t.task_id,
                    "status": t.status.value if isinstance(t.status, ExecutionStatus) else t.status,
                    "start_time": t.start_time,
                    "end_time": t.end_time,
                    "duration_seconds": t.duration_seconds,
                    "output": t.output,
                    "error": asdict(t.error) if isinstance(t.error, ErrorInfo) else t.error,
                    "retry_count": t.retry_count
                }
                for t in self.task_executions
            ],
            "error": asdict(self.error) if isinstance(self.error, ErrorInfo) else self.error,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "failure_count": self.failure_count,
            "failure_cases": self.failure_cases,
            "trigger_type": self.trigger_type,
            "trigger_source": self.trigger_source,
            "executed_by": self.executed_by
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Execution":
        task_executions = []
        for t in data.get("task_executions", []):
            error = None
            if t.get("error"):
                if isinstance(t["error"], dict):
                    error = ErrorInfo(**t["error"])
                else:
                    error = t["error"]
            task_executions.append(TaskExecution(
                task_id=t["task_id"],
                status=ExecutionStatus(t.get("status", "pending")),
                start_time=t.get("start_time"),
                end_time=t.get("end_time"),
                duration_seconds=t.get("duration_seconds", 0.0),
                output=t.get("output"),
                error=error,
                retry_count=t.get("retry_count", 0)
            ))

        error = None
        if data.get("error"):
            if isinstance(data["error"], dict):
                error = ErrorInfo(**data["error"])
            else:
                error = data["error"]

        return cls(
            execution_id=data.get("execution_id", f"exec_{uuid.uuid4().hex[:12]}"),
            workflow_id=data.get("workflow_id", ""),
            workflow_version=data.get("workflow_version", "1.0.0"),
            status=ExecutionStatus(data.get("status", "pending")),
            start_time=data.get("start_time"),
            end_time=data.get("end_time"),
            duration_seconds=data.get("duration_seconds", 0.0),
            task_executions=task_executions,
            error=error,
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3),
            trigger_type=data.get("trigger_type", "manual"),
            trigger_source=data.get("trigger_source", ""),
            executed_by=data.get("executed_by", "")
        )


@dataclass
class TimeSlot:
    start_time: str
    end_time: str
    agent_id: str


@dataclass
class AgentSchedule:
    schedule_id: str = field(default_factory=lambda: f"schedule_{uuid.uuid4().hex[:8]}")
    agent_id: str = ""
    agent_name: str = ""

    schedule_type: ScheduleType = ScheduleType.DAILY
    time_slots: List[TimeSlot] = field(default_factory=list)

    assigned_workflows: List[str] = field(default_factory=list)

    status: AgentStatus = AgentStatus.ACTIVE
    current_shift: Optional[str] = None

    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "schedule_id": self.schedule_id,
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "schedule_type": self.schedule_type.value if isinstance(self.schedule_type, ScheduleType) else self.schedule_type,
            "time_slots": [
                {
                    "start_time": ts.start_time,
                    "end_time": ts.end_time,
                    "agent_id": ts.agent_id
                }
                for ts in self.time_slots
            ],
            "assigned_workflows": self.assigned_workflows,
            "status": self.status.value if isinstance(self.status, AgentStatus) else self.status,
            "current_shift": self.current_shift,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "AgentSchedule":
        time_slots = []
        for ts in data.get("time_slots", []):
            if isinstance(ts, dict):
                time_slots.append(TimeSlot(**ts))
            else:
                time_slots.append(ts)

        return cls(
            schedule_id=data.get("schedule_id", f"schedule_{uuid.uuid4().hex[:8]}"),
            agent_id=data.get("agent_id", ""),
            agent_name=data.get("agent_name", ""),
            schedule_type=ScheduleType(data.get("schedule_type", "daily")),
            time_slots=time_slots,
            assigned_workflows=data.get("assigned_workflows", []),
            status=AgentStatus(data.get("status", "active")),
            current_shift=data.get("current_shift"),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat())
        )
