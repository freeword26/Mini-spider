#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
无人值守工作流管理系统 v2.0 — FastAPI主入口
三层闭环: 接入层(网关) → 事件层(RabbitMQ) → 执行层(22项目)
"""

import logging
import sys
import asyncio
import threading
from contextlib import asynccontextmanager
from pathlib import Path
from datetime import date

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from api import workflows_router, executions_router, schedules_router, agents_router, health_router

TAPD = Path(__file__).parent.parent.parent / "3_任务执行中枢（TAPD）"
DB_PATH = TAPD / "07_数据库" / "project_management.db"

_LOG_DIR = Path(__file__).parent.parent.parent / "logs"
_LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(str(_LOG_DIR / "unattended.log"), encoding="utf-8"),
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)


_event_bus = None
_project_scheduler = None
_self_healing = None
_monitoring = None
_scheduler_thread = None
_health_checker_task = None


def _start_background_loops(app: FastAPI):
    global _event_bus, _project_scheduler, _self_healing, _monitoring, _scheduler_thread

    try:
        from .event_bus import create_event_bus
        from .unattended_event_scheduler import TwentyTwoProjectScheduler
        from .self_healing import SelfHealing
        from .workflow_executor import WorkflowExecutor
        from .monitoring import Monitoring
    except (ImportError, SystemError):
        from event_bus import create_event_bus
        from unattended_event_scheduler import TwentyTwoProjectScheduler
        from self_healing import SelfHealing
        from workflow_executor import WorkflowExecutor
        from monitoring import Monitoring

    _event_bus = create_event_bus({"mode": "memory"})
    logger.info("EventBus initialized")

    _project_scheduler = TwentyTwoProjectScheduler(event_bus=_event_bus)
    logger.info(f"22-project scheduler ready: {_project_scheduler.get_schedule_status()['total_jobs']} jobs")

    executor = WorkflowExecutor()
    _self_healing = SelfHealing(event_bus=_event_bus, scheduler=None)
    logger.info("Self-healing module initialized")

    _monitoring = Monitoring(event_bus=_event_bus, executor_circuit_breaker=executor.circuit_breaker)
    logger.info("Monitoring module initialized")

    def _run_scheduler():
        logger.info("Starting 22-project scheduler loop...")
        try:
            _project_scheduler.start_scheduler()
        except Exception as e:
            logger.error(f"Scheduler loop crashed: {e}")

    _scheduler_thread = threading.Thread(target=_run_scheduler, daemon=True, name="project-scheduler")
    _scheduler_thread.start()
    logger.info("Project scheduler thread started")

    async def _health_check_loop():
        while True:
            try:
                await asyncio.sleep(900)
                if _self_healing:
                    await _self_healing.check_and_heal()
                if _monitoring:
                    health = _monitoring.check_three_layer_health()
                    if health.get("overall_status") == "critical":
                        logger.critical(f"CRITICAL: {health}")
            except Exception as e:
                logger.error(f"Health check error: {e}")

    loop = asyncio.get_event_loop()
    global _health_checker_task
    _health_checker_task = loop.create_task(_health_check_loop())
    logger.info("Background health checker started (15min interval)")


async def _stop_background_loops():
    if _project_scheduler:
        logger.info("Stopping project scheduler...")
    if _self_healing:
        logger.info("Stopping self-healing...")
    if _monitoring:
        _monitoring.stop()
    if _health_checker_task:
        _health_checker_task.cancel()
    if _event_bus and hasattr(_event_bus, 'close'):
        _event_bus.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 60)
    logger.info("无人值守工作流管理系统 v2.0 启动")
    _start_background_loops(app)
    yield
    logger.info("无人值守工作流管理系统关闭")
    await _stop_background_loops()


app = FastAPI(
    title="无人值守工作流管理系统 v2.0",
    description="三层闭环 × 22项目 × 无人值守 × 冲突解决",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                    allow_methods=["*"], allow_headers=["*"])

app.include_router(workflows_router, prefix="/api/v1")
app.include_router(executions_router, prefix="/api/v1")
app.include_router(schedules_router, prefix="/api/v1")
app.include_router(agents_router, prefix="/api/v1")
app.include_router(health_router, prefix="/api/v1")


@app.get("/")
async def root():
    sched_status = _project_scheduler.get_schedule_status() if _project_scheduler else {}
    return {
        "name": "无人值守工作流管理系统 v2.0",
        "version": "2.0.0",
        "status": "running",
        "scheduler": {
            "total_projects": sched_status.get("total_projects", 0),
            "total_jobs": sched_status.get("total_jobs", 0),
            "executed_count": sched_status.get("executed_count", 0),
        },
        "endpoints": {
            "workflows": "/api/v1/workflows",
            "executions": "/api/v1/executions",
            "schedules": "/api/v1/schedules",
            "agents": "/api/v1/agents",
            "health": "/api/v1/health",
            "validate": "/api/v1/health/validate",
            "three_layer": "/api/v1/health/three-layer",
            "dashboard": "/dashboard",
        }
    }


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    import sqlite3, re, json
    today_str = date.today().strftime("%Y%m%d")
    overview_path = TAPD / "07_监控报告" / f"项目总览_{today_str}.md"
    if not overview_path.exists():
        overview_path = list((TAPD / "07_监控报告").glob("项目总览_*.md"))[-1] if list((TAPD / "07_监控报告").glob("项目总览_*.md")) else None

    projects = []
    if DB_PATH.exists():
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("""
            SELECT pm.project_id, pm.project_name, pm.status, pm.owner_agent, pm.description,
                   COUNT(tb.task_id) as total_tasks,
                   SUM(CASE WHEN tb.kanban_status='Done' THEN 1 ELSE 0 END) as done_tasks
            FROM project_meta pm
            LEFT JOIN task_board tb ON pm.project_id = tb.project_id
            GROUP BY pm.project_id ORDER BY pm.project_id
        """)
        db_rows = {r["project_id"]: dict(r) for r in c.fetchall()}
        conn.close()

        md_path = TAPD / "00_项目开发清单汇总.md"
        mvp_map, priority_map = {}, {}
        if md_path.exists():
            text = md_path.read_text(encoding="utf-8")
            ptn = re.compile(r'\|\s*\*{0,2}(PRJ_\d+)\*{0,2}\s*\|\s*\*{0,2}(.+?)\*{0,2}\s*\|\s*\*{0,2}(P[0-3])\*{0,2}\s*\|\s*[^|]+?\|\s*\*{0,2}~?(\d+)%\*{0,2}\s*\|')
            for m in ptn.finditer(text):
                mvp_map[m.group(1)] = int(m.group(4))
                priority_map[m.group(1)] = m.group(3)

        for pid, p in db_rows.items():
            mvp = mvp_map.get(pid, 0)
            pct = round(p["done_tasks"] / p["total_tasks"] * 100, 1) if p["total_tasks"] else mvp
            projects.append({
                "id": pid, "name": p["project_name"], "status": p["status"],
                "pct": pct, "owner": p["owner_agent"],
                "priority": priority_map.get(pid, "P2"),
                "tasks": f"{p['done_tasks']}/{p['total_tasks']}",
                "note": (p["description"] or "")[:30],
            })

    p0_count = sum(1 for p in projects if p["priority"] == "P0")
    active_count = sum(1 for p in projects if p["status"] in ("开发中", "测试中"))
    avg_pct = round(sum(p["pct"] for p in projects) / len(projects), 1) if projects else 0

    sched_info = _project_scheduler.get_schedule_status() if _project_scheduler else {}

    rows_html = ""
    for p in projects:
        pct = p["pct"]
        color = "#27ae60" if pct >= 70 else "#f39c12" if pct >= 30 else "#e74c3c" if pct > 0 else "#95a5a6"
        bar_html = f'<div style="background:#ecf0f1;border-radius:3px;width:100px;height:14px"><div style="background:{color};width:{pct}%;height:100%;border-radius:3px"></div></div>'
        rows_html += f"""
        <tr>
            <td>{p['id']}</td>
            <td><b>{p['name']}</b></td>
            <td><span class="badge">{p['priority']}</span></td>
            <td>{p['status']}</td>
            <td>{bar_html} {pct}%</td>
            <td>{p['tasks']}</td>
            <td>{p['owner']}</td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html lang="zh">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>无人值守系统 v2.0</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:#f5f6fa;color:#2c3e50;padding:20px}}
