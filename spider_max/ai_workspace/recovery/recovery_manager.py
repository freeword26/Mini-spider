#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RecoveryManager — 灾难恢复统一入口
整合: DatabaseBackup + ConfigRollback + SystemMonitorAlerts + RebuildScript
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from spider_max.ai_workspace.recovery.db_backup import DatabaseBackup
from spider_max.ai_workspace.recovery.config_rollback import ConfigRollback
from spider_max.ai_workspace.recovery.monitor_alerts import SystemMonitorAlerts
from spider_max.ai_workspace.recovery.rebuild import RebuildScript

logger = logging.getLogger(__name__)


class RecoveryManager:
    """灾难恢复统一管理器"""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.db_backup = DatabaseBackup(
            retention_days=self.config.get("backup_retention_days", 7),
        )
        self.config_rollback = ConfigRollback(
            max_snapshots=self.config.get("max_config_snapshots", 20),
        )
        self.monitor = SystemMonitorAlerts(
            thresholds=self.config.get("alert_thresholds"),
        )
        self.rebuild = RebuildScript(
            repo_url=self.config.get("repo_url", "https://github.com/freeword26/Mini-spider.git"),
            branch=self.config.get("branch", "main"),
        )

    def full_health_check(self) -> Dict:
        """执行完整健康检查"""
        db_health = self.db_backup.check_health()
        monitor_health = self.monitor.check_system_health()
        snapshots = len(self.config_rollback.list_snapshots())
        active_alerts = len(self.monitor.get_active_alerts())

        all_healthy = db_health.get("healthy", False) and monitor_health.get("healthy", False)

        return {
            "overall_healthy": all_healthy,
            "timestamp": datetime.now().isoformat(),
            "database": db_health,
            "system": monitor_health,
            "config_snapshots": snapshots,
            "active_alerts": active_alerts,
        }

    def disaster_recovery_runbook(self) -> Dict:
        """输出灾难恢复操作手册（供运维人员参考）"""
        db_health = self.db_backup.check_health()
        backups = self.db_backup.list_backups()[:3]

        return {
            "scenario_1_db_corrupted": {
                "description": "数据库文件损坏",
                "steps": [
                    "1. 确认损坏: python -m spider_max.ai_workspace.recovery.db_backup check",
                    "2. 恢复备份: python -m spider_max.ai_workspace.recovery.db_backup restore",
                    "3. 验证: curl http://localhost:8041/api/v1/health",
                ],
                "available_backups": db_health.get("available_backups", 0),
            },
            "scenario_2_config_error": {
                "description": "配置错误导致服务异常",
                "steps": [
                    "1. 回滚配置: python -m spider_max.ai_workspace.recovery.config_rollback rollback",
                    "2. 重启服务: spider_max restart",
                ],
                "config_snapshots": len(self.config_rollback.list_snapshots()),
            },
            "scenario_3_resource_exhaustion": {
                "description": "CPU/内存/磁盘耗尽",
                "steps": [
                    "1. 查看监控: python -m spider_max.ai_workspace.recovery.monitor_alerts check",
                    "2. 紧急重启: docker compose restart spider-max",
                    "3. 如需重建: python -m spider_max.ai_workspace.recovery.rebuild rebuild",
                ],
            },
            "scenario_4_full_rebuild": {
                "description": "从零重建完整环境",
                "steps": [
                    "1. git clone https://github.com/freeword26/Mini-spider.git",
                    "2. cd spider_max && pip install -e '.[dev]'",
                    "3. docker compose up -d",
                    "4. curl http://localhost:8041/api/v1/health",
                ],
                "estimated_time": "< 5 minutes",
            },
            "latest_backups": backups,
        }
