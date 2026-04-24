---
description: mdformat, frontmatter plugin, ordered list normalization, CI check paths
paths:
  - "**/*.md"
---

# Markdown Formatting

Project-specific mdformat conventions. The markdown skill (`.claude/skills/markdown/`)
defines general conventions; this rule captures the mdformat pain points that have
caused CI failures in this project.

## IMPORTANT: Frontmatter Plugin

This project uses a custom mdformat plugin (`mdformat_frontmatter_preserve`) that
preserves YAML frontmatter quote styles. It replaces the upstream `mdformat-frontmatter`
plugin, which normalizes double quotes to single quotes. Always install the project
(via `uv sync`) so the custom plugin is registered. Do NOT install the upstream
`mdformat-frontmatter` package — it conflicts with our preserve-quotes plugin.

## IMPORTANT: Skill File Frontmatter

Skill files (`.claude/skills/*/SKILL.md`) use proper YAML frontmatter with `---`
delimiters — not `## heading` metadata lines and not `______` horizontal rules.
mdformat normalizes thematic breaks (dashes or underscores) to `______`, but
preserves `---` as frontmatter delimiters when the frontmatter plugin is active.
Always use YAML frontmatter in skill files.

## Configuration

mdformat settings are pinned in `.mdformat.toml` at the project root. The current
configuration sets `wrap = "keep"` (preserve existing line wrapping). Do not add
`--wrap` flags on the command line — let the config file control wrapping behavior.

## Ordered List Markers

mdformat normalizes all ordered list items to sequential numbering (1., 2., 3.).
Write `1.` for every ordered list item — mdformat will renumber on format.
Do not fight the normalization by writing manual numbers.

## CI Check Paths

The CI lint-markdown job checks these paths:

```
mdformat --check README.md docs/*.md docs/**/*.md .claude/skills/*/SKILL.md .claude/agents/*.md .claude/rules/*.md
```

Run the same command locally before pushing.

## Frontmatter Fields

Project docs use these frontmatter fields:

- `title` (required, quoted if it contains colons)
- `aliases` (list of alternate names)
- `tags` (YAML list: `tags: [tag1, tag2]`)
- `created` (date: YYYY-MM-DD)
- `updated` (date: YYYY-MM-DD, update on every edit)

Skill files use these frontmatter fields:

- `name` (skill name, matches directory name)
- `description` (quoted string describing the skill)
- `argument-hint` (quoted string showing expected arguments)

## Line Length

mdformat uses `wrap = "keep"` (configured in `.mdformat.toml`), which preserves
existing line wrapping. Let mdformat handle wrapping — do not insert hard line
breaks in paragraphs.
