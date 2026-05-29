#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工作流执行器 - WorkflowExecutor
整合DAG引擎、重试机制、熔断器、状态追踪
"""

import asyncio
import logging
import sqlite3
import time
import sys
import json
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field

_PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

try:
    from .models import (
        Workflow, Execution, TaskDefinition, TaskExecution,
        ExecutionStatus, ErrorInfo, RetryConfig, CircuitBreakerConfig
    )
except ImportError:
    from models import (
        Workflow, Execution, TaskDefinition, TaskExecution,
        ExecutionStatus, ErrorInfo, RetryConfig, CircuitBreakerConfig
    )

logger = logging.getLogger(__name__)

_EVENT_PUBLISHER = None


def _get_event_publisher():
    global _EVENT_PUBLISHER
    if _EVENT_PUBLISHER is None:
        try:
            from agents_orchestrator.core.event_publisher import EventPublisher
            _EVENT_PUBLISHER = EventPublisher()
            _EVENT_PUBLISHER.connect()
        except Exception as e:
            logger.warning(f"RabbitMQ 事件发布器初始化失败: {e}")
            _EVENT_PUBLISHER = False
    if _EVENT_PUBLISHER is False:
        return None
    return _EVENT_PUBLISHER


def _publish_workflow_event(event_type: str, payload: dict, target: str = "*"):
    pub = _get_event_publisher()
    if pub:
        try:
            from agents_orchestrator.core.message_bus import AgentMessage
            msg = AgentMessage(
                sender_id="workflow-executor",
                receiver_id=target,
                priority=payload.get("priority", 3),
                payload={"event_type": event_type, **payload},
            )
            pub.publish(msg)
        except Exception as e:
            logger.error(f"工作流事件发布失败: {e}")


@dataclass
class CircuitBreaker:
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[float] = None
    state: str = "closed"

    config: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)

    def record_success(self) -> None:
        self.failure_count = 0
        self.success_count += 1
        if self.state == "half_open" and self.success_count >= self.config.success_threshold:
            self.state = "closed"
            logger.info("Circuit breaker closed")
        elif self.state == "half_open" and self.success_count < self.config.success_threshold:
            self.state = "open"
            self.last_failure_time = time.time()
            logger.warning("Circuit breaker reopened after insufficient successes")

    def record_failure(self) -> None:
        self.failure_count += 1
        self.success_count = 0
        self.last_failure_time = time.time()

        if self.state == "closed" and self.failure_count >= self.config.failure_threshold:
            self.state = "open"
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")
        elif self.state == "half_open":
            self.state = "open"
            logger.warning("Circuit breaker reopened after failure in half-open state")

    def is_open(self) -> bool:
        if self.state == "open":
            if self.last_failure_time and (time.time() - self.last_failure_time) > self.config.timeout:
                self.state = "half_open"
                self.success_count = 0
                logger.info("Circuit breaker entering half-open state")
                return False
            return True
        return False

    def can_execute(self) -> bool:
        return self.state != "open"


class WorkflowExecutor:
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.circuit_breaker = CircuitBreaker(
            config=CircuitBreakerConfig(**self.config.get("circuit_breaker", {}))
        )
        self._executions: Dict[str, Execution] = {}
        self._running_tasks: Set[str] = set()

    async def execute(
        self,
        workflow: Workflow,
        context: Optional[Dict] = None,
        trigger_type: str = "manual",
        trigger_source: str = ""
    ) -> Execution:
        execution = Execution(
            workflow_id=workflow.workflow_id,
            workflow_version=workflow.version,
            trigger_type=trigger_type,
            trigger_source=trigger_source,
            executed_by="system"
        )
        execution.start_time = datetime.now().isoformat()

        self._executions[execution.execution_id] = execution

        logger.info(f"Starting workflow execution: {execution.execution_id} for workflow: {workflow.workflow_id}")

        _publish_workflow_event("workflow.started", {
            "workflow_id": workflow.workflow_id,
            "execution_id": execution.execution_id,
            "trigger_type": trigger_type,
            "trigger_source": trigger_source,
        })

        try:
            if not self.circuit_breaker.can_execute():
                raise Exception("Circuit breaker is open")

            execution.status = ExecutionStatus.RUNNING

            sorted_task_ids = self._topological_sort(workflow)

            failed_task_ids: List[str] = []

            for task_id in sorted_task_ids:
                task_def = self._get_task_by_id(workflow, task_id)
                if not task_def:
                    continue

                task_exec = TaskExecution(task_id=task_id)
                execution.task_executions.append(task_exec)

                try:
                    result = await self._execute_task(task_def, context or {}, workflow)
                    task_exec.status = ExecutionStatus.COMPLETED
                    task_exec.output = result
                    self.circuit_breaker.record_success()

                except Exception as e:
                    task_exec.status = ExecutionStatus.FAILED
                    task_exec.error = ErrorInfo(
                        error_type=type(e).__name__,
                        message=str(e),
                        stack_trace=""
                    )
                    logger.error(f"Task {task_id} failed: {e}")
                    failed_task_ids.append(task_id)

                    if not task_def.continue_on_failure:
                        raise

            execution.status = ExecutionStatus.COMPLETED
            logger.info(f"Workflow {workflow.workflow_id} completed successfully")

        except Exception as e:
            execution.status = ExecutionStatus.FAILED
            execution.error = ErrorInfo(
                error_type=type(e).__name__,
                message=str(e),
                stack_trace=""
            )
            logger.error(f"Workflow {workflow.workflow_id} failed: {e}")
            self.circuit_breaker.record_failure()

            self._record_failure_case(
                task_id=",".join(failed_task_ids) if failed_task_ids else "workflow_level",
                workflow_id=workflow.workflow_id,
                error_type=type(e).__name__,
                error_message=str(e)
            )

        execution.end_time = datetime.now().isoformat()
        if execution.start_time and execution.end_time:
            start = datetime.fromisoformat(execution.start_time)
            end = datetime.fromisoformat(execution.end_time)
            execution.duration_seconds = (end - start).total_seconds()

        _publish_workflow_event("workflow.completed" if execution.status == ExecutionStatus.COMPLETED else "workflow.failed", {
            "workflow_id": workflow.workflow_id,
            "execution_id": execution.execution_id,
            "status": execution.status.value,
            "duration_seconds": execution.duration_seconds,
        })

        execution.failure_count = len(failed_task_ids)
        execution.failure_cases = failed_task_ids

        return execution

    async def _execute_task(
        self,
        task: TaskDefinition,
        context: Dict,
        workflow: Workflow
    ) -> Dict[str, Any]:
        retry_config = task.retry if isinstance(task.retry, RetryConfig) else RetryConfig(**task.retry)

        for attempt in range(retry_config.max_attempts):
            try:
                logger.info(f"Executing task {task.task_id}, attempt {attempt + 1}/{retry_config.max_attempts}")

                result = await self._run_task_logic(task, context)

                return result

            except Exception as e:
                error_type = type(e).__name__
                if error_type not in retry_config.retryable_errors:
                    logger.warning(f"Task {task.task_id} failed with non-retryable error: {error_type}")
                    raise

                if attempt < retry_config.max_attempts - 1:
                    wait_time = retry_config.retry_interval * (2 ** attempt) if retry_config.exponential_backoff else retry_config.retry_interval
                    wait_time = min(wait_time, retry_config.max_interval)
                    logger.warning(f"Task {task.task_id} failed, retrying in {wait_time}s: {e}")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Task {task.task_id} failed after {retry_config.max_attempts} attempts")
                    raise

    async def _run_task_logic(self, task: TaskDefinition, context: Dict) -> Dict[str, Any]:
        if task.task_id == "fetch_db":
            return await self._fetch_db_data(context)
        elif task.task_id == "update_dashboard":
            return await self._update_dashboard(context)
        elif task.task_id == "update_kanban":
            return await self._update_kanban(context)
        elif task.task_id == "generate_okr_report":
            return await self._generate_okr_report(context)
        elif task.task_id == "generate_project_overview":
            return await self._generate_project_overview(context)
        
        await asyncio.sleep(0.1)
        return {
            "task_id": task.task_id,
            "status": "completed",
            "timestamp": datetime.now().isoformat()
        }
    
    async def _fetch_db_data(self, context: Dict) -> Dict[str, Any]:
        try:
            from project_db import db
            stats = db.get_stats()
            return {"status": "success", **stats}
        except Exception as e:
            return {"status": "error", "reason": str(e)}
    
    async def _update_dashboard(self, context: Dict) -> Dict[str, Any]:
        try:
            from project_db import db
        except Exception:
            return {"status": "skipped", "reason": "import_failed"}

        projects = db.get_all_projects()
        stats = db.get_stats()

        output_dir = _PROJECT_ROOT / "3_任务执行中枢（TAPD）" / "07_监控报告"
        output_dir.mkdir(parents=True, exist_ok=True)

        dashboard = f"""# 实时进度仪表盘 (ProjectDB)

