# Spider MAX (大蜘蛛) v3.0.0

全栈项目管理与多Agent协同平台

## 一句话说明

Spider MAX 是一个**自动化项目管理引擎** — 你把项目和工作流定义好，它自动调度执行、监控健康、故障自愈，7×24小时无人值守跑完整个项目生命周期。

---

## 核心概念

### 工作流 (Workflow)

由多个**任务(Task)** 组成的自动化流程。每个任务有执行者(Agent)、依赖关系、超时和重试策略。

```
示例：每日运维检查工作流
  → 检查系统状态 → 检查磁盘 → 检查内存 → 检查进程 → 检查项目 → 生成报告
```

### 编排模式 (Collaboration Mode)

5种工作流执行策略：

| 模式 | 说明 | 适用场景 |
|---|---|---|
| **DAG** | 有向无环图，按依赖关系并行执行 | 有依赖关系的任务链 |
| **PMO** | 项目经理主导，顺序执行 | 需要逐步确认的审批流 |
| **SOP** | 标准操作流程，严格按步骤 | 不可跳过的标准操作 |
| **Blackboard** | 共享黑板，多Agent协同贡献 | 多角色协作的头脑风暴 |
| **Meta** | 元认知反思，执行前先思考 | 需要智能决策的复杂任务 |

### 触发器 (Trigger)

工作流的启动时机：

| 类型 | 说明 |
|---|---|
| **Cron** | 定时触发，如每天8点 `"0 8 * * *"` |
| **Interval** | 间隔触发，如每3600秒 |
| **OneTime** | 一次性触发，指定时间点手动 |
| **Event** | 事件触发，订阅某个消息主题 |
| **Manual** | 手动触发 |

### 熔断器 (Circuit Breaker)

防止故障扩散的保护机制：
- **Closed(关闭)** — 正常运行，记录失败次数
- **Open(打开)** — 失败达到阈值，暂停执行，熔断所有请求
- **Half-Open(半开)** — 超时后尝试恢复，成功则关闭，失败则重新打开

### 事件总线 (EventBus)

Agent之间的通信通道，支持：
- **发布/订阅** — Agent 发布消息，订阅者自动收到
- **死信队列** — 处理失败的消息保存到死信队列
- **RabbitMQ** — 可选的消息队列后端
- **请求-回复** — 发送消息并等待回复

---

## 项目结构

```
spider_max/                          # 项目根目录
├── spider_max/                      # Python 主包
│   ├── api/                         # FastAPI API路由
│   │   ├── server.py               # FastAPI应用入口
│   │   ├── health.py               # 健康检查 /health
│   │   ├── dashboard.py            # 仪表板数据 /api/v1/dashboard
│   │   ├── modules.py              # 模块管理 /api/v1/modules
│   │   ├── permissions.py          # 权限管理 /api/v1/permissions
│   │   ├── agents.py               # Agent管理 /api/v1/agents
│   │   ├── workflows.py            # 工作流API /api/v1/workflows
│   │   ├── executions.py           # 执行记录 /api/v1/executions
│   │   ├── schedules.py            # 定时任务 /api/v1/schedules
│   │   └── store.py                # 数据查询 /api/v1/store
│   ├── cli/                         # 命令行接口
│   │   ├── __init__.py             # CLI命令定义
│   │   └── main.py                 # CLI入口
│   ├── core/                        # 核心框架
│   │   ├── registry.py             # 模块注册 (44个服务模块)
│   │   └── plugin_manager.py       # 插件管理
│   ├── agents/                      # Agent管理
│   │   ├── registry.py             # Agent注册表
│   │   └── schedules/              # Agent排班调度
│   ├── workflows/                   # 内置工作流 (14个)
│   │   ├── wf_001_data_sync.py     # 数据同步
│   │   ├── wf_002_task_tracking.py # 任务跟踪
│   │   ├── wf_003_overdue_alert.py # 逾期告警
│   │   ├── wf_004_cicd.py          # CI/CD
│   │   ├── wf_005_compliance.py    # 合规审计
│   │   ├── wf_006_backup.py        # 备份
│   │   ├── wf_007_git_sync.py      # Git同步
│   │   ├── wf_008_log_analysis.py  # 日志分析
│   │   ├── wf_011_doc_slice.py     # 文档切片
│   │   ├── wf_012_ctx_track.py     # 上下文跟踪
│   │   ├── wf_013_agent_collect.py # Agent采集
│   │   ├── wf_014_doc_archive.py   # 文档归档
│   │   ├── wf_daily_ops.py         # 每日运维 (核心)
│   │   ├── wf_lifecycle_scan.py    # 生命周期扫描
│   │   └── wf_okr_report.py        # OKR报告
│   ├── tests/                       # 单元测试 (67个用例)
│   ├── models.py                    # 数据模型 (Workflow/Task/Execution)
│   ├── orchestrator.py              # 编排调度器 (5种协作模式)
│   ├── scheduler.py                 # 工作流调度中心 (Cron/Interval/Event)
│   ├── event_bus.py                 # 事件总线 (内存/RabbitMQ)
│   ├── workflow_executor.py         # 工作流执行器 (DAG/重试/熔断)
│   ├── monitoring.py                # 监控告警 (指标/告警/报告)
│   ├── self_healing.py              # 自愈引擎
│   ├── auth_gateway.py              # 权限认证网关
│   ├── report_generator.py         # 报告生成器
│   ├── file_access_layer.py         # 文件访问层
│   ├── unattended_event_scheduler.py # 22项目无人值守调度
│   ├── unattended_validator.py     # 24×7运维验证器
│   ├── astrbot_gateway_adapter.py  # AstrBot网关适配器
│   └── config.py                    # 配置管理
├── db/                              # 数据库
│   ├── __init__.py                 # DatabaseManager
│   ├── pool.py                     # 连接池
│   └── migrations/001_initial.sql  # 初始Schema
├── config/                          # 项目配置
│   ├── RULE1_communication.md      # 通信规则
│   ├── RULE2_storage.md            # 存储规则
│   ├── RULE3_skill_lifecycle.md    # 技能生命周期规则
│   └── docker-compose.yml          # Docker编排
├── run.py                           # 一键启动入口
├── spider_max.bat                   # Windows启动脚本
├── pyproject.toml                   # 项目元数据+依赖
├── Makefile                         # Make快捷命令
└── metadata.json                    # 项目元数据
```

