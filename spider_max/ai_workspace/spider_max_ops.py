#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Spider MAX v3.1.0 主入口 — AI Workspace 集成

使用示例:
    from spider_max.ai_workspace import SpiderMAXOps

    ops = SpiderMAXOps()
    ops.start_monitoring()          # 启动系统监控
    ops.backup_database()           # 备份数据库
    ops.snapshot_config()           # 配置快照
    ops.send_notification(...)      # 发送通知
    ops.check_health()              # 完整健康检查
    ops.execute_recovery_runbook()  # 灾难恢复手册
"""

import asyncio
import logging
from typing import Dict, Optional

from spider_max.ai_workspace.recovery.recovery_manager import RecoveryManager
from spider_max.ai_workspace.notifications.notification_hub import NotificationHub, NotificationLevel, ChannelType
from spider_max.ai_workspace.dispatchers.agent_dispatcher import AgentDispatcher, AgentRole
from spider_max.ai_workspace.recovery.db_backup import DatabaseBackup
from spider_max.ai_workspace.recovery.config_rollback import ConfigRollback
from spider_max.ai_workspace.recovery.monitor_alerts import SystemMonitorAlerts
from spider_max.ai_workspace.recovery.rebuild import RebuildScript
from spider_max.ai_workspace.docs.doc_generator import generate_all

logger = logging.getLogger(__name__)


class SpiderMAXOps:
    """Spider MAX 运营操作统一入口（人类接口）"""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.recovery = RecoveryManager(config)
        self.notifications = NotificationHub(self.config.get("notifications", {}))
        self.dispatcher = AgentDispatcher(max_concurrent=self.config.get("max_concurrent_agents", 5))

    def backup_database(self, tag: str = "") -> Dict:
        return self.recovery.db_backup.backup(tag=tag)

    def restore_database(self) -> Dict:
        return self.recovery.db_backup.restore()

    def snapshot_config(self, config_data: Optional[Dict] = None, tag: str = "") -> Dict:
        from spider_max.config import load_config
        if config_data is None:
            config_data = load_config().to_dict()
        return self.recovery.config_rollback.snapshot(config_data, tag=tag)

    def rollback_config(self, steps: int = 1) -> Dict:
        return self.recovery.config_rollback.rollback(steps=steps)

    def check_system_health(self) -> Dict:
        return self.recovery.monitor.check_system_health()

    def check_full_health(self) -> Dict:
        return self.recovery.full_health_check()

    def generate_docs(self, output_dir: Optional[str] = None) -> Dict:
        return generate_all(output_dir=output_dir)

    def get_recovery_runbook(self) -> Dict:
        return self.recovery.disaster_recovery_runbook()

    def test_notification_channels(self) -> Dict:
        return self.notifications.test_channels()

    async def notify(self, title: str, message: str, level: str = "info", channels: Optional[list] = None) -> Dict:
        ch_list = [ChannelType(c) for c in (channels or ["console"])]
        result = await self.notifications.notify(
            title=title, message=message,
            level=NotificationLevel(level), channels=ch_list,
        )
        return {
            "id": result.notification_id,
            "delivered": result.delivered,
            "results": result.delivery_results,
        }

    def list_backups(self) -> list:
        return self.recovery.db_backup.list_backups()

    def list_config_snapshots(self) -> list:
        return self.recovery.config_rollback.list_snapshots()

    def list_active_alerts(self) -> list:
        return self.recovery.monitor.get_active_alerts()

    def get_system_metrics(self) -> Dict:
        return self.recovery.monitor.get_metrics()
