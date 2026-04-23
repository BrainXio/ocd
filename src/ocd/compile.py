"""Compile daily conversation logs into structured knowledge articles.

This is the "LLM compiler" - it reads daily logs (source code) and produces
organized knowledge articles (the executable).

Usage:
    ocd compile                    # compile new/changed logs only
    ocd compile --all              # force recompile everything
    ocd compile --file daily/2026-04-01.md  # compile a specific log
    ocd compile --dry-run          # show what would be compiled
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Any

from ocd.config import (
    CONCEPTS_DIR,
    CONNECTIONS_DIR,
    DAILY_DIR,
    KNOWLEDGE_DIR,
    PROJECT_ROOT,
    USER_DIR,
    now_iso,
)
from ocd.utils import (
    file_hash,
    list_raw_files,
    list_wiki_articles,
    load_state,
    read_wiki_index,
    save_state,
)


def _build_paths_section() -> str:
    """Single source of truth for all paths fed to the LLM."""
    return f"""## Paths (Single Source of Truth)

- CONCEPTS_DIR     : {CONCEPTS_DIR}
- CONNECTIONS_DIR  : {CONNECTIONS_DIR}
- KNOWLEDGE_INDEX  : {KNOWLEDGE_DIR / "index.md"}
- KNOWLEDGE_LOG    : {KNOWLEDGE_DIR / "log.md"}

All file writes and updates MUST use exactly these paths. Never assume any other layout."""


# ── Inline schema ─────────────────────────────────────────────────────
SCHEMA = """\
# Knowledge Base Article Format

Every article is a markdown file with YAML frontmatter and structured sections.

## Frontmatter (required)

```yaml
---
title: "Article Title"
aliases: [alternative-name, other-name]
tags: [category, subcategory]
sources:
  - "daily/YYYY-MM-DD.md"
created: YYYY-MM-DD
updated: YYYY-MM-DD
---
```

## Sections (required)

### Key Points
- 3-5 bullet points summarizing the concept

### Details
- 2+ paragraphs explaining the concept in depth

### Related Concepts
- [[concepts/other-article]] - Brief explanation of relationship

### Sources
- [[daily/YYYY-MM-DD.md]] - What was discovered in this session

## Wikilinks

Use `[[concepts/slug]]` format to link between articles. Links must point to
files that exist under the directories listed in the Paths section.
"""


async def compile_daily_log(log_path: Path, state: dict[str, Any]) -> float:
    """Compile a single daily log into knowledge articles.

    Returns the API cost of the compilation.
    """
    from claude_agent_sdk import (
        AssistantMessage,
        ClaudeAgentOptions,
        ResultMessage,
        TextBlock,
        query,
    )

    log_content = log_path.read_text(encoding="utf-8")
    wiki_index = read_wiki_index()

    # Read existing articles for context
    existing_articles_context = ""
    existing: dict[str, str] = {}
    for article_path in list_wiki_articles():
        rel = article_path.relative_to(KNOWLEDGE_DIR)
        existing[str(rel)] = article_path.read_text(encoding="utf-8")

    if existing:
        parts = []
        for rel_path, content in existing.items():
            parts.append(f"### {rel_path}\n```markdown\n{content}\n```")
        existing_articles_context = "\n\n".join(parts)

    timestamp = now_iso()

    paths_section = _build_paths_section()

    prompt = f"""You are a knowledge compiler. Your job is to read a daily conversation log
and extract knowledge into structured wiki articles.

## Schema

{SCHEMA}

{paths_section}

## Current Wiki Index

{wiki_index}

## Existing Wiki Articles

{existing_articles_context if existing_articles_context else "(No existing articles yet)"}

## Daily Log to Compile

**File:** {log_path.name}

{log_content}

## Your Task

Read the daily log above and compile it into wiki articles following the schema exactly.

### Rules:

1. **Extract key concepts** - Identify 3-7 distinct concepts worth their own article
2. **Create concept articles** - One .md file per concept in the CONCEPTS_DIR from the Paths section
   - Use the exact article format from the Schema above (YAML frontmatter + sections)
   - Include `sources:` in frontmatter pointing to the daily log file
   - Use `[[concepts/slug]]` wikilinks to link to related concepts
   - Write in encyclopedia style - neutral, comprehensive
   relationships between 2+ existing concepts, write to
   CONNECTIONS_DIR (see Paths section)
4. **Update existing articles** if this log adds new information to concepts already in the wiki
   - Read the existing article, add the new information, add the source to frontmatter
5. **Update the knowledge index** - Add new entries to the
   KNOWLEDGE_INDEX path (see Paths section)
   - Each entry: `| [[path/slug]] | One-line summary | source-file | {timestamp[:10]} |`
