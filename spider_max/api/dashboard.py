"""Spider Max 系统仪表板"""
import sqlite3
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, Optional

router = APIRouter()

TAPD_ROOT = Path(__file__).resolve().parents[2] / "3_任务执行中枢（TAPD）"
DB_PATH = TAPD_ROOT / "07_数据库" / "tapd.db"


class DashboardSummary(BaseModel):
    total_projects: int = 0
    total_tasks: int = 0
    completed_tasks: int = 0
    in_progress_tasks: int = 0
    blocked_tasks: int = 0
    p0_pending: int = 0
    overdue_tasks: int = 0
    total_agents: int = 0
    completion_rate: float = 0.0
    timestamp: str = ""


class DashboardResponse(BaseModel):
    summary: DashboardSummary
    by_status: Dict[str, int]
    by_priority: Dict[str, int]
    health_dist: Dict[str, int]


def _fetch_summary(conn) -> DashboardSummary:
    total = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    done = conn.execute("SELECT COUNT(*) FROM tasks WHERE status='Done'").fetchone()[0]
    ip = conn.execute("SELECT COUNT(*) FROM tasks WHERE status IN ('In Progress','Review')").fetchone()[0]
    blk = conn.execute("SELECT COUNT(*) FROM tasks WHERE status='Blocked'").fetchone()[0]
    p0 = conn.execute("SELECT COUNT(*) FROM tasks WHERE priority='P0' AND status NOT IN ('Done','Cancelled')").fetchone()[0]
    overdue = conn.execute("SELECT COUNT(*) FROM tasks WHERE deadline < datetime('now') AND status NOT IN ('Done','Cancelled')").fetchone()[0]
    projects = conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
    agents = conn.execute("SELECT COUNT(*) FROM agents").fetchone()[0]
    rate = round(done / max(total, 1) * 100, 1)
    return DashboardSummary(
        total_projects=projects, total_tasks=total, completed_tasks=done,
        in_progress_tasks=ip, blocked_tasks=blk, p0_pending=p0,
        overdue_tasks=overdue, total_agents=agents,
        completion_rate=rate, timestamp=datetime.now().isoformat(),
    )


@router.get("/dashboard", response_model=DashboardResponse)
async def dashboard():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    summary = _fetch_summary(conn)
    by_status = {}
    for r in conn.execute("SELECT status, COUNT(*) as cnt FROM tasks GROUP BY status"):
        by_status[r["status"]] = r["cnt"]
    by_priority = {}
    for r in conn.execute("SELECT priority, COUNT(*) as cnt FROM tasks GROUP BY priority"):
        by_priority[r["priority"]] = r["cnt"]
    health_dist = {}
    for r in conn.execute("SELECT health_status, COUNT(*) as cnt FROM projects GROUP BY health_status"):
        health_dist[r["health_status"]] = r["cnt"]
    conn.close()
    return DashboardResponse(summary=summary, by_status=by_status, by_priority=by_priority, health_dist=health_dist)
