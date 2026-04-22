---
title: "Planning: Future Expansions"
aliases: [planning, future, roadmap]
tags: [planning]
created: 2026-04-17
updated: 2026-04-22
---

Planned additions and improvements to the O.C.D. project. Items are organized into execution phases based on dependency order. Each phase lists its items in the order they should be completed.

## Completed: Token Preservation & Context Optimization

All five TP items shipped (TP-1 through TP-5, 2026-04-17 to 2026-04-21). Projected savings achieved: 23,000-32,000 tokens per typical session. Summary of what was delivered:

| ID | Feature | New Module | New Entry Point |
| ---- | -------------------------------------------- | ----------------- | --------------- |
| TP-1 | Smart KB Injection (TF-IDF relevance-ranked) | `relevance.py` | `ocd-kb-query` |
| TP-2 | Lightweight Task Router (keyword matcher) | `router.py` | `ocd-route` |
| TP-3 | Standards-as-Reference (hash-gated) | `standards.py` | `ocd-standards` |
| TP-4 | Closed-Loop Fix Family | `fix.py` | `ocd-fix-cycle` |
| TP-5 | Session State Card | `session_card.py` | — |

Generated artifacts (all in `.agent/.state/`, git-ignored): `kb-index.json`, `manifest.json`, `session-card.md`.

## Phase 1: Foundation

No external dependencies. These unblock everything that follows.

| # | Item | Purpose | Status |
| --- | ----------------------------- | --------------------------------------------------------------------------------------------------------- | ------ |
| 1.1 | Local dev requirements | Document all prerequisites and setup steps for a local dev environment (system packages, tools, versions) | Done |
| 1.2 | SQL skill stack investigation | Evaluate `sqlfluff` dialect support, identify formatter companion, assess CI job requirements | Done |
| 1.3 | `sqlfluff` linter | SQL linting CI job for the `sql` skill (depends on 1.2 results) | Done |

## Completed: Markdown Formatting Consistency

Normalized all tracked `.md` files to mdformat canonical form, added `.mdformat.toml` config, expanded CI and `ocd format` coverage to include `.claude/agents/` and `.claude/rules/`, documented frontmatter quote style convention (single quotes). This eliminates the ghost reformatting cycle where the PostToolUse hook repeatedly changed double-quoted frontmatter to single quotes on every edit.

## Phase 2: Version & Release Chain

Linear dependency chain. Each item builds on the one before it. Complete in order.

| # | Item | Purpose | Depends on | Status |
| --- | --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- | ------------- | ------- |
| 2.1 | Semantic versioning | Automated version bumps from conventional commits | — | Planned |
| 2.2 | Changelog generation | Auto-generate CHANGELOG.md from commit history | 2.1 | Planned |
| 2.3 | Release package composition | Bundled SQLite database inside the wheel; `ocd-compile-db` at build time, `ocd-materialize` at runtime | — | Done |
| 2.4 | GitHub Release packaging | Build and attach the `brainxio-ocd` sdist/wheel to GitHub Releases alongside container images | 2.3 | Planned |
| 2.5 | Release automation | CI job that composes release artifacts, creates a GitHub Release with composed package content, and uploads assets | 2.1, 2.2, 2.4 | Planned |
| 2.6 | `AGENTS.md` | Instruction file for external agents on which packages and assets to download from this repo and how to set them up in foreign environments | 2.3 | Planned |
| 2.7 | Deployment pipelines | Staging → production deployment workflows | 2.5 | Planned |

### Release Package Composition

All `.claude/` content (agents, rules, skills, standards) is compiled into a
bundled SQLite database (`content.db`) at build time and shipped inside the
Python wheel via hatch `force-include`. At runtime, `ocd-materialize`
reconstructs the markdown files to any target directory (`.claude/`, `.cursor/`,
`.copilot/`, etc.), letting consumers select only the content they need.

A GitHub Release contains:

| Artifact | Contents |
| ----------------------------------------- | ----------------------------------------------------------- |
| `brainxio_ocd-<version>-py3-none-any.whl` | Python package (all modules, entry points, `content.db`) |
| `brainxio_ocd-<version>.tar.gz` | Source distribution |
| Container images | Published to GHCR (`ghcr.io/brainxio/ocd-<name>:<version>`) |

The `AGENTS.md` file should document how to install the wheel and run
`ocd-materialize` to deploy the configuration.

## Phase 3: Knowledge Pipeline Extensions

Independent of the release chain. Can run in parallel with Phase 2.

| # | Item | Purpose | Depends on | Status |
| --- | ----------------------- | --------------------------------------------------- | ---------- | ------- |
| 3.1 | KB export/sync | Share compiled knowledge between instances | — | Planned |
| 3.2 | Automated URL ingestion | Fetch URL content and route to flush.py in one step | — | Planned |

## Phase 4: CI Extension

Higher complexity, benefits from release automation patterns established in Phase 2.

| # | Item | Purpose | Depends on | Status |
| --- | ------------------- | --------------------------------------------------------------------------------------- | ---------- | ------- |
| 4.1 | Internal CI library | Python library for agent-based CI workflows, driven by `.github/workflows/` definitions | 2.5 | Planned |

## Resolved Decisions

### Agent Architecture: Task-Driven (Decided)

Agents are **task-driven** — each does one focused job. Role-based agents were rejected because they conflate concerns, have broader surface area, and are harder to test. The task-driven model aligns with Minimal Surface Area and keeps each agent composable and precise.

The original role-based proposals (frontend-dev, backend-dev, devops-engineer, security-auditor) were replaced with task-driven equivalents: accessibility-auditor, api-contract-auditor, dockerfile-auditor, and owasp-scanner.

## Process

To add an item from this list:

- Create the skill/agent/linter following existing patterns in [how-to](02-how-to.md) or [reference](03-reference.md)
- Update this file to change the status from `Planned`/`Pending` to `Done`
- Once all items in a category are done, remove that section
