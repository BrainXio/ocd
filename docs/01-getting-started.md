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

# Install git hooks (branch protection + AI attribution blocking)
bash .claude/scripts/setup-hooks.sh

# Install Python venv and dependencies
cd .claude && uv sync && cd ..
```

Verify the hooks are installed:

```bash
ls -la .git/hooks/pre-commit .git/hooks/commit-msg
# Both should be symlinks pointing to .claude/hooks/
```

## 2. Start a Session

Launch Claude Code in the project directory:

```bash
claude
```

The `session-start.py` hook runs automatically and injects:

- The current date
- The full knowledge base index from `.agent/knowledge/index.md`
- The last 30 lines of the most recent daily log

You start every session with context — not from nothing.

## 3. Make a Change

Create a feature branch and make an edit:

```bash
git checkout -b feat/my-change
```

Edit a file — for example, add a line to `docs/01-getting-started.md`. The `lint-work.py --edit` hook runs after every Write/Edit and lints the changed file. If mdformat, ruff, or another linter finds issues, you see the error immediately.

## 4. Commit the Change

```bash
git add <file>
git commit -m "feat: describe what changed"
```

Two hooks fire:

- **pre-commit** — confirms you're not on `main`
- **lint-work.py --commit** — lints all staged files

If the commit message contains AI attribution (`Co-Authored-By:`, `Generated with`, `[AI]`), the `commit-msg` hook rejects it.

## 5. End the Session

When the session ends, `session-end.py` captures the transcript and spawns `flush.py` as a background process. Flush extracts structured knowledge and appends it to `.agent/daily/YYYY-MM-DD.md`.

After 18:00 local time, flush automatically triggers `compile.py` if today's log hasn't been compiled yet. Compile transforms daily log entries into persistent knowledge articles in `.agent/knowledge/`.

On your next session, those compiled articles appear in the KB index injected at startup. The cycle continues.

## Next Steps

- [How-to guides](02-how-to.md) — add a skill, add a subagent, run pipeline commands manually
- [Reference](03-reference.md) — full tables of skills, agents, hooks, and commands
- [Explanation](04-explanation.md) — architecture, the Eight Standards, design rationale
