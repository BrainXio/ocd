---
title: Getting Started
aliases: [getting-started, tutorial, setup]
tags: [tutorial]
created: 2026-04-17
updated: 2026-04-17
---

Walk through your first 15 minutes with O.C.D. — set up, work a session, commit a change, and see the knowledge pipeline in action.

## 1. Clone and Set Up

```bash
git clone <repo-url> && cd ocd

# Install Python package and dependencies
uv sync

# Install git hooks (branch protection + AI attribution blocking + secret scanning)
bash git_hooks/setup-hooks.sh

# Install gitleaks for local secret scanning (optional but recommended)
# See: https://github.com/gitleaks/gitleaks#installing
# On macOS: brew install gitleaks
# On Ubuntu: download from https://github.com/gitleaks/gitleaks/releases
```

Or use the devcontainer (requires Docker and VS Code with the Remote Containers extension):

```bash
# Open in VS Code and select "Reopen in Container"
code .
```

The devcontainer includes all dependencies (Python, Node.js, linters, Ollama, Claude Code) — no manual setup required. It uses the pre-built `ghcr.io/brainxio/ocd` image and runs `ocd init` on creation.

Verify the entry points and hooks are installed:

```bash
source .venv/bin/activate

which ocd-session-start ocd-lint-work
# Should resolve to .venv/bin/ocd-session-start, etc.

ls -la .git/hooks/pre-commit .git/hooks/commit-msg
# Both should be symlinks pointing to git_hooks/
```

## 2. Start a Session

Activate the virtual environment, then launch Claude Code:

```bash
source .venv/bin/activate
claude
```

Or, if using the Ollama devcontainer:

```bash
# Ollama runs automatically inside the devcontainer
# Start Claude Code from the devcontainer terminal
claude
```

The venv must be active before starting Claude — otherwise the hook commands won't be on PATH and sessions will start without knowledge injection or lint checks. See [development setup](07-development.md) for details.

The `ocd-session-start` hook runs automatically and injects:

- The current date
- The full knowledge base index from `.agent/knowledge/index.md`
- The last 30 lines of the most recent daily log

You start every session with context — not from nothing.

## 3. Make a Change

Create a feature branch and make an edit:

```bash
git checkout -b feat/my-change
```

Edit a file — for example, add a line to `docs/01-getting-started.md`. The `ocd-lint-work --edit` hook runs after every Write/Edit and lints the changed file. If mdformat, ruff, or another linter finds issues, you see the error immediately.

## 4. Commit the Change

```bash
git add <file>
git commit -m "feat: describe what changed"
```

Two hooks fire:

- **pre-commit** — confirms you're not on `main` and scans staged changes for secrets (gitleaks)
- **ocd-lint-work --commit** — lints all staged files

If the commit message contains AI attribution (`Co-Authored-By:`, `Generated with`, `[AI]`), the `commit-msg` hook rejects it.

If gitleaks detects a potential secret, the pre-commit hook rejects the commit. Add an allowlist entry to `.gitleaks.toml` if it's a false positive.

## 5. Push the Change

```bash
git push
```

The `pre-push` hook runs `pytest -q` before allowing the push. If tests fail, the push is aborted. This ensures broken tests never reach the remote repository.

## 6. End the Session

When the session ends, `ocd-session-end` captures the transcript and spawns `ocd-flush` as a background process. Flush extracts structured knowledge and appends it to `.agent/daily/YYYY-MM-DD.md`.

After 18:00 local time, flush automatically triggers `ocd-compile` if today's log hasn't been compiled yet. Compile transforms daily log entries into persistent knowledge articles in `.agent/knowledge/`.

On your next session, those compiled articles appear in the KB index injected at startup. The cycle continues.

## Next Steps

- [How-to guides](02-how-to.md) — add a skill, add a subagent, run pipeline commands manually
- [Reference](03-reference.md) — full tables of skills, agents, hooks, and commands
- [Explanation](04-explanation.md) — architecture, the Eight Standards, design rationale
- [Development Setup](07-development.md) — venv activation and local development workflow
