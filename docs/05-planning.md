---
title: 'Planning: Future Expansions'
aliases: [planning, future, roadmap]
tags: [planning]
created: 2026-04-17
updated: 2026-04-17
---

Planned additions and improvements to the O.C.D. project. Items are organized by category and tracked with status.

## New Linters

| Linter | Purpose | Status |
|--------|---------|--------|
| `sqlfluff` | SQL linting CI job for the `sql` skill | Pending tool evaluation |
| `trivy` | Container image and dependency vulnerability scanning in CI | Pending tool evaluation |
| `hadolint` | Dockerfile linting commit gate for the `docker` skill | Pending tool evaluation |

## New Container Images

| Image | Base | Purpose | Status |
|-------|------|---------|--------|
| `ocd-base` | Debian Bookworm Slim | Hardened foundational image with `uv`, `git`, `shellcheck` | Planned |
| `ocd-python` | `ocd-base` | Python 3.12+ toolchain: `ruff`, `mypy`, `mdformat` | Planned |
| `ocd-node` | `ocd-base` | Node.js 22+ toolchain: `pnpm`, `prettier`, `eslint` | Planned |
| `ocd-ollama` | `ocd-base` | Ollama runtime for local LLM inference | Planned |
| `ocd-devcontainer` | `ocd-python` + `ocd-node` | Full devcontainer with Claude Code, all linters, and Ollama | Planned |

Images follow a layered architecture: hardened base → language toolchains → application runtimes → integrated dev environments. Each image adds only what the layer above needs, following the Minimal Surface Area standard.

## New Subagents

| Agent | Model | Tools | Purpose | Status |
|-------|-------|-------|---------|--------|
| `accessibility-auditor` | haiku | Glob, Grep, Read | A11y review: semantic HTML, ARIA attributes, keyboard navigation, screen reader compatibility | Planned |
| `api-contract-auditor` | haiku | Glob, Grep, Read | API review: REST conventions, error response consistency, endpoint naming | Planned |
| `dockerfile-auditor` | haiku | Glob, Grep, Read, Bash | Docker review: layer ordering, security best practices, multi-stage builds, pinned digests | Planned |
| `owasp-scanner` | haiku | Glob, Grep, Read | Security review: OWASP Top 10 patterns (XSS, injection, CSRF, insecure deserialization) | Planned |
| `test-writer` | haiku | Glob, Grep, Read, Bash | Test generation: identify uncovered code, generate test cases, enforce coverage gates | Planned |

All agents follow the task-driven model: single concern, composable, testable. See Resolved Decisions below for the rationale.

## Security

| Item | Purpose | Status |
|------|---------|--------|
| `trivy` CI job | Scan container images and Python dependencies for known vulnerabilities | Planned |
| `semgrep` CI job | Static analysis for OWASP Top 10 patterns | Planned |

## IDE and Devcontainer

| Item | Purpose | Status |
|------|---------|--------|
| `.devcontainer/` definition | Instant onboarding using planned container images | Planned |

## CI/CD Beyond Lint

| Item | Purpose | Status |
|------|---------|--------|
| Semantic versioning | Automated version bumps from conventional commits | Planned |
| Changelog generation | Auto-generate CHANGELOG.md from commit history | Planned |
| Container image publishing | Push built images to GHCR on release | Planned |
| Deployment pipelines | Staging → production deployment workflows | Planned |

## Knowledge Pipeline

| Item | Purpose | Status |
|------|---------|--------|
| Automated URL ingestion | Fetch URL content and route to flush.py in one step | Planned |
| KB export/sync | Share compiled knowledge between instances | Planned |
| Multi-project KB | Apply O.C.D. to another project without starting `.agent/` from scratch | Planned |

## Resolved Decisions

### Agent Architecture: Task-Driven (Decided)

Agents are **task-driven** — each does one focused job. Role-based agents were rejected because they conflate concerns, have broader surface area, and are harder to test. The task-driven model aligns with Minimal Surface Area and keeps each agent composable and precise.

The original role-based proposals (frontend-dev, backend-dev, devops-engineer, security-auditor) were replaced with task-driven equivalents: accessibility-auditor, api-contract-auditor, dockerfile-auditor, and owasp-scanner.

## Process

To add an item from this list:

- Create the skill/agent/linter following existing patterns in [how-to](02-how-to.md) or [reference](03-reference.md)
- Update this file to change the status from `Planned`/`Pending` to `Done`
- Once all items in a category are done, remove that section
