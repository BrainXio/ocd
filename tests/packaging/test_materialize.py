"""Tests for ocd.packaging.materialize — materialization and selective skills."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from ocd.packaging.materialize import (
    _CORE_SKILLS,
    VENDOR_CHOICES,
    VENDOR_LAYOUTS,
    _materialize_agents,
    _materialize_rules,
    _materialize_settings,
    _materialize_skills,
    _materialize_standards,
    _materialize_symlinks,
    _materialize_worktrees_dir,
    _quote_if_needed,
    _resolve_skill_filter,
    materialize,
)


@pytest.fixture
def db(tmp_path: Path) -> sqlite3.Connection:
    """Create a test database with sample content."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "CREATE TABLE agents (name TEXT PRIMARY KEY, "
        "frontmatter TEXT NOT NULL, body TEXT NOT NULL, "
        "created TEXT NOT NULL, updated TEXT NOT NULL)"
    )
    conn.execute(
        "CREATE TABLE rules (name TEXT PRIMARY KEY, "
        "description TEXT NOT NULL, paths TEXT, body TEXT NOT NULL, "
        "created TEXT NOT NULL, updated TEXT NOT NULL)"
    )
    conn.execute(
        "CREATE TABLE skills (name TEXT PRIMARY KEY, "
        "description TEXT NOT NULL, argument_hint TEXT, body TEXT NOT NULL, "
        "created TEXT NOT NULL, updated TEXT NOT NULL)"
    )
    conn.execute(
        "CREATE TABLE standards (id INTEGER PRIMARY KEY CHECK(id=1), "
        "version TEXT NOT NULL, hash TEXT NOT NULL, body TEXT NOT NULL, "
        "created TEXT NOT NULL, updated TEXT NOT NULL)"
    )
    conn.execute(
        "CREATE TABLE settings (name TEXT PRIMARY KEY, "
        "body TEXT NOT NULL, created TEXT NOT NULL, updated TEXT NOT NULL)"
    )

    conn.execute(
        "INSERT INTO agents VALUES (?, ?, ?, ?, ?)",
        (
            "test-agent",
            "name: test-agent\ndescription: A test agent",
            "You are a test agent.",
            "2026-01-01",
            "2026-01-01",
        ),
    )
    conn.execute(
        "INSERT INTO rules VALUES (?, ?, ?, ?, ?, ?)",
        (
            "commit-hygiene",
            "Conventional commits",
            None,
            "Use conventional commits.",
            "2026-01-01",
            "2026-01-01",
        ),
    )
    conn.execute(
        "INSERT INTO rules VALUES (?, ?, ?, ?, ?, ?)",
        ("markdown", "mdformat rules", '"**/*.md"', "Use mdformat.", "2026-01-01", "2026-01-01"),
    )
    conn.execute(
        "INSERT INTO skills VALUES (?, ?, ?, ?, ?, ?)",
        ("ocd", "OCD skill", None, "Obsessive Code Discipline skill.", "2026-01-01", "2026-01-01"),
    )
    conn.execute(
        "INSERT INTO skills VALUES (?, ?, ?, ?, ?, ?)",
        ("python", "Python skill", "[path]", "Write Python code.", "2026-01-01", "2026-01-01"),
    )
    conn.execute(
        "INSERT INTO skills VALUES (?, ?, ?, ?, ?, ?)",
        ("git", "Git skill", None, "Git workflow.", "2026-01-01", "2026-01-01"),
    )
    conn.execute(
        "INSERT INTO standards VALUES (?, ?, ?, ?, ?, ?)",
        (1, "2.0", "abc123", "Nine Standards text", "2026-01-01", "2026-01-01"),
    )
    conn.execute(
        "INSERT INTO settings VALUES (?, ?, ?, ?)",
        ("settings", '{"hooks": {}}', "2026-01-01", "2026-01-01"),
    )
    conn.execute(
        "INSERT INTO settings VALUES (?, ?, ?, ?)",
        ("settings.local", '{"permissions": {}}', "2026-01-01", "2026-01-01"),
    )
    conn.commit()
    return conn


