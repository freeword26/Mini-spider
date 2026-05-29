"""spider_max API Server — 统一FastAPI应用"""

import os
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s [SpiderMax] %(levelname)s: %(message)s")
logger = logging.getLogger("spider-max")


class AppState(BaseModel):
    started_at: str = ""
    version: str = "3.0.0"
    modules_loaded: int = 0


state = AppState()


def _include_module_routers(app: FastAPI, base_path: str):
    """自动发现并注册api模块中的路由"""
    api_dir = Path(base_path) / "api"
    if not api_dir.exists():
        return
    sys_path = str(api_dir.parent)
    if sys_path not in os.sys.path:
        os.sys.path.insert(0, sys_path)
    for f in sorted(api_dir.glob("*.py")):
        if f.stem in ("__init__", "main"):
            continue
        try:
            mod = __import__(f"api.{f.stem}", fromlist=["*"])
            if hasattr(mod, "router") or hasattr(mod, f"{f.stem}_router"):
                router = getattr(mod, f"{f.stem}_router", None) or getattr(mod, "router", None)
                if router:
                    app.include_router(router)
                    logger.info(f"  Router loaded: {f.stem}")
        except Exception as e:
            logger.debug(f"  Skip {f.stem}: {e}")


def create_app() -> FastAPI:
    from datetime import datetime

    app = FastAPI(
        title="Spider Max API",
        description="Spider Max (大蜘蛛) — 全栈项目管理与多Agent智能体协同平台",
        version="3.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    _include_module_routers(app, str(Path(__file__).resolve().parents[2]))
    from spider_max.api.dashboard import router as dash_router
    from spider_max.api.modules import router as modules_router
    from spider_max.api.permissions import router as perm_router

    app.include_router(health_router, prefix="/api/v1", tags=["系统"])
    app.include_router(dash_router, prefix="/api/v1", tags=["仪表板"])
    app.include_router(modules_router, prefix="/api/v1", tags=["模块管理"])
    app.include_router(perm_router, prefix="/api/v1", tags=["权限"])

    _include_module_routers(app, str(Path(__file__).resolve().parents[2]))

    state.started_at = datetime.now().isoformat()
    logger.info(f"Spider Max API v{state.version} started")

    @app.get("/", tags=["根"])
    async def root():
        return {
            "service": "Spider Max",
            "version": "3.0.0",
            "started_at": state.started_at,
            "docs": "/docs",
        }

    return app


app = create_app()
