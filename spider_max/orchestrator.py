#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
编排调度器 - Orchestrator
整合multi_agent_orchestrator.py的5种协作模式
支持: PMO, DAG, SOP, BLACKBOARD, META_COGNITIVE
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from enum import Enum

try:
    from .models import Workflow, Execution, TaskDefinition
    from .event_bus import EventBus, AgentMessage
    from .workflow_executor import WorkflowExecutor
except ImportError:
    from models import Workflow, Execution, TaskDefinition
    from event_bus import EventBus, AgentMessage
    from workflow_executor import WorkflowExecutor

logger = logging.getLogger(__name__)


class CollaborationMode(str, Enum):
    PMO = "pmo"
    DAG = "dag"
    SOP = "sop"
    BLACKBOARD = "blackboard"
    META_COGNITIVE = "meta"


class BaseCollaborationMode:
    def __init__(self, event_bus: EventBus, executor: WorkflowExecutor):
        self.event_bus = event_bus
        self.executor = executor

    async def execute(self, workflow: Workflow, context: Dict) -> Dict[str, Any]:
        raise NotImplementedError


class PMOMode(BaseCollaborationMode):
    """PMO模式 - 项目经理主导，按顺序执行"""

    async def execute(self, workflow: Workflow, context: Dict) -> Dict[str, Any]:
        results = {}
        for task in workflow.tasks:
            logger.info(f"PMO: Executing task {task.task_id}")
            result = await self._execute_single_task(task, context)
            results[task.task_id] = result

            await self.event_bus.publish(AgentMessage(
                sender_id="orchestrator",
                receiver_id="*",
                payload={
                    "type": "task_completed",
                    "workflow_id": workflow.workflow_id,
                    "task_id": task.task_id,
                    "result": result
                }
            ))
        return results

    async def _execute_single_task(self, task: TaskDefinition, context: Dict) -> Dict:
        await asyncio.sleep(0.1)
        return {"status": "completed", "task_id": task.task_id}


class DAGMode(BaseCollaborationMode):
    """DAG模式 - 有向无环图，按依赖顺序执行"""

    async def execute(self, workflow: Workflow, context: Dict) -> Dict[str, Any]:
        results = {}
        executed = set()
        pending = {t.task_id for t in workflow.tasks}

        while pending:
            for task_id in list(pending):
                task = next((t for t in workflow.tasks if t.task_id == task_id), None)
                if not task:
                    pending.remove(task_id)
                    continue

                deps_met = all(dep in executed for dep in task.dependencies)
                if deps_met:
                    logger.info(f"DAG: Executing task {task_id}")
                    result = await self._execute_single_task(task, context)
                    results[task_id] = result
                    executed.add(task_id)
                    pending.remove(task_id)

                    await self.event_bus.publish(AgentMessage(
                        sender_id="orchestrator",
                        receiver_id="*",
                        payload={
                            "type": "task_completed",
                            "workflow_id": workflow.workflow_id,
                            "task_id": task_id,
                            "result": result
                        }
                    ))

            await asyncio.sleep(0.05)

        return results

    async def _execute_single_task(self, task: TaskDefinition, context: Dict) -> Dict:
        await asyncio.sleep(0.1)
        return {"status": "completed", "task_id": task.task_id}


class SOPMode(BaseCollaborationMode):
    """SOP模式 - 标准操作流程，严格步骤执行"""

    async def execute(self, workflow: Workflow, context: Dict) -> Dict[str, Any]:
        results = {}
        for i, task in enumerate(workflow.tasks):
            logger.info(f"SOP: Step {i+1}/{len(workflow.tasks)} - Executing {task.task_id}")
            result = await self._execute_single_task(task, context, step=i+1, total=len(workflow.tasks))
            results[task.task_id] = result

            if result.get("status") == "failed":
                logger.error(f"SOP: Step {i+1} failed, stopping workflow")
                break

        return results

    async def _execute_single_task(self, task: TaskDefinition, context: Dict, step: int = 1, total: int = 1) -> Dict:
        await asyncio.sleep(0.1)
        return {"status": "completed", "task_id": task.task_id, "step": step, "total": total}


