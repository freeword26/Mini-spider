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

## Spider 系列全景

| 项目 | 角色 | 核心能力 | 状态 |
|---|---|---|---|
| **Spider MAX** | **立项后全栈项目管理** | OKR追踪、DAG任务调度、多Agent协同编排、监控告警、无人值守执行 | v3.0.0 已上线 |
| **Spider-X** | **后端Agent执行引擎** | Worker节点集群：serve起API、worker跑任务、RabbitMQ通信 | v1.0.0 已上线 |
| **mini_spider** | **多Agent协作框架** | 25个Agent角色、单Agent对话、多Agent会议、DAG工作流、黑板模式、项目看板（交互式，人在时用） | v3.0.0 已上线 |
| **spider_meta** | **生态元数据+监控** | 管理所有Spider项目的元数据，监控各Spider运行状态 | v0.5.0 开发中 |
| **spider_diary** | **日历提醒** | 日程管理、提醒 | v1.0.0 已上线 |

### 协作关系（不重叠）

```
你(人类)
  ├── 用 mini_spider ── 交互式多Agent协作（人在场）
  │     spider meet / spider team / spider workflow
  │
  └── 用 Spider MAX ── 自动化项目管理（人不在场）
        │
        ├── 调用 Spider-X Worker集群 执行具体任务
        ├── 通过 mini_spider 管道 采集数据
        └── 被 spider_meta 监控 运行状态
```

- **mini_spider** = 交互式协作工具（人驱动，即时对话/会议）
- **Spider MAX** = 自动化管理平台（系统驱动，自动调度/监控/自愈）
- **Spider-X** = Worker执行集群（实际干活的节点）
- 三者协作而非竞争，MAX是唯一的管理入口

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
spider version                              # 版本信息
spider serve --port 8041 --reload           # 启动 API 服务
spider db_init                              # 初始化数据库
spider dashboard                            # 命令行仪表板（项目数/任务数/完成率）
spider list_modules                         # 列出所有已注册的服务模块
spider module <name> info                   # 查看模块详情
spider module <name> call --method=<func>   # 调用模块函数
spider sync                                 # 全量数据同步
```

---

## 核心模块一览（16个）

| 模块 | 文件 | 作用 |
|---|---|---|
| **API服务** | `api/server.py` | FastAPI，统一入口，端口8041，14个路由 |
| **编排调度器** | `orchestrator.py` | 5种协作模式：DAG/PMO/SOP/Blackboard/Meta |
| **工作流引擎** | `workflow_executor.py` | DAG拓扑执行、自动重试、熔断器 |
| **调度中心** | `scheduler.py` | Cron/Interval/Event/OneTime 定时调度 |
| **事件总线** | `event_bus.py` | Agent间通信，支持内存和RabbitMQ |
| **模块注册** | `core/registry.py` | 44个服务模块自动发现与注册 |
| **插件管理** | `core/plugin_manager.py` | 插件安装/启动/停止/卸载 |
| **监控告警** | `monitoring.py` | 指标采集、阈值告警、日报周报、三层健康检查 |
| **自愈引擎** | `self_healing.py` | 自动重启失败工作流、重新分配超时任务 |
| **验证器** | `unattended_validator.py` | 24×7可用性验证、六大冲突检测 |
| **报告生成** | `report_generator.py` | 自动生成项目报告 |
| **权限认证** | `auth_gateway.py` | 用户授权、权限边界、关键操作确认 |
| **文件访问** | `file_access_layer.py` | 文件访问控制层 |
| **Agent调度** | `unattended_event_scheduler.py` | 22个项目无人值守调度 |
| **数据库** | `db/` | SQLite+SQLAlchemy，连接池 |
| **配置** | `config.py` | 系统/服务器/工作流/告警配置 |

---

## 内置工作流（15个）

| 工作流 | 触发 | 说明 |
|---|---|---|
| `wf_daily_ops` | Cron每日 | 每日运维巡检（系统/磁盘/内存/进程）+报告 |
| `wf_okr_report` | Cron每日 | OKR进度报告自动生成 |
| `wf_lifecycle_scan` | Cron | 项目生命周期扫描 |
| `wf_001_data_sync` | Cron/Interval | 数据同步（飞书→本地） |
| `wf_002_task_tracking` | Cron | 任务进度跟踪 |
| `wf_003_overdue_alert` | Cron | 逾期告警 |
| `wf_004_cicd` | Event(git_push) | CI/CD自动构建测试部署 |
| `wf_005_compliance` | Cron每日 | 合规审计 |
| `wf_006_backup` | Cron每日 | 数据备份 |
| `wf_007_git_sync` | Cron每日 | GitHub自动同步与备份 |
| `wf_008_log_analysis` | Cron | 日志分析 |
| `wf_011_doc_slice` | Cron | 文档切片 |
| `wf_012_ctx_track` | Event | 上下文跟踪 |
| `wf_013_agent_collect` | Cron | Agent信息采集 |
| `wf_014_doc_archive` | Cron每日 | 文档归档 |

---

## 5种编排模式

| 模式 | 说明 | 适用场景 |
|---|---|---|
| **DAG** | 有向无环图，按依赖关系并行执行 | 有依赖关系的任务链 |
| **PMO** | 项目经理主导，顺序执行 | 需要逐步确认的审批流 |
| **SOP** | 标准操作流程，严格按步骤 | 不可跳过的标准操作 |
| **Blackboard** | 共享黑板，多Agent协同贡献 | 多角色协作的头脑风暴 |
| **Meta** | 元认知反思，执行前先思考 | 需要智能决策的复杂任务 |

---

## API 接口（14个）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/` | 服务状态 |
| GET | `/docs` | Swagger 交互式文档 |
| GET | `/api/v1/health` | 健康检查 |
| GET | `/api/v1/health/ready` | 就绪检查 |
| GET | `/api/v1/health/live` | 存活检查 |
| GET | `/api/v1/dashboard` | 项目仪表板 |
| GET | `/api/v1/modules` | 模块列表 |
| GET | `/api/v1/modules/{name}` | 模块详情 |
| POST | `/api/v1/modules/{name}/load` | 加载模块 |
| GET | `/api/v1/workflows` | 工作流列表 |
| GET | `/api/v1/executions/{id}` | 执行记录 |
| GET | `/api/v1/schedules` | 定时任务列表 |
| POST | `/api/v1/permissions/check` | 权限检查 |
| POST | `/api/v1/permissions/grant` | 授权 |

