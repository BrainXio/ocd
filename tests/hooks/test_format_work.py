"""Tests for ocd.hooks.format_work — per-file auto-format hook."""

import json
import sys
from unittest.mock import MagicMock, patch

from ocd.hooks.format_work import (
    FILE_FORMATTERS,
    _config_present,
    _ext_from_path,
    _file_hash,
    _format_install_hint,
    _log_violation,
    _tool_available,
    format_file,
)


class TestFileFormattersRegistry:
    def test_registry_not_empty(self):
        assert len(FILE_FORMATTERS) > 0

    def test_each_entry_has_five_fields(self):
        for entry in FILE_FORMATTERS:
            assert len(entry) == 5, f"Entry has {len(entry)} fields, expected 5"

    def test_commands_are_callables(self):
        for entry in FILE_FORMATTERS:
            assert callable(entry[1]), f"Command for {entry[0]} should be callable"

    def test_python_formatters_present(self):
        exts = set()
        for entry in FILE_FORMATTERS:
            exts.update(entry[0])
        assert "py" in exts

    def test_mdformatter_present(self):
        exts = set()
        for entry in FILE_FORMATTERS:
            exts.update(entry[0])
        assert "md" in exts


class TestExtFromPath:
    def test_python(self):
        assert _ext_from_path("src/ocd/format.py") == "py"

    def test_markdown(self):
        assert _ext_from_path("README.md") == "md"

    def test_no_extension(self):
        assert _ext_from_path("Makefile") is None

    def test_nested_path(self):
        assert _ext_from_path("docs/guide.md") == "md"


class TestToolAvailable:
    def test_available_tool(self, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda cmd: "/usr/bin/ruff" if cmd == "ruff" else None)
        assert _tool_available(["ruff", "format", "file.py"]) is True

    def test_unavailable_tool(self, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda _: None)
        fake_dir = MagicMock()
        fake_dir.__truediv__ = lambda s, o: MagicMock(exists=lambda: False)
        monkeypatch.setattr("ocd.hooks.format_work.VENV_BIN", fake_dir)
        assert _tool_available(["nonexistent_xyz"]) is False

    def test_npx_check(self, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda cmd: "/usr/bin/npx" if cmd == "npx" else None)
        assert _tool_available(["npx", "stylelint", "--fix", "f.css"]) is True


class TestConfigPresent:
    def test_none_config_always_present(self):
        assert _config_present(None) is True

    def test_existing_config(self):
        assert _config_present(["pyproject.toml"]) is True

    def test_missing_config(self):
        assert _config_present(["nonexistent_config_xyz.yml"]) is False


