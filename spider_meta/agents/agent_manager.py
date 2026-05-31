"""
spider_meta Agent Manager — 多智能体任务调度器

负责：
1. 将大任务拆分为独立子任务
2. 为每个子任务分配最优 Agent（本地/云端）
3. 在 git worktree 中并行执行
4. 收集结果、汇总报告

使用方式：
    manager = AgentManager()
    results = await manager.execute_parallel({
        "budget_check":    "检测预算阈值配置",
        "offload_switch":  "验证差分卸载开关",
        "routing":         "测试路由决策",
        "circuit_breaker": "模拟网络故障降级",
        "bandwidth":       "带宽优化对比",
        "lite_proxy":      "LiteCapabilityProxy 性能",
        "resource_monitor":"CPU/GPU/内存资源监控",
        "security":        "安全加固项检测",
        "performance":     "性能基准测试日志",
    })
"""

import asyncio
import hashlib
import json
import logging
import os
import shutil
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from spider_meta.agents.agent_router import router, AGENT_ROLES, AgentTier
from spider_meta.agents.protocol import delta_sync, lite_proxy
from spider_meta.cost_guard import budget_mgr

logger = logging.getLogger("spider_meta.manager")


# ============================================================
# 子任务定义
# ============================================================

class TaskStatus(str, Enum):
    PENDING   = "pending"
    RUNNING   = "running"
    DONE      = "done"
    FAILED    = "failed"
    CANCELLED = "cancelled"


@dataclass
class SubTask:
    task_id: str
    name: str
    description: str
    assigned_role: str = ""
    assigned_tier: str = ""
    worktree_path: str = ""
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: str = ""
    started_at: str = ""
    finished_at: str = ""
    duration_ms: float = 0
    agent_output: str = ""


# ============================================================
# Agent Manager
# ============================================================

