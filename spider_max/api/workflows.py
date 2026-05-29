# -*- coding: utf-8 -*-
"""工作流API — SQLite持久化"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/workflows", tags=["workflows"])


def _get_store():
    try:
        from .store import PersistentStore
    except (ImportError, SystemError):
        from store import PersistentStore
    db_path = Path(__file__).parent.parent.parent.parent / "06_系统管理" / "11_无人值守工作流" / "api_data.db"
    return PersistentStore(str(db_path))


class WorkflowCreate(BaseModel):
    workflow_id: str
    name: str
    description: str = ""
    version: str = "1.0.0"
    enabled: bool = True

class WorkflowUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None

class WorkflowResponse(BaseModel):
    workflow_id: str
    name: str
    description: str
    version: str
    enabled: bool
    task_count: int = 0


@router.get("", response_model=List[WorkflowResponse])
async def list_workflows():
    store = _get_store()
    rows = store.list_workflows()
    return [WorkflowResponse(
        workflow_id=r["workflow_id"], name=r["name"], description=r["description"],
        version=r["version"], enabled=bool(r["enabled"]),
        task_count=len(json.loads(r.get("tasks", "[]")))
    ) for r in rows]


@router.post("")
async def create_workflow(workflow: WorkflowCreate):
    store = _get_store()
    if store.get_workflow(workflow.workflow_id):
        raise HTTPException(status_code=400, detail="Workflow already exists")
    store.create_workflow(workflow.dict())
    return {"message": "Workflow created", "workflow_id": workflow.workflow_id}


@router.get("/{workflow_id}")
async def get_workflow(workflow_id: str):
    store = _get_store()
    wf = store.get_workflow(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return wf


@router.put("/{workflow_id}")
async def update_workflow(workflow_id: str, update: WorkflowUpdate):
    store = _get_store()
    updates = {k: v for k, v in update.dict().items() if v is not None}
    if not store.update_workflow(workflow_id, updates):
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {"message": "Workflow updated", "workflow_id": workflow_id}


@router.delete("/{workflow_id}")
async def delete_workflow(workflow_id: str):
    store = _get_store()
    if not store.delete_workflow(workflow_id):
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {"message": "Workflow deleted", "workflow_id": workflow_id}


@router.post("/{workflow_id}/enable")
async def enable_workflow(workflow_id: str):
    store = _get_store()
    if not store.update_workflow(workflow_id, {"enabled": True}):
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {"message": "Workflow enabled", "workflow_id": workflow_id}


@router.post("/{workflow_id}/disable")
async def disable_workflow(workflow_id: str):
    store = _get_store()
    if not store.update_workflow(workflow_id, {"enabled": False}):
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {"message": "Workflow disabled", "workflow_id": workflow_id}
