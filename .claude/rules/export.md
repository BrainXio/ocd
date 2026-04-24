---
description: Behavioral guidance for the ocd export command
paths:
  - "src/ocd/kb/export.py"
  - "tests/kb/test_export.py"
---

# Export Command

Rules for the `ocd export` command behavior.

## Default Export Target

- `ocd export` (no flags) writes to `USER/knowledge-export/`
- This directory is gitignored (falls under the `USER/*` pattern)
- Never prompt for confirmation when writing to the default target

## Commit-Friendly Export

- `ocd export --commit` writes to `docs/knowledge/`
- This directory IS version-controlled
- Always warn on stderr before overwriting files in `docs/knowledge/`
- Never delete files in `docs/knowledge/` that have no corresponding DB row

## Wikilink Format

- Same-type links use bare slug: `[[other-concept]]`
- Cross-type links use path prefix: `[[qa/why-tests]]`
- Never include `.md` extensions in wikilinks

## Frontmatter

- Always use `yaml.safe_dump` for consistent formatting
- Include all DB fields: title, aliases, tags, sources, created, updated, score, type
- The `type` field is derived from the path prefix (concepts/ -> concept, etc.)
- Never omit the frontmatter delimiters (`---`)
