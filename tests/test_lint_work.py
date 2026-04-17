"""Tests for lint_work — linter registry, extension detection, and install hints."""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from ocd.hooks import lint_work


class TestExtFromPath:
    def test_python_file(self):
        assert lint_work._ext_from_path("script.py") == "py"

    def test_markdown_file(self):
        assert lint_work._ext_from_path("README.md") == "md"

    def test_no_extension(self):
        assert lint_work._ext_from_path("Makefile") is None

    def test_double_extension(self):
        assert lint_work._ext_from_path("archive.tar.gz") == "gz"

    def test_path_with_directories(self):
        assert lint_work._ext_from_path("src/utils/script.py") == "py"


class TestFormatInstallHint:
    def test_pip_hint(self):
        entry = (("py",), "ruff check {file}", None, True, 8, "file", "pip:ruff")
        result = lint_work._format_install_hint(entry)
        assert "uv" in result
        assert "ruff" in result

    def test_apt_hint(self):
        entry = (
            ("sh", "bash"),
            "shellcheck {file}",
            None,
            True,
            8,
            "file",
            "apt:shellcheck",
        )
        result = lint_work._format_install_hint(entry)
        assert "apt" in result
        assert "shellcheck" in result

    def test_npm_hint(self):
        entry = (
            ("ts", "tsx"),
            "eslint {file}",
            (".eslintrc",),
            True,
            8,
            "file",
            "npm:eslint",
        )
        result = lint_work._format_install_hint(entry)
        assert "npm" in result
        assert "eslint" in result

    def test_go_hint(self):
        entry = (("go",), "go vet {file}", None, True, 8, "file", "go:vet")
        result = lint_work._format_install_hint(entry)
        assert "Go toolchain" in result

    def test_rustup_hint(self):
        entry = (
            ("rs",),
            "cargo clippy -- -D warnings",
            ("Cargo.toml",),
            True,
            15,
            "project",
            "rustup:clippy",
        )
        result = lint_work._format_install_hint(entry)
        assert "rustup" in result


class TestToolAvailable:
    def test_tool_in_venv(self, monkeypatch):
        """A binary in VENV_BIN should be found."""
        monkeypatch.setattr(lint_work, "VENV_BIN", lint_work.VENV_BIN)
        assert lint_work._tool_available("ruff check") is True

    def test_tool_missing(self, monkeypatch):
        """A binary that doesn't exist anywhere should not be found."""
        fake_dir = Path("/nonexistent/bin")
        monkeypatch.setattr(lint_work, "VENV_BIN", fake_dir)
        monkeypatch.setattr("shutil.which", lambda _: None)
        assert lint_work._tool_available("nonexistent_tool_xyz") is False


class TestConfigPresent:
    def test_none_config_always_present(self):
        assert lint_work._config_present(None) is True

    def test_existing_config(self):
        """When the config file exists in PROJECT_ROOT, should return True."""
        assert lint_work._config_present(["pyproject.toml"]) is True

    def test_missing_config(self):
        assert lint_work._config_present(["nonexistent_config_file_xyz.yml"]) is False


