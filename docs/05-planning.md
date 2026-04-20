---
title: 'Planning: Future Expansions'
aliases: [planning, future, roadmap]
tags: [planning]
created: 2026-04-17
updated: 2026-04-20
---

Planned additions and improvements to the O.C.D. project. Items are organized by category and tracked with status.

## New Linters

| Linter | Purpose | Status |
| ---------- | -------------------------------------- | ----------------------- |
| `sqlfluff` | SQL linting CI job for the `sql` skill | Pending tool evaluation |

### SQL Skill Stack Investigation

Before adding `sqlfluff`, determine what additional tools and dependencies the `sql` skill requires in the stack:

- Evaluate `sqlfluff` dialect support against project SQL targets
- Identify SQL formatter companion (e.g., `sqlfmt` or `sqlfluff format`)
- Determine if a SQL type checker or linter beyond `sqlfluff` is needed
- Assess CI job requirements: extra dependencies, database fixtures for linting

## New Commands

| Command | Purpose | Status |
| ------------ | ------------------------------------------------------- | ------ |
| `ocd format` | Run all formatters with auto-fix (ruff, mdformat, etc.) | Done |

## Packaging and Distribution

| Item | Purpose | Status |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- | ------- |
| GitHub Release packaging | Build and attach the `brainxio-ocd` sdist/wheel to GitHub Releases alongside container images | Planned |
| Release package composition | Define which artifacts go into a GitHub Release and how they are assembled (see below) | Planned |
| `AGENTS.md` | Instruction file for external agents on which packages and assets to download from this repo and how to set them up in foreign environments | Planned |
| Internal CI library | Python library for agent-based CI workflows, driven by `.github/workflows/` definitions | Planned |

### Release Package Composition

A GitHub Release should contain three tiers of artifacts:

**Essential** (minimum viable OCD — knowledge pipeline + hooks):

| Artifact | Contents |
| ----------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| `brainxio_ocd-<version>-py3-none-any.whl` | Python package (all 13 modules, 9 entry points) |
| `brainxio_ocd-<version>.tar.gz` | Source distribution |
| `ocd-config.zip` | `.claude/settings.json`, `.claude/rules/commit-hygiene.md`, `.claude/rules/infrastructure.md`, `.claude/skills/ocd/SKILL.md` |
| `ocd-templates.zip` | `git_hooks/setup-hooks.sh`, `git_hooks/ai-patterns.txt`, `.gitleaks.toml`, `package.json`, `package-lock.json` |

**Recommended** (adds enforcement + core skills + audit agents):

| Artifact | Contents |
| --------------------- | ------------------------------------------------------------------------------- |
| `ocd-hooks.zip` | `git_hooks/commit-msg`, `git_hooks/pre-commit`, `git_hooks/pre-push` |
| `ocd-skills-core.zip` | `.claude/skills/{git,bash,python,docker}/SKILL.md` |
| `ocd-rules-core.zip` | `.claude/rules/{markdown,doc-sync,pr-workflow}.md` |
| `ocd-agents-core.zip` | `.claude/agents/{lint-status,hook-integrity,hook-coverage,dead-code-hunter}.md` |

**Optional** (language-specific skills, remaining agents, containers):

| Artifact | Contents |
| ---------------------- | -------------------------------------------------------------------- |
| `ocd-skills-extra.zip` | All remaining `.claude/skills/*/SKILL.md` (15 language/infra skills) |
| `ocd-agents-extra.zip` | All remaining `.claude/agents/*.md` (21 audit agents) |
| Container images | Published to GHCR (`ghcr.io/brainxio/ocd-<name>:<version>`) |

The `AGENTS.md` file should document these tiers and provide setup instructions for each.

## CI/CD Beyond Lint

| Item | Purpose | Status |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------ | ------- |
| CI path filters | Add path-based triggers to `ci.yml` so doc-only changes skip Python lint/test/security jobs and only run relevant checks | Done |
| Semantic versioning | Automated version bumps from conventional commits | Planned |
| Changelog generation | Auto-generate CHANGELOG.md from commit history | Planned |
| Release automation | CI job that composes release artifacts, creates a GitHub Release with composed package content, and uploads assets | Planned |
| Deployment pipelines | Staging → production deployment workflows | Planned |

## Developer Experience

| Item | Purpose | Status |
| ---------------------- | --------------------------------------------------------------------------------------------------------- | ------- |
| Local dev requirements | Document all prerequisites and setup steps for a local dev environment (system packages, tools, versions) | Planned |

## Knowledge Pipeline

| Item | Purpose | Status |
| ----------------------- | --------------------------------------------------- | ------- |
| Automated URL ingestion | Fetch URL content and route to flush.py in one step | Planned |
| KB export/sync | Share compiled knowledge between instances | Planned |

## Resolved Decisions

### Agent Architecture: Task-Driven (Decided)

Agents are **task-driven** — each does one focused job. Role-based agents were rejected because they conflate concerns, have broader surface area, and are harder to test. The task-driven model aligns with Minimal Surface Area and keeps each agent composable and precise.

The original role-based proposals (frontend-dev, backend-dev, devops-engineer, security-auditor) were replaced with task-driven equivalents: accessibility-auditor, api-contract-auditor, dockerfile-auditor, and owasp-scanner.

## Process

To add an item from this list:

- Create the skill/agent/linter following existing patterns in [how-to](02-how-to.md) or [reference](03-reference.md)
- Update this file to change the status from `Planned`/`Pending` to `Done`
- Once all items in a category are done, remove that section
