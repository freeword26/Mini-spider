#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
运维文档自动生成器 — Spider MAX v3.1.0
自动生成: 运行手册 / 故障排查 / 成本报告 / 升级流程 / 联系人清单
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

DOC_DIR = Path(__file__).resolve().parent


def generate_runbook() -> str:
    return """# Spider MAX 运行手册

## 启动命令

```bash
# 开发模式
pip install -e .
spider serve --port 8041

# Docker 单容器
docker run -d --name spider-max -p 8041:8041 spider-max:3.0.0

# Docker 完整部署
cd config && docker-compose up -d
```

## 停止命令

```bash
# 本地
Ctrl+C 或 kill $(lsof -t -i:8041)

# Docker
docker stop spider-max

# Docker 完整
cd config && docker-compose down
```

## 重启命令

```bash
# Docker
docker restart spider-max

# Docker 完整
cd config && docker-compose restart
```

## 查看状态

```bash
# API 健康检查
curl http://localhost:8041/api/v1/health

# CLI 仪表板
spider dashboard

# 系统监控
python -c "from spider_max.ai_workspace.recovery.recovery_manager import RecoveryManager; r=RecoveryManager(); print(r.full_health_check())"

# 容器状态
docker ps | grep spider
docker logs -f spider-max
```
"""


def generate_troubleshooting() -> str:
    return """# Spider MAX 故障排查指南

## 常见错误代码

### E001 — 端口已被占用
**现象**: `Error: [Errno 98] Address already in use: ('0.0.0.0', 8041)`
**解决**:
```bash
lsof -i :8041      # 查找占用进程
kill -9 <PID>       # 结束进程
# 或更换端口
spider serve --port 8042
```

### E002 — 数据库损坏
**现象**: `sqlite3.DatabaseError: database disk image is malformed`
**解决**:
```bash
python -c "
from spider_max.ai_workspace.recovery.db_backup import DatabaseBackup
b = DatabaseBackup()
result = b.restore()
print(result)
"
```

### E003 — Docker 容器启动失败
**现象**: `docker: Error response from daemon: Conflict`
**解决**:
```bash
docker rm -f spider-max spider-scheduler spider-rabbitmq
docker-compose up -d
```

### E004 — 依赖缺失
**现象**: `ModuleNotFoundError: No module named 'xxx'`
**解决**:
```bash
pip install -e '.[dev]'
```

### E005 — 配置错误导致服务异常
**现象**: 服务启动后立即崩溃，日志显示配置解析错误
**解决**:
```bash
python -c "
from spider_max.ai_workspace.recovery.config_rollback import ConfigRollback
cr = ConfigRollback()
result = cr.rollback(steps=1)
print(result)
"
```

### E006 — CPU/内存告警
**现象**: 收到 CPU > 90% 或内存 > 90% 告警
**解决**:
```bash
# 检查资源使用
docker stats spider-max

# 限制容器资源
docker update --cpus=2 --memory=2g spider-max

# 或重启
docker restart spider-max
```

## 日志位置
- 本地: `logs/spider_max.log`
- Docker: `docker logs spider-max`
- 工作流执行: `spider_max/tests/`

## 紧急联系
- GitHub Issues: https://github.com/freeword26/Mini-spider/issues
"""


def generate_cost_report() -> str:
    return """# Spider MAX 成本报告模板

## 资源使用概览（自动生成）

| 资源 | 用量 | 单位 | 备注 |
|---|---|---|---|
| CPU | -- | % | 容器限制: 2核 |
| 内存 | -- | MB | 容器限制: 2GB |
| 磁盘 | -- | MB | 数据+日志+备份 |
| 网络 | -- | MB | API请求+通知 |

## Docker 容器资源

| 容器 | CPU限制 | 内存限制 | 实际CPU | 实际内存 |
|---|---|---|---|---|
| spider-max | 2核 | 2GB | -- | -- |
| spider-scheduler | 共享 | 共享 | -- | -- |
| spider-rabbitmq | 共享 | 共享 | -- | -- |

## 备份存储

| 项目 | 路径 | 保留策略 | 总大小 |
|---|---|---|---|
| 数据库备份 | data/backups/ | 7天 | -- |
| 配置快照 | data/config_snapshots/ | 20个 | -- |

## 成本优化建议
- 非生产环境可降低 CPU 限制到 0.5 核
- 备份可配置为 S3/OSS 远程存储
- RabbitMQ 如不需要可关闭（设置 EVENT_BUS_MODE=memory）
"""


