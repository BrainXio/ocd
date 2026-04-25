---
title: How-To Guides
aliases: [how-to, guides, tasks]
tags: [how-to]
created: 2026-04-17
updated: 2026-04-24
---

Task-oriented guides. Each section is independent — jump to what you need.

## Add a New Skill

- Create `docs/reference/skills/<name>.md` (canonical location)
- Create a symlink: `ln -s ../../../docs/reference/skills/<name>.md .claude/skills/<name>/SKILL.md`
- Include the metadata header (`name`, `description`, `argument-hint`)
- Define mandatory practices, hard prohibitions, and commit gates
- If the skill has a commit-gate linter, add it to `pyproject.toml` and the CI pipeline (`.github/workflows/ci.yml`)
- Restart the session or use `/skills` to load the new skill
- Add a deny rule in `.claude/settings.json` to protect the SKILL.md file

## Add a New Subagent

- Create `docs/reference/agents/<name>.md` with YAML frontmatter (`name`, `description`, `tools`, `model`)
- Create a symlink: `ln -s ../../docs/reference/agents/<name>.md .claude/agents/<name>.md`
- Quote `description` values containing colons (YAML requirement): `description: 'value with: colon'`
- Write the prompt body with scope, output format, and failure conditions
- Restart the session or use `/agents` to load the new agent

See [reference](../reference/README.md) for the full agent frontmatter schema.

## Add a New Hook

Python hooks live in `src/ocd/hooks/` as part of the installable package. Git hooks live in `.githooks/`.

### Python hook (invoked by Claude Code)

- Create the module in `src/ocd/hooks/` (e.g., `my_hook.py`)
- Add a handler function in `src/ocd/cli.py` under the `hook` subcommand group
- Add an entry in `.claude/settings.json` under the appropriate event key (`SessionStart`, `PreCompact`, `SessionEnd`, `PostToolUse`, `PreToolUse`)
- Set the matcher, command (`ocd hook my-hook`), and timeout
- Add deny rules in `settings.json` to protect the new hook file
- Run `uv sync` to install the updated CLI

### Git hook (invoked by git)

- Create the script in `.githooks/` (e.g., `my-hook`)
- Make it executable: `chmod +x .githooks/my-hook`
- Add an entry in `.githooks/setup-hooks.sh` to make the new hook executable
- Run `bash .githooks/setup-hooks.sh` to configure git's `core.hooksPath`

See [reference](../reference/README.md) for the hook configuration schema and available events.

## Add a Claude Code Rule

Rules are modular markdown files in `.claude/rules/` that provide advisory instructions to Claude Code. They guide behavior where hooks would be too rigid.

- Create `.claude/rules/<name>.md` with a YAML frontmatter `description` field
- For path-scoped rules, add a `paths` list in the frontmatter (YAML array of glob patterns)
- Keep under 60 lines — use positive instructions and add emphasis (`IMPORTANT`, `YOU MUST`) for critical rules
- Unconditional rules (no `paths`) load every session; path-scoped rules load only when matching files are read
- Rules are advisory — use hooks for hard enforcement
- Update `reference/README.md` with the new rule entry

See [reference](../reference/README.md) for the rules registry and [explanation](../explanation/README.md) for the rules-vs-hooks-vs-skills hierarchy.

## Modify a Protected File

Infrastructure files (hooks, scripts, `pyproject.toml`) are protected by deny rules in `.claude/settings.json`:

- Open `.claude/settings.json`
- Find the deny rules under `permissions.deny` that match the target file path (e.g., `Edit(src/ocd/hooks/lint_work.py)`)
- Remove those rules
- Make your changes
- Re-add the deny rule(s)

See [reference](../reference/README.md) for the full list of protected files and deny rule patterns.

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
ocd compile

# Force recompile all logs
ocd compile --all

# Compile a specific log file
ocd compile --file USER/logs/daily/2026-04-17.md

# Lint the knowledge base (structural checks only)
ocd lint-kb --structural-only

# Lint the knowledge base (structural + LLM contradiction checks)
ocd lint-kb

# Query the knowledge base
ocd query "how does the flush pipeline work"

# Query and save answer to a file
ocd query "flush pipeline" --file-back
```

All commands are installed entry points — run them directly or via `ocd <command>`.

## Add External Knowledge

### Via Daily Log Entry

Create a markdown file at `USER/logs/daily/YYYY-MM-DD.md` with structured content, then compile:

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
ocd compile --file USER/logs/daily/2026-04-18.md
```

