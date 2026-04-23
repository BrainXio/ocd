"""Raw knowledge ingestion pipeline — raw articles into ocd.db.

Scans USER/knowledge/raw/ for markdown articles, parses frontmatter,
computes quality scores, deduplicates by hash, and inserts/updates
records in the ocd.db SQLite database. Rebuilds the TF-IDF index
after ingestion.

Usage:
    ocd ingest             # incremental (only new/changed files)
    ocd ingest --all       # force re-ingest all files
    ocd ingest --dry-run   # report only, no DB changes
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from ocd.config import OCD_DB, RAW_DIR
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

# ── Data structures ──────────────────────────────────────────────────────────

_RAW_SUBDIRS = ("concepts", "connections", "qa", "resources")


@dataclass
class IngestResult:
    """Summary of an ingestion run."""

    scanned: int = 0
    inserted: int = 0
    updated: int = 0
    skipped: int = 0
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


def _scan_raw_files(raw_dir: Path) -> list[Path]:
    """Scan raw directory for markdown article files."""
    if not raw_dir.is_dir():
        return []
    files: list[Path] = []
    for subdir_name in _RAW_SUBDIRS:
        subdir = raw_dir / subdir_name
        if subdir.is_dir():
            files.extend(sorted(subdir.glob("*.md")))
    return files


def ingest_raw(
    *,
    raw_dir: Path | None = None,
    db_path: Path | None = None,
    force_all: bool = False,
    dry_run: bool = False,
) -> IngestResult:
    """Ingest raw knowledge articles into ocd.db.

    Scans the raw directory, parses frontmatter, computes scores,
    deduplicates by hash, and inserts/updates records.
    """
    raw = raw_dir or RAW_DIR
    db_file = db_path or OCD_DB
    result = IngestResult()

    raw_files = _scan_raw_files(raw)
    result.scanned = len(raw_files)

    if not raw_files:
        return result

    if dry_run:
        for f in raw_files:
            content = f.read_text(encoding="utf-8")
            frontmatter, body = _split_frontmatter(content)
            score = _score_article(frontmatter, body)
            print(f"  would ingest: {f.relative_to(raw)} (score={score})")
        return result

    db_file.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(db_file))
    db.executescript(SCHEMA)

    for f in raw_files:
        rel_path = str(f.relative_to(raw))
        try:
            content = f.read_text(encoding="utf-8")
            content_hash = _file_hash(content)
            frontmatter, body = _split_frontmatter(content)

            # Check for existing article with same hash
            row = db.execute("SELECT hash FROM articles WHERE path = ?", (rel_path,)).fetchone()

            if row and row[0] == content_hash and not force_all:
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

            action = "update" if row else "insert"
            db.execute(
                "INSERT OR REPLACE INTO articles VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (rel_path, title, aliases, tags, sources, body, content_hash, score, now, now),
            )
            db.execute(
                "INSERT INTO ingestion_log VALUES (NULL, ?, ?, ?, ?)",
                (_now_iso(), rel_path, action, "ok"),
            )

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

    db.commit()
    db.close()

    # Rebuild TF-IDF index after ingestion
    try:
        from ocd.relevance import build_kb_index_json

        build_kb_index_json()
    except Exception:
        pass  # Index rebuild is best-effort

    # Optionally generate vector embeddings
    try:
        from ocd.vec import ensure_vec_schema, insert_vectors, is_vec_available

        if is_vec_available():
            vec_db = sqlite3.connect(str(db_file))
            if ensure_vec_schema(vec_db):
                rows = vec_db.execute("SELECT path, body FROM articles").fetchall()
                insert_vectors(vec_db, [(r[0], r[1]) for r in rows])
            vec_db.close()
    except ImportError:
        pass  # vec extras not installed, skip

    return result


# ── CLI entry point ──────────────────────────────────────────────────────────


def main() -> None:
    """Entry point for ocd ingest command."""
    parser = argparse.ArgumentParser(
        prog="ocd-ingest",
        description="Ingest raw knowledge articles into ocd.db",
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
