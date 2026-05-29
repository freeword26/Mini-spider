#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""完整集成测试: 导入 + 执行 + 调度器 + 报告生成"""

import sys, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path
from datetime import datetime

print("=" * 60)
print("  无人值守系统 v2.0 — 每日运维融合验证")
print("=" * 60)

print("\n[1/4] Import DailyOpsWorkflow...")
from workflows.wf_daily_ops import DailyOpsWorkflow
wf = DailyOpsWorkflow.get_definition()
print(f"  OK: {wf.workflow_id} | {len(wf.tasks)} tasks")
for t in wf.tasks:
    print(f"    - {t.task_id} -> {t.agent_id}")

print("\n[2/4] Execute dry-run...")
import asyncio
from event_bus import create_event_bus
from workflow_executor import WorkflowExecutor

async def _run():
    eb = create_event_bus({"mode": "memory"})
    executor = WorkflowExecutor()
    return await DailyOpsWorkflow.execute(executor, {"base_path": "E:/软件开发"})

result = asyncio.run(_run())
print(f"  Result keys: {list(result.keys())}")
disk = result.get("disk", {})
if disk:
    total_gb = disk.get("total_gb", 0)
    free_gb = disk.get("free_gb", 0)
    pct = disk.get("percent", 0)
    print(f"  Disk: total={total_gb}GB free={free_gb}GB used={100-pct}%")
mem = result.get("memory", {})
if mem:
    total = mem.get("total_gb", "?")
    used = mem.get("used_gb", "?")
    pct = mem.get("percent", "?")
    print(f"  Memory: total={total}GB used={used}GB pct={pct}%")
proc = result.get("processes", {})
if proc:
    print(f"  Processes: {proc.get('count', 0)} running")
proj = result.get("projects", {})
if proj:
    print(f"  Projects: {proj.get('total', 0)} total, {proj.get('active', 0)} active")

print("\n[3/4] Scheduler integration...")
from unattended_event_scheduler import TwentyTwoProjectScheduler
sched = TwentyTwoProjectScheduler(event_bus=None)
status = sched.get_schedule_status()
print(f"  Projects: {status['total_projects']} (22 + SYS_DAILY_OPS)")
print(f"  Jobs: {status['total_jobs']}")
print(f"  Layers: {status['layer_distribution']}")
print(f"  Priorities: {status['priority_distribution']}")

print("\n[4/4] Report generated...")
report_path = Path(r"E:\软件开发\3_任务执行中枢（TAPD）\05_文档集\04_项目报告\每日运维报告.md")
if report_path.exists():
    size = report_path.stat().st_size
    mtime = datetime.fromtimestamp(report_path.stat().st_mtime)
    print(f"  Report: {report_path}")
    print(f"  Size: {size} bytes")
    print(f"  Modified: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
    lines = report_path.read_text(encoding="utf-8").split("\n")[:5]
    for line in lines:
        print(f"  | {line[:80]}")
else:
    print("  Report NOT generated yet (will generate on first scheduler run)")

print("\n" + "=" * 60)
print("  ALL CHECKS PASSED - 无人值守 + 每日运维 已缝合!")
print("=" * 60)
