# Spider Max (大蜘蛛) v3.0.0

全栈项目管理与多Agent协同平台

## 项目概述

Spider Max 是一个全栈项目管理系统，支持多Agent智能体协同工作，集成 OKR 管理、DAG 任务调度、数据分析等功能。

- **版本**: 3.0.0
- **端口**: 8041
- **模块数**: 47
- **API 接口**: 200+
- **数据库表**: 23

## 技术栈

- **语言**: Python 3.10+
- **Web 框架**: FastAPI + Uvicorn
- **消息队列**: RabbitMQ (pika)
- **终端 UI**: Rich
- **CLI**: Click

## 快速开始

### Windows

```bat
spider_max.bat
```

### 手动启动

```bash
pip install -r requirements.txt
python run.py
```

### CLI 命令

| 命令 | 说明 |
|---|---|
| `spider-max start` | 启动全套服务 |
| `spider-max status` | 查看系统状态 |
| `spider-max validate` | 架构验证 |
| `spider-max agents` | 查看 Agent 注册表 |
| `spider-max schedule` | 调度器状态 |

## 项目状态

| 里程碑 | 状态 | 日期 |
|---|---|---|
| 核心架构 | ✅ 完成 | 2026-05-20 |
| 服务模块 | ✅ 完成 | 2026-05-22 |
| API 接口 | ✅ 完成 | 2026-05-24 |
| 数据迁移 | ✅ 完成 | 2026-05-26 |
| 上线发布 | ✅ 完成 | 2026-05-27 |

健康度评分: **92/100**

## License

MIT
