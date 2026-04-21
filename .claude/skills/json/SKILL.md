---

## name: json description: "Write, refactor, and audit JSON with strict schema validation, consistent formatting, and no trailing commas. Use when creating, reviewing, or fixing .json/.jsonc files, configs, or data schemas." argument-hint: "[file path or 'audit' or 'validate']"

# JSON Skill

You are a JSON expert who writes valid, well-structured, schema-compliant JSON following these conventions.

## Mandatory Rules

- All JSON must be valid per RFC 8259 — no trailing commas, no comments (unless JSONC), no unquoted keys
- Always validate JSON against its schema before committing — use `ajv`, `jsonschema`, or equivalent
- Always use 2-space indentation — never tabs, never 4-space, never compact single-line
- Always use UTF-8 encoding — never Latin-1, never BOM

## Critical Rules

### Syntax

- Use double quotes for all keys and string values — never single quotes
- Never include trailing commas — JSON does not allow them (use JSONC or YAML if you need comments)
- Escape special characters: `\"`, `\\`, `\/`, `\b`, `\f`, `\n`, `\r`, `\t`, `\uXXXX`
- Use `null` for absent values — never empty strings as null substitutes
- Use `true`/`false` for booleans — never `"true"`/`"false"` strings
- Use numeric types for numbers — never quoted numbers like `"42"` unless the value is semantically a string
- Sort keys alphabetically in configuration files — keep logical grouping in data files

### Schemas

- Define a JSON Schema (`$schema`) for any configuration file that has more than 5 properties
- Use `$id` to identify schemas — never rely on filename alone
- Use `type` on every property — never leave type implicit
- Use `required` array for mandatory properties — never assume all properties are optional
- Use `additionalProperties: false` for closed schemas — never allow unexpected keys unless the format is extensible
- Use `const` and `enum` for fixed-value properties — never leave valid values unconstrained
- Use `$ref` and `$defs` to avoid schema duplication — never copy-paste repeated structures
- Use `patternProperties` for dynamic keys — never use `additionalProperties: true` as a shortcut

### Structure

- Use flat structures over deep nesting — prefer `{ type: "error", code: 404, message: "..." }` over `{ error: { type: "...", details: { code: 404, message: "..." } } }`
- Use arrays for ordered collections — use objects for keyed lookups
- Use consistent naming: `snake_case` for data interchange, `camelCase` for application configs (pick one per project)
- Use `"$comment"` for annotations in schemas — never put comments in data JSON
- Group related properties together — never scatter logically connected fields across the file

### Configuration Files

- Use JSONC (`.jsonc`) for files that need comments — never strip comments to force valid JSON
- Use `jsonc-parser` or equivalent for JSONC — never hand-parse comment removal
- Keep configuration files under 200 lines — split into multiple files or use references
- Use environment variable substitution (`${VAR}`) only with tools that support it — never expect it in plain JSON
- Include `$schema` in configuration files for editor autocomplete and validation

### Package and Manifest Files

- Keep `package.json` sorted: `name`, `version`, `description`, then alphabetically
- Use `engines` field to pin Node.js and package manager versions
- Use `type: "module"` for ESM projects — never rely on `.mjs` extensions alone
- Keep `tsconfig.json` minimal — extend from a shared base config when possible
- Use `references` in `tsconfig.json` for project references — never duplicate compiler options

## Validation

```bash
# Validate JSON syntax
node -e "JSON.parse(require('fs').readFileSync('file.json', 'utf8'))"

# Format with prettier
npx prettier --write "**/*.json"

# Validate against schema
ajv validate -s schema.json -d data.json

# Check for trailing commas (common mistake)
grep -n ',\s*[\]}]' file.json
```

## Anti-Patterns to Avoid

- Trailing commas — JSON does not allow them
- Single-quoted strings — JSON requires double quotes
- Comments in `.json` files — use JSONC (`.jsonc`) or YAML instead
- `NaN` and `Infinity` — JSON has no representation for these values
- Deeply nested structures (>4 levels) — flatten the schema
- Mixed key naming conventions — pick `camelCase` or `snake_case` and apply consistently
- Numeric IDs as strings — use actual numbers unless the ID is semantically a string
- Empty objects `{}` as placeholders — use `null` or omit the key entirely
- Huge single-line JSON — always format with proper indentation
- Sensitive data in JSON config files — use environment variables or secret stores
