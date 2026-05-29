# spider_max (spider_max)

**Full-Stack Project Management & Multi-Agent Collaboration Platform**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

spider_max is a full-stack project management and multi-agent collaboration platform that integrates 47 service modules, 200+ API endpoints, and 23 database tables into a unified package.

## Features

- **OKR Engine** — Weighted priority scoring, progress tracking, trend analysis
- **Project Lifecycle** — State machine, health evaluation, cross-repo collaboration
- **Task Management** — Smart allocation, DAG dependency validation, Kanban/Gantt views
- **Agent System** — Heartbeat monitoring, load balancing, auto-scaling
- **Skill System** — 7-dimension model, version control, recommendation engine
- **Workflow Engine** — Reverse workflow, DAG orchestration, template library
- **Data Pipeline** — Multi-source collection, ETL engine, quality monitoring
- **DevOps** — Chaos engineering, auto-deployment, rollback management
- **PMO** — Portfolio management, agile kanban, sprint planning, defect tracking
- **Knowledge** — Full-text search, knowledge graph, report generation
- **Messaging** — Message queue, event consumers, distributed tracing
- **Monitoring** — Health checks, self-healing, service mesh

## Quick Start

```bash
# Install
pip install spider-max

# Initialize database
spider db-init

# Start API server
spider serve

# View dashboard
spider dashboard
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `spider version` | Show version info |
| `spider serve` | Start API server (port 8041) |
| `spider dashboard` | Show system dashboard |
| `spider list-modules` | List all 44 service modules |
| `spider db-init` | Initialize database |
| `spider sync` | Sync data from sources |

## API Documentation

After starting the server, visit `http://localhost:8041/docs` for Swagger UI.

## Architecture

```
Command & Control Layer
  Meta-Agent | DAG Manager | Watchdog | OKR Engine | Permissions

Execution & Collaboration Layer
  Worker Cluster | Workflow Engine | Skill System | Message Queue | Task Manager

Resource & Environment Layer
  Global State | Database (23 tables) | Knowledge Index | Monitoring | DevOps
```

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy
- **Database**: SQLite (default), PostgreSQL (optional)
- **Message Queue**: RabbitMQ (via aio-pika)
- **Monitoring**: Prometheus + Grafana
- **Container**: Docker + Docker Compose

## Project Structure

```
spider_max/
├── core/           # Module registry, plugin manager, permissions
├── api/            # FastAPI routes (health, dashboard, modules, permissions)
├── cli/            # Click CLI (6 commands)
├── db/             # Database manager, connection pool, migrations
├── services/       # 47 service modules (auto-discovered)
├── plugins/        # Plugin directory
├── monitoring/     # Distributed tracing, health checks
├── data_pipeline/  # ETL, data collection, quality monitoring
├── workflows/      # Workflow templates, DAG definitions
└── docs/           # Technical documentation
```

## Configuration

Environment variables (`.env` file):

```env
SPIDER_HOST=0.0.0.0
SPIDER_PORT=8041
SPIDER_DB_PATH=data/spider.db
SPIDER_LOG_LEVEL=INFO
SPIDER_REDIS_URL=redis://localhost:6379/0
SPIDER_RABBITMQ_URL=amqp://guest:guest@localhost:5672/
```

## Development

```bash
# Clone
git clone https://github.com/your-org/spider-max.git
cd spider-max

# Install in dev mode
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Lint
ruff check spider_max/
mypy spider_max/
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

[MIT License](LICENSE)
