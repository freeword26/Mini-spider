"""Spider Max 模块管理API"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional

router = APIRouter()


class ModuleInfoResponse(BaseModel):
    name: str
    category: str
    status: str
    functions: List[str]


class ModuleSummaryResponse(BaseModel):
    total: int
    loaded: int
    missing: int
    by_category: Dict[str, Dict]


@router.get("/modules", response_model=ModuleSummaryResponse)
async def list_modules():
    from spider_max import get_registry
    reg = get_registry()
    reg.discover_all()
    return ModuleSummaryResponse(**reg.get_status_summary())


@router.get("/modules/{name}", response_model=ModuleInfoResponse)
async def get_module(name: str):
    from spider_max import get_registry
    reg = get_registry()
    reg.discover_all()
    info = reg.get(name)
    if not info:
        raise HTTPException(status_code=404, detail=f"Module '{name}' not found")
    return ModuleInfoResponse(
        name=info.name, category=info.category.value,
        status=info.status, functions=info.functions[:30],
    )


@router.post("/modules/{name}/load")
async def load_module(name: str):
    from spider_max import get_registry
    reg = get_registry()
    reg.discover_all()
    info = reg.get(name)
    if not info:
        raise HTTPException(status_code=404, detail=f"Module '{name}' not found")
    ok = info.load()
    return {"name": name, "loaded": ok, "status": info.status}
