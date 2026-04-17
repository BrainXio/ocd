"""Tests for flush.py — memory flush agent."""

import json
import os
from unittest.mock import MagicMock

import pytest

# Remove recursion guard env var before import
os.environ.pop("CLAUDE_INVOKED_BY", None)

import flush


@pytest.fixture
def mock_flush_paths(mock_config_paths, monkeypatch):
    """Patch flush's module-level imports from config."""
    monkeypatch.setattr(flush, "DAILY_DIR", mock_config_paths / "daily")
    monkeypatch.setattr(flush, "STATE_DIR", mock_config_paths / ".state")
    monkeypatch.setattr(flush, "FLUSH_STATE_FILE", mock_config_paths / ".state" / "last-flush.json")
    monkeypatch.setattr(flush, "FLUSH_LOG_FILE", mock_config_paths / ".state" / "flush.log")
    monkeypatch.setattr(flush, "STATE_DIR", mock_config_paths / ".state")
    return mock_config_paths


class TestLoadFlushState:
    def test_missing_file_returns_empty(self, mock_flush_paths):
        state = flush.load_flush_state()
        assert state == {}

    def test_existing_file_returns_content(self, mock_flush_paths):
        import config

        config.FLUSH_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        config.FLUSH_STATE_FILE.write_text(json.dumps({"session_id": "abc", "timestamp": 1234.5}))
        state = flush.load_flush_state()
        assert state["session_id"] == "abc"

    def test_corrupt_json_returns_empty(self, mock_flush_paths):
        import config

        config.FLUSH_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        config.FLUSH_STATE_FILE.write_text("{bad json")
        state = flush.load_flush_state()
        assert state == {}


class TestSaveFlushState:
    def test_writes_valid_json(self, mock_flush_paths):
        flush.save_flush_state({"session_id": "test", "timestamp": 999.0})
        loaded = flush.load_flush_state()
        assert loaded["session_id"] == "test"

    def test_roundtrip(self, mock_flush_paths):
        original = {"session_id": "abc123", "timestamp": 1700000000.0}
        flush.save_flush_state(original)
        loaded = flush.load_flush_state()
        assert loaded == original


class TestAppendToDailyLog:
    def test_creates_new_log_file(self, mock_flush_paths):
        from datetime import UTC, datetime

        flush.append_to_daily_log("Test content", "Session")
        import config

        today = datetime.now(UTC).astimezone().strftime("%Y-%m-%d")
        log_path = config.DAILY_DIR / f"{today}.md"
        assert log_path.exists()
        content = log_path.read_text()
        assert "Test content" in content
        assert "### Session" in content

    def test_appends_to_existing_log(self, mock_flush_paths, daily_log):
        from datetime import UTC, datetime

        today = datetime.now(UTC).astimezone().strftime("%Y-%m-%d")
        daily_log(today, "# Daily Log: today\n\n## Sessions\n\n")
        flush.append_to_daily_log("New content", "Memory Flush")
        import config

        log_path = config.DAILY_DIR / f"{today}.md"
        content = log_path.read_text()
        assert "New content" in content
        assert "Memory Flush" in content


class TestRunFlush:
    @pytest.mark.asyncio
    async def test_returns_text_from_sdk(self, monkeypatch):
        """run_flush should return the text from the LLM response."""

        async def mock_query(*, prompt, options):
            from claude_agent_sdk import AssistantMessage, ResultMessage, TextBlock

            yield AssistantMessage(content=[TextBlock(text="FLUSH_OK")], model="test")
            yield ResultMessage(
                subtype="success",
                duration_ms=100,
                duration_api_ms=50,
                is_error=False,
                num_turns=1,
                session_id="test-session",
                total_cost_usd=0.01,
            )

        monkeypatch.setattr("claude_agent_sdk.query", mock_query)
        result = await flush.run_flush("some context")
        assert "FLUSH_OK" in result

    @pytest.mark.asyncio
    async def test_handles_sdk_error(self, monkeypatch):
        """run_flush should return FLUSH_ERROR on SDK exception."""

        async def mock_query(*, prompt, options):
            raise RuntimeError("SDK connection failed")
            yield  # makes this an async generator

        monkeypatch.setattr("claude_agent_sdk.query", mock_query)
        result = await flush.run_flush("some context")
        assert "FLUSH_ERROR" in result


class TestMaybeTriggerCompilation:
    def test_skips_before_compile_hour(self, monkeypatch, mock_flush_paths):
        """Before 18:00, compilation should not be triggered."""
        from datetime import UTC, datetime

        # Mock datetime inside flush to return 10:00
        real_datetime = datetime

        class FakeDatetime:
            @staticmethod
            def now(tz=None):
                return real_datetime(2026, 4, 17, 10, 0, 0, tzinfo=UTC)

        monkeypatch.setattr(flush, "datetime", FakeDatetime)

        import subprocess

        popen_mock = MagicMock()
        monkeypatch.setattr(subprocess, "Popen", popen_mock)
        flush.maybe_trigger_compilation()
        popen_mock.assert_not_called()

    def test_triggers_after_compile_hour(self, monkeypatch, mock_flush_paths):
        """After 18:00, compilation should be triggered if not already compiled."""
        from datetime import UTC, datetime

        real_datetime = datetime

        class FakeDatetime:
            @staticmethod
            def now(tz=None):
                return real_datetime(2026, 4, 17, 19, 0, 0, tzinfo=UTC)

        monkeypatch.setattr(flush, "datetime", FakeDatetime)

        import subprocess

        popen_mock = MagicMock()
        monkeypatch.setattr(subprocess, "Popen", popen_mock)
        flush.maybe_trigger_compilation()
        popen_mock.assert_called_once()
