"""Materialize .claude/ content from SQLite database into target directory.

Reads agents, rules, skills, and standards from the bundled content.db
and reconstructs the original markdown files in the target directory. This
enables deploying the OCD configuration to any agent directory, not just
.claude/ — for example, .cursor/, .copilot/, etc.

Usage:
    ocd-materialize                        # materialize to .claude/
    ocd-materialize -t /path/.claude      # materialize to custom target
    ocd-materialize --vendor aider          # materialize for Aider
    ocd-materialize --vendor all            # materialize for all vendors
    ocd-materialize --force                # overwrite existing files
    ocd-materialize --db /path/to/db       # use custom database
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

try:
    from ocd.config import PROJECT_ROOT
except ImportError:
    PROJECT_ROOT = Path.cwd()


def _find_bundled_db() -> Path:
    """Locate the bundled database inside the installed package."""
    # When running from source, use the project root path
    source_db = PROJECT_ROOT / "src" / "ocd" / "data" / "content.db"
    if source_db.exists():
        return source_db
    # When installed as a package, use __file__-relative path
    installed_db = Path(__file__).parent / "data" / "content.db"
    if installed_db.exists():
        return installed_db
    raise FileNotFoundError(
        "Cannot find content.db. Run 'ocd-compile-db' to generate it, or specify --db path."
    )


def _reconstruct_agent(name: str, frontmatter: str, body: str) -> str:
    """Reconstruct an agent .md file from database fields."""
    return f"---\n{frontmatter}\n---\n\n{body}\n"


def _reconstruct_rule(name: str, description: str, paths: str | None, body: str) -> str:
    """Reconstruct a rule .md file from database fields."""
    lines = ["---"]
    lines.append(f"description: {_quote_if_needed(description)}")
    if paths:
        lines.append(f"paths: {paths}")
    lines.append("---")
    lines.append("")
    lines.append(body)
    return "\n".join(lines) + "\n"


def _reconstruct_skill(name: str, description: str, argument_hint: str | None, body: str) -> str:
    """Reconstruct a skill SKILL.md file from database fields."""
    lines = ["---"]
    lines.append(f"name: {name}")
    lines.append(f"description: {_quote_if_needed(description)}")
    if argument_hint:
        lines.append(f"argument-hint: {_quote_if_needed(argument_hint)}")
    lines.append("---")
    lines.append("")
    lines.append(body)
    return "\n".join(lines) + "\n"


def _reconstruct_standards(version: str, hash_value: str, body: str) -> str:
    """Reconstruct the standards.md file from database fields."""
    return f'---\nversion: "{version}"\nhash: "{hash_value}"\n---\n\n{body}\n'


def _quote_if_needed(value: str) -> str:
    """Quote a YAML value if it contains special characters."""
    if any(
        c in value
        for c in (
            ":",
            "#",
            "{",
            "}",
            "[",
            "]",
            ",",
            "&",
            "*",
            "?",
            "|",
            "-",
            "<",
            ">",
            "=",
            "!",
            "%",
            "@",
            "`",
        )
    ):
        return f'"{value}"'
    return value


def _materialize_agents(db: sqlite3.Connection, target_dir: Path, force: bool) -> int:
    """Write agent files from database to target directory."""
    target_dir.mkdir(parents=True, exist_ok=True)
    rows = db.execute("SELECT name, frontmatter, body FROM agents").fetchall()
    count = 0
    for name, frontmatter, body in rows:
        path = target_dir / f"{name}.md"
        if path.exists() and not force:
            continue
        path.write_text(_reconstruct_agent(name, frontmatter, body))
        count += 1
    return count


def _materialize_rules(db: sqlite3.Connection, target_dir: Path, force: bool) -> int:
    """Write rule files from database to target directory."""
    target_dir.mkdir(parents=True, exist_ok=True)
    rows = db.execute("SELECT name, description, paths, body FROM rules").fetchall()
    count = 0
    for name, description, paths, body in rows:
        path = target_dir / f"{name}.md"
        if path.exists() and not force:
            continue
        path.write_text(_reconstruct_rule(name, description, paths, body))
        count += 1
    return count


def _materialize_skills(db: sqlite3.Connection, target_dir: Path, force: bool) -> int:
    """Write skill SKILL.md files from database to target directory."""
    target_dir.mkdir(parents=True, exist_ok=True)
    rows = db.execute("SELECT name, description, argument_hint, body FROM skills").fetchall()
    count = 0
    for name, description, argument_hint, body in rows:
        skill_dir = target_dir / name
        skill_dir.mkdir(parents=True, exist_ok=True)
        path = skill_dir / "SKILL.md"
        if path.exists() and not force:
            continue
        path.write_text(_reconstruct_skill(name, description, argument_hint, body))
        count += 1
    return count


def _materialize_standards(db: sqlite3.Connection, target_dir: Path, force: bool) -> int:
    """Write the standards.md file from database to target directory."""
    row = db.execute("SELECT version, hash, body FROM standards WHERE id = 1").fetchone()
    if not row:
        return 0
    version, hash_value, body = row
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / "standards.md"
    if path.exists() and not force:
        return 0
    path.write_text(_reconstruct_standards(version, hash_value, body))
    return 1


def materialize(db_path: Path, target: Path, force: bool = False) -> dict[str, int]:
    """Materialize all content from database to target directory.

    Returns a dict with counts: {agents: N, rules: N, skills: N, standards: N}.
    """
    db = sqlite3.connect(str(db_path))
    n_agents = _materialize_agents(db, target / "agents", force)
    n_rules = _materialize_rules(db, target / "rules", force)
    n_skills = _materialize_skills(db, target / "skills", force)
    n_standards = _materialize_standards(db, target / "skills" / "ocd", force)
    db.close()
    return {
        "agents": n_agents,
        "rules": n_rules,
        "skills": n_skills,
        "standards": n_standards,
    }


def materialize_vendor(db_path: Path, vendor: str, force: bool = False) -> dict[str, int]:
    """Materialize configuration for a specific vendor.

    Args:
        db_path: Path to the content.db database.
        vendor: Vendor name (aider, cursor, copilot, windsurf, amazonq, agents-md, all).
        force: Overwrite existing files.

    Returns:
        Dict with counts per vendor target.
    """
    from ocd.vendors import VENDOR_TARGETS, VENDORS, generate_agents_md

    db = sqlite3.connect(str(db_path))
    counts: dict[str, int] = {}

    if vendor == "all":
        for vname, func in VENDORS.items():
            vtarget = Path(VENDOR_TARGETS[vname])
            vtarget.mkdir(parents=True, exist_ok=True)
            result = func(db, vtarget, force)
            for key, val in result.items():
                counts[f"{vname}_{key}"] = val
        # Also generate AGENTS.md
        agents_md = generate_agents_md(db)
        agents_path = Path("AGENTS.md")
        if not agents_path.exists() or force:
            agents_path.write_text(agents_md)
            counts["agents_md"] = 1
        else:
            counts["agents_md"] = 0
    elif vendor == "agents-md":
        agents_md = generate_agents_md(db)
        agents_path = Path("AGENTS.md")
        if not agents_path.exists() or force:
            agents_path.write_text(agents_md)
            counts["agents_md"] = 1
        else:
            counts["agents_md"] = 0
    elif vendor in VENDORS:
        vtarget = Path(VENDOR_TARGETS[vendor])
        vtarget.mkdir(parents=True, exist_ok=True)
        result = VENDORS[vendor](db, vtarget, force)
        counts.update(result)
    else:
        db.close()
        print(f"Unknown vendor: {vendor}", file=sys.stderr)
        print(f"Available: {', '.join(sorted(VENDORS))}, all, agents-md", file=sys.stderr)
        sys.exit(1)

    db.close()
    return counts


def main() -> None:
    """Entry point for ocd-materialize."""
    from ocd.vendors import VENDORS

    parser = argparse.ArgumentParser(description="Materialize agent config from content.db")
    parser.add_argument(
        "--target",
        "-t",
        default=".claude",
        help="Target directory (default: .claude)",
    )
    parser.add_argument(
        "--db",
        default=None,
        help="Database path (default: package-bundled content.db)",
    )
    parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Overwrite existing files",
    )
    parser.add_argument(
        "--vendor",
        choices=[*sorted(VENDORS), "all", "agents-md"],
        default=None,
        help="Vendor format to materialize (default: claude, uses --target)",
    )
    args = parser.parse_args()

    db_path = Path(args.db) if args.db else _find_bundled_db()

    if args.vendor:
        counts = materialize_vendor(db_path, args.vendor, args.force)
        total = sum(counts.values())
        print(f"Materialized {total} files for {args.vendor}")
        for key, val in sorted(counts.items()):
            print(f"  {key}: {val}")
    else:
        target = Path(args.target)
        counts = materialize(db_path, target, args.force)
        total = sum(counts.values())
        print(f"Materialized {total} files to {target}")
        print(
            f"  agents: {counts['agents']}, rules: {counts['rules']}, "
            f"skills: {counts['skills']}, standards: {counts['standards']}"
        )


if __name__ == "__main__":
    main()