class TestFileHash:
    def test_returns_value_for_existing_file(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text("pass")
        result = _file_hash(str(f))
        assert result is not None

    def test_returns_none_for_missing_file(self):
        result = _file_hash("/nonexistent/path/file.py")
        assert result is None


class TestFormatInstallHint:
    def test_pip_hint(self):
        entry = (("py",), lambda f: ["ruff", "format", f], None, 10, "pip:ruff")
        result = _format_install_hint(entry)
        assert "uv" in result
        assert "ruff" in result

    def test_npm_hint(self):
        entry = (("css",), lambda f: ["npx", "stylelint", "--fix", f], None, 15, "npm:stylelint")
        result = _format_install_hint(entry)
        assert "npm" in result
        assert "stylelint" in result


class TestLogViolation:
    def test_appends_entry(self, tmp_path, monkeypatch):
        log_file = tmp_path / "violations.jsonl"
        monkeypatch.setattr("ocd.hooks.format_work.VIOLATIONS_LOG", log_file)
        monkeypatch.setattr("ocd.hooks.format_work.STATE_DIR", tmp_path)

        _log_violation("test.py", "ruff", "py")

        assert log_file.exists()
        entry = json.loads(log_file.read_text().strip())
        assert entry["file"] == "test.py"
        assert entry["formatter"] == "ruff"
        assert entry["extension"] == "py"
        assert "timestamp" in entry

    def test_appends_multiple_entries(self, tmp_path, monkeypatch):
        log_file = tmp_path / "violations.jsonl"
        monkeypatch.setattr("ocd.hooks.format_work.VIOLATIONS_LOG", log_file)
        monkeypatch.setattr("ocd.hooks.format_work.STATE_DIR", tmp_path)

        _log_violation("a.py", "ruff", "py")
        _log_violation("b.md", "mdformat", "md")

        lines = log_file.read_text().strip().splitlines()
        assert len(lines) == 2


class TestFormatFile:
    def test_non_matching_extension_returns_none(self):
        result = format_file("Makefile")
        assert result is None

    def test_missing_tool_returns_advisory(self, monkeypatch):
        monkeypatch.setattr("ocd.hooks.format_work._tool_available", lambda _: False)
        result = format_file("test.py")
        assert result is not None
        assert "hookSpecificOutput" in result
        assert "not installed" in result["hookSpecificOutput"]["additionalContext"]

    def test_missing_config_returns_advisory(self, monkeypatch):
        monkeypatch.setattr("ocd.hooks.format_work._tool_available", lambda _: True)
        monkeypatch.setattr("ocd.hooks.format_work._config_present", lambda _: False)
        result = format_file("test.py")
        assert result is not None
        assert "hookSpecificOutput" in result
        assert "not configured" in result["hookSpecificOutput"]["additionalContext"]

    def test_formatter_failure_returns_block(self, monkeypatch, tmp_path):
        monkeypatch.setattr("ocd.hooks.format_work._tool_available", lambda _: True)
        monkeypatch.setattr("ocd.hooks.format_work._config_present", lambda _: True)
        monkeypatch.setattr("ocd.hooks.format_work.VIOLATIONS_LOG", tmp_path / "violations.jsonl")
        monkeypatch.setattr("ocd.hooks.format_work.STATE_DIR", tmp_path)

        with patch(
            "subprocess.run",
            return_value=MagicMock(returncode=1, stdout="error", stderr=""),
        ):
            result = format_file("test.py")
        assert result is not None
        assert result.get("decision") == "block"

    def test_formatter_success_no_change_returns_none(self, monkeypatch, tmp_path):
        monkeypatch.setattr("ocd.hooks.format_work._tool_available", lambda _: True)
        monkeypatch.setattr("ocd.hooks.format_work._config_present", lambda _: True)
        monkeypatch.setattr("ocd.hooks.format_work._file_hash", lambda _: "same")

        with patch(
            "subprocess.run",
            return_value=MagicMock(returncode=0, stdout="", stderr=""),
        ):
            result = format_file("test.py")
        assert result is None

    def test_formatter_success_with_change_reports_context(self, monkeypatch, tmp_path):
        monkeypatch.setattr("ocd.hooks.format_work._tool_available", lambda _: True)
        monkeypatch.setattr("ocd.hooks.format_work._config_present", lambda _: True)
        monkeypatch.setattr("ocd.hooks.format_work.VIOLATIONS_LOG", tmp_path / "violations.jsonl")
        monkeypatch.setattr("ocd.hooks.format_work.STATE_DIR", tmp_path)

        call_count = [0]

        def fake_hash(_):
            call_count[0] += 1
            return "before" if call_count[0] % 2 == 1 else "after"

        monkeypatch.setattr("ocd.hooks.format_work._file_hash", fake_hash)

        with patch(
            "subprocess.run",
            return_value=MagicMock(returncode=0, stdout="", stderr=""),
        ):
            result = format_file("test.py")
        assert result is not None
        assert "hookSpecificOutput" in result
        assert "auto-formatted" in result["hookSpecificOutput"]["additionalContext"]


class TestEditMode:
    def test_empty_file_path(self, monkeypatch, capsys):
        monkeypatch.setattr(
            "ocd.hooks.format_work.parse_stdin_json",
            lambda: {"tool_input": {"file_path": ""}},
        )
        from ocd.hooks.format_work import edit_mode

        edit_mode()
        assert capsys.readouterr().out == ""

    def test_non_md_file_no_output(self, monkeypatch, capsys):
        monkeypatch.setattr(
            "ocd.hooks.format_work.parse_stdin_json",
            lambda: {"tool_input": {"file_path": "Makefile"}},
        )
        monkeypatch.setattr("ocd.hooks.format_work._tool_available", lambda _: False)
        from ocd.hooks.format_work import edit_mode

        edit_mode()
        assert capsys.readouterr().out == ""


class TestRecursionGuard:
    def test_format_work_running_env_exits(self, monkeypatch):
        monkeypatch.setenv("OCD_FORMAT_WORK_RUNNING", "1")
        from ocd.hooks.format_work import main

        # Should return without doing anything
        main()

    def test_claude_invoked_by_env_exits(self, monkeypatch):
        monkeypatch.setenv("CLAUDE_INVOKED_BY", "memory_flush")
        from ocd.hooks.format_work import main

        main()


class TestMainDispatch:
    def test_edit_flag_dispatches(self, monkeypatch):
        called = []
        monkeypatch.setattr("ocd.hooks.format_work.edit_mode", lambda: called.append(True))
        monkeypatch.setattr(sys, "argv", ["format_work", "--edit"])
        from ocd.hooks.format_work import main

        main()
        assert called

    def test_no_flags_does_nothing(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["format_work"])
        from ocd.hooks.format_work import main

        # Should not raise
        main()
