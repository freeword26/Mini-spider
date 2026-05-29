# Changelog

All notable changes to spider_max will be documented in this file.

## [3.0.0] - 2026-05-28

### Added
- 47 service modules covering OKR, project management, task management, agents, skills, workflows, data pipeline, DevOps, PMO, knowledge, messaging, and monitoring
- Module registry with auto-discovery for 44 registered modules
- Plugin manager with lifecycle management and hook system
- FastAPI API server with health checks, dashboard, and module management
- Click CLI with 6 commands (version, serve, dashboard, list-modules, db-init, sync)
- Database migrations for 23+ tables
- Comprehensive documentation (README, whitepaper, quickstart guide, module reference)
- Docker support for 13 project services
- Cross-repo collaboration protocol
- Distributed tracing system
- Chaos engineering platform
- Agile kanban and sprint planning
- Knowledge indexing and search
- Message queue management
- Service mesh foundation

### Technical Details
- Python 3.11+ required
- FastAPI + SQLAlchemy + Click + Rich
- SQLite (default), PostgreSQL (optional)
- RabbitMQ via aio-pika
- Prometheus + Grafana for monitoring
