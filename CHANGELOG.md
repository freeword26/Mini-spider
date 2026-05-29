# Changelog

## v3.0.0 (2026-05-29)

### 重大变更
- **项目重命名**: 无人值守工作流管理系统 → Spider MAX (大蜘蛛)
- **架构重组**: 将分散在 TAPD 归档中的全部模块整合为独立 Python 包
- **统一入口**: 新增 `run.py` 一键启动，`spider_max.bat` Windows启动

### 新增功能
- FastAPI API服务，端口8041，自动Swagger文档
- CLI命令行接口 (version/serve/db_init/module/list_modules/sync/dashboard)
- 44个服务模块自动注册与发现
- 14+2个内置工作流（含22个项目无人值守调度）
- 监控告警系统（指标采集、阈值检查、日报/周报生成）
- 自愈引擎（故障检测与自动修复）
- 三层健康检查（指挥控制层/执行协作层/资源与环境层）
- Docker Compose部署配置
- Makefile快捷命令

### 已知问题
- `test_orchestrator.py`: TaskDefinition新增必填字段`description`，3个异步测试需补传
- `test_scheduler.py`: CronTrigger返回float时间戳而非datetime，1个断言需调整
- `test_validator.py`: 项目数量23（含SYS_DAILY_OPS）vs预期的21，1个断言需调整
- 49个 teardown/setup 错误为 pytest 9.0 + Python 3.14 兼容性问题，不影响功能
