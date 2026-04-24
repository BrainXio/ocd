"""Tests for relevance — TF-IDF scoring engine and KB injection."""

import json
from typing import Any

from ocd.config import KB_INDEX_JSON
from ocd.kb.relevance import (
    _cosine_similarity,
    _extract_details,
    _extract_key_points,
    _idf,
    _parse_frontmatter,
    _term_freq,
    _tfidf_vector,
    build_health_card,
    build_kb_index_json,
    build_relevant_context,
    is_kb_index_stale,
    load_articles_for_injection,
    load_kb_index,
    save_kb_index,
    score_articles,
    tokenize,
)

# ── Tokenization tests ───────────────────────────────────────────────────


class TestTokenize:
    def test_basic(self):
        tokens = tokenize("Hello world of code review")
        assert "hello" in tokens
        assert "world" in tokens
        assert "code" in tokens
        assert "review" in tokens

    def test_filters_stop_words(self):
        tokens = tokenize("The quick brown fox jumps over the lazy dog")
        assert "the" not in tokens
        assert "over" not in tokens

    def test_short_words_filtered(self):
        tokens = tokenize("a b c de ef")
        assert "de" in tokens
        assert "ef" in tokens
        assert len([t for t in tokens if len(t) < 2]) == 0

    def test_lowercase(self):
        tokens = tokenize("Python LINTER Format")
        assert "python" in tokens
        assert "linter" in tokens
        assert "format" in tokens

    def test_empty(self):
        assert tokenize("") == []

    def test_numbers_excluded(self):
        tokens = tokenize("test123 abc456 def")
        assert "test" not in tokens  # test123 has no word boundary split
        assert "def" in tokens


# ── TF-IDF tests ─────────────────────────────────────────────────────────


class TestTermFreq:
    def test_basic(self):
        tf = _term_freq(["hello", "hello", "world"])
        assert abs(tf["hello"] - 2 / 3) < 0.01
        assert abs(tf["world"] - 1 / 3) < 0.01

    def test_empty(self):
        assert _term_freq([]) == {}


class TestIdf:
    def test_basic(self):
        docs = [{"hello": 0.5, "world": 0.5}, {"hello": 1.0}]
        idf = _idf(docs)
        # "hello" appears in both docs, "world" only in one
        assert idf["world"] > idf["hello"]

    def test_empty(self):
        assert _idf([]) == {}


class TestCosineSimilarity:
    def test_identical(self):
        vec = {"a": 1.0, "b": 2.0}
        assert abs(_cosine_similarity(vec, vec) - 1.0) < 0.001

    def test_orthogonal(self):
        a = {"a": 1.0}
        b = {"b": 1.0}
        assert _cosine_similarity(a, b) == 0.0

    def test_partial_overlap(self):
        a = {"a": 1.0, "b": 1.0}
        b = {"a": 1.0, "c": 1.0}
        score = _cosine_similarity(a, b)
        assert 0 < score < 1.0

    def test_empty_vectors(self):
        assert _cosine_similarity({}, {}) == 0.0


# ── Frontmatter parsing tests ────────────────────────────────────────────


class TestParseFrontmatter:
    def test_basic(self):
        content = "---\ntitle: Test Article\ntags: [a, b]\nupdated: 2026-04-21\n---\nBody"
        fm = _parse_frontmatter(content)
        assert fm["title"] == "Test Article"
        assert fm["tags"] == ["a", "b"]
        assert fm["updated"] == "2026-04-21"

    def test_no_frontmatter(self):
        assert _parse_frontmatter("Just body text") == {}

    def test_aliases(self):
        content = "---\ntitle: My Article\naliases: [one, two]\n---\nBody"
        fm = _parse_frontmatter(content)
        assert fm["aliases"] == ["one", "two"]


class TestExtractKeyPoints:
    def test_basic(self):
        content = (
            "---\n---\n## Key Points\n\n- Point one\n- Point two\n\n## Details\n\nDetails here."
        )
        result = _extract_key_points(content)
        assert "Point one" in result
        assert "Point two" in result

    def test_missing(self):
        assert _extract_key_points("---\n---\n## Details\n\nNo key points.") == ""


