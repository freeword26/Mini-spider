FROM python:3.11-slim

LABEL maintainer="Spider MAX Team"
LABEL description="Spider MAX v3.0.0 — 全栈项目管理与多Agent协同平台"

ENV PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    TZ=Asia/Shanghai \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libsqlite3-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 先复制依赖文件，利用 Docker 缓存层
COPY pyproject.toml README.md ./
COPY spider_max/__init__.py ./spider_max/__init__.py

# 安装 Python 依赖
RUN pip install --upgrade pip && \
    pip install -e ".[dev]"

# 复制全部源码
COPY . .

# 创建数据目录
RUN mkdir -p /app/data /app/logs

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:5005/api/v1/health || exit 1

EXPOSE 5005

CMD ["python", "-m", "uvicorn", "spider_max.main:app", "--host", "0.0.0.0", "--port", "5005"]
