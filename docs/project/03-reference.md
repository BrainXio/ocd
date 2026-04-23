---
title: Reference
aliases: [reference, api, specs, tables]
tags: [reference]
created: 2026-04-17
updated: 2026-04-21
---

All lookup tables, schemas, and specifications in one place. Dry, authoritative, complete.

## Skill Registry

| Skill | Description |
| ------------ | --------------------------------------------------------------------------------------------------------------- |
| `bash` | `set -euo pipefail` mandatory, `shellcheck` zero-warnings gate. No unquoted expansions. |
| `cpp` | C++17 minimum, smart pointers only, `#pragma once` headers, CMake. No raw `new`/`delete`. |
| `csharp` | C# 10+ / .NET 8+, nullable reference types, file-scoped namespaces. No legacy collections. |
| `css` | CSS Grid/Flexbox layouts, Custom Properties for tokens, BEM or utility-first. No `!important` except utilities. |
| `docker` | Multi-stage builds, pinned base image digests. No `latest` tags in production. |
| `git` | Conventional Commits, squash merge with GPG signing. Every branch has a purpose. |
| `github` | Actions workflows pinned to SHA, least-privilege permissions, branch protection, `gh` CLI. No unpinned actions. |
| `go` | Go 1.22+, `gofmt` commit gate, doc comments on all exports. No `panic` in library code. |
| `html` | HTML5 semantic elements, accessibility attributes, keyboard navigation. No `<div>` soup. |
| `java` | Java 17+, `final` by default, records, sealed classes, Javadoc on publics. No `System.out` in production. |
| `js` | ES2022+, strict equality, `const`/`let`, ESLint zero-warnings gate. No `var`, no `==`. |
| `json` | RFC 8259 compliance, 2-space indent, schema validation. No trailing commas, no comments in `.json`. |
| `kubernetes` | Resource limits, liveness/readiness probes, `runAsNonRoot`, `readOnlyRootFilesystem`. No unbounded pods. |
| `markdown` | CommonMark spec, `mdformat` gate, frontmatter preservation. No inline HTML for layout. |
| `ocd` | Meta-standard: reviews, refactors, creates code against the Nine Standards. Every line must earn its existence. |
| `php` | PHP 8.1+, `declare(strict_types=1)`, Composer, PSR-12. No legacy patterns. |
| `python` | Python 3.12+, strict type hints, `uv` packaging, `ruff` commit gate. No bare `except`, no `Any`. |
| `ruby` | Ruby 3.1+, `frozen_string_literal: true`, Bundler, `rubocop` zero-offense gate. No unfrozen strings. |
| `rust` | Edition 2021+, `cargo fmt` + `cargo clippy -- -D warnings` commit gates. No `unsafe` without safety comment. |
| `sql` | Parameterized queries, explicit JOINs, `NOT NULL` constraints. No `SELECT *`, no comma joins. |
| `swift` | Swift 5.9+, strict concurrency, `async`/`await`, SwiftLint zero-warnings gate. No force-unwrap outside tests. |
| `terraform` | HCL2, remote state with locking, `sensitive = true` for secrets, module composition. No hardcoded secrets. |
| `typescript` | TypeScript 5.x, `strict: true`, `pnpm`, explicit return types. No `any` — use `unknown`. |
| `yaml` | 2-space indent, quoted ambiguous types, `yamllint` zero-errors gate. No tabs, no unquoted booleans. |

All skills live in `.claude/skills/<name>/SKILL.md`.

## Subagent Registry

