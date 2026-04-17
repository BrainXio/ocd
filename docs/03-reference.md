---
title: Reference
aliases: [reference, api, specs, tables]
tags: [reference]
created: 2026-04-17
updated: 2026-04-17
---

All lookup tables, schemas, and specifications in one place. Dry, authoritative, complete.

## Skill Registry

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
| `python` | Python 3.12+, strict type hints, `uv` packaging, `ruff` commit gate. No bare `except`, no `Any`. |
| `ruby` | Ruby 3.1+, `frozen_string_literal: true`, Bundler, `rubocop` zero-offense gate. No unfrozen strings. |
| `rust` | Edition 2021+, `cargo fmt` + `cargo clippy -- -D warnings` commit gates. No `unsafe` without safety comment. |
| `typescript` | TypeScript 5.x, `strict: true`, `pnpm`, explicit return types. No `any` — use `unknown`. |

All skills live in `.claude/skills/<name>/SKILL.md`.

## Subagent Registry

| Agent | Model | Tools | Purpose |
|-------|-------|-------|---------|
| `ci-drift` | haiku | Glob, Grep, Read | Detect CI drift: compare local config vs CI workflow |
| `dead-code-hunter` | haiku | Glob, Grep, Read | Find dead code: unused functions, variables, configs |
| `dependency-auditor` | haiku | Bash, Read, Glob, Grep | Audit Python dependencies: unused, conflicting, missing |
| `docstring-enforcer` | haiku | Grep, Read, Glob | Check docstring coverage: missing, inconsistent, public API |
| `exception-auditor` | haiku | Grep, Read, Glob | Audit exception handling: bare excepts, broad catches |
| `hook-coverage` | haiku | Bash, Read, Glob | Verify hook coverage: symlinks, executables, CI parity |
| `hook-integrity` | haiku | Bash, Read, Glob | Verify hook chain integrity: symlinks, scripts, patterns |
| `lint-status` | haiku | Bash, Glob | Run linters, report triad: errors, clean, missing |

All agents live in `.claude/agents/<name>.md`.

### Agent Frontmatter Schema

| Field | Required | Description |
|-------|----------|-------------|
| `name` | yes | Agent identifier (matches filename without `.md`) |
| `description` | yes | One-line purpose (quote values containing colons) |
| `tools` | yes | Comma-separated list of tools the agent can use |
| `model` | no | Model to use (defaults to parent model). Options: `haiku`, `sonnet`, `opus` |

Example:

```yaml
---
name: lint-status
description: 'Run linters and report: errors, clean, missing'
tools: Bash, Glob
model: haiku
---
```

## Claude Code Hooks

| Hook | Trigger | Purpose |
|------|---------|---------|
| `session-start.py` | SessionStart | Inject KB index + recent log as context |
| `pre-compact.py` | PreCompact | Save context before auto-compaction discards it |
| `session-end.py` | SessionEnd | Capture transcript → spawn flush.py |
| `lint-work.py --edit` | PostToolUse (Write|Edit) | Lint edited files, report missing linters |
| `lint-work.py --commit` | PreToolUse (Bash: git commit) | Lint staged files before commit |

### Hook Configuration Schema

Hooks are declared in `.claude/settings.json` under the `hooks` key:

| Field | Required | Description |
|-------|----------|-------------|
| `matcher` | yes | Tool event pattern (e.g., `Write|Edit`, `Bash`) |
| `if` | no | Conditional filter (e.g., `Bash(git commit*)`). Note: `if` is a YAML reserved word — some parsers require quoting |
| `type` | yes | Currently only `command` |
| `command` | yes | Shell command to run |
| `timeout` | yes | Maximum execution time in seconds |

### Hook Stdin JSON

Hooks receive a JSON object on stdin:

```json
{
  "session_id": "string",
  "transcript_path": "string (path to JSONL transcript)",
  "source": "string"
}
```

### hookslib.py API

