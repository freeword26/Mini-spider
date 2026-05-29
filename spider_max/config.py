#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置文件
无人值守工作流管理系统配置
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


@dataclass
class SystemConfig:
    system_name: str = "无人值守工作流管理系统"
    version: str = "1.0.0"
    environment: str = "development"
    debug: bool = True
    timezone: str = "Asia/Shanghai"


@dataclass
class ServerConfig:
    host: str = "0.0.0.0"
    port: int = 5005
    workers: int = 4
    reload: bool = True


@dataclass
class StorageConfig:
    data_dir: str = "e:/统计数据系统/08_上下文记录"
    workflow_dir: str = "e:/统计数据系统/10_自动化工作流"
    backup_dir: str = "e:/统计数据系统/04_备份"
    max_storage_days: int = 90


@dataclass
class WorkflowConfig:
    max_concurrent_workflows: int = 10
    default_timeout: int = 3600
    default_retry_attempts: int = 3
    default_retry_interval: int = 300
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: int = 3600


@dataclass
class AgentConfig:
    agent_registry_path: str = "e:/统计数据系统/06_Agent定义"
    schedule_config_path: str = "e:/统计数据系统/06_Agent定义/排班表"
    heartbeat_interval: int = 30
    offline_threshold: int = 90


@dataclass
class MonitoringConfig:
    metrics_retention_days: int = 30
    alert_retention_days: int = 90
    report_generation_hour: int = 8
    health_check_interval: int = 60


@dataclass
class EventBusConfig:
    mode: str = "memory"
    rabbitmq_url: str = "amqp://admin:admin123@localhost:5672/"
    exchange_name: str = "project.events"
    exchange_type: str = "topic"
    reconnect_interval: int = 5
    max_history_size: int = 1000
    dead_letter_threshold: int = 10


@dataclass
class AstrBotGatewayConfig:
    enabled: bool = False
    intent_recognition_url: str = ""
    authorization_timeout: int = 300
    max_tokens: int = 300
    low_token_mode: bool = True


@dataclass
class AlertConfig:
    enabled: bool = True
    feishu_webhook: Optional[str] = None
    email_enabled: bool = False
    email_recipients: List[str] = field(default_factory=list)
    webhook_urls: Dict[str, str] = field(default_factory=dict)


@dataclass
class Config:
    system: SystemConfig = field(default_factory=SystemConfig)
    server: ServerConfig = field(default_factory=ServerConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    workflow: WorkflowConfig = field(default_factory=WorkflowConfig)
    agent: AgentConfig = field(default_factory=AgentConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    alert: AlertConfig = field(default_factory=AlertConfig)
    event_bus: EventBusConfig = field(default_factory=EventBusConfig)
    astrbot_gateway: AstrBotGatewayConfig = field(default_factory=AstrBotGatewayConfig)

    @classmethod
    def from_dict(cls, data: Dict) -> "Config":
        return cls(
            system=SystemConfig(**data.get("system", {})),
            server=ServerConfig(**data.get("server", {})),
            storage=StorageConfig(**data.get("storage", {})),
            workflow=WorkflowConfig(**data.get("workflow", {})),
            agent=AgentConfig(**data.get("agent", {})),
            monitoring=MonitoringConfig(**data.get("monitoring", {})),
            alert=AlertConfig(**data.get("alert", {}))
        )

    def to_dict(self) -> Dict:
        return {
            "system": {
                "system_name": self.system.system_name,
                "version": self.system.version,
                "environment": self.system.environment,
                "debug": self.system.debug,
                "timezone": self.system.timezone
            },
            "server": {
                "host": self.server.host,
                "port": self.server.port,
                "workers": self.server.workers,
                "reload": self.server.reload
            },
            "storage": {
                "data_dir": self.storage.data_dir,
                "workflow_dir": self.storage.workflow_dir,
                "backup_dir": self.storage.backup_dir,
                "max_storage_days": self.storage.max_storage_days
            },
            "workflow": {
                "max_concurrent_workflows": self.workflow.max_concurrent_workflows,
                "default_timeout": self.workflow.default_timeout,
                "default_retry_attempts": self.workflow.default_retry_attempts,
                "default_retry_interval": self.workflow.default_retry_interval,
                "circuit_breaker_threshold": self.workflow.circuit_breaker_threshold,
                "circuit_breaker_timeout": self.workflow.circuit_breaker_timeout
            },
            "agent": {
                "agent_registry_path": self.agent.agent_registry_path,
                "schedule_config_path": self.agent.schedule_config_path,
                "heartbeat_interval": self.agent.heartbeat_interval,
                "offline_threshold": self.agent.offline_threshold
            },
            "monitoring": {
                "metrics_retention_days": self.monitoring.metrics_retention_days,
                "alert_retention_days": self.monitoring.alert_retention_days,
                "report_generation_hour": self.monitoring.report_generation_hour,
                "health_check_interval": self.monitoring.health_check_interval
            },
            "alert": {
                "enabled": self.alert.enabled,
                "feishu_webhook": self.alert.feishu_webhook,
                "email_enabled": self.alert.email_enabled,
                "email_recipients": self.alert.email_recipients,
                "webhook_urls": self.alert.webhook_urls
            }
        }


def load_config(config_path: Optional[str] = None) -> Config:
    import json

    if config_path is None:
        config_path = os.environ.get("WORKFLOW_CONFIG", "config.json")

    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return Config.from_dict(data)
        except Exception as e:
            print(f"Failed to load config from {config_path}: {e}")

    return Config()


DEFAULT_CONFIG = Config()