| Agent | Model | Tools | Purpose |
| ----------------------- | ----- | ---------------------- | --------------------------------------------------------------------------------------------- |
| `ci-drift` | haiku | Glob, Grep, Read | Detect CI drift: compare local config vs CI workflow |
| `dead-code-hunter` | haiku | Glob, Grep, Read | Find dead code: unused functions, variables, configs |
| `dependency-auditor` | haiku | Bash, Read, Glob, Grep | Audit Python dependencies: unused, conflicting, missing |
| `docstring-enforcer` | haiku | Grep, Read, Glob | Check docstring coverage: missing, inconsistent, public API |
| `exception-auditor` | haiku | Grep, Read, Glob | Audit exception handling: bare excepts, broad catches |
| `hook-coverage` | haiku | Bash, Read, Glob | Verify hook coverage: symlinks, executables, CI parity |
| `hook-integrity` | haiku | Bash, Read, Glob | Verify hook chain integrity: symlinks, scripts, patterns |
| `lint-status` | haiku | Bash, Glob | Run linters, report triad: errors, clean, missing |
| `test-coverage-auditor` | haiku | Glob, Grep, Read | Audit test coverage: missing test files, untested public functions |
| `kb-health-checker` | haiku | Glob, Grep, Read | Verify KB structural health: broken wikilinks, orphan pages, stale articles |
| `single-source-auditor` | haiku | Glob, Grep, Read | Find duplicated constants, config, patterns violating Single Source of Truth |
| `perf-opportunist` | haiku | Glob, Grep, Read | Find low-effort performance wins: unnecessary loops, redundant computations, caching |
| `deps-upgrader` | haiku | Bash, Read, Glob, Grep | Scan for outdated dependencies with safe upgrade paths |
| `dry-enforcer` | haiku | Glob, Grep, Read | Find duplicated logic blocks that could be extracted into shared utilities |
| `complexity-reducer` | haiku | Glob, Grep, Read | Flag high-cyclomatic-complexity functions and suggest simplifications |
| `readability-scorer` | haiku | Glob, Grep, Read | Flag unclear variable names, missing type hints, dense one-liners |
| `yagni-auditor` | haiku | Glob, Grep, Read | Find over-engineered code: unused abstractions, premature generalizations |
| `kiss-auditor` | haiku | Glob, Grep, Read | Find unnecessarily complex implementations that could be simpler |
| `solid-auditor` | haiku | Glob, Grep, Read | Find SOLID principle violations: SRP, OCP, LSP, ISP, DIP |
| `oop-auditor` | haiku | Glob, Grep, Read | Find OOP design issues: god classes, improper inheritance, leaked internals |
| `accessibility-auditor` | haiku | Glob, Grep, Read | A11y review: semantic HTML, ARIA attributes, keyboard navigation, screen reader compatibility |
| `api-contract-auditor` | haiku | Glob, Grep, Read | API review: REST conventions, error response consistency, endpoint naming, HTTP semantics |
| `dockerfile-auditor` | haiku | Glob, Grep, Read, Bash | Docker review: layer ordering, security best practices, multi-stage builds, pinned digests |
| `owasp-scanner` | haiku | Glob, Grep, Read | Security review: OWASP Top 10 patterns (XSS, injection, CSRF, insecure deserialization) |
| `test-writer` | haiku | Glob, Grep, Read, Bash | Test generation: identify uncovered code, generate test cases, enforce coverage gates |

All agents live in `.claude/agents/<name>.md`.

### Agent Frontmatter Schema

| Field | Required | Description |
| ------------- | -------- | --------------------------------------------------------------------------- |
| `name` | yes | Agent identifier (matches filename without `.md`) |
| `description` | yes | One-line purpose (quote values containing colons) |
| `tools` | yes | Comma-separated list of tools the agent can use |
| `model` | no | Model to use (defaults to parent model). Options: `haiku`, `sonnet`, `opus` |

Example:

```yaml
---
name: lint-status
description: "Run linters and report: errors, clean, missing"
tools: Bash, Glob
model: haiku
---
```

## Claude Code Hooks

| Hook | Entry Point | Trigger | Purpose |
| ------------- | ------------------------ | ----------------------------- | ----------------------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| SessionStart | `ocd-session-start` | SessionStart | Inject relevant KB articles + health card + standards reference + session card as context |
| PreCompact | `ocd-pre-compact` | PreCompact | Save context before auto-compaction discards it |
| SessionEnd | `ocd-session-end` | SessionEnd | Capture transcript → spawn flush |
| Lint (edit) | `ocd-lint-work --edit` | PostToolUse (Write | Edit) | Lint edited files, report missing linters |
| Format (edit) | `ocd-format-work --edit` | PostToolUse (Write | Edit) | Auto-format edited files, capture violations, update session card |
| Lint (commit) | `ocd-lint-work --commit` | PreToolUse (Bash: git commit) | Lint staged files before commit |

