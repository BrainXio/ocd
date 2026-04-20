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
| `trivy` | Container image and dependency vulnerability scanning in CI | Done |
| `hadolint` | Dockerfile linting commit gate for the `docker` skill | Done

## Security

| Item | Purpose | Status |
|------|---------|--------|
| `trivy` CI job | Scan container images and Python dependencies for known vulnerabilities | Done |
| `semgrep` CI job | Static analysis for OWASP Top 10 patterns | Done |

## New Commands

| Command | Purpose | Status |
|---------|---------|--------|
| `ocd format` | Run all formatters with auto-fix (ruff, mdformat, etc.) | Planned |

## CI/CD Beyond Lint

| Item | Purpose | Status |
|------|---------|--------|
| Semantic versioning | Automated version bumps from conventional commits | Planned |
| Changelog generation | Auto-generate CHANGELOG.md from commit history | Planned |
| Container image publishing | Push built images to GHCR on release | Done |
| Deployment pipelines | Staging → production deployment workflows | Planned |

## Knowledge Pipeline

| Item | Purpose | Status |
|------|---------|--------|
| Agent directory scaffolding | `ocd init` creates `.agent/` structure with gitkeep files | Done |
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
