"""Compile .claude/ content into SQLite database for release packaging.

Reads agents, rules, skills, and standards from the source .claude/ directory
and compiles them into a single content.db that ships inside the Python
wheel. The runtime materializer (ocd-materialize) reconstructs the files from
this database into any target directory.

Usage:
    ocd-compile-db                     # compile to default location
    ocd-compile-db -o /tmp/ocd.db      # compile to specific path
    ocd-compile-db --source /path/.claude  # use non-default source
"""

from __future__ import annotations

import argparse
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from ocd.config import PROJECT_ROOT

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


def compile_db(source: Path, output: Path) -> dict[str, int]:
    """Compile .claude/ content into a SQLite database.

    Returns a dict with counts: {agents: N, rules: N, skills: N, standards: N}.
    """
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        output.unlink()

    db = sqlite3.connect(str(output))
    _create_schema(db)
    n_agents = _load_agents(db, source / "agents")
    n_rules = _load_rules(db, source / "rules")
    n_skills = _load_skills(db, source / "skills")
    n_standards = _load_standards(db, source / "skills" / "ocd" / "standards.md")
    db.commit()
    db.close()

    return {
        "agents": n_agents,
        "rules": n_rules,
        "skills": n_skills,
        "standards": n_standards,
    }


def main() -> None:
    """Entry point for ocd-compile-db."""
    parser = argparse.ArgumentParser(description="Compile .claude/ content into content.db")
    parser.add_argument(
        "--output",
        "-o",
        default=str(PROJECT_ROOT / "src" / "ocd" / "data" / "content.db"),
        help="Output database path (default: src/ocd/data/content.db)",
    )
    parser.add_argument(
        "--source",
        default=None,
        help="Source .claude/ directory (default: auto-detect from project root)",
    )
    args = parser.parse_args()

    source = Path(args.source) if args.source else PROJECT_ROOT / ".claude"
    output = Path(args.output)

    counts = compile_db(source, output)
    size = output.stat().st_size
    total = sum(counts.values())
    print(f"Compiled {total} entries ({size:,} bytes) to {output}")
    print(
        f"  agents: {counts['agents']}, rules: {counts['rules']}, "
        f"skills: {counts['skills']}, standards: {counts['standards']}"
    )


if __name__ == "__main__":
    main()
