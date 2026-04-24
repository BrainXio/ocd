"""Tests for session_start — relevance-based context injection hook."""

import json

import pytest

from ocd.hooks import session_start


@pytest.fixture
def mock_session_start_paths(mock_config_paths, monkeypatch):
    """Patch session_start's module-level imports from config."""
    from ocd.config import MAX_CONTEXT_CHARS, MAX_RELEVANT_CONTEXT_CHARS

    monkeypatch.setattr(session_start, "MAX_RELEVANT_CONTEXT_CHARS", MAX_RELEVANT_CONTEXT_CHARS)
    monkeypatch.setattr(session_start, "MAX_CONTEXT_CHARS", MAX_CONTEXT_CHARS)
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


class TestAppSpecIntegration:
    """Tests that app spec context is injected into session-start output."""

    def test_app_spec_injected_when_present(self, mock_config_paths, monkeypatch, capsys):
        app_spec_path = mock_config_paths.parent / "app_spec.txt"
        app_spec_path.write_text("Build a CLI tool for task management", encoding="utf-8")
        monkeypatch.setattr("ocd.session.app_spec.APP_SPEC_FILE", app_spec_path)
        session_start.main()
        output = capsys.readouterr().out
        result = json.loads(output)
        context = result["hookSpecificOutput"]["additionalContext"]
        assert "## App Spec" in context
        assert "task management" in context

    def test_app_spec_absent_when_no_file(self, mock_config_paths, monkeypatch, capsys):
        monkeypatch.setattr(
            "ocd.session.app_spec.APP_SPEC_FILE",
            mock_config_paths / "nonexistent" / "app_spec.txt",
        )
        session_start.main()
        output = capsys.readouterr().out
        result = json.loads(output)
        context = result["hookSpecificOutput"]["additionalContext"]
        assert "## App Spec" not in context

    def test_total_context_within_hard_cap(self, mock_config_paths, monkeypatch, capsys):
        app_spec_path = mock_config_paths.parent / "app_spec.txt"
        app_spec_path.write_text("x" * 50000, encoding="utf-8")
        monkeypatch.setattr("ocd.session.app_spec.APP_SPEC_FILE", app_spec_path)
        session_start.main()
        output = capsys.readouterr().out
        result = json.loads(output)
        context = result["hookSpecificOutput"]["additionalContext"]
        from ocd.config import MAX_CONTEXT_CHARS

        assert len(context) <= MAX_CONTEXT_CHARS + len("\n\n...(truncated)")
