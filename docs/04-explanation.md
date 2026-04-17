---
title: Explanation
aliases: [explanation, concepts, architecture, rationale]
tags: [explanation]
created: 2026-04-17
updated: 2026-04-17
---

Why things are the way they are. This is not a guide for what to do — see [how-to](02-how-to.md) for that. This is for understanding the design.

## Architecture

O.C.D. has four layers of augmentation:

1. **Context injection** — At session start, you receive the KB index and recent daily log. You do not start from nothing.
1. **Enforcement** — Hooks lint edits and commits in real time. Skills define what "correct" means per language. Git hooks block violations before they enter history.
1. **Persistence** — The knowledge pipeline captures insights at session end and before compaction, compiles them into articles, and feeds them back at the next session start.
1. **Delegation** — Subagents handle bounded analysis tasks (dead code hunting, dependency auditing, lint checking) so you can focus on design and synthesis.

These layers are independent and reinforce each other. Context injection makes enforcement smarter (you know the standards). Persistence makes context richer (previous sessions feed future ones). Delegation keeps enforcement scalable (agents run checks you'd forget to run). For the AI-facing perspective on these layers, see [usage](06-usage.md).

## The Eight Standards

| Standard | Meaning | How It Applies |
|----------|---------|----------------|
| Consistent Defaults | Every tool and config has a sensible zero-config starting point | Skills ship with default rules; no configuration needed to get started |
| Defense in Depth | Multiple independent protections against each failure mode | Deny rules + git hooks + CI gates all enforce the same constraints independently |
| Deterministic Ordering | Same inputs always produce same outputs | Ordered lists, sorted tables, consistent commit message format |
| Minimal Surface Area | Fewer moving parts means fewer failures | Skills are declarative rules, not frameworks; agents are scoped to single concerns |
| No Dead Code | Every line must earn its existence | The `dead-code-hunter` agent finds unused functions, variables, and configs |
| Progressive Simplification | Start strict, relax only when justified | Skills begin with hard prohibitions; exemptions require explicit justification |
| Single Source of Truth | Each fact lives in exactly one place | AI patterns in `ai-patterns.txt` (shared by hook + CI); config in `pyproject.toml` |
| Structural Honesty | The structure reflects the reality, not a facade | Root is the project, `.agent/` is data, `.claude/` is the LLM-processor |

## Why Symlinks Not core.hooksPath

Git's `core.hooksPath` redirects all hook lookups to a single directory. This would expose Claude Code's Python hooks (which expect Claude-specific JSON on stdin) to git, causing cryptic failures when git runs them as regular shell scripts.

Symlinks provide selective exposure — only the bash hooks (`pre-commit`, `commit-msg`) are installed into `.git/hooks/`, while Python hooks remain in `.claude/hooks/` where they're invoked exclusively by the settings.json hook system. Each hook type runs in the environment it was designed for.

## Why Deny Rules and Protected Files

Claude Code can edit any file it has permission to access. For most files this is fine, but the hooks and scripts that enforce project standards form the project's immune system — if Claude can modify the lint rules, the lint rules become meaningless.

Deny rules in `settings.json` block three attack surfaces: direct edits (`Edit`), full overwrites (`Write`), and shell deletion (`Bash rm`). This is not trust — it is structural assurance. The deny rules can be lifted temporarily, but doing so is a deliberate act that requires opening the config file and removing a line.

## Why AI Attribution Blocking

The `commit-msg` hook and CI `check-commit-messages` job reject AI-generated attribution patterns in commit messages. This is not about hiding AI involvement — it is about keeping the git log as a clean record of intent and change, not a billboard for tooling. Attribution lines add noise, drift as tools change, and provide no actionable information to a reader trying to understand why a change was made.

The patterns are the single source of truth in `.claude/scripts/ai-patterns.txt`, shared between the local hook and CI. Add a pattern once, it takes effect everywhere.

## The Feedback Loop

The system is designed to improve itself:

1. Work in a session — hooks enforce standards in real time
1. Session ends — transcript is captured and knowledge is extracted
1. Knowledge is compiled into articles and fed back at the next session start
1. New sessions are smarter — they have the context of every previous session
1. Gaps in the system (missing skills, needed agents, uncaught patterns) are recorded in [planning](05-planning.md) and filled

This loop means the project accumulates institutional memory. Decisions, lessons, and rationale are not lost at session end — they become part of the context for every future session.

## Data Isolation

The project has three layers with distinct purposes:

- **Project** (root) — The code being developed. In a real project this contains the application source, tests, and documentation. In O.C.D.'s own repo it is self-referential — the "code being developed" is O.C.D. itself.
- `.agent/` — Data (daily logs, knowledge base, state). Isolated from git via a nested `.gitignore`. Conversation data and compiled knowledge stay local to each instance.
- `.claude/` — LLM-Processor (scripts, hooks, skills, venv, `pyproject.toml`). Version-controlled. The automation layer that processes the data.

This separation means you can share the project and LLM-processor code without exposing conversation data, and you can reset the `.agent/` data without losing the automation infrastructure.
