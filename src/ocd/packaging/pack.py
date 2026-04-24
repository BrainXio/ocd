"""Compile OCD content into SQLite database for release packaging.

Reads OCD-specific content (agents, rules, skills, standards, settings) from
a source directory and portable content (skills, agents) from a portable
source directory, compiling both into a single content.db that ships inside
the Python wheel. The runtime materializer (ocd materialize) reconstructs
the files from this database into any target directory.

Usage:
    ocd compile-db                                        # defaults
    ocd compile-db -o /tmp/content.db                     # specific output
    ocd compile-db --source src/ocd/content               # OCD content only
    ocd compile-db --portable-source docs/reference        # with portable content
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path

try:
    from ocd.config import CONTENT_DIR, DOCS_AGENTS_DIR, DOCS_SKILLS_DIR, PROJECT_ROOT
except ImportError:
    PROJECT_ROOT = Path.cwd()
    CONTENT_DIR = Path.cwd() / "src" / "ocd" / "content"
    DOCS_SKILLS_DIR = Path.cwd() / "docs" / "reference" / "skills"
    DOCS_AGENTS_DIR = Path.cwd() / "docs" / "reference" / "agents"

SCHEMA = """
CREATE TABLE IF NOT EXISTS agents (
    name TEXT PRIMARY KEY,
    frontmatter TEXT NOT NULL,
    body TEXT NOT NULL,
    created TEXT NOT NULL,
    updated TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS rules (
    name TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    paths TEXT,
    body TEXT NOT NULL,
    created TEXT NOT NULL,
    updated TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS skills (
    name TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    argument_hint TEXT,
    body TEXT NOT NULL,
    created TEXT NOT NULL,
    updated TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS standards (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    version TEXT NOT NULL,
    hash TEXT NOT NULL,
    body TEXT NOT NULL,
    created TEXT NOT NULL,
    updated TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    name TEXT PRIMARY KEY,
    body TEXT NOT NULL,
    created TEXT NOT NULL,
    updated TEXT NOT NULL
);
"""


def _iso_mtime(path: Path) -> str:
    """Return ISO 8601 timestamp from file modification time."""
    return datetime.fromtimestamp(path.stat().st_mtime, tz=UTC).isoformat(timespec="seconds")


def _split_frontmatter(content: str) -> tuple[str, str]:
    """Split markdown content into (frontmatter_text, body_text).

    Returns ("", content) if no frontmatter delimiters are found.
    """
    if not content.startswith("---"):
        return "", content
    end = content.find("---", 3)
    if end == -1:
        return "", content
    fm = content[3:end].strip()
    body = content[end + 3 :].strip()
    return fm, body


def _parse_simple_frontmatter(fm: str) -> dict[str, str]:
    """Parse simple key: value YAML frontmatter (no nested structures)."""
    result: dict[str, str] = {}
    for line in fm.splitlines():
        line = line.strip()
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        result[key.strip()] = val.strip().strip('"').strip("'")
    return result


def _create_schema(db: sqlite3.Connection) -> None:
    """Create database tables if they don't exist."""
    db.executescript(SCHEMA)


def _load_agents(db: sqlite3.Connection, agents_dir: Path) -> int:
    """Load all agent .md files into the agents table."""
    count = 0
    for path in sorted(agents_dir.glob("*.md")):
        name = path.stem
        content = path.read_text()
        frontmatter, body = _split_frontmatter(content)
        if not frontmatter:
            continue
        db.execute(
            "INSERT OR REPLACE INTO agents VALUES (?, ?, ?, ?, ?)",
            (name, frontmatter, body, _iso_mtime(path), _iso_mtime(path)),
        )
        count += 1
    return count


def _load_rules(db: sqlite3.Connection, rules_dir: Path) -> int:
    """Load all rule .md files into the rules table."""
    count = 0
    for path in sorted(rules_dir.glob("*.md")):
        name = path.stem
        content = path.read_text()
        frontmatter, body = _split_frontmatter(content)
        if not frontmatter:
            continue
        parsed = _parse_simple_frontmatter(frontmatter)
        description = parsed.get("description", "")
        paths = parsed.get("paths")
        db.execute(
            "INSERT OR REPLACE INTO rules VALUES (?, ?, ?, ?, ?, ?)",
            (name, description, paths, body, _iso_mtime(path), _iso_mtime(path)),
        )
        count += 1
    return count


def _load_skills(db: sqlite3.Connection, skills_dir: Path) -> int:
    """Load all skill SKILL.md files into the skills table."""
    count = 0
    for skill_dir in sorted(skills_dir.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            continue
        name = skill_dir.name
        content = skill_file.read_text()
        frontmatter, body = _split_frontmatter(content)
        if not frontmatter:
            continue
        parsed = _parse_simple_frontmatter(frontmatter)
        description = parsed.get("description", "")
        argument_hint = parsed.get("argument-hint")
        db.execute(
            "INSERT OR REPLACE INTO skills VALUES (?, ?, ?, ?, ?, ?)",
            (
                name,
                description,
                argument_hint,
                body,
                _iso_mtime(skill_file),
                _iso_mtime(skill_file),
            ),
        )
        count += 1
    return count


def _load_portable_skills(db: sqlite3.Connection, skills_dir: Path) -> int:
    """Load portable skill .md files from a flat directory structure.

    Unlike _load_skills which expects skills/<name>/SKILL.md subdirectories,
    portable skills are stored as flat files: skills/<name>.md with the
    skill name derived from the file stem.
    """
    count = 0
    for path in sorted(skills_dir.glob("*.md")):
        name = path.stem
        content = path.read_text()
        frontmatter, body = _split_frontmatter(content)
        if not frontmatter:
            continue
        parsed = _parse_simple_frontmatter(frontmatter)
        description = parsed.get("description", "")
        argument_hint = parsed.get("argument-hint")
        db.execute(
            "INSERT OR REPLACE INTO skills VALUES (?, ?, ?, ?, ?, ?)",
            (
                name,
                description,
                argument_hint,
                body,
                _iso_mtime(path),
                _iso_mtime(path),
            ),
        )
        count += 1
    return count


def _load_standards(db: sqlite3.Connection, standards_file: Path) -> int:
    """Load the standards document into the singleton standards table."""
    if not standards_file.exists():
        return 0
    content = standards_file.read_text()
    frontmatter, body = _split_frontmatter(content)
    if not frontmatter:
        return 0
    parsed = _parse_simple_frontmatter(frontmatter)
    version = parsed.get("version", "0.0")
    hash_value = parsed.get("hash", "")
    db.execute(
        "INSERT OR REPLACE INTO standards VALUES (?, ?, ?, ?, ?, ?)",
        (1, version, hash_value, body, _iso_mtime(standards_file), _iso_mtime(standards_file)),
    )
    return 1


def _load_settings(db: sqlite3.Connection, settings_dir: Path) -> int:
    """Load .json settings files into the settings table."""
    count = 0
    for path in sorted(settings_dir.glob("*.json")):
        name = path.stem
        body = path.read_text()
        db.execute(
            "INSERT OR REPLACE INTO settings VALUES (?, ?, ?, ?)",
            (name, body, _iso_mtime(path), _iso_mtime(path)),
        )
        count += 1
    return count


def compile_db(
    source: Path,
    output: Path,
    portable_source: Path | None = None,
) -> dict[str, int]:
    """Compile content into a SQLite database.

    Args:
        source: OCD-specific content directory (agents, rules, skills, standards, settings).
        output: Path to the output database file.
        portable_source: Optional portable content directory (skills/ and agents/ subdirs).
            When provided, portable content is loaded first, then OCD content is loaded
            with INSERT OR REPLACE so OCD items override any same-name portable items.

    Returns:
        Dict with counts for each content type.
    """
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        output.unlink()

    db = sqlite3.connect(str(output))
    _create_schema(db)

    n_agents = 0
    n_skills = 0

    if portable_source and portable_source.exists():
        n_agents += _load_agents(db, portable_source / "agents")
        n_skills += _load_portable_skills(db, portable_source / "skills")

    n_agents += _load_agents(db, source / "agents")
    n_rules = _load_rules(db, source / "rules")
    n_skills += _load_skills(db, source / "skills")
    n_standards = _load_standards(db, source / "skills" / "ocd" / "standards.md")
    n_settings = _load_settings(db, source / "settings")
    db.commit()
    db.close()

    return {
        "agents": n_agents,
        "rules": n_rules,
        "skills": n_skills,
        "standards": n_standards,
        "settings": n_settings,
    }


# ── Public API ────────────────────────────────────────────────────────────


def run_compile_db(
    output: str | None = None,
    source: str | None = None,
    portable_source: str | None = None,
) -> int:
    """Compile content into content.db.

    Args:
        output: Output database path, or None for default (src/ocd/data/content.db).
        source: OCD content directory, or None for default (src/ocd/content/).
        portable_source: Portable content directory (docs/reference/), or None for default.

    Returns:
        0 on success.
    """
    src = Path(source) if source else CONTENT_DIR
    out = Path(output) if output else PROJECT_ROOT / "src" / "ocd" / "data" / "content.db"
    psrc = Path(portable_source) if portable_source else None

    counts = compile_db(src, out, portable_source=psrc)
    size = out.stat().st_size
    total = sum(counts.values())
    print(f"Compiled {total} entries ({size:,} bytes) to {out}")
    print(
        f"  agents: {counts['agents']}, rules: {counts['rules']}, "
        f"skills: {counts['skills']}, standards: {counts['standards']}, "
        f"settings: {counts['settings']}"
    )
    return 0


# ── CLI ──────────────────────────────────────────────────────────────────


def main() -> None:
    """Entry point for ocd compile-db command."""
    parser = argparse.ArgumentParser(description="Compile content into content.db")
    parser.add_argument(
        "--output",
        "-o",
        default=str(PROJECT_ROOT / "src" / "ocd" / "data" / "content.db"),
        help="Output database path (default: src/ocd/data/content.db)",
    )
    parser.add_argument(
        "--source",
        default=None,
        help="OCD content directory (default: src/ocd/content/)",
    )
    parser.add_argument(
        "--portable-source",
        default=None,
        help="Portable content directory (default: docs/reference/)",
    )
    args = parser.parse_args()

    sys.exit(
        run_compile_db(output=args.output, source=args.source, portable_source=args.portable_source)
    )


if __name__ == "__main__":
    main()
