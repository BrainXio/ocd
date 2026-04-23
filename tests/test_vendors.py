"""Tests for ocd.vendors — vendor format adapters."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from ocd.vendors import (
    VENDOR_TARGETS,
    VENDORS,
    generate_agents_md,
    materialize_aider,
    materialize_amazonq,
    materialize_copilot,
    materialize_cursor,
    materialize_windsurf,
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
            "Conventional commits and no AI attribution",
            None,
            "Use conventional commits.\nNo AI attribution.",
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
        ("python", "Python skill", "[path]", "Write Python code.", "2026-01-01", "2026-01-01"),
    )
    conn.execute(
        "INSERT INTO standards VALUES (?, ?, ?, ?, ?, ?)",
        (1, "2.0", "abc123", "Nine Standards text", "2026-01-01", "2026-01-01"),
    )
    conn.commit()
    return conn


class TestAider:
    """materialize_aider creates CONVENTIONS.md and .aider.conf.yml."""

    def test_creates_conventions_and_config(self, db: sqlite3.Connection, tmp_path: Path) -> None:
        target = tmp_path / "aider"
        counts = materialize_aider(db, target, force=True)
        assert counts["conventions"] == 1
        assert counts["config"] == 1
        assert (target / "CONVENTIONS.md").exists()
        assert (target / ".aider.conf.yml").exists()

    def test_conventions_contains_rules(self, db: sqlite3.Connection, tmp_path: Path) -> None:
        target = tmp_path / "aider"
        materialize_aider(db, target, force=True)
        content = (target / "CONVENTIONS.md").read_text()
        assert "commit-hygiene" in content
        assert "markdown" in content
        assert "Conventional commits" in content

    def test_config_points_to_conventions(self, db: sqlite3.Connection, tmp_path: Path) -> None:
        target = tmp_path / "aider"
        materialize_aider(db, target, force=True)
        content = (target / ".aider.conf.yml").read_text()
        assert "CONVENTIONS.md" in content

    def test_skip_existing(self, db: sqlite3.Connection, tmp_path: Path) -> None:
        target = tmp_path / "aider"
        materialize_aider(db, target, force=True)
        counts = materialize_aider(db, target, force=False)
        assert counts["conventions"] == 0
        assert counts["config"] == 0

    def test_overwrite_with_force(self, db: sqlite3.Connection, tmp_path: Path) -> None:
        target = tmp_path / "aider"
        materialize_aider(db, target, force=True)
        counts = materialize_aider(db, target, force=True)
        assert counts["conventions"] == 1
        assert counts["config"] == 1


class TestCursor:
    """materialize_cursor creates .cursor/rules/*.mdc files."""

    def test_creates_mdc_files(self, db: sqlite3.Connection, tmp_path: Path) -> None:
        target = tmp_path / "cursor" / "rules"
        counts = materialize_cursor(db, target, force=True)
        assert counts["rules"] == 2
        assert (target / "commit-hygiene.mdc").exists()
        assert (target / "markdown.mdc").exists()

    def test_mdc_has_frontmatter(self, db: sqlite3.Connection, tmp_path: Path) -> None:
        target = tmp_path / "cursor" / "rules"
        materialize_cursor(db, target, force=True)
        content = (target / "commit-hygiene.mdc").read_text()
        assert content.startswith("---")
        assert "description:" in content
        assert "alwaysApply: true" in content

    def test_mdc_with_globs(self, db: sqlite3.Connection, tmp_path: Path) -> None:
        target = tmp_path / "cursor" / "rules"
        materialize_cursor(db, target, force=True)
        content = (target / "markdown.mdc").read_text()
        assert "globs:" in content


class TestCopilot:
    """materialize_copilot creates .github/copilot-instructions.md and instructions/."""

    def test_creates_global_instructions(self, db: sqlite3.Connection, tmp_path: Path) -> None:
        target = tmp_path / "project"
        counts = materialize_copilot(db, target, force=True)
        assert counts["global"] == 1
        assert (target / ".github" / "copilot-instructions.md").exists()

    def test_creates_scoped_instructions(self, db: sqlite3.Connection, tmp_path: Path) -> None:
        target = tmp_path / "project"
        counts = materialize_copilot(db, target, force=True)
        assert counts["scoped"] == 1
        assert (target / ".github" / "instructions" / "markdown.instructions.md").exists()

    def test_scoped_instructions_have_apply_to(
        self, db: sqlite3.Connection, tmp_path: Path
    ) -> None:
        target = tmp_path / "project"
        materialize_copilot(db, target, force=True)
        content = (target / ".github" / "instructions" / "markdown.instructions.md").read_text()
        assert "applyTo:" in content


class TestWindsurf:
    """materialize_windsurf creates .windsurf/rules/*.md files."""

    def test_creates_rule_files(self, db: sqlite3.Connection, tmp_path: Path) -> None:
        target = tmp_path / "windsurf" / "rules"
        counts = materialize_windsurf(db, target, force=True)
        assert counts["rules"] == 2
        assert (target / "commit-hygiene.md").exists()

    def test_rule_has_frontmatter(self, db: sqlite3.Connection, tmp_path: Path) -> None:
        target = tmp_path / "windsurf" / "rules"
        materialize_windsurf(db, target, force=True)
        content = (target / "commit-hygiene.md").read_text()
        assert "trigger: always" in content
        assert "description:" in content


class TestAmazonQ:
    """materialize_amazonq creates .amazonq/rules/*.md files."""

    def test_creates_rule_files(self, db: sqlite3.Connection, tmp_path: Path) -> None:
        target = tmp_path / "amazonq" / "rules"
        counts = materialize_amazonq(db, target, force=True)
        assert counts["rules"] == 2
        assert (target / "commit-hygiene.md").exists()

    def test_rule_has_sections(self, db: sqlite3.Connection, tmp_path: Path) -> None:
        target = tmp_path / "amazonq" / "rules"
        materialize_amazonq(db, target, force=True)
        content = (target / "commit-hygiene.md").read_text()
        assert "**Purpose:**" in content
        assert "**Instructions:**" in content
        assert "**Priority:**" in content


class TestAgentsMd:
    """generate_agents_md produces a cross-vendor instruction file."""

    def test_contains_standards_reference(self, db: sqlite3.Connection) -> None:
        content = generate_agents_md(db)
        assert "v2.0" in content
        assert "abc123" in content

    def test_contains_agents(self, db: sqlite3.Connection) -> None:
        content = generate_agents_md(db)
        assert "test-agent" in content

    def test_contains_rules(self, db: sqlite3.Connection) -> None:
        content = generate_agents_md(db)
        assert "commit-hygiene" in content

    def test_contains_skills(self, db: sqlite3.Connection) -> None:
        content = generate_agents_md(db)
        assert "python" in content


class TestVendorRegistry:
    """VENDORS and VENDOR_TARGETS are consistent."""

    def test_all_vendors_have_targets(self) -> None:
        for vendor in VENDORS:
            assert vendor in VENDOR_TARGETS

    def test_all_targets_have_vendors(self) -> None:
        for vendor in VENDOR_TARGETS:
            assert vendor in VENDORS