All Python hooks are installed as entry points via `pyproject.toml` `[project.scripts]`. Source code lives in `src/ocd/hooks/`.

### Hook Configuration Schema

Hooks are declared in `.claude/settings.json` under the `hooks` key:

| Field | Required | Description |
| --------- | -------- | ----------------------------------------------------------------------------------------------------------------- |
| `matcher` | yes | Tool event pattern (e.g., `Write&#124;Edit`, `Bash`) |
| `if` | no | Conditional filter (e.g., `Bash(git commit*)`). Note: `if` is a YAML reserved word — some parsers require quoting |
| `type` | yes | Currently only `command` |
| `command` | yes | Shell command to run (entry point name) |
| `timeout` | yes | Maximum execution time in seconds |

### Hook Stdin JSON

Hooks receive a JSON object on stdin:

```json
{
  "session_id": "string",
  "transcript_path": "string (path to JSONL transcript)",
  "source": "string"
}
```

### hookslib API

| Function | Purpose |
| ------------------------------------------------- | -------------------------------------------------------------------------------- |
| `parse_stdin_json()` | Parse JSON from stdin (includes Windows backslash fix) |
| `extract_conversation_context(path)` | Read JSONL transcript, extract last 30 turns as markdown, capped at 15,000 chars |
| `spawn_flush(context_file, session_id)` | Launch `ocd-flush` as detached background process |
| `write_context_file(session_id, context, prefix)` | Write context to `USER/state/{prefix}-{session_id}-{timestamp}.md` |

### State Files

| File | Purpose |
| ------------------------------------ | ----------------------------------------------------------------------------- |
| `USER/state/format-violations.jsonl` | Per-line JSON records of auto-format corrections (file, formatter, timestamp) |
| `USER/state/flush.log` | Background flush process log |
| `USER/state/state.json` | Session state |
| `USER/state/last-flush.json` | Last flush metadata |
| `USER/state/kb-index.json` | TF-IDF search index for KB relevance queries |
| `USER/state/manifest.json` | Agent keyword manifest for task routing |
| `USER/state/session-card.md` | Session state card for post-compaction recovery (FIFO, 1,200 char cap) |
| `.claude/skills/ocd/standards.md` | Nine Standards full text with version + hash frontmatter |

## Claude Code Rules

Rules in `.claude/rules/` provide advisory instructions to Claude Code sessions.
Rules are distinct from hooks: hooks enforce deterministically, rules guide behavior.

| Rule File | Scope | Purpose |
| ------------------- | -------------------- | --------------------------------------------------------------------- |
| `commit-hygiene.md` | Unconditional | Conventional commits, branch naming, no AI attribution |
| `pr-workflow.md` | Unconditional | PR labels, body template, merge requirements |
| `doc-sync.md` | Unconditional | Update reference/planning docs when shipping features |
| `markdown.md` | `**/*.md` | mdformat, frontmatter plugin, quote style, ordered list normalization |
| `infrastructure.md` | Infrastructure paths | Deny rule modification procedure for protected files |

All rule files live in `.claude/rules/`. The root `CLAUDE.md` serves as the rules index.
Path-scoped rules load only when matching files are read; unconditional rules load every session.

## Git Hooks

| Hook | Purpose |
| ------------ | ---------------------------------------------------------------------------------------------------------------------------------------- |
| `pre-commit` | Block commits on `main` branch; scan staged changes for secrets (gitleaks); lint Dockerfiles (hadolint); auto-format markdown (mdformat) |
| `pre-push` | Run `pytest` before push; abort if tests fail |
| `commit-msg` | Reject AI attribution in commit messages |

### AI Attribution Patterns

Single source of truth: `git_hooks/ai-patterns.txt`