class TestMaterializeAgents:
    def test_creates_agent_files(self, db: sqlite3.Connection, tmp_path: Path) -> None:
        target = tmp_path / "agents"
        count = _materialize_agents(db, target, force=True)
        assert count == 1
        assert (target / "test-agent.md").exists()

    def test_skip_existing(self, db: sqlite3.Connection, tmp_path: Path) -> None:
        target = tmp_path / "agents"
        _materialize_agents(db, target, force=True)
        count = _materialize_agents(db, target, force=False)
        assert count == 0

    def test_overwrite_with_force(self, db: sqlite3.Connection, tmp_path: Path) -> None:
        target = tmp_path / "agents"
        _materialize_agents(db, target, force=True)
        count = _materialize_agents(db, target, force=True)
        assert count == 1


class TestMaterializeRules:
    def test_creates_rule_files(self, db: sqlite3.Connection, tmp_path: Path) -> None:
        target = tmp_path / "rules"
        count = _materialize_rules(db, target, force=True)
        assert count == 2
        assert (target / "commit-hygiene.md").exists()
        assert (target / "markdown.md").exists()


class TestMaterializeSkills:
    def test_creates_skill_dirs(self, db: sqlite3.Connection, tmp_path: Path) -> None:
        target = tmp_path / "skills"
        count = _materialize_skills(db, target, force=True, include=None)
        assert count == 3  # ocd, python, git
        assert (target / "ocd" / "SKILL.md").exists()
        assert (target / "python" / "SKILL.md").exists()
        assert (target / "git" / "SKILL.md").exists()

    def test_minimal_only_core(self, db: sqlite3.Connection, tmp_path: Path) -> None:
        target = tmp_path / "skills"
        count = _materialize_skills(db, target, force=True, include={"ocd"})
        assert count == 1
        assert (target / "ocd" / "SKILL.md").exists()
        assert not (target / "python" / "SKILL.md").exists()

    def test_include_specific_skills(self, db: sqlite3.Connection, tmp_path: Path) -> None:
        target = tmp_path / "skills"
        count = _materialize_skills(db, target, force=True, include={"python", "git"})
        # Core skill (ocd) is always included
        assert count == 3
        assert (target / "ocd" / "SKILL.md").exists()
        assert (target / "python" / "SKILL.md").exists()
        assert (target / "git" / "SKILL.md").exists()

    def test_include_nonexistent_skill(self, db: sqlite3.Connection, tmp_path: Path) -> None:
        target = tmp_path / "skills"
        count = _materialize_skills(db, target, force=True, include={"nonexistent"})
        # Only core skills
        assert count == 1
        assert (target / "ocd" / "SKILL.md").exists()


class TestMaterializeSettings:
    def test_creates_settings_files(self, db: sqlite3.Connection, tmp_path: Path) -> None:
        count = _materialize_settings(db, tmp_path, force=True)
        assert count == 2
        assert (tmp_path / "settings.json").exists()
        assert (tmp_path / "settings.local.json").exists()

    def test_skip_existing(self, db: sqlite3.Connection, tmp_path: Path) -> None:
        _materialize_settings(db, tmp_path, force=True)
        count = _materialize_settings(db, tmp_path, force=False)
        assert count == 0

    def test_overwrite_with_force(self, db: sqlite3.Connection, tmp_path: Path) -> None:
        _materialize_settings(db, tmp_path, force=True)
        count = _materialize_settings(db, tmp_path, force=True)
        assert count == 2


class TestMaterializeStandards:
    def test_creates_standards(self, db: sqlite3.Connection, tmp_path: Path) -> None:
        target = tmp_path / "skills" / "ocd"
        count = _materialize_standards(db, target, force=True)
        assert count == 1
        assert (target / "standards.md").exists()

    def test_skip_existing(self, db: sqlite3.Connection, tmp_path: Path) -> None:
        target = tmp_path / "skills" / "ocd"
        _materialize_standards(db, target, force=True)
        count = _materialize_standards(db, target, force=False)
        assert count == 0


