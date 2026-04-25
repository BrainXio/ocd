---
title: Containers
aliases: [containers, docker, images]
tags: [containers]
created: 2026-04-20
updated: 2026-04-20
---

Container images, the CI pipeline that builds and publishes them, and the
security scanning that gates releases.

## Images

| Image | Base | Purpose |
| ------------ | ---------------------- | ----------------------------------------------------------------------------- |
| `ocd-base` | `debian:bookworm-slim` | Hardened foundation: `uv`, `git`, `shellcheck` |
| `ocd-python` | `ocd-base` | Python 3.12+ toolchain: `ruff`, `mypy`, `mdformat` with frontmatter plugin |
| `ocd-node` | `ocd-base` | Node.js 22+ toolchain: `pnpm`, `prettier`, `eslint`, `stylelint`, `htmlhint` |
| `ocd-ollama` | `ocd-base` | Ollama runtime for local LLM inference |
| `ocd` | `ocd-python` | Product image: Python + Node + Ollama + Claude Code + OCD package + dep cache |

All Dockerfiles live in `containers/<name>/Dockerfile`. Each image has its own
`.dockerignore`.

## Build Hierarchy

```
debian:bookworm-slim
  └─ ocd-base
       ├─ ocd-python ── ocd
       ├─ ocd-node
       └─ ocd-ollama
```

Child images use `BASE_IMAGE` and `BASE_TAG` build arguments to select their
parent. In CI, `BASE_IMAGE` points to the GHCR registry; locally it defaults to
the image name.

## Local Builds

```bash
# Simple images build from their directory
docker build -t ocd-base:0.1.0 containers/ocd-base/

# Child images need BASE_TAG
docker build --build-arg BASE_TAG=0.1.0 -t ocd-python:0.1.0 containers/ocd-python/
docker build --build-arg BASE_TAG=0.1.0 -t ocd-node:0.1.0 containers/ocd-node/
docker build --build-arg BASE_TAG=0.1.0 -t ocd-ollama:0.1.0 containers/ocd-ollama/

# Product image builds from project root
docker build --build-arg BASE_TAG=0.1.0 -t ocd:0.1.0 -f containers/ocd/Dockerfile .
```

Lint a Dockerfile before building:

```bash
hadolint containers/ocd-base/Dockerfile
```

The pre-commit hook runs hadolint on staged Dockerfiles when hadolint is
installed. If hadolint is missing, it prints a warning and continues.

## Smoke Tests

Each CI build job runs smoke tests to verify the image is functional:

