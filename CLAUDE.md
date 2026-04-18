# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Setup
uv sync                                    # install package + all deps
bash git_hooks/setup-hooks.sh              # install git hook symlinks
ocd init                                   # container setup (seeds templates + deps + hooks)
ocd shell                                  # start interactive shell (in container)

# Lint (run individually)
uv run ruff check src/ocd/ tests/          # Python lint
uv run ruff format --check src/ocd/ tests/ # Python format check
uv run mypy src/ocd/ --strict              # type check
mdformat --check README.md docs/*.md .claude/skills/*/SKILL.md  # markdown
yamllint -f parsable .github/workflows/    # YAML
shellcheck git_hooks/commit-msg git_hooks/pre-commit git_hooks/pre-push git_hooks/setup-hooks.sh

# Test
uv run pytest -v                           # all tests
uv run pytest tests/test_config.py -v      # single test file
uv run pytest tests/test_utils.py::test_slugify -v  # single test

# Knowledge pipeline
ocd-compile                                # compile new/changed daily logs
ocd-compile --all                          # force recompile all
ocd-compile --file .agent/daily/2026-04-18.md  # specific log
ocd-lint-kb                                # full KB lint (structural + LLM)
ocd-lint-kb --structural-only              # skip LLM checks
ocd-query "question"                       # query the knowledge base

# Merge PRs
gh pr merge --squash --delete-branch        # only viable method (branch protection blocks direct push)
```

## Architecture

Knowledge pipeline cycle: **session-start → flush → compile → query → session-start**

1. `ocd-session-start` — injects KB index + recent daily log into every new session
1. `ocd-session-end` / `ocd-pre-compact` — extract conversation context, spawn background `ocd-flush`
1. `ocd-flush` — uses Claude Agent SDK to extract knowledge from context, appends to `.agent/daily/YYYY-MM-DD.md`
1. `ocd-compile` — reads daily logs, produces structured articles in `.agent/knowledge/` (concepts/, connections/, qa/)
1. `ocd-query` — index-guided retrieval, no vector DB — just structured markdown + LLM reasoning
1. `ocd-lint-kb` — structural checks (broken links, orphans, stale) + LLM contradiction checks on KB articles

Data flow: `.agent/daily/` → `ocd-compile` → `.agent/knowledge/{concepts,connections,qa}/` + `index.md` → `ocd-session-start` injection

### Hook chain

- **SessionStart** → `ocd-session-start` (inject KB context)
- **PostToolUse (Write|Edit)** → `ocd-lint-work --edit` (lint edited file, report missing linters)
- \**PreToolUse (Bash: git commit*)\*\* → `ocd-lint-work --commit` (lint staged files)
- **PreCompact** → `ocd-pre-compact` (save context before compaction)
- **SessionEnd** → `ocd-session-end` (capture transcript → spawn flush)
- **git pre-commit** → block commits on main, run gitleaks on staged changes
- **git commit-msg** → reject AI attribution patterns
- **git pre-push** → run pytest, abort if tests fail

All Python hooks are entry points defined in `pyproject.toml [project.scripts]`. Recursion prevention: `ocd-flush` sets `CLAUDE_INVOKED_BY=memory_flush` — hooks check this env var and exit early.

### Lint-work triad

`ocd-lint-work` reports three statuses per linter: **errors** (blocking), **clean** (passed), **missing** (linter not installed — advisory, does not block edits). The registry is in `src/ocd/hooks/lint_work.py`.

## Protected Files

Deny rules in `.claude/settings.json` block direct edits to core infrastructure files (`src/ocd/hooks/*.py`, `src/ocd/{config,compile,flush,lint,query,utils}.py`, `git_hooks/*`, `.gitleaks.toml`). To modify a protected file:

1. Remove the specific deny rules from `.claude/settings.json`
1. Make the change
1. Re-add the deny rules
1. Commit both changes together

Never leave deny rules removed — they are the project's immune system.

## Constraints

- **Venv required**: activate `.venv` before starting Claude — hook entry points must be on PATH
- **No commits on main**: pre-commit hook blocks it; always create a feature branch
- **No AI attribution**: commit-msg hook and CI reject `Co-Authored-By:`, `Generated with/by/using`, `[AI]` tags
- **Squash merge only**: `gh pr merge --squash --delete-branch` — branch protection prevents direct push
- **mdformat requires frontmatter plugin**: always use `mdformat-frontmatter>=2.0.10`, or frontmatter delimiters get stripped

## Rules

Unconditional rules (always loaded):

- `.claude/rules/commit-hygiene.md` — conventional commits, branch naming, AI attribution
- `.claude/rules/pr-workflow.md` — PR labels, body template, merge checks
- `.claude/rules/doc-sync.md` — update reference and planning docs when shipping features

Path-scoped rules (loaded on file Read):

- `.claude/rules/markdown.md` — mdformat, frontmatter, list markers (scoped to `**/*.md`)
- `.claude/rules/infrastructure.md` — deny rules, protected file procedure (scoped to infrastructure paths)

## Priority

When rules conflict with a skill file, rules win. Rules codify project-specific
process; skills define language-specific conventions. When a hook blocks an action,
the hook wins unconditionally — rules are advisory, hooks enforce.
