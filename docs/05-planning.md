---
title: 'Planning: Future Expansions'
aliases: [planning, future, roadmap]
tags: [planning]
created: 2026-04-17
updated: 2026-04-17
---

Planned additions and improvements to the O.C.D. project. Items are organized by category and tracked with status.

## New Skills

| Skill | Description | Status |
|-------|-------------|--------|
| `html` | Modern HTML5 standards, semantic markup, accessibility attributes, no deprecated elements | Planned |
| `css` | Modern CSS (Grid, Flexbox, Custom Properties), BEM or utility-first methodology, no `!important` except utilities | Planned |
| `sql` | SQL standards, query analysis, no SELECT \*, explicit JOINs, parameterized queries only | Planned |
| `terraform` | IaC standards, state hygiene, no hardcoded secrets, module composition | Planned |
| `swift` | Swift 5.9+, strict concurrency, SwiftLint commit gate | Planned |

Skills follow the existing pattern in `.claude/skills/<name>/SKILL.md` with mandatory practices, hard prohibitions, and commit gates.

## New Linters

| Linter | Purpose | Status |
|--------|---------|--------|
| `htmlhint` | HTML linting commit gate for the `html` skill | Pending tool evaluation |
| `stylelint` | CSS linting commit gate for the `css` skill | Pending tool evaluation |
| `gitleaks` | Secret scanning in pre-commit hook and CI | Pending tool evaluation |
| `trivy` | Container image and dependency vulnerability scanning in CI | Pending tool evaluation |
| `hadolint` | Dockerfile linting commit gate for the `docker` skill | Pending tool evaluation |

New linters will be added to `pyproject.toml`, the CI pipeline (`.github/workflows/ci.yml`), and the `ocd-lint-work` hook registry once available and configured.

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
| `frontend-dev` | haiku | Glob, Grep, Read | Frontend code review: HTML semantics, CSS architecture, accessibility, responsive patterns | Planned |
| `backend-dev` | haiku | Glob, Grep, Read, Bash | Backend code review: API design, database queries, error handling, security patterns | Planned |
| `devops-engineer` | haiku | Glob, Grep, Read, Bash | Infrastructure review: Dockerfile best practices, CI/CD pipeline health, deployment safety | Planned |
| `security-auditor` | haiku | Glob, Grep, Read, Bash | Security review: secret scanning, dependency vulnerabilities, input validation, OWASP patterns | Planned |
| `test-writer` | haiku | Glob, Grep, Read, Bash | Test generation: identify uncovered code, generate test cases, enforce coverage gates | Planned |

These role-aligned agents complement the existing task-driven agents (dead-code-hunter, exception-auditor, etc.) by providing domain-specific reviews that mirror traditional team responsibilities. See Open Design Decisions below for the investigation into how role-based and task-driven agents should coexist.

## Security

| Item | Purpose | Status |
|------|---------|--------|
| `gitleaks` pre-commit hook | Block secrets (API keys, tokens, credentials) from entering git history | Planned |
| `trivy` CI job | Scan container images and Python dependencies for known vulnerabilities | Planned |
| `semgrep` CI job | Static analysis for OWASP Top 10 patterns | Planned |
| `.env` in `.gitignore` enforcement | Ensure environment files are never committed | Done |

## Testing

| Item | Purpose | Status |
|------|---------|--------|
| `pytest` infrastructure for `src/ocd/` and `tests/` | Prevent broken hooks and scripts from reaching main | Done |
| `pre-push` hook | Run test suite before push (complements pre-commit's lint gate) | Planned |
| `pytest` as commit gate | Require passing tests before merge, tracked in CI | Done |

## IDE and Devcontainer

| Item | Purpose | Status |
|------|---------|--------|
| `.devcontainer/` definition | Instant onboarding using planned container images | Planned |
| VS Code recommended extensions | Auto-prompt for linters, Python, Docker extensions on repo open | Planned |
| Workspace settings for linters on save | Run mdformat/ruff on save instead of waiting for commit gate | Planned |

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

## Open Design Decisions

Unresolved architectural questions. Each should be investigated before committing to implementation.

### Agent Architecture: Role-Based vs Task-Driven

The current 8 agents are **task-driven** — each does one focused job (dead-code-hunter, exception-auditor, lint-status). The planned agents are **role-based** (backend-dev, security-auditor). Which model should O.C.D. standardize on?

**Task-driven (current)**

- Pros: composable, single concern, easy to test, aligns with Minimal Surface Area
- Cons: user must know which agent to invoke, running 4 agents for one review is tedious

**Role-based (proposed)**

- Pros: intuitive ("run backend-dev" vs "run 4 agents"), mirrors how teams think about responsibilities
- Cons: broader surface area, harder to test, conflates concerns, output may be less focused

**Hybrid (under investigation)**

- Role-based agents as a routing layer that composes task-driven agents internally
- User invokes `backend-dev`, it runs dead-code-hunter + exception-auditor + dependency-auditor + docstring-enforcer and synthesizes the results
- Task-driven agents stay focused and testable; role-based agents compose them into domain-specific reviews
- This preserves both models: task-driven for precision, role-based for convenience

**Investigation needed:** Can Claude Code subagents invoke other subagents? If not, the hybrid approach requires the role-based agent's prompt to include the task-driven agent's logic inline, which defeats composable reuse. This determines whether the hybrid is architecturally feasible or just role-based in disguise.

## Process

To add an item from this list:

- Create the skill/agent/linter following existing patterns in [how-to](02-how-to.md) or [reference](03-reference.md)
- Update this file to change the status from `Planned`/`Pending` to `Done`
- Once all items in a category are done, remove that section