| Image | Checks |
| ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ocd-base` | `uv --version`, `git --version`, `shellcheck --version`, `whoami` = `ocd` |
| `ocd-python` | `python3 --version`, `ruff --version`, `mypy --version`, `mdformat --version`, `whoami` = `ocd` |
| `ocd-node` | `node --version`, `pnpm --version`, `prettier --version`, `whoami` = `ocd` |
| `ocd-ollama` | `ollama --version` (detached container, 3-second startup wait) |
| `ocd` | `python3 --version`, `node --version`, `ruff --version`, `claude --version`, `ollama --version`, `whoami` = `ocd`, `which ocd`, `/home/ocd/.claude/` exists, `/opt/ocd/templates/` exists |

Run the same checks locally:

```bash
docker run --rm ocd-base:0.1.0 whoami  # should output: ocd
docker run --rm ocd-python:0.1.0 ruff --version
docker run --rm --entrypoint="" ocd:0.1.0 claude --version
```

## CI Pipeline

The container pipeline is defined in `.github/workflows/containers.yml`, separate
from the main CI pipeline to avoid gating code quality checks on slow container
builds.

### Triggers

| Event | Condition |
| ------------------- | --------------------------------------- |
| Push to `main` | Path filters match |
| Pull request | Path filters match |
| `workflow_dispatch` | Manual trigger from GitHub Actions UI |
| Tag push | `v*` pattern (triggers release publish) |

Path filters:

- `containers/**`
- `.hadolint.yaml`
- `trivy.yaml`
- `src/ocd/**`
- `pyproject.toml`
- `package.json`, `package-lock.json`
- `.claude/**`
- `.github/workflows/containers.yml`

### Stages

| Stage | Job | Tool | Details |
| ----------- | ----------------- | ------------------------ | ------------------------------------------------------------------------- |
| 1 (lint) | `lint-dockerfile` | hadolint | Scans all `containers/*/Dockerfile` |
| 2 (build) | `build-base` | build-push-action → GHCR | Builds `ocd-base`, pushes `:sha-<commit>` tag, runs smoke tests |
| 2 (build) | `build-python` | build-push-action → GHCR | Builds `ocd-python` from registry base, pushes `:sha-<commit>` tag |
| 2 (build) | `build-node` | build-push-action → GHCR | Builds `ocd-node` from registry base, pushes `:sha-<commit>` tag |
| 2 (build) | `build-ollama` | build-push-action → GHCR | Builds `ocd-ollama` from registry base, pushes `:sha-<commit>` tag |
| 2 (build) | `build-ocd` | build-push-action → GHCR | Builds `ocd` from registry base, pushes `:sha-<commit>` tag |
| 3 (scan) | `scan-images` | trivy image | Pulls `ocd:sha-<commit>` from GHCR; scans with `trivy.yaml` config |
| 3 (scan) | `scan-images` | trivy SARIF | Generates SARIF report on push; uploads to GitHub Security tab via CodeQL |
| 4 (publish) | `publish-latest` | build-push-action | Pushes `:latest` tags to GHCR on push to `main` only |
| 4 (publish) | `publish-release` | build-push-action | Pushes `:<version>` + `:latest` tags to GHCR on `v*` tag push |

All build jobs use `docker/build-push-action` with GHCR layer caching
(`cache-from`/`cache-to`). Images are pushed with ephemeral `:sha-<commit>` tags
so downstream jobs (scan, publish) can pull them without rebuilding.

### Scan Stage Details

The `scan-images` job pulls the `ocd` image from GHCR (tagged
`:sha-<commit>`) instead of rebuilding it. This eliminates redundant Docker
builds that previously accounted for ~131s per run.

Trivy scans with severity `CRITICAL` and exit code 1, meaning any CRITICAL CVE
fails the pipeline. Accepted risks are documented in `.trivyignore` with NVD
links and rationale.

On push events, trivy also generates a SARIF report and uploads it to the
GitHub Security tab via `github/codeql-action/upload-sarif`.

### Publish Stage Details

Publishing uses `docker/build-push-action` with GHCR layer caching. Child
images use `BASE_IMAGE` set to the GHCR registry path so they pull cached base
layers instead of building from scratch.

| Job | When | Tags pushed |
| ----------------- | -------------- | ----------------------------------------- |
| `publish-latest` | Push to `main` | `:latest` for all 5 images |
| `publish-release` | `v*` tag push | `:<version>` + `:latest` for all 5 images |

Release version is derived from the git tag (e.g., tag `v1.2.3` → version
`1.2.3`). Each child image uses the version-tagged parent as its
`BASE_TAG`.

## Registry

Published images are available at:

```
ghcr.io/brainxio/ocd-base:<tag>
ghcr.io/brainxio/ocd-python:<tag>
ghcr.io/brainxio/ocd-node:<tag>
ghcr.io/brainxio/ocd-ollama:<tag>
ghcr.io/brainxio/ocd:<tag>
```

Tags: `latest` (main push or release), `<version>` (release only).

The workflow requires `packages: write` permission to push to GHCR. Authentication
uses `GITHUB_TOKEN` (automatic in GitHub Actions).

## Inceptive Container

The `ocd` product image is "inceptive" — it embeds the OCD tooling itself so
any project using it immediately benefits from OCD features:

- **OCD package** installed in `/opt/ocd/venv/` (entry points on PATH regardless
  of workspace mount)
- **`.claude/` config** at `/home/ocd/.claude/` (skills, agents, rules, settings)
- **Templates** at `/opt/ocd/templates/` (git hooks, gitleaks config — copied to
  project by `ocd init`)
- **`ocd init`** scaffolds `USER/` structure, seeds project-level templates,
  installs dependencies, sets up git hooks
- **`ocd shell`** starts an interactive bash session with the OCD environment

## Accepted CVEs

Some CRITICAL CVEs in base images have no upstream fix or are not exploitable in
OCD's context. These are documented in `.trivyignore` with NVD links and
acceptance rationale. See [reference](README.md) for the trivy
configuration details.
