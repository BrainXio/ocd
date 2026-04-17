---
description: Conventional commits, branch naming, no AI attribution, no direct pushes to main
---

# Commit Hygiene

Rules for commit messages, branch naming, and push behavior.

## Conventional Commits

All commit messages MUST follow Conventional Commits:

```
<type>(<optional-scope>): <subject>
```

Types: feat, fix, docs, style, refactor, test, ci, chore, perf, revert

Subject rules:

- Lowercase, imperative mood ("add" not "added")
- No trailing period
- Under 72 characters
- Explain why, not what — the diff shows what

Examples:

- `feat(hooks): add post-merge hook for dependency sync`
- `fix(lint): handle missing linter binary gracefully`
- `docs(reference): add skill registry table`

## Branch Naming

```
<type>/<short-description>
```

Examples: feat/token-refresh, fix/parse-empty-input, docs/split-readme

Branch from main for every change. Delete branches after merge.

## IMPORTANT: No AI Attribution

The commit-msg hook and CI reject these patterns (see `git_hooks/ai-patterns.txt`):

- `Co-Authored-By:` lines
- `Generated with/by/using` lines
- `[AI]` or `[AI-generated]` tags

Do NOT include any of these in commit messages. The hook will block the commit.
If Claude Code's default behavior appends Co-Authored-By, remove it before committing.

## IMPORTANT: No Direct Pushes to Main

The pre-commit hook blocks commits on main. Always create a feature branch:

```
git checkout -b <type>/<description>
```

Never use `--no-verify` to skip hooks. Never force-push to main.

## Staging

Stage specific files with `git add <file>`. Never use `git add -A` or `git add .`.