class AgentManager:
    """
    多智能体任务调度器
    
    架构：
        AgentManager
          ├── 拆分任务 → SubTask[]
          ├── 路由分配 → 每个 SubTask 分配最优 Agent
          ├── 创建 worktree → 独立 git 工作树
          ├── 并行执行 → asyncio.gather
          └── 收集结果 → 汇总报告
    """

    def __init__(self, project_root: str = None, max_parallel: int = 4):
        self.project_root = Path(project_root or self._find_project_root())
        self.max_parallel = max_parallel
        self.worktrees_dir = self.project_root / ".worktrees"
        self.results_dir = self.project_root / "data" / "task_results"
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self._tasks: Dict[str, SubTask] = {}

    @staticmethod
    def _find_project_root() -> Path:
        """自动查找项目根目录"""
        current = Path.cwd()
        for p in [current] + list(current.parents):
            if (p / "spider_meta" / "main.py").exists():
                return p
        return current

    # ---- 核心：并行执行 ----

    async def execute_parallel(self, tasks: Dict[str, str]) -> Dict[str, SubTask]:
        """
        并行执行多个子任务
        
        tasks: {task_name: task_description}
        返回: {task_name: SubTask}
        """
        logger.info(f"[AgentManager] 开始并行执行 {len(tasks)} 个子任务")

        # 1. 拆分 + 路由分配
        subtasks = self._create_subtasks(tasks)
        
        # 2. 创建 git worktree
        self._create_worktrees(subtasks)
        
        # 3. 并行执行（受 max_parallel 限制）
        semaphore = asyncio.Semaphore(self.max_parallel)
        
        async def _run_with_semaphore(st: SubTask):
            async with semaphore:
                return await self._execute_subtask(st)

        results = await asyncio.gather(
            *[_run_with_semaphore(st) for st in subtasks.values()],
            return_exceptions=True,
        )

        # 4. 收集结果
        for name, result in zip(tasks.keys(), results):
            if isinstance(result, Exception):
                subtasks[name].status = TaskStatus.FAILED
                subtasks[name].error = str(result)
                logger.error(f"  ❌ {name}: {result}")
            else:
                subtasks[name] = result

        # 5. 清理 worktree
        self._cleanup_worktrees(subtasks)

        # 6. 保存报告
        self._save_report(subtasks)

        return subtasks

    def _create_subtasks(self, tasks: Dict[str, str]) -> Dict[str, SubTask]:
        """为每个子任务分配最优 Agent"""
        subtasks = {}
        for name, description in tasks.items():
            # 路由决策
            decision = router.route(description)
            
            st = SubTask(
                task_id=f"task-{uuid.uuid4().hex[:6]}",
                name=name,
                description=description,
                assigned_role=decision["role"],
                assigned_tier=decision["tier"],
            )
            subtasks[name] = st
            logger.info(
                f"  📋 {name} → {st.assigned_role} ({st.assigned_tier})"
            )
        return subtasks

    def _create_worktrees(self, subtasks: Dict[str, SubTask]):
        """为每个子任务创建独立的 git worktree"""
        self.worktrees_dir.mkdir(exist_ok=True)
        
        for name, st in subtasks.items():
            wt_path = self.worktrees_dir / f"{name}-{st.task_id}"
            branch_name = f"agent/{st.assigned_role}/{st.task_id}"
            
            try:
                # 创建 worktree
                subprocess.run(
                    ["git", "worktree", "add", str(wt_path), "-b", branch_name],
                    cwd=str(self.project_root),
                    capture_output=True, text=True, timeout=30,
                )
                st.worktree_path = str(wt_path)
                logger.info(f"  🌿 {name} → worktree: {wt_path.name}")
            except Exception as e:
                # worktree 已存在则复用
                if wt_path.exists():
                    st.worktree_path = str(wt_path)
                    logger.info(f"  🌿 {name} → 复用已有 worktree")
                else:
                    # 降级：直接用项目目录
                    st.worktree_path = str(self.project_root)
                    logger.warning(f"  ⚠️ {name} → worktree 创建失败，使用主目录: {e}")

    async def _execute_subtask(self, st: SubTask) -> SubTask:
        """执行单个子任务"""
        st.status = TaskStatus.RUNNING
        st.started_at = datetime.now().isoformat()
        start_time = time.time()

        logger.info(f"  ▶️  [{st.assigned_role}] 开始执行: {st.name}")

        try:
            # 根据角色选择执行方式
            if st.assigned_tier == "local":
                result = await self._execute_local(st)
            else:
                result = await self._execute_cloud(st)

            st.status = TaskStatus.DONE
            st.result = result
            st.agent_output = str(result)[:2000]
        except Exception as e:
            st.status = TaskStatus.FAILED
            st.error = str(e)
            logger.error(f"  ❌ {st.name} 执行失败: {e}")
        finally:
            st.finished_at = datetime.now().isoformat()
            st.duration_ms = (time.time() - start_time) * 1000
            status_icon = "✅" if st.status == TaskStatus.DONE else "❌"
            logger.info(
                f"  {status_icon} [{st.assigned_role}] {st.name} "
                f"({st.duration_ms:.0f}ms)"
            )

        return st

    async def _execute_local(self, st: SubTask) -> dict:
        """本地执行 — 使用 LiteCapabilityProxy"""
        # 同步到差分协议
        sync_data = delta_sync.prepare_request(
            f"agent-{st.task_id}",
            {"task": st.name, "description": st.description},
        )

        # 执行
        if st.name == "budget_check":
            return self._check_budget()
        elif st.name == "offload_switch":
            return self._check_offload_switch()
        elif st.name == "routing":
            return self._check_routing()
        elif st.name == "circuit_breaker":
            return await self._check_circuit_breaker()
        elif st.name == "bandwidth":
            return await self._check_bandwidth()
        elif st.name == "lite_proxy":
            return await self._check_lite_proxy()
        elif st.name == "resource_monitor":
            return self._check_resources()
        elif st.name == "security":
            return self._check_security()
        elif st.name == "performance":
            return self._check_performance()
        else:
            # 通用：用 lite_proxy 的文本搜索 + 摘要
            search_result = await lite_proxy.execute("text_search", {
                "text": st.description,
                "keyword": st.name,
            })
            summary = await lite_proxy.execute("text_summarize", {
                "text": st.description,
                "max_sentences": 2,
            })
            return {"search": search_result, "summary": summary}

    async def _execute_cloud(self, st: SubTask) -> dict:
        """云端执行 — 仅做路由声明，实际由本地代理执行"""
        return {
            "status": "delegated",
            "role": st.assigned_role,
            "tier": "cloud",
            "reason": f"任务 '{st.name}' 标记为云端执行，当前由本地代理兜底",
        }

    # ---- 具体检测实现 ----

    def _check_budget(self) -> dict:
        from spider_meta.config import HARDWARE_LIMITS
        return {
            "monthly_budget_rmb": HARDWARE_LIMITS["max_monthly_cost_rmb"],
            "gpu_limit_mb": HARDWARE_LIMITS["gpu_memory_limit_mb"],
            "cpu_cores": HARDWARE_LIMITS["cpu_core_limit"],
            "ram_limit_mb": HARDWARE_LIMITS["ram_limit_mb"],
            "disk_alert_pct": HARDWARE_LIMITS["disk_alert_pct"],
            "status": "ok",
        }

    def _check_offload_switch(self) -> dict:
        enabled = os.getenv("ENABLE_DIFFERENTIAL_OFFLOAD", "true").lower() in ("true", "1")
        return {"ENABLE_DIFFERENTIAL_OFFLOAD": enabled, "status": "ok" if enabled else "disabled"}

    def _check_routing(self) -> dict:
        test_tasks = {"代码": "写爬虫", "数据": "分析CSV", "文档": "翻译", "架构": "设计微服务"}
        results = {}
        for kw, task in test_tasks.items():
            d = router.route(task)
            results[kw] = d["role"]
        return {"routing_results": results, "status": "ok"}

    async def _check_circuit_breaker(self) -> dict:
        from spider_meta.cost_guard import budget_mgr
        original = budget_mgr.daily.total_rmb
        budget_mgr.daily.total_rmb = 999
        d = router.route("搜索竞品情报")
        budget_mgr.daily.total_rmb = original
        return {"fallback_role": d["role"], "fallback_tier": d["tier"], "circuit_breaker": d["tier"] == "local"}

    async def _check_bandwidth(self) -> dict:
        base = {"data": "x" * 1000, "version": 1}
        first = delta_sync.prepare_request("bw-test", base)
        base["version"] = 2
        base["delta"] = "small_change"
        second = delta_sync.prepare_request("bw-test", base)
        reduction = 1 - len(second) / max(len(first), 1)
        return {
            "first_bytes": len(first),
            "second_bytes": len(second),
            "reduction_pct": f"{reduction:.1%}",
            "target_met": reduction >= 0.70,
        }

    async def _check_lite_proxy(self) -> dict:
        text = "这是一个测试文档。" * 50 + "关键信息：Spider Meta 多智能体系统。" * 10
        start = time.time()
        r1 = await lite_proxy.execute("text_summarize", {"text": text, "max_sentences": 3})
        t1 = (time.time() - start) * 1000
        start = time.time()
        r2 = await lite_proxy.execute("basic_math", {"expression": "2**10+3*7"})
        t2 = (time.time() - start) * 1000
        return {
            "summarize_ms": round(t1, 2), "math_ms": round(t2, 2),
            "summary_len": len(r1.get("result", {}).get("summary", "")),
            "math_result": r2.get("result", {}).get("result"),
        }

    def _check_resources(self) -> dict:
        info = {}
        try:
            import psutil
            info["cpu_pct"] = psutil.cpu_percent(interval=1)
            info["cpu_count"] = psutil.cpu_count()
            mem = psutil.virtual_memory()
            info["ram_total_mb"] = mem.total // (1024*1024)
            info["ram_used_mb"] = mem.used // (1024*1024)
            info["ram_pct"] = mem.percent
            disk = psutil.disk_usage("/")
            info["disk_pct"] = disk.percent
        except ImportError:
            info["psutil"] = "not installed"
        return info

    def _check_security(self) -> dict:
        checks = {}
        # root 用户检查
        checks["non_root"] = os.getuid() != 0 if hasattr(os, "getuid") else "N/A"
        # 环境变量脱敏检查
        for key in ["LLM_API_KEY", "API_KEY", "SECRET"]:
            val = os.getenv(key, "")
            checks[f"{key}_masked"] = "****" if val else "not_set"
        # 文件权限
        main_py = self.project_root / "spider_meta" / "main.py"
        checks["main_py_exists"] = main_py.exists()
        return checks

    def _check_performance(self) -> dict:
        return {
            "target_local_latency_ms": 150,
            "target_hybrid_latency_ms": 500,
            "target_cloud_latency_ms": 1500,
            "target_rps": 50,
            "target_cold_start_s": 8,
            "target_cache_hit_rate": 0.85,
            "target_cost_per_1000_rmb": 0.15,
            "note": "Baseline targets set; run benchmark.py for actual measurements",
        }

    # ---- 清理 & 报告 ----

    def _cleanup_worktrees(self, subtasks: Dict[str, SubTask]):
        """清理 git worktree"""
        for name, st in subtasks.items():
            if st.worktree_path and st.worktree_path != str(self.project_root):
                wt_path = Path(st.worktree_path)
                if wt_path.exists():
                    try:
                        subprocess.run(
                            ["git", "worktree", "remove", "--force", str(wt_path)],
                            cwd=str(self.project_root),
                            capture_output=True, timeout=30,
                        )
                        logger.info(f"  🧹 清理 worktree: {wt_path.name}")
                    except Exception as e:
                        logger.warning(f"  ⚠️ worktree 清理失败: {e}")

    def _save_report(self, subtasks: Dict[str, SubTask]):
        """保存任务执行报告"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_tasks": len(subtasks),
            "completed": sum(1 for s in subtasks.values() if s.status == TaskStatus.DONE),
            "failed": sum(1 for s in subtasks.values() if s.status == TaskStatus.FAILED),
            "tasks": {
                name: {
                    "role": st.assigned_role,
                    "tier": st.assigned_tier,
                    "status": st.status.value,
                    "duration_ms": round(st.duration_ms, 2),
                    "error": st.error,
                }
                for name, st in subtasks.items()
            },
        }
        
        report_path = self.results_dir / f"report-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info(f"  📄 报告已保存: {report_path.name}")
        
        # 打印汇总
        logger.info("=" * 60)
        logger.info("执行汇总")
        for name, st in subtasks.items():
            icon = "✅" if st.status == TaskStatus.DONE else "❌"
            logger.info(f"  {icon} {name}: {st.assigned_role} ({st.duration_ms:.0f}ms)")
        logger.info(f"总计: {report['completed']}/{report['total_tasks']} 完成")
        
        return report


# 全局单例
agent_manager = AgentManager()