def generate_upgrade_guide() -> str:
    return """# Spider MAX 升级流程

## 零停机升级（Docker）

```bash
# 1. 拉取最新代码
git pull origin main

# 2. 构建新镜像
docker build -t spider-max:latest .

# 3. 滚动重启（逐个容器）
docker compose up -d --no-deps --build spider-max

# 4. 健康检查
curl http://localhost:8041/api/v1/health

# 5. 验证工作流
spider dashboard
```

## 本地升级

```bash
# 1. 备份当前数据库
python -c "from spider_max.ai_workspace.recovery.db_backup import DatabaseBackup; DatabaseBackup().backup(tag='pre-upgrade')"

# 2. 保存配置快照
python -c "from spider_max.ai_workspace.recovery.config_rollback import ConfigRollback; from spider_max.config import load_config; ConfigRollback().snapshot(load_config().to_dict(), tag='pre-upgrade')"

# 3. 拉取代码 + 安装
git pull origin main
pip install -e '.[dev]'

# 4. 重启服务
spider serve --port 8041

# 5. 验证
curl http://localhost:8041/api/v1/health
```

## 回滚

```bash
# 配置回滚
python -c "from spider_max.ai_workspace.recovery.config_rollback import ConfigRollback; print(ConfigRollback().rollback(steps=1))"

# 数据库回滚
python -c "from spider_max.ai_workspace.recovery.db_backup import DatabaseBackup; print(DatabaseBackup().restore())"

# 代码回滚
git log --oneline -5
git checkout <commit_hash>
```
"""


def generate_contacts() -> str:
    return """# Spider MAX 联系人清单

## 核心组件负责人

| 组件 | 模块路径 | 职责 | 状态 |
|---|---|---|---|
| API服务 | api/server.py | FastAPI路由、健康检查 | ✅ 已实现 |
| CLI | cli/ | 命令行接口 | ✅ 已实现 |
| 工作流引擎 | workflow_executor.py | DAG执行、重试、熔断 | ✅ 已实现 |
| 事件总线 | event_bus.py | 内存/RabbitMQ通信 | ✅ 已实现 |
| 监控告警 | monitoring.py | 指标采集、阈值告警 | ✅ 已实现 |
| 自愈引擎 | self_healing.py | 故障检测、自动修复 | ✅ 已实现 |
| 数据库备份 | ai-workspace/recovery/db_backup.py | 备份/恢复 | 🆕 v3.1.0 |
| 配置回滚 | ai-workspace/recovery/config_rollback.py | 快照/回滚 | 🆕 v3.1.0 |
| 系统监控 | ai-workspace/recovery/monitor_alerts.py | CPU/内存/磁盘 | 🆕 v3.1.0 |
| 一键重建 | ai-workspace/recovery/rebuild.py | 环境重建 | 🆕 v3.1.0 |
| 通知中心 | ai-workspace/notifications/ | 飞书/邮件/Webhook | 🆕 v3.1.0 |
| 任务编排 | ai-workspace/dispatchers/ | 多Agent并行 | 🆕 v3.1.0 |

## 项目信息
- 仓库: https://github.com/freeword26/Mini-spider
- 版本: v3.1.0
- Python: 3.11+
- 协议: MIT

## 问题反馈
- GitHub Issues: https://github.com/freeword26/Mini-spider/issues
"""


def generate_all(base_dir=None, output_dir=None) -> Dict:
    if base_dir is None and output_dir:
        base_dir = Path(output_dir)
    """生成全部运维文档"""
    base = Path(base_dir) if base_dir else DOC_DIR
    docs = {
        "RUNBOOK.md": generate_runbook(),
        "TROUBLESHOOTING.md": generate_troubleshooting(),
        "COST_REPORT.md": generate_cost_report(),
        "UPGRADE_GUIDE.md": generate_upgrade_guide(),
        "CONTACTS.md": generate_contacts(),
    }

    results = {}
    for filename, content in docs.items():
        path = base / filename
        path.write_text(content, encoding="utf-8")
        results[filename] = str(path)
        logger.info(f"Generated: {path}")

    return results
