# Contributing to spidermax_room

Thanks for your interest! This document explains how to contribute effectively.

## Code of Conduct

Be respectful, constructive, and inclusive.

## How to Contribute

### Reporting Issues

1. Check if the issue already exists
2. Use a clear, descriptive title
3. Include steps to reproduce, expected vs actual behavior
4. Attach logs if relevant (`src/logs/unattended.log`)

### Submitting Changes

1. **Fork** the repository
2. **Create a branch**: `git checkout -b feature/your-feature` or `fix/your-fix`
3. **Write code** — keep it clean and focused
4. **Write tests** — ensure existing and new tests pass: `pytest tests/`
5. **Commit** — use clear commit messages:
   - `feat:` new feature
   - `fix:` bug fix
   - `docs:` documentation
   - `chore:` maintenance
6. **Push** and open a **Pull Request**

### Code Style

- Follow PEP 8
- Use type hints where applicable
- No unnecessary comments — let code speak for itself

### Commit Message Format

```
<type>(<scope>): <short description>

<optional body>
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

## Development Setup

```bash
git clone https://github.com/freeword26/Mini-spider.git
cd Mini-spider/spidermax_room
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -e ".[dev]"
```

## Architecture Overview

MAX ROOM 采用三层闭环架构:
- **调度层** — 22 项目 / 116 定时任务的 Cron 调度
- **事件层** — EventBus 发布/订阅解耦
- **执行层** — Worker 节点异步执行

See `docs/architecture.md` for details.
