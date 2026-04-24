---
description: Update reference and planning docs when shipping features
---

# Documentation Sync

Rules for keeping `docs/` in sync with codebase changes.

## When Shipping a Feature

After merging a feature that adds, removes, or changes project infrastructure,
YOU MUST update these documents:

1. **docs/reference/README.md** — Add or update entries in the relevant registry
   table (skills, agents, hooks, entry points, deny rules, CI pipeline stages)

1. **docs/planning.md** — Change the status of shipped items from
   "Planned"/"Pending" to "Done". Remove sections where all items are done.

1. **docs/how-to/README.md** — Add a how-to section if the feature introduces a new
   user-facing workflow not covered by an existing section.

## When to Sync

Update reference and planning docs BEFORE creating the PR, so the PR includes
the documentation changes alongside the code changes. Do not defer doc updates.

## What NOT to Update

- `README.md` — only changes when project structure or setup changes
- `docs/how-to/ai-usage.md` — only changes when the AI-facing workflow changes
- `docs/explanation/README.md` — only changes when architecture or rationale changes

## Verification

Before finalizing a PR, check: did this PR add a skill, agent, hook, entry point,
deny rule, or CI job? If yes, `docs/reference/README.md` MUST be updated.
