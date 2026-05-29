#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工作流4: CI/CD自动化
自动构建、测试、部署
"""

try:
    from ..models import Workflow, TaskDefinition, TriggerConfig, ScheduleConfig, TriggerType
except (ImportError, SystemError):
    from models import Workflow, TaskDefinition, TriggerConfig, ScheduleConfig, TriggerType


class CICDWorkflow:
    workflow_id = "WF-004"
    name = "CI/CD自动化"
    description = "代码提交后自动触发构建测试部署"

    @staticmethod
    def get_definition() -> Workflow:
        task1 = TaskDefinition(
            task_id="code_checkout",
            name="代码检出",
            description="从Git仓库拉取最新代码",
            agent_id="devops"
        )

        task2 = TaskDefinition(
            task_id="run_tests",
            name="运行测试",
            description="执行单元测试和集成测试",
            agent_id="devops",
            dependencies=["code_checkout"]
        )

        task3 = TaskDefinition(
            task_id="build",
            name="构建",
            description="构建可执行产物",
            agent_id="devops",
            dependencies=["run_tests"]
        )

        task4 = TaskDefinition(
            task_id="deploy",
            name="部署",
            description="部署到目标环境",
            agent_id="devops",
            dependencies=["build"]
        )

        task5 = TaskDefinition(
            task_id="verify",
            name="验证",
            description="验证部署结果",
            agent_id="devops",
            dependencies=["deploy"]
        )

        return Workflow(
            workflow_id=CICDWorkflow.workflow_id,
            name=CICDWorkflow.name,
            description=CICDWorkflow.description,
            trigger=TriggerConfig(
                trigger_type=TriggerType.EVENT,
                event_name="git_push"
            ),
            schedule=ScheduleConfig(enabled=True),
            tasks=[task1, task2, task3, task4, task5],
            dependencies={
                "code_checkout": [],
                "run_tests": ["code_checkout"],
                "build": ["run_tests"],
                "deploy": ["build"],
                "verify": ["deploy"]
            },
            assigned_agents=["devops"]
        )
