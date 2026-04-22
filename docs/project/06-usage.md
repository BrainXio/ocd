---
title: "Usage: An Intelligence's Guide to O.C.D."
aliases: [usage, ai-guide, another-intelligence]
tags: [ai, prompts, usage]
created: 2026-04-17
updated: 2026-04-17
---

You are an intelligence operating within the O.C.D. framework. This is your decision layer — what you can do, how to do it, and the prompts that unlock the system.

## What You Are Working With

O.C.D. augments you with four layers:

- **Context injection** — KB index and recent daily log at session start
- **Enforcement** — Hooks lint in real time; skills define per-language correctness
- **Persistence** — Knowledge pipeline captures insights and feeds them back
- **Delegation** — Subagents handle bounded analysis (dead code, deps, lint checks)

See [explanation](04-explanation.md) for the architecture and design rationale.

## Prompt Cookbook

### Starting a Feature

```
I need to add rate limiting to the API. What patterns does the knowledge base suggest?
```

```
/ocd audit the API layer — check the python skill for the right patterns, then propose a rate limiting design
```

### Code Review and Refactoring

```
Run the hook-integrity agent, then based on its findings, update the CI workflow to close any parity gaps.
```

```
Run dead-code-hunter on src/ocd/ and git_hooks/. Report what it finds, then clean up anything that's truly unused.
```

### Knowledge Capture

```
We just made a significant architectural decision about how subagents share state. Compile today's log so the knowledge base captures it.
```

```
What does the knowledge base say about error propagation in the hook system?
```

### Cross-Language Work

```
Write a Dockerfile for this service. Use the docker skill — multi-stage build, pinned digests, no latest tags.
```

```
Refactor the Kubernetes deployment. Apply the kubernetes skill — add resource limits, liveness probes, runAsNonRoot.
```

```
Write a bash script to automate the deployment pipeline. The bash skill requires set -euo pipefail and shellcheck must pass with zero warnings.
```

### Expanding the System

```
Create a python subagent that audits type annotation coverage — check for missing return types, Any usage, and bare except clauses. Follow the pattern in .claude/agents/exception-auditor.md.
```

```
Add a css skill following the same structure as the python skill. Mandatory: modern CSS (Grid, Flexbox, Custom Properties). Prohibited: !important except in utility classes. Commit gate: stylelint when available.
```

### Troubleshooting

```
The ocd-lint-work hook is failing on commit. Run lint-status to see which linters are failing and on which files.
```

```
CI is failing on the check-commit-messages job. Show me the git_hooks/ai-patterns.txt file so I can see what pattern my commit message matched.
```

## Adding External Knowledge

The pipeline is content-agnostic — anything you can get into a markdown file can be fed to `ocd-flush` or `ocd-compile`.

### Daily Log Entry

Create `.agent/daily/YYYY-MM-DD.md` with structured content and compile it. See [how-to](02-how-to.md#add-external-knowledge) for the full format.

### flush Ingestion

Pass any markdown file directly to `ocd-flush`:

```bash
cat > /tmp/external.md << 'EOF'
Key findings from the Go concurrency docs:
- Goroutines are multiplexed onto OS threads
- Channels are the primary synchronization primitive
EOF

ocd-flush /tmp/external.md external-ingest
```

### URL-Based Knowledge

No automated URL fetching exists. Fetch and route manually:

```
Fetch the Rust ownership documentation from doc.rust-lang.org and summarize the key rules. Then create a daily log entry and compile it.
```

```
Read https://docs.docker.com/build/cache/ and extract the key caching strategies. Write them to a temp file, then run ocd-flush to ingest them.
```

## Navigation

- [Getting Started](01-getting-started.md) — first 15 minutes walkthrough
- [How-To](02-how-to.md) — step-by-step task guides
- [Reference](03-reference.md) — all tables, schemas, and specs
- [Explanation](04-explanation.md) — architecture, standards, design rationale
- [Planning](05-planning.md) — record gaps and planned improvements
- [Development Setup](07-development.md) — venv activation and local development workflow
