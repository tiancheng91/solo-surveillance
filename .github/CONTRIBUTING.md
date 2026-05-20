# Contributing to solo-surveillance

Thanks for your interest in contributing! This document covers guidelines for contributing to the project.

## Development Setup

```bash
# Clone the repository
git clone https://github.com/tiancheng91/solo-surveillance.git
cd solo-surveillance

# Create virtual environment and install dependencies
uv sync

# Install optional LLM dependencies (if needed)
uv sync --group llm
```

## Code Style

- Python 3.11+ with type hints
- Follow existing patterns in the codebase
- Use `ruff` or similar linter for consistent formatting
- No auto-commit/push please — keep commit control manual

## Testing

```bash
# Run all non-integration tests
uv run pytest -v --tb=short -m "not slow"

# Run all tests (including integration tests that require API keys)
uv run pytest -v
```

Tests are in the `tests/` directory. When adding new features, please include tests.

## Pull Request Guidelines

1. Create a feature branch from `dev`
2. Keep changes focused — one feature/fix per PR
3. Update `CHANGELOG.md` if adding notable functionality
4. Update `docs/` if changing configuration or behavior
5. Ensure existing tests pass before submitting

## Detector Extension

To add a new detector, see [docs/scenarios.md](docs/scenarios.md) for the extension pattern.

## Configuration Changes

If your PR modifies configuration keys or behavior:
- Update `config.example.yaml`
- Update `docs/configuration.md`
- Update the architecture table in `README.md` if modules change

## Reporting Issues

Use the GitHub issue tracker. Include:
- Your `config.yaml` (redact passwords/URLs)
- Relevant log output (`solo-surveillance -v`)
- Steps to reproduce

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