6. **Append to the knowledge log** - Add a timestamped entry to the
   KNOWLEDGE_LOG path (see Paths section):
   ```
   ## [{timestamp}] compile | {log_path.name}
   - Source: daily/{log_path.name}
   - Articles created: [[concepts/x]], [[concepts/y]]
   - Articles updated: [[concepts/z]] (if any)
   ```

Write ONLY to the directories and files listed in the Paths section above.
The Paths section is authoritative — do not hardcode or assume any other locations.

### Quality standards:
- Every article must have complete YAML frontmatter
- Every article must link to at least 2 other articles via [[wikilinks]]
- Key Points section should have 3-5 bullet points
- Details section should have 2+ paragraphs
- Related Concepts section should have 2+ entries
- Sources section should cite the daily log with specific claims extracted
"""

    cost = 0.0

    try:
        async for message in query(
            prompt=prompt,
            options=ClaudeAgentOptions(
                cwd=str(PROJECT_ROOT),
                system_prompt={"type": "preset", "preset": "claude_code"},
                allowed_tools=["Read", "Write", "Edit", "Glob", "Grep"],
                permission_mode="acceptEdits",
                max_turns=30,
            ),
        ):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        pass  # compilation output - LLM writes files directly
            elif isinstance(message, ResultMessage):
                cost = message.total_cost_usd or 0.0
                print(f"  Cost: ${cost:.4f}")
    except Exception as e:
        print(f"  Error: {e}")
        return 0.0

    # Update state
    rel_path = log_path.name
    state.setdefault("ingested", {})[rel_path] = {
        "hash": file_hash(log_path),
        "compiled_at": now_iso(),
        "cost_usd": cost,
    }
    state["total_cost"] = state.get("total_cost", 0.0) + cost
    save_state(state)

    return cost


def main() -> None:
    parser = argparse.ArgumentParser(description="Compile daily logs into knowledge articles")
    parser.add_argument("--all", action="store_true", help="Force recompile all logs")
    parser.add_argument("--file", type=str, help="Compile a specific daily log file")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be compiled")
    parser.add_argument(
        "--manifest", action="store_true", help="Rebuild agent manifest after compilation"
    )
    parser.add_argument(
        "--update-standards-hash",
        action="store_true",
        help="Recompute and update the standards.md hash",
    )
    args = parser.parse_args()

    state = load_state()

    # Determine which files to compile
    if args.file:
        target = Path(args.file)
        if not target.is_absolute():
            target = DAILY_DIR / target.name
        if not target.exists():
            # Try resolving relative to user data directory
            target = USER_DIR / args.file
        if not target.exists():
            print(f"Error: {args.file} not found")
            sys.exit(1)
        to_compile = [target]
    else:
        all_logs = list_raw_files()
        if args.all:
            to_compile = all_logs
        else:
            to_compile = []
            for log_path in all_logs:
                rel = log_path.name
                prev = state.get("ingested", {}).get(rel, {})
                if not prev or prev.get("hash") != file_hash(log_path):
                    to_compile.append(log_path)

    if not to_compile:
        print("Nothing to compile - all daily logs are up to date.")
        return

    print(f"{'[DRY RUN] ' if args.dry_run else ''}Files to compile ({len(to_compile)}):")
    for f in to_compile:
        print(f"  - {f.name}")

    if args.dry_run:
        return

    # Compile each file sequentially
    total_cost = 0.0
    for i, log_path in enumerate(to_compile, 1):
        print(f"\n[{i}/{len(to_compile)}] Compiling {log_path.name}...")
        cost = asyncio.run(compile_daily_log(log_path, state))
        total_cost += cost
        print("  Done.")

    articles = list_wiki_articles()
    print(f"\nCompilation complete. Total cost: ${total_cost:.2f}")
    print(f"Knowledge base: {len(articles)} articles")

    # Auto-ingest: load new articles into the wiki database
    from ocd.ingest import ingest_raw

    print("Ingesting into knowledge.db...")
    result = ingest_raw()
    print(
        f"Ingest: {result.inserted} inserted, {result.updated} updated, "
        f"{result.skipped} unchanged, {result.errors} errors"
    )

    # Rebuild the KB search index after compilation
    from ocd.relevance import build_kb_index_json, save_kb_index

    print("Rebuilding KB search index...")
    index = build_kb_index_json()
    save_kb_index(index)
    print(f"Index saved: {len(index['articles'])} articles indexed")

    # Rebuild agent manifest if requested
    if args.manifest:
        from ocd.router import build_manifest, save_manifest

        print("Rebuilding agent manifest...")
        manifest = build_manifest()
        save_manifest(manifest)
        print(f"Manifest saved: {len(manifest['agents'])} agents")

    # Update standards hash if requested
    if args.update_standards_hash:
        from ocd.standards import update_standards_hash

        print("Updating standards hash...")
        new_hash = update_standards_hash()
        if new_hash:
            print(f"Standards hash updated: {new_hash}")
        else:
            print("Warning: standards.md not found", file=sys.stderr)


if __name__ == "__main__":
    main()
