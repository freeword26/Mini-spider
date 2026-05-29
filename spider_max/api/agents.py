# -*- coding: utf-8 -*-
"""Agent管理API — SQLite持久化"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(prefix="/agents", tags=["agents"])


def _get_store():
    try:
        from .store import PersistentStore
    except (ImportError, SystemError):
        from store import PersistentStore
    db_path = Path(__file__).parent.parent.parent.parent / "06_系统管理" / "11_无人值守工作流" / "api_data.db"
    return PersistentStore(str(db_path))


class AgentScheduleUpdate(BaseModel):
    schedule_type: str = "daily"
    time_slots: List[Dict] = []
    assigned_workflows: List[str] = []

class AgentStatus(BaseModel):
    agent_id: str
    agent_name: str
    status: str
    current_shift: Optional[str] = None
    last_heartbeat: Optional[str] = None

class AgentResponse(BaseModel):
    agent_id: str
    agent_name: str
    status: str
    assigned_workflows: List[str]
    schedule_type: str


def _parse_json_field(value, default="[]"):
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return default
    return value or default


@router.get("", response_model=List[AgentResponse])
async def list_agents():
    store = _get_store()
    rows = store.list_agents()
    return [AgentResponse(
        agent_id=r["agent_id"], agent_name=r.get("agent_name", ""),
        status=r.get("status", "active"),
        assigned_workflows=_parse_json_field(r.get("assigned_workflows")),
        schedule_type=r.get("schedule_type", "daily")
    ) for r in rows]


@router.get("/{agent_id}")
async def get_agent(agent_id: str):
    store = _get_store()
    agent = store.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.get("/{agent_id}/schedule")
async def get_agent_schedule(agent_id: str):
    store = _get_store()
    agent = store.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {
        "agent_id": agent_id,
        "agent_name": agent.get("agent_name", ""),
        "schedule_type": agent.get("schedule_type", "daily"),
        "time_slots": _parse_json_field(agent.get("time_slots")),
        "assigned_workflows": _parse_json_field(agent.get("assigned_workflows")),
    }


@router.put("/{agent_id}/schedule")
async def update_agent_schedule(agent_id: str, update: AgentScheduleUpdate):
    store = _get_store()
    existing = store.get_agent(agent_id)
    data = {
        "schedule_type": update.schedule_type,
        "time_slots": update.time_slots,
        "assigned_workflows": update.assigned_workflows,
        "updated_at": datetime.now().isoformat(),
    }
    if existing:
        store.update_agent(agent_id, data)
    else:
        store.create_agent({
            "agent_id": agent_id, "agent_name": agent_id,
            "status": "active", **data,
        })
    return {"message": "Agent schedule updated", "agent_id": agent_id}


@router.get("/{agent_id}/status")
async def get_agent_status(agent_id: str):
    store = _get_store()
    agent = store.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return AgentStatus(
        agent_id=agent_id, agent_name=agent.get("agent_name", ""),
        status=agent.get("status", "active"),
        current_shift=agent.get("current_shift"),
        last_heartbeat=agent.get("last_heartbeat"),
    )


@router.post("/{agent_id}/heartbeat")
async def agent_heartbeat(agent_id: str):
    store = _get_store()
    now = datetime.now().isoformat()
    existing = store.get_agent(agent_id)
    if existing:
        store.update_agent(agent_id, {"last_heartbeat": now, "status": "active"})
    else:
        store.create_agent({
            "agent_id": agent_id, "agent_name": agent_id,
            "status": "active", "last_heartbeat": now,
        })
    return {"message": "Heartbeat received", "agent_id": agent_id}
