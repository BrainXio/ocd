---
title: Development Setup
aliases: [development, dev-setup, contributing]
tags: [how-to, development]
created: 2026-04-17
updated: 2026-04-22
---

How to set up your local environment so that O.C.D. hooks are available when you start a Claude Code session.

## System Prerequisites

Full development requires system tools, Python tools, and Node.js tools. The
[Linter Configurations](03-reference.md#linter-configurations) table in the
reference docs lists config files and scopes for each linter.

### Required System Tools

| Tool | Minimum Version | Install | Purpose |
| ------- | --------------- | -------------------------------------------------- | ---------------------------------- |
| uv | 0.4+ | `curl -LsSf https://astral.sh/uv/install.sh \| sh` | Python package manager |
| Python | 3.12+ | system package manager or `uv python install 3.12` | Runtime |
| Node.js | 22+ | system package manager or `fnm`/`nvm` | CSS/HTML/JSON linting via `npm ci` |
| Git | 2.40+ | system package manager | Version control and hooks |

### Python Tools (installed by `uv sync`)

| Tool | Minimum Version | Purpose |
| -------------------- | --------------- | ------------------------------------- |
| ruff | 0.8+ | Lint and format Python |
| mypy | 1.13+ | Strict type checking |
| yamllint | 1.35+ | Lint YAML |
| mdformat | 0.7+ | Format Markdown |
| mdformat-frontmatter | 2.0.10+ | Preserve YAML frontmatter in Markdown |
| claude-agent-sdk | 0.1.29+ | Agent SDK for compile and flush |
| pytest | 9.0.3+ | Test runner |
| pytest-asyncio | 1.3.0+ | Async test support |

### Optional: SQL Tools

SQL linting and formatting require the `sql` extra:

```bash
uv sync --extra sql
```

This installs `sqlfluff >=3.0`, which provides both `sqlfluff lint` and
`sqlfluff fix`. Configuration lives in `.sqlfluff` (INI format) at the project
root.

### Optional System Linters

These linters are not required for basic development. Git hooks warn but do not
fail when they are missing. CI always installs them.

| Tool | Install | CI Job |
| ---------- | ------------------------------------------------------------------ | -------------- |
| gitleaks | [binary install](https://github.com/gitleaks/gitleaks#installing) | `secret-scan` |
| hadolint | [binary install](https://github.com/hadolint/hadolint#installing) | containers CI |
| shellcheck | `apt install shellcheck` / `brew install shellcheck` | `lint-shell` |
| actionlint | [binary install](https://github.com/rhysd/actionlint#install) | `lint-actions` |
| trivy | [binary install](https://github.com/aquasecurity/trivy#installing) | `scan-deps` |
| semgrep | `pip install semgrep` | `sast-scan` |

### Node.js Tools (installed by `npm ci`)

Running `npm ci` in the project root installs into `node_modules/`:

| Tool | Purpose |
| --------- | ------------------------ |
| stylelint | CSS linting |
| htmlhint | HTML linting |
| prettier | JSON/CSS/HTML formatting |

## Devcontainer Setup

The devcontainer includes all dependencies — Python, Node.js, linters, Ollama,
and Claude Code. Open the project in VS Code and select "Reopen in Container"
to use it. No manual setup is required.

The devcontainer uses the pre-built `ghcr.io/brainxio/ocd` image and runs
`ocd init` on creation, which installs the project entry points, Node
dependencies, and git hooks.

## Local Setup

O.C.D. hooks (`ocd hook session-start`, `ocd hook lint-work`, `ocd hook pre-compact`, etc.)
are subcommands of the `ocd` CLI, installed by `uv sync`. They live in `.venv/bin/ocd`.
Claude Code runs these hooks as subprocesses — if the virtual environment isn't
on `PATH`, the hooks won't be found and every session will start without
knowledge injection, linting, or flush.

### 1. Sync dependencies

Installs the package and creates `.venv/`:

```bash
uv sync
```

For SQL linting support:

```bash
uv sync --extra sql
```

### 2. Activate the virtual environment

```bash
source .venv/bin/activate
```

### 3. Start Claude Code

```bash
claude
```

Or, if you're using the Ollama devcontainer:

```bash
ollama launch claude
```

## Verifying Hooks Are Available

After activating the venv, confirm the CLI is on PATH:

```bash
which ocd
```

It should resolve to `.venv/bin/ocd`. If missing,
re-run `uv sync`.

## Common Mistakes

- **Starting `claude` before activating the venv** — hooks silently fail; you
  get a session with no knowledge base injection or lint checks.
- **Running `uv sync` without following up with `source .venv/bin/activate`** —
  the packages are installed but not on PATH for the current shell.
- **Opening a new terminal tab** — each terminal starts a fresh shell;
  re-activate the venv before launching `claude`.
- **Missing `--extra sql` for SQL work** — `sqlfluff` is an optional dependency;
  run `uv sync --extra sql` to enable SQL linting.