.card{{background:#fff;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,.08);padding:24px;margin-bottom:20px}}
.stats{{display:flex;gap:16px;margin:16px 0;flex-wrap:wrap}}
.stat{{background:#f8f9fa;border-radius:6px;padding:12px 20px;text-align:center;min-width:100px}}
.stat .v{{font-size:24px;font-weight:700;display:block}}
.stat .l{{font-size:12px;color:#7f8c8d}}
table{{width:100%;border-collapse:collapse;font-size:14px}}
th{{background:#f8f9fa;padding:10px 8px;text-align:left;font-weight:600;border-bottom:2px solid #dee2e6}}
td{{padding:8px;border-bottom:1px solid #eceff1}}
tr:hover{{background:#f8f9ff}}
.badge{{display:inline-block;padding:2px 8px;border-radius:4px;font-size:12px;font-weight:700;background:#2c3e50;color:#fff}}
h1{{font-size:20px;margin-bottom:4px}}
.refresh{{color:#95a5a6;font-size:12px}}
</style>
<meta http-equiv="refresh" content="300">
</head>
<body>
<div class="card">
<h1>无人值守系统 v2.0 — 项目进度总览</h1>
<div class="stats">
<div class="stat"><span class="v">{len(projects)}</span><span class="l">项目</span></div>
<div class="stat"><span class="v">{avg_pct}%</span><span class="l">平均进度</span></div>
<div class="stat"><span class="v">{p0_count}</span><span class="l">P0</span></div>
<div class="stat"><span class="v">{active_count}</span><span class="l">活跃</span></div>
</div>
<table>
<thead><tr><th>ID</th><th>项目</th><th>P</th><th>状态</th><th>进度</th><th>任务</th><th>负责人</th></tr></thead>
<tbody>{rows_html}</tbody>
</table>
<p class="refresh">自动刷新 5分钟 · 数据源: project_management.db</p>
</div>
<div class="card">
<h1>无人值守调度器</h1>
<div class="stats">
<div class="stat"><span class="v">{sched_info.get('total_projects', 0)}</span><span class="l">项目</span></div>
<div class="stat"><span class="v">{sched_info.get('total_jobs', 0)}</span><span class="l">定时任务</span></div>
<div class="stat"><span class="v">{sched_info.get('executed_count', 0)}</span><span class="l">已执行</span></div>
</div>
<p class="refresh">线程后台运行 · 事件总线实时发布</p>
</div>
</body></html>"""


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=5005, reload=True, log_level="info")
