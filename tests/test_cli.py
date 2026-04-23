"""Tests for ocd.cli — init, shell, argparse dispatch, and _init_agent_dir."""

import os
import sys
from unittest.mock import patch

import pytest

from ocd.cli import _init_agent_dir, main


class TestInitAgentDir:
    """_init_agent_dir scaffolds USER/ with directory structure and .gitignore."""

    def test_creates_structure_from_scratch(self, tmp_path):
        _init_agent_dir(tmp_path)

        user = tmp_path / "USER"
        assert (user / ".gitignore").exists()
        assert (user / "logs" / "daily").is_dir()
        assert (user / "knowledge" / "concepts").is_dir()
        assert (user / "knowledge" / "connections").is_dir()
        assert (user / "knowledge" / "qa").is_dir()
        assert (user / "knowledge" / "index.md").exists()
        assert (user / "reports").is_dir()
        assert (user / "state").is_dir()
        assert (user / "agents" / "tasks").is_dir()
        assert (user / "agents" / "runtime").is_dir()
        assert (user / "cache").is_dir()
        assert (user / "worktrees").is_dir()

    def test_idempotent(self, tmp_path):
        _init_agent_dir(tmp_path)
        index_before = (tmp_path / "USER" / "knowledge" / "index.md").read_text()
        _init_agent_dir(tmp_path)
        index_after = (tmp_path / "USER" / "knowledge" / "index.md").read_text()
        assert index_before == index_after

    def test_skips_if_gitignore_exists(self, tmp_path):
        user = tmp_path / "USER"
        user.mkdir()
        (user / ".gitignore").write_text("# custom\n")
        _init_agent_dir(tmp_path)
        assert (user / ".gitignore").read_text() == "# custom\n"

    def test_index_has_header_row(self, tmp_path):
        _init_agent_dir(tmp_path)
        index = (tmp_path / "USER" / "knowledge" / "index.md").read_text()
        assert "Article" in index
        assert "Summary" in index

    def test_gitignore_ignores_runtime_data(self, tmp_path):
        _init_agent_dir(tmp_path)
        gitignore = (tmp_path / "USER" / ".gitignore").read_text()
        assert "*" in gitignore
        assert "!*/" in gitignore


class TestMainDispatch:
    """main() dispatches to subcommands via argparse."""

    def test_init_runs_without_templates(self, tmp_path, capsys):
        with (
            patch.object(sys, "argv", ["ocd", "init"]),
            patch.dict(os.environ, {"PWD": str(tmp_path)}),
            patch("ocd.cli.Path.cwd", return_value=tmp_path),
        ):
            os.chdir(tmp_path)
            main()
        output = capsys.readouterr().out
        assert "OCD environment initialized" in output

    def test_format_dispatches(self):
        with (
            patch.object(sys, "argv", ["ocd", "format"]),
            patch("ocd.cli.run_formatters", return_value=0),
            pytest.raises(SystemExit) as exc_info,
        ):
            main()
        assert exc_info.value.code == 0

    def test_unknown_command_exits(self):
        with patch.object(sys, "argv", ["ocd", "bogus"]), pytest.raises(SystemExit) as exc_info:
            main()
        # argparse returns exit code 2 for unknown subcommands
        assert exc_info.value.code in (1, 2)

    def test_no_args_runs_init(self, tmp_path, capsys):
        with (
            patch.object(sys, "argv", ["ocd"]),
            patch.dict(os.environ, {"PWD": str(tmp_path)}),
            patch("ocd.cli.Path.cwd", return_value=tmp_path),
        ):
            os.chdir(tmp_path)
            main()
        output = capsys.readouterr().out
        assert "OCD environment initialized" in output

    def test_check_dispatches(self):
        with (
            patch.object(sys, "argv", ["ocd", "check"]),
            patch("ocd.check.run_check", return_value=0),
            pytest.raises(SystemExit) as exc_info,
        ):
            main()
        assert exc_info.value.code == 0

    def test_compile_db_dispatches(self, tmp_path):
        with (
            patch.object(sys, "argv", ["ocd", "compile-db"]),
            patch("ocd.cli._cmd_compile_db") as mock,
        ):
            main()
            mock.assert_called_once()

    def test_materialize_dispatches(self, tmp_path):
        with (
            patch.object(sys, "argv", ["ocd", "materialize", "--target", str(tmp_path)]),
            patch("ocd.cli._cmd_materialize") as mock,
        ):
            main()
            mock.assert_called_once()

    def test_standards_dispatches(self, capsys):
        with patch.object(sys, "argv", ["ocd", "standards"]):
            main()
        output = capsys.readouterr().out
        assert "ocd-standards" in output


class TestHookDispatch:
    """hook subcommands delegate to the correct module main()."""

    def test_hook_session_start(self):
        with (
            patch.object(sys, "argv", ["ocd", "hook", "session-start"]),
            patch("ocd.hooks.session_start.main") as mock,
        ):
            main()
            mock.assert_called_once()

    def test_hook_session_end(self):
        with (
            patch.object(sys, "argv", ["ocd", "hook", "session-end"]),
            patch("ocd.hooks.session_end.main") as mock,
        ):
            main()
            mock.assert_called_once()

    def test_hook_pre_compact(self):
        with (
            patch.object(sys, "argv", ["ocd", "hook", "pre-compact"]),
            patch("ocd.hooks.pre_compact.main") as mock,
        ):
            main()
            mock.assert_called_once()

    def test_hook_format_work_edit(self):
        with (
            patch.object(sys, "argv", ["ocd", "hook", "format-work", "--edit"]),
            patch("ocd.hooks.format_work.main") as mock,
        ):
            main()
            mock.assert_called_once()

    def test_hook_lint_work_edit(self):
        with (
            patch.object(sys, "argv", ["ocd", "hook", "lint-work", "--edit"]),
            patch("ocd.hooks.lint_work.main") as mock,
        ):
            main()
            mock.assert_called_once()

    def test_hook_lint_work_commit(self):
        with (
            patch.object(sys, "argv", ["ocd", "hook", "lint-work", "--commit"]),
            patch("ocd.hooks.lint_work.main") as mock,
        ):
            main()
            mock.assert_called_once()

    def test_hook_verify_commit(self):
        with (
            patch.object(sys, "argv", ["ocd", "hook", "verify-commit"]),
            patch("ocd.verify_commit.main") as mock,
        ):
            main()
            mock.assert_called_once()

    def test_hook_ci_check(self):
        with (
            patch.object(sys, "argv", ["ocd", "hook", "ci-check", "--fast"]),
            patch("ocd.ci_check.main") as mock,
        ):
            main()
            mock.assert_called_once()

    def test_hook_no_subcommand_exits(self):
        with patch.object(sys, "argv", ["ocd", "hook"]), pytest.raises(SystemExit) as exc_info:
            main()
        # argparse prints help and exits with code 2 for missing required subcommand
        assert exc_info.value.code in (1, 2)
