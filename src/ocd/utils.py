"""Shared utilities for the personal knowledge base."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from ocd.config import (
    CONCEPTS_DIR,
    CONNECTIONS_DIR,
    DAILY_DIR,
    DEFAULT_INDEX_CONTENT,
    INDEX_FILE,
    KNOWLEDGE_DIR,
    QA_DIR,
    STATE_FILE,
)

# ── State management ──────────────────────────────────────────────────


def load_state() -> dict[str, Any]:
    """Load persistent state from state.json."""
    if STATE_FILE.exists():
        result: dict[str, Any] = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return result
    return {"ingested": {}, "query_count": 0, "last_lint": None, "total_cost": 0.0}


def save_state(state: dict[str, Any]) -> None:
    """Save state to state.json."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


# ── File hashing ──────────────────────────────────────────────────────


def file_hash(path: Path) -> str:
    """SHA-256 hash of a file (first 16 hex chars)."""
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


# ── Wikilink helpers ──────────────────────────────────────────────────


def extract_wikilinks(content: str) -> list[str]:
    """Extract all [[wikilinks]] from markdown content."""
    return re.findall(r"\[\[([^\]]+)\]\]", content)


def wiki_article_exists(link: str) -> bool:
    """Check if a wikilinked article exists on disk."""
    if ".." in link.split("/") or "\\" in link or link.startswith("/"):
        return False
    path = KNOWLEDGE_DIR / f"{link}.md"
    return path.resolve().is_relative_to(KNOWLEDGE_DIR.resolve()) and path.exists()


# ── Wiki content helpers ──────────────────────────────────────────────


def read_wiki_index() -> str:
    """Read the knowledge base index file."""
    if INDEX_FILE.exists():
        return INDEX_FILE.read_text(encoding="utf-8")
    return DEFAULT_INDEX_CONTENT


def read_all_wiki_content() -> str:
    """Read index + all wiki articles into a single string for context."""
    parts = [f"## INDEX\n\n{read_wiki_index()}"]

    for subdir in [CONCEPTS_DIR, CONNECTIONS_DIR, QA_DIR]:
        if not subdir.exists():
            continue
        for md_file in sorted(subdir.glob("*.md")):
            rel = md_file.relative_to(KNOWLEDGE_DIR)
            content = md_file.read_text(encoding="utf-8")
            parts.append(f"## {rel}\n\n{content}")

    return "\n\n---\n\n".join(parts)


def list_wiki_articles() -> list[Path]:
    """List all wiki article files."""
    articles = []
    for subdir in [CONCEPTS_DIR, CONNECTIONS_DIR, QA_DIR]:
        if subdir.exists():
            articles.extend(sorted(subdir.glob("*.md")))
    return articles


def list_raw_files() -> list[Path]:
    """List all daily log files."""
    if not DAILY_DIR.exists():
        return []
    return sorted(DAILY_DIR.glob("*.md"))


# ── Index helpers ─────────────────────────────────────────────────────


def count_inbound_links(target: str) -> int:
    """Count how many wiki articles link to a given target."""
    count = 0
    for article in list_wiki_articles():
        content = article.read_text(encoding="utf-8")
        if f"[[{target}]]" in content:
            count += 1
    return count


def get_article_word_count(path: Path) -> int:
    """Count words in an article, excluding YAML frontmatter."""
    content = path.read_text(encoding="utf-8")
    # Strip frontmatter
    if content.startswith("---"):
        end = content.find("---", 3)
        if end != -1:
            content = content[end + 3 :]
    return len(content.split())