---

## Docker 部署

### 构建镜像

```bash
docker build -t spider-max:3.0.0 .
```

### 快速启动（单容器）

```bash
docker run -d \
  --name spider-max \
  -p 8041:8041 \
  -v spider-data:/app/data \
  -v spider-logs:/app/logs \
  spider-max:3.0.0
```

### 完整部署（含 RabbitMQ）

```bash
cd config
cp .env.example .env
docker-compose up -d
```

完整部署包含3个服务：

| 服务 | 端口 | 说明 |
|---|---|---|
| spider-rabbitmq | 5672 / 15672 | 事件总线，管理面板 http://localhost:15672 |
| spider-max | 8041 | FastAPI 主服务 |
| spider-scheduler | 5005 | 调度器 + 监控 + 自愈 |

### Docker 验证

```bash
# 健康检查
docker exec spider-max curl -s http://localhost:8041/api/v1/health

# 查看日志
docker logs -f spider-max

# 停止
docker rm -f spider-max
```

---

## 项目结构

```
spider_max/                              ← 项目目录
├── spider_max/                          ← Python 主包（pip 安装为 spider-max）
│   ├── api/                             ← FastAPI 路由层 (14个接口)
│   │   ├── server.py                    # 主入口，端口8041
│   │   ├── health.py                    # /health 健康检查
│   │   ├── dashboard.py                 # /dashboard 仪表板
│   │   ├── modules.py                   # /modules 模块CRUD
│   │   ├── permissions.py               # /permissions 权限
│   │   ├── agents.py                    # /agents Agent管理
│   │   ├── workflows.py                 # /workflows 工作流
│   │   ├── executions.py                # /executions 执行记录
│   │   ├── schedules.py                 # /schedules 定时任务
│   │   └── store.py                     # /store 数据查询
│   ├── cli/                             ← Click CLI
│   │   ├── __init__.py                  # 命令定义
│   │   └── main.py                      # CLI入口
│   ├── core/                            ← 核心框架
│   │   ├── registry.py                  # 模块注册中心 (44个模块)
│   │   └── plugin_manager.py            # 插件生命周期管理
│   ├── agents/                          ← Agent管理
│   │   ├── registry.py                  # Agent注册表
│   │   └── schedules/                   # Agent排班调度
│   │       ├── daily_schedule.py        # 日排班
│   │       └── weekly_schedule.py       # 周排班
│   ├── workflows/                       ← 15个内置工作流
│   │   ├── wf_daily_ops.py              # 每日运维
│   │   ├── wf_okr_report.py             # OKR报告
│   │   ├── wf_lifecycle_scan.py         # 生命周期扫描
│   │   ├── wf_001_data_sync.py          # 数据同步
│   │   ├── wf_002_task_tracking.py      # 任务跟踪
│   │   ├── wf_003_overdue_alert.py      # 逾期告警
│   │   ├── wf_004_cicd.py               # CI/CD
│   │   ├── wf_005_compliance.py         # 合规审计
│   │   ├── wf_006_backup.py             # 数据备份
│   │   ├── wf_007_git_sync.py           # Git同步
│   │   ├── wf_008_log_analysis.py       # 日志分析
│   │   ├── wf_011_doc_slice.py          # 文档切片
│   │   ├── wf_012_ctx_track.py          # 上下文跟踪
│   │   ├── wf_013_agent_collect.py      # Agent采集
│   │   └── wf_014_doc_archive.py        # 文档归档
│   ├── tests/                           ← 单元测试 (67个)
│   ├── models.py                        ← 数据模型 (Workflow/Task/Execution/Agent)
│   ├── orchestrator.py                  ← 编排调度器 (5种模式)
│   ├── scheduler.py                     ← 调度中心 (Cron/Interval/Event/OneTime)
│   ├── event_bus.py                     ← 事件总线 (内存/RabbitMQ)
│   ├── workflow_executor.py             ← 工作流执行器 (DAG/重试/熔断)
│   ├── monitoring.py                    ← 监控告警 (指标/告警/日报周报)
│   ├── self_healing.py                  ← 自愈引擎
│   ├── unattended_validator.py         ← 验证器 (24×7可用性)
│   ├── unattended_event_scheduler.py   ← 22项目调度器
│   ├── report_generator.py             ← 报告生成
│   ├── auth_gateway.py                  ← 权限认证网关
│   ├── file_access_layer.py             ← 文件访问控制层
│   ├── astrbot_gateway_adapter.py       ← AstrBot网关适配器
│   ├── config.py                        ← 配置管理
│   └── main.py                          ← FastAPI v2入口 (端口5005)
├── config/                              ← 部署配置
│   ├── docker-compose.unattended.yml    # Docker编排
│   └── .env.example                     # 环境变量模板
├── db/                                  ← 数据库
│   ├── __init__.py                      # DatabaseManager
│   ├── pool.py                          # 连接池
│   └── migrations/001_initial.sql       # 初始Schema
├── Dockerfile                           ← Docker镜像定义
├── run.py                               ← 一键启动入口
├── spider_max.bat                       ← Windows双击启动
├── pyproject.toml                       ← 项目元数据+依赖
├── Makefile                             ← Make快捷命令 (Linux/Mac)
├── Makefile.bat                         ← Make快捷命令 (Windows)
├── metadata.json                        ← 项目元数据
├── CHANGELOG.md                         ← 版本日志
└── README.md                            ← 本文件
```

