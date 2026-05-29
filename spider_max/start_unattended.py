# -*- coding: utf-8 -*-
"""无人值守系统 v2.0 — 一键启动"""

import sys
import os
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
os.chdir(str(_SCRIPT_DIR))
sys.path.insert(0, str(_SCRIPT_DIR))
sys.path.insert(0, str(_SCRIPT_DIR.parent))
os.environ["PYTHONIOENCODING"] = "utf-8"

_LOG_DIR = _SCRIPT_DIR.parent.parent / "logs"
_LOG_DIR.mkdir(parents=True, exist_ok=True)

from main import app

BANNER = r"""
╔══════════════════════════════════════════════════════════════╗
║          无人值守系统 v2.0 — 服务已启动                     ║
╠══════════════════════════════════════════════════════════════╣
║  Root      GET  http://localhost:5005/                      ║
║  Dashboard GET  http://localhost:5005/dashboard             ║
║  API Docs  GET  http://localhost:5005/docs                  ║
║  ReDoc     GET  http://localhost:5005/redoc                 ║
╠══════════════════════════════════════════════════════════════╣
║  API v1 Endpoints:                                          ║
║    GET    /api/v1/workflows                                 ║
║    POST   /api/v1/workflows                                 ║
║    GET    /api/v1/workflows/{id}                            ║
║    PUT    /api/v1/workflows/{id}                            ║
║    DELETE /api/v1/workflows/{id}                            ║
║    POST   /api/v1/workflows/{id}/enable                     ║
║    POST   /api/v1/workflows/{id}/disable                    ║
║    GET    /api/v1/executions                                ║
║    POST   /api/v1/executions                                ║
║    GET    /api/v1/executions/{id}                           ║
║    POST   /api/v1/executions/{id}/cancel                    ║
║    POST   /api/v1/executions/{id}/retry                     ║
║    GET    /api/v1/schedules                                 ║
║    GET    /api/v1/schedules/{id}                            ║
║    PUT    /api/v1/schedules/{id}                            ║
║    POST   /api/v1/schedules/{id}/pause                      ║
║    POST   /api/v1/schedules/{id}/resume                     ║
║    GET    /api/v1/agents                                    ║
║    GET    /api/v1/agents/{id}                               ║
║    GET    /api/v1/agents/{id}/schedule                      ║
║    PUT    /api/v1/agents/{id}/schedule                      ║
║    GET    /api/v1/agents/{id}/status                        ║
║    POST   /api/v1/agents/{id}/heartbeat                     ║
║    GET    /api/v1/health                                    ║
║    GET    /api/v1/health/live                               ║
║    GET    /api/v1/health/ready                              ║
║    GET    /api/v1/health/metrics                            ║
║    GET    /api/v1/health/validate                           ║
║    GET    /api/v1/health/three-layer                        ║
╚══════════════════════════════════════════════════════════════╝
"""

if __name__ == "__main__":
    import uvicorn
    print(BANNER)
    uvicorn.run(app, host="0.0.0.0", port=5005, log_level="info")