---

## 快速开始

### 1. 启动API服务

```bash
# 方式一：Python直接启动
python run.py

# 方式二：Windows双击
spider_max.bat

# 方式三：调用CLI命令
spider serve --port 8041
```

服务启动后自动打开 `http://localhost:8041/docs` (Swagger文档)

### 2. 使用CLI命令

```bash
spider version          # 查看版本信息
spider serve            # 启动API服务 (默认端口8041)
spider db_init          # 初始化数据库
spider list_modules     # 列出所有注册的44个服务模块
spider module <name> info     # 查看某模块详情
spider module <name> call --method=<func>  # 调用某模块函数
spider sync             # 执行全量数据同步
spider dashboard        # 命令行仪表板
```

### 3. API接口速查

启动服务后访问：

| 地址 | 用途 |
|---|---|
| `http://localhost:8041/` | 服务信息 |
| `http://localhost:8041/docs` | Swagger交互式API文档 |
| `GET /api/v1/health` | 健康检查 |
| `GET /api/v1/dashboard` | 仪表板概览 |
| `GET /api/v1/modules` | 注册模块列表 |
| `GET /api/v1/modules/{name}` | 模块详情 |
| `POST /api/v1/modules/{name}/load` | 加载模块 |
| `GET /api/v1/workflows` | 工作流列表 |
| `POST /api/v1/workflows` | 创建工作流 |
| `POST /api/v1/workflows/{id}/execute` | 执行工作流 |
| `GET /api/v1/executions/{id}` | 查看执行记录 |
| `GET /api/v1/schedules` | 定时任务列表 |
| `POST /api/v1/permissions/check` | 权限检查 |

---

## 14个内置工作流

| 工作流 | 触发方式 | 说明 |
|---|---|---|
| **wf_daily_ops** | Cron(每日) | 每日运维：检查系统/磁盘/内存/进程/项目，生成报告 |
| **wf_001_data_sync** | Cron/Interval | 全量数据同步 |
| **wf_002_task_tracking** | Cron | 任务进度跟踪 |
| **wf_003_overdue_alert** | Cron | 逾期任务告警 |
| **wf_004_cicd** | Event | CI/CD流水线 |
| **wf_005_compliance** | Cron(每日) | 合规审计 |
| **wf_006_backup** | Cron(每日) | 数据备份 |
| **wf_007_git_sync** | Cron | Git仓库同步 |
| **wf_008_log_analysis** | Cron | 日志分析 |
| **wf_009_lifecycle_scan** | Cron(每日) | 项目生命周期扫描 |
| **wf_010_okr_report** | Cron(每日) | OKR进度报告 |
| **wf_011_doc_slice** | Cron | 文档切片 |
| **wf_012_ctx_track** | Event | 上下文跟踪 |
| **wf_013_agent_collect** | Cron | Agent信息采集 |
| **wf_014_doc_archive** | Cron(每日) | 文档归档 |

---

## 22个无人值守项目

系统预置22个项目的全自动调度，分三层：

- **指挥控制层** (P001-P006) — 6个项目，目标效率90%
- **执行协作层** (P007-P010) — 4个项目，目标完成率85%
- **资源与环境层** (P011-P022) — 12个项目，目标可用性99%

---

## Docker部署

```bash
cd config
docker-compose -f docker-compose.unattended.yml up -d
```

---

## 常用Make命令

```bash
make dev          # 开发模式启动
make test         # 运行测试
make lint         # 代码检查
make check        # 架构验证
make clean        # 清理临时文件
make info         # 项目信息
```

---

## 测试

```bash
# 运行全部测试
pytest spider_max/tests/ -v

# 运行特定测试
pytest spider_max/tests/test_event_bus.py -v
pytest spider_max/tests/test_scheduler.py -v
```

---

## 技术栈

- **语言**: Python 3.11+
- **Web框架**: FastAPI + Uvicorn
- **消息队列**: RabbitMQ (pika/aio-pika)
- **定时调度**: croniter + APScheduler
- **终端UI**: Rich + Click
- **数据库**: SQLite (可切换PostgreSQL via SQLAlchemy)
- **监控**: Prometheus Client
- **部署**: Docker + docker-compose

---

## License

MIT
