"""Tests for the raw knowledge ingestion pipeline."""

import json
import sqlite3

from ocd.ingest import (
    _file_hash,
    _parse_list_field,
    _score_article,
    _split_frontmatter,
    ingest_raw,
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
        db_path = tmp_path / "knowledge" / "ocd.db"
        raw_dir = tmp_path / "knowledge" / "raw"
        raw_dir.mkdir(parents=True)
        monkeypatch.setattr("ocd.ingest.RAW_DIR", raw_dir)
        monkeypatch.setattr("ocd.ingest.OCD_DB", db_path)

        # Create a file so the DB is actually created (empty scan returns early)
        (raw_dir / "concepts").mkdir()
        (raw_dir / "concepts" / "test.md").write_text("---\ntitle: Test\n---\nBody.")

        result = ingest_raw(raw_dir=raw_dir, db_path=db_path)
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


# ── Ingest articles ─────────────────────────────────────────────────────────


class TestIngestArticles:
    def test_insert_articles(self, tmp_raw_kb, tmp_path, monkeypatch):
        db_path = tmp_path / "knowledge" / "ocd.db"
        monkeypatch.setattr("ocd.ingest.OCD_DB", db_path)

        tmp_raw_kb("concepts", "oauth", "---\ntitle: OAuth\n---\nOAuth content.")
        tmp_raw_kb("connections", "auth-flow", "---\ntitle: Auth Flow\n---\nFlow content.")

        result = ingest_raw(raw_dir=tmp_path / "knowledge" / "raw", db_path=db_path)
        assert result.scanned == 2
        assert result.inserted == 2
        assert result.skipped == 0

    def test_article_metadata_stored(self, tmp_raw_kb, tmp_path, monkeypatch):
        db_path = tmp_path / "knowledge" / "ocd.db"
        monkeypatch.setattr("ocd.ingest.OCD_DB", db_path)

        tmp_raw_kb(
            "concepts",
            "oauth",
            "---\ntitle: OAuth Redirect\ntags: [auth, security]\n---\nContent here.",
        )

        ingest_raw(raw_dir=tmp_path / "knowledge" / "raw", db_path=db_path)

        db = sqlite3.connect(str(db_path))
        row = db.execute("SELECT path, title, tags, score FROM articles").fetchone()
        db.close()
        assert row is not None
        assert row[0] == "concepts/oauth.md"
        assert row[1] == "OAuth Redirect"
        assert json.loads(row[2]) == ["auth", "security"]
        assert row[3] > 0


# ── Deduplication ───────────────────────────────────────────────────────────


class TestDeduplication:
    def test_unchanged_articles_skipped(self, tmp_raw_kb, tmp_path, monkeypatch):
        db_path = tmp_path / "knowledge" / "ocd.db"
        monkeypatch.setattr("ocd.ingest.OCD_DB", db_path)
        raw = tmp_path / "knowledge" / "raw"

        tmp_raw_kb("concepts", "oauth", "---\ntitle: OAuth\n---\nSame content.")

        result1 = ingest_raw(raw_dir=raw, db_path=db_path)
        assert result1.inserted == 1

        result2 = ingest_raw(raw_dir=raw, db_path=db_path)
        assert result2.skipped == 1
        assert result2.inserted == 0


# ── Update detection ────────────────────────────────────────────────────────


class TestUpdateDetection:
    def test_changed_articles_updated(self, tmp_raw_kb, tmp_path, monkeypatch):
        db_path = tmp_path / "knowledge" / "ocd.db"
        monkeypatch.setattr("ocd.ingest.OCD_DB", db_path)
        raw = tmp_path / "knowledge" / "raw"

        path = tmp_raw_kb("concepts", "oauth", "---\ntitle: OAuth\n---\nOriginal.")
        ingest_raw(raw_dir=raw, db_path=db_path)

        path.write_text("---\ntitle: OAuth v2\n---\nUpdated content.")

        result = ingest_raw(raw_dir=raw, db_path=db_path)
        assert result.updated == 1

        db = sqlite3.connect(str(db_path))
        row = db.execute("SELECT title FROM articles").fetchone()
        db.close()
        assert row[0] == "OAuth v2"


# ── Ingestion log ───────────────────────────────────────────────────────────


class TestIngestionLog:
    def test_log_entries_written(self, tmp_raw_kb, tmp_path, monkeypatch):
        db_path = tmp_path / "knowledge" / "ocd.db"
        monkeypatch.setattr("ocd.ingest.OCD_DB", db_path)

        tmp_raw_kb("concepts", "test", "---\ntitle: Test\n---\nBody.")

        ingest_raw(raw_dir=tmp_path / "knowledge" / "raw", db_path=db_path)

        db = sqlite3.connect(str(db_path))
        rows = db.execute("SELECT action, status FROM ingestion_log").fetchall()
        db.close()
        assert len(rows) == 1
        assert rows[0] == ("insert", "ok")


# ── Dry run ─────────────────────────────────────────────────────────────────


class TestDryRun:
    def test_no_db_changes(self, tmp_raw_kb, tmp_path, monkeypatch):
        db_path = tmp_path / "knowledge" / "ocd.db"
        monkeypatch.setattr("ocd.ingest.OCD_DB", db_path)

        tmp_raw_kb("concepts", "test", "---\ntitle: Test\n---\nBody.")

        result = ingest_raw(
            raw_dir=tmp_path / "knowledge" / "raw",
            db_path=db_path,
            dry_run=True,
        )
        assert result.scanned == 1
        assert not db_path.exists()


# ── Force all ────────────────────────────────────────────────────────────────


class TestForceAll:
    def test_force_reingest(self, tmp_raw_kb, tmp_path, monkeypatch):
        db_path = tmp_path / "knowledge" / "ocd.db"
        monkeypatch.setattr("ocd.ingest.OCD_DB", db_path)
        raw = tmp_path / "knowledge" / "raw"

        tmp_raw_kb("concepts", "test", "---\ntitle: Test\n---\nBody.")

        ingest_raw(raw_dir=raw, db_path=db_path)
        result = ingest_raw(raw_dir=raw, db_path=db_path, force_all=True)

        assert result.updated == 1
        assert result.skipped == 0


# ── Error handling ──────────────────────────────────────────────────────────


class TestErrorHandling:
    def test_unreadable_file_counted(self, tmp_path, monkeypatch):
        db_path = tmp_path / "knowledge" / "ocd.db"
        raw_dir = tmp_path / "knowledge" / "raw"
        raw_dir.mkdir(parents=True)
        monkeypatch.setattr("ocd.ingest.OCD_DB", db_path)

        bad_file = raw_dir / "concepts" / "bad.md"
        bad_file.parent.mkdir(parents=True, exist_ok=True)
        bad_file.write_text("---\ntitle: Bad\n---\nContent.")
        bad_file.chmod(0o000)

        try:
            result = ingest_raw(raw_dir=raw_dir, db_path=db_path)
            assert result.errors >= 1
        finally:
            bad_file.chmod(0o644)


# ── TF-IDF rebuild ──────────────────────────────────────────────────────────


class TestTFIDFRebuild:
    def test_rebuild_called_after_ingest(self, tmp_raw_kb, tmp_path, monkeypatch):
        db_path = tmp_path / "knowledge" / "ocd.db"
        monkeypatch.setattr("ocd.ingest.OCD_DB", db_path)

        # Mock build_kb_index_json to track calls (it's a lazy import in ingest.py)
        called: list[bool] = []

        def _mock_build() -> dict[str, object]:
            called.append(True)
            return {}

        monkeypatch.setattr("ocd.relevance.build_kb_index_json", _mock_build)

        tmp_raw_kb("concepts", "test", "---\ntitle: Test\n---\nBody.")

        ingest_raw(raw_dir=tmp_path / "knowledge" / "raw", db_path=db_path)
        assert len(called) == 1


# ── Backward compatibility ──────────────────────────────────────────────────


class TestBackwardCompat:
    def test_relevance_falls_back_to_flat_files(self, wiki_article, mock_config_paths):
        """When no ocd.db exists, build_kb_index_json reads from flat files."""
        from ocd.relevance import build_kb_index_json

        wiki_article("concepts/test-art", "Test content here.")

        index = build_kb_index_json(use_db=True)
        assert len(index["articles"]) >= 1
        assert index["articles"][0]["title"] == "test-art"

    def test_relevance_reads_from_db(self, tmp_raw_kb, tmp_path, mock_config_paths, monkeypatch):
        """When ocd.db exists, build_kb_index_json reads from it."""
        from ocd.relevance import build_kb_index_json

        db_path = tmp_path / "knowledge" / "ocd.db"
        monkeypatch.setattr("ocd.ingest.OCD_DB", db_path)
        monkeypatch.setattr("ocd.relevance.OCD_DB", db_path)

        tmp_raw_kb("concepts", "oauth", "---\ntitle: OAuth\n---\nOAuth content.")

        ingest_raw(raw_dir=tmp_path / "knowledge" / "raw", db_path=db_path)

        index = build_kb_index_json(use_db=True)
        assert len(index["articles"]) >= 1
        assert index["articles"][0]["title"] == "OAuth"