class TestMaterializeSymlinks:
    def test_creates_skill_symlinks(self, tmp_path: Path) -> None:
        target = tmp_path / "claude"
        docs_dir = tmp_path / "docs" / "reference"
        skills_dir = docs_dir / "skills"
        skills_dir.mkdir(parents=True)
        (skills_dir / "bash.md").write_text("---\nname: bash\ndescription: Bash\n---\nBash skill.")
        (skills_dir / "python.md").write_text(
            "---\nname: python\ndescription: Python\n---\nPython skill."
        )

        counts = _materialize_symlinks(target, skills_dir, tmp_path / "agents", force=True)
        assert counts["skill_symlinks"] == 2
        link = target / "skills" / "bash" / "SKILL.md"
        assert link.is_symlink()

    def test_creates_agent_symlinks(self, tmp_path: Path) -> None:
        target = tmp_path / "claude"
        agents_dir = tmp_path / "docs" / "reference" / "agents"
        agents_dir.mkdir(parents=True)
        (agents_dir / "accessibility-auditor.md").write_text(
            "---\nname: accessibility-auditor\n---\nAgent."
        )

        counts = _materialize_symlinks(target, tmp_path / "skills", agents_dir, force=True)
        assert counts["agent_symlinks"] == 1
        link = target / "agents" / "accessibility-auditor.md"
        assert link.is_symlink()

    def test_selective_skill_symlinks(self, tmp_path: Path) -> None:
        target = tmp_path / "claude"
        docs_dir = tmp_path / "docs" / "reference"
        skills_dir = docs_dir / "skills"
        skills_dir.mkdir(parents=True)
        (skills_dir / "bash.md").write_text("---\nname: bash\n---\nBash.")
        (skills_dir / "python.md").write_text("---\nname: python\n---\nPython.")
        (skills_dir / "git.md").write_text("---\nname: git\n---\nGit.")

        counts = _materialize_symlinks(
            target, skills_dir, tmp_path / "agents", force=True, include={"python", "git"}
        )
        # Core skills always included, plus explicitly named
        assert counts["skill_symlinks"] == 2  # python, git (ocd not in docs)
        assert (target / "skills" / "python" / "SKILL.md").is_symlink()
        assert (target / "skills" / "git" / "SKILL.md").is_symlink()
        assert not (target / "skills" / "bash").exists()


class TestMaterializeWorktreesDir:
    def test_creates_worktrees_dir(self, tmp_path: Path) -> None:
        target = tmp_path / "claude"
        result = _materialize_worktrees_dir(target)
        assert result == 1
        assert (target / "worktrees").is_dir()