| 更新时间 | 总进度 | 任务数 | 项目数 |
|----------|--------|--------|--------|
| {datetime.now().strftime('%Y-%m-%d %H:%M')} | **{stats['progress_pct']}%** | {stats['tasks']} | {stats['projects']} |

## 项目进度表
| ID | 名称 | 状态 | 任务 | 完成 |
|----|------|------|------|------|
"""
        for p in projects:
            dashboard += f"| {p['project_id']} | {p['project_name']} | {p['status']} | {p['total_tasks'] or 0} | {p['done_tasks'] or 0} |\n"

        dashboard += f"""
---
*最后更新: ProjectDB*
"""
        output_path = output_dir / "实时进度仪表盘.md"
        output_path.write_text(dashboard, encoding="utf-8")
        return {"status": "success", "output": str(output_path)}
    
    async def _update_kanban(self, context: Dict) -> Dict[str, Any]:
        try:
            from project_db import db
        except Exception:
            return {"status": "skipped", "reason": "import_failed"}

        output_path = _PROJECT_ROOT / "3_任务执行中枢（TAPD）" / "03_任务看板" / "Kanban.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        statuses = ['Backlog', 'Doing', 'Review', 'Done', 'Blocked']
        names = {'Backlog': 'todo', 'Doing': 'doing', 'Review': 'review', 'Done': 'done', 'Blocked': 'blocked'}
        kanban = {}
        for st in statuses:
            tasks = db.get_tasks(status=st)
            kanban[names[st]] = [{'id': t['task_id'], 'desc': t['description'], 'assignee': t['assignee'], 'priority': t['priority']} for t in tasks]

        output_path.write_text(json.dumps(kanban, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"status": "success", "output": str(output_path)}
    
    async def _generate_okr_report(self, context: Dict) -> Dict[str, Any]:
        try:
            from project_db import db
        except Exception:
            return {"status": "skipped", "reason": "import_failed"}

        okr_path = _PROJECT_ROOT / "3_任务执行中枢（TAPD）" / "07_OKR管理" / "OKR_Master.json"
        output_path = _PROJECT_ROOT / "3_任务执行中枢（TAPD）" / "07_监控报告" / f"Daily_OKR_Pulse_{date.today().strftime('%Y%m%d')}.md"

        objectives = []
        if okr_path.exists():
            objectives = json.loads(okr_path.read_text(encoding="utf-8")).get("objectives", [])

        db_okrs = {o["id"]: o for o in db.get_all_okrs()}
        all_tasks = db.get_tasks()

        for obj in objectives:
            db_o = db_okrs.get(obj["Objective_ID"], {})
            obj["_db_confidence"] = db_o.get("confidence", 0)

        alerts = []
        for obj in objectives:
            for kr in obj.get("Key_Results", []):
                lag = 50 - kr.get("Progress", 0)
                if lag > 20:
                    alerts.append({"kr": kr, "lag": lag, "obj_id": obj["Objective_ID"]})

        now = datetime.now()
        lines = [
            "# 每日 OKR Pulse 报告",
            "",
            f"> 报告日期: {now.strftime('%Y-%m-%d')}  |  时间: {now.strftime('%H:%M')}  |  ProjectDB",
            "",
            "---",
            "## OKR 状态概览",
            "",
            "| 目标ID | 描述 | 负责人 | DB信心 | 状态 |",
            "|--------|------|--------|--------|------|",
        ]
        for obj in objectives:
            conf = obj["_db_confidence"]
            icon = "🟢" if conf >= 70 else "🟡" if conf >= 40 else "🔴"
            lines.append(f"| {obj['Objective_ID']} | {obj['Description'][:30]} | {obj['Owner_Agent']} | {icon} {conf}% | {obj['Status']} |")

        lines.extend(["", "---", "## 预警", ""])
        if alerts:
            lines.extend(["| KR ID | 描述 | 滞后 |", "|-------|------|------|"])
            for a in alerts:
                lines.append(f"| {a['kr']['KR_ID']} | {a['kr']['Description']} | {a['lag']}% |")
        else:
            lines.append(" 无滞后")

        lines.extend(["", "---", "## 任务看板", ""])
        doing = [t for t in all_tasks if t["kanban_status"] == "Doing"]
        backlog = [t for t in all_tasks if t["kanban_status"] == "Backlog"]
        done_tasks = [t for t in all_tasks if t["kanban_status"] == "Done"]

        if backlog:
            lines.extend(["### 待办", "", "| 任务ID | 标题 | 执行者 | 优先级 |", "|--------|------|--------|--------|"])
            for t in backlog:
                lines.append(f"| {t['task_id']} | {t['description'][:30]} | {t['assignee']} | {t['priority']} |")
            lines.append("")

        if doing:
            lines.extend(["### 进行中", "", "| 任务ID | 标题 | 执行者 |", "|--------|------|--------|"])
            for t in doing:
                lines.append(f"| {t['task_id']} | {t['description'][:30]} | {t['assignee']} |")
            lines.append("")

        lines.extend(["---", "", "## 今日完成", ""])
        if done_tasks:
            for t in done_tasks:
                lines.append(f"- [{t['priority']}] {t['description']} ({t['assignee']})")
        else:
            lines.append("- 无")
        lines.append("")

        risk_lines = []
        for obj in objectives:
            if obj["_db_confidence"] < 50:
                risk_lines.append(f"| RISK-{obj['Objective_ID'][-3:]} | {obj['Description'][:25]} ({obj['_db_confidence']}%) | 高 | 追加资源 | {obj['Owner_Agent']} |")

        lines.extend(["---", "## 风险", ""])
        if risk_lines:
            lines.extend(["| ID | 描述 | 影响 | 应对 | 责任人 |", "|----|------|------|------|--------|"])
            lines.extend(risk_lines)
        else:
            lines.append(" 无严重风险")
        lines.append("")
        lines.extend(["---", f"*下次: {(date.today() + timedelta(days=1)).strftime('%Y-%m-%d')} 20:00*"])

        report = "\n".join(lines)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report, encoding="utf-8")
        return {"status": "success", "output": str(output_path)}
    
    async def _generate_project_overview(self, context: Dict) -> Dict[str, Any]:
        try:
            from project_db import db
        except Exception:
            return {"status": "skipped", "reason": "import_failed"}

        output_dir = _PROJECT_ROOT / "3_任务执行中枢（TAPD）" / "07_监控报告"
        output_dir.mkdir(parents=True, exist_ok=True)

        db_projects = db.get_all_projects()
        projects = []
        for p in db_projects:
            total = p["total_tasks"] or 0
            done = p["done_tasks"] or 0
            pct = round(done / total * 100, 1) if total > 0 else 0
            projects.append({
                "id": p["project_id"], "name": p["project_name"],
                "status": p["status"], "pct": pct,
                "owner": p["owner_agent"], "tasks": f"{done}/{total}",
                "okr": p["linked_okr_id"],
            })

        if not projects:
            return {"status": "skipped", "reason": "no_projects"}

        active = [p for p in projects if p["status"] in ("开发中", "测试中")]
        avg_pct = round(sum(p["pct"] for p in projects) / len(projects), 1)

        now = datetime.now()
        lines = [
            f"# 项目进度总览",
            f"",
            f"> 更新时间: {now.strftime('%Y-%m-%d %H:%M')}  |  ProjectDB",
            f"> {len(projects)} 个项目  |  平均 {avg_pct}%  |  活跃: {len(active)}",
            "",
            "---",
            "",
            "| # | 项目 | 状态 | 进度 | 任务 | 负责人 | OKR |",
            "|---|------|------|------|------|--------|------|",
        ]

        for i, p in enumerate(projects, 1):
            pct = int(p["pct"])
            bar = "#" * (pct // 10) + "-" * (10 - pct // 10)
            m = "=" if pct >= 70 else "~" if pct >= 30 else "." if pct > 0 else " "
            lines.append(f"| {i} | {p['name']} | {p['status']} | {m} {bar} {pct}% | {p['tasks']} | {p['owner']} | {p['okr']} |")

        lines.extend(["", "---", "", f"*下次: {(date.today() + timedelta(days=1)).strftime('%Y-%m-%d')} 20:00*"])

        report = "\n".join(lines)
        output_path = output_dir / f"项目总览_{date.today().strftime('%Y%m%d')}.md"
        output_path.write_text(report, encoding="utf-8")

        return {"status": "success", "output": str(output_path), "projects": len(projects), "avg_pct": avg_pct}

    def _record_failure_case(self, task_id: str, workflow_id: str, error_type: str, error_message: str) -> None:
        db_path = _PROJECT_ROOT / "tapd_temp" / "07_数据库" / "tapd_v3.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            conn = sqlite3.connect(str(db_path))
            try:
                conn.execute(
                    "CREATE TABLE IF NOT EXISTS failure_cases ("
                    "id INTEGER PRIMARY KEY, "
                    "task_id TEXT, "
                    "workflow_id TEXT, "
                    "error_type TEXT, "
                    "error_message TEXT, "
                    "occurred_at TEXT, "
                    "resolved INTEGER DEFAULT 0)"
                )
                conn.execute(
                    "INSERT INTO failure_cases (task_id, workflow_id, error_type, error_message, occurred_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (task_id, workflow_id, error_type, error_message, datetime.now().isoformat())
                )
                conn.commit()
            finally:
                conn.close()
        except Exception as db_err:
            logger.error(f"Failed to record failure case to tapd_v3.db: {db_err}")

    def _topological_sort(self, workflow: Workflow) -> List[str]:
        in_degree: Dict[str, int] = {t.task_id: 0 for t in workflow.tasks}
        adjacency: Dict[str, List[str]] = {t.task_id: [] for t in workflow.tasks}

        for task_id, deps in workflow.dependencies.items():
            for dep in deps:
                if dep in adjacency and task_id in in_degree:
                    adjacency[dep].append(task_id)
                    in_degree[task_id] += 1

        queue = [tid for tid, degree in in_degree.items() if degree == 0]
        result = []

        while queue:
            current = queue.pop(0)
            result.append(current)

            for neighbor in adjacency.get(current, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(result) != len(workflow.tasks):
            logger.warning("Cycle detected in workflow dependencies")

        return result

    def _get_task_by_id(self, workflow: Workflow, task_id: str) -> Optional[TaskDefinition]:
        for task in workflow.tasks:
            if task.task_id == task_id:
                return task
        return None

    def get_execution(self, execution_id: str) -> Optional[Execution]:
        return self._executions.get(execution_id)

    def list_executions(self, workflow_id: Optional[str] = None) -> List[Execution]:
        if workflow_id:
            return [e for e in self._executions.values() if e.workflow_id == workflow_id]
        return list(self._executions.values())

    def get_circuit_breaker_status(self) -> Dict:
        return {
            "state": self.circuit_breaker.state,
            "failure_count": self.circuit_breaker.failure_count,
            "success_count": self.circuit_breaker.success_count,
            "is_open": self.circuit_breaker.is_open()
        }
