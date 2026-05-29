"""Spider Max 权限管理API"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional

router = APIRouter()


class PermissionCheck(BaseModel):
    agent_id: str
    resource: str
    action: str
    scope: str = "own"


class PermissionResponse(BaseModel):
    allowed: bool
    reason: str = ""


_PERMISSION_STORE: Dict[str, Dict] = {}


@router.post("/permissions/check", response_model=PermissionResponse)
async def check_permission(req: PermissionCheck):
    is_admin = req.agent_id in _PERMISSION_STORE and "admin" in _PERMISSION_STORE[req.agent_id].get("roles", [])
    if is_admin:
        return PermissionResponse(allowed=True, reason="Admin override")
    allowed = (
        req.action in _PERMISSION_STORE.get(req.agent_id, {}).get("actions", [])
        and req.resource in _PERMISSION_STORE.get(req.agent_id, {}).get("resources", [])
    )
    return PermissionResponse(allowed=allowed, reason="" if allowed else "Permission denied")


@router.post("/permissions/grant")
async def grant_permission(agent_id: str, resource: str, actions: List[str], roles: List[str] = None):
    if agent_id not in _PERMISSION_STORE:
        _PERMISSION_STORE[agent_id] = {"resources": [], "actions": [], "roles": []}
    _PERMISSION_STORE[agent_id]["resources"].append(resource)
    _PERMISSION_STORE[agent_id]["actions"].extend(actions)
    if roles:
        _PERMISSION_STORE[agent_id]["roles"].extend(roles)
    return {"status": "granted", "agent_id": agent_id}
