# OCD Architecture

## Role

OCD is the **discipline & enforcement layer** in the BrainXio ecosystem. It turns
obsessive attention to detail, perfectionism, and ritualistic discipline into an
external quality enforcement system that forces agents to stay aligned with the
Nine Standards at all times.

## Boundaries

- **OCD** drives enforcement (rules, gates, standards)
- **ADHD** handles coordination (message bus, agent lifecycle)
- **ASD** manages memory (knowledge compilation, semantic storage)

OCD never imports or hard-depends on ADHD or ASD. Communication happens
exclusively through the MCP registry when the three servers run together.

## Package Structure

```
src/ocd/
├── __init__.py           # Package marker with version
├── mcp_server.py         # FastMCP server with all tool definitions
├── standards_data.py     # Embedded Nine Standards, hash logic, AI patterns
└── modes/
    └── developer/        # Developer mode placeholder (future mode-specific logic)
```

## MCP Tools

All functionality is exposed as typed MCP tools via FastMCP stdio transport.
There is no CLI, no standalone scripts, and no Agent SDK orchestration.

### Quality Gates

- `ocd_check()` — Fast gate for pre-commit workflows. Runs branch protection,
  standards verification, staged secret scan, and ruff check.
- `ocd_ci_check(fast)` — Full CI mirror. Adds mypy, yamllint, pytest, and
  ruff format checking.

### Standards

- `ocd_standards_verify()` — Verify that the embedded Nine Standards content
  matches its stored hash.
- `ocd_standards_update()` — Report the current standards reference and hash.

### Enforcement

- `ocd_verify_commit(message)` — Check commit messages for prohibited
  attribution patterns.
- `ocd_scan_secrets(staged)` — Run gitleaks to detect secrets.
- `ocd_run_formatters()` — Auto-format source code with ruff and related tools.
- `ocd_lint_work(files)` — Lint specified files and report violations.

## Mode System

OCD operates in modes. Each mode activates a specific bundle of rules, skills,
and gates. The mode system is designed for extensibility:

- **Phase 1 (MVP):** `developer` mode only
- **Future:** `research`, `review`, `ops`, `personal`

## Graceful Degradation

All tools gracefully handle missing external dependencies (gitleaks, mypy,
yamllint, shellcheck). Tools return a `"skipped"` status when a required
binary is not installed, never crashing or throwing exceptions.

## The Nine Standards

The Nine Standards are embedded as Python constants in `standards_data.py`.
They are the immutable quality baseline:

1. No Dead Code
2. Single Source of Truth
3. Consistent Defaults
4. Minimal Surface Area
5. Defense in Depth
6. Structural Honesty
7. Progressive Simplification
8. Deterministic Ordering
9. Inconsistent Elimination
