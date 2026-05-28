# Contributing

Contributions are welcome! Here's how to get started.

## Development setup

```bash
git clone https://github.com/your-username/context-renderer.git
cd context-renderer

# Install in editable mode with dev extras
pip install -e ".[dev]"
```

## Running tests

```bash
pytest
```

## Code style

This project uses [ruff](https://github.com/astral-sh/ruff) for linting:

```bash
ruff check .
ruff format .
```

## Adding a new connector

1. Create `context_renderer/connectors/{name}_connector.py`
2. Implement the same interface as `MSSQLConnector` (`.get_engine()`, `.test_connection()`, `.close()`)
3. Export it from `context_renderer/__init__.py`
4. Add an example notebook under `notebooks/`

## Submitting a PR

- Keep PRs focused on a single change
- Add or update tests when relevant
- Update the README if you add features
