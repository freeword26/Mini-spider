# Contributing to spider_max

Thank you for your interest in contributing to spider_max (spider_max)! This document provides guidelines for contributing to the project.

## Code of Conduct

This project adheres to a code of conduct. By participating, you are expected to uphold this code.

## How to Contribute

### Reporting Bugs

1. Check if the issue already exists
2. Create a new issue with a clear title and description
3. Include steps to reproduce, expected behavior, and actual behavior
4. Attach relevant logs or screenshots

### Suggesting Features

1. Open an issue with the "enhancement" label
2. Describe the use case and expected behavior
3. Discuss implementation approach

### Pull Requests

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`pytest tests/ -v`)
5. Run linter (`ruff check spider_max/`)
6. Commit with clear messages
7. Push and create a Pull Request

## Development Setup

```bash
git clone https://github.com/your-org/spider-max.git
cd spider-max
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -e ".[dev,full]"
```

## Code Style

- Follow PEP 8
- Use type hints where appropriate
- No inline comments (self-documenting code)
- Maximum line length: 120 characters
- Use `ruff` for linting and formatting

## Module Development

To add a new service module:

1. Create `spider_max/services/your_module.py`
2. Register in `spider_max/core/registry.py`:
   ```python
   "your_module": ModuleCategory.CORE,  # or appropriate category
   ```
3. The module will be auto-discovered by the registry

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test
pytest tests/test_module.py -v

# With coverage
pytest tests/ --cov=spider_max --cov-report=html
```

## Commit Messages

Use conventional commit format:

```
feat: add new priority calculation algorithm
fix: resolve task allocation deadlock
docs: update API reference
refactor: simplify module registry
test: add tests for OKR tracker
```

## Release Process

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Create a git tag: `git tag v3.x.x`
4. Push tags: `git push --tags`
5. GitHub Actions will publish to PyPI

## Questions?

Open an issue with the "question" label or join our discussions.
