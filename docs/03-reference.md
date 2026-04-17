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
| `css` | CSS Grid/Flexbox layouts, Custom Properties for tokens, BEM or utility-first. No `!important` except utilities. |
| `docker` | Multi-stage builds, pinned base image digests. No `latest` tags in production. |
| `git` | Conventional Commits, linear rebase history. Every branch has a purpose. |
| `go` | Go 1.22+, `gofmt` commit gate, doc comments on all exports. No `panic` in library code. |
| `html` | HTML5 semantic elements, accessibility attributes, keyboard navigation. No `<div>` soup. |
| `java` | Java 17+, `final` by default, records, sealed classes, Javadoc on publics. No `System.out` in production. |
| `js` | ES2022+, strict equality, `const`/`let`, ESLint zero-warnings gate. No `var`, no `==`. |
| `json` | RFC 8259 compliance, 2-space indent, schema validation. No trailing commas, no comments in `.json`. |
| `kubernetes` | Resource limits, liveness/readiness probes, `runAsNonRoot`, `readOnlyRootFilesystem`. No unbounded pods. |
| `markdown` | CommonMark spec, `mdformat` gate, frontmatter preservation. No inline HTML for layout. |
| `ocd` | Meta-standard: reviews, refactors, creates code against the Eight Standards. Every line must earn its existence. |
| `php` | PHP 8.1+, `declare(strict_types=1)`, Composer, PSR-12. No legacy patterns. |
| `python` | Python 3.12+, strict type hints, `uv` packaging, `ruff` commit gate. No bare `except`, no `Any`. |
| `ruby` | Ruby 3.1+, `frozen_string_literal: true`, Bundler, `rubocop` zero-offense gate. No unfrozen strings. |
| `rust` | Edition 2021+, `cargo fmt` + `cargo clippy -- -D warnings` commit gates. No `unsafe` without safety comment. |
| `sql` | Parameterized queries, explicit JOINs, `NOT NULL` constraints. No `SELECT *`, no comma joins. |
| `swift` | Swift 5.9+, strict concurrency, `async`/`await`, SwiftLint zero-warnings gate. No force-unwrap outside tests. |
| `terraform` | HCL2, remote state with locking, `sensitive = true` for secrets, module composition. No hardcoded secrets. |
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

| Hook | Entry Point | Trigger | Purpose |
|------|-------------|---------|---------|
| SessionStart | `ocd-session-start` | SessionStart | Inject KB index + recent log as context |
| PreCompact | `ocd-pre-compact` | PreCompact | Save context before auto-compaction discards it |
| SessionEnd | `ocd-session-end` | SessionEnd | Capture transcript → spawn flush |
| Lint (edit) | `ocd-lint-work --edit` | PostToolUse (Write|Edit) | Lint edited files, report missing linters |
| Lint (commit) | `ocd-lint-work --commit` | PreToolUse (Bash: git commit) | Lint staged files before commit |

All Python hooks are installed as entry points via `pyproject.toml` `[project.scripts]`. Source code lives in `src/ocd/hooks/`.

### Hook Configuration Schema

Hooks are declared in `.claude/settings.json` under the `hooks` key:

| Field | Required | Description |
|-------|----------|-------------|
| `matcher` | yes | Tool event pattern (e.g., `Write|Edit`, `Bash`) |
| `if` | no | Conditional filter (e.g., `Bash(git commit*)`). Note: `if` is a YAML reserved word — some parsers require quoting |
| `type` | yes | Currently only `command` |
| `command` | yes | Shell command to run (entry point name) |
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

### hookslib API

| Function | Purpose |
|----------|---------|
| `read_stdin()` | Parse JSON from stdin (includes Windows backslash fix) |
| `extract_conversation_context(path)` | Read JSONL transcript, extract last 30 turns as markdown, capped at 15,000 chars |
| `spawn_flush(context_file, session_id)` | Launch `ocd-flush` as detached background process |
| `write_context_file(session_id, context, prefix)` | Write context to `.agent/.state/{prefix}-{session_id}-{timestamp}.md` |

## Git Hooks

| Hook | Purpose |
|------|---------|
| `pre-commit` | Block commits on `main` branch; scan staged changes for secrets (gitleaks) |
| `pre-push` | Run `pytest` before push; abort if tests fail |
| `commit-msg` | Reject AI attribution in commit messages |

### AI Attribution Patterns

Single source of truth: `git_hooks/ai-patterns.txt`

| Pattern | Matches |
|---------|---------|
| `^Co-Authored-By:` | Standard git co-author trailer |
| `^Generated (with\|by\|using)` | "Generated with/by/using" attribution |
| `^\[AI(-generated)?\]` | `[AI]` or `[AI-generated]` tags |

Git hooks are installed as symlinks: `.git/hooks/<hook>` → `git_hooks/<hook>`. Run `bash git_hooks/setup-hooks.sh` after cloning.

### Secret Scanning (gitleaks)

Single source of truth: `.gitleaks.toml`

Gitleaks runs in two contexts:

- **Local pre-commit hook**: `gitleaks protect --staged` scans staged changes before each commit
- **CI `secret-scan` job**: `gitleaks detect` scans the full diff on push and PR

If gitleaks is not installed locally, the pre-commit hook prints a warning to stderr and continues. CI always runs gitleaks (binary installed directly in the `secret-scan` job).

To allowlist a false positive, add an entry under `[allowlist]` in `.gitleaks.toml`.

## IDE Configuration

The `ocd.code-workspace` file provides shared workspace settings:

- **Format on save** enabled globally
- **Ruler at 100 characters** (matches `ruff` line-length)
- **Python**: organize imports on save, strict type checking
- **Markdown**: word wrap enabled
- **Files**: insert final newline, trim trailing whitespace, exclude `__pycache__`, `.venv`, `.mypy_cache`, `.ruff_cache` from file tree and search

