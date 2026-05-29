# -*- coding: utf-8 -*-
"""Quick pre-flight check before starting the unattended system."""

import sys
import os

wf_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(wf_dir))
os.chdir(wf_dir)
sys.path.insert(0, wf_dir)
sys.path.insert(0, project_root)
os.environ["PYTHONIOENCODING"] = "utf-8"

print("=" * 60)
print("  无人值守系统 v2.0 — 启动前检查")
print("=" * 60)

print("\n[1/4] 检查依赖...")
required = ["fastapi", "uvicorn", "pika", "schedule", "croniter"]
for pkg in required:
    try:
        __import__(pkg)
        print(f"  [OK] {pkg}")
    except ImportError:
        print(f"  [MISSING] {pkg}")
        sys.exit(1)

print("\n[2/4] 检查数据库...")
from pathlib import Path
import sqlite3

db_path = Path(__file__).parent.parent.parent / "3_任务执行中枢（TAPD）" / "07_数据库" / "project_management.db"
if db_path.exists():
    conn = sqlite3.connect(str(db_path))
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM project_meta")
    projects = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM task_board")
    tasks = c.fetchone()[0]
    conn.close()
    print(f"  [OK] DB: {projects} projects, {tasks} tasks")
else:
    print(f"  [WARN] DB not found: {db_path}")

try:
    from project_db import db
    stats = db.get_stats()
    print(f"  [OK] ProjectDB: {stats}")
except Exception as e:
    print(f"  [ERROR] ProjectDB: {e}")
    sys.exit(1)

print("\n[3/4] 导入核心模块...")
try:
    from main import app
    print(f"  [OK] FastAPI: {app.title} v{app.version}, {len(app.routes)} routes")
except Exception as e:
    print(f"  [ERROR] main.py: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

from unattended_event_scheduler import TwentyTwoProjectScheduler
sched = TwentyTwoProjectScheduler(event_bus=None)
status = sched.get_schedule_status()
print(f"  [OK] Scheduler: {status['total_projects']} projects, {status['total_jobs']} jobs")

from unattended_validator import UnattendedValidator
v = UnattendedValidator()
r = v.validate_24_7_operation()
print(f"  [OK] Validator: {r['uptime_score']}/100")

from agents.registry import agent_registry
total = len(agent_registry.get_all_agents())
print(f"  [OK] Agents: {total} total")
for layer in ["指挥控制层", "执行协作层", "资源与环境层"]:
    agents = agent_registry.get_agents_by_layer(layer)
    print(f"         {layer}: {len(agents)}")

print("\n[4/4] 检查通过!")
print("=" * 60)
print("  启动命令:")
print("    python3.14 start_unattended.py")
print("  或双击: 启动无人值守系统.bat")
print("=" * 60)
