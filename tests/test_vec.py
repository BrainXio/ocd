"""Tests for the semantic vector memory module."""

import sqlite3

import pytest

from ocd.config import VEC_DIMENSIONS, VEC_EMBEDDING_MODEL
from ocd.kb.vec import (
    ensure_vec_schema,
    insert_vectors,
    is_vec_available,
    search_vectors,
    vec_status,
)

# Mark all tests that need vec extras
requires_vec = pytest.mark.skipif(
    not is_vec_available(),
    reason="vec extras not installed (install with: uv sync --extra vec)",
)


# ── Availability check ────────────────────────────────────────────────────────


class TestIsVecAvailable:
    def test_returns_bool(self):
        result = is_vec_available()
        assert isinstance(result, bool)


# ── Schema creation ──────────────────────────────────────────────────────────


class TestEnsureVecSchema:
    @requires_vec
    def test_creates_vec_tables(self, tmp_path):
        db_path = tmp_path / "test.db"
        db = sqlite3.connect(str(db_path))
        result = ensure_vec_schema(db)
        assert result is True

        # Check vec_metadata table exists
        tables = {
            row[0]
            for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        assert "vec_metadata" in tables
        db.close()

    @requires_vec
    def test_idempotent_schema(self, tmp_path):
        db_path = tmp_path / "test.db"
        db = sqlite3.connect(str(db_path))
        ensure_vec_schema(db)
        result = ensure_vec_schema(db)
        assert result is True
        db.close()

    def test_returns_false_when_unavailable(self, monkeypatch):
        monkeypatch.setattr("ocd.kb.vec.is_vec_available", lambda: False)
        db = sqlite3.connect(":memory:")
        result = ensure_vec_schema(db)
        assert result is False
        db.close()


# ── Embedding ────────────────────────────────────────────────────────────────


class TestEmbedTexts:
    @requires_vec
    def test_embeds_single_text(self):
        from ocd.kb.vec import embed_texts

        result = embed_texts(["hello world"])
        assert result is not None
        assert len(result) == 1
        assert len(result[0]) == VEC_DIMENSIONS

    @requires_vec
    def test_embeds_multiple_texts(self):
        from ocd.kb.vec import embed_texts

        result = embed_texts(["hello", "world"])
        assert result is not None
        assert len(result) == 2

    def test_returns_none_when_unavailable(self, monkeypatch):
        monkeypatch.setattr("ocd.kb.vec.is_vec_available", lambda: False)
        from ocd.kb.vec import embed_texts

        # embed_texts calls _get_model which returns None
        # when fastembed is not available
        result = embed_texts(["test"])
        assert result is None


# ── Insert vectors ────────────────────────────────────────────────────────────


class TestInsertVectors:
    @requires_vec
    def test_inserts_vectors_and_metadata(self, tmp_path, monkeypatch):
        db_path = tmp_path / "test.db"
        db = sqlite3.connect(str(db_path))
        ensure_vec_schema(db)

        # Create articles table for referential integrity
        db.execute(
            "CREATE TABLE IF NOT EXISTS articles (path TEXT PRIMARY KEY, title TEXT, body TEXT)"
        )
        db.execute("INSERT INTO articles VALUES ('concepts/test', 'Test', 'Test body')")
        db.commit()

        count = insert_vectors(db, [("concepts/test", "Test body content")])
        assert count == 1

        # Check metadata
        meta = db.execute("SELECT article_path, model_name, dims FROM vec_metadata").fetchone()
        assert meta is not None
        assert meta[0] == "concepts/test"
        assert meta[1] == VEC_EMBEDDING_MODEL
        assert meta[2] == VEC_DIMENSIONS
        db.close()

    @requires_vec
    def test_deduplication(self, tmp_path, monkeypatch):
        db_path = tmp_path / "test.db"
        db = sqlite3.connect(str(db_path))
        ensure_vec_schema(db)

        count1 = insert_vectors(db, [("concepts/test", "First content")])
        count2 = insert_vectors(db, [("concepts/test", "Updated content")])

        # Second insert replaces the first (same path)
        assert count1 == 1
        assert count2 == 1

        meta_count = db.execute("SELECT COUNT(*) FROM vec_metadata").fetchone()[0]
        assert meta_count == 1
        db.close()

    def test_skips_when_vec_unavailable(self, monkeypatch):
        monkeypatch.setattr("ocd.kb.vec.is_vec_available", lambda: False)
        db = sqlite3.connect(":memory:")
        result = insert_vectors(db, [("test", "content")])
        assert result == 0
        db.close()


# ── Search ───────────────────────────────────────────────────────────────────


class TestSearchVectors:
    @requires_vec
    def test_search_returns_results(self, tmp_path, monkeypatch):
        db_path = tmp_path / "test.db"
        db = sqlite3.connect(str(db_path))
        ensure_vec_schema(db)

        # Insert test vectors
        insert_vectors(
            db,
            [
                ("concepts/auth", "authentication and authorization patterns"),
                ("concepts/testing", "unit testing and integration testing"),
                ("concepts/perf", "performance optimization and caching"),
            ],
        )

        results = search_vectors(db, "how to test code", top_k=2)
        assert results is not None
        assert len(results) <= 2
        db.close()

    @requires_vec
    def test_search_returns_none_when_unavailable(self, monkeypatch):
        monkeypatch.setattr("ocd.kb.vec.is_vec_available", lambda: False)
        db = sqlite3.connect(":memory:")
        result = search_vectors(db, "test query")
        assert result is None
        db.close()


# ── Status ───────────────────────────────────────────────────────────────────


class TestVecStatus:
    def test_status_without_vec(self, monkeypatch):
        monkeypatch.setattr("ocd.kb.vec.is_vec_available", lambda: False)
        fake_path = __import__("pathlib").Path("/tmp/fake.db")
        status = vec_status(fake_path)
        assert status["available"] is False

    @requires_vec
    def test_status_with_db(self, tmp_path, monkeypatch):
        db_path = tmp_path / "knowledge.db"
        db = sqlite3.connect(str(db_path))
        ensure_vec_schema(db)
        insert_vectors(db, [("test", "test content")])
        db.close()
        monkeypatch.setattr("ocd.kb.vec.WIKI_DB", db_path)
        status = vec_status(db_path)
        assert status["available"] is True
        assert status["db_exists"] is True
        assert status["embedding_count"] == 1
        assert status["model"] == VEC_EMBEDDING_MODEL


# ── Rebuild ──────────────────────────────────────────────────────────────────


class TestRebuildVectors:
    @requires_vec
    def test_rebuild_creates_embeddings(self, tmp_path, monkeypatch):
        from ocd.kb.ingest import ingest_raw

        db_path = tmp_path / "knowledge.db"
        knowledge_dir = tmp_path / "knowledge"
        knowledge_dir.mkdir(parents=True)
        (knowledge_dir / "concepts").mkdir()
        (knowledge_dir / "concepts" / "test.md").write_text(
            "---\ntitle: Test\n---\nTest body content."
        )
        monkeypatch.setattr("ocd.kb.ingest.WIKI_DB", db_path)

        # First, ingest articles
        ingest_raw(knowledge_dir=knowledge_dir, db_path=db_path)

        # Now rebuild vectors
        from ocd.kb.vec import rebuild_vectors

        count = rebuild_vectors(db_path)
        assert count == 1

        db = sqlite3.connect(str(db_path))
        meta = db.execute("SELECT COUNT(*) FROM vec_metadata").fetchone()[0]
        db.close()
        assert meta == 1

    @requires_vec
    def test_rebuild_model_change_requires_force(self, tmp_path, monkeypatch):
        from ocd.kb.vec import rebuild_vectors

        db_path = tmp_path / "knowledge.db"
        db = sqlite3.connect(str(db_path))
        ensure_vec_schema(db)
        insert_vectors(db, [("test", "content")])
        db.close()

        # Simulate model change
        monkeypatch.setattr("ocd.kb.vec.VEC_EMBEDDING_MODEL", "different-model")

        with pytest.raises(ValueError, match="Embedding model changed"):
            rebuild_vectors(db_path)

        # Force should succeed
        count = rebuild_vectors(db_path, force=True)
        # It may return 0 if no articles table exists, but shouldn't raise
        assert isinstance(count, int)