class TestExtractDetails:
    def test_basic(self):
        content = "---\n---\n## Details\n\nFirst paragraph.\n\nSecond paragraph.\n\n## Related"
        result = _extract_details(content)
        assert "First paragraph" in result

    def test_missing(self):
        assert _extract_details("---\n---\nJust text.") == ""


# ── KB index building tests ──────────────────────────────────────────────


class TestBuildKbIndexJson:
    def test_builds_index_from_articles(self, mock_config_paths, wiki_article, monkeypatch):
        wiki_article("concepts/test-article", "Test content about formatting and linting.")
        wiki_article("concepts/other-article", "Other content about security and Docker.")

        index = build_kb_index_json()
        assert index["version"] == 1
        assert index["article_count"] == 2
        assert "articles" in index
        assert len(index["articles"]) == 2

    def test_empty_kb(self, mock_config_paths):
        index = build_kb_index_json()
        assert index["article_count"] == 0
        assert index["articles"] == []

    def test_index_has_tfidf_vectors(self, mock_config_paths, wiki_article):
        wiki_article("concepts/tfidf-test", "TF-IDF testing content for vector computation.")
        index = build_kb_index_json()
        article = index["articles"][0]
        assert "tfidf" in article
        assert isinstance(article["tfidf"], dict)


class TestSaveLoadKbIndex:
    def test_round_trip(self, mock_config_paths):
        index = {
            "version": 1,
            "built_at": "2026-04-21T00:00:00",
            "article_count": 1,
            "connection_count": 0,
            "articles": [{"path": "concepts/test", "title": "Test"}],
            "idf": {},
        }
        path = save_kb_index(index)
        assert path.exists()

        loaded = load_kb_index()
        assert loaded is not None
        assert loaded["article_count"] == 1
        assert loaded["articles"][0]["title"] == "Test"

    def test_load_missing(self, mock_config_paths):
        # Ensure no index file exists
        if KB_INDEX_JSON.exists():
            KB_INDEX_JSON.unlink()
        assert load_kb_index() is None


class TestIsKbIndexStale:
    def test_stale_when_missing(self, mock_config_paths):
        assert is_kb_index_stale(None) is True

    def test_not_stale_when_current(self, mock_config_paths, wiki_article):
        wiki_article("concepts/stale-test", "Content for stale check.")
        index = build_kb_index_json()
        save_kb_index(index)
        assert is_kb_index_stale(index) is False

    def test_stale_when_article_changed(self, mock_config_paths, wiki_article):
        path = wiki_article("concepts/changed", "Original content.")
        index = build_kb_index_json()
        save_kb_index(index)
        # Modify the article
        path.write_text("---\ntitle: Changed\n---\nNew content.", encoding="utf-8")
        assert is_kb_index_stale(index) is True


# ── Scoring tests ────────────────────────────────────────────────────────


