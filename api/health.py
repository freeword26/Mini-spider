"""Spider Max 系统健康检查"""
from datetime import datetime
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    timestamp: str
    uptime: str
    modules_loaded: int


_start = datetime.now()


@router.get("/health", response_model=HealthResponse)
async def health():
    from spider_max import get_registry
    reg = get_registry()
    summary = reg.get_status_summary()
    uptime = str(datetime.now() - _start).split(".")[0]
    return HealthResponse(
        status="ok",
        service="spider-max",
        version="3.0.0",
        timestamp=datetime.now().isoformat(),
        uptime=uptime,
        modules_loaded=summary["loaded"],
    )


@router.get("/health/ready")
async def readiness():
    return {"status": "ready", "timestamp": datetime.now().isoformat()}


@router.get("/health/live")
async def liveness():
    return {"status": "alive"}
