#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RebuildScript — 一键重建完整运行环境
- 从 Git 仓库拉取代码
- 安装依赖
- 初始化数据库
- 启动所有服务
- 目标：< 5分钟
"""

import os
import sys
import subprocess
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class RebuildScript:
    """一键重建管理器"""

    STEPS = [
        ("clone", "Clone 代码", "git clone {repo_url} {target_dir}"),
        ("checkout", "切换分支", "cd {target_dir} && git checkout {branch}"),
        ("install_deps", "安装依赖", "cd {target_dir} && pip install -e '.[dev]'"),
        ("init_db", "初始化数据库", "cd {target_dir} && python -c \"from spider_max.db import DatabaseManager; DatabaseManager()\""),
        ("run_tests", "运行测试", "cd {target_dir} && python -m pytest spider_max/tests/ -x -q"),
        ("start_api", "启动API服务", "cd {target_dir} && python -m uvicorn spider_max.api.server:create_app --host 0.0.0.0 --port 8041"),
    ]

    def __init__(
        self,
        repo_url: str = "https://github.com/freeword26/Mini-spider.git",
        target_dir: str = "E:/软件开发/spider_max",
        branch: str = "main",
        python_cmd: Optional[str] = None,
    ):
        self.repo_url = repo_url
        self.target_dir = Path(target_dir)
        self.branch = branch
        self.python_cmd = python_cmd or sys.executable
        self._log: list = []

    def rebuild(self, steps: Optional[list] = None) -> Dict:
        """
        执行一键重建。
        返回: {"status": "ok"/"error", "total_steps": N, "completed": N, "duration_seconds": N, "details": [...]}
        """
        start_time = time.time()
        target_steps = steps or [s[0] for s in self.STEPS]
        completed = 0
        failed = 0
        details = []

        for step_id, step_name, cmd_template in self.STEPS:
            if step_id not in target_steps:
                continue
            ctx = {
                "repo_url": self.repo_url,
                "target_dir": str(self.target_dir),
                "branch": self.branch,
                "python": self.python_cmd,
            }
            cmd = cmd_template.format(**ctx)

            logger.info(f"[{completed+1}/{len(target_steps)}] {step_name}: {cmd}")
            step_start = time.time()

            try:
                result = subprocess.run(
                    cmd, shell=True, capture_output=True, text=True, timeout=120,
                    cwd=str(self.target_dir.parent if step_id == "start_api" else self.target_dir.parent),
                )
                duration = time.time() - step_start
                success = result.returncode == 0

                step_result = {
                    "step": step_id, "name": step_name,
                    "status": "ok" if success else "error",
                    "duration_seconds": round(duration, 2),
                    "returncode": result.returncode,
                    "stdout": result.stdout[-500:] if result.stdout else "",
                    "stderr": result.stderr[-500:] if result.stderr else "",
                }

                if success:
                    completed += 1
                    logger.info(f"  OK ({duration:.1f}s)")
                else:
                    failed += 1
                    logger.error(f"  FAILED (rc={result.returncode}): {result.stderr[-200:]}")
                    step_result["status"] = "error"

                details.append(step_result)

                if not success and step_id != "run_tests":
                    break

            except subprocess.TimeoutExpired:
                failed += 1
                details.append({
                    "step": step_id, "name": step_name,
                    "status": "timeout", "duration_seconds": 120,
                    "stderr": "Command timed out after 120s",
                })
                logger.error(f"  TIMEOUT (120s)")
                break
            except Exception as e:
                failed += 1
                details.append({
                    "step": step_id, "name": step_name,
                    "status": "error", "duration_seconds": 0,
                    "stderr": str(e),
                })
                logger.error(f"  ERROR: {e}")
                break

        total_duration = time.time() - start_time
        all_ok = failed == 0 and completed == len(target_steps)

        return {
            "status": "ok" if all_ok else "error",
            "completed": completed,
            "failed": failed,
            "total_steps": len(target_steps),
            "duration_seconds": round(total_duration, 2),
            "target_under_5min": total_duration < 300,
            "timestamp": datetime.now().isoformat(),
            "details": details,
        }

    def rebuild_docker(self) -> Dict:
        """通过 Docker Compose 一键重建"""
        start_time = time.time()
        steps = [
            ("pull", "拉取最新代码", "git pull origin main"),
            ("build", "构建镜像", "docker build -t spider-max:latest ."),
            ("restart", "重启服务", "docker compose down && docker compose up -d"),
            ("health_check", "健康检查", "sleep 5 && curl -f http://localhost:8041/api/v1/health"),
        ]
        return self._run_steps(steps, start_time)

    def _run_steps(self, steps: list, start_time: float) -> Dict:
        completed = 0
        failed = 0
        details = []
        for step_id, step_name, cmd in steps:
            try:
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=180)
                success = result.returncode == 0
                dur = 0
                details.append({
                    "step": step_id, "name": step_name,
                    "status": "ok" if success else "error",
                    "returncode": result.returncode,
                    "stderr": result.stderr[-300:] if not success else "",
                })
                if success:
                    completed += 1
                else:
                    failed += 1
                    break
            except subprocess.TimeoutExpired:
                failed += 1
                details.append({"step": step_id, "name": step_name, "status": "timeout"})
                break
        total_duration = time.time() - start_time
        return {
            "status": "ok" if failed == 0 else "error",
            "completed": completed, "failed": failed,
            "duration_seconds": round(total_duration, 2),
            "target_under_5min": total_duration < 300,
            "details": details,
        }