class TestScoreArticles:
    def _make_index(self, articles: list[dict[str, str]]) -> dict[str, Any]:
        """Build a minimal index for testing scoring."""
        all_tfs: list[dict[str, float]] = []
        article_entries: list[dict[str, Any]] = []
        idf_data: dict[str, float] = {}

        for a in articles:
            tokens = tokenize(a["content"])
            tf = _term_freq(tokens)
            all_tfs.append(tf)
            article_entries.append(
                {
                    "path": a["path"],
                    "title": a.get("title", ""),
                    "summary": a.get("summary", ""),
                    "tags": a.get("tags", []),
                    "aliases": a.get("aliases", []),
                    "updated": a.get("updated", "2026-01-01"),
                    "tfidf": {},
                    "hash": "abc123",
                }
            )

        idf_data = _idf(all_tfs)
        for i, entry in enumerate(article_entries):
            entry["tfidf"] = _tfidf_vector(all_tfs[i], idf_data)

        return {
            "version": 1,
            "built_at": "2026-04-21T00:00:00",
            "article_count": len(articles),
            "connection_count": 0,
            "articles": article_entries,
            "idf": idf_data,
        }

    def test_relevant_article_scores_highest(self):
        index = self._make_index(
            [
                {
                    "path": "concepts/formatting",
                    "content": "Code formatting with ruff and mdformat",
                    "title": "Formatting",
                    "summary": "Code formatting tools",
                    "updated": "2026-04-20",
                },
                {
                    "path": "concepts/security",
                    "content": "Security scanning with semgrep and trivy",
                    "title": "Security",
                    "summary": "Security scanning tools",
                    "updated": "2026-04-19",
                },
            ]
        )

        results = score_articles("format code with ruff", index, top_k=2)
        assert len(results) >= 1
        assert results[0]["path"] == "concepts/formatting"

    def test_fallback_when_no_query(self):
        index = self._make_index(
            [
                {
                    "path": "concepts/recent",
                    "content": "Recent article content",
                    "title": "Recent",
                    "summary": "Most recent",
                    "updated": "2026-04-21",
                },
                {
                    "path": "concepts/older",
                    "content": "Older article content",
                    "title": "Older",
                    "summary": "Older article",
                    "updated": "2026-04-01",
                },
            ]
        )

        results = score_articles("", index, top_k=2)
        assert len(results) == 2
        # Fallback returns most recently updated first
        assert results[0]["path"] == "concepts/recent"

    def test_fallback_when_score_below_threshold(self):
        index = self._make_index(
            [
                {
                    "path": "concepts/docker",
                    "content": "Docker container builds",
                    "title": "Docker",
                    "summary": "Container images",
                    "updated": "2026-04-20",
                },
            ]
        )

        # Completely unrelated query
        results = score_articles("quantum physics astronomy", index, top_k=1)
        # Should fall back to recent since score is below threshold
        assert len(results) >= 1
        assert results[0]["path"] == "concepts/docker"


# ── Health card tests ────────────────────────────────────────────────────


class TestBuildHealthCard:
    def test_basic(self, mock_config_paths):
        index = {
            "article_count": 55,
            "connection_count": 12,
            "built_at": "2026-04-21T10:00:00",
        }
        card = build_health_card(index)
        assert "55 articles" in card
        assert "12 connections" in card
        assert "2026-04-21" in card

    def test_with_lint_warnings(self, mock_config_paths, state_file):
        state_file.write_text(
            json.dumps(
                {
                    "ingested": {},
                    "query_count": 0,
                    "last_lint": {"warning_count": 3},
                    "total_cost": 0.0,
                }
            )
        )
        index = {
            "article_count": 10,
            "connection_count": 2,
            "built_at": "2026-04-21T10:00:00",
        }
        card = build_health_card(index)
        assert "3 lint warnings" in card


# ── Article loading tests ───────────────────────────────────────────────


class TestLoadArticlesForInjection:
    def test_loads_articles(self, mock_config_paths, wiki_article):
        wiki_article(
            "concepts/test-load",
            "Content for loading test article about formatting.",
        )

        scored = [
            {
                "path": "concepts/test-load",
                "title": "Test Load",
                "summary": "Test summary",
                "score": 0.85,
            }
        ]

        result = load_articles_for_injection(scored, max_chars=5000)
        assert "test-load" in result
        assert "formatting" in result

    def test_truncates_to_max_chars(self, mock_config_paths, wiki_article):
        wiki_article(
            "concepts/long-article",
            "Very long content. " * 500,
        )

        scored = [
            {
                "path": "concepts/long-article",
                "title": "Long",
                "summary": "",
                "score": 0.9,
            }
        ]

        result = load_articles_for_injection(scored, max_chars=200)
        assert len(result) <= 210  # 200 + truncation marker


# ── Integration: build_relevant_context ──────────────────────────────────


class TestBuildRelevantContext:
    def test_builds_context_without_query(self, mock_config_paths, wiki_article):
        wiki_article(
            "concepts/context-test",
            "Article content for context building test.",
        )

        context = build_relevant_context(query="", max_chars=8000)
        assert "## Today" in context
        assert "KB:" in context
        assert len(context) <= 8200  # 8000 + small buffer for truncation marker

    def test_empty_kb(self, mock_config_paths):
        context = build_relevant_context(query="", max_chars=8000)
        assert "## Today" in context