class TestMaterializeIntegration:
    def test_full_materialize(self, db: sqlite3.Connection, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        target = tmp_path / "claude"
        # Close the in-memory db and use the file-based one
        db.close()
        counts = materialize(db_path, target, force=True)
        assert counts["agents"] == 1
        assert counts["rules"] == 2
        assert counts["skills"] == 3
        assert counts["standards"] == 1
        assert counts["settings"] == 2
        assert (target / "agents" / "test-agent.md").exists()
        assert (target / "rules" / "commit-hygiene.md").exists()
        assert (target / "skills" / "ocd" / "SKILL.md").exists()
        assert (target / "skills" / "ocd" / "standards.md").exists()
        assert (target / "settings.json").exists()
        assert (target / "worktrees").is_dir()

    def test_minimal_materialize(self, db: sqlite3.Connection, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        target = tmp_path / "claude"
        db.close()
        counts = materialize(db_path, target, force=True, include={"ocd"})
        assert counts["agents"] == 1
        assert counts["rules"] == 2
        assert counts["skills"] == 1  # only ocd
        assert counts["standards"] == 1
        assert counts["settings"] == 2

    def test_selective_materialize(self, db: sqlite3.Connection, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        target = tmp_path / "claude"
        db.close()
        counts = materialize(db_path, target, force=True, include={"python"})
        assert counts["skills"] == 2  # ocd (core) + python

    def test_materialize_with_symlinks(self, tmp_path: Path) -> None:
        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            "CREATE TABLE agents (name TEXT PRIMARY KEY, "
            "frontmatter TEXT NOT NULL, body TEXT NOT NULL, "
            "created TEXT NOT NULL, updated TEXT NOT NULL)"
        )
        conn.execute(
            "CREATE TABLE rules (name TEXT PRIMARY KEY, "
            "description TEXT NOT NULL, paths TEXT, body TEXT NOT NULL, "
            "created TEXT NOT NULL, updated TEXT NOT NULL)"
        )
        conn.execute(
            "CREATE TABLE skills (name TEXT PRIMARY KEY, "
            "description TEXT NOT NULL, argument_hint TEXT, body TEXT NOT NULL, "
            "created TEXT NOT NULL, updated TEXT NOT NULL)"
        )
        conn.execute(
            "CREATE TABLE standards (id INTEGER PRIMARY KEY CHECK(id=1), "
            "version TEXT NOT NULL, hash TEXT NOT NULL, body TEXT NOT NULL, "
            "created TEXT NOT NULL, updated TEXT NOT NULL)"
        )
        conn.execute(
            "CREATE TABLE settings (name TEXT PRIMARY KEY, "
            "body TEXT NOT NULL, created TEXT NOT NULL, updated TEXT NOT NULL)"
        )
        conn.execute(
            "INSERT INTO skills VALUES (?, ?, ?, ?, ?, ?)",
            ("ocd", "OCD", None, "Skill.", "2026-01-01", "2026-01-01"),
        )
        conn.execute(
            "INSERT INTO rules VALUES (?, ?, ?, ?, ?, ?)",
            ("test-rule", "Test", None, "Rule.", "2026-01-01", "2026-01-01"),
        )
        conn.execute(
            "INSERT INTO standards VALUES (?, ?, ?, ?, ?, ?)",
            (1, "1.0", "hash", "Standards.", "2026-01-01", "2026-01-01"),
        )
        conn.execute(
            "INSERT INTO settings VALUES (?, ?, ?, ?)",
            ("settings", "{}", "2026-01-01", "2026-01-01"),
        )
        conn.commit()
        conn.close()

        target = tmp_path / "claude"
        docs_dir = tmp_path / "docs" / "reference"
        skills_dir = docs_dir / "skills"
        skills_dir.mkdir(parents=True)
        (skills_dir / "bash.md").write_text("---\nname: bash\n---\nBash.")

        counts = materialize(db_path, target, force=True, docs_dir=docs_dir)
        assert counts["skill_symlinks"] == 1
        assert counts["agent_symlinks"] == 0
        link = target / "skills" / "bash" / "SKILL.md"
        assert link.is_symlink()


class TestResolveSkillFilter:
    def test_minimal_returns_core_only(self) -> None:
        result = _resolve_skill_filter(include=None, all_skills=False, minimal=True)
        assert result == _CORE_SKILLS

    def test_include_adds_core(self) -> None:
        result = _resolve_skill_filter(include="python,git", all_skills=False, minimal=False)
        assert "python" in result
        assert "git" in result
        assert "ocd" in result  # core always included

    def test_all_returns_none(self) -> None:
        result = _resolve_skill_filter(include=None, all_skills=True, minimal=False)
        assert result is None

    def test_default_returns_none(self) -> None:
        result = _resolve_skill_filter(include=None, all_skills=False, minimal=False)
        assert result is None

    def test_minimal_overrides_include(self) -> None:
        result = _resolve_skill_filter(include="python", all_skills=False, minimal=True)
        assert result == _CORE_SKILLS


class TestQuoteIfNeeded:
    def test_plain_string(self) -> None:
        assert _quote_if_needed("hello") == "hello"

    def test_colon(self) -> None:
        assert _quote_if_needed("hello: world") == '"hello: world"'

    def test_hash(self) -> None:
        assert _quote_if_needed("#tag") == '"#tag"'


class TestVendorLayouts:
    def test_claude_code_layout(self) -> None:
        layout = VENDOR_LAYOUTS["claude-code"]
        assert layout["root"] == ".claude"
        assert layout["agents_dir"] == "agents"
        assert layout["rules_dir"] == "rules"
        assert layout["skills_dir"] == "skills"
        assert "settings_file" in layout

    def test_all_vendors_have_layouts(self) -> None:
        for vendor in ("aider", "cursor", "copilot", "windsurf", "amazonq"):
            assert vendor in VENDOR_LAYOUTS

    def test_vendor_choices_include_claude_code(self) -> None:
        assert "claude-code" in VENDOR_CHOICES
