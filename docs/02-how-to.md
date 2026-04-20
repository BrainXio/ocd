---
title: How-To Guides
aliases: [how-to, guides, tasks]
tags: [how-to]
created: 2026-04-17
updated: 2026-04-20
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

## Add a Claude Code Rule

Rules are modular markdown files in `.claude/rules/` that provide advisory instructions to Claude Code. They guide behavior where hooks would be too rigid.

- Create `.claude/rules/<name>.md` with a YAML frontmatter `description` field
- For path-scoped rules, add a `paths` list in the frontmatter (YAML array of glob patterns)
- Keep under 60 lines — use positive instructions and add emphasis (`IMPORTANT`, `YOU MUST`) for critical rules
- Unconditional rules (no `paths`) load every session; path-scoped rules load only when matching files are read
- Rules are advisory — use hooks for hard enforcement
- Update `docs/03-reference.md` with the new rule entry

See [reference](03-reference.md) for the rules registry and [explanation](04-explanation.md) for the rules-vs-hooks-vs-skills hierarchy.

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

## Build and Test a Container Image

Container images live in `containers/<name>/Dockerfile`. Each image has its own `.dockerignore`.

```bash
# Build an image (simple images build from their directory)
docker build -t ocd-base:0.1.0 containers/ocd-base/

# Build an image that needs dependency specs (ocd product image)
docker build --build-arg BASE_TAG=0.1.0 -t ocd:0.1.0 -f containers/ocd/Dockerfile .

# Smoke test — verify tools are installed and non-root user is set
docker run --rm ocd-base:0.1.0 uv --version
docker run --rm ocd-base:0.1.0 whoami  # should output: ocd

# Lint a Dockerfile
hadolint containers/ocd-base/Dockerfile
```

The pre-commit hook runs hadolint on staged Dockerfiles if hadolint is installed. If hadolint is not installed, it prints a warning and continues — install it from <https://github.com/hadolint/hadolint#installing>.

## Trigger Container CI

The container pipeline runs automatically on path filters (see [containers](09-containers.md#triggers)) and on `workflow_dispatch`.

Trigger manually from the GitHub Actions UI:

1. Go to **Actions** → **Containers** workflow
1. Click **Run workflow** → select branch → **Run workflow**

Or via `gh` CLI:

```bash
gh workflow run containers.yml
```

## Publish a Container Release

1. Ensure CI passes on `main` and the container build + scan succeeds
1. Create and push a version tag:

```bash
git tag v1.2.3
git push origin v1.2.3
```

The `publish-release` job builds all 5 images and pushes `:<version>` + `:latest`
tags to GHCR. The version is derived from the tag (e.g., `v1.2.3` → `1.2.3`).

To verify published images:

```bash
docker pull ghcr.io/brainxio/ocd:1.2.3
docker run --rm --entrypoint="" ghcr.io/brainxio/ocd:1.2.3 whoami  # ocd
```

See [containers](09-containers.md) for the full pipeline documentation.
