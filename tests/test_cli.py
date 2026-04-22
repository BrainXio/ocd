"""Tests for ocd.cli — init, shell, and _init_agent_dir."""

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
    """main() dispatches to subcommands correctly."""

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
        assert exc_info.value.code == 1
