---
description: Mandatory worktree development rule
---

# Worktree Development Rule

**All development must happen in a dedicated git worktree. Never edit
directly on main.**

## Mandatory Workflow

1. Create a new worktree for any task:

   ```bash
   ocd worktree new <short-kebab-description>
   ```

1. Use conventional branch prefixes:

   - `feat/` — new features
   - `fix/` — bug fixes
   - `refactor/` — code restructuring
   - `experiment/` — exploratory work
   - `docs/` — documentation changes
   - `test/` — test additions/changes
   - `ci/` — CI/CD changes
   - `chore/` — maintenance tasks

1. After work is done:

   - Push branch and create PR from the worktree
   - Delete worktree after merge: `ocd worktree remove <slug>`

## Worktree Location

All worktrees live in `.claude/worktrees/`. Directory names use `+` in
place of `/` from the branch name:

- Branch `feat/add-search` → directory `feat+add-search`
- Branch `fix/parse-error` → directory `fix+parse-error`

## Hotfix Exception

Direct edits on main are allowed **only** for urgent production hotfixes.
In all other cases, use a worktree.

## Enforcement

- Any plan suggesting direct edits on main (outside hotfixes) must be
  rejected.
- Nested worktrees (creating a worktree from inside another worktree) are
  forbidden.
