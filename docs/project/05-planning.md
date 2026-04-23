---
title: "Planning: Future Expansions"
aliases: [planning, future, roadmap]
tags: [planning]
created: 2026-04-17
updated: 2026-04-23
---

Planned additions and improvements to the O.C.D. project. Items are organized into execution phases based on dependency order. Each phase lists its items in the order they should be completed.

## Completed: Token Preservation & Context Optimization

All five TP items shipped (TP-1 through TP-5, 2026-04-17 to 2026-04-21). Projected savings achieved: 23,000-32,000 tokens per typical session. Summary of what was delivered:

| ID | Feature | New Module | New Entry Point |
| ---- | -------------------------------------------- | ----------------- | --------------- |
| TP-1 | Smart KB Injection (TF-IDF relevance-ranked) | `relevance.py` | `ocd kb query` |
| TP-2 | Lightweight Task Router (keyword matcher) | `router.py` | `ocd route` |
| TP-3 | Standards-as-Reference (hash-gated) | `standards.py` | `ocd standards` |
| TP-4 | Closed-Loop Fix Family | `fix.py` | `ocd fix-cycle` |
| TP-5 | Session State Card | `session_card.py` | — |

Generated artifacts (all in `USER/state/`, git-ignored): `kb-index.json`, `manifest.json`, `session-card.md`.

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
| 2.3 | Release package composition | Bundled SQLite database inside the wheel; `ocd compile-db` at build time, `ocd materialize` at runtime | — | Done |
| 2.4 | GitHub Release packaging | Build and attach the `brainxio-ocd` sdist/wheel to GitHub Releases alongside container images | 2.3 | Planned |
| 2.5 | Release automation | CI job that composes release artifacts, creates a GitHub Release with composed package content, and uploads assets | 2.1, 2.2, 2.4 | Planned |
| 2.6 | `AGENTS.md` | Instruction file for external agents on which packages and assets to download from this repo and how to set them up in foreign environments | 2.3 | Done |
| 2.7 | Deployment pipelines | Staging → production deployment workflows | 2.5 | Planned |

### Release Package Composition

All `.claude/` content (agents, rules, skills, standards) is compiled into a
bundled SQLite database (`content.db`) at build time and shipped inside the
Python wheel via hatch `force-include`. At runtime, `ocd materialize`
reconstructs the markdown files to any target directory (`.claude/`, `.cursor/`,
`.copilot/`, etc.), letting consumers select only the content they need.

A GitHub Release contains:

| Artifact | Contents |
| ----------------------------------------- | ----------------------------------------------------------- |
| `brainxio_ocd-<version>-py3-none-any.whl` | Python package (all modules, entry points, `content.db`) |
| `brainxio_ocd-<version>.tar.gz` | Source distribution |
| Container images | Published to GHCR (`ghcr.io/brainxio/ocd-<name>:<version>`) |

The `AGENTS.md` file documents how to install the wheel and run
`ocd materialize` to deploy the configuration. The `--vendor` flag materializes
to vendor-specific formats: `--vendor aider`, `--vendor cursor`,
`--vendor copilot`, `--vendor windsurf`, `--vendor amazonq`,
`--vendor agents-md` (project root AGENTS.md), or `--vendor all`.

## Phase 3: Knowledge Pipeline Extensions

Independent of the release chain. Can run in parallel with Phase 2.

| # | Item | Purpose | Depends on | Status |
| --- | ----------------------- | --------------------------------------------------- | ---------- | ------- |
| 3.1 | KB export/sync | Share compiled knowledge between instances | — | Planned |
| 3.2 | Automated URL ingestion | Fetch URL content and route to flush.py in one step | — | Planned |
| 3.3 | Raw knowledge ingestion | Ingest raw articles into ocd.db with scoring/dedup | — | Done |

## Phase 4: CI Extension

Higher complexity, benefits from release automation patterns established in Phase 2.

| # | Item | Purpose | Depends on | Status |
| --- | ------------------- | --------------------------------------------------------------------------------------- | ---------- | ------- |
| 4.1 | Internal CI library | Python library for agent-based CI workflows, driven by `.github/workflows/` definitions | 2.5 | Planned |