| Function | Purpose |
|----------|---------|
| `read_stdin()` | Parse JSON from stdin (includes Windows backslash fix) |
| `extract_conversation_context(path)` | Read JSONL transcript, extract last 30 turns as markdown, capped at 15,000 chars |
| `spawn_flush(context_file, session_id)` | Launch flush.py as detached background process |
| `write_context_file(session_id, context, prefix)` | Write context to `.agent/.state/{prefix}-{session_id}-{timestamp}.md` |

## Git Hooks

| Hook | Purpose |
|------|---------|
| `pre-commit` | Block commits on `main` branch |
| `commit-msg` | Reject AI attribution in commit messages |

### AI Attribution Patterns

Single source of truth: `.claude/scripts/ai-patterns.txt`

| Pattern | Matches |
|---------|---------|
| `^Co-Authored-By:` | Standard git co-author trailer |
| `^Generated (with\|by\|using)` | "Generated with/by/using" attribution |
| `^\[AI(-generated)?\]` | `[AI]` or `[AI-generated]` tags |

Git hooks are installed as symlinks: `.git/hooks/<hook>` → `.claude/hooks/<hook>`. Run `bash .claude/scripts/setup-hooks.sh` after cloning.

## Scripts

| Script | Purpose |
|--------|---------|
| `compile.py` | Daily logs → knowledge articles (LLM compiler) |
| `config.py` | Path constants and shared configuration |
| `flush.py` | Extract knowledge from session context (background) |
| `lint.py` | Structural + LLM contradiction checks on knowledge base |
| `query.py` | Index-guided knowledge base search |
| `utils.py` | Shared utilities (hashing, parsing, I/O) |

All scripts live in `.claude/scripts/` and run via `uv --directory .claude run python scripts/<script>`.

## CI Pipeline

| Stage | Job | Tool | Trigger |
|-------|-----|------|---------|
| 1 (gate) | `check-commit-messages` | grep (reads `ai-patterns.txt`) | push only |
| 2 (parallel) | `lint-yaml` | yamllint | all |
| 2 (parallel) | `lint-shell` | shellcheck | all |
| 2 (parallel) | `lint-markdown` | mdformat | all |
| 3 (after 1+2) | `lint-python` | ruff + mypy | all |

Concurrency: `cancel-in-progress: true` per ref. Permissions: `contents: read` only. Branch protection on `main` requires passing CI, linear history, and resolved conversations.

## Protected Files

Deny rules in `.claude/settings.json` block Claude from modifying infrastructure files:

| Surface | Pattern | What it blocks |
|---------|---------|----------------|
| `Edit(path)` | Edit tool on matching files | Direct file modifications |
| `Write(path)` | Write tool on matching files | Full file overwrites |
| `Bash(rm *:path)` | `rm` commands targeting matching paths | Deletion via shell |

Protected files (paths relative to `.claude/`):

- `hooks/commit-msg`, `hooks/hookslib.py`, `hooks/pre-commit`, `hooks/pre-compact.py`, `hooks/session-end.py`, `hooks/session-start.py`
- `scripts/compile.py`, `scripts/config.py`, `scripts/flush.py`, `scripts/lint.py`, `scripts/query.py`, `scripts/setup-hooks.sh`, `scripts/utils.py`
- `pyproject.toml`

## Pipeline Constants

| Constant | Value | Where |
|----------|-------|-------|
| Max context chars (session start) | 20,000 | `session-start.py` |
| Max flush turns | 30 | `config.py` |
| Max flush context chars | 15,000 | `config.py` |
| Min turns (session end) | 1 | `config.py` |
| Min turns (pre-compact) | 5 | `config.py` |
| Flush dedup window | 60 seconds | `flush.py` |
| Auto-compile trigger time | 18:00+ local | `flush.py` |

## Pipeline Commands

```bash
uv --directory .claude run python scripts/compile.py                 # compile new/changed logs
uv --directory .claude run python scripts/compile.py --all            # force recompile
uv --directory .claude run python scripts/compile.py --file <path>  # compile specific log
uv --directory .claude run python scripts/lint.py                    # full lint (structural + LLM)
uv --directory .claude run python scripts/lint.py --structural-only  # skip LLM checks
uv --directory .claude run python scripts/query.py "question"        # query the KB
uv --directory .claude run python scripts/query.py "q" --file-back   # query + file answer
```
