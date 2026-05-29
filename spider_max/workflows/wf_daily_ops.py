#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WF-DAILY-OPS: 无人值守每日运维报告生成引擎
每日自动检查系统状态(磁盘/内存/进程/项目)并生成 Markdown 运维报告
"""

import asyncio
import logging
import shutil
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

try:
    from ..models import Workflow, TaskDefinition, TriggerConfig, ScheduleConfig, TriggerType
except ImportError:
    from models import Workflow, TaskDefinition, TriggerConfig, ScheduleConfig, TriggerType  # type: ignore[no-redef]

try:
    import psutil
except ImportError:
    psutil = None

_SCRIPT_DIR = Path(__file__).resolve().parent.parent.parent.parent

try:
    sys.path.insert(0, str(_SCRIPT_DIR))
    from project_db import db
except ImportError:
    db = None

logger = logging.getLogger(__name__)

REPORT_PATH = Path(
    _SCRIPT_DIR / "3_任务执行中枢（TAPD）" / "05_文档集" / "04_项目报告" / "每日运维报告.md"
)


class DailyOpsWorkflow:
    workflow_id = "WF-DAILY-OPS"
    name = "无人值守每日运维报告生成"
    description = "每日自动检查系统状态(磁盘/内存/进程/项目)并生成Markdown运维报告"

    @staticmethod
    def get_definition() -> Workflow:
        tasks = [
            TaskDefinition(
                task_id="check_system",
                name="系统状态检查",
                description="检查系统基本状态",
                agent_id="system-manager",
            ),
            TaskDefinition(
                task_id="check_disk",
                name="磁盘空间检查",
                description="检查磁盘空间使用情况",
                agent_id="tech-expert",
                dependencies=["check_system"],
            ),
            TaskDefinition(
                task_id="check_memory",
                name="内存使用检查",
                description="检查内存使用情况",
                agent_id="tech-expert",
                dependencies=["check_system"],
            ),
            TaskDefinition(
                task_id="check_processes",
                name="运行进程检查",
                description="检查当前运行进程数量",
                agent_id="system-manager",
                dependencies=["check_system"],
            ),
            TaskDefinition(
                task_id="check_projects",
                name="项目状态检查",
                description="读取 project_db 项目统计数据",
                agent_id="project-manager",
                dependencies=["check_system", "check_disk", "check_memory", "check_processes"],
            ),
            TaskDefinition(
                task_id="generate_report",
                name="生成运维报告",
                description="汇总所有检查结果生成每日运维报告",
                agent_id="system-manager",
                dependencies=[
                    "check_system", "check_disk", "check_memory",
                    "check_processes", "check_projects",
                ],
            ),
        ]
        return Workflow(
            workflow_id=DailyOpsWorkflow.workflow_id,
            name=DailyOpsWorkflow.name,
            description=DailyOpsWorkflow.description,
            trigger=TriggerConfig(
                trigger_type=TriggerType.CRON,
                cron_expression="0 22 * * *"
            ),
            schedule=ScheduleConfig(enabled=True, timezone="Asia/Shanghai"),
            tasks=tasks,
            dependencies={
                "check_system": [],
                "check_disk": ["check_system"],
                "check_memory": ["check_system"],
                "check_processes": ["check_system"],
                "check_projects": ["check_system", "check_disk", "check_memory", "check_processes"],
                "generate_report": [
                    "check_system", "check_disk", "check_memory",
                    "check_processes", "check_projects",
                ],
            },
            assigned_agents=["system-manager", "tech-expert", "project-manager"],
        )

    @staticmethod
    async def execute(executor, context: Dict[str, Any]) -> Dict[str, Any]:
        now = datetime.now()
        report_time = now.strftime("%Y-%m-%d %H:%M:%S")
        date_str = now.strftime("%Y-%m-%d")

        # ---- 系统状态 ----
        hostname = os.environ.get("COMPUTERNAME", os.uname().nodename if hasattr(os, "uname") else "unknown")
        system_status = "正常"
        issues = []

        # ---- 磁盘检查 ----
        disk_result = {}
        disk_total_gb = 0
        disk_used_gb = 0
        disk_free_gb = 0
        disk_pct = 0
        disk_status = "正常"
        try:
            usage = shutil.disk_usage("E:\\")
            disk_total_gb = round(usage.total / (1024 ** 3), 1)
            disk_used_gb = round(usage.used / (1024 ** 3), 1)
            disk_free_gb = round(usage.free / (1024 ** 3), 1)
            disk_pct = round(usage.used / usage.total * 100, 1) if usage.total > 0 else 0
            disk_result = {
                "total_gb": disk_total_gb,
                "used_gb": disk_used_gb,
                "free_gb": disk_free_gb,
                "percent_used": disk_pct,
            }
            if disk_pct > 90:
                disk_status = "⚠️ 预警"
                issues.append(f"E盘磁盘使用率已达 {disk_pct}%，建议清理")
            elif disk_pct > 80:
                disk_status = "需关注"
            logger.info(f"磁盘检查完成: E盘 总计{disk_total_gb}GB, 已用{disk_used_gb}GB({disk_pct}%)")
        except Exception as e:
            disk_result = {"error": str(e)}
            disk_status = "检查失败"
            issues.append(f"磁盘检查失败: {e}")
            logger.warning(f"磁盘检查失败: {e}")

        # ---- 内存检查 ----
        mem_result = {}
        mem_total_gb = 0
        mem_used_gb = 0
        mem_free_gb = 0
        mem_pct = 0
        mem_status = "正常"
        try:
            if psutil:
                vmem = psutil.virtual_memory()
                mem_total_gb = round(vmem.total / (1024 ** 3), 1)
                mem_available_gb = round(vmem.available / (1024 ** 3), 1)
                mem_used_gb = round(vmem.used / (1024 ** 3), 1)
                mem_free_gb = mem_available_gb
                mem_pct = vmem.percent
                mem_result = {
                    "total_gb": mem_total_gb,
                    "used_gb": mem_used_gb,
                    "available_gb": mem_available_gb,
                    "percent_used": mem_pct,
                }
                if mem_pct > 90:
                    mem_status = "⚠️ 预警"
                    issues.append(f"内存使用率达 {mem_pct}%，建议释放内存")
                elif mem_pct > 80:
                    mem_status = "需关注"
                logger.info(f"内存检查完成: 总计{mem_total_gb}GB, 已用{mem_used_gb}GB({mem_pct}%)")
            else:
                mem_result = {"error": "psutil 模块未安装"}
                mem_status = "无法检查"
                logger.warning("psutil 未安装，无法检查内存")
        except Exception as e:
            mem_result = {"error": str(e)}
            mem_status = "检查失败"
            issues.append(f"内存检查失败: {e}")
            logger.warning(f"内存检查失败: {e}")

        # ---- 进程检查 ----
        process_count = 0
        process_status = "正常"
        try:
            if psutil:
                pids = psutil.pids()
                process_count = len(pids)
                process_status = "正常" if process_count < 500 else "需关注"
                logger.info(f"进程检查完成: 当前运行 {process_count} 个进程")
            else:
                process_status = "无法检查"
                logger.warning("psutil 未安装，无法检查进程")
        except Exception as e:
            process_status = "检查失败"
            issues.append(f"进程检查失败: {e}")
            logger.warning(f"进程检查失败: {e}")

        # ---- 项目统计 ----
        project_stats = {}
        project_status = "正常"
        try:
            if db:
                stats = db.get_stats()
                projects = db.get_all_projects()
                project_stats = stats
                project_list = []
                for p in projects:
                    p_total = p.get("total_tasks", 0) or 0
                    p_done = p.get("done_tasks", 0) or 0
                    p_pct = round(p_done / p_total * 100, 1) if p_total > 0 else 0
                    project_list.append({
                        "project_id": p.get("project_id", ""),
                        "project_name": p.get("project_name", ""),
                        "status": p.get("status", ""),
                        "total_tasks": p_total,
                        "done_tasks": p_done,
                        "progress_pct": p_pct,
                    })
                project_stats["project_list"] = project_list
                logger.info(f"项目统计完成: {stats.get('projects', 0)} 个项目, {stats.get('tasks', 0)} 个任务")
            else:
                project_stats = {"error": "project_db 模块不可用"}
                project_status = "无法检查"
                logger.warning("project_db 不可用")
        except Exception as e:
            project_stats = {"error": str(e)}
            project_status = "检查失败"
            issues.append(f"项目统计失败: {e}")
            logger.warning(f"项目统计失败: {e}")

        # ---- 生成报告 ----
        if issues:
            system_status = "需关注"

        report = _build_report(
            report_time=report_time,
            hostname=hostname,
            date_str=date_str,
            system_status=system_status,
            disk_total_gb=disk_total_gb, disk_used_gb=disk_used_gb,
            disk_free_gb=disk_free_gb, disk_pct=disk_pct, disk_status=disk_status,
            mem_total_gb=mem_total_gb, mem_used_gb=mem_used_gb,
            mem_free_gb=mem_free_gb, mem_pct=mem_pct, mem_status=mem_status,
            process_count=process_count, process_status=process_status,
            project_stats=project_stats, project_status=project_status,
            issues=issues,
        )

        try:
            REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
            REPORT_PATH.write_text(report, encoding="utf-8")
            logger.info(f"每日运维报告已生成: {REPORT_PATH}")
        except Exception as e:
            logger.error(f"运维报告写入失败: {e}")
            issues.append(f"报告写入失败: {e}")

        # ── 附加：每日生命周期扫描（仅报告） ──
        lifecycle_result = _run_lifecycle_scan()

        return {
            "execution_id": context.get("execution_id", ""),
            "status": "completed" if not issues else "completed_with_issues",
            "report_path": str(REPORT_PATH),
            "disk": disk_result,
            "memory": mem_result,
            "process_count": process_count,
            "project_stats": project_stats,
            "issues": issues,
            "lifecycle_scan": lifecycle_result,
        }


def _build_report(
    report_time: str,
    hostname: str,
    date_str: str,
    system_status: str,
    disk_total_gb: float, disk_used_gb: float, disk_free_gb: float,
    disk_pct: float, disk_status: str,
    mem_total_gb: float, mem_used_gb: float, mem_free_gb: float,
    mem_pct: float, mem_status: str,
    process_count: int, process_status: str,
    project_stats: Dict, project_status: str,
    issues: list,
) -> str:
    risk_level = "⚠️ 高" if len(issues) > 2 else ("需关注" if issues else "低")
    suggestions = []

    if disk_pct > 80:
        suggestions.append("磁盘使用率超过80%，建议清理不必要文件或扩展存储")
    if mem_pct > 80:
        suggestions.append("内存使用率超过80%，建议检查内存占用较大的进程")
    if process_count > 500:
        suggestions.append("运行进程数较多，建议检查是否有僵尸进程")
    if not issues:
        suggestions.append("系统运行状态良好，无需紧急处理")

    # build project table rows
    project_rows = ""
    project_list = project_stats.get("project_list", [])
    if project_list:
        for p in project_list:
            pct = p.get("progress_pct", 0)
            status_icon = "✅" if pct >= 100 else ("🔄" if pct > 0 else "⬜")
            project_rows += (
                f"| {p.get('project_id', '')} | {p.get('project_name', '')} "
                f"| {status_icon} {p.get('status', '')} "
                f"| {p.get('done_tasks', 0)}/{p.get('total_tasks', 0)} ({pct}%) |\n"
            )
    else:
        project_rows = "| - | 暂无项目数据 | - | - |\n"

    return f'''# 每日运维报告

**生成时间**: {report_time}
**执行人**: 系统经理
**主机名**: {hostname}

## 1. 系统状态检查

### 1.1 系统总体状态
- **状态**: {system_status}
- **风险等级**: {risk_level}
- **主机**: {hostname}

### 1.2 磁盘空间检查 (E:)
- **总容量**: {disk_total_gb} GB
- **已使用**: {disk_used_gb} GB ({disk_pct}%)
- **可用空间**: {disk_free_gb} GB
- **状态**: {disk_status}

### 1.3 内存使用检查
- **总内存**: {mem_total_gb} GB
- **已使用**: {mem_used_gb} GB ({mem_pct}%)
- **可用内存**: {mem_free_gb} GB
- **状态**: {mem_status}

### 1.4 进程状态检查
- **运行进程数**: {process_count} 个
- **状态**: {process_status}

## 2. 项目状态总览

- **状态**: {project_status}
- **项目总数**: {project_stats.get("projects", "N/A") if isinstance(project_stats, dict) else "N/A"}
- **任务总数**: {project_stats.get("tasks", "N/A") if isinstance(project_stats, dict) else "N/A"}
- **已完成**: {project_stats.get("done", "N/A") if isinstance(project_stats, dict) else "N/A"}
- **进行中**: {project_stats.get("doing", "N/A") if isinstance(project_stats, dict) else "N/A"}
- **活跃项目**: {project_stats.get("active", "N/A") if isinstance(project_stats, dict) else "N/A"}
- **整体进度**: {project_stats.get("progress_pct", "N/A") if isinstance(project_stats, dict) else "N/A"}%

### 2.1 项目详情

| 项目ID | 项目名称 | 状态 | 进度 |
|--------|----------|------|------|
{project_rows}

## 3. 发现的问题

{chr(10).join(f"- **问题{chr(96)}{i+1}{chr(96)}**: {issue}" for i, issue in enumerate(issues)) if issues else "- **无**: 未发现明显问题"}

## 4. 运维建议

### 4.1 立即执行
{"- 无紧急任务需要立即执行" if risk_level == "低" else "- 请根据上述问题列表立即处理"}

### 4.2 短期计划
{chr(10).join(f"{i+1}. **建议**: {s}" for i, s in enumerate(suggestions)) if suggestions else "1. 保持当前运维策略"}

## 5. 总结

本次每日运维检查显示系统运行状态{system_status}，风险等级{risk_level}。{f'发现 {len(issues)} 个潜在问题需要关注。' if issues else '未发现明显问题。'}{'建议按照上述运维建议进行处理，以保障系统稳定运行。' if issues else '系统各项指标均在正常范围内，建议保持当前运维节奏。'}

---

**报告生成完成**
'''


def _run_lifecycle_scan() -> dict:
    """
    每日附加生命周期扫描（仅报告模式）。
    调用 data_lifecycle_engine --scan 生成归档/冗余报告。
    """
    engine_script = _SCRIPT_DIR / "scripts" / "data_lifecycle_engine.py"
    if not engine_script.exists():
        logger.warning("[LIFECYCLE] engine not found, skip")
        return {"status": "skipped", "reason": "engine_not_found"}

    try:
        proc = subprocess.run(
            [sys.executable, str(engine_script), "--scan"],
            capture_output=True, text=True, timeout=300,
            cwd=str(_SCRIPT_DIR),
            env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"},
        )
        stdout = proc.stdout.strip()
        stderr = proc.stderr.strip()
        # 提取报告路径
        report_path = ""
        for line in stdout.splitlines():
            if "REPORT" in line or "report" in line.lower():
                report_path = line.strip()
                break
        logger.info(f"[LIFECYCLE] scan done: rc={proc.returncode}")
        return {
            "status": "completed" if proc.returncode == 0 else "failed",
            "returncode": proc.returncode,
            "report_hint": report_path,
        }
    except subprocess.TimeoutExpired:
        logger.warning("[LIFECYCLE] scan timeout")
        return {"status": "timeout"}
    except Exception as e:
        logger.error(f"[LIFECYCLE] scan error: {e}")
        return {"status": "error", "error": str(e)}

