# Spider MAX (大蜘蛛) v3.0.0

全栈项目管理与多Agent协同平台

## 定位

Spider MAX 是**项目立项后的全栈管理工具**。项目已经确认立项，进入执行阶段后，用它来做：

- **多Agent协同** — 多个智能体分工合作，自动推进项目
- **OKR拆解追踪** — 目标分解到关键结果，实时监控进度
- **DAG任务调度** — 有依赖关系的任务自动按拓扑序执行
- **数据分析仪表板** — 项目进度、健康度、完成率一目了然
- **无人值守运行** — 24×7自动调度、故障自愈、异常告警

它不是项目立项工具，而是**立项后的执行引擎**。

---

## 快速启动

### Windows — 双击运行

```
spider_max.bat
```

自动检查 Python 环境、安装依赖、显示 CLI 帮助。

### 命令行

```bash
# 安装依赖 + 可编辑安装
pip install -e .

# 启动 API 服务（默认端口 8041）
spider serve

# 或直接
python run.py
```

启动后访问 `http://localhost:8041/docs` 查看完整 API 文档。

---

## CLI 命令

```bash
spider version              # 版本信息
spider serve --port 8041    # 启动 API 服务
spider db_init              # 初始化数据库
spider dashboard            # 命令行仪表板（项目数/任务数/完成率）
spider list_modules         # 列出所有已注册的服务模块
spider module <name> info   # 查看模块详情
spider module <name> call --method=<func> --args='{}'  # 调用模块
spider sync                 # 全量数据同步
```

---

## 核心模块一览

| 模块 | 文件 | 作用 |
|---|---|---|
| **API服务** | `api/server.py` | FastAPI，统一入口，端口8041 |
| **编排调度器** | `orchestrator.py` | 5种协作模式：DAG/PMO/SOP/Blackboard/Meta |
| **工作流引擎** | `workflow_executor.py` | DAG执行、自动重试、熔断器 |
| **调度中心** | `scheduler.py` | Cron/Interval/Event 定时调度 |
| **事件总线** | `event_bus.py` | Agent间通信，支持内存和RabbitMQ |
| **模块注册** | `core/registry.py` | 44个服务模块自动发现与注册 |
| **插件管理** | `core/plugin_manager.py` | 插件安装/启动/停止/卸载 |
| **监控告警** | `monitoring.py` | 指标采集、阈值告警、日报周报 |
| **自愈引擎** | `self_healing.py` | 自动重启失败工作流、重新分配任务 |
| **验证器** | `unattended_validator.py` | 24×7可用性验证、六大冲突检测 |
| **报告生成** | `report_generator.py` | 自动生成项目报告 |
| **权限认证** | `auth_gateway.py` | 用户授权、权限边界 |
| **数据库** | `db/` | SQLite+SQLAlchemy，连接池 |
| **配置** | `config.py` | 系统/服务器/工作流/告警配置 |

---

## 内置工作流（14个）

| 工作流 | 触发 | 说明 |
|---|---|---|
| `wf_daily_ops` | Cron每日 | 每日运维巡检+报告 |
| `wf_001_data_sync` | Cron/Interval | 全量数据同步 |
| `wf_002_task_tracking` | Cron | 任务进度跟踪 |
| `wf_003_overdue_alert` | Cron | 逾期告警 |
| `wf_004_cicd` | Event | CI/CD流水线 |
| `wf_005_compliance` | Cron每日 | 合规审计 |
| `wf_006_backup` | Cron每日 | 数据备份 |
| `wf_007_git_sync` | Cron | Git仓库同步 |
| `wf_008_log_analysis` | Cron | 日志分析 |
| `wf_011_doc_slice` | Cron | 文档切片 |
| `wf_012_ctx_track` | Event | 上下文跟踪 |
| `wf_013_agent_collect` | Cron | Agent信息采集 |
| `wf_014_doc_archive` | Cron每日 | 文档归档 |
| `wf_lifecycle_scan` | Cron | 项目生命周期扫描 |
| `wf_okr_report` | Cron每日 | OKR进度报告 |

---

## API 接口

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/` | 服务状态 |
| GET | `/docs` | Swagger 文档 |
| GET | `/api/v1/health` | 健康检查 |
| GET | `/api/v1/dashboard` | 项目仪表板 |
| GET | `/api/v1/modules` | 模块列表 |
| GET | `/api/v1/modules/{name}` | 模块详情 |
| POST | `/api/v1/modules/{name}/load` | 加载模块 |
| GET | `/api/v1/workflows` | 工作流列表 |
| POST | `/api/v1/workflows` | 创建工作流 |
| POST | `/api/v1/workflows/{id}/execute` | 执行工作流 |
| GET | `/api/v1/executions/{id}` | 执行记录 |
| GET | `/api/v1/schedules` | 定时任务列表 |
| GET | `/api/v1/agents` | Agent列表 |
| POST | `/api/v1/permissions/check` | 权限检查 |
| POST | `/api/v1/permissions/grant` | 授权 |

---

## 项目结构

```
spider_max/                          ← 项目目录
├── spider_max/                      ← Python 主包（安装为 spider-max）
│   ├── api/                         ← FastAPI 路由层
│   │   ├── server.py               # 主入口，端口8041
│   │   ├── health.py               # /health
│   │   ├── dashboard.py            # /dashboard
│   │   ├── modules.py              # /modules CRUD
│   │   ├── permissions.py          # /permissions
│   │   ├── agents.py               # /agents
│   │   ├── workflows.py            # /workflows
│   │   ├── executions.py           # /executions
│   │   ├── schedules.py            # /schedules
│   │   └── store.py                # /store 数据查询
│   ├── cli/                         ← Click CLI
│   ├── core/                        ← 核心框架
│   │   ├── registry.py             # 模块注册中心
│   │   └── plugin_manager.py       # 插件生命周期
│   ├── agents/                      ← Agent 管理
│   ├── workflows/                   ← 14个内置工作流
│   ├── tests/                       ← 67个单元测试
│   ├── models.py                    ← 数据模型
│   ├── orchestrator.py              ← 编排调度器（5种模式）
│   ├── scheduler.py                 ← 调度中心
│   ├── event_bus.py                 ← 事件总线
│   ├── workflow_executor.py         ← 工作流执行器
│   ├── monitoring.py                ← 监控告警
│   ├── self_healing.py              ← 自愈引擎
│   ├── unattended_validator.py     ← 验证器
│   ├── report_generator.py         ← 报告生成
│   ├── auth_gateway.py              ← 权限认证
│   ├── file_access_layer.py         ← 文件访问
│   ├── config.py                    ← 配置
│   └── main.py                      ← FastAPI v2入口(端口5005)
├── db/                              ← 数据库
├── config/                          ← 规则文档 + Docker
├── run.py                           ← 一键启动入口
├── spider_max.bat                   ← Windows 双击启动
├── pyproject.toml                   ← 项目定义
├── Makefile / Makefile.bat          ← 快捷命令
└── CHANGELOG.md
```

---

## Make / Makefile.bat 快捷命令

```bash
# 开发模式
make validate          # 架构验证（输出健康分数）
make test              # 运行测试
make daily-ops         # 手动执行一次每日运维
```

---

## 技术栈

- Python 3.11+ / FastAPI / Uvicorn
- RabbitMQ (pika/aio-pika) / SQLite + SQLAlchemy
- croniter / Click / Rich / Prometheus Client
- Docker + docker-compose

---

## License

MIT
