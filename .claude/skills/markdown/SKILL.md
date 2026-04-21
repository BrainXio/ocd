---
name: markdown
description: Write, refactor, and audit Markdown with consistent structure, frontmatter preservation, and mdformat gates. Use when creating, reviewing, or fixing .md files, documentation, or knowledge base articles.
argument-hint: "[file path or 'audit' or 'format']"
---

# Markdown Skill

You are a Markdown expert who writes clean, consistent, well-structured documents following these conventions.

## Mandatory Rules

- Use CommonMark specification — no non-standard extensions unless explicitly required by the toolchain
- Always run `mdformat` before committing — zero tolerance for formatting drift
- Never use inline HTML unless the feature is unsupported in Markdown (e.g., `<details>` for collapsibles)
- Every file must start with a YAML frontmatter block (`---` delimited) when the project uses frontmatter

## Critical Rules

### Structure

- Use `#` for the document title (H1) — use only one H1 per file
- Use `##` for major sections, `###` for subsections — never skip heading levels
- Use ATX headings (`# Heading`) — never Setext headings (underlines)
- Use bullet lists (`-`) for unordered items — never `*` or `+` (consistency)
- Use `1.` for all ordered list items — mdformat normalizes to sequential numbering
- Add a blank line before and after headings, lists, code blocks, and tables
- Limit line length to 100 characters where practical — mdformat handles wrapping

### Frontmatter

- Preserve YAML frontmatter exactly as written — mdformat may strip `---` delimiters without the `mdformat-frontmatter` plugin
- Use `title`, `created`, `updated` fields in project frontmatter
- Quote values containing colons, special characters, or URLs
- Use `tags` as a YAML list: `tags: [tag1, tag2]`
- Never nest frontmatter — one `---` block at the top, nothing else

### Links and References

- Use reference-style links (`[text][ref]`) for documents with many links or repeated URLs
- Define reference links at the bottom of the file, sorted alphabetically
- Use relative paths for internal links: `[how-to](02-how-to.md)` not `[how-to](/docs/02-how-to)`
- Always include link text — never bare URLs (`https://...`) in running text
- Use autolinks (`<https://...>`) only when the URL itself is the display text

### Code Blocks

- Always specify the language on fenced code blocks: ```` ```bash ````, ```` ```python ````, ```` ```yaml ````
- Use fenced code blocks (triple backticks) — never indented code blocks
- Use inline code (`` ` ` ``) for command names, file paths, variable names, and flag names
- Never use code blocks for emphasis or headings

### Tables

- Use Markdown tables for structured data — never inline HTML tables
- Align columns for readability (left-align text, right-align numbers)
- Use `|` borders on both sides of every row
- Keep tables narrow — if a table exceeds 4 columns or 100 chars per row, consider a list instead

### Emphasis

- Use `**bold**` for strong emphasis or UI labels — never `__bold__`
- Use `*italic*` for light emphasis or terms — never `_italic_`
- Use `~~strikethrough~~` for deprecated or removed items only if the toolchain supports it
- Never use emphasis for headings — use proper `#` headings

## Linting / Formatting

```bash
# Format
mdformat .

# Check without modifying
mdformat --check .

# With frontmatter plugin (required for projects using YAML frontmatter)
mdformat --plugin mdformat-frontmatter .
```

## Anti-Patterns to Avoid

- Setext-style headings (underlines) — use ATX (`#`)
- Mixed list markers (`-` and `*` in the same list) — pick one (`-`) and stick with it
- Bare URLs in running text — use `[link text](url)` or `<url>`
- Inline HTML for layout — use Markdown tables, lists, or blockquotes
- Hard line breaks (`  ` or `\`) inside paragraphs — let mdformat handle wrapping
- Nested blockquotes deeper than one level — restructure the content
- Blank table headers — every column needs a header row
- Missing language on fenced code blocks — always specify the language
- `README.md` files that duplicate content better served by dedicated docs — link instead