## Resolved Decisions

### Agent Architecture: Task-Driven (Decided)

Agents are **task-driven** — each does one focused job. Role-based agents were rejected because they conflate concerns, have broader surface area, and are harder to test. The task-driven model aligns with Minimal Surface Area and keeps each agent composable and precise.

The original role-based proposals (frontend-dev, backend-dev, devops-engineer, security-auditor) were replaced with task-driven equivalents: accessibility-auditor, api-contract-auditor, dockerfile-auditor, and owasp-scanner.

## Peer Integration Initiative

Systematic incorporation of best practices from Aider, Superpowers, and top Claude Code skill collections into O.C.D., preserving the Nine Standards and minimal-surface-area philosophy.

### 5.1 Superior Git & Diff Workflow (Aider)

**Description:** Aider auto-commits every AI edit as an atomic commit with descriptive messages, separates user edits from AI edits on dirty files, and provides `/undo` for instant revert of the last AI commit. Its layered edit-matching engine (exact → fuzzy `diff_match_patch` → git cherry-pick) reduces edit errors 9x.

**Value:** Atomic AI commits create a granular undo history — every change is individually reversible, not just the final result. Dirty-file separation means user state and AI state never interleave in a single commit.

**Adaptation strategy:** O.C.D.'s hooks already enforce pre-commit quality gates (lint, secrets, format). Aider's `--no-verify` default contradicts Standard 5 (Defense in Depth) — O.C.D. must never skip verify. The dirty-file pre-commit pattern is worth adopting: stash or commit pending changes before AI edits land on a clean tree.

**Implementation approach:**

1. Add git SHA to session card entries — `00:07 edit: config.py (abc1234)` instead of just `00:07 edit: config.py`. Minimal change to `session_card.py`, aligns with Standard 9 (Inconsistent Elimination).
1. Add "reason" field to session card entries — `00:07 edit: config.py | reason: added SESSION_CARD_FILE constant`. Improves post-compaction recovery without significant size increase. Aligns with Standard 6 (Structural Honesty).
1. Pre-session dirty-file stash — before any AI editing session, auto-stash or commit pending changes so AI edits land on a clean tree. Medium effort, aligns with Standard 5 (Defense in Depth).

**Impact:** Small-to-medium effort. Items 1 and 2 are session card enhancements (< 1 day each). Item 3 requires hook orchestration (2–3 days).

**Acceptance criteria:**

- Session card entries include git SHA and reason field
- Pre-commit hook enforces clean-tree invariant before AI edits
- `/undo`-style revert available via `git revert` on atomic AI commits

### 5.2 Self-Healing Review & Clarification System (Superpowers)

**Description:** Superpowers uses a sequential workflow (brainstorm → plan → execute → review → verify) with a clarification gate that blocks code generation until user intent is validated. Two-stage review (spec compliance, then code quality) blocks progress on critical issues. TDD enforcement means code written before a test gets deleted and redone.

**Value:** Activation is the bottleneck, not prompt quality. Superpowers achieves ~66% skill activation via SessionStart hooks vs. ~6% for plain skill files. The sequential workflow makes skipping steps structurally difficult.

**Adaptation strategy:** O.C.D. already has closed-loop fix commands (`fix-cycle`, `test-and-fix`, `security-scan-and-patch`) and PostToolUse lint enforcement. The gap is a **pre-edit** review gate — O.C.D. only reviews after edits land, not before.

**Implementation approach:**

1. Add `ocd review` command that runs the Nine Standards scoring as a structured JSON gate. Returns non-zero exit on critical issues, blockable by hooks or CI.
1. Add `ocd clarify` command that checks task descriptions against the agent manifest (already has `ocd route`). If relevance score is below threshold, emits a structured clarification prompt instead of proceeding.
1. Enforce review as a PreToolUse hook pattern: before `Write` or `Edit`, run the Nine Standards score on the target file. This closes the loop (currently only PostToolUse lint exists).

**Impact:** Medium effort. Items 1 and 2 are new CLI commands (2–3 days each). Item 3 requires extending the PreToolUse hook pattern (1 day).

