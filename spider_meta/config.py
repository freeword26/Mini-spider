import os
import logging
from typing import Optional

from pydantic_settings import BaseSettings

logger = logging.getLogger("spider_meta.config")


# ============================================================
# 立项协议：硬件资源硬限制（保护机制）
# 硬件：GTX 1050 Ti 4GB + 32GB RAM + i5-12400F
# 月成本上限：¥50/月
# ============================================================
HARDWARE_LIMITS = {
    "gpu_memory_limit_mb": 3500,     # 3.5GB 硬限制
    "gpu_memory_total_mb": 4096,     # 4GB 物理显存
    "cpu_core_limit": 3.0,           # 3核硬限制
    "ram_limit_mb": 16384,           # 16GB硬限制
    "ram_total_mb": 32768,           # 32GB物理内存
    "cpu_limit_pct": 80,             # CPU使用率 ≤80%
    "disk_alert_pct": 85,           # 磁盘空间告警 85%
    "max_monthly_cost_rmb": 50,      # 月成本 ≤¥50
    "daily_budget_rmb": 50 / 30,     # 日均预算
}


class Settings(BaseSettings):
    service_name: str = "Meta-Agent"
    service_version: str = "1.0.0"
    debug: bool = False

    redis_host: str = "localhost"
    redis_port: int = 6381
    redis_db: int = 0

    api_host: str = "0.0.0.0"
    api_port: int = 8003

    llm_provider: str = "openrouter"
    llm_model: str = "default"
    llm_max_tokens: int = 4096
    llm_api_url: str = ""
    llm_api_key: str = ""

    kg_collection_name: str = "knowledge_graph"
    kg_top_k: int = 5
    enable_knowledge_retrieval: bool = True
    kg_cache_size: int = 1000
    kg_retrieval_timeout: float = 2.0

    enable_experience_reuse: bool = True
    experience_top_k: int = 3

    default_parallelism: int = 3
    min_parallelism: int = 1
    max_parallelism: int = 10

    worker_heartbeat_timeout: int = 60
    worker_max_tasks: int = 5

    log_level: str = "INFO"

    class Config:
        env_prefix: str = ""
        env_file_encoding = "utf-8"


def check_hardware_limits() -> dict:
    """启动时检查硬件资源是否满足立项协议硬限制。"""
    L = HARDWARE_LIMITS
    report = {"status": "ok", "warnings": [], "critical": [], "limits": L}

    try:
        import psutil
    except ImportError:
        report["warnings"].append("psutil 未安装，跳过硬件检查")
        return report

    # ===== RAM 检查（16GB硬限制） =====
    ram = psutil.virtual_memory()
    ram_total_mb = ram.total // (1024 * 1024)
    ram_used_mb = ram.used // (1024 * 1024)
    report["ram_total_mb"] = ram_total_mb
    report["ram_used_mb"] = ram_used_mb
    report["ram_limit_mb"] = L["ram_limit_mb"]

    if ram_used_mb > L["ram_limit_mb"]:
        c = f"RAM超限: 已用 {ram_used_mb}MB > 硬限制 {L['ram_limit_mb']}MB"
        report["critical"].append(c)
        report["status"] = "critical"

    # ===== CPU 检查（3核硬限制） =====
    cpu_count = psutil.cpu_count(logical=True)
    cpu_pct = psutil.cpu_percent(interval=1)
    report["cpu_count"] = cpu_count
    report["cpu_pct"] = cpu_pct
    report["cpu_core_limit"] = L["cpu_core_limit"]

    if cpu_count > L["cpu_core_limit"]:
        # 检测到超过3核时告警但不阻止（Docker可能看到全部核心）
        w = f"CPU核心数 {cpu_count} > 限制 {L['cpu_core_limit']}核，将通过 cpuset 限制"
        report["warnings"].append(w)

    if cpu_pct > L["cpu_limit_pct"]:
        w = f"CPU使用率 {cpu_pct}% > {L['cpu_limit_pct']}%"
        report["warnings"].append(w)
        if report["status"] != "critical":
            report["status"] = "warning"

    # ===== 磁盘检查（85%告警） =====
    disk = psutil.disk_usage("/")
    disk_pct = disk.percent
    report["disk_pct"] = disk_pct
    report["disk_alert_pct"] = L["disk_alert_pct"]

    if disk_pct > L["disk_alert_pct"]:
        c = f"磁盘空间告警: 已用 {disk_pct}% > {L['disk_alert_pct']}%"
        report["critical"].append(c)
        report["status"] = "critical"

    # ===== GPU 检查（3.5GB硬限制） =====
    try:
        result = os.popen(
            "nvidia-smi --query-gpu=memory.total,memory.used "
            "--format=csv,noheader,nounits"
        ).read().strip()
        if result:
            parts = result.split(",")
            gpu_total_mb = int(parts[0].strip())
            gpu_used_mb = int(parts[1].strip())
            report["gpu_total_mb"] = gpu_total_mb
            report["gpu_used_mb"] = gpu_used_mb
            report["gpu_limit_mb"] = L["gpu_memory_limit_mb"]

            if gpu_used_mb > L["gpu_memory_limit_mb"]:
                c = f"GPU显存超限: 已用 {gpu_used_mb}MB > 硬限制 {L['gpu_memory_limit_mb']}MB"
                report["critical"].append(c)
                report["status"] = "critical"
        else:
            report["warnings"].append("未检测到 NVIDIA GPU")
    except Exception as e:
        report["warnings"].append(f"GPU检查失败: {e}")

    return report


def load_settings() -> Settings:
    return Settings()
