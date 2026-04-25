---
description: Respect org defaults for linter/formatter configs; check source before modifying
---

# Org Defaults Rule

When modifying `.yamllint`, `.hadolint.yaml`, `.mdformat.toml`, or `.prettierrc`, read `docs/explanation/org-defaults.md` first.

These files originate from BrainXio/.github/defaults/. Do not modify them without first checking the org default. If the change is generic, update the source of truth in .github first.

Respect the header comments in each file (where present).
