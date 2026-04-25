"""Materialize vendor directory content from SQLite database.

Reads agents, rules, skills, standards, and settings from the bundled
content.db and reconstructs the original files in the target directory.
For Claude Code, also creates symlinks to portable content in
docs/reference/ and the worktrees directory.

Usage:
    ocd materialize                        # materialize to .claude/
    ocd materialize -t /path/.claude       # materialize to custom target
    ocd materialize --vendor aider          # materialize for Aider
    ocd materialize --vendor all            # materialize for all vendors
    ocd materialize --force                # overwrite existing files
    ocd materialize --db /path/to/db       # use custom database
    ocd materialize --docs-dir docs         # symlink portable content from here
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path

try:
    from ocd.config import DOCS_AGENTS_DIR, DOCS_SKILLS_DIR, PROJECT_ROOT
except ImportError:
    PROJECT_ROOT = Path.cwd()
    DOCS_SKILLS_DIR = PROJECT_ROOT / "docs" / "reference" / "skills"
    DOCS_AGENTS_DIR = PROJECT_ROOT / "docs" / "reference" / "agents"


def _find_bundled_db() -> Path:
    """Locate the bundled database inside the installed package."""
    # When running from source, use the project root path
    source_db = PROJECT_ROOT / "src" / "ocd" / "data" / "content.db"
    if source_db.exists():
        return source_db
    # When installed as a package, use __file__-relative path
    installed_db = Path(__file__).resolve().parent.parent / "data" / "content.db"
    if installed_db.exists():
        return installed_db
    raise FileNotFoundError(
        "Cannot find content.db. Run 'ocd compile-db' to generate it, or specify --db path."
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


def _materialize_settings(db: sqlite3.Connection, target_dir: Path, force: bool) -> int:
    """Write settings .json files from database to target directory."""
    target_dir.mkdir(parents=True, exist_ok=True)
    rows = db.execute("SELECT name, body FROM settings").fetchall()
    count = 0
    for name, body in rows:
        path = target_dir / f"{name}.json"
        if path.exists() and not force:
            continue
        path.write_text(body)
        count += 1
    return count


def _materialize_symlinks(
    target: Path,
    skills_dir: Path,
    agents_dir: Path,
    force: bool = False,
) -> dict[str, int]:
    """Create symlinks from target to portable content directories.

    Creates symlinks for each portable skill and agent file, pointing
    to their canonical source in docs/reference/. Symlinks use relative
    paths that work when target and docs share a common project root:
      .claude/skills/<name>/SKILL.md -> ../../../docs/reference/skills/<name>.md
      .claude/agents/<name>.md       -> ../../docs/reference/agents/<name>.md
    """
    counts: dict[str, int] = {"skill_symlinks": 0, "agent_symlinks": 0}

    # Compute the relative path from target to docs_dir's parent
    # For .claude/ -> docs/reference/, the relative is ../docs/reference/
    # But we need per-skill paths from .claude/skills/<name>/SKILL.md
    # Skill symlinks: target/skills/<name>/SKILL.md -> docs/reference/skills/<name>.md
    if skills_dir.is_dir():
        target_skills = target / "skills"
        target_skills.mkdir(parents=True, exist_ok=True)
        for skill_file in sorted(skills_dir.glob("*.md")):
            skill_name = skill_file.stem
            link_dir = target_skills / skill_name
            link_dir.mkdir(parents=True, exist_ok=True)
            link_path = link_dir / "SKILL.md"
            # 3 levels up from skills/<name>/ to project root
            rel_target = f"../../../docs/reference/skills/{skill_name}.md"
            if link_path.is_symlink() or link_path.exists():
                if force:
                    link_path.unlink()
                else:
                    continue
            os.symlink(rel_target, link_path)
            counts["skill_symlinks"] += 1

    # Agent symlinks: target/agents/<name>.md -> docs/reference/agents/<name>.md
    if agents_dir.is_dir():
        target_agents = target / "agents"
        target_agents.mkdir(parents=True, exist_ok=True)
        for agent_file in sorted(agents_dir.glob("*.md")):
            agent_name = agent_file.stem
            link_path = target_agents / f"{agent_name}.md"
            # From .claude/agents/ go up 2 to project root, then docs/reference/agents/<name>.md
            rel_target = f"../../docs/reference/agents/{agent_name}.md"
            if link_path.is_symlink() or link_path.exists():
                if force:
                    link_path.unlink()
                else:
                    continue
            os.symlink(rel_target, link_path)
            counts["agent_symlinks"] += 1

    return counts


def _materialize_worktrees_dir(target: Path) -> int:
    """Create the empty worktrees directory inside target."""
    worktrees = target / "worktrees"
    worktrees.mkdir(parents=True, exist_ok=True)
    return 1


def materialize(
    db_path: Path,
    target: Path,
    force: bool = False,
    docs_dir: Path | None = None,
) -> dict[str, int]:
    """Materialize all content from database to target directory.

    Args:
        db_path: Path to content.db.
        target: Target directory (e.g. .claude/).
        force: Overwrite existing files.
        docs_dir: Path to docs/reference/ for symlink creation. If provided,
            creates symlinks for portable skills and agents.

    Returns:
        Dict with counts for each content type.
    """
    db = sqlite3.connect(str(db_path))
    n_agents = _materialize_agents(db, target / "agents", force)
    n_rules = _materialize_rules(db, target / "rules", force)
    n_skills = _materialize_skills(db, target / "skills", force)
    n_standards = _materialize_standards(db, target / "skills" / "ocd", force)
    n_settings = _materialize_settings(db, target, force)
    db.close()

    # Create symlinks to portable content if docs_dir is provided
    symlink_counts: dict[str, int] = {}
    if docs_dir:
        skills_dir = docs_dir / "skills"
        agents_dir = docs_dir / "agents"
        symlink_counts = _materialize_symlinks(target, skills_dir, agents_dir, force)

    # Create worktrees directory
    _materialize_worktrees_dir(target)

    return {
        "agents": n_agents,
        "rules": n_rules,
        "skills": n_skills,
        "standards": n_standards,
        "settings": n_settings,
        **symlink_counts,
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
    from ocd.packaging.vendors import VENDOR_TARGETS, VENDORS, generate_agents_md

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


# ── Public API ────────────────────────────────────────────────────────────


def run_materialize(
    target: str = ".claude",
    db: str | None = None,
    force: bool = False,
    vendor: str | None = None,
    docs_dir: str | None = None,
) -> int:
    """Materialize agent config from content.db.

    Args:
        target: Target directory (default: .claude).
        db: Database path, or None to use the bundled content.db.
        force: Overwrite existing files.
        vendor: Vendor format to materialize, or None for default claude format.
        docs_dir: Path to docs/reference/ for creating symlinks to portable content.

    Returns:
        0 on success, 1 on error.
    """
    from ocd.packaging.vendors import VENDORS

    db_path = Path(db) if db else _find_bundled_db()

    if vendor:
        valid_vendors = set(VENDORS) | {"all", "agents-md"}
        if vendor not in valid_vendors:
            print(f"Unknown vendor: {vendor}", file=sys.stderr)
            print(f"Available: {', '.join(sorted(VENDORS))}, all, agents-md", file=sys.stderr)
            return 1
        counts = materialize_vendor(db_path, vendor, force)
        total = sum(counts.values())
        print(f"Materialized {total} files for {vendor}")
        for key, val in sorted(counts.items()):
            print(f"  {key}: {val}")
    else:
        target_path = Path(target)
        docs_path = Path(docs_dir) if docs_dir else None
        counts = materialize(db_path, target_path, force, docs_dir=docs_path)
        total = sum(counts.values())
        print(f"Materialized {total} files to {target_path}")
        print(
            f"  agents: {counts['agents']}, rules: {counts['rules']}, "
            f"skills: {counts['skills']}, standards: {counts['standards']}, "
            f"settings: {counts['settings']}"
        )
        if counts.get("skill_symlinks") or counts.get("agent_symlinks"):
            print(
                f"  skill_symlinks: {counts.get('skill_symlinks', 0)}, "
                f"agent_symlinks: {counts.get('agent_symlinks', 0)}"
            )
    return 0


# ── CLI ──────────────────────────────────────────────────────────────────


def main() -> None:
    """Entry point for ocd materialize command."""
    from ocd.packaging.vendors import VENDORS

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
    parser.add_argument(
        "--docs-dir",
        default=None,
        help="Path to docs/reference/ for creating symlinks to portable content",
    )
    args = parser.parse_args()

    sys.exit(
        run_materialize(
            target=args.target,
            db=args.db,
            force=args.force,
            vendor=args.vendor,
            docs_dir=args.docs_dir,
        )
    )


if __name__ == "__main__":
    main()
