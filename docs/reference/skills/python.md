---
name: python
description: Write, refactor, and debug Python code with strict typing, modern idioms, and safety. Use when creating, reviewing, or fixing Python files, packages, scripts, or type annotations.
argument-hint: "[script path or 'audit' or 'typecheck']"
title: "Python Skill Reference"
aliases: ["python-skill"]
tags: ["skill", "language", "python"]
created: "2026-04-24"
updated: "2026-04-24"
---

# Python Skill

You are a Python expert who writes clean, typed, modern Python following these conventions.

## Mandatory Rules

- Target Python 3.12+ (use `match`, `X | Y` union types, `TypeAlias`, `datetime.UTC`)
- Use `uv` for package management and virtual environments
- Every function must have type hints on parameters and return types
- All modules must have a docstring at the top

## Critical Rules

### Type Safety

- Use `X | Y` for unions — never `Union[X, Y]` in new code
- Use `list[X]`, `dict[K, V]`, `set[X]` — never `List`, `Dict`, `Set` from `typing`
- Use `TypeAlias` for type aliases: `ConnectionId: TypeAlias = str`
- Use `typing.Protocol` for structural typing over abstract base classes
- Use `typing.override` for method overrides (Python 3.12+)
- Prefer `Final` for constants that should not be reassigned
- Use `TypedDict` for dictionaries with known structure instead of `Dict[str, Any]`
- Never use `Any` without a comment explaining why — prefer `object` or `Unknown`

### Error Handling

- Never use bare `except:` — always catch specific exceptions
- Use `except Exception` only when genuinely necessary, with a comment
- Use custom exception hierarchies: `class AppError(Exception): pass`
- Raise with `from` to preserve tracebacks: `raise ValueError(msg) from cause`
- Use `try/except/else/finally` fully when the pattern calls for it
- Never silently swallow exceptions — at minimum log them

### Project Structure

- Use `pyproject.toml` as the single source of project configuration
- Use `src/` layout for packages: `src/package_name/__init__.py`
- Use `__init__.py` to re-export public API — keep implementation in submodules
- Keep `if __name__ == "__main__"` blocks minimal — delegate to a function

### Modern Idioms

- Use `pathlib.Path` over `os.path` — always
- Use f-strings for all string formatting — never `.format()` or `%`
- Use `dataclasses.dataclass` for simple data containers, `pydantic.BaseModel` for validated data
- Use `@dataclass(frozen=True, slots=True)` for immutable value objects
- Use `enum.Enum` or `enum.StrEnum` (3.11+) for fixed sets of values
- Use `with` statements for all resource management (files, connections, locks)
- Use `collections.abc` for abstract base types — never `collections` directly
- Use walrus operator `:=` when it improves readability (e.g., in `while` loops, `if` filters)
- Use `functools.cache` instead of manual memoization

### Dependencies

- Pin dependencies in `pyproject.toml` with version ranges: `>=1.0,<2.0`
- Use `uv pip install` and `uv run` — never `pip install` directly
- Keep dev dependencies in `[project.optional-dependencies]` groups
- Never add a dependency when the stdlib suffices

## Linting / Formatting

```bash
# Format (replaces black)
ruff format .

# Lint (replaces flake8, isort, and more)
ruff check .

# Type check
mypy --strict src/
```

`ruff` configuration belongs in `pyproject.toml` under `[tool.ruff]`:

- `line-length = 88` (default, matches black)
- `target-version = "py312"`

## Anti-Patterns to Avoid

- Mutable default arguments: `def f(items=[])` — use `items: list[T] | None = None` then `items = items or []`
- `import *` — always use explicit imports
- `eval()` or `exec()` — never, no exceptions
- `type: ignore` without a specific code: `type: ignore[arg-type]`
- String concatenation in loops — use `"".join(parts)`
- `== True` / `== False` — use `if flag:` / `if not flag:`
- Manual iteration with index: `for i in range(len(x))` — use `enumerate()`
- Dictionary merge in loops: `{**a, **b}` repeatedly — build once
- `sys.path` manipulation — use proper package structure instead
- `__all__` that doesn't match what's actually exported
