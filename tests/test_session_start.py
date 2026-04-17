"""Tests for session_start — context injection hook."""

import json

import pytest

from ocd.hooks import session_start


@pytest.fixture
def mock_session_start_paths(mock_config_paths, monkeypatch):
    """Patch session_start's module-level imports from config."""
    monkeypatch.setattr(session_start, "DAILY_DIR", mock_config_paths / "daily")
    monkeypatch.setattr(session_start, "INDEX_FILE", mock_config_paths / "knowledge" / "index.md")
    return mock_config_paths


class TestGetRecentLog:
    def test_todays_log_exists(self, mock_session_start_paths, daily_log):
        from datetime import UTC, datetime

        today = datetime.now(UTC).astimezone().strftime("%Y-%m-%d")
        daily_log(today, "# Today's log\nLine 1\nLine 2")
        result = session_start.get_recent_log()
        assert "Today's log" in result

    def test_yesterdays_log_fallback(self, mock_session_start_paths, daily_log):
        from datetime import UTC, datetime, timedelta

        today = datetime.now(UTC).astimezone()
        yesterday = (today - timedelta(days=1)).strftime("%Y-%m-%d")
        daily_log(yesterday, "# Yesterday's log\nContent here")
        result = session_start.get_recent_log()
        assert "Yesterday" in result or "Content here" in result

    def test_no_log_available(self, mock_session_start_paths):
        result = session_start.get_recent_log()
        assert result == "(no recent daily log)"


class TestBuildContext:
    def test_assembles_all_parts(self, mock_session_start_paths, daily_log):
        from datetime import UTC, datetime

        today = datetime.now(UTC).astimezone().strftime("%Y-%m-%d")
        daily_log(today, "Log content here")
        context = session_start.build_context()
        assert "## Today" in context
        assert "## Knowledge Base Index" in context
        assert "## Recent Daily Log" in context

    def test_truncation(self, mock_session_start_paths, daily_log, monkeypatch):
        """Context exceeding MAX_CONTEXT_CHARS should be truncated."""
        monkeypatch.setattr(session_start, "MAX_CONTEXT_CHARS", 100)
        from datetime import UTC, datetime

        today = datetime.now(UTC).astimezone().strftime("%Y-%m-%d")
        daily_log(today, "x" * 500)
        context = session_start.build_context()
        assert len(context) <= 200


class TestMain:
    def test_outputs_valid_json(self, mock_session_start_paths, daily_log, capsys):
        from datetime import UTC, datetime

        today = datetime.now(UTC).astimezone().strftime("%Y-%m-%d")
        daily_log(today, "Log entry")
        session_start.main()
        output = capsys.readouterr().out
        result = json.loads(output)
        assert "hookSpecificOutput" in result
        assert result["hookSpecificOutput"]["hookEventName"] == "SessionStart"
        assert "additionalContext" in result["hookSpecificOutput"]
