"""Tests for session_start — relevance-based context injection hook."""

import json

import pytest

from ocd.hooks import session_start


@pytest.fixture
def mock_session_start_paths(mock_config_paths, monkeypatch):
    """Patch session_start's module-level imports from config."""
    from ocd.config import MAX_RELEVANT_CONTEXT_CHARS

    monkeypatch.setattr(session_start, "MAX_RELEVANT_CONTEXT_CHARS", MAX_RELEVANT_CONTEXT_CHARS)
    return mock_config_paths


class TestMain:
    def test_outputs_valid_json(self, mock_config_paths, wiki_article, capsys):
        wiki_article("concepts/test-session", "Content for session start test.")
        session_start.main()
        output = capsys.readouterr().out
        result = json.loads(output)
        assert "hookSpecificOutput" in result
        assert result["hookSpecificOutput"]["hookEventName"] == "SessionStart"
        assert "additionalContext" in result["hookSpecificOutput"]

    def test_context_contains_today(self, mock_config_paths, wiki_article, capsys):
        wiki_article("concepts/today-test", "Testing today date in context.")
        session_start.main()
        output = capsys.readouterr().out
        result = json.loads(output)
        context = result["hookSpecificOutput"]["additionalContext"]
        assert "## Today" in context

    def test_context_contains_health_card(self, mock_config_paths, wiki_article, capsys):
        wiki_article("concepts/health-test", "Health card test content.")
        session_start.main()
        output = capsys.readouterr().out
        result = json.loads(output)
        context = result["hookSpecificOutput"]["additionalContext"]
        assert "KB:" in context

    def test_context_size_within_limit(self, mock_config_paths, wiki_article, capsys):
        wiki_article("concepts/size-test", "Content for size limit test.")
        session_start.main()
        output = capsys.readouterr().out
        result = json.loads(output)
        context = result["hookSpecificOutput"]["additionalContext"]
        assert len(context) <= 8200  # MAX_RELEVANT_CONTEXT_CHARS + small buffer

    def test_empty_kb_still_works(self, mock_config_paths, capsys):
        session_start.main()
        output = capsys.readouterr().out
        result = json.loads(output)
        context = result["hookSpecificOutput"]["additionalContext"]
        assert "## Today" in context
