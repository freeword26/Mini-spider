#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用示例
展示如何使用无人值守工作流管理系统
"""

import asyncio
import logging
from datetime import datetime, timedelta

from models import (
    Workflow, TaskDefinition, TriggerConfig, ScheduleConfig,
    RetryConfig, CircuitBreakerConfig, TriggerType
)
from workflow_executor import WorkflowExecutor
from event_bus import EventBus, AgentMessage
from scheduler import WorkflowScheduler
from orchestrator import Orchestrator, CollaborationMode
from monitoring import Monitoring, Alert

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def example_basic_workflow():
    logger.info("=== 示例1: 基本工作流执行 ===")

    event_bus = EventBus()
    executor = WorkflowExecutor()

    task1 = TaskDefinition(
        task_id="task_1",
        name="数据采集",
        description="从数据源采集数据",
        agent_id="data-scientist"
    )

    task2 = TaskDefinition(
        task_id="task_2",
        name="数据处理",
        description="处理采集的数据",
        agent_id="data-scientist",
        dependencies=["task_1"]
    )

    task3 = TaskDefinition(
        task_id="task_3",
        name="生成报表",
        description="生成分析报表",
        agent_id="data-scientist",
        dependencies=["task_2"]
    )

    workflow = Workflow(
        workflow_id="WF-DEMO-001",
        name="数据采集处理流程",
        description="演示用数据采集处理工作流",
        tasks=[task1, task2, task3],
        dependencies={
            "task_1": [],
            "task_2": ["task_1"],
            "task_3": ["task_2"]
        }
    )

    execution = await executor.execute(workflow, {"source": "demo"})
    logger.info(f"Execution completed: {execution.execution_id}, Status: {execution.status}")

    return execution


async def example_scheduled_workflow():
    logger.info("=== 示例2: 定时调度工作流 ===")

    event_bus = EventBus()
    executor = WorkflowExecutor()
    scheduler = WorkflowScheduler(executor, event_bus)

    task = TaskDefinition(
        task_id="daily_task",
        name="每日数据同步",
        description="每日同步数据",
        agent_id="data-scientist"
    )

    workflow = Workflow(
        workflow_id="WF-SCHED-001",
        name="每日数据同步",
        description="每日定时同步数据",
        trigger=TriggerConfig(
            trigger_type=TriggerType.CRON,
            cron_expression="0 2 * * *"
        ),
        schedule=ScheduleConfig(
            enabled=True,
            timezone="Asia/Shanghai"
        ),
        tasks=[task]
    )

    scheduler.register_workflow(workflow)
    logger.info(f"Registered workflow: {workflow.workflow_id}")
    logger.info(f"Next fire time: {scheduler.get_next_scheduled_time(workflow.workflow_id)}")

    execution = await scheduler.trigger_workflow(
        workflow.workflow_id,
        trigger_type="manual",
        trigger_source="demo"
    )
    logger.info(f"Manual trigger result: {execution.execution_id}")


async def example_with_orchestrator():
    logger.info("=== 示例3: 使用编排器(PMO模式) ===")

    event_bus = EventBus()
    executor = WorkflowExecutor()
    orchestrator = Orchestrator(event_bus, executor)

    tasks = [
        TaskDefinition(
            task_id="plan",
            name="项目规划",
            description="制定项目计划",
            agent_id="system-manager"
        ),
        TaskDefinition(
            task_id="design",
            name="系统设计",
            description="完成系统设计",
            agent_id="tech-expert",
            dependencies=["plan"]
        ),
        TaskDefinition(
            task_id="implement",
            name="编码实现",
            description="实现系统功能",
            agent_id="developer",
            dependencies=["design"]
        ),
        TaskDefinition(
            task_id="test",
            name="测试验证",
            description="完成测试验证",
            agent_id="qa",
            dependencies=["implement"]
        )
    ]

    workflow = Workflow(
        workflow_id="WF-PMO-001",
        name="项目开发流程",
        description="PMO模式项目开发流程",
        tasks=tasks,
        dependencies={
            "plan": [],
            "design": ["plan"],
            "implement": ["design"],
            "test": ["implement"]
        }
    )

    result = await orchestrator.execute_workflow(
        workflow,
        mode=CollaborationMode.PMO.value
    )
    logger.info(f"PMO execution result: {result['status']}")


async def example_with_monitoring():
    logger.info("=== 示例4: 监控与告警 ===")

    event_bus = EventBus()
    executor = WorkflowExecutor()
    monitoring = Monitoring(event_bus, executor.circuit_breaker)

    task = TaskDefinition(
        task_id="monitored_task",
        name="被监控的任务",
        description="执行一个被监控的任务",
        agent_id="system-manager"
    )

    workflow = Workflow(
        workflow_id="WF-MON-001",
        name="监控测试工作流",
        tasks=[task]
    )

    execution = await executor.execute(workflow)
    await monitoring.record_execution(execution)

    alerts = await monitoring.check_thresholds()
    if alerts:
        for alert in alerts:
            logger.warning(f"Alert: [{alert.level}] {alert.title}")

    report = monitoring.generate_daily_report()
    logger.info(f"Daily report: {report.total_executions} executions, {report.success_rate:.2%} success rate")


async def example_event_driven():
    logger.info("=== 示例5: 事件驱动工作流 ===")

    event_bus = EventBus()
    executor = WorkflowExecutor()
    scheduler = WorkflowScheduler(executor, event_bus)

    task = TaskDefinition(
        task_id="event_task",
        name="事件处理任务",
        description="处理触发的事件",
        agent_id="skill-manager"
    )

    workflow = Workflow(
        workflow_id="WF-EVENT-001",
        name="事件驱动工作流",
        trigger=TriggerConfig(
            trigger_type=TriggerType.EVENT,
            event_name="data_uploaded"
        ),
        tasks=[task]
    )

    scheduler.register_workflow(workflow)

    await event_bus.publish(AgentMessage(
        sender_id="external_system",
        receiver_id="scheduler",
        payload={
            "event": "data_uploaded",
            "file_id": "file_123",
            "timestamp": datetime.now().isoformat()
        }
    ))

    await asyncio.sleep(2)

    status = scheduler.get_workflow_status("WF-EVENT-001")
    logger.info(f"Workflow status: {status['total_executions']} executions")


async def main():
    logger.info("无人值守工作流管理系统演示")
    logger.info("=" * 50)

    await example_basic_workflow()
    await asyncio.sleep(1)

    await example_scheduled_workflow()
    await asyncio.sleep(1)

    await example_with_orchestrator()
    await asyncio.sleep(1)

    await example_with_monitoring()
    await asyncio.sleep(1)

    await example_event_driven()

    logger.info("=" * 50)
    logger.info("所有演示完成")


if __name__ == "__main__":
    asyncio.run(main())
