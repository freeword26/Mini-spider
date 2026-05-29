# -*- coding: utf-8 -*-
"""执行记录API — SQLite持久化"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(prefix="/executions", tags=["executions"])


def _get_store():
    try:
        from .store import PersistentStore
    except (ImportError, SystemError):
        from store import PersistentStore
    db_path = Path(__file__).parent.parent.parent.parent / "06_系统管理" / "11_无人值守工作流" / "api_data.db"
    return PersistentStore(str(db_path))


class ExecutionTrigger(BaseModel):
    workflow_id: str
    context: Optional[Dict] = None

class ExecutionResponse(BaseModel):
    execution_id: str
    workflow_id: str
    status: str
    start_time: Optional[str]
    end_time: Optional[str]
    duration_seconds: float


@router.get("", response_model=List[ExecutionResponse])
async def list_executions(workflow_id: Optional[str] = None, limit: int = 100):
    store = _get_store()
    rows = store.list_executions(workflow_id, limit)
    return [ExecutionResponse(
        execution_id=r["execution_id"], workflow_id=r["workflow_id"],
        status=r["status"], start_time=r.get("start_time"),
        end_time=r.get("end_time"), duration_seconds=r.get("duration_seconds", 0.0)
    ) for r in rows]


@router.post("")
async def trigger_execution(trigger: ExecutionTrigger):
    store = _get_store()
    execution_id = "exec_{}".format(datetime.now().strftime("%Y%m%d%H%M%S"))
    store.create_execution({
        "execution_id": execution_id,
        "workflow_id": trigger.workflow_id,
        "status": "pending",
        "start_time": datetime.now().isoformat(),
        "context": trigger.context or {},
    })
    return {"message": "Execution triggered", "execution_id": execution_id, "workflow_id": trigger.workflow_id}


@router.get("/{execution_id}")
async def get_execution(execution_id: str):
    store = _get_store()
    execution = store.get_execution(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    return execution


@router.post("/{execution_id}/cancel")
async def cancel_execution(execution_id: str):
    store = _get_store()
    execution = store.get_execution(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    if execution["status"] in ("completed", "failed", "cancelled"):
        raise HTTPException(status_code=400, detail="Cannot cancel finished execution")
    store.update_execution(execution_id, {"status": "cancelled", "end_time": datetime.now().isoformat()})
    return {"message": "Execution cancelled", "execution_id": execution_id}


@router.post("/{execution_id}/retry")
async def retry_execution(execution_id: str):
    store = _get_store()
    execution = store.get_execution(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    new_id = "exec_{}".format(datetime.now().strftime("%Y%m%d%H%M%S"))
    store.create_execution({
        "execution_id": new_id,
        "workflow_id": execution["workflow_id"],
        "status": "pending",
        "start_time": datetime.now().isoformat(),
        "context": json.loads(execution.get("context", "{}")),
    })
    return {"message": "Execution retry triggered", "execution_id": new_id, "original_execution_id": execution_id}
