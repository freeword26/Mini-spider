#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
22个项目无人值守事件调度器
三层闭环架构 - 事件层 (Event Fabric)
"""

import time
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)

try:
    import schedule
except ImportError:
    schedule = None

try:
    from workflows.wf_daily_ops import DailyOpsWorkflow
except ImportError:
    DailyOpsWorkflow = None
    logger.warning("DailyOpsWorkflow not available")


@dataclass
class ProjectScheduleConfig:
    project_id: str
    project_name: str
    layer: str
    tasks: List[str]
    schedule: List[str]
    priority: str


class TwentyTwoProjectScheduler:
    """22个项目无人值守事件调度器"""

    PROJECT_SCHEDULES = {
        "SYS_DAILY_OPS": {
            "project_name": "无人值守每日运维",
            "tasks": ["system_health", "generate_report"],
            "schedule": ["07:00", "20:00"],
            "layer": "指挥控制层",
            "priority": "P0"
        },
        "P001_TAPD": {
            "project_name": "3_任务执行中枢（TAPD）",
            "tasks": ["task_distribution", "progress_monitoring"],
            "schedule": ["09:00", "14:00", "18:00"],
            "layer": "指挥控制层",
            "priority": "P0"
        },
        "P002_meta_agent": {
            "project_name": "Meta-Agent元智能体",
            "tasks": ["decision_sync", "reflection_cycle"],
            "schedule": ["10:00", "16:00"],
            "layer": "指挥控制层",
            "priority": "P0"
        },
        "P003_dag_manager": {
            "project_name": "多项目DAG管理系统",
            "tasks": ["dag_visualization", "dependency_check"],
            "schedule": ["09:30", "15:00"],
            "layer": "指挥控制层",
            "priority": "P0"
        },
        "P004_watchdog": {
            "project_name": "看门狗与自愈系统",
            "tasks": ["health_check", "self_healing"],
            "schedule": ["*/15"],
            "layer": "指挥控制层",
            "priority": "P0"
        },
        "P005_lqm_framework": {
            "project_name": "LQM轻量级微服务框架",
            "tasks": ["service_registration", "health_poll"],
            "schedule": ["*/30"],
            "layer": "指挥控制层",
            "priority": "P1"
        },
        "P006_notification_center": {
            "project_name": "异步通知中心",
            "tasks": ["queue_drain", "alert_delivery"],
            "schedule": ["*/10"],
            "layer": "指挥控制层",
            "priority": "P1"
        },
        "P007_worker_cluster": {
            "project_name": "Worker智能体集群",
            "tasks": ["task_execution", "agent_coordination"],
            "schedule": ["09:00-18:00/30"],
            "layer": "执行协作层",
            "priority": "P0"
        },
        "P008_astrbot": {
            "project_name": "AstrBot",
            "tasks": ["user_interaction", "intent_recognition"],
            "schedule": ["09:00-21:00/15"],
            "layer": "执行协作层",
            "priority": "P0"
        },
        "P009_obsidian_manager": {
            "project_name": "Obsidian笔记管理系统",
            "tasks": ["note_sync", "vault_maintenance"],
            "schedule": ["08:00", "12:00", "20:00"],
            "layer": "执行协作层",
            "priority": "P1"
        },
        "P010_chaos_workflow": {
            "project_name": "混沌工作流执行系统",
            "tasks": ["chaos_execution", "result_collection"],
            "schedule": ["11:00", "17:00"],
            "layer": "执行协作层",
            "priority": "P1"
        },
        "P011_stats_system": {
            "project_name": "统计数据系统",
            "tasks": ["data_collection", "report_generation"],
            "schedule": ["02:00", "14:00"],
            "layer": "资源与环境层",
            "priority": "P1"
        },
        "P012_obsidian_vault": {
            "project_name": "Obsidian Vault",
            "tasks": ["vault_sync", "metadata_update"],
            "schedule": ["03:00", "15:00"],
            "layer": "资源与环境层",
            "priority": "P2"
        },
        "P013_api_gateway": {
            "project_name": "API网关与服务发现",
            "tasks": ["route_sync", "service_discovery"],
            "schedule": ["*/30"],
            "layer": "资源与环境层",
            "priority": "P1"
        },
        "P014_etl_skills": {
            "project_name": "ETL技能库迭代系统",
            "tasks": ["skill_sync", "dependency_update"],
            "schedule": ["*/30"],
            "layer": "资源与环境层",
            "priority": "P1"
        },
        "P015_automa_plugin": {
            "project_name": "Automa浏览器插件本地连接",
            "tasks": ["browser_health", "script_sync"],
            "schedule": ["*/45"],
            "layer": "资源与环境层",
            "priority": "P2"
        },
        "P016_global_memory": {
            "project_name": "全局状态与记忆库",
            "tasks": ["memory_consolidation", "state_backup"],
            "schedule": ["04:00", "16:00"],
            "layer": "资源与环境层",
            "priority": "P1"
        },
        "P017_scenario_sales": {
            "project_name": "场景式销售系统",
            "tasks": ["scenario_refresh", "template_sync"],
            "schedule": ["06:00", "18:00"],
            "layer": "资源与环境层",
            "priority": "P2"
        },
        "P018_cultural_kb": {
            "project_name": "多元文化知识库",
            "tasks": ["kb_index", "content_refresh"],
            "schedule": ["05:00"],
            "layer": "资源与环境层",
            "priority": "P2"
        },
        "P019_core_lib": {
            "project_name": "core_lib",
            "tasks": ["lib_sync", "version_check"],
            "schedule": ["*/60"],
            "layer": "资源与环境层",
            "priority": "P1"
        },
        "P020_experiments": {
            "project_name": "experiments",
            "tasks": ["sandbox_cleanup", "result_archive"],
            "schedule": ["22:00"],
            "layer": "资源与环境层",
            "priority": "P2"
        },
        "P021_dashboard": {
            "project_name": "数据可视化仪表板",
            "tasks": ["metric_refresh", "chart_update"],
            "schedule": ["*/15"],
            "layer": "资源与环境层",
            "priority": "P1"
        },
        "P022_fast_dev": {
            "project_name": "快反开发模式项目",
            "tasks": ["template_sync", "ci_trigger"],
            "schedule": ["09:00", "14:00", "19:00"],
            "layer": "资源与环境层",
            "priority": "P2"
        }
    }

    def __init__(
        self,
        event_bus=None,
        rabbitmq_publisher: Optional[Callable] = None,
        workspace_sync: Optional[Callable] = None
    ):
        self.event_bus = event_bus
        self.rabbitmq_publisher = rabbitmq_publisher
        self.workspace_sync = workspace_sync
        self._executed_count = 0
        if schedule:
            self.setup_schedules()

    def setup_schedules(self):
        if not schedule:
            logger.warning("schedule module not available, skipping schedule setup")
            return
        for project_id, config in self.PROJECT_SCHEDULES.items():
            for task in config["tasks"]:
                for time_str in config["schedule"]:
                    if "*/" in time_str:
                        interval = int(time_str.split("*/")[1])
                        schedule.every(interval).minutes.do(
                            self._execute_project_task,
                            project_id, task
                        )
                    elif "-" in time_str:
                        parts = time_str.split("/")
                        time_range = parts[0]
                        start_hour = int(time_range.split("-")[0].split(":")[0])
                        end_hour = int(time_range.split("-")[1].split(":")[0])
                        for hour in range(start_hour, end_hour + 1):
                            schedule.every().day.at(f"{hour:02d}:00").do(
                                self._execute_project_task,
                                project_id, task
                            )
                    else:
                        schedule.every().day.at(time_str).do(
                            self._execute_project_task,
                            project_id, task
                        )
        logger.info(
            f"22项目调度器已注册 {len(schedule.get_jobs())} 个定时任务"
        )

    def start_scheduler(self):
        if not schedule:
            logger.error("schedule module not available, cannot start scheduler")
            return
        jobs = len(schedule.get_jobs())
        logger.info(f"22项目无人值守调度器启动，共 {jobs} 个定时任务")
        while True:
            schedule.run_pending()
            time.sleep(1)

    def _execute_project_task(self, project_id: str, task_name: str):
        if project_id == "SYS_DAILY_OPS":
            if DailyOpsWorkflow:
                try:
                    DailyOpsWorkflow.execute(task_name)
                    self._executed_count += 1
                    logger.info(f"DailyOpsWorkflow executed: {task_name}")
                except Exception as e:
                    logger.error(f"DailyOpsWorkflow execution failed: {e}")
            else:
                logger.error("DailyOpsWorkflow not available")
            return True

        config = self.PROJECT_SCHEDULES.get(project_id, {})
        timestamp = datetime.utcnow().isoformat()
        priority = config.get("priority", "P2")
        event = {
            "event_id": f"task_{project_id}_{task_name}_{int(time.time())}",
            "event_type": "scheduled_task",
            "project_id": project_id,
            "project_name": config.get("project_name", project_id),
            "layer": config.get("layer", ""),
            "priority": priority,
            "task_name": task_name,
            "timestamp": timestamp,
            "routing_key": f"project.{project_id.lower()}.{task_name.lower()}"
        }

        try:
            from .event_bus import AgentMessage
        except (ImportError, SystemError):
            from event_bus import AgentMessage

        try:
            message = AgentMessage(
                sender_id="project_scheduler",
                receiver_id="*",
                priority=5 if priority == "P0" else 3,
                payload=event
            )

            if self.event_bus:
                import asyncio
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(self.event_bus.publish(message))
                except RuntimeError:
                    asyncio.run(self.event_bus.publish(message))

            if self.rabbitmq_publisher:
                self.rabbitmq_publisher(event.get("routing_key"), event)

            if self.workspace_sync:
                self.workspace_sync(event)

        except Exception as e:
            logger.error(f"Error publishing task event {project_id}/{task_name}: {e}")

        self._executed_count += 1
        logger.info(f"已调度: {project_id}/{task_name} (总计: {self._executed_count})")
        return True

    def get_schedule_status(self) -> Dict:
        if schedule:
            total_jobs = len(schedule.get_jobs())
        else:
            total_jobs = 0
        layer_counts = {}
        priority_counts = {}
        for pid, cfg in self.PROJECT_SCHEDULES.items():
            layer = cfg.get("layer", "未知")
            layer_counts[layer] = layer_counts.get(layer, 0) + 1
            pri = cfg.get("priority", "P2")
            priority_counts[pri] = priority_counts.get(pri, 0) + 1
        return {
            "total_projects": len(self.PROJECT_SCHEDULES),
            "total_jobs": total_jobs,
            "executed_count": self._executed_count,
            "layer_distribution": layer_counts,
            "priority_distribution": priority_counts,
        }
