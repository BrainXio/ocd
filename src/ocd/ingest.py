"""Knowledge ingestion pipeline — wiki articles into knowledge.db.

Scans USER/knowledge/ subdirectories for markdown articles, parses
frontmatter, computes quality scores, deduplicates by hash, and
inserts/updates records in the knowledge.db SQLite database.
Rebuilds the TF-IDF index after ingestion.

Uses mtime-first, hash-confirmed change detection: compares file mtime
with stored mtime for a fast skip, then reads and hashes only when mtime
differs. Detects orphaned DB rows (files deleted from disk) and removes
them. Only re-embeds changed articles for vector search.

Usage:
    ocd ingest             # incremental (only new/changed files)
    ocd ingest --all       # force re-ingest all files
    ocd ingest --dry-run   # report only, no DB changes
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import sqlite3
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ocd.config import WIKI_DB
from ocd.utils import extract_wikilinks

# ── Schema ───────────────────────────────────────────────────────────────────

SCHEMA = """
CREATE TABLE IF NOT EXISTS articles (
    path TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    aliases TEXT,
    tags TEXT,
    sources TEXT,
    body TEXT NOT NULL,
    hash TEXT NOT NULL,
    mtime REAL NOT NULL DEFAULT 0,
    score REAL NOT NULL DEFAULT 0,
    created TEXT NOT NULL,
    updated TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ingestion_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    path TEXT NOT NULL,
    action TEXT NOT NULL,
    status TEXT NOT NULL
);
"""

_MIGRATION_MTIME = "ALTER TABLE articles ADD COLUMN mtime REAL NOT NULL DEFAULT 0"

# ── Data structures ──────────────────────────────────────────────────────────

_WIKI_SUBDIRS = ("concepts", "connections", "qa", "resources")


@dataclass
class IngestResult:
    """Summary of an ingestion run."""

    scanned: int = 0
    inserted: int = 0
    updated: int = 0
    skipped: int = 0
    deleted: int = 0
    errors: int = 0

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)


# ── Frontmatter parsing ─────────────────────────────────────────────────────


def _split_frontmatter(content: str) -> tuple[dict[str, str], str]:
    """Split markdown content into (frontmatter_dict, body_text).

    Returns ({}, content) if no frontmatter delimiters found.
    """
    if not content.startswith("---"):
        return {}, content
    end = content.find("---", 3)
    if end == -1:
        return {}, content
    fm_text = content[3:end].strip()
    body = content[end + 3 :].strip()

    result: dict[str, str] = {}
    for line in fm_text.splitlines():
        line = line.strip()
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        result[key.strip()] = val.strip().strip('"').strip("'")
    return result, body


def _parse_list_field(value: str | None) -> list[str]:
    """Parse a YAML list field like '[tag1, tag2]' into a Python list."""
    if not value:
        return []
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        value = value[1:-1]
    return [v.strip().strip('"').strip("'") for v in value.split(",") if v.strip()]


# ── Scoring ──────────────────────────────────────────────────────────────────


def _score_article(
    frontmatter: dict[str, str],
    body: str,
) -> float:
    """Compute a quality score (0.0-1.0) for a raw article.

    Criteria (each worth 0.2):
    - Has a title in frontmatter
    - Has tags
    - Has sources
    - Word count >= 100
    - Contains wikilinks
    """
    score = 0.0
    if frontmatter.get("title"):
        score += 0.2
    tags = _parse_list_field(frontmatter.get("tags"))
    if tags:
        score += 0.2
    sources = _parse_list_field(frontmatter.get("sources"))
    if sources:
        score += 0.2
    if len(body.split()) >= 100:
        score += 0.2
    if extract_wikilinks(body):
        score += 0.2
    return round(score, 1)


# ── Hashing ───────────────────────────────────────────────────────────────────


def _file_hash(content: str) -> str:
    """SHA-256 hash of content (first 16 hex chars)."""
    return hashlib.sha256(content.encode()).hexdigest()[:16]


# ── Ingestion ────────────────────────────────────────────────────────────────


def _now_iso() -> str:
    """Current UTC time in ISO 8601 format."""
    return datetime.now(UTC).isoformat(timespec="seconds")


def _scan_wiki_files(knowledge_dir: Path) -> list[Path]:
    """Scan knowledge directory for markdown article files."""
    if not knowledge_dir.is_dir():
        return []
    files: list[Path] = []
    for subdir_name in _WIKI_SUBDIRS:
        subdir = knowledge_dir / subdir_name
        if subdir.is_dir():
            files.extend(sorted(subdir.glob("*.md")))
    return files


def _apply_migrations(db: sqlite3.Connection) -> None:
    """Apply backward-compatible schema migrations (idempotent)."""
    with contextlib.suppress(sqlite3.OperationalError):
        db.execute(_MIGRATION_MTIME)


def ingest_raw(
    *,
    knowledge_dir: Path | None = None,
    db_path: Path | None = None,
    force_all: bool = False,
    dry_run: bool = False,
) -> IngestResult:
    """Ingest wiki articles into knowledge.db.

    Scans the knowledge directory, parses frontmatter, computes scores,
    deduplicates by hash, and inserts/updates records. Uses mtime-first
    change detection for fast incremental runs. Removes orphaned DB rows
    when files are deleted from disk.
    """
    from ocd.config import KNOWLEDGE_DIR

    kdir = knowledge_dir or KNOWLEDGE_DIR
    db_file = db_path or WIKI_DB
    result = IngestResult()

    wiki_files = _scan_wiki_files(kdir)
    result.scanned = len(wiki_files)

    if dry_run:
        for f in wiki_files:
            content = f.read_text(encoding="utf-8")
            frontmatter, body = _split_frontmatter(content)
            score = _score_article(frontmatter, body)
            print(f"  would ingest: {f.relative_to(kdir)} (score={score})")
        return result

    db_file.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(db_file))
    db.executescript(SCHEMA)
    _apply_migrations(db)

    disk_paths: set[str] = set()
    changed_paths: list[str] = []  # Paths that were inserted or updated
    changed_articles: list[tuple[str, str]] = []  # (path, body) for incremental vectors

    for f in wiki_files:
        rel_path = str(f.relative_to(kdir))
        disk_paths.add(rel_path)
        try:
            file_mtime = os.path.getmtime(f)

            # Fast path: mtime matches — skip without reading file
            if not force_all:
                row = db.execute(
                    "SELECT hash, mtime FROM articles WHERE path = ?", (rel_path,)
                ).fetchone()
                if row and row[1] == file_mtime:
                    result.skipped += 1
                    db.execute(
                        "INSERT INTO ingestion_log VALUES (NULL, ?, ?, ?, ?)",
                        (_now_iso(), rel_path, "skip", "ok"),
                    )
                    continue

            # Slow path: read file and hash
            content = f.read_text(encoding="utf-8")
            content_hash = _file_hash(content)
            frontmatter, body = _split_frontmatter(content)

            # Check if content actually changed (mtime can change without content change)
            if not force_all:
                row = db.execute(
                    "SELECT hash, mtime FROM articles WHERE path = ?", (rel_path,)
                ).fetchone()
                if row and row[0] == content_hash:
                    # Mtime changed but content didn't — just update mtime
                    db.execute(
                        "UPDATE articles SET mtime = ? WHERE path = ?",
                        (file_mtime, rel_path),
                    )
                    result.skipped += 1
                    db.execute(
                        "INSERT INTO ingestion_log VALUES (NULL, ?, ?, ?, ?)",
                        (_now_iso(), rel_path, "skip", "ok"),
                    )
                    continue

            title = frontmatter.get("title", f.stem)
            aliases = json.dumps(_parse_list_field(frontmatter.get("aliases")))
            tags = json.dumps(_parse_list_field(frontmatter.get("tags")))
            sources = json.dumps(_parse_list_field(frontmatter.get("sources")))
            score = _score_article(frontmatter, body)
            now = _now_iso()

            existing = db.execute("SELECT 1 FROM articles WHERE path = ?", (rel_path,)).fetchone()
            action = "update" if existing else "insert"

            db.execute(
                "INSERT OR REPLACE INTO articles VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    rel_path,
                    title,
                    aliases,
                    tags,
                    sources,
                    body,
                    content_hash,
                    file_mtime,
                    score,
                    now,
                    now,
                ),
            )
            db.execute(
                "INSERT INTO ingestion_log VALUES (NULL, ?, ?, ?, ?)",
                (_now_iso(), rel_path, action, "ok"),
            )

            changed_paths.append(rel_path)
            changed_articles.append((rel_path, body))

            if action == "insert":
                result.inserted += 1
            else:
                result.updated += 1

        except Exception as e:
            result.errors += 1
            db.execute(
                "INSERT INTO ingestion_log VALUES (NULL, ?, ?, ?, ?)",
                (_now_iso(), rel_path, "error", str(e)),
            )

    # Deletion detection: remove DB rows for files no longer on disk
    db_paths = {row[0] for row in db.execute("SELECT path FROM articles").fetchall()}
    orphaned = db_paths - disk_paths
    for orphan_path in orphaned:
        db.execute("DELETE FROM articles WHERE path = ?", (orphan_path,))
        db.execute(
            "INSERT INTO ingestion_log VALUES (NULL, ?, ?, ?, ?)",
            (_now_iso(), orphan_path, "delete", "ok"),
        )
        result.deleted += 1
        changed_paths.append(orphan_path)

    db.commit()
    db.close()

    # Rebuild TF-IDF index after ingestion
    try:
        from ocd.relevance import build_kb_index_json

        build_kb_index_json()
    except Exception:
        pass  # Index rebuild is best-effort

    # Incremental vector update: only re-embed changed articles
    try:
        from ocd.vec import ensure_vec_schema, insert_vectors, is_vec_available

        if is_vec_available() and changed_articles:
            vec_db = sqlite3.connect(str(db_file))
            if ensure_vec_schema(vec_db):
                insert_vectors(vec_db, changed_articles)
            vec_db.close()
    except ImportError:
        pass  # vec extras not installed, skip

    return result


# ── Knowledge status ─────────────────────────────────────────────────────────


def kb_status(*, knowledge_dir: Path | None = None, db_path: Path | None = None) -> dict[str, Any]:
    """Compare filesystem with the DB and report sync status.

    Returns a dict with:
        db_count: number of articles in DB
        disk_count: number of article files on disk
        new: list of paths on disk but not in DB
        stale: list of paths in DB with different mtime
        orphaned: list of paths in DB but not on disk
        last_ingest: ISO timestamp of last ingestion, or None
        synced: True if db_count == disk_count and no new/stale/orphaned
    """
    from ocd.config import KNOWLEDGE_DIR

    kdir = knowledge_dir or KNOWLEDGE_DIR
    db_file = db_path or WIKI_DB

    wiki_files = _scan_wiki_files(kdir)
    disk_paths: dict[str, float] = {}
    for f in wiki_files:
        rel = str(f.relative_to(kdir))
        with contextlib.suppress(OSError):
            disk_paths[rel] = os.path.getmtime(f)

    status: dict[str, Any] = {
        "db_count": 0,
        "disk_count": len(disk_paths),
        "new": [],
        "stale": [],
        "orphaned": [],
        "last_ingest": None,
        "synced": False,
    }

    if not db_file.exists():
        status["new"] = sorted(disk_paths)
        status["synced"] = len(disk_paths) == 0
        return status

    db = sqlite3.connect(str(db_file))
    _apply_migrations(db)

    rows = db.execute("SELECT path, mtime FROM articles").fetchall()
    db_paths: dict[str, float] = {r[0]: r[1] for r in rows}
    status["db_count"] = len(db_paths)

    # Last ingest timestamp
    last = db.execute("SELECT timestamp FROM ingestion_log ORDER BY id DESC LIMIT 1").fetchone()
    if last:
        status["last_ingest"] = last[0]

    db.close()

    new_paths = set(disk_paths) - set(db_paths)
    status["new"] = sorted(new_paths)

    orphaned_paths = set(db_paths) - set(disk_paths)
    status["orphaned"] = sorted(orphaned_paths)

    # Stale: on both disk and DB but mtime differs
    for path in sorted(set(disk_paths) & set(db_paths)):
        if disk_paths[path] != db_paths[path]:
            status["stale"].append(path)

    status["synced"] = not status["new"] and not status["stale"] and not status["orphaned"]
    return status


# ── CLI entry point ──────────────────────────────────────────────────────────


def main() -> None:
    """Entry point for ocd ingest command."""
    parser = argparse.ArgumentParser(
        prog="ocd-ingest",
        description="Ingest wiki articles into knowledge.db",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Force re-ingest all files (ignore hash matching)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be ingested without making changes",
    )
    args = parser.parse_args()

    result = ingest_raw(force_all=args.all, dry_run=args.dry_run)
    print(result.to_json())
    sys.exit(1 if result.errors else 0)


if __name__ == "__main__":
    main()
