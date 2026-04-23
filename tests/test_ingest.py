"""Tests for the knowledge ingestion pipeline."""

import json
import os
import sqlite3
import time

from ocd.ingest import (
    _file_hash,
    _parse_list_field,
    _score_article,
    _split_frontmatter,
    ingest_raw,
    kb_status,
)

# ── Frontmatter parsing ─────────────────────────────────────────────────────


class TestSplitFrontmatter:
    def test_basic_frontmatter(self):
        content = "---\ntitle: Foo\ntags: [a, b]\n---\nBody text."
        fm, body = _split_frontmatter(content)
        assert fm["title"] == "Foo"
        assert fm["tags"] == "[a, b]"
        assert body == "Body text."

    def test_no_frontmatter(self):
        content = "Just plain text."
        fm, body = _split_frontmatter(content)
        assert fm == {}
        assert body == "Just plain text."

    def test_unclosed_frontmatter(self):
        content = "---\ntitle: Foo\nBody text."
        fm, body = _split_frontmatter(content)
        assert fm == {}
        assert body == content


class TestParseListField:
    def test_bracket_list(self):
        assert _parse_list_field("[tag1, tag2]") == ["tag1", "tag2"]

    def test_empty(self):
        assert _parse_list_field("") == []
        assert _parse_list_field(None) == []

    def test_single_value(self):
        assert _parse_list_field("single") == ["single"]


# ── Scoring ──────────────────────────────────────────────────────────────────


class TestScoreArticle:
    def test_perfect_score(self):
        fm = {"title": "Test", "tags": "[a, b]", "sources": "[src1]"}
        body = "word " * 120 + "[[link]]"
        assert _score_article(fm, body) == 1.0

    def test_minimal_score(self):
        fm: dict[str, str] = {}
        body = "short"
        assert _score_article(fm, body) == 0.0

    def test_partial_score(self):
        fm = {"title": "Test"}
        body = "short"
        assert _score_article(fm, body) == 0.2


# ── Hashing ──────────────────────────────────────────────────────────────────


class TestFileHash:
    def test_deterministic(self):
        h1 = _file_hash("content")
        h2 = _file_hash("content")
        assert h1 == h2

    def test_different_content(self):
        h1 = _file_hash("content1")
        h2 = _file_hash("content2")
        assert h1 != h2

    def test_length(self):
        assert len(_file_hash("x")) == 16


# ── Schema creation ──────────────────────────────────────────────────────────


