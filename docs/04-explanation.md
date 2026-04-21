---
title: Explanation
aliases: [explanation, concepts, architecture, rationale]
tags: [explanation]
created: 2026-04-17
updated: 2026-04-20
---

Why things are the way they are. This is not a guide for what to do — see [how-to](02-how-to.md) for that. This is for understanding the design.

## Architecture

O.C.D. has four layers of augmentation:

- **Context injection** — At session start, you receive the KB index and recent daily log. You do not start from nothing.
- **Enforcement** — Hooks lint edits and commits in real time. Skills define what "correct" means per language. Git hooks block violations before they enter history.
- **Persistence** — The knowledge pipeline captures insights at session end and before compaction, compiles them into articles, and feeds them back at the next session start.
- **Delegation** — Subagents handle bounded analysis tasks (dead code hunting, dependency auditing, lint checking) so you can focus on design and synthesis.

These layers are independent and reinforce each other. Context injection makes enforcement smarter (you know the standards). Persistence makes context richer (previous sessions feed future ones). Delegation keeps enforcement scalable (agents run checks you'd forget to run). For the AI-facing perspective on these layers, see [usage](06-usage.md).

## Directory Layout

The project has four distinct areas:

```
(root)              Project source, tests, docs, pyproject.toml, .git
src/ocd/            Installable Python package (hooks, scripts, config, utils)
git_hooks/          Shell git hooks (commit-msg, pre-commit) + setup script
.agent/             Data — daily logs, knowledge base, state (git-ignored)
.claude/            LLM-Processor config — settings.json, skills/, agents/
```

- **Project root** — The code being developed. `pyproject.toml`, `src/ocd/`, `tests/`, and `docs/` live here.
- **`src/ocd/`** — The installable Python package. Entry points (`ocd-compile`, `ocd-flush`, etc.) are defined in `pyproject.toml` and installed by `uv sync`. This replaces the old pattern of running scripts with `uv --directory .claude run python scripts/...`.
- **`git_hooks/`** — Bash git hooks and their setup script. Symlinks from `.git/hooks/` point here, not to `.claude/hooks/`.
- **`.agent/`** — Conversation data and compiled knowledge. Isolated from git via `.gitignore`. Each instance has its own `.agent/` data.
- **`.claude/`** — Claude Code configuration only: `settings.json` (hooks, permissions), `skills/` (language standards), `agents/` (subagent definitions). No Python code lives here.

This separation means you can share the project and source code without exposing conversation data, and you can reset `.agent/` without losing the automation infrastructure.

## The Eight Standards

| Standard                   | Meaning                                                         | How It Applies                                                                         |
| -------------------------- | --------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| Consistent Defaults        | Every tool and config has a sensible zero-config starting point | Skills ship with default rules; no configuration needed to get started                 |
| Defense in Depth           | Multiple independent protections against each failure mode      | Deny rules + git hooks + CI gates all enforce the same constraints independently       |
| Deterministic Ordering     | Same inputs always produce same outputs                         | Ordered lists, sorted tables, consistent commit message format                         |
| Minimal Surface Area       | Fewer moving parts means fewer failures                         | Skills are declarative rules, not frameworks; agents are scoped to single concerns     |
| No Dead Code               | Every line must earn its existence                              | The `dead-code-hunter` agent finds unused functions, variables, and configs            |
| Progressive Simplification | Start strict, relax only when justified                         | Skills begin with hard prohibitions; exemptions require explicit justification         |
| Single Source of Truth     | Each fact lives in exactly one place                            | AI patterns in `ai-patterns.txt` (shared by hook + CI); config in `pyproject.toml`     |
| Structural Honesty         | The structure reflects the reality, not a facade                | Root is the project, `.agent/` is data, `src/ocd/` is automation, `.claude/` is config |

## Why an Installable Package

The original structure embedded Python code in `.claude/scripts/` and `.claude/hooks/`, requiring `sys.path` hacks, `importlib` for hyphenated filenames, and `uv --directory .claude run` for every invocation. The installable package layout (`src/ocd/`) solves these problems:

- **Entry points** — `ocd-compile`, `ocd-flush`, `ocd-lint-kb`, `ocd-query`, and hook commands are installed as shell commands by `uv sync`. No path manipulation needed.
- **Clean imports** — `from ocd.config import ...` instead of `sys.path.insert(0, ...)`. No `importlib` hacks.
- **Consistent invocation** — Hooks in `settings.json` use `ocd-session-start` instead of `.claude/.venv/bin/python .claude/hooks/session-start.py`.
- **Standard tooling** — `ruff`, `mypy`, `pytest` all work from project root with no `--config-file` or `--directory` flags.

## Why Symlinks Not core.hooksPath

Git's `core.hooksPath` redirects all hook lookups to a single directory. This would expose Claude Code's Python hooks (which expect Claude-specific JSON on stdin) to git, causing cryptic failures when git runs them as regular shell scripts.

Symlinks provide selective exposure — only the bash hooks (`pre-commit`, `commit-msg`) are installed into `.git/hooks/`, while Python hooks are invoked via installed entry points (`ocd-session-start`, `ocd-lint-work`, etc.) in the settings.json hook system. Each hook type runs in the environment it was designed for.

## Why Deny Rules and Protected Files

Claude Code can edit any file it has permission to access. For most files this is fine, but the hooks and scripts that enforce project standards form the project's immune system — if Claude can modify the lint rules, the lint rules become meaningless.

Deny rules in `settings.json` block three attack surfaces: direct edits (`Edit`), full overwrites (`Write`), and shell deletion (`Bash rm`). This is not trust — it is structural assurance. The deny rules can be lifted temporarily, but doing so is a deliberate act that requires opening the config file and removing a line.

## Why AI Attribution Blocking

The `commit-msg` hook and CI `check-commit-messages` job reject AI-generated attribution patterns in commit messages. This is not about hiding AI involvement — it is about keeping the git log as a clean record of intent and change, not a billboard for tooling. Attribution lines add noise, drift as tools change, and provide no actionable information to a reader trying to understand why a change was made.

The patterns are the single source of truth in `git_hooks/ai-patterns.txt`, shared between the local hook and CI. Add a pattern once, it takes effect everywhere.

## The Feedback Loop

The system is designed to improve itself:

- Work in a session — hooks enforce standards in real time
- Session ends — transcript is captured and knowledge is extracted
- Knowledge is compiled into articles and fed back at the next session start
- New sessions are smarter — they have the context of every previous session
- Gaps in the system (missing skills, needed agents, uncaught patterns) are recorded in [planning](05-planning.md) and filled

This loop means the project accumulates institutional memory. Decisions, lessons, and rationale are not lost at session end — they become part of the context for every future session.

## Why Separate CI Pipelines

The main CI pipeline (`.github/workflows/ci.yml`) and the container pipeline (`.github/workflows/containers.yml`) are intentionally separate:

- **Speed** — Container builds take minutes; linters take seconds. A slow Docker build should not block a fast lint failure from being reported.
- **Trigger scope** — The main pipeline runs on every push and PR. The container pipeline runs only when container-relevant paths change (Dockerfiles, dependencies, workflow file), plus `workflow_dispatch` for manual triggers.
- **Permissions** — The container pipeline needs `packages: write` to push images to GHCR. The main pipeline only needs `contents: read`. Separating them follows least privilege.
- **Independent failure** — A trivy image scan failure should not prevent the main pipeline from reporting lint or test results. Each pipeline's status is reported independently on PRs.

The two pipelines share no state — the container pipeline rebuilds images from scratch rather than depending on artifacts from the main pipeline.
