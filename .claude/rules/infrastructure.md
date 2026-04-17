---
description: Deny rule modification procedure for protected files
paths:
  - .claude/settings.json
  - src/ocd/**
  - git_hooks/**
  - .gitleaks.toml
  - pyproject.toml
---

# Infrastructure Files

Rules for modifying protected files covered by deny rules in `.claude/settings.json`.

## Protected Files

The following files have Edit, Write, and Bash rm deny rules:

- `src/ocd/hooks/*.py` (all hook modules)
- `src/ocd/{config,compile,flush,lint,query,utils}.py` (core modules)
- `git_hooks/{commit-msg,pre-commit,pre-push,setup-hooks.sh}`
- `.gitleaks.toml`

You CANNOT directly edit or overwrite these files. The deny rules will block
the operation.

## Modification Procedure

When a protected file must be modified:

1. Open `.claude/settings.json`
1. Locate the deny rules under `permissions.deny` that match the target file
   (e.g., `Edit(src/ocd/hooks/lint_work.py)` and `Write(src/ocd/hooks/lint_work.py)`)
1. Remove those specific deny rules
1. Make the required changes to the protected file
1. Re-add the same deny rules to `permissions.deny`
1. Commit both changes together (settings.json + the protected file)

## IMPORTANT: Do Not Skip Re-adding Deny Rules

The deny rules are the project's immune system. Removing them and forgetting to
re-add creates a window where the infrastructure is unprotected. Always re-add
immediately after editing. Commit both changes in the same commit.

## Why This Exists

Protected files enforce project standards. If they can be freely modified, the
enforcement becomes meaningless. The deny-remove-edit-readd cycle makes
modification a deliberate act, not an accidental one.

See `docs/03-reference.md` for the full list of protected files and deny patterns.
