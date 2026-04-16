# OCD — Obsessive Claude Developer

A Claude Code environment with a personal knowledge base compiled from AI conversations.

Inspired by [Karpathy's LLM KB](https://github.com/karpathy/llm-knowledge-base) architecture: daily conversation logs are the source, compiled knowledge articles are the executable.

## Structure

```
.agent/           Data — daily logs, knowledge base, state  (isolated via nested .gitignore)
.claude/          Code — scripts, hooks, skills, venv, pyproject.toml
```

## Eight Standards

1. Consistent Defaults
1. Defense in Depth
1. Deterministic Ordering
1. Minimal Surface Area
1. No Dead Code
1. Progressive Simplification
1. Single Source of Truth
1. Structural Honesty

## Knowledge Pipeline

```
SessionStart → inject KB index + recent log into context
SessionEnd   → extract transcript → spawn flush.py → append to daily log
PreCompact   → extract transcript → spawn flush.py (safety net before compaction)
flush.py     → LLM extraction → daily log → maybe trigger compile.py
compile.py   → daily logs → knowledge articles (concepts, connections, index, log)
```

## Scripts

All scripts live in `.claude/scripts/` and run via `uv` from the `.claude/` directory:

| Script | Purpose |
|--------|---------|
| `compile.py` | Daily logs → knowledge articles (LLM compiler) |
| `config.py` | Path constants and shared configuration |
| `flush.py` | Extract knowledge from session context (background) |
| `lint.py` | Structural + LLM contradiction checks on knowledge base |
| `query.py` | Index-guided knowledge base search |
| `utils.py` | Shared utilities (hashing, parsing, I/O) |

```bash
uv --directory .claude run python scripts/compile.py                 # compile new/changed logs
uv --directory .claude run python scripts/compile.py --all            # force recompile
uv --directory .claude run python scripts/compile.py --file <path>  # compile specific log
uv --directory .claude run python scripts/lint.py                    # full lint (structural + LLM)
uv --directory .claude run python scripts/lint.py --structural-only  # skip LLM checks
uv --directory .claude run python scripts/query.py "question"        # query the KB
uv --directory .claude run python scripts/query.py "q" --file-back   # query + file answer
```

Hooks use the same pattern: `uv --directory .claude run python hooks/<hook>.py`

The Python venv is at `.claude/.venv/`. Dependencies are managed in `.claude/pyproject.toml`.

## Hooks

| Hook | Trigger | Purpose |
|------|---------|---------|
| `session-start.py` | SessionStart | Inject KB index + recent log as context |
| `pre-compact.py` | PreCompact | Save context before auto-compaction discards it |
| `session-end.py` | SessionEnd | Capture transcript → spawn flush.py |
| `lint-work.py --edit` | PostToolUse (Write|Edit) | Lint edited files, report missing linters |
| `lint-work.py --commit` | PreToolUse (Bash: git commit) | Lint staged files before commit |

`hookslib.py` is the shared utility library. It imports path constants from `scripts/config.py`.

## Skills

Each skill in `.claude/skills/` enforces OCD standards with strict type safety, custom error hierarchies, hard prohibitions, and zero-tolerance linting gates.

| Skill | Description |
|-------|-------------|
| `bash` | `set -euo pipefail` mandatory, `shellcheck` zero-warnings gate. No unquoted expansions. |
| `cpp` | C++17 minimum, smart pointers only, `#pragma once` headers, CMake. No raw `new`/`delete`. |
| `csharp` | C# 10+ / .NET 8+, nullable reference types, file-scoped namespaces. No legacy collections. |
| `docker` | Multi-stage builds, pinned base image digests. No `latest` tags in production. |
| `git` | Conventional Commits, linear rebase history. Every branch has a purpose. |
| `go` | Go 1.22+, `gofmt` commit gate, doc comments on all exports. No `panic` in library code. |
| `java` | Java 17+, `final` by default, records, sealed classes, Javadoc on publics. No `System.out` in production. |
| `kubernetes` | Resource limits, liveness/readiness probes, `runAsNonRoot`, `readOnlyRootFilesystem`. No unbounded pods. |
| `ocd` | Meta-standard: reviews, refactors, creates code against the Eight Standards. Every line must earn its existence. |
| `php` | PHP 8.1+, `declare(strict_types=1)`, Composer, PSR-12. No legacy patterns. |
| `python` | Python 3.10+, strict type hints, `uv` packaging, `ruff` commit gate. No bare `except`, no `Any`. |
| `ruby` | Ruby 3.1+, `frozen_string_literal: true`, Bundler, `rubocop` zero-offense gate. No unfrozen strings. |
| `rust` | Edition 2021+, `cargo fmt` + `cargo clippy -- -D warnings` commit gates. No `unsafe` without safety comment. |
| `typescript` | TypeScript 5.x, `strict: true`, `pnpm`, explicit return types. No `any` — use `unknown`. |

## Protected Files

Settings in `.claude/settings.json` deny Claude from modifying infrastructure files via Edit, Write, or Bash. New hooks and scripts can still be created — only the existing ones are locked:

- All 5 hooks (`hooks/*.py`)
- All 6 scripts (`scripts/*.py`)
- `pyproject.toml` and `settings.json`

To modify protected files, remove the deny rule in `settings.json` first.
