# O.C.D. — Obsessive Compulsive Driver

Discipline & enforcement layer for MCP-based agents.

## Overview

OCD enforces the Nine Standards at every quality gate. It operates as a FastMCP
stdio server (`ocd-mcp`) with zero hard dependencies on other packages. When run
alongside ADHD (message bus) and ASD (knowledge memory), all three compose into a
full discipline stack under one agent.

## Installation

```bash
cd behave-ocd
uv sync
uv pip install -e ".[dev]"
```

## MCP Tools

| Tool | Description |
|------|-------------|
| `ocd_set_mode` | Switch active rule/gate/skill set |
| `ocd_get_mode` | Return currently active mode |
| `ocd_check` | Fast local quality gate |
| `ocd_ci_check` | Full CI mirror of all quality gates |
| `ocd_verify_commit` | Check commit messages for prohibited attribution |
| `ocd_scan_secrets` | Scan for secrets using gitleaks |
| `ocd_run_formatters` | Run formatters with auto-fix |
| `ocd_lint_work` | Lint specified files |
| `ocd_standards_verify` | Verify standards hash consistency |
| `ocd_standards_update` | Report current standards reference |

## MCP Configuration

```json
{
  "mcpServers": {
    "ocd": {
      "command": "uv",
      "args": ["--directory", ".", "run", "ocd-mcp"]
    }
  }
}
```

## Development

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest -q
```

## Modes

Phase 1 supports `developer` mode only. Future modes will include `research`,
`review`, `ops`, and `personal`.
