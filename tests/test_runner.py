"""Tests for the ToolRunner registry and executor."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest import mock

from ocd.tools.runner import Tool, ToolResult, ToolRunner, ci_gate_tools, fast_gate_tools


class TestTool:
    def test_is_available_when_binary_exists(self) -> None:
        tool = Tool(name="test", binary="python3")
        assert tool.is_available() is True

    def test_is_available_when_binary_missing(self) -> None:
        tool = Tool(name="test", binary="nonexistent_binary_12345")
        assert tool.is_available() is False

    def test_build_command_simple(self) -> None:
        tool = Tool(name="ruff-check", binary="ruff", args=["check", "src/"])
        cmd = tool.build_command(Path("/project"))
        assert cmd == ["ruff", "check", "src/"]

    def test_build_command_with_config_flag(self, tmp_path: Path) -> None:
        config_file = tmp_path / ".gitleaks.toml"
        config_file.write_text("[extend]")
        tool = Tool(
            name="secret-scan",
            binary="gitleaks",
            args=["protect", "--staged"],
            config_flag=("-c", ".gitleaks.toml"),
        )
        cmd = tool.build_command(tmp_path)
        assert "-c" in cmd
        assert str(tmp_path / ".gitleaks.toml") in cmd

    def test_build_command_skips_missing_config(self, tmp_path: Path) -> None:
        tool = Tool(
            name="secret-scan",
            binary="gitleaks",
            args=["detect"],
            config_flag=("-c", ".gitleaks.toml"),
        )
        cmd = tool.build_command(tmp_path)
        assert "-c" not in cmd


class TestToolRunner:
    def test_register_and_run_skipped(self, tmp_path: Path) -> None:
        runner = ToolRunner(tmp_path)
        runner.register(Tool(name="fake", binary="nonexistent_12345"))
        results = runner.run_all()
        assert len(results) == 1
        assert results[0].status == "skip"

    def test_run_one_pass(self, tmp_path: Path) -> None:
        runner = ToolRunner(tmp_path)
        tool = Tool(name="echo-test", binary="echo", args=["hello"])
        result = runner.run_one(tool)
        assert result.status == "pass"
        assert result.detail == "clean"

    def test_run_one_timeout(self, tmp_path: Path) -> None:
        runner = ToolRunner(tmp_path)
        tool = Tool(name="sleep-test", binary="sleep", args=["60"], timeout=1)
        result = runner.run_one(tool)
        assert result.status == "fail"
        assert "timed out" in result.detail

    def test_results_as_dicts(self, tmp_path: Path) -> None:
        results = [ToolResult(check="a", status="pass", detail="ok")]
        runner = ToolRunner(tmp_path)
        dicts = runner.results_as_dicts(results)
        assert dicts == [{"check": "a", "status": "pass", "detail": "ok"}]

    def test_run_all_multiple_tools(self, tmp_path: Path) -> None:
        runner = ToolRunner(tmp_path)
        runner.register(Tool(name="echo-1", binary="echo", args=["first"]))
        runner.register(Tool(name="fake", binary="nonexistent_12345"))
        runner.register(Tool(name="echo-2", binary="echo", args=["second"]))
        results = runner.run_all()
        assert len(results) == 3
        assert results[0].status == "pass"
        assert results[1].status == "skip"
        assert results[2].status == "pass"

    def test_run_one_failing_command(self, tmp_path: Path) -> None:
        runner = ToolRunner(tmp_path)
        tool = Tool(name="false", binary="false", args=[])
        result = runner.run_one(tool)
        assert result.status == "fail"

    def test_file_not_found_treated_as_skip(self, tmp_path: Path) -> None:
        runner = ToolRunner(tmp_path)
        tool = Tool(name="missing", binary="absolutely_no_such_binary_xyz")
        result = runner.run_one(tool)
        assert result.status == "skip"
        assert "not installed" in result.detail

    def test_cwd_suffix_appended_to_root(self, tmp_path: Path) -> None:
        subdir = tmp_path / "subproject"
        subdir.mkdir()
        tool = Tool(name="echo-test", binary="echo", args=["hello"], cwd_suffix="subproject")
        runner = ToolRunner(tmp_path)
        with mock.patch.object(
            subprocess, "run", return_value=mock.Mock(returncode=0, stderr="", stdout="hello")
        ) as mock_run:
            runner.run_one(tool)
            assert mock_run.call_args[1]["cwd"] == str(subdir)


class TestGateToolFactories:
    def test_fast_gate_tools_count(self) -> None:
        tools = fast_gate_tools(Path("/project"))
        assert len(tools) == 2
        names = [t.name for t in tools]
        assert "secret-scan" in names
        assert "ruff-check" in names

    def test_ci_gate_tools_count(self) -> None:
        tools = ci_gate_tools(Path("/project"))
        assert len(tools) == 5
        names = [t.name for t in tools]
        assert "secret-scan" in names
        assert "ruff-check" in names
        assert "ruff-format" in names
        assert "mypy" in names
        assert "yamllint" in names

    def test_fast_gate_tools_have_correct_binaries(self) -> None:
        tools = fast_gate_tools(Path("/project"))
        binaries = {t.binary for t in tools}
        assert "gitleaks" in binaries
        assert "ruff" in binaries

    def test_ci_gate_tools_have_timeouts(self) -> None:
        tools = ci_gate_tools(Path("/project"))
        for tool in tools:
            assert tool.timeout > 0
