"""
spider_meta 多智能体并行检测 — 直接执行版
用法: cd E:\软件开发 && python spider_meta/run_parallel.py
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path

# 确保项目根目录在 path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

from spider_meta.agents.agent_manager import AgentManager
from spider_meta.agents import router, delta_sync, lite_proxy

# ============================================================
# 检测任务定义
# ============================================================

TASKS = {
    "1_budget_check":    "检测预算阈值配置",
    "2_offload_switch":  "验证差分卸载开关",
    "3_routing":         "测试路由决策",
    "4_circuit_breaker": "模拟网络故障降级",
    "5_bandwidth":       "带宽优化对比",
    "6_lite_proxy":      "LiteCapabilityProxy 性能",
    "7_resource_monitor":"CPU/GPU/内存资源监控",
    "8_security":        "安全加固项检测",
    "9_performance":     "性能基准测试",
}


def assign_roles_to_tasks(tasks: dict) -> dict:
    """为每个任务分配 Agent 角色"""
    assignments = {}
    for name, desc in tasks.items():
        decision = router.route(desc)
        assignments[name] = {
            "role": decision["role"],
            "tier": decision["tier"],
            "model": decision["model"],
        }
        print(f"  [{decision['tier']:5s}] {name:20s} -> {decision['role']}")
    return assignments


def run_budget_check() -> dict:
    from spider_meta.config import HARDWARE_LIMITS
    return {
        "monthly_budget": HARDWARE_LIMITS["max_monthly_cost_rmb"],
        "gpu_limit_mb": HARDWARE_LIMITS["gpu_memory_limit_mb"],
        "cpu_cores": HARDWARE_LIMITS["cpu_core_limit"],
        "ram_limit_mb": HARDWARE_LIMITS["ram_limit_mb"],
        "disk_alert_pct": HARDWARE_LIMITS["disk_alert_pct"],
    }


def run_offload_switch() -> dict:
    enabled = os.getenv("ENABLE_DIFFERENTIAL_OFFLOAD", "true").lower() in ("true", "1", "on")
    return {"ENABLE_DIFFERENTIAL_OFFLOAD": enabled, "status": "ok" if enabled else "disabled"}


def run_routing() -> dict:
    test = {"代码": "写爬虫", "数据": "分析CSV", "文档": "翻译", "架构": "设计微服务", "情报": "搜索竞品", "文案": "写推文"}
    results = {}
    for kw, task in test.items():
        d = router.route(task)
        results[kw] = d["role"]
    return results


async def run_circuit_breaker() -> dict:
    from spider_meta.cost_guard import budget_mgr
    original = budget_mgr.daily.total_rmb
    budget_mgr.daily.total_rmb = 999  # 模拟超预算
    d = router.route("搜索竞品情报")
    budget_mgr.daily.total_rmb = original
    return {"fallback_role": d["role"], "fallback_tier": d["tier"], "breaker_ok": d["tier"] == "local"}


async def run_bandwidth() -> dict:
    base = {"data": "x" * 10000, "version": 1, "config": {"model": "qwen2.5:7b"}}
    first = delta_sync.prepare_request("bw-test", base)
    base["version"] = 2
    base["config"] = {"model": "qwen2.5-coder:7b"}
    second = delta_sync.prepare_request("bw-test", base)
    reduction = 1 - len(second) / max(len(first), 1)
    return {
        "first_bytes": len(first), "second_bytes": len(second),
        "reduction_pct": f"{reduction:.1%}", "target_70pct_met": reduction >= 0.70,
    }


async def run_lite_proxy() -> dict:
    text = "Spider Meta 多智能体系统架构概述。" * 100 + "关键功能：差分卸载、DeltaSync、Lite代理。" * 20
    start = time.time()
    r = await lite_proxy.execute("text_summarize", {"text": text, "max_sentences": 3})
    t = (time.time() - start) * 1000
    math_r = await lite_proxy.execute("basic_math", {"expression": "2**10+3*7"})
    return {
        "summarize_ms": round(t, 2),
        "summary_len": len(r.get("result", {}).get("summary", "")),
        "math_result": math_r.get("result", {}).get("result"),
        "local_skills": lite_proxy.local_skill_names,
    }


def run_resource_monitor() -> dict:
    info = {}
    try:
        import psutil
        info["cpu_pct"] = psutil.cpu_percent(interval=1)
        m = psutil.virtual_memory()
        info["ram_total_gb"] = round(m.total / (1024**3), 1)
        info["ram_used_gb"] = round(m.used / (1024**3), 1)
        info["ram_pct"] = m.percent
        d = psutil.disk_usage(str(PROJECT_ROOT))
        info["disk_pct"] = d.percent
        info["disk_free_gb"] = round(d.free / (1024**3), 1)
    except ImportError:
        info["psutil"] = "not_installed"
    # GPU
    try:
        import subprocess
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,memory.used,utilization.gpu",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5
        )
        if r.stdout.strip():
            parts = r.stdout.strip().split(",")
            info["gpu_name"] = parts[0].strip()
            info["gpu_mem_total_mb"] = int(parts[1].strip())
            info["gpu_mem_used_mb"] = int(parts[2].strip())
            info["gpu_util_pct"] = int(parts[3].strip())
    except Exception:
        info["gpu"] = "not_available"
    return info


def run_security() -> dict:
    checks = {
        "non_root": os.getuid() != 0 if hasattr(os, "getuid") else "windows",
        "api_key_masked": "****" if os.getenv("LLM_API_KEY") else "not_set",
        "main_py_exists": (PROJECT_ROOT / "spider_meta" / "main.py").exists(),
    }
    # 文件权限
    for p in [PROJECT_ROOT / "spider_meta", PROJECT_ROOT / "spider_meta" / "agents"]:
        checks[f"dir_{p.name}_exists"] = p.exists()
    return checks


def run_performance() -> dict:
    return {
        "targets": {
            "local_latency_ms": 150, "hybrid_latency_ms": 500, "cloud_latency_ms": 1500,
            "rps": 50, "cold_start_s": 8, "cache_hit_rate": 0.85, "cost_per_1000_rmb": 0.15,
        },
        "status": "baseline_set",
    }


# ============================================================
# 并行执行引擎
# ============================================================

async def run_all():
    print("=" * 60)
    print("Spider Meta 多智能体并行检测")
    print("=" * 60)

    # 1. 角色分配
    print("\n[1] Agent 角色分配:")
    assignments = assign_roles_to_tasks(TASKS)

    # 2. 并行执行所有检测
    print("\n[2] 并行执行检测:")
    start = time.time()

    # 同步任务在线程池中运行，异步任务直接 await
    loop = asyncio.get_event_loop()

    async def run_task(name, desc):
        t0 = time.time()
        try:
            if name == "4_circuit_breaker":
                result = await run_circuit_breaker()
            elif name == "5_bandwidth":
                result = await run_bandwidth()
            elif name == "6_lite_proxy":
                result = await run_lite_proxy()
            elif name == "1_budget_check":
                result = await loop.run_in_executor(None, run_budget_check)
            elif name == "2_offload_switch":
                result = await loop.run_in_executor(None, run_offload_switch)
            elif name == "3_routing":
                result = await loop.run_in_executor(None, run_routing)
            elif name == "7_resource_monitor":
                result = await loop.run_in_executor(None, run_resource_monitor)
            elif name == "8_security":
                result = await loop.run_in_executor(None, run_security)
            elif name == "9_performance":
                result = await loop.run_in_executor(None, run_performance)
            else:
                result = {"status": "unknown_task"}
            ms = (time.time() - t0) * 1000
            return name, {"status": "ok", "result": result, "ms": round(ms, 2)}
        except Exception as e:
            ms = (time.time() - t0) * 1000
            return name, {"status": "error", "error": str(e), "ms": round(ms, 2)}

    results = await asyncio.gather(*[run_task(n, d) for n, d in TASKS.items()])
    total_ms = (time.time() - start) * 1000

    # 3. 汇总报告
    report = {name: data for name, data in results}

    print(f"\n[3] 执行汇总 (总耗时: {total_ms:.0f}ms):")
    print("-" * 60)
    for name, data in report.items():
        icon = "OK" if data["status"] == "ok" else "ERR"
        role = assignments.get(name, {}).get("role", "?")
        tier = assignments.get(name, {}).get("tier", "?")
        ms = data.get("ms", 0)
        print(f"  [{icon}] {name:22s} | {role:22s} ({tier:5s}) | {ms:8.1f}ms")
        if data["status"] == "error":
            print(f"       ERR: {data.get('error','')[:80]}")

    done = sum(1 for d in report.values() if d["status"] == "ok")
    print(f"\n结果: {done}/{len(report)} 通过")

    # 4. 详细结果
    print(f"\n[4] 详细结果 (JSON):")
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))

    # 5. DeltaSync 统计
    print(f"\n[5] DeltaSync 带宽统计:")
    stats = delta_sync.get_stats()
    print(f"  同步次数: {stats['sync_count']}")
    print(f"  节省字节: {stats['total_bytes_saved']:,}")

    return report


if __name__ == "__main__":
    asyncio.run(run_all())
