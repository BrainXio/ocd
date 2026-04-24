"""Tests for ocd.kb.export — knowledge base export to Obsidian vault."""

from __future__ import annotations

import sqlite3

import pytest
import yaml

from ocd.kb.export import (
    _build_frontmatter,
    _convert_wikilinks,
    _derive_article_type,
    _generate_backlinks_map,
    _generate_moc,
    _reconstruct_article,
    _slug_from_path,
    run_export,
)
from ocd.kb.ingest import SCHEMA


@pytest.fixture
def temp_export_db(tmp_path):
    """Create a temporary knowledge.db with sample articles."""
    db_path = tmp_path / "knowledge.db"
    conn = sqlite3.connect(str(db_path))
    conn.executescript(SCHEMA)
    conn.execute(
        "INSERT INTO articles VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "concepts/test-concept.md",
            "Test Concept",
            '["alias1", "alias2"]',
            '["tag1", "concepts"]',
            '["daily/2026-04-20.md"]',
            "Body with [[concepts/other-concept]] and [[qa/test-qa]].",
            "abc123def456",
            1000000.0,
            0.8,
            "2026-04-20T10:00:00",
            "2026-04-21T12:00:00",
        ),
    )
    conn.execute(
        "INSERT INTO articles VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "connections/test-connection.md",
            "Test Connection",
            '["conn-alias"]',
            '["tag2", "connections"]',
            '["daily/2026-04-19.md"]',
            "Links to [[concepts/test-concept]].",
            "def789ghi012",
            1000001.0,
            0.6,
            "2026-04-19T08:00:00",
            "2026-04-19T08:00:00",
        ),
    )
    conn.execute(
        "INSERT INTO articles VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "qa/test-qa.md",
            "Test QA",
            None,
            '["qa"]',
            '["daily/2026-04-18.md"]',
            "Q&A about [[concepts/test-concept]].",
            "ghi345jkl678",
            1000002.0,
            0.9,
            "2026-04-18T06:00:00",
            "2026-04-22T14:00:00",
        ),
    )
    conn.commit()
    conn.close()
    return db_path


class TestDeriveArticleType:
    def test_concepts(self):
        assert _derive_article_type("concepts/error-propagation.md") == "concept"

    def test_connections(self):
        assert _derive_article_type("connections/auth-flow.md") == "connection"

    def test_qa(self):
        assert _derive_article_type("qa/why-tests.md") == "qa"

    def test_resources(self):
        assert _derive_article_type("resources/python-style.md") == "resource"

    def test_unknown(self):
        assert _derive_article_type("unknown/file.md") == "article"

    def test_no_prefix(self):
        assert _derive_article_type("standalone.md") == "article"


class TestSlugFromPath:
    def test_strips_md(self):
        assert _slug_from_path("concepts/error-propagation.md") == "concepts/error-propagation"

    def test_no_extension(self):
        assert _slug_from_path("concepts/test") == "concepts/test"


class TestConvertWikilinks:
    def test_same_type_strips_prefix(self):
        body = "See [[concepts/other-concept]] for details."
        assert _convert_wikilinks(body, "concept") == "See [[other-concept]] for details."

    def test_cross_type_keeps_prefix(self):
        body = "See [[qa/test-qa]] for details."
        assert _convert_wikilinks(body, "concept") == "See [[qa/test-qa]] for details."

    def test_daily_link_keeps_prefix(self):
        body = "From [[daily/2026-04-20]]."
        assert _convert_wikilinks(body, "concept") == "From [[daily/2026-04-20]]."

    def test_no_links_passthrough(self):
        body = "No links here."
        assert _convert_wikilinks(body, "concept") == "No links here."

    def test_mixed_links(self):
        body = "See [[concepts/other]] and [[qa/test-qa]]."
        result = _convert_wikilinks(body, "concept")
        assert "[[other]]" in result
        assert "[[qa/test-qa]]" in result