---

## Make / Makefile.bat 快捷命令

```bash
make dev          # 开发模式启动
make test         # 运行测试 (67个用例)
make validate     # 架构验证（输出健康分数/100）
make daily-ops    # 手动执行一次每日运维
make clean        # 清理临时文件
make info         # 项目信息
make lint         # 代码检查
make check        # 架构验证
```

Windows 对应：`make.bat test` / `make.bat validate` 等

---

## 技术栈

- **语言**: Python 3.11+
- **Web框架**: FastAPI + Uvicorn
- **消息队列**: RabbitMQ (pika / aio-pika)
- **定时调度**: croniter + schedule
- **终端UI**: Rich + Click
- **数据库**: SQLite（可切换 PostgreSQL via SQLAlchemy）
- **监控**: Prometheus Client
- **部署**: Docker + docker-compose

---

## 版本管理

### 版本号规则

采用语义化版本 `MAJOR.MINOR.PATCH`：

| 级别 | 含义 | 示例 |
|---|---|---|
| MAJOR | 重大重构/不兼容变更 | 2.x.x → 3.0.0 |
| MINOR | 新增功能/模块 | 3.0.x → 3.1.0 |
| PATCH | Bug修复/小优化 | 3.0.0 → 3.0.1 |

### 版本历史

| 版本 | 日期 | 说明 |
|---|---|---|
| v3.0.0 | 2026-05-29 | 正式版：合并全部模块，独立Python包，Docker部署，CI通过 |
| v2.x | — | 无人值守工作流系统阶段（已归档） |
| v1.x | — | TAPD任务执行中枢阶段（已归档） |

### 发布流程

```bash
# 1. 更新版本号（pyproject.toml / metadata.json）
# 2. 更新 CHANGELOG.md
# 3. 打标签
git tag -a v3.0.0 -m "Spider MAX v3.0.0 正式版"
# 4. 推送
git push origin main --tags
```

---

## License

MIT
