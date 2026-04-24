---
title: Explanation
aliases: [explanation, concepts, architecture, rationale]
tags: [explanation]
created: 2026-04-17
updated: 2026-04-24
---

Why things are the way they are. This is not a guide for what to do — see [how-to](../how-to/README.md) for that. This is for understanding the design.

## Architecture

O.C.D. has four layers of augmentation:

- **Context injection** — At session start, you receive the KB index and recent daily log. You do not start from nothing.
- **Enforcement** — Hooks lint edits and commits in real time. Skills define what "correct" means per language. Git hooks block violations before they enter history.
- **Persistence** — The knowledge pipeline captures insights at session end and before compaction, compiles them into articles, and feeds them back at the next session start.
- **Delegation** — Subagents handle bounded analysis tasks (dead code hunting, dependency auditing, lint checking) so you can focus on design and synthesis.

These layers are independent and reinforce each other. Context injection makes enforcement smarter (you know the standards). Persistence makes context richer (previous sessions feed future ones). Delegation keeps enforcement scalable (agents run checks you'd forget to run). For the AI-facing perspective on these layers, see [usage](../how-to/ai-usage.md).

## Directory Layout

The project has four distinct areas:

```
(root)              Project source, tests, docs, pyproject.toml, .git
src/ocd/            Installable Python package (hooks, scripts, config, utils)
.githooks/          Shell git hooks (commit-msg, pre-commit) + setup script
USER/             Data — daily logs, knowledge base, state (git-ignored)
.claude/            LLM-Processor config — settings.json, skills/, agents/, worktrees/
```

- **Project root** — The code being developed. `pyproject.toml`, `src/ocd/`, `tests/`, and `docs/` live here.
- **`src/ocd/`** — The installable Python package. The `ocd` umbrella CLI (including `ocd hook` subcommands) is defined in `pyproject.toml` and installed by `uv sync`. This replaces the old pattern of running scripts with `uv --directory .claude run python scripts/...`.
- **`.githooks/`** — Bash git hooks and their setup script. Symlinks from `.git/hooks/` point here, not to `.claude/hooks/`.
- **`USER/`** — Conversation data and compiled knowledge. Isolated from git via `.gitignore`. Each instance has its own `USER/` data.
- **`.claude/`** — Claude Code configuration only: `settings.json` (hooks, permissions), `skills/` (language standards), `agents/` (subagent definitions), `worktrees/` (isolated autofix worktrees). No Python code lives here.

This separation means you can share the project and source code without exposing conversation data, and you can reset `USER/` without losing the automation infrastructure.

## The Nine Standards

| Standard | Meaning | How It Applies |
| -------------------------- | --------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| Consistent Defaults | Every tool and config has a sensible zero-config starting point | Skills ship with default rules; no configuration needed to get started |
| Defense in Depth | Multiple independent protections against each failure mode | Deny rules + git hooks + CI gates all enforce the same constraints independently |
| Deterministic Ordering | Same inputs always produce same outputs | Ordered lists, sorted tables, consistent commit message format |
| Inconsistent Elimination | Conflicting sources are resolved, not tolerated side by side | Standards hash verification in CI and pre-commit; mdformat normalization eliminates format drift |
| Minimal Surface Area | Fewer moving parts means fewer failures | Skills are declarative rules, not frameworks; agents are scoped to single concerns |
| No Dead Code | Every line must earn its existence | The `dead-code-hunter` agent finds unused functions, variables, and configs |
| Progressive Simplification | Start strict, relax only when justified | Skills begin with hard prohibitions; exemptions require explicit justification |
| Single Source of Truth | Each fact lives in exactly one place | AI patterns in `ai-patterns.txt` (shared by hook + CI); config in `pyproject.toml` |
| Structural Honesty | The structure reflects the reality, not a facade | Root is the project, `USER/` is data, `src/ocd/` is automation, `.claude/` is config |

## Why an Installable Package

The original structure embedded Python code in `.claude/scripts/` and `.claude/hooks/`, requiring `sys.path` hacks, `importlib` for hyphenated filenames, and `uv --directory .claude run` for every invocation. The installable package layout (`src/ocd/`) solves these problems:

- **Entry points** — `ocd compile`, `ocd flush`, `ocd lint-kb`, `ocd query`, and hook commands are installed as a single `ocd` CLI by `uv sync`. No path manipulation needed.
- **Clean imports** — `from ocd.config import ...` instead of `sys.path.insert(0, ...)`. No `importlib` hacks.
- **Consistent invocation** — Hooks in `settings.json` use `ocd hook session-start` instead of `.claude/.venv/bin/python .claude/hooks/session-start.py`.
- **Standard tooling** — `ruff`, `mypy`, `pytest` all work from project root with no `--config-file` or `--directory` flags.

## Why core.hooksPath Not Symlinks

Git's `core.hooksPath` tells git to look for hooks in `.githooks/` instead of `.git/hooks/`. This is the standard convention for projects that version their hooks alongside the code. The setup script (`bash .githooks/setup-hooks.sh`) runs `git config core.hooksPath .githooks/` and makes the hook scripts executable.

Python hooks are invoked via the `ocd hook` CLI (`ocd hook session-start`, `ocd hook lint-work`, etc.) in the settings.json hook system, not by git directly. Each hook type runs in the environment it was designed for.

## Why Deny Rules and Protected Files

Claude Code can edit any file it has permission to access. For most files this is fine, but the hooks and scripts that enforce project standards form the project's immune system — if Claude can modify the lint rules, the lint rules become meaningless.

Deny rules in `settings.json` block three attack surfaces: direct edits (`Edit`), full overwrites (`Write`), and shell deletion (`Bash rm`). This is not trust — it is structural assurance. The deny rules can be lifted temporarily, but doing so is a deliberate act that requires opening the config file and removing a line.

## Why AI Attribution Blocking

The `commit-msg` hook and CI `check-commit-messages` job reject AI-generated attribution patterns in commit messages. This is not about hiding AI involvement — it is about keeping the git log as a clean record of intent and change, not a billboard for tooling. Attribution lines add noise, drift as tools change, and provide no actionable information to a reader trying to understand why a change was made.

The patterns are the single source of truth in `.githooks/ai-patterns.txt`, shared between the local hook and CI. Add a pattern once, it takes effect everywhere.

## The Feedback Loop

The system is designed to improve itself:

- Work in a session — hooks enforce standards in real time
- Session ends — transcript is captured and knowledge is extracted
- Knowledge is compiled into articles and fed back at the next session start
- New sessions are smarter — they have the context of every previous session
- Gaps in the system (missing skills, needed agents, uncaught patterns) are recorded in [planning](../planning.md) and filled

This loop means the project accumulates institutional memory. Decisions, lessons, and rationale are not lost at session end — they become part of the context for every future session.

## Why Separate CI Pipelines

The main CI pipeline (`.github/workflows/ci.yml`) and the container pipeline (`.github/workflows/containers.yml`) are intentionally separate:

- **Speed** — Container builds take minutes; linters take seconds. A slow Docker build should not block a fast lint failure from being reported.
- **Trigger scope** — The main pipeline runs on every push and PR. The container pipeline runs only when container-relevant paths change (Dockerfiles, dependencies, workflow file), plus `workflow_dispatch` for manual triggers.
- **Permissions** — The container pipeline needs `packages: write` to push images to GHCR. The main pipeline only needs `contents: read`. Separating them follows least privilege.
- **Independent failure** — A trivy image scan failure should not prevent the main pipeline from reporting lint or test results. Each pipeline's status is reported independently on PRs.

The two pipelines share no state — the container pipeline rebuilds images from
scratch rather than depending on artifacts from the main pipeline.

## Why a Read-Only Export

The `ocd export` command reads from `knowledge.db` and writes an
Obsidian-compatible markdown vault. It is deliberately one-directional: the
knowledge pipeline owns the database, and the export is a derived view.

- **Default target** (`USER/knowledge-export/`) is gitignored — personal
  exports never leak to version control
- **`--commit` flag** targets `docs/knowledge/` for projects that want
  curated knowledge in version control
- **Wikilink format** strips same-type prefixes (`[[concepts/other]]` becomes
  `[[other]]` within concepts) so Obsidian's graph view groups articles by
  type naturally
- **MOC index** with Dataview queries gives immediate interactive navigation
  in Obsidian without any plugins beyond Dataview

The export never writes back to the database. It is a snapshot, not a sync.