class TestSchemaCreation:
    def test_creates_db_with_tables(self, tmp_path, monkeypatch):
        db_path = tmp_path / "knowledge.db"
        knowledge_dir = tmp_path / "knowledge"
        knowledge_dir.mkdir()
        monkeypatch.setattr("ocd.ingest.WIKI_DB", db_path)

        # Create a file so the DB is actually created (empty scan returns early)
        (knowledge_dir / "concepts").mkdir()
        (knowledge_dir / "concepts" / "test.md").write_text("---\ntitle: Test\n---\nBody.")

        result = ingest_raw(knowledge_dir=knowledge_dir, db_path=db_path)
        assert result.scanned == 1

        assert db_path.exists()
        db = sqlite3.connect(str(db_path))
        tables = {
            row[0]
            for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        db.close()
        assert "articles" in tables
        assert "ingestion_log" in tables

    def test_mtime_column_exists(self, tmp_path, monkeypatch):
        db_path = tmp_path / "knowledge.db"
        knowledge_dir = tmp_path / "knowledge"
        knowledge_dir.mkdir()
        monkeypatch.setattr("ocd.ingest.WIKI_DB", db_path)

        (knowledge_dir / "concepts").mkdir()
        (knowledge_dir / "concepts" / "test.md").write_text("---\ntitle: Test\n---\nBody.")

        ingest_raw(knowledge_dir=knowledge_dir, db_path=db_path)

        db = sqlite3.connect(str(db_path))
        cols = [row[1] for row in db.execute("PRAGMA table_info(articles)").fetchall()]
        db.close()
        assert "mtime" in cols

    def test_mtime_stored(self, tmp_path, monkeypatch):
        db_path = tmp_path / "knowledge.db"
        knowledge_dir = tmp_path / "knowledge"
        knowledge_dir.mkdir()
        monkeypatch.setattr("ocd.ingest.WIKI_DB", db_path)

        f = knowledge_dir / "concepts" / "test.md"
        f.parent.mkdir(parents=True)
        f.write_text("---\ntitle: Test\n---\nBody.")
        file_mtime = os.path.getmtime(f)

        ingest_raw(knowledge_dir=knowledge_dir, db_path=db_path)

        db = sqlite3.connect(str(db_path))
        row = db.execute("SELECT mtime FROM articles WHERE path = 'concepts/test.md'").fetchone()
        db.close()
        assert row is not None
        assert row[0] == file_mtime


# ── Ingest articles ──────────────────────────────────────────────────────────


class TestIngestArticles:
    def test_insert_articles(self, tmp_raw_kb, tmp_path, monkeypatch):
        db_path = tmp_path / "knowledge.db"
        monkeypatch.setattr("ocd.ingest.WIKI_DB", db_path)

        tmp_raw_kb("concepts", "oauth", "---\ntitle: OAuth\n---\nOAuth content.")
        tmp_raw_kb("connections", "auth-flow", "---\ntitle: Auth Flow\n---\nFlow content.")

        result = ingest_raw(knowledge_dir=tmp_path / "knowledge", db_path=db_path)
        assert result.scanned == 2
        assert result.inserted == 2
        assert result.skipped == 0

    def test_article_metadata_stored(self, tmp_raw_kb, tmp_path, monkeypatch):
        db_path = tmp_path / "knowledge.db"
        monkeypatch.setattr("ocd.ingest.WIKI_DB", db_path)

        tmp_raw_kb(
            "concepts",
            "oauth",
            "---\ntitle: OAuth Redirect\ntags: [auth, security]\n---\nContent here.",
        )

        ingest_raw(knowledge_dir=tmp_path / "knowledge", db_path=db_path)

        db = sqlite3.connect(str(db_path))
        row = db.execute("SELECT path, title, tags, score FROM articles").fetchone()
        db.close()
        assert row is not None
        assert row[0] == "concepts/oauth.md"
        assert row[1] == "OAuth Redirect"
        assert json.loads(row[2]) == ["auth", "security"]
        assert row[3] > 0


# ── Deduplication ────────────────────────────────────────────────────────────


class TestDeduplication:
    def test_unchanged_articles_skipped(self, tmp_raw_kb, tmp_path, monkeypatch):
        db_path = tmp_path / "knowledge.db"
        monkeypatch.setattr("ocd.ingest.WIKI_DB", db_path)
        knowledge_dir = tmp_path / "knowledge"

        tmp_raw_kb("concepts", "oauth", "---\ntitle: OAuth\n---\nSame content.")

        result1 = ingest_raw(knowledge_dir=knowledge_dir, db_path=db_path)
        assert result1.inserted == 1

        result2 = ingest_raw(knowledge_dir=knowledge_dir, db_path=db_path)
        assert result2.skipped == 1
        assert result2.inserted == 0


# ── Mtime change detection ──────────────────────────────────────────────────


class TestMtimeDetection:
    def test_mtime_match_skips_file(self, tmp_raw_kb, tmp_path, monkeypatch):
        """When mtime matches, file is skipped without reading content."""
        db_path = tmp_path / "knowledge.db"
        monkeypatch.setattr("ocd.ingest.WIKI_DB", db_path)
        knowledge_dir = tmp_path / "knowledge"

        tmp_raw_kb("concepts", "oauth", "---\ntitle: OAuth\n---\nSame content.")

        result1 = ingest_raw(knowledge_dir=knowledge_dir, db_path=db_path)
        assert result1.inserted == 1

        result2 = ingest_raw(knowledge_dir=knowledge_dir, db_path=db_path)
        assert result2.skipped == 1

    def test_mtime_change_triggers_hash_check(self, tmp_raw_kb, tmp_path, monkeypatch):
        """When mtime changes but content is the same, still skipped (hash match)."""
        db_path = tmp_path / "knowledge.db"
        monkeypatch.setattr("ocd.ingest.WIKI_DB", db_path)
        knowledge_dir = tmp_path / "knowledge"

        content = "---\ntitle: OAuth\n---\nSame content."
        path = tmp_raw_kb("concepts", "oauth", content)

        ingest_raw(knowledge_dir=knowledge_dir, db_path=db_path)

        # Touch file (change mtime without changing content)
        os.utime(path, (time.time() + 10, time.time() + 10))

        result = ingest_raw(knowledge_dir=knowledge_dir, db_path=db_path)
        assert result.skipped == 1

        # Verify mtime was updated in DB
        db = sqlite3.connect(str(db_path))
        row = db.execute("SELECT mtime FROM articles WHERE path = 'concepts/oauth.md'").fetchone()
        db.close()
        assert row is not None
        assert row[0] > 0

    def test_content_change_detected(self, tmp_raw_kb, tmp_path, monkeypatch):
        """When both mtime and hash differ, article is updated."""
        db_path = tmp_path / "knowledge.db"
        monkeypatch.setattr("ocd.ingest.WIKI_DB", db_path)
        knowledge_dir = tmp_path / "knowledge"

        path = tmp_raw_kb("concepts", "oauth", "---\ntitle: OAuth\n---\nOriginal.")
        ingest_raw(knowledge_dir=knowledge_dir, db_path=db_path)

        # Change content (this also changes mtime)
        path.write_text("---\ntitle: OAuth v2\n---\nUpdated content.")

        result = ingest_raw(knowledge_dir=knowledge_dir, db_path=db_path)
        assert result.updated == 1

        db = sqlite3.connect(str(db_path))
        row = db.execute("SELECT title FROM articles").fetchone()
        db.close()
        assert row[0] == "OAuth v2"


# ── Deletion detection ───────────────────────────────────────────────────────


class TestDeletionDetection:
    def test_deleted_file_removed_from_db(self, tmp_raw_kb, tmp_path, monkeypatch):
        db_path = tmp_path / "knowledge.db"
        monkeypatch.setattr("ocd.ingest.WIKI_DB", db_path)
        knowledge_dir = tmp_path / "knowledge"

        path = tmp_raw_kb("concepts", "oauth", "---\ntitle: OAuth\n---\nOAuth content.")
        ingest_raw(knowledge_dir=knowledge_dir, db_path=db_path)

        # Delete the file from disk
        path.unlink()

        result = ingest_raw(knowledge_dir=knowledge_dir, db_path=db_path)
        assert result.deleted == 1

        # Verify row removed from DB
        db = sqlite3.connect(str(db_path))
        count = db.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
        db.close()
        assert count == 0

    def test_deletion_logged(self, tmp_raw_kb, tmp_path, monkeypatch):
        db_path = tmp_path / "knowledge.db"
        monkeypatch.setattr("ocd.ingest.WIKI_DB", db_path)
        knowledge_dir = tmp_path / "knowledge"

        path = tmp_raw_kb("concepts", "oauth", "---\ntitle: OAuth\n---\nOAuth content.")
        ingest_raw(knowledge_dir=knowledge_dir, db_path=db_path)

        path.unlink()

        ingest_raw(knowledge_dir=knowledge_dir, db_path=db_path)

        db = sqlite3.connect(str(db_path))
        actions = [r[0] for r in db.execute("SELECT action FROM ingestion_log").fetchall()]
        db.close()
        assert "delete" in actions

    def test_ingest_result_has_deleted_field(self, tmp_raw_kb, tmp_path, monkeypatch):
        db_path = tmp_path / "knowledge.db"
        monkeypatch.setattr("ocd.ingest.WIKI_DB", db_path)

        tmp_raw_kb("concepts", "test", "---\ntitle: Test\n---\nBody.")

        result = ingest_raw(knowledge_dir=tmp_path / "knowledge", db_path=db_path)
        assert hasattr(result, "deleted")
        assert result.deleted == 0


# ── Update detection ────────────────────────────────────────────────────────


class TestUpdateDetection:
    def test_changed_articles_updated(self, tmp_raw_kb, tmp_path, monkeypatch):
        db_path = tmp_path / "knowledge.db"
        monkeypatch.setattr("ocd.ingest.WIKI_DB", db_path)
        knowledge_dir = tmp_path / "knowledge"

        path = tmp_raw_kb("concepts", "oauth", "---\ntitle: OAuth\n---\nOriginal.")
        ingest_raw(knowledge_dir=knowledge_dir, db_path=db_path)

        path.write_text("---\ntitle: OAuth v2\n---\nUpdated content.")

        result = ingest_raw(knowledge_dir=knowledge_dir, db_path=db_path)
        assert result.updated == 1

        db = sqlite3.connect(str(db_path))
        row = db.execute("SELECT title FROM articles").fetchone()
        db.close()
        assert row[0] == "OAuth v2"


# ── Ingestion log ────────────────────────────────────────────────────────────


class TestIngestionLog:
    def test_log_entries_written(self, tmp_raw_kb, tmp_path, monkeypatch):
        db_path = tmp_path / "knowledge.db"
        monkeypatch.setattr("ocd.ingest.WIKI_DB", db_path)

        tmp_raw_kb("concepts", "test", "---\ntitle: Test\n---\nBody.")

        ingest_raw(knowledge_dir=tmp_path / "knowledge", db_path=db_path)

        db = sqlite3.connect(str(db_path))
        rows = db.execute("SELECT action, status FROM ingestion_log").fetchall()
        db.close()
        assert len(rows) == 1
        assert rows[0] == ("insert", "ok")


# ── Dry run ─────────────────────────────────────────────────────────────────


class TestDryRun:
    def test_no_db_changes(self, tmp_raw_kb, tmp_path, monkeypatch):
        db_path = tmp_path / "knowledge.db"
        monkeypatch.setattr("ocd.ingest.WIKI_DB", db_path)

        tmp_raw_kb("concepts", "test", "---\ntitle: Test\n---\nBody.")

        result = ingest_raw(
            knowledge_dir=tmp_path / "knowledge",
            db_path=db_path,
            dry_run=True,
        )
        assert result.scanned == 1
        assert not db_path.exists()


# ── Force all ────────────────────────────────────────────────────────────────


class TestForceAll:
    def test_force_reingest(self, tmp_raw_kb, tmp_path, monkeypatch):
        db_path = tmp_path / "knowledge.db"
        monkeypatch.setattr("ocd.ingest.WIKI_DB", db_path)
        knowledge_dir = tmp_path / "knowledge"

        tmp_raw_kb("concepts", "test", "---\ntitle: Test\n---\nBody.")

        ingest_raw(knowledge_dir=knowledge_dir, db_path=db_path)
        result = ingest_raw(knowledge_dir=knowledge_dir, db_path=db_path, force_all=True)

        assert result.updated == 1
        assert result.skipped == 0


# ── Error handling ──────────────────────────────────────────────────────────


class TestErrorHandling:
    def test_unreadable_file_counted(self, tmp_path, monkeypatch):
        db_path = tmp_path / "knowledge.db"
        knowledge_dir = tmp_path / "knowledge"
        knowledge_dir.mkdir()
        monkeypatch.setattr("ocd.ingest.WIKI_DB", db_path)

        bad_file = knowledge_dir / "concepts" / "bad.md"
        bad_file.parent.mkdir(parents=True, exist_ok=True)
        bad_file.write_text("---\ntitle: Bad\n---\nContent.")
        bad_file.chmod(0o000)

        try:
            result = ingest_raw(knowledge_dir=knowledge_dir, db_path=db_path)
            assert result.errors >= 1
        finally:
            bad_file.chmod(0o644)


# ── TF-IDF rebuild ──────────────────────────────────────────────────────────


class TestTFIDFRebuild:
    def test_rebuild_called_after_ingest(self, tmp_raw_kb, tmp_path, monkeypatch):
        db_path = tmp_path / "knowledge.db"
        monkeypatch.setattr("ocd.ingest.WIKI_DB", db_path)

        # Mock build_kb_index_json to track calls (it's a lazy import in ingest.py)
        called: list[bool] = []

        def _mock_build() -> dict[str, object]:
            called.append(True)
            return {}

        monkeypatch.setattr("ocd.relevance.build_kb_index_json", _mock_build)

        tmp_raw_kb("concepts", "test", "---\ntitle: Test\n---\nBody.")

        ingest_raw(knowledge_dir=tmp_path / "knowledge", db_path=db_path)
        assert len(called) == 1


# ── DB fallback ──────────────────────────────────────────────────────────────


class TestDBFallback:
    def test_relevance_falls_back_to_flat_files(self, wiki_article, mock_config_paths):
        """When no knowledge.db exists, build_kb_index_json reads from flat files."""
        from ocd.relevance import build_kb_index_json

        wiki_article("concepts/test-art", "Test content here.")

        index = build_kb_index_json(use_db=True)
        assert len(index["articles"]) >= 1
        assert index["articles"][0]["title"] == "test-art"

    def test_relevance_reads_from_db(self, tmp_raw_kb, tmp_path, mock_config_paths, monkeypatch):
        """When knowledge.db exists, build_kb_index_json reads from it."""
        from ocd.relevance import build_kb_index_json

        db_path = tmp_path / "knowledge.db"
        monkeypatch.setattr("ocd.ingest.WIKI_DB", db_path)
        monkeypatch.setattr("ocd.relevance.WIKI_DB", db_path)

        tmp_raw_kb("concepts", "oauth", "---\ntitle: OAuth\n---\nOAuth content.")

        ingest_raw(knowledge_dir=tmp_path / "knowledge", db_path=db_path)

        index = build_kb_index_json(use_db=True)
        assert len(index["articles"]) >= 1
        assert index["articles"][0]["title"] == "OAuth"


# ── Knowledge status ─────────────────────────────────────────────────────────


class TestKbStatus:
    def test_synced_when_empty(self, tmp_path, monkeypatch):
        db_path = tmp_path / "knowledge.db"
        knowledge_dir = tmp_path / "knowledge"
        knowledge_dir.mkdir()
        monkeypatch.setattr("ocd.ingest.WIKI_DB", db_path)

        status = kb_status(knowledge_dir=knowledge_dir, db_path=db_path)
        assert status["synced"] is True
        assert status["db_count"] == 0
        assert status["disk_count"] == 0

    def test_synced_after_ingest(self, tmp_raw_kb, tmp_path, monkeypatch):
        db_path = tmp_path / "knowledge.db"
        monkeypatch.setattr("ocd.ingest.WIKI_DB", db_path)
        knowledge_dir = tmp_path / "knowledge"

        tmp_raw_kb("concepts", "test", "---\ntitle: Test\n---\nBody.")
        ingest_raw(knowledge_dir=knowledge_dir, db_path=db_path)

        status = kb_status(knowledge_dir=knowledge_dir, db_path=db_path)
        assert status["synced"] is True
        assert status["db_count"] == 1
        assert status["disk_count"] == 1

    def test_new_files_detected(self, tmp_raw_kb, tmp_path, monkeypatch):
        db_path = tmp_path / "knowledge.db"
        monkeypatch.setattr("ocd.ingest.WIKI_DB", db_path)
        knowledge_dir = tmp_path / "knowledge"

        # Ingest one article
        tmp_raw_kb("concepts", "existing", "---\ntitle: Existing\n---\nBody.")
        ingest_raw(knowledge_dir=knowledge_dir, db_path=db_path)

        # Add another article without ingesting
        tmp_raw_kb("concepts", "new-one", "---\ntitle: New\n---\nNew body.")

        status = kb_status(knowledge_dir=knowledge_dir, db_path=db_path)
        assert status["synced"] is False
        assert len(status["new"]) == 1
        assert "concepts/new-one.md" in status["new"]

    def test_orphaned_files_detected(self, tmp_raw_kb, tmp_path, monkeypatch):
        db_path = tmp_path / "knowledge.db"
        monkeypatch.setattr("ocd.ingest.WIKI_DB", db_path)
        knowledge_dir = tmp_path / "knowledge"

        path = tmp_raw_kb("concepts", "oauth", "---\ntitle: OAuth\n---\nBody.")
        ingest_raw(knowledge_dir=knowledge_dir, db_path=db_path)

        # Delete file from disk
        path.unlink()

        status = kb_status(knowledge_dir=knowledge_dir, db_path=db_path)
        assert status["synced"] is False
        assert len(status["orphaned"]) == 1
        assert "concepts/oauth.md" in status["orphaned"]

    def test_stale_files_detected(self, tmp_raw_kb, tmp_path, monkeypatch):
        db_path = tmp_path / "knowledge.db"
        monkeypatch.setattr("ocd.ingest.WIKI_DB", db_path)
        knowledge_dir = tmp_path / "knowledge"

        path = tmp_raw_kb("concepts", "oauth", "---\ntitle: OAuth\n---\nBody.")
        ingest_raw(knowledge_dir=knowledge_dir, db_path=db_path)

        # Touch file to change mtime
        os.utime(path, (time.time() + 100, time.time() + 100))

        status = kb_status(knowledge_dir=knowledge_dir, db_path=db_path)
        assert status["synced"] is False
        assert len(status["stale"]) == 1
        assert "concepts/oauth.md" in status["stale"]

    def test_no_db_reports_all_as_new(self, tmp_path, monkeypatch):
        db_path = tmp_path / "knowledge.db"
        knowledge_dir = tmp_path / "knowledge"
        knowledge_dir.mkdir()
        monkeypatch.setattr("ocd.ingest.WIKI_DB", db_path)

        (knowledge_dir / "concepts").mkdir()
        (knowledge_dir / "concepts" / "test.md").write_text("---\ntitle: Test\n---\nBody.")

        # No DB exists yet
        status = kb_status(knowledge_dir=knowledge_dir, db_path=db_path)
        assert status["synced"] is False
        assert len(status["new"]) == 1
        assert status["db_count"] == 0

    def test_last_ingest_timestamp(self, tmp_raw_kb, tmp_path, monkeypatch):
        db_path = tmp_path / "knowledge.db"
        monkeypatch.setattr("ocd.ingest.WIKI_DB", db_path)
        knowledge_dir = tmp_path / "knowledge"

        tmp_raw_kb("concepts", "test", "---\ntitle: Test\n---\nBody.")
        ingest_raw(knowledge_dir=knowledge_dir, db_path=db_path)

        status = kb_status(knowledge_dir=knowledge_dir, db_path=db_path)
        assert status["last_ingest"] is not None
