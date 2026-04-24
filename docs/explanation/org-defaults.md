# Org Defaults

This repository follows BrainXio's shared defaults policy to maintain **minimal surface area** and **consistent defaults** across the disorder-family projects.

## Shared Configuration Files

The following files are managed centrally in [`BrainXio/.github/defaults/`](https://github.com/brainxio/.github/tree/main/defaults):

- `.yamllint`
- `.hadolint.yaml`
- `.mdformat.toml` (load-bearing — changing `wrap` would reformat every markdown file)
- `.prettierrc` (advisory only, not enforced in CI)

Local copies exist in this repository with a short header (where supported).

## Project-Specific Files

The following remain local and are **not** shared:

- `.gitleaks.toml` (allowlist is project-specific)
- `.trivyignore`, `trivy.yaml`
- `.actrc`
- `.semgrep.yml`

See `defaults/README.md` in `.github` for the canonical source of truth.
