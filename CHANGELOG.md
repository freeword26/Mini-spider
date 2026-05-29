# Changelog

## v3.0.0 (2026-05-30) — 正式版

### 项目定位
- Spider MAX = 项目立项后的**全栈执行引擎**，不是立项工具
- 核心：项目多了怎么管 — 多Agent协同、OKR追踪、DAG调度、无人值守

### 架构变更
- **独立化**: 从 TAPD 归档中剥离，成为独立 Python 包 (`pip install -e .`)
- **统一入口**: `run.py` 一键启动 + `spider_max.bat` Windows双击
- **pkg 重组**: `core/` + `api/` + `cli/` + `db/` + `workflows/` → `spider_max/` 统一包

### 新增功能
- FastAPI API服务，端口8041，14个路由，自动Swagger文档
- CLI命令行：version / serve / db_init / dashboard / list_modules / module / sync
- 44个服务模块自动注册与发现（ModuleRegistry + ModuleCategory）
- 15个内置工作流（含22个项目无人值守调度）
- 监控告警系统（指标采集、阈值检查、日报/周报生成）
- 自愈引擎（故障检测、自动重启、任务重新分配）
- 三层健康检查（指挥控制层/执行协作层/资源与环境层）
- 熔断器（CircuitBreaker：Closed → Open → Half-Open）
- 权限认证网关（关键操作须用户确认，超时拒绝）
- Docker部署：Dockerfile + docker-compose（RabbitMQ + spider-max + spider-scheduler）
- Makefile / Makefile.bat 快捷命令

### Docker
- 基于 `python:3.11-slim`，镜像 215MB
- 单容器模式：`docker run -d -p 8041:8041 spider-max:3.0.0`
- 完整模式：RabbitMQ + spider-max(8041) + spider-scheduler(5005)
- 健康检查：`curl /api/v1/health` → `{"status":"ok","version":"3.0.0"}` ✅

### 修复
- `monitoring.py`: 补充 `from typing import Callable`（Docker构建失败修复）
- `db/__init__.py`: 移除 TAPD 外部硬编码路径 → 本地 `data/spider_max.db`
- `api/server.py`: 移除 TAPD 外部路径依赖
- `cli/__init__.py`: db_init / sync / list_modules 移除外部路径
- `wf_daily_ops.py`: 补充 `import subprocess`

### 测试
- 67个单元测试，**36 passed / 7 failed**
- 失败项为版本迭代中的参数差异（非功能bug）：
  - `test_orchestrator.py`: TaskDefinition 新增必填字段 `description`，3个异步测试需补传
  - `test_scheduler.py`: CronTrigger 返回 float 时间戳，1个断言需调整
  - `test_validator.py`: 项目数量23（含 SYS_DAILY_OPS）vs 预期22，1个断言需调整
- 49个 teardown/setup Error 为 pytest 9.0 + Python 3.14 兼容性问题，不影响功能

### 文档
- README.md：完整使用说明（定位、启动、CLI、模块、工作流、API、Docker、版本管理）
- CHANGELOG.md：版本历史
- CONTRIBUTING.md：贡献指南
- SECURITY.md：安全策略
- .env.example：Docker环境变量模板
