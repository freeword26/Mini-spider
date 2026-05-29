#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
监控告警模块 - Monitoring
整合chaos_engine.py的评估监控能力
支持指标采集、熔断控制、告警通知、报告生成
"""

import asyncio
import logging
import time
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from collections import defaultdict

try:
    from .models import Execution, ExecutionStatus, Workflow
    from .event_bus import EventBus, AgentMessage
    from .workflow_executor import CircuitBreaker
except ImportError:
    from models import Execution, ExecutionStatus, Workflow
    from event_bus import EventBus, AgentMessage
    from workflow_executor import CircuitBreaker

logger = logging.getLogger(__name__)


@dataclass
class Alert:
    alert_id: str
    level: str
    title: str
    detail: str
    workflow_id: Optional[str] = None
    execution_id: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[str] = None


@dataclass
class Metric:
    name: str
    value: float
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class DailyReport:
    date: date
    total_executions: int = 0
    success_count: int = 0
    failure_count: int = 0
    success_rate: float = 0.0
    avg_duration_seconds: float = 0.0
    total_duration_seconds: float = 0.0
    alerts: List[Alert] = field(default_factory=list)
    top_workflows: List[Dict] = field(default_factory=list)
    circuit_breaker_states: Dict[str, str] = field(default_factory=dict)


class AlertManager:
    def __init__(self, event_bus: EventBus, config: Optional[Dict] = None):
        self.event_bus = event_bus
        self.config = config or {}
        self._alerts: List[Alert] = []
        self._alert_handlers: List[Callable] = []

    def add_alert_handler(self, handler: Callable) -> None:
        self._alert_handlers.append(handler)

    async def send_alert(self, alert: Alert) -> None:
        self._alerts.append(alert)
        logger.warning(f"Alert: [{alert.level}] {alert.title} - {alert.detail}")

        for handler in self._alert_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(alert)
                else:
                    handler(alert)
            except Exception as e:
                logger.error(f"Error in alert handler: {e}")

        await self.event_bus.publish(AgentMessage(
            sender_id="monitoring",
            receiver_id="*",
            payload={
                "type": "alert",
                "alert": {
                    "alert_id": alert.alert_id,
                    "level": alert.level,
                    "title": alert.title,
                    "detail": alert.detail,
                    "workflow_id": alert.workflow_id,
                    "timestamp": alert.timestamp
                }
            }
        ))

    def get_active_alerts(self, level: Optional[str] = None) -> List[Alert]:
        if level:
            return [a for a in self._alerts if not a.acknowledged and a.level == level]
        return [a for a in self._alerts if not a.acknowledged]

    def get_today_alerts(self) -> List[Alert]:
        today = date.today()
        return [
            a for a in self._alerts
            if datetime.fromisoformat(a.timestamp).date() == today
        ]

    def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        for alert in self._alerts:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                alert.acknowledged_by = acknowledged_by
                alert.acknowledged_at = datetime.now().isoformat()
                return True
        return False


class MetricsCollector:
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self._metrics: List[Metric] = []
        self._execution_history: List[Dict] = []
        self._max_history = self.config.get("max_history", 10000)

    def record_metric(self, metric: Metric) -> None:
        self._metrics.append(metric)
        if len(self._metrics) > self._max_history:
            self._metrics.pop(0)

    def record_execution(self, execution: Execution) -> None:
        record = {
            "execution_id": execution.execution_id,
            "workflow_id": execution.workflow_id,
            "status": execution.status.value if isinstance(execution.status, ExecutionStatus) else execution.status,
            "start_time": execution.start_time,
            "end_time": execution.end_time,
            "duration_seconds": execution.duration_seconds,
            "retry_count": execution.retry_count
        }
        self._execution_history.append(record)
        if len(self._execution_history) > self._max_history:
            self._execution_history.pop(0)

    def get_success_rate(self, workflow_id: Optional[str] = None, hours: int = 24) -> float:
        cutoff = datetime.now() - timedelta(hours=hours)
        executions = self._get_filtered_executions(workflow_id, cutoff)

        if not executions:
            return 1.0

        completed = [e for e in executions if e["status"] in ("completed", "failed")]
        if not completed:
            return 1.0

        successes = [e for e in completed if e["status"] == "completed"]
        return len(successes) / len(completed)

    def get_avg_duration(self, workflow_id: Optional[str] = None, hours: int = 24) -> float:
        cutoff = datetime.now() - timedelta(hours=hours)
        executions = self._get_filtered_executions(workflow_id, cutoff)

        if not executions:
            return 0.0

        durations = [e["duration_seconds"] for e in executions if e["duration_seconds"]]
        return sum(durations) / len(durations) if durations else 0.0

    def get_execution_count(self, workflow_id: Optional[str] = None, hours: int = 24) -> int:
        cutoff = datetime.now() - timedelta(hours=hours)
        return len(self._get_filtered_executions(workflow_id, cutoff))

    def _get_filtered_executions(self, workflow_id: Optional[str], cutoff: datetime) -> List[Dict]:
        executions = self._execution_history

        if workflow_id:
            executions = [e for e in executions if e["workflow_id"] == workflow_id]

        if cutoff:
            executions = [
                e for e in executions
                if e.get("start_time") and datetime.fromisoformat(e["start_time"]) >= cutoff
            ]

        return executions

    def get_workflow_stats(self, workflow_id: str, hours: int = 24) -> Dict:
        cutoff = datetime.now() - timedelta(hours=hours)
        executions = self._get_filtered_executions(workflow_id, cutoff)

        statuses = defaultdict(int)
        for e in executions:
            statuses[e["status"]] += 1

        return {
            "workflow_id": workflow_id,
            "total_executions": len(executions),
            "status_breakdown": dict(statuses),
            "success_rate": self.get_success_rate(workflow_id, hours),
            "avg_duration": self.get_avg_duration(workflow_id, hours)
        }


class Monitoring:
    def __init__(
        self,
        event_bus: EventBus,
        executor_circuit_breaker: Optional[CircuitBreaker] = None,
        config: Optional[Dict] = None
    ):
        self.event_bus = event_bus
        self.circuit_breaker = executor_circuit_breaker
        self.config = config or {}

        self.metrics_collector = MetricsCollector(config)
        self.alert_manager = AlertManager(event_bus, config)

        self._thresholds = self.config.get("thresholds", {
            "success_rate_warning": 0.95,
            "success_rate_critical": 0.90,
            "avg_duration_warning": 300,
            "avg_duration_critical": 600
        })

        self._running = False

    async def record_execution(self, execution: Execution) -> None:
        self.metrics_collector.record_execution(execution)

        await self.event_bus.publish(AgentMessage(
            sender_id="monitoring",
            receiver_id="*",
            payload={
                "type": "execution_recorded",
                "execution_id": execution.execution_id,
                "workflow_id": execution.workflow_id,
                "status": execution.status.value if hasattr(execution.status, 'value') else execution.status,
                "duration": execution.duration_seconds
            }
        ))

    async def check_thresholds(self) -> List[Alert]:
        alerts = []

        success_rate = self.metrics_collector.get_success_rate()
        if success_rate < self._thresholds["success_rate_critical"]:
            alerts.append(Alert(
                alert_id=f"alert_{int(time.time())}",
                level="critical",
                title="工作流成功率严重低于阈值",
                detail=f"当前成功率: {success_rate:.2%}, 临界值: {self._thresholds['success_rate_critical']:.2%}"
            ))
        elif success_rate < self._thresholds["success_rate_warning"]:
            alerts.append(Alert(
                alert_id=f"alert_{int(time.time())}",
                level="warning",
                title="工作流成功率低于阈值",
                detail=f"当前成功率: {success_rate:.2%}, 目标值: {self._thresholds['success_rate_warning']:.2%}"
            ))

        avg_duration = self.metrics_collector.get_avg_duration()
        if avg_duration > self._thresholds["avg_duration_critical"]:
            alerts.append(Alert(
                alert_id=f"alert_{int(time.time())}",
                level="critical",
                title="平均执行时间严重超标",
                detail=f"当前平均: {avg_duration:.1f}秒, 临界值: {self._thresholds['avg_duration_critical']}秒"
            ))
        elif avg_duration > self._thresholds["avg_duration_warning"]:
            alerts.append(Alert(
                alert_id=f"alert_{int(time.time())}",
                level="warning",
                title="平均执行时间超过阈值",
                detail=f"当前平均: {avg_duration:.1f}秒, 目标值: {self._thresholds['avg_duration_warning']}秒"
            ))

        if self.circuit_breaker and self.circuit_breaker.is_open():
            alerts.append(Alert(
                alert_id=f"alert_{int(time.time())}",
                level="warning",
                title="熔断器打开",
                detail="部分工作流可能被暂停执行，请检查系统状态"
            ))

        for alert in alerts:
            await self.alert_manager.send_alert(alert)

        return alerts

    def generate_daily_report(self, target_date: Optional[date] = None) -> DailyReport:
        target_date = target_date or date.today()
        executions = [
            e for e in self.metrics_collector._execution_history
            if e.get("start_time") and datetime.fromisoformat(e["start_time"]).date() == target_date
        ]

        success_count = len([e for e in executions if e["status"] == "completed"])
        failure_count = len([e for e in executions if e["status"] == "failed"])
        total_count = len(executions)

        durations = [e["duration_seconds"] for e in executions if e["duration_seconds"]]
        total_duration = sum(durations)
        avg_duration = total_duration / len(durations) if durations else 0.0

        workflow_counts: Dict[str, int] = defaultdict(int)
        for e in executions:
            workflow_counts[e["workflow_id"]] += 1

        top_workflows = sorted(
            [{"workflow_id": k, "count": v} for k, v in workflow_counts.items()],
            key=lambda x: x["count"],
            reverse=True
        )[:5]

        circuit_breaker_state = {}
        if self.circuit_breaker:
            circuit_breaker_state = {
                "state": self.circuit_breaker.state,
                "failure_count": self.circuit_breaker.failure_count,
                "success_count": self.circuit_breaker.success_count
            }

        return DailyReport(
            date=target_date,
            total_executions=total_count,
            success_count=success_count,
            failure_count=failure_count,
            success_rate=success_count / total_count if total_count > 0 else 1.0,
            avg_duration_seconds=avg_duration,
            total_duration_seconds=total_duration,
            alerts=self.alert_manager.get_today_alerts(),
            top_workflows=top_workflows,
            circuit_breaker_states=circuit_breaker_state
        )

    def generate_weekly_report(self) -> Dict:
        start_date = date.today() - timedelta(days=7)
        daily_reports = []

        for i in range(7):
            day = start_date + timedelta(days=i)
            report = self.generate_daily_report(day)
            daily_reports.append({
                "date": day.isoformat(),
                "total_executions": report.total_executions,
                "success_rate": report.success_rate
            })

        total_executions = sum(r["total_executions"] for r in daily_reports)
        avg_success_rate = sum(r["success_rate"] for r in daily_reports) / 7 if daily_reports else 0.0

        return {
            "start_date": start_date.isoformat(),
            "end_date": date.today().isoformat(),
            "daily_reports": daily_reports,
            "summary": {
                "total_executions": total_executions,
                "avg_success_rate": avg_success_rate
            }
        }

    async def run_periodic_check(self, interval: int = 60) -> None:
        self._running = True
        logger.info(f"Monitoring periodic check started (interval: {interval}s)")

        while self._running:
            try:
                await self.check_thresholds()
                await asyncio.sleep(interval)
            except Exception as e:
                logger.error(f"Error in periodic check: {e}")
                await asyncio.sleep(interval * 5)

    def stop(self) -> None:
        self._running = False
        logger.info("Monitoring periodic check stopped")

    def get_system_status(self) -> Dict:
        return {
            "status": "healthy",
            "metrics": {
                "total_executions_24h": self.metrics_collector.get_execution_count(hours=24),
                "success_rate_24h": self.metrics_collector.get_success_rate(hours=24),
                "avg_duration_24h": self.metrics_collector.get_avg_duration(hours=24)
            },
            "alerts": {
                "active_count": len(self.alert_manager.get_active_alerts()),
                "critical_count": len(self.alert_manager.get_active_alerts("critical")),
                "warning_count": len(self.alert_manager.get_active_alerts("warning"))
            },
            "circuit_breaker": self.circuit_breaker.get_circuit_breaker_status() if self.circuit_breaker else {}
        }

    def check_three_layer_health(self) -> Dict:
        layer_metrics = {
            "指挥控制层": {
                "projects": ["P001", "P002", "P003", "P004", "P005", "P006"],
                "target_efficiency": 0.90,
                "current_efficiency": 0.0,
                "status": "unknown"
            },
            "执行协作层": {
                "projects": ["P007", "P008", "P009", "P010"],
                "target_completion_rate": 0.85,
                "current_completion_rate": 0.0,
                "status": "unknown"
            },
            "资源与环境层": {
                "projects": ["P011", "P012", "P013", "P014", "P015", "P016",
                             "P017", "P018", "P019", "P020", "P021", "P022"],
                "target_availability": 0.99,
                "current_availability": 0.0,
                "status": "unknown"
            }
        }

        total_executions = self.metrics_collector.get_execution_count(hours=24)
        success_rate = self.metrics_collector.get_success_rate(hours=24)

        command_control_rate = min(success_rate / 0.90, 1.0) if success_rate > 0 else 0.0
        layer_metrics["指挥控制层"]["current_efficiency"] = round(command_control_rate, 3)
        layer_metrics["指挥控制层"]["status"] = (
            "healthy" if command_control_rate >= 0.90
            else "warning" if command_control_rate >= 0.70
            else "critical"
        )

        execution_rate = min(success_rate / 0.85, 1.0) if success_rate > 0 else 0.0
        layer_metrics["执行协作层"]["current_completion_rate"] = round(execution_rate, 3)
        layer_metrics["执行协作层"]["status"] = (
            "healthy" if execution_rate >= 0.85
            else "warning" if execution_rate >= 0.60
            else "critical"
        )

        availability = min(success_rate / 0.99, 1.0) if success_rate > 0 else 0.0
        layer_metrics["资源与环境层"]["current_availability"] = round(availability, 3)
        layer_metrics["资源与环境层"]["status"] = (
            "healthy" if availability >= 0.99
            else "warning" if availability >= 0.95
            else "critical"
        )

        overall_status = "healthy"
        for layer_name, layer_data in layer_metrics.items():
            if layer_data["status"] == "critical":
                overall_status = "critical"
                break
            elif layer_data["status"] == "warning" and overall_status != "critical":
                overall_status = "warning"

        return {
            "overall_status": overall_status,
            "layers": layer_metrics,
            "total_executions_24h": total_executions,
            "overall_success_rate": success_rate,
            "timestamp": datetime.now().isoformat()
        }
