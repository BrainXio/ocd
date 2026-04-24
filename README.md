# O.C.D. — Obsessive Claude Developer

A Claude Code environment with a personal knowledge base compiled from AI conversations.

Inspired by [Karpathy's LLM KB](https://github.com/karpathy/llm-knowledge-base) architecture: daily conversation logs are the source, compiled knowledge articles are the executable.

> **Note:** This README documents O.C.D. itself because this project _is_ O.C.D. When applied to another project, the root README would describe that project's code — O.C.D.'s documentation lives in `docs/`.

## Structure

```text
(root)             Project source, tests, docs, pyproject.toml
src/ocd/           Installable Python package (hooks, scripts, config, utils)
.githooks/         Shell git hooks (commit-msg, pre-commit) + setup script
USER/            Data — daily logs, knowledge base, state (git-ignored)
.claude/           LLM-Processor config — settings.json, skills/, agents/
```

## Setup

```bash
git clone <repo-url> && cd ocd
bash .githooks/setup-hooks.sh
uv sync
```

## Nine Standards

1. Consistent Defaults
1. Defense in Depth
1. Deterministic Ordering
1. Inconsistent Elimination
1. Minimal Surface Area
1. No Dead Code
1. Progressive Simplification
1. Single Source of Truth
1. Structural Honesty

## Documentation

See [docs/index.md](docs/index.md) for the full documentation index.