**Acceptance criteria:**

- `ocd review <file>` returns structured scoring JSON with exit code
- `ocd clarify <task>` emits clarification prompt when relevance is below threshold
- PreToolUse hook runs standards scoring before edits land

### 5.3 Improved Multi-Agent Coordination & Task Router

**Description:** Top skill collections use shared task boards with pending/in-progress/completed states, file-lock-based claiming to prevent race conditions, and worktree isolation per agent. Superpowers dispatches a fresh subagent per task with two-stage review.

**Value:** Lateral coordination via a shared task board (not top-down orchestration) lets agents self-claim tasks, commit independently, and merge continuously. Worktrees give each agent its own filesystem so there are zero file conflicts.

**Adaptation strategy:** O.C.D.'s router already does keyword-based task-agent matching (zero API calls, < 50ms). The enhancement is adding a task board to `manifest.json` and integrating it with `USER/worktrees/`.

**Implementation approach:**

1. Extend `manifest.json` with a `tasks` array: `{id, status, claimed_by, branch}`. The `ocd route` command already returns top-3 agents; add `ocd claim <task-id>` and `ocd complete <task-id>` subcommands that update the board atomically.
1. Integrate task board with worktree creation: `ocd claim <task-id>` spins up a worktree in `.claude/worktrees/`, `ocd complete` merges and cleans up.
1. Quality gate on task completion: before marking a task done, run `ocd fix-cycle` on modified files (O.C.D. already has the closed-loop fix commands).

**Impact:** Medium effort. Item 1 is a manifest schema extension + 2 CLI commands (2–3 days). Item 2 is worktree orchestration (3–5 days). Item 3 is hook integration (1 day).

**Acceptance criteria:**

- `ocd claim` and `ocd complete` update `manifest.json` atomically
- Claiming a task creates a worktree; completing merges and cleans up
- Tasks cannot be marked complete without passing `fix-cycle`

### 5.4 Robust Session State Management & Recovery

**Description:** Community patterns include PreCompact handover documents (spawn a fresh instance via `claude -p` to generate a structured `HANDOVER-YYYY-MM-DD.md`), StatusLine-based proactive backups at token thresholds (50K, then every 10K), and post-compaction `/clear` + reload instead of continuing with the lossy summary.

**Value:** Proactive backups prevent the "last-chance save" problem where compaction destroys context before the flush completes. A structured handover document recovers task intent, not just file edit history.

**Adaptation strategy:** O.C.D. currently conflates two things in PreCompact: knowledge extraction (flush to daily log) and state preservation (session card). The session card records file edits but not decisions or intent. Splitting these concerns and adding proactive snapshots improves recovery without adding config surface area.

**Implementation approach:**

1. Upgrade session card to a structured handover document — extend `update_session_card()` to capture: (1) current task description, (2) files modified so far, (3) test results, (4) outstanding decisions, (5) next steps. This is what the community calls a "handover doc." Already runs on PostToolUse Write/Edit; extend the payload.
1. Add StatusLine-based proactive backup — trigger session card enrichment at token thresholds (first at 50K, then every 10K). This gives incremental snapshots rather than a single last-chance save. Uses the existing `ocd.statusline` hook point.
1. Post-compaction reload pattern — on SessionStart, if the session card shows an active task (not just file edits), inject a "Resume from: {task_description}" instruction. This is the `/clear + load backup` pattern, automated.

**Impact:** Small-to-medium effort. Item 1 extends `session_card.py` (1–2 days). Item 2 adds a new hook pattern (2–3 days). Item 3 modifies `session_start.py` (1 day).

**Acceptance criteria:**

- Session card captures task description, decisions, and next steps (not just file paths)
- Proactive snapshots at token thresholds create incremental recovery points
- SessionStart detects active tasks and injects resume instructions

## Process

To add an item from this list:

- Create the skill/agent/linter following existing patterns in [how-to](02-how-to.md) or [reference](03-reference.md)
- Update this file to change the status from `Planned`/`Pending` to `Done`
- Once all items in a category are done, remove that section
