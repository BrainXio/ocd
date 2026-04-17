---
description: mdformat, frontmatter plugin, ordered list normalization, CI check paths
paths:
  - '**/*.md'
---

# Markdown Formatting

Project-specific mdformat conventions. The markdown skill (`.claude/skills/markdown/`)
defines general conventions; this rule captures the mdformat pain points that have
caused CI failures in this project.

## IMPORTANT: mdformat-frontmatter Plugin

This project uses YAML frontmatter in `docs/*.md` and `.claude/skills/*/SKILL.md`.
YOU MUST install and use the frontmatter plugin, or mdformat will strip the
`---` delimiters and break the frontmatter:

```
pip install mdformat-frontmatter>=2.0.10
```

The CI lint-markdown job installs both mdformat and mdformat-frontmatter.
The dependency is declared in `pyproject.toml`.

## Ordered List Markers

mdformat normalizes all ordered list items to sequential numbering (1., 2., 3.).
Write `1.` for every ordered list item — mdformat will renumber on format.
Do not fight the normalization by writing manual numbers.

## CI Check Paths

The CI lint-markdown job checks these paths:

```
mdformat --check README.md docs/*.md .claude/skills/*/SKILL.md
```

Run the same command locally before pushing.

## Frontmatter Fields

Project docs use these frontmatter fields:

- `title` (required, quoted if it contains colons)
- `aliases` (list of alternate names)
- `tags` (YAML list: `tags: [tag1, tag2]`)
- `created` (date: YYYY-MM-DD)
- `updated` (date: YYYY-MM-DD, update on every edit)

## Line Length

mdformat wraps at 80 characters by default. The project ruler is at 100.
Let mdformat handle wrapping — do not insert hard line breaks in paragraphs.