The workspace also adds `.agent/` subdirectories (daily logs, knowledge, state) as folder entries for quick navigation.

Extension recommendations live in `.vscode/extensions.json` (gitignored — each developer chooses their own).

## Package Entry Points

| Command | Module | Purpose |
|---------|--------|---------|
| `ocd-compile` | `ocd.compile:main` | Daily logs → knowledge articles (LLM compiler) |
| `ocd-flush` | `ocd.flush:main` | Extract knowledge from session context (background) |
| `ocd-lint-kb` | `ocd.lint:main` | Structural + LLM contradiction checks on knowledge base |
| `ocd-query` | `ocd.query:main` | Index-guided knowledge base search |
| `ocd-session-start` | `ocd.hooks.session_start:main` | Session start context injection |
| `ocd-session-end` | `ocd.hooks.session_end:main` | Session end transcript capture |
| `ocd-pre-compact` | `ocd.hooks.pre_compact:main` | Pre-compaction context save |
| `ocd-lint-work` | `ocd.hooks.lint_work:main` | Real-time file linting on edit/commit |

All entry points are defined in `pyproject.toml` `[project.scripts]` and installed by `uv sync`.

## CI Pipeline

| Stage | Job | Tool | Trigger |
|-------|-----|------|---------|
| 1 (gate) | `check-commit-messages` | grep (reads `git_hooks/ai-patterns.txt`) | push only |
| 2 (parallel) | `lint-yaml` | yamllint | all |
| 2 (parallel) | `lint-shell` | shellcheck | all |
| 2 (parallel) | `lint-markdown` | mdformat | all |
| 2 (parallel) | `secret-scan` | gitleaks (binary install, reads `.gitleaks.toml`) | all |
| 3 (after 1+2) | `lint-python` | ruff + mypy | all |
| 4 (after 3) | `test-python` | pytest | all |

Concurrency: `cancel-in-progress: true` per ref. Permissions: `contents: read` only. Branch protection on `main` requires passing CI, linear history, and resolved conversations.

## Permissions and Sandbox

### Deny Rules

Deny rules in `.claude/settings.json` block Claude from reading secrets or modifying infrastructure files:

**Read deny** (block access to sensitive files):

| Pattern | What it blocks |
|---------|----------------|
| `Read(**/.env*)` | Environment variable files |
| `Read(**/*.pem)` | TLS certificates |
| `Read(**/*.key)` | Private keys |
| `Read(**/*.crt)` | Certificate files |
| `Read(**/secrets/**)` | Secrets directories |
| `Read(**/credentials/**)` | Credentials directories |
| `Read(**/.aws/**)` | AWS configuration |
| `Read(**/.ssh/**)` | SSH keys |
| `Read(**/.gnupg/**)` | GPG keys |
| `Read(**/id_rsa*)` | RSA private keys |
| `Read(**/docker-compose*.yml)` | Docker Compose files |
| `Read(**/config/database*.yml)` | Database configuration |
| `Read(~/Library/Keychains/**)` | macOS keychains |
| `Read(**/private/**)` | Private directories |
| `Read(~/)` | Home directory access |

**Edit/Write deny** (block modification of infrastructure):

| Surface | Pattern | What it blocks |
|---------|---------|----------------|
| `Edit(path)` / `Write(path)` | Edit and Write tools on matching files | Direct modification or overwrite |

Protected files (project-root-relative paths):

- `src/ocd/hooks/lint_work.py`, `src/ocd/hooks/hookslib.py`, `src/ocd/hooks/pre_compact.py`, `src/ocd/hooks/session_start.py`, `src/ocd/hooks/session_end.py`
- `src/ocd/config.py`, `src/ocd/compile.py`, `src/ocd/flush.py`, `src/ocd/lint.py`, `src/ocd/query.py`, `src/ocd/utils.py`
- `git_hooks/commit-msg`, `git_hooks/pre-commit`, `git_hooks/pre-push`, `git_hooks/setup-hooks.sh`
- `.gitleaks.toml`

**Bash deny** (block shell deletion of infrastructure):

| Surface | Pattern | What it blocks |
|---------|---------|----------------|
| `Bash(rm *:path)` | `rm` commands targeting matching paths | Deletion via shell |

Bash deny covers the same paths as Edit/Write deny.

### Sandbox

The sandbox restricts Claude's filesystem access at the process level:

```json
"sandbox": {
  "enabled": true,
  "filesystem": {
    "allowRead": ["."],
    "denyRead": ["~/"]
  }
}
```

- `allowRead: ["."]` — read access is scoped to the project directory
- `denyRead: ["~/"]` — the home directory is explicitly denied even within allowed paths

## Pipeline Constants

| Constant | Value | Where |
|----------|-------|-------|
| Max context chars (session start) | 20,000 | `ocd.hooks.session_start` |
| Max flush turns | 30 | `ocd.config` |
| Max flush context chars | 15,000 | `ocd.config` |
| Min turns (session end) | 1 | `ocd.config` |
| Min turns (pre-compact) | 5 | `ocd.config` |
| Flush dedup window | 60 seconds | `ocd.flush` |
| Auto-compile trigger time | 18:00+ local | `ocd.flush` |

## Pipeline Commands

```bash
ocd-compile                              # compile new/changed logs
ocd-compile --all                         # force recompile
ocd-compile --file .agent/daily/<date>.md # compile specific log
ocd-lint-kb                              # full lint (structural + LLM)
ocd-lint-kb --structural-only             # skip LLM checks
ocd-query "question"                     # query the KB
ocd-query "q" --file-back                # query + file answer
```
