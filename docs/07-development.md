---
title: Development Setup
aliases: [development, dev-setup, contributing]
tags: [how-to, development]
created: 2026-04-17
updated: 2026-04-17
---

How to set up your local environment so that O.C.D. hooks are available when you start a Claude Code session.

## Why This Matters

O.C.D. hooks (`ocd-session-start`, `ocd-lint-work`, `ocd-pre-compact`, etc.) are Python entry points installed by `uv sync`. They live in `.venv/bin/`. Claude Code runs these hooks as subprocesses — if the virtual environment isn't on `PATH`, the hooks won't be found and every session will start without knowledge injection, linting, or flush.

### 1. Sync dependencies

Installs the package and creates `.venv/`:

```bash
uv sync
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

After activating the venv, confirm the entry points are on PATH:

```bash
which ocd-session-start ocd-lint-work ocd-pre-compact ocd-session-end
```

All four should resolve to paths inside `.venv/bin/`. If any are missing, re-run `uv sync`.

## Common Mistakes

- **Starting `claude` before activating the venv** — hooks silently fail; you get a session with no knowledge base injection or lint checks.
- **Running `uv sync` without following up with `source .venv/bin/activate`** — the packages are installed but not on PATH for the current shell.
- **Opening a new terminal tab** — each terminal starts a fresh shell; re-activate the venv before launching `claude`.