class TestBuildFrontmatter:
    def test_full_fields(self):
        fm = _build_frontmatter(
            title="Test",
            aliases='["a1", "a2"]',
            tags='["t1"]',
            sources='["daily/2026-04-20.md"]',
            score=0.8,
            created="2026-04-20",
            updated="2026-04-21",
            article_type="concept",
        )
        parsed = yaml.safe_load(fm)
        assert parsed["title"] == "Test"
        assert parsed["aliases"] == ["a1", "a2"]
        assert parsed["tags"] == ["t1"]
        assert parsed["score"] == 0.8
        assert parsed["type"] == "concept"

    def test_null_aliases_tags_sources(self):
        fm = _build_frontmatter(
            title="Test",
            aliases=None,
            tags=None,
            sources=None,
            score=0.0,
            created="2026-04-20",
            updated="2026-04-20",
            article_type="article",
        )
        parsed = yaml.safe_load(fm)
        assert parsed["aliases"] == []
        assert parsed["tags"] == []
        assert parsed["sources"] == []

    def test_score_rounded(self):
        fm = _build_frontmatter(
            title="T",
            aliases=None,
            tags=None,
            sources=None,
            score=0.8567,
            created="2026-04-20",
            updated="2026-04-20",
            article_type="concept",
        )
        parsed = yaml.safe_load(fm)
        assert parsed["score"] == 0.86


class TestReconstructArticle:
    def test_valid_format(self):
        content = _reconstruct_article(
            path="concepts/test.md",
            title="Test",
            aliases='["a1"]',
            tags='["t1"]',
            sources='["daily/2026-04-20.md"]',
            body="Body text.",
            score=0.8,
            created="2026-04-20",
            updated="2026-04-21",
        )
        assert content.startswith("---\n")
        parts = content.split("---\n", 2)
        assert len(parts) == 3
        fm = yaml.safe_load(parts[1])
        assert fm["title"] == "Test"
        assert "Body text." in parts[2]

    def test_wikilinks_converted(self):
        content = _reconstruct_article(
            path="concepts/test.md",
            title="Test",
            aliases=None,
            tags=None,
            sources=None,
            body="See [[concepts/other]].",
            score=0.0,
            created="2026-04-20",
            updated="2026-04-20",
        )
        assert "[[other]]" in content


class TestGenerateMoc:
    def test_contains_dataview(self):
        articles = [
            {
                "slug": "concepts/test",
                "type": "concept",
                "updated": "2026-04-21",
                "score": 0.8,
                "body": "",
            },
        ]
        moc = _generate_moc(articles)
        assert "dataview" in moc
        assert 'FROM "concepts"' in moc

    def test_dataview_queries_section(self):
        articles = [
            {
                "slug": "concepts/test",
                "type": "concept",
                "updated": "2026-04-21",
                "score": 0.8,
                "body": "",
            },
        ]
        moc = _generate_moc(articles)
        assert "Dataview Queries" in moc
        assert "WHERE score >= 0.8" in moc

    def test_article_count(self):
        articles = [
            {"slug": "a", "type": "concept", "updated": "2026-04-21", "score": 0.8, "body": ""},
            {"slug": "b", "type": "connection", "updated": "2026-04-20", "score": 0.6, "body": ""},
        ]
        moc = _generate_moc(articles)
        assert "2 articles" in moc

    def test_recent_changes(self):
        articles = [
            {"slug": "new", "type": "concept", "updated": "2026-04-22", "score": 0.8, "body": ""},
            {"slug": "old", "type": "concept", "updated": "2026-04-10", "score": 0.6, "body": ""},
        ]
        moc = _generate_moc(articles)
        assert "[[new]]" in moc


class TestGenerateBacklinksMap:
    def test_basic_backlinks(self):
        articles = [
            {"slug": "concepts/a", "body": "Links to [[concepts/b]]."},
            {"slug": "concepts/b", "body": "No outgoing links."},
        ]
        result = _generate_backlinks_map(articles)
        assert "[[b]]" in result
        assert "[[concepts/a]]" in result

    def test_no_backlinks(self):
        articles = [
            {"slug": "concepts/standalone", "body": "No links."},
        ]
        result = _generate_backlinks_map(articles)
        assert "# Backlinks Map" in result


