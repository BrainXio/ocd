"""Tests for fix — closed-loop fix commands."""

import json

from ocd.fix import FixResult, fix_cycle, lint_and_fix, security_scan_and_patch, test_and_fix


class TestFixResult:
    def test_default_values(self):
        r = FixResult()
        assert r.fixed == []
        assert r.remaining == []
        assert r.exit_code == 0

    def test_to_json(self):
        r = FixResult(fixed=["ruff-format"], remaining=["mypy: error"], exit_code=1)
        data = json.loads(r.to_json())
        assert data["fixed"] == ["ruff-format"]
        assert data["remaining"] == ["mypy: error"]
        assert data["exit_code"] == 1

    def test_empty_to_json(self):
        r = FixResult()
        data = json.loads(r.to_json())
        assert data == {"fixed": [], "remaining": [], "exit_code": 0}


class TestFixCycle:
    def test_nonexistent_file(self):
        result = fix_cycle("/nonexistent/file.py")
        assert result.exit_code == 1

    def test_python_file(self):
        # fix_cycle on an actual project file should succeed or report remaining
        result = fix_cycle("src/ocd/config.py")
        assert isinstance(result, FixResult)
        assert isinstance(result.fixed, list)
        assert isinstance(result.remaining, list)
        assert isinstance(result.exit_code, int)

    def test_markdown_file(self):
        result = fix_cycle("README.md")
        assert isinstance(result, FixResult)


class TestLintAndFix:
    def test_nonexistent_path(self):
        result = lint_and_fix("/nonexistent/path")
        assert result.exit_code == 1
        assert any("not found" in r for r in result.remaining)

    def test_src_directory(self):
        result = lint_and_fix("src/ocd/")
        assert isinstance(result, FixResult)
        assert isinstance(result.fixed, list)

    def test_single_file(self):
        result = lint_and_fix("src/ocd/config.py")
        assert isinstance(result, FixResult)


class TestTestAndFix:
    def test_runs(self):
        # Should succeed since the project's tests are green
        result = test_and_fix()
        assert isinstance(result, FixResult)
        assert isinstance(result.fixed, list)
        assert isinstance(result.remaining, list)


class TestSecurityScanAndPatch:
    def test_runs(self):
        # semgrep may or may not be installed; just check it returns FixResult
        result = security_scan_and_patch()
        assert isinstance(result, FixResult)
        assert isinstance(result.fixed, list)
        assert isinstance(result.remaining, list)
