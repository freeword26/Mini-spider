# -*- coding: utf-8 -*-
"""
API路由模块
"""

try:
    from .workflows import router as workflows_router
    from .executions import router as executions_router
    from .schedules import router as schedules_router
    from .agents import router as agents_router
    from .health import router as health_router
except (ImportError, SystemError):
    from workflows import router as workflows_router
    from executions import router as executions_router
    from schedules import router as schedules_router
    from agents import router as agents_router
    from health import router as health_router

__all__ = [
    "workflows_router",
    "executions_router",
    "schedules_router",
    "agents_router",
    "health_router",
]