class TestLintFile:
    def test_no_linter_for_extension(self):
        """Files with unregistered extensions return empty results."""
        results = lint_work.lint_file("data.xyz")
        assert results == []

    def test_no_extension(self):
        results = lint_work.lint_file("Makefile")
        assert results == []

    def test_missing_linter_reported(self, monkeypatch):
        """If a linter is not installed, it should be reported as missing."""
        monkeypatch.setattr(lint_work, "_tool_available", lambda cmd: False)
        monkeypatch.setattr(lint_work, "_config_present", lambda cfg: True)
        results = lint_work.lint_file("test.py")
        assert len(results) > 0
        assert any(r["status"] == "missing" for r in results)

    def test_missing_config_reported(self, monkeypatch):
        """If a linter has no config, it should be reported as missing."""
        monkeypatch.setattr(lint_work, "_tool_available", lambda cmd: True)
        monkeypatch.setattr(lint_work, "_config_present", lambda cfg: not cfg)
        # TypeScript requires tsconfig.json
        results = lint_work.lint_file("test.ts")
        assert any(r["status"] == "missing" and r["reason"] == "no_config" for r in results)

    def test_linter_errors_reported(self, monkeypatch):
        """Linter with errors should produce an 'errors' result."""
        monkeypatch.setattr(lint_work, "_tool_available", lambda cmd: True)
        monkeypatch.setattr(lint_work, "_config_present", lambda cfg: True)
        monkeypatch.setattr(
            lint_work,
            "run_linter",
            lambda entry, path: (True, "error output"),
        )
        results = lint_work.lint_file("test.py")
        assert any(r["status"] == "errors" for r in results)

    def test_linter_clean_reported(self, monkeypatch):
        """Linter with no errors should produce a 'clean' result."""
        monkeypatch.setattr(lint_work, "_tool_available", lambda cmd: True)
        monkeypatch.setattr(lint_work, "_config_present", lambda cfg: True)
        monkeypatch.setattr(
            lint_work,
            "run_linter",
            lambda entry, path: (False, "all clean"),
        )
        results = lint_work.lint_file("test.py")
        assert any(r["status"] == "clean" for r in results)


class TestEditMode:
    def test_outputs_block_on_errors(self, monkeypatch, capsys):
        """When linters find errors, edit_mode should output a block decision."""
        monkeypatch.setattr(lint_work, "_tool_available", lambda cmd: True)
        monkeypatch.setattr(lint_work, "_config_present", lambda cfg: True)
        monkeypatch.setattr(
            lint_work,
            "run_linter",
            lambda entry, path: (True, "E501 line too long"),
        )
        monkeypatch.setattr(
            lint_work, "read_stdin", lambda: {"tool_input": {"file_path": "test.py"}}
        )

        lint_work.edit_mode()
        output = capsys.readouterr().out
        result = json.loads(output)
        assert result["decision"] == "block"

    def test_outputs_context_on_missing(self, monkeypatch, capsys):
        """When a linter is missing, edit_mode should report it as context."""
        monkeypatch.setattr(lint_work, "_tool_available", lambda cmd: False)
        monkeypatch.setattr(
            lint_work, "read_stdin", lambda: {"tool_input": {"file_path": "test.py"}}
        )

        lint_work.edit_mode()
        output = capsys.readouterr().out
        if output.strip():
            result = json.loads(output)
            assert "hookSpecificOutput" in result

    def test_no_output_for_unknown_extension(self, monkeypatch, capsys):
        """Files with no registered linter should produce no output."""
        monkeypatch.setattr(
            lint_work, "read_stdin", lambda: {"tool_input": {"file_path": "data.xyz"}}
        )

        lint_work.edit_mode()
        output = capsys.readouterr().out
        assert output == ""


class TestCommitMode:
    def test_exits_on_errors(self, monkeypatch):
        """commit_mode should exit with code 2 when lint errors found."""
        monkeypatch.setattr(lint_work, "_tool_available", lambda cmd: True)
        monkeypatch.setattr(lint_work, "_config_present", lambda cfg: True)
        monkeypatch.setattr(
            lint_work,
            "run_linter",
            lambda entry, path: (True, "error output"),
        )
        monkeypatch.setattr(
            lint_work,
            "read_stdin",
            lambda: {"tool_input": {"command": "git commit -m test"}},
        )
        monkeypatch.setattr(
            "subprocess.run",
            lambda *a, **kw: MagicMock(stdout="test.py", returncode=0, stderr=""),
        )
        monkeypatch.setattr("os.chdir", lambda _: None)

        with pytest.raises(SystemExit) as exc_info:
            lint_work.commit_mode()
        assert exc_info.value.code == 2

    def test_skips_non_git_commit(self, monkeypatch, capsys):
        """commit_mode should do nothing for non-git-commit commands."""
        monkeypatch.setattr(
            lint_work, "read_stdin", lambda: {"tool_input": {"command": "npm test"}}
        )
        lint_work.commit_mode()
        output = capsys.readouterr().out
        assert output == ""
