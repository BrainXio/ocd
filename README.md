# O.C.D. — Obsessive Claude Developer

A Claude Code environment with a personal knowledge base compiled from AI conversations.

Inspired by [Karpathy's LLM KB](https://github.com/karpathy/llm-knowledge-base) architecture: daily conversation logs are the source, compiled knowledge articles are the executable.

> **Note:** This README documents O.C.D. itself because this project *is* O.C.D. When applied to another project, the root README would describe that project's code — O.C.D.'s documentation lives in [index.md](index.md) and `docs/`.

## Structure

```text
(root)             Project — the code being developed (README, docs/, .github/)
.agent/            Data — daily logs, knowledge base, state  (isolated via nested .gitignore)
.claude/           LLM-Processor — scripts, hooks, skills, venv, pyproject.toml
```

## Eight Standards

1. Consistent Defaults
1. Defense in Depth
1. Deterministic Ordering
1. Minimal Surface Area
1. No Dead Code
1. Progressive Simplification
1. Single Source of Truth
1. Structural Honesty

## Documentation

See [index.md](index.md) for the full documentation index.
