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
|--------|---------|--------|
| `sqlfluff` | SQL linting CI job for the `sql` skill | Pending tool evaluation |

### SQL Skill Stack Investigation

Before adding `sqlfluff`, determine what additional tools and dependencies the `sql` skill requires in the stack:

- Evaluate `sqlfluff` dialect support against project SQL targets
- Identify SQL formatter companion (e.g., `sqlfmt` or `sqlfluff format`)
- Determine if a SQL type checker or linter beyond `sqlfluff` is needed
- Assess CI job requirements: extra dependencies, database fixtures for linting

## New Commands

| Command | Purpose | Status |
|---------|---------|--------|
| `ocd format` | Run all formatters with auto-fix (ruff, mdformat, etc.) | Planned |

## Packaging and Distribution

| Item | Purpose | Status |
|------|---------|--------|
| GitHub Release packaging | Build and attach the `obsessive-claude-developer` sdist/wheel to GitHub Releases alongside container images | Planned |
| Internal CI library | Python library for agent-based CI workflows, driven by `.github/workflows/` definitions | Planned |

## CI/CD Beyond Lint

| Item | Purpose | Status |
|------|---------|--------|
| Semantic versioning | Automated version bumps from conventional commits | Planned |
| Changelog generation | Auto-generate CHANGELOG.md from commit history | Planned |
| Deployment pipelines | Staging → production deployment workflows | Planned |

## Developer Experience

| Item | Purpose | Status |
|------|---------|--------|
| Local dev requirements | Document all prerequisites and setup steps for a local dev environment (system packages, tools, versions) | Planned |

## Knowledge Pipeline

| Item | Purpose | Status |
|------|---------|--------|
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
