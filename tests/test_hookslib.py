"""Tests for hookslib.py — stdin parsing, context extraction, file writing, subprocess."""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

import ocd.config
import ocd.hooks.hookslib as hookslib


class TestReadStdin:
    def test_valid_json(self, monkeypatch):
        monkeypatch.setattr("sys.stdin", MagicMock(read=lambda: '{"key": "value"}'))
        result = hookslib.read_stdin()
        assert result == {"key": "value"}

    def test_windows_backslash_fix(self, monkeypatch):
        raw = '{"path": "C:\\\\Users\\\\test"}'
        monkeypatch.setattr("sys.stdin", MagicMock(read=lambda: raw))
        result = hookslib.read_stdin()
        assert "path" in result

    def test_invalid_json_raises(self, monkeypatch):
        monkeypatch.setattr("sys.stdin", MagicMock(read=lambda: "not json at all"))
        with pytest.raises(json.JSONDecodeError):
            hookslib.read_stdin()


class TestExtractConversationContext:
    def test_basic_transcript(self, sample_transcript, mock_config_paths):
        context, count = hookslib.extract_conversation_context(sample_transcript)
        assert count == 4  # 2 user + 2 assistant
        assert "**User:**" in context
        assert "**Assistant:**" in context

    def test_empty_transcript(self, tmp_path, mock_config_paths):
        empty = tmp_path / "empty.jsonl"
        empty.write_text("")
        context, count = hookslib.extract_conversation_context(empty)
        assert count == 0
        assert context.strip() == ""

    def test_skips_system_messages(self, tmp_path, mock_config_paths):
        f = tmp_path / "transcript.jsonl"
        f.write_text(
            json.dumps({"message": {"role": "system", "content": "You are helpful"}}) + "\n"
        )
        _context, count = hookslib.extract_conversation_context(f)
        assert count == 0

    def test_truncation_respects_max_chars(self, tmp_path, mock_config_paths):
        lines = []
        for _i in range(100):
            lines.append(json.dumps({"message": {"role": "user", "content": "x" * 500}}))
        f = tmp_path / "long.jsonl"
        f.write_text("\n".join(lines))
        context, _count = hookslib.extract_conversation_context(f)
        assert len(context) <= hookslib.MAX_FLUSH_CONTEXT_CHARS + 200

    def test_turn_limit_respected(self, tmp_path, mock_config_paths):
        lines = []
        for i in range(hookslib.MAX_FLUSH_TURNS + 10):
            lines.append(json.dumps({"message": {"role": "user", "content": f"turn {i}"}}))
        f = tmp_path / "many.jsonl"
        f.write_text("\n".join(lines))
        _context, count = hookslib.extract_conversation_context(f)
        assert count <= hookslib.MAX_FLUSH_TURNS

    def test_content_block_list_format(self, tmp_path, mock_config_paths):
        f = tmp_path / "blocks.jsonl"
        entry = {
            "message": {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "Block one"},
                    {"type": "text", "text": "Block two"},
                ],
            }
        }
        f.write_text(json.dumps(entry))
        context, _count = hookslib.extract_conversation_context(f)
        assert "Block one" in context
        assert "Block two" in context


class TestWriteContextFile:
    def test_creates_file_in_state_dir(self, mock_config_paths):
        path = hookslib.write_context_file("sess-123", "test context", prefix="flush-context")
        assert path.exists()
        assert path.read_text() == "test context"

    def test_filename_format(self, mock_config_paths):
        path = hookslib.write_context_file("sess-456", "ctx", prefix="session-flush")
        assert path.name.startswith("session-flush-sess-456-")
        assert path.suffix == ".md"

    def test_creates_state_dir_if_missing(self, mock_config_paths, tmp_path, monkeypatch):
        new_state = tmp_path / "new_state"
        monkeypatch.setattr(ocd.config, "STATE_DIR", new_state)
        monkeypatch.setattr(hookslib, "STATE_DIR", new_state)
        path = hookslib.write_context_file("test", "content")
        assert new_state.exists()
        assert path.exists()


class TestSpawnFlush:
    def test_calls_popen_with_module_flag(self, mock_config_paths, monkeypatch):
        """spawn_flush now uses sys.executable -m ocd.flush instead of a script path."""
        import subprocess

        popen_mock = MagicMock()
        monkeypatch.setattr(subprocess, "Popen", popen_mock)

        context_file = Path("/tmp/test-context.md")
        hookslib.spawn_flush(context_file, "sess-123")

        popen_mock.assert_called_once()
        cmd = popen_mock.call_args[0][0]
        assert "-m" in cmd
        assert "ocd.flush" in cmd
        assert str(context_file) in cmd
        assert "sess-123" in cmd

    def test_popen_uses_devnull(self, mock_config_paths, monkeypatch):
        import subprocess

        popen_mock = MagicMock()
        monkeypatch.setattr(subprocess, "Popen", popen_mock)

        hookslib.spawn_flush(Path("/tmp/ctx.md"), "sess")

        call_kwargs = popen_mock.call_args[1]
        assert call_kwargs["stdout"] == subprocess.DEVNULL
        assert call_kwargs["stderr"] == subprocess.DEVNULL