The compiler will extract concepts and create knowledge articles. The format is advisory — the LLM compiler handles any reasonable markdown. See [explanation](../explanation/README.md#the-feedback-loop) for why the pipeline is content-agnostic.

### Via flush

`ocd flush` accepts any markdown file — it doesn't validate that the content came from a session:

```bash
cat > /tmp/external-knowledge.md << 'EOF'
Key findings from the Go concurrency documentation:
- Goroutines are multiplexed onto OS threads by the Go scheduler
- Channels are the primary synchronization primitive
EOF

ocd flush /tmp/external-knowledge.md external-ingest
```

Flush sends the content to the LLM, extracts structured knowledge, and appends it to today's daily log.

### Via URL

There is no automated URL fetching. Fetch web content yourself and route it through either pathway above:

```bash
curl -s https://example.com/docs | pandoc -f html -t markdown > /tmp/fetched.md
ocd flush /tmp/fetched.md url-ingest
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

The container pipeline runs automatically on path filters (see [containers](../reference/containers.md#triggers)) and on `workflow_dispatch`.

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

See [containers](../reference/containers.md) for the full pipeline documentation.

## Run Autonomous Fix Loops

The `ocd autofix` command wraps the existing fix-cycle commands inside an iterative engine that runs in isolated Git worktrees. It detects violations, applies deterministic fixes, and verifies convergence — without ever modifying the main working tree directly.

```bash
# Fix a single file (fix-cycle strategy)
ocd autofix src/ocd/config.py

# Fix all files under a path (lint-and-fix strategy)
ocd autofix src/ocd/ --batch

# Limit iterations (default: 5)
ocd autofix src/ocd/config.py --max-iterations 3

# Report only — no merge, worktree is cleaned up
ocd autofix src/ocd/config.py --dry-run
```

The loop iterates detect-fix-verify until no violations remain or max iterations is reached. On convergence, it validates the worktree and merges the fix branch. If convergence fails or validation fails, the worktree is preserved under `.claude/worktrees/` for manual review.

All loop iterations are logged to `USER/state/autofix-loop.jsonl`.

## Ingest Raw Knowledge Articles

The `ocd ingest` command processes markdown articles from `USER/knowledge/raw/` into the `USER/knowledge/ocd.db` SQLite database. It parses frontmatter, computes quality scores, deduplicates by content hash, and rebuilds the TF-IDF index.

```bash
# Incremental ingest (only new/changed files)
ocd ingest

# Force re-ingest all files (ignore hashes)
ocd ingest --all

# Report what would be ingested without making changes
ocd ingest --dry-run
```

Raw articles live in subdirectories under `USER/knowledge/raw/`: `concepts/`, `connections/`, `qa/`, and `resources/`. Each file should have YAML frontmatter with `title`, `tags`, `aliases`, and `sources` fields.

The quality score (0.0–1.0) is based on:

| Criterion | Points |
| ------------------ | ------ |
| Has title | 0.2 |
| Has tags | 0.2 |
| Has sources | 0.2 |
| Word count >= 100 | 0.2 |
| Contains wikilinks | 0.2 |

After ingestion, `relevance.py` automatically reads from `ocd.db` when it exists, falling back to flat files when the database is absent.

## Use Vector Search

Semantic vector search lets agents retrieve knowledge by meaning, not just keyword matching. It uses local ONNX embeddings (`BAAI/bge-small-en-v1.5`, 384 dims) and `sqlite-vec` for KNN search.

### Install vec extras

```bash
uv sync --extra vec
```

Without vec extras, all search falls back to TF-IDF + quality scoring. No error is raised — it just degrades gracefully.

### Ingest articles and generate embeddings

```bash
ocd ingest              # automatically generates embeddings when vec extras are installed
ocd ingest --all        # force re-ingest all files
```

### Query with semantic search

```bash
ocd vec search "how to handle authentication"
ocd kb query --relevant-to "authentication" --vectors
```

The `--vectors` flag on `kb query` enables hybrid scoring (TF-IDF + vector + quality). Without it, only TF-IDF + quality is used.

### Rebuild embeddings

```bash
ocd vec rebuild          # regenerate all embeddings from articles table
ocd vec rebuild --force  # force rebuild even if embedding model changed
```

Rebuilding without `--force` raises an error if the configured model differs from the one stored in `vec_metadata`. This prevents accidental model switches from corrupting the vector index.

### Check status

```bash
ocd vec status
```

Shows whether vec extras are available, the embedding count, model name, and database path.