| Pattern | Matches |
| ------------------------------ | ------------------------------------- |
| `^Co-Authored-By:` | Standard git co-author trailer |
| `^Generated (with\|by\|using)` | "Generated with/by/using" attribution |
| `^\[AI(-generated)?\]` | `[AI]` or `[AI-generated]` tags |

Git hooks are installed as symlinks: `.git/hooks/<hook>` → `git_hooks/<hook>`. Run `bash git_hooks/setup-hooks.sh` after cloning.

### Secret Scanning (gitleaks)

Single source of truth: `.gitleaks.toml`

Gitleaks runs in two contexts:

- **Local pre-commit hook**: `gitleaks protect --staged` scans staged changes before each commit
- **CI `secret-scan` job**: `gitleaks detect` scans the full diff on push and PR

If gitleaks is not installed locally, the pre-commit hook prints a warning to stderr and continues. CI always runs gitleaks (binary installed directly in the `secret-scan` job).

To allowlist a false positive, add an entry under `[allowlist]` in `.gitleaks.toml`.

## Linter Configurations

| Linter | Config file | Scope | Install |
| ---------- | --------------------------------------------------------- | ------------------- | --------------------- |
| ruff | `pyproject.toml` `[tool.ruff]` | Python | `uv sync` |
| mypy | `pyproject.toml` `[tool.mypy]` | Python | `uv sync` |
| mdformat | `.mdformat.toml` + `mdformat_frontmatter_preserve` plugin | Markdown | `uv sync` |
| yamllint | `.yamllint` | YAML | `uv sync` |
| shellcheck | — | Shell | system package |
| gitleaks | `.gitleaks.toml` | Secrets | binary install |
| actionlint | — | GitHub Actions | binary install |
| stylelint | `.stylelintrc.json` | CSS | `npm ci` |
| htmlhint | `.htmlhintrc` | HTML | `npm ci` |
| prettier | `.prettierrc` | JSON | `npm ci` |
| sqlfluff | `.sqlfluff` | SQL | `uv sync --extra sql` |
| hadolint | `.hadolint.yaml` | Dockerfile | binary install |
| trivy | `trivy.yaml` + `.trivyignore` | Vulnerabilities | binary install |
| semgrep | `.semgrep.yml` | SAST (OWASP Top 10) | pip install |

Python linters are installed via `uv sync`. Node.js linters are installed via `npm ci` (defined in `package.json`). The `ocd-lint-work` hook reports missing linters gracefully — it does not block edits when a linter is unavailable.

## Formatter Registry

`ocd format` runs all available formatters with auto-fix. Each formatter is only run if its tool is installed and its config file exists.

| Formatter | Command | Scope |
| -------------- | ------------------------------------------------------------------------- | ----------------- |
| `ruff-format` | `ruff format src/ tests/` | Python |
| `ruff-fix` | `ruff check --fix src/ tests/` | Python |
| `mdformat` | `mdformat README.md docs/ .claude/skills/ .claude/agents/ .claude/rules/` | Markdown |
| `prettier` | `npx prettier --write .` | JSON / CSS / HTML |
| `stylelint` | `npx stylelint --fix "**/*.css"` | CSS |
| `sqlfluff-fix` | `sqlfluff fix --force` | SQL |

The formatter registry lives in `src/ocd/format.py`. Missing formatters are reported with install hints. Formatters that fail (non-zero exit) cause `ocd format` to exit with code 1.

## IDE Configuration

The `ocd.code-workspace` file provides shared workspace settings:

- **Format on save** enabled globally
- **Ruler at 100 characters** (matches `ruff` line-length)
- **Python**: organize imports on save, strict type checking
- **Markdown**: word wrap enabled
- **Files**: insert final newline, trim trailing whitespace, exclude `__pycache__`, `.venv`, `.mypy_cache`, `.ruff_cache` from file tree and search

The workspace also adds `USER/` subdirectories (daily logs, knowledge, state) as folder entries for quick navigation.

Extension recommendations live in `.vscode/extensions.json` (gitignored — each developer chooses their own).

## Package Entry Points

