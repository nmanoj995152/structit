# Contributing

Thanks for helping improve StructIt.

## Principles

- Keep all inference local and CPU-first.
- Do not add cloud AI APIs.
- Prefer FOSS dependencies.
- Keep code modular, typed, and testable.
- Add tests for new parsing, storage, or UI-facing behavior.

## Local Checks

Run these before opening a merge request:

```powershell
python -m ruff check src tests
python -m black --check src tests
python -m isort --check-only src tests
python -m mypy src
python -m pytest --cov=src --cov-report=term-missing
python -m bandit -r src
```

## Dependency Changes

When adding dependencies:

- Confirm they work offline after installation.
- Confirm they do not require CUDA or GPU packages.
- Confirm they are compatible with GPL-3.0-or-later distribution.
