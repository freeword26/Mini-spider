# -*- coding: utf-8 -*-
"""调度配置API — SQLite持久化"""

from pathlib import Path
from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/schedules", tags=["schedules"])


def _get_store():
    try:
        from .store import PersistentStore
    except (ImportError, SystemError):
        from store import PersistentStore
    db_path = Path(__file__).parent.parent.parent.parent / "06_系统管理" / "11_无人值守工作流" / "api_data.db"
    return PersistentStore(str(db_path))


class ScheduleConfig(BaseModel):
    workflow_id: str
    trigger_type: str = "cron"
    cron_expression: Optional[str] = None
    interval_seconds: Optional[int] = None
    enabled: bool = True
    timezone: str = "Asia/Shanghai"

class ScheduleResponse(BaseModel):
    workflow_id: str
    name: str
    trigger_type: str
    enabled: bool
    next_fire_time: Optional[str]


@router.get("", response_model=List[ScheduleResponse])
async def list_schedules():
    store = _get_store()
    rows = store.list_schedules()
    return [ScheduleResponse(
        workflow_id=r["workflow_id"], name=r.get("name", ""),
        trigger_type=r.get("trigger_type", "cron"),
        enabled=bool(r["enabled"]), next_fire_time=None
    ) for r in rows]


@router.get("/{workflow_id}")
async def get_schedule(workflow_id: str):
    store = _get_store()
    s = store.get_schedule(workflow_id)
    if not s:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return s


@router.put("/{workflow_id}")
async def update_schedule(workflow_id: str, config: ScheduleConfig):
    store = _get_store()
    existing = store.get_schedule(workflow_id)
    data = {
        "workflow_id": workflow_id, "name": config.workflow_id,
        "trigger_type": config.trigger_type, "cron_expression": config.cron_expression,
        "interval_seconds": config.interval_seconds,
        "enabled": config.enabled, "timezone": config.timezone,
    }
    if existing:
        store.update_schedule(workflow_id, data)
    else:
        store.create_schedule(data)
    return {"message": "Schedule updated", "workflow_id": workflow_id}


@router.post("/{workflow_id}/pause")
async def pause_schedule(workflow_id: str):
    store = _get_store()
    if not store.update_schedule(workflow_id, {"enabled": False}):
        raise HTTPException(status_code=404, detail="Schedule not found")
    return {"message": "Schedule paused", "workflow_id": workflow_id}


@router.post("/{workflow_id}/resume")
async def resume_schedule(workflow_id: str):
    store = _get_store()
    if not store.update_schedule(workflow_id, {"enabled": True}):
        raise HTTPException(status_code=404, detail="Schedule not found")
    return {"message": "Schedule resumed", "workflow_id": workflow_id}