| Command | Module | Purpose |
| ------------------- | ------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ocd` | `ocd.cli:main` | Container init, shell, format, KB query, routing, standards, and fix — `ocd init` scaffolds `USER/`, seeds templates, installs deps/hooks; `ocd shell` drops into bash; `ocd format` runs all formatters with auto-fix; `ocd kb query --relevant-to "<q>"` returns relevant KB articles; `ocd route <query>` routes to optimal agents; `ocd standards` manages standards hash reference; `ocd fix-cycle <file>` runs closed-loop detect-fix-verify |
| `ocd-compile` | `ocd.compile:main` | Daily logs → knowledge articles (LLM compiler) |
| `ocd-flush` | `ocd.flush:main` | Extract knowledge from session context (background) |
| `ocd-format` | `ocd.format:main` | Run all formatters with auto-fix |
| `ocd-lint-kb` | `ocd.lint:main` | Structural + LLM contradiction checks on knowledge base |
| `ocd-query` | `ocd.query:main` | Index-guided knowledge base search |
| `ocd-session-start` | `ocd.hooks.session_start:main` | Session start context injection |
| `ocd-session-end` | `ocd.hooks.session_end:main` | Session end transcript capture |
| `ocd-pre-compact` | `ocd.hooks.pre_compact:main` | Pre-compaction context save |
| `ocd-lint-work` | `ocd.hooks.lint_work:main` | Real-time file linting on edit/commit |
| `ocd-format-work` | `ocd.hooks.format_work:main` | Real-time file auto-formatting on edit, session card updates |
| `ocd-kb-query` | `ocd.relevance:main` | TF-IDF relevance query against KB index |
| `ocd-route` | `ocd.router:main` | Route user request to optimal agent(s) |
| `ocd-standards` | `ocd.standards:main` | Manage standards hash reference (verify, update) |
| `ocd-fix-cycle` | `ocd.fix:main` | Closed-loop fix commands: fix-cycle, lint-and-fix, test-and-fix, security-scan-and-patch |
| `ocd-compile-db` | `ocd.pack:main` | Compile `.claude/` content into bundled SQLite database (`content.db`) |
| `ocd-materialize` | `ocd.materialize:main` | Reconstruct markdown files from `content.db` to target directory; `--vendor` flag materializes to vendor-specific formats (aider, cursor, copilot, windsurf, amazonq, all, agents-md) |
| `ocd-vendors` | `ocd.materialize:main` | Alias for `ocd-materialize` — vendor format adapter entry point |

All entry points are defined in `pyproject.toml` `[project.scripts]` and installed by `uv sync`.

## Bundled Content Database

The `content.db` SQLite database ships inside the Python wheel. It is compiled
at build time by `ocd-compile-db` from `.claude/` source files and
force-included via hatch config. At runtime, `ocd-materialize` reconstructs
markdown files to any target directory.

### Database Schema

| Table | Columns | Primary Key |
| ----------- | -------------------------------------------------------------------- | ----------- |
| `agents` | `name`, `frontmatter`, `body`, `created`, `updated` | `name` |
| `rules` | `name`, `description`, `paths`, `body`, `created`, `updated` | `name` |
| `skills` | `name`, `description`, `argument_hint`, `body`, `created`, `updated` | `name` |
| `standards` | `id`, `version`, `hash`, `body`, `created`, `updated` | `id` (= 1) |

### Build/Deploy Flow

```bash
ocd-compile-db                          # compile .claude/ → content.db
ocd-materialize                         # materialize content.db → .claude/
ocd-materialize -t /path/.cursor       # materialize to any agent directory
ocd-materialize -t /path/.copilot -f    # overwrite existing files
```

## CI Pipeline

Stage 1 detects changed paths and gates commit messages. Stage 2 runs
path-conditioned lints in parallel — only jobs matching the changed files run.
Stages 3–4 run only when Python code changes.

| Stage | Job | Tool | Condition |
| ------------ | ----------------------- | ---------------------------------------- | ---------------------- |
| 1 (detect) | `changes` | `dorny/paths-filter` | always |
| 1 (gate) | `check-commit-messages` | grep (reads `git_hooks/ai-patterns.txt`) | always |
| 1 (gate) | `verify-standards` | `ocd-standards --verify` | always |
| 2 (parallel) | `lint-yaml` | yamllint | YAML/workflow changes |
| 2 (parallel) | `lint-shell` | shellcheck | `git_hooks/**` changes |
| 2 (parallel) | `lint-markdown` | mdformat | `**/*.md` changes |
| 2 (parallel) | `secret-scan` | gitleaks (reads `.gitleaks.toml`) | always |
| 2 (parallel) | `lint-actions` | actionlint | workflow changes |
| 2 (parallel) | `lint-node` | stylelint + htmlhint + prettier (npm) | CSS/HTML/JSON changes |
| 2 (parallel) | `lint-sql` | sqlfluff | SQL changes |
| 2 (parallel) | `scan-deps` | trivy fs (reads `trivy.yaml`) | Python changes |
| 2 (parallel) | `sast-scan` | semgrep (reads `.semgrep.yml`) | Python changes |
| 3 (after 2) | `lint-python` | `ocd-compile-db` + ruff + mypy | Python changes |
| 4 (after 3) | `test-python` | `ocd-compile-db` + pytest | Python changes |

Concurrency: `cancel-in-progress: true` per ref. Permissions: `contents: read` only. Branch protection on `main` requires passing CI, signed commits, and resolved conversations.

## Container CI Pipeline

Defined in `.github/workflows/containers.yml`. Full details in
[containers](09-containers.md).

| Stage | Job | Tool | Trigger |
| ----------- | ----------------------------------------------------------------------- | -------------------------- | ------------ |
| 1 (lint) | `lint-dockerfile` | hadolint | paths filter |
| 2 (build) | `build-base`, `build-python`, `build-node`, `build-ollama`, `build-ocd` | Docker + smoke tests | after lint |
| 3 (scan) | `scan-images` | trivy image + SARIF upload | after build |
| 4 (publish) | `publish-latest`, `publish-release` | build-push-action → GHCR | after scan |

Separate from the main CI pipeline to avoid gating code quality checks on slow
container builds. Also triggered by `workflow_dispatch`.

### Container Images

| Image | Base | Purpose |
| ------------ | ---------------------- | ---------------------------------------------------------------------------- |
| `ocd-base` | `debian:bookworm-slim` | Hardened foundation: `uv`, `git`, `shellcheck` |
| `ocd-node` | `ocd-base` | Node.js 22+ toolchain: `pnpm`, `prettier`, `eslint`, `stylelint`, `htmlhint` |
| `ocd-ollama` | `ocd-base` | Ollama runtime for local LLM inference |
| `ocd-python` | `ocd-base` | Python 3.12+ toolchain: `ruff`, `mypy`, `mdformat` with frontmatter plugin |
| `ocd` | `ocd-python` | Product image: Python + Node + Ollama + Claude Code + OCD package |

Images live in `containers/<name>/Dockerfile`. Published to
`ghcr.io/brainxio/ocd-<name>:<tag>`.

### Inceptive Container

The `ocd` product image embeds the OCD tooling itself — see
[containers](09-containers.md#inceptive-container) for details.

## Permissions and Sandbox

### Deny Rules

Deny rules in `.claude/settings.json` block Claude from reading secrets or modifying infrastructure files:

**Read deny** (block access to sensitive files):

| Pattern | What it blocks |
| ------------------------------- | -------------------------- |
| `Read(**/.env*)` | Environment variable files |
| `Read(**/*.pem)` | TLS certificates |
| `Read(**/*.key)` | Private keys |
| `Read(**/*.crt)` | Certificate files |
| `Read(**/secrets/**)` | Secrets directories |
| `Read(**/credentials/**)` | Credentials directories |
| `Read(**/.aws/**)` | AWS configuration |
| `Read(**/.ssh/**)` | SSH keys |
| `Read(**/.gnupg/**)` | GPG keys |
| `Read(**/id_rsa*)` | RSA private keys |
| `Read(**/docker-compose*.yml)` | Docker Compose files |
| `Read(**/config/database*.yml)` | Database configuration |
| `Read(~/Library/Keychains/**)` | macOS keychains |
| `Read(**/private/**)` | Private directories |

**Edit/Write deny** (block modification of infrastructure):

| Surface | Pattern | What it blocks |
| ---------------------------- | -------------------------------------- | -------------------------------- |
| `Edit(path)` / `Write(path)` | Edit and Write tools on matching files | Direct modification or overwrite |

Protected files (project-root-relative paths):

- `src/ocd/hooks/format_work.py`, `src/ocd/hooks/lint_work.py`, `src/ocd/hooks/hookslib.py`, `src/ocd/hooks/pre_compact.py`, `src/ocd/hooks/session_start.py`, `src/ocd/hooks/session_end.py`
- `src/ocd/config.py`, `src/ocd/compile.py`, `src/ocd/flush.py`, `src/ocd/lint.py`, `src/ocd/query.py`, `src/ocd/utils.py`
- `git_hooks/commit-msg`, `git_hooks/pre-commit`, `git_hooks/pre-push`, `git_hooks/setup-hooks.sh`
- `.gitleaks.toml`

**Bash deny** (block shell deletion of infrastructure):

| Surface | Pattern | What it blocks |
| ----------------- | -------------------------------------- | ------------------ |
| `Bash(rm *:path)` | `rm` commands targeting matching paths | Deletion via shell |

Bash deny covers the same paths as Edit/Write deny.

### Sandbox

The sandbox restricts Claude's filesystem access at the process level:

```json
"sandbox": {
  "enabled": true,
  "filesystem": {
    "allowRead": ["."],
    "denyRead": ["~/"]
  }
}
```

- `allowRead: ["."]` — read access is scoped to the project directory
- `denyRead: ["~/"]` — the home directory is explicitly denied even within allowed paths

## Pipeline Constants

| Constant | Value | Where |
| --------------------------------- | --------------------------------- | ------------ |
| Max context chars (session start) | 20,000 | `ocd.config` |
| Max log lines (session start) | 30 | `ocd.config` |
| Max flush turns | 30 | `ocd.config` |
| Max flush context chars | 15,000 | `ocd.config` |
| Min turns (session end) | 1 | `ocd.config` |
| Min turns (pre-compact) | 5 | `ocd.config` |
| Flush dedup window | 60 seconds | `ocd.flush` |
| Auto-compile trigger time | 18:00+ local | `ocd.config` |
| KB injection count | 3 | `ocd.config` |
| Max relevant context chars | 8,000 | `ocd.config` |
| Standards file | `.claude/skills/ocd/standards.md` | `ocd.config` |
| Max session card chars | 1,200 | `ocd.config` |
| Session card file | `USER/state/session-card.md` | `ocd.config` |

## Pipeline Commands

```bash
ocd-compile                              # compile new/changed logs
ocd-compile --all                         # force recompile
ocd-compile --file USER/logs/daily/<date>.md # compile specific log
ocd-compile --manifest                   # rebuild agent manifest after compile
ocd-lint-kb                              # full lint (structural + LLM)
ocd-lint-kb --structural-only             # skip LLM checks
ocd-query "question"                     # query the KB
ocd-query "q" --file-back                # query + file answer
ocd format                                # run all formatters with auto-fix
ocd kb query --relevant-to "auth redirect" # TF-IDF relevance query (3-5 articles)
ocd-kb-query --build-index               # rebuild KB search index
ocd route "find dead code"               # route request to optimal agent(s)
ocd-route --build-manifest               # rebuild agent manifest
ocd standards                            # print current standards reference
ocd-standards --verify                    # verify hash matches content
ocd-standards --update                   # recompute and update hash in frontmatter
ocd fix-cycle <file>                    # detect-fix-verify cycle on a single file
ocd lint-and-fix <path>                 # fix all matching files under path
ocd test-and-fix                         # fix + verify tests still pass
ocd security-scan-and-patch              # semgrep scan + categorize findings
ocd-compile-db                           # compile .claude/ → content.db
ocd-materialize                          # materialize content.db → .claude/
ocd-materialize -t /path/.cursor        # materialize to custom target
ocd-materialize -f                       # overwrite existing files
```
