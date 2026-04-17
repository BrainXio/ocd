---
title: How-To Guides
aliases: [how-to, guides, tasks]
tags: [how-to]
created: 2026-04-17
updated: 2026-04-17
---

Task-oriented guides. Each section is independent — jump to what you need.

## Add a New Skill

1. Create `.claude/skills/<name>/SKILL.md`
1. Include the metadata header (`name`, `description`, `argument-hint`)
1. Define mandatory practices, hard prohibitions, and commit gates
1. If the skill has a commit-gate linter, add it to `.claude/pyproject.toml` and the CI pipeline (`.github/workflows/ci.yml`)
1. Restart the session or use `/skills` to load the new skill
1. Add a deny rule in `.claude/settings.json` to protect the SKILL.md file

## Add a New Subagent

1. Create `.claude/agents/<name>.md` with YAML frontmatter (`name`, `description`, `tools`, `model`)
1. Quote `description` values containing colons (YAML requirement): `description: 'value with: colon'`
1. Write the prompt body with scope, output format, and failure conditions
1. Restart the session or use `/agents` to load the new agent

See [reference](03-reference.md) for the full agent frontmatter schema.

## Add a New Hook

1. Create the script in `.claude/hooks/` (e.g., `my-hook.py`)
1. Add an entry in `.claude/settings.json` under the appropriate event key (`SessionStart`, `PreCompact`, `SessionEnd`, `PostToolUse`, `PreToolUse`)
1. Set the matcher, command, and timeout
1. If it's a git hook, add a symlink entry in `.claude/scripts/setup-hooks.sh`
1. Add deny rules in `settings.json` to protect the new hook file

See [reference](03-reference.md) for the hook configuration schema and available events.

## Modify a Protected File

Infrastructure files (hooks, scripts, `pyproject.toml`) are protected by deny rules in `.claude/settings.json`:

1. Open `.claude/settings.json`
1. Find the deny rules under `permissions.deny` that match the target file path (e.g., `Edit(.claude/hooks/pre-commit)`)
1. Remove those rules
1. Make your changes
1. Re-add the deny rule(s)

See [reference](03-reference.md) for the full list of protected files and deny rule patterns.

## Test CI Locally

Use [act](https://github.com/nektos/act) to run the GitHub Actions pipeline locally:

```bash
act -l                          # list all jobs
act push -s GITHUB_TOKEN="$(gh auth token)"   # test full push pipeline
act -j lint-python -s GITHUB_TOKEN="$(gh auth token)"  # test single job
```

## Run Manual Pipeline Commands

The knowledge pipeline runs automatically, but you can control it manually:

```bash
# Compile knowledge from new/changed daily logs
uv --directory .claude run python scripts/compile.py

# Force recompile all logs
uv --directory .claude run python scripts/compile.py --all

# Compile a specific log file
uv --directory .claude run python scripts/compile.py --file .agent/daily/2026-04-17.md

# Lint the knowledge base (structural checks only)
uv --directory .claude run python scripts/lint.py --structural-only

# Lint the knowledge base (structural + LLM contradiction checks)
uv --directory .claude run python scripts/lint.py

# Query the knowledge base
uv --directory .claude run python scripts/query.py "how does the flush pipeline work"

# Query and save answer to a file
uv --directory .claude run python scripts/query.py "flush pipeline" --file-back
```

## Add External Knowledge

### Via Daily Log Entry

Create a markdown file at `.agent/daily/YYYY-MM-DD.md` with structured content, then compile:

```markdown
# Daily Log: 2026-04-18

## Sessions

## Memory Maintenance

### External Reference (09:00)

**Context:** Key insights from the Kubernetes documentation.

**Key Exchanges:**
- Init containers run before app containers
- Pod phases: Pending → Running → Succeeded/Failed

**Decisions Made:**
- Use startup probes for slow-starting containers

**Lessons Learned:**
- readinessProbe failures remove pods from Service endpoints without restarting
```

```bash
uv --directory .claude run python scripts/compile.py --file .agent/daily/2026-04-18.md
```

The compiler will extract concepts and create knowledge articles. The format is advisory — the LLM compiler handles any reasonable markdown. See [explanation](04-explanation.md#the-feedback-loop) for why the pipeline is content-agnostic.

### Via flush.py

flush.py accepts any markdown file — it doesn't validate that the content came from a session:

```bash
cat > /tmp/external-knowledge.md << 'EOF'
Key findings from the Go concurrency documentation:
- Goroutines are multiplexed onto OS threads by the Go scheduler
- Channels are the primary synchronization primitive
EOF

uv --directory .claude run python scripts/flush.py /tmp/external-knowledge.md external-ingest
```

flush.py sends the content to the LLM, extracts structured knowledge, and appends it to today's daily log.

### Via URL

There is no automated URL fetching. Fetch web content yourself and route it through either pathway above:

```bash
curl -s https://example.com/docs | pandoc -f html -t markdown > /tmp/fetched.md
uv --directory .claude run python scripts/flush.py /tmp/fetched.md url-ingest
```
