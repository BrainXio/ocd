"""Knowledge base export — articles from knowledge.db to Obsidian vault.

Reads all rows from knowledge.db and writes Obsidian-compatible markdown
files with rich YAML frontmatter, wikilinks, a MOC index, and a backlinks
map. Default export target is USER/knowledge/ (gitignored). Use --commit to
export to docs/knowledge/ for version control.

Usage:
    ocd export                          # export to USER/knowledge/
    ocd export --commit                 # export to docs/knowledge/
    ocd export --output /path/to/vault  # export to custom path
    ocd export --force                  # overwrite existing files
    ocd export --dry-run                # report only, no writes
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

import yaml

from ocd.config import COMMIT_KNOWLEDGE_DIR, KNOWLEDGE_DB, KNOWLEDGE_DIR
from ocd.utils import extract_wikilinks

_EXPORT_SUBDIRS = ("concepts", "connections", "qa", "resources")

_TYPE_MAP = {
    "concepts": "concept",
    "connections": "connection",
    "qa": "qa",
    "resources": "resource",
}


def _derive_article_type(path: str) -> str:
    """Derive article type from DB path prefix."""
    prefix = path.split("/")[0] if "/" in path else ""
    return _TYPE_MAP.get(prefix, "article")


def _slug_from_path(path: str) -> str:
    """Extract Obsidian slug from DB path (strip .md extension)."""
    return path.removesuffix(".md")


def _convert_wikilinks(body: str, article_type: str) -> str:
    """Convert wikilinks to Obsidian format.

    Same-type links strip the type prefix (concept→concept uses bare slug).
    Cross-type links keep the prefix (concept→qa uses qa/slug).
    """
    links = extract_wikilinks(body)
    if not links:
        return body

    type_prefix = article_type + "s"
    replacements: dict[str, str] = {}

    for link in links:
        if link in replacements:
            continue
        parts = link.split("/")
        if len(parts) >= 2 and parts[0] == type_prefix:
            replacements[link] = parts[1]
        else:
            replacements[link] = link

    result = body
    for old, new in replacements.items():
        if old != new:
            result = result.replace(f"[[{old}]]", f"[[{new}]]")
    return result


def _build_frontmatter(
    title: str,
    aliases: str | None,
    tags: str | None,
    sources: str | None,
    score: float,
    created: str,
    updated: str,
    article_type: str,
) -> str:
    """Build YAML frontmatter string from article fields."""
    fm: dict[str, str | list[str] | float] = {
        "title": title,
        "aliases": json.loads(aliases) if aliases else [],
        "tags": json.loads(tags) if tags else [],
        "sources": json.loads(sources) if sources else [],
        "created": created,
        "updated": updated,
        "score": round(score, 2),
        "type": article_type,
    }
    return str(yaml.safe_dump(fm, default_flow_style=False, sort_keys=False).strip())


def _reconstruct_article(
    path: str,
    title: str,
    aliases: str | None,
    tags: str | None,
    sources: str | None,
    body: str,
    score: float,
    created: str,
    updated: str,
) -> str:
    """Reconstruct a full markdown file with frontmatter and converted wikilinks."""
    article_type = _derive_article_type(path)
    fm = _build_frontmatter(title, aliases, tags, sources, score, created, updated, article_type)
    converted_body = _convert_wikilinks(body, article_type)
    return f"---\n{fm}\n---\n\n{converted_body}\n"


def _generate_moc(articles: list[dict[str, object]]) -> str:
    """Generate Map of Content index.md with Dataview queries."""
    type_counts: dict[str, int] = {}
    for a in articles:
        t = str(a.get("type", "article"))
        type_counts[t] = type_counts.get(t, 0) + 1

    total = len(articles)

    lines = [
        "---",
        "title: Knowledge Base Index",
        "tags: [moc]",
        "type: moc",
        "---",
        "",
        f"# Knowledge Base Index ({total} articles)",
        "",
    ]

    lines.append("## Dataview Queries")
    lines.append("")
    lines.append("Use these queries in Obsidian's Dataview plugin:")
    lines.append("")
    lines.append("```dataview")
    lines.append("TABLE title, type, score, updated")
    lines.append('FROM "concepts" OR "connections" OR "qa" OR "resources"')
    lines.append("SORT updated DESC")
    lines.append("```")
    lines.append("")
    lines.append("```dataview")
    lines.append("LIST")
    lines.append("WHERE score >= 0.8")
    lines.append("SORT score DESC")
    lines.append("```")
    lines.append("")

    lines.append("## By Type")
    lines.append("")
    for subdir in _EXPORT_SUBDIRS:
        article_type = _TYPE_MAP[subdir]
        count = type_counts.get(article_type, 0)
        lines.append(f"### {article_type.capitalize()} ({count})")
        lines.append("")
        lines.append("```dataview")
        lines.append(f'LIST FROM "{subdir}"')
        lines.append("```")
        lines.append("")

    recent = sorted(articles, key=lambda a: str(a.get("updated", "")), reverse=True)[:10]
    if recent:
        lines.append("## Recent Changes")
        lines.append("")
        lines.append("| Article | Updated | Score |")
        lines.append("|---------|---------|-------|")
        for a in recent:
            slug = str(a.get("slug", ""))
            updated = str(a.get("updated", ""))
            score = str(a.get("score", ""))
            lines.append(f"| [[{slug}]] | {updated} | {score} |")
        lines.append("")

    high_quality = [a for a in articles if float(str(a.get("score", 0))) >= 0.8]
    if high_quality:
        lines.append("## High Quality (score >= 0.8)")
        lines.append("")
        for a in high_quality:
            slug = str(a.get("slug", ""))
            lines.append(f"- [[{slug}]]")
        lines.append("")

    return "\n".join(lines)


def _generate_backlinks_map(articles: list[dict[str, object]]) -> str:
    """Generate backlinks map from article body wikilinks."""
    backlinks: dict[str, list[str]] = {}

    for a in articles:
        source_slug = str(a.get("slug", ""))
        body = str(a.get("body", ""))
        for link in extract_wikilinks(body):
            target_slug = link.split("/")[-1] if "/" in link else link
            if target_slug not in backlinks:
                backlinks[target_slug] = []
            if source_slug not in backlinks[target_slug]:
                backlinks[target_slug].append(source_slug)

    lines = [
        "---",
        "title: Backlinks Map",
        "tags: [moc, backlinks]",
        "type: backlinks",
        "---",
        "",
        "# Backlinks Map",
        "",
    ]

    for target in sorted(backlinks):
        sources = sorted(backlinks[target])
        lines.append(f"## [[{target}]]")
        lines.append("")
        lines.append(f"Referenced by {len(sources)} article(s):")
        lines.append("")
        for s in sources:
            lines.append(f"- [[{s}]]")
        lines.append("")

    return "\n".join(lines)


def run_export(
    output: str | None = None,
    commit: bool = False,
    force: bool = False,
    dry_run: bool = False,
    db_path: Path | None = None,
) -> int:
    """Export knowledge base articles to Obsidian-compatible markdown vault.

    Returns 0 on success, 1 on error.
    """
    if output:
        output_dir = Path(output)
    elif commit:
        output_dir = COMMIT_KNOWLEDGE_DIR
    else:
        output_dir = KNOWLEDGE_DIR

    db = db_path or KNOWLEDGE_DB

    if not db.exists():
        print(f"error: database not found: {db}", file=sys.stderr)
        return 1

    conn = sqlite3.connect(str(db))
    rows = conn.execute(
        "SELECT path, title, aliases, tags, sources, body, hash, mtime, score, "
        "created, updated FROM articles ORDER BY path"
    ).fetchall()
    conn.close()

    if not rows:
        print("No articles to export.")
        return 0

    type_counts: dict[str, int] = {}
    articles_data: list[dict[str, object]] = []

    for row in rows:
        path, title, aliases, tags, sources, body, _hash, _mtime, score, created, updated = row
        article_type = _derive_article_type(path)
        slug = _slug_from_path(path)
        type_counts[article_type] = type_counts.get(article_type, 0) + 1
        articles_data.append(
            {
                "path": path,
                "slug": slug,
                "title": title,
                "type": article_type,
                "score": score,
                "created": created,
                "updated": updated,
                "body": body,
                "aliases": aliases,
                "tags": tags,
                "sources": sources,
            }
        )

    if dry_run:
        print(f"Would export {len(rows)} article(s) to {output_dir}")
        for atype, count in sorted(type_counts.items()):
            print(f"  {atype}: {count}")
        return 0

    for subdir in _EXPORT_SUBDIRS:
        (output_dir / subdir).mkdir(parents=True, exist_ok=True)

    exported = 0
    skipped = 0
    errors = 0

    for a in articles_data:
        path = str(a["path"])
        target = output_dir / path
        if target.exists() and not force:
            skipped += 1
            continue
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            content = _reconstruct_article(
                path=path,
                title=str(a["title"]),
                aliases=str(a["aliases"]) if a["aliases"] else None,
                tags=str(a["tags"]) if a["tags"] else None,
                sources=str(a["sources"]) if a["sources"] else None,
                body=str(a["body"]),
                score=float(str(a["score"])),
                created=str(a["created"]),
                updated=str(a["updated"]),
            )
            target.write_text(content, encoding="utf-8")
            exported += 1
        except OSError as e:
            print(f"error writing {target}: {e}", file=sys.stderr)
            errors += 1

    moc_content = _generate_moc(articles_data)
    (output_dir / "index.md").write_text(moc_content, encoding="utf-8")

    backlinks_content = _generate_backlinks_map(articles_data)
    (output_dir / "_backlinks.md").write_text(backlinks_content, encoding="utf-8")

    print(f"Exported {exported} article(s) to {output_dir}")
    if skipped:
        print(f"  skipped: {skipped} (use --force to overwrite)")
    if errors:
        print(f"  errors: {errors}", file=sys.stderr)
    print("  index.md + _backlinks.md generated")
    return 0 if errors == 0 else 1


def main() -> None:
    """Entry point for ocd export command."""
    parser = argparse.ArgumentParser(description="Export knowledge base to Obsidian vault")
    parser.add_argument(
        "--commit", action="store_true", help="Export to docs/knowledge/ (commit-friendly)"
    )
    parser.add_argument("--output", "-o", default=None, help="Custom output directory path")
    parser.add_argument("--force", "-f", action="store_true", help="Overwrite existing files")
    parser.add_argument(
        "--dry-run", action="store_true", help="Report what would be exported, no writes"
    )
    parser.add_argument("--db", default=None, help="Database path (default: knowledge.db)")
    args = parser.parse_args()

    db_path = Path(args.db) if args.db else None
    sys.exit(
        run_export(
            output=args.output,
            commit=args.commit,
            force=args.force,
            dry_run=args.dry_run,
            db_path=db_path,
        )
    )


if __name__ == "__main__":
    main()
