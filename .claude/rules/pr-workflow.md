---
description: PR labels, body template, merge requirements, and label mapping from commit prefix
---

# PR Workflow

Rules for creating and managing pull requests on this project.

## IMPORTANT: Always Add Labels

Every PR MUST have at least one label. Apply labels based on the conventional
commit prefix of the PR title:

| Prefix | Primary label | Additional labels |
| --------- | ------------- | ---------------------------------------------- |
| feat: | enhancement | + documentation if docs/ changed |
| fix: | bug | |
| docs: | documentation | |
| ci: | ci | + github-actions if .github/workflows/ changed |
| refactor: | enhancement | |
| test: | ci | |
| perf: | enhancement | |
| chore: | enhancement | |
| style: | enhancement | |
| security: | security | |

Add `documentation` as a second label when the PR changes any file in `docs/`.
Add `github-actions` when the PR changes `.github/workflows/`.

## PR Title Format

Use the same conventional commit prefix as the branch: `feat:`, `fix:`, `docs:`,
`ci:`, `chore:`, `refactor:`, `test:`, `perf:`. Keep under 70 characters.

## PR Body Template

Use this structure for every PR:

```
## Summary

1-3 bullet points describing what changed and why.

## Test plan

- [ ] Checklist of verification steps
- [ ] Include both automated (CI) and manual checks
```

Link related issues with `Closes #N` or `Relates to #N` in the body.

## Before Creating a PR

1. Ensure all commits pass the pre-push hook (pytest)
1. Rebase onto main to maintain linear history
1. Verify CI passes on the branch
1. Add labels at creation time using `--label` flags on `gh pr create`

## Merge Requirements

- CI must pass
- All conversations must be resolved
- Use `gh pr merge --squash --delete-branch` (branch protection prevents direct
  push to main; GitHub squash merge creates a single signed commit if GPG is
  configured in GitHub)
- Delete the branch after merge
