---
name: yaml
description: Write, refactor, and audit YAML with consistent formatting, strict typing, and yamllint gates. Use when creating, reviewing, or fixing .yml/.yaml files, configs, CI workflows, or data definitions.
argument-hint: "[file path or 'audit' or 'lint']"
title: "Yaml Skill Reference"
aliases: ["yaml-skill"]
tags: ["skill", "format", "yaml"]
created: "2026-04-24"
updated: "2026-04-24"
---

# YAML Skill

You are a YAML expert who writes clean, consistent, well-structured YAML following these conventions.

## Mandatory Rules

- Always run `yamllint` before committing — zero tolerance for lint errors
- Never use tabs — YAML requires spaces, always use 2-space indentation
- Always quote strings that could be interpreted as non-string types (booleans, numbers, null)
- Never use YAML anchors/aliases (`&`/`*`) unless the toolchain explicitly supports them

## Critical Rules

### Syntax

- Use 2-space indentation — never tabs, never 4-space
- Use `-` for list items with a space after: `- item` not `-item` or `-  item`
- Use `---` document start marker for files with frontmatter or multiple documents
- Use `...` document end marker only when the file has multiple documents
- Use `key:` with a space before the value: `name: value` not `name:value`
- Use `true`/`false` for booleans — never `yes`/`no`/`on`/`off` (ambiguous)
- Use `null` or `~` for null values — never empty values when the key exists
- Use folded scalars (`>`) for long prose — use literal scalars (`|`) for code blocks and scripts
- Use flow syntax (`{}`, `[]`) only for inline single-line maps and sequences — never for nested structures

### Strings and Types

- Quote strings that look like booleans: `"true"`, `"false"`, `"yes"`, `"no"`, `"on"`, `"off"`
- Quote strings that look like numbers: `"3.12"`, `"2024"`, `"0x1F"`
- Quote strings that start with special characters: `"@mention"`, `"#tag"`, `"*glob"`
- Quote colon-containing strings: `"key: value in a string"`
- Use double quotes for strings with escape sequences — use single quotes or no quotes otherwise
- Use `|` or `>` for multiline strings — never use `\n` escape sequences in YAML values
- Never leave a key with no value when the intent is `null` — write `key: null` explicitly

### Structure

- Group related keys together — order by importance: `name`, `on`, `permissions`, `jobs`
- Use consistent key ordering within similar blocks (e.g., all jobs list `runs-on` before `steps`)
- Keep nesting under 5 levels — flatten deep structures with anchors or separate files
- Use comments (`#`) sparingly — explain why, not what
- Leave one blank line between top-level sections for readability
- Never duplicate keys in the same mapping — YAML forbids this per spec

### Configuration Files

- Include a comment header explaining the file's purpose when it's not obvious from context
- Use environment variable substitution (`${VAR}`) only with tools that support it — never expect it in plain YAML
- Use `!reference` tags only in GitLab CI — never use custom tags unless the toolchain documents them
- Keep line length under 120 characters — break long strings with `>` folded scalars
- Use `default` and `override` sections in docker-compose — never mix them in the same service block

### Validation

- Validate against the target tool's schema (JSON Schema for GitHub Actions, GitLab CI, etc.)
- Use `yamllint -d relaxed` for legacy files — use default strict rules for new files
- Test YAML parsing before committing: `python -c "import yaml; yaml.safe_load(open('file.yml'))"`
- Never use `yaml.load()` with the default loader in Python — always use `yaml.safe_load()`

## Linting / Formatting

```bash
# Lint
yamllint .

# Lint with relaxed rules for legacy files
yamllint -d relaxed .

# Validate syntax
python -c "import yaml; yaml.safe_load(open('file.yml'))"

# Format (if prettier is available)
npx prettier --write "**/*.yml"
```

## Anti-Patterns to Avoid

- Tabs for indentation — YAML requires spaces
- Unquoted boolean-like strings (`yes`, `no`, `on`, `off`, `true`, `false`) — always quote these
- Unquoted number-like strings (`"3.12"`, `"1e6"`) — quote when semantically a string
- YAML anchors/aliases in tools that strip them — test before using
- Deep nesting (>5 levels) — flatten the structure
- Duplicate keys in the same mapping — forbidden by the YAML spec
- Empty values without explicit `null` — write `key: null`
- Inline flow syntax for complex nested structures — use block style
- `!!python/object` or other language-specific tags in data files — use JSON or a proper serialization
