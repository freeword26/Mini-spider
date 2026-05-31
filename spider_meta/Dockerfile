# ============================================================
# spider_meta Dockerfile（生产环境版 · 硬件保护）
# 构建上下文：E:\软件开发（项目根目录）
# 用法: docker build -f spider_meta/Dockerfile -t spider-meta .
#
# 硬件硬限制（立项协议）：
#   GPU_MEMORY_LIMIT=3500M  CPU_CORE_LIMIT=3.0
#   RAM_LIMIT=16G           DISK_ALERT=85%
# ============================================================

FROM python:3.12-slim

# 安装必需工具
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r appuser && useradd -r -g appuser appuser

# 安装 Python 依赖
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
        fastapi>=0.100.0 \
        uvicorn[standard]>=0.23.0 \
        httpx>=0.24.0 \
        pydantic>=2.0.0 \
        pydantic-settings>=2.0.0 \
        python-dotenv>=1.0.0 \
        pyyaml>=6.0.0 \
        redis>=5.0.0 \
        psutil>=5.9.0

WORKDIR /app

# 复制应用代码
COPY spider_meta/ ./spider_meta/

RUN mkdir -p /app/data /app/logs && chown -R appuser:appuser /app

# ---- 硬件资源限制环境变量（立项协议硬限制） ----
ENV GPU_MEMORY_LIMIT_MB=3500 \
    CPU_CORE_LIMIT=3.0 \
    RAM_LIMIT_MB=16384 \
    DISK_ALERT_PCT=85 \
    MONTHLY_BUDGET_RMB=50 \
    SPIDER_META_DATA=/app/data

USER appuser

EXPOSE 8003

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8003/health || exit 1

ENTRYPOINT ["uvicorn", "spider_meta.main:app"]
CMD ["--host", "0.0.0.0", "--port", "8003", "--log-level", "info"]
