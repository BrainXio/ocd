---
title: How-To Guides
aliases: [how-to, guides, tasks]
tags: [how-to]
created: 2026-04-17
updated: 2026-04-17
---

Task-oriented guides. Each section is independent — jump to what you need.

## Add a New Skill

- Create `.claude/skills/<name>/SKILL.md`
- Include the metadata header (`name`, `description`, `argument-hint`)
- Define mandatory practices, hard prohibitions, and commit gates
- If the skill has a commit-gate linter, add it to `pyproject.toml` and the CI pipeline (`.github/workflows/ci.yml`)
- Restart the session or use `/skills` to load the new skill
- Add a deny rule in `.claude/settings.json` to protect the SKILL.md file

## Add a New Subagent

- Create `.claude/agents/<name>.md` with YAML frontmatter (`name`, `description`, `tools`, `model`)
- Quote `description` values containing colons (YAML requirement): `description: 'value with: colon'`
- Write the prompt body with scope, output format, and failure conditions
- Restart the session or use `/agents` to load the new agent

See [reference](03-reference.md) for the full agent frontmatter schema.

## Add a New Hook

Python hooks live in `src/ocd/hooks/` as part of the installable package. Git hooks live in `git_hooks/`.

### Python hook (invoked by Claude Code)

- Create the module in `src/ocd/hooks/` (e.g., `my_hook.py`)
- Add an entry point in `pyproject.toml` under `[project.scripts]`: `ocd-my-hook = "ocd.hooks.my_hook:main"`
- Add an entry in `.claude/settings.json` under the appropriate event key (`SessionStart`, `PreCompact`, `SessionEnd`, `PostToolUse`, `PreToolUse`)
- Set the matcher, command (`ocd-my-hook`), and timeout
- Add deny rules in `settings.json` to protect the new hook file
- Run `uv sync` to install the new entry point

### Git hook (invoked by git)

- Create the script in `git_hooks/` (e.g., `my-hook`)
- Make it executable: `chmod +x git_hooks/my-hook`
- Add a symlink entry in `git_hooks/setup-hooks.sh`
- Run `bash git_hooks/setup-hooks.sh` to install the symlink

See [reference](03-reference.md) for the hook configuration schema and available events.

## Modify a Protected File

Infrastructure files (hooks, scripts, `pyproject.toml`) are protected by deny rules in `.claude/settings.json`:

- Open `.claude/settings.json`
- Find the deny rules under `permissions.deny` that match the target file path (e.g., `Edit(src/ocd/hooks/lint_work.py)`)
- Remove those rules
- Make your changes
- Re-add the deny rule(s)

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
ocd-compile

# Force recompile all logs
ocd-compile --all

# Compile a specific log file
ocd-compile --file .agent/daily/2026-04-17.md

# Lint the knowledge base (structural checks only)
ocd-lint-kb --structural-only

# Lint the knowledge base (structural + LLM contradiction checks)
ocd-lint-kb

# Query the knowledge base
ocd-query "how does the flush pipeline work"

# Query and save answer to a file
ocd-query "flush pipeline" --file-back
```

All commands are installed entry points — run them directly or via `uv run ocd-<command>`.

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
ocd-compile --file .agent/daily/2026-04-18.md
```

The compiler will extract concepts and create knowledge articles. The format is advisory — the LLM compiler handles any reasonable markdown. See [explanation](04-explanation.md#the-feedback-loop) for why the pipeline is content-agnostic.

### Via flush

`ocd-flush` accepts any markdown file — it doesn't validate that the content came from a session:

```bash
cat > /tmp/external-knowledge.md << 'EOF'
Key findings from the Go concurrency documentation:
- Goroutines are multiplexed onto OS threads by the Go scheduler
- Channels are the primary synchronization primitive
EOF

ocd-flush /tmp/external-knowledge.md external-ingest
```

Flush sends the content to the LLM, extracts structured knowledge, and appends it to today's daily log.

### Via URL

There is no automated URL fetching. Fetch web content yourself and route it through either pathway above:

```bash
curl -s https://example.com/docs | pandoc -f html -t markdown > /tmp/fetched.md
ocd-flush /tmp/fetched.md url-ingest
```
