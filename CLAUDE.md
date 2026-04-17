# O.C.D. — Obsessive Claude Developer

Claude Code project with knowledge pipeline, enforcement hooks, and language skills.
See `docs/` for full documentation; this file is the rules index.

## Project Layout

- `src/ocd/` — installable Python package (hooks, scripts, config)
- `git_hooks/` — shell git hooks (pre-commit, commit-msg, pre-push)
- `.claude/` — settings.json, skills/, agents/, rules/
- `docs/` — Diataxis-structured documentation
- `.agent/` — daily logs, knowledge base, state (gitignored)

## Rules

Unconditional rules (always loaded):

- `.claude/rules/commit-hygiene.md` — conventional commits, branch naming, AI attribution
- `.claude/rules/pr-workflow.md` — PR labels, body template, merge checks
- `.claude/rules/doc-sync.md` — update reference and planning docs when shipping features

Path-scoped rules (loaded on file Read):

- `.claude/rules/markdown.md` — mdformat, frontmatter, list markers (scoped to `**/*.md`)
- `.claude/rules/infrastructure.md` — deny rules, protected file procedure (scoped to infrastructure paths)

## Priority

When rules conflict with a skill file, rules win. Rules codify project-specific
process; skills define language-specific conventions. When a hook blocks an action,
the hook wins unconditionally — rules are advisory, hooks enforce.

## Quick Reference

- Package manager: uv
- Linter gate: ruff + mypy + mdformat + shellcheck + yamllint
- Test gate: pytest (pre-push hook)
- Branch protection: no commits on main (pre-commit hook)
- AI attribution: blocked by commit-msg hook and CI
