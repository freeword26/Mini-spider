#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SystemMonitorAlerts — 系统资源监控与告警
- CPU/内存/磁盘实时监控
- 工作流成功率监控
- 阈值告警 → 通过 NotificationHub 异步投递
- Prometheus 指标导出
"""

import asyncio
import logging
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

try:
    import psutil
except ImportError:
    psutil = None
    logger.warning("psutil not available, system metrics will be limited")

DEFAULT_THRESHOLDS = {
    "cpu_warning": 80.0,
    "cpu_critical": 90.0,
    "memory_warning": 80.0,
    "memory_critical": 90.0,
    "disk_warning": 85.0,
    "disk_critical": 95.0,
}


@dataclass
class AlertEvent:
    alert_id: str
    level: str
    category: str
    title: str
    detail: str
    value: float
    threshold: float
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    acknowledged: bool = False


class SystemMonitorAlerts:
    """系统资源监控 + 告警"""

    def __init__(self, thresholds: Optional[Dict] = None, alert_callback: Optional[Callable] = None):
        self.thresholds = {**DEFAULT_THRESHOLDS, **(thresholds or {})}
        self.alert_callback = alert_callback
        self._alerts: List[AlertEvent] = []
        self._running = False

    def check_system_health(self) -> Dict:
        """检查系统整体健康状态"""
        now = datetime.now()
        metrics = self._collect_metrics()
        alerts = self._evaluate_thresholds(metrics)

        if alerts and self.alert_callback:
            for alert in alerts:
                self._alerts.append(alert)
                try:
                    if asyncio.iscoroutinefunction(self.alert_callback):
                        asyncio.create_task(self.alert_callback(alert))
                    else:
                        self.alert_callback(alert)
                except Exception as e:
                    logger.error(f"Alert callback error: {e}")

        healthy = not any(a.level in ("critical", "error") for a in alerts)

        return {
            "healthy": healthy,
            "timestamp": now.isoformat(),
            "metrics": metrics,
            "alerts": len(alerts),
            "alert_details": [
                {"level": a.level, "category": a.category, "title": a.title, "value": a.value, "threshold": a.threshold}
                for a in alerts
            ],
            "summary": self._generate_summary(metrics, alerts),
        }

    def get_metrics(self) -> Dict:
        """获取当前系统指标（供 Prometheus / API 使用）"""
        return self._collect_metrics()

    def get_active_alerts(self) -> List[Dict]:
        """获取未确认的告警"""
        return [
            {
                "alert_id": a.alert_id,
                "level": a.level,
                "category": a.category,
                "title": a.title,
                "value": a.value,
                "threshold": a.threshold,
                "timestamp": a.timestamp,
            }
            for a in self._alerts
            if not a.acknowledged
        ]

    def acknowledge_alert(self, alert_id: str) -> bool:
        for a in self._alerts:
            if a.alert_id == alert_id:
                a.acknowledged = True
                return True
        return False

    def _collect_metrics(self) -> Dict:
        metrics = {"cpu_percent": 0.0, "memory_percent": 0.0, "disk_percent": 0.0, "timestamp": datetime.now().isoformat()}
        if psutil:
            try:
                metrics["cpu_percent"] = psutil.cpu_percent(interval=1)
                metrics["memory_percent"] = psutil.virtual_memory().percent
                metrics["disk_percent"] = psutil.disk_usage("/").percent
                metrics["cpu_count"] = psutil.cpu_count()
                metrics["memory_total_gb"] = round(psutil.virtual_memory().total / (1024 ** 3), 2)
                metrics["memory_available_gb"] = round(psutil.virtual_memory().available / (1024 ** 3), 2)
                metrics["disk_total_gb"] = round(psutil.disk_usage("/").total / (1024 ** 3), 2)
                metrics["disk_free_gb"] = round(psutil.disk_usage("/").free / (1024 ** 3), 2)
            except Exception as e:
                logger.warning(f"Failed to collect system metrics: {e}")
        return metrics

    def _evaluate_thresholds(self, metrics: Dict) -> List[AlertEvent]:
        alerts = []
        checks = [
            ("cpu", metrics.get("cpu_percent", 0), "cpu_warning", "cpu_critical", "%"),
            ("memory", metrics.get("memory_percent", 0), "memory_warning", "memory_critical", "%"),
            ("disk", metrics.get("disk_percent", 0), "disk_warning", "disk_critical", "%"),
        ]
        for category, value, warn_key, crit_key, unit in checks:
            warn_threshold = self.thresholds.get(warn_key, 80)
            crit_threshold = self.thresholds.get(crit_key, 90)
            if value >= crit_threshold:
                alerts.append(AlertEvent(
                    alert_id=f"alert_{category}_{int(time.time())}",
                    level="critical", category=category,
                    title=f"{category.upper()} 使用率超过 {crit_threshold}%",
                    detail=f"当前: {value:.1f}{unit}, 阈值: {crit_threshold}{unit}",
                    value=value, threshold=crit_threshold,
                ))
            elif value >= warn_threshold:
                alerts.append(AlertEvent(
                    alert_id=f"alert_{category}_{int(time.time())}",
                    level="warning", category=category,
                    title=f"{category.upper()} 使用率超过 {warn_threshold}%",
                    detail=f"当前: {value:.1f}{unit}, 阈值: {warn_threshold}{unit}",
                    value=value, threshold=warn_threshold,
                ))
        return alerts

    def _generate_summary(self, metrics: Dict, alerts: List[AlertEvent]) -> str:
        cpu = metrics.get("cpu_percent", 0)
        mem = metrics.get("memory_percent", 0)
        disk = metrics.get("disk_percent", 0)
        alert_count = len(alerts)
        critical = sum(1 for a in alerts if a.level == "critical")
        return f"CPU {cpu:.1f}% | MEM {mem:.1f}% | DISK {disk:.1f}% | Alerts: {alert_count} ({critical} critical)"