class BlackboardMode(BaseCollaborationMode):
    """BLACKBOARD模式 - 共享黑板，多Agent协同"""

    def __init__(self, event_bus: EventBus, executor: WorkflowExecutor):
        super().__init__(event_bus, executor)
        self.blackboard: Dict[str, Any] = {}

    async def execute(self, workflow: Workflow, context: Dict) -> Dict[str, Any]:
        self.blackboard = {
            "shared_memory": {},
            "task_results": {},
            "contributions": []
        }

        async def contribute(agent_id: str, task_id: str, contribution: Dict) -> None:
            self.blackboard["shared_memory"][f"{agent_id}_{task_id}"] = contribution
            self.blackboard["contributions"].append({
                "agent_id": agent_id,
                "task_id": task_id,
                "contribution": contribution,
                "timestamp": datetime.now().isoformat()
            })

        tasks = workflow.tasks
        if tasks:
            first_task = tasks[0]
            logger.info(f"BLACKBOARD: Agent {first_task.agent_id} initiating workflow")
            result = await self._execute_single_task(first_task, context)
            await contribute(first_task.agent_id, first_task.task_id, result)

            for task in tasks[1:]:
                logger.info(f"BLACKBOARD: Agent {task.agent_id} contributing")
                result = await self._execute_single_task(task, context)
                await contribute(task.agent_id, task.task_id, result)

        return {
            "blackboard": self.blackboard,
            "status": "completed"
        }

    async def _execute_single_task(self, task: TaskDefinition, context: Dict) -> Dict:
        await asyncio.sleep(0.1)
        return {"status": "completed", "task_id": task.task_id, "agent_id": task.agent_id}


class MetaCognitiveMode(BaseCollaborationMode):
    """META_COGNITIVE模式 - 元认知反思模式"""

    async def execute(self, workflow: Workflow, context: Dict) -> Dict[str, Any]:
        results = {}
        reflections = []

        for task in workflow.tasks:
            logger.info(f"META: Reflecting before executing {task.task_id}")

            reflection = await self._reflect(task, context, reflections)
            reflections.append(reflection)

            if reflection.get("should_execute", True):
                logger.info(f"META: Executing task {task_id}")
                result = await self._execute_single_task(task, context)
                results[task.task_id] = result
            else:
                logger.info(f"META: Skipping task {task.task_id} based on reflection")
                results[task.task_id] = {"status": "skipped", "reason": reflection.get("reason")}

        return {
            "results": results,
            "reflections": reflections,
            "status": "completed"
        }

    async def _reflect(self, task: TaskDefinition, context: Dict, previous_reflections: List) -> Dict:
        await asyncio.sleep(0.05)
        return {
            "task_id": task.task_id,
            "should_execute": True,
            "reason": None,
            "confidence": 0.9
        }

    async def _execute_single_task(self, task: TaskDefinition, context: Dict) -> Dict:
        await asyncio.sleep(0.1)
        return {"status": "completed", "task_id": task.task_id}


class Orchestrator:
    def __init__(self, event_bus: EventBus, executor: WorkflowExecutor, config: Optional[Dict] = None):
        self.event_bus = event_bus
        self.executor = executor
        self.config = config or {}

        self._modes = {
            CollaborationMode.PMO: PMOMode(event_bus, executor),
            CollaborationMode.DAG: DAGMode(event_bus, executor),
            CollaborationMode.SOP: SOPMode(event_bus, executor),
            CollaborationMode.BLACKBOARD: BlackboardMode(event_bus, executor),
            CollaborationMode.META_COGNITIVE: MetaCognitiveMode(event_bus, executor),
        }

        self._default_mode = CollaborationMode.DAG

    async def execute_workflow(
        self,
        workflow: Workflow,
        mode: Optional[str] = None,
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        mode_enum = CollaborationMode(mode) if mode else self._default_mode
        executor = self._modes.get(mode_enum, self._modes[self._default_mode])

        logger.info(f"Executing workflow {workflow.workflow_id} in {mode_enum.value} mode")

        await self.event_bus.publish(AgentMessage(
            sender_id="orchestrator",
            receiver_id="*",
            payload={
                "type": "workflow_start",
                "workflow_id": workflow.workflow_id,
                "mode": mode_enum.value
            }
        ))

        try:
            result = await executor.execute(workflow, context or {})

            await self.event_bus.publish(AgentMessage(
                sender_id="orchestrator",
                receiver_id="*",
                payload={
                    "type": "workflow_complete",
                    "workflow_id": workflow.workflow_id,
                    "mode": mode_enum.value,
                    "result": result
                }
            ))

            return {
                "workflow_id": workflow.workflow_id,
                "mode": mode_enum.value,
                "status": "completed",
                "result": result
            }

        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")

            await self.event_bus.publish(self.event_bus.make_error_event(
                agent_id="orchestrator",
                task_id=workflow.workflow_id,
                error_type=type(e).__name__,
                stack_trace=str(e)
            ))

            return {
                "workflow_id": workflow.workflow_id,
                "mode": mode_enum.value,
                "status": "failed",
                "error": str(e)
            }

    def get_supported_modes(self) -> List[str]:
        return [m.value for m in CollaborationMode]

    def set_default_mode(self, mode: str) -> bool:
        try:
            mode_enum = CollaborationMode(mode)
            self._default_mode = mode_enum
            logger.info(f"Default mode set to {mode}")
            return True
        except ValueError:
            logger.error(f"Invalid mode: {mode}")
            return False