class TestRunExport:
    def test_default_output_dir(self, temp_export_db, tmp_path, monkeypatch):
        export_dir = tmp_path / "knowledge-export"
        monkeypatch.setattr("ocd.kb.export.KNOWLEDGE_EXPORT_DIR", export_dir)
        monkeypatch.setattr("ocd.kb.export.WIKI_DB", temp_export_db)
        result = run_export(db_path=temp_export_db)
        assert result == 0
        assert (export_dir / "index.md").exists()
        assert (export_dir / "_backlinks.md").exists()
        assert (export_dir / "concepts" / "test-concept.md").exists()

    def test_commit_flag(self, temp_export_db, tmp_path, monkeypatch):
        commit_dir = tmp_path / "docs" / "knowledge"
        monkeypatch.setattr("ocd.kb.export.COMMIT_KNOWLEDGE_DIR", commit_dir)
        result = run_export(commit=True, db_path=temp_export_db)
        assert result == 0
        assert commit_dir.exists()

    def test_output_override(self, temp_export_db, tmp_path):
        custom_dir = tmp_path / "custom-export"
        result = run_export(output=str(custom_dir), db_path=temp_export_db)
        assert result == 0
        assert (custom_dir / "index.md").exists()

    def test_force_overwrite(self, temp_export_db, tmp_path):
        export_dir = tmp_path / "export"
        result = run_export(output=str(export_dir), db_path=temp_export_db)
        assert result == 0
        article = export_dir / "concepts" / "test-concept.md"
        article.write_text("modified content")
        result = run_export(output=str(export_dir), force=True, db_path=temp_export_db)
        assert result == 0
        assert article.read_text() != "modified content"

    def test_skip_existing(self, temp_export_db, tmp_path, capsys):
        export_dir = tmp_path / "export"
        run_export(output=str(export_dir), db_path=temp_export_db)
        run_export(output=str(export_dir), db_path=temp_export_db)
        captured = capsys.readouterr()
        assert "skipped" in captured.out

    def test_dry_run(self, temp_export_db, tmp_path, capsys):
        export_dir = tmp_path / "export"
        result = run_export(output=str(export_dir), dry_run=True, db_path=temp_export_db)
        assert result == 0
        captured = capsys.readouterr()
        assert "Would export" in captured.out
        assert not export_dir.exists()

    def test_missing_db(self, tmp_path, monkeypatch):
        monkeypatch.setattr("ocd.kb.export.WIKI_DB", tmp_path / "nonexistent.db")
        result = run_export(db_path=tmp_path / "nonexistent.db")
        assert result == 1

    def test_empty_db(self, tmp_path):
        db_path = tmp_path / "empty.db"
        conn = sqlite3.connect(str(db_path))
        conn.executescript(SCHEMA)
        conn.close()
        result = run_export(db_path=db_path)
        assert result == 0

    def test_directory_structure(self, temp_export_db, tmp_path):
        export_dir = tmp_path / "export"
        run_export(output=str(export_dir), db_path=temp_export_db)
        assert (export_dir / "concepts").is_dir()
        assert (export_dir / "connections").is_dir()
        assert (export_dir / "qa").is_dir()

    def test_moc_generated(self, temp_export_db, tmp_path):
        export_dir = tmp_path / "export"
        run_export(output=str(export_dir), db_path=temp_export_db)
        moc = (export_dir / "index.md").read_text()
        assert "dataview" in moc
        assert "Knowledge Base Index" in moc

    def test_article_count(self, temp_export_db, tmp_path):
        export_dir = tmp_path / "export"
        run_export(output=str(export_dir), db_path=temp_export_db)
        md_files = list(export_dir.rglob("*.md"))
        article_files = [f for f in md_files if f.parent.name != "export"]
        assert len(article_files) >= 3
