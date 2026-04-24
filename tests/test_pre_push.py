"""Tests for ocd.gates.pre_push — diff-aware test runner."""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock

import pytest

from ocd.gates.pre_push import _FULL_SUITE_FILES, get_changed_files, map_files_to_tests


class TestGetChangedFiles:
    """get_changed_files() returns changed file paths from git."""

    def test_returns_changed_files(self, monkeypatch):
        result = MagicMock()
        result.stdout = "src/ocd/flush.py\nsrc/ocd/utils.py\n"
        result.returncode = 0
        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: result)
        files = get_changed_files("origin/main")
        assert "src/ocd/flush.py" in files
        assert "src/ocd/utils.py" in files

    def test_returns_empty_on_failure(self, monkeypatch):
        result = MagicMock()
        result.returncode = 128
        result.stdout = ""
        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: result)
        files = get_changed_files("origin/main")
        assert files == []

    def test_uses_merge_base_when_available(self, monkeypatch):
        calls = []

        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            r = MagicMock()
            if "merge-base" in cmd:
                r.returncode = 0
                r.stdout = "abc123\n"
            else:
                r.returncode = 0
                r.stdout = "src/ocd/config.py\n"
            return r

        monkeypatch.setattr(subprocess, "run", fake_run)
        get_changed_files("origin/main")
        assert any("merge-base" in c for c in calls)
        assert any("abc123" in str(c) for c in calls)

    def test_falls_back_to_base_when_no_merge_base(self, monkeypatch):
        calls = []

        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            r = MagicMock()
            if "merge-base" in cmd:
                r.returncode = 1
                r.stdout = ""
            else:
                r.returncode = 0
                r.stdout = "src/ocd/flush.py\n"
            return r

        monkeypatch.setattr(subprocess, "run", fake_run)
        files = get_changed_files("origin/main")
        assert "src/ocd/flush.py" in files

    def test_strips_empty_lines(self, monkeypatch):
        result = MagicMock()
        result.stdout = "src/ocd/flush.py\n\nsrc/ocd/utils.py\n"
        result.returncode = 0
        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: result)
        files = get_changed_files("origin/main")
        assert "" not in files


class TestMapFilesToTests:
    """map_files_to_tests() maps source files to test files."""

    def test_maps_source_module(self):
        result = map_files_to_tests(["src/ocd/flush.py"])
        assert result == ["tests/test_flush.py"]

    def test_maps_hooks_module(self):
        result = map_files_to_tests(["src/ocd/hooks/lint_work.py"])
        assert result == ["tests/test_lint_work.py"]

    def test_maps_test_file(self):
        result = map_files_to_tests(["tests/test_flush.py"])
        assert result == ["tests/test_flush.py"]

    def test_maps_multiple_files(self):
        result = map_files_to_tests(
            [
                "src/ocd/flush.py",
                "src/ocd/hooks/session_start.py",
                "tests/test_router.py",
            ]
        )
        assert "tests/test_flush.py" in result
        assert "tests/test_session_start.py" in result
        assert "tests/test_router.py" in result

    def test_infrastructure_file_triggers_full_suite(self):
        for infra in _FULL_SUITE_FILES:
            result = map_files_to_tests([infra])
            assert result == [], f"{infra} should trigger full suite"

    def test_infrastructure_file_mixed_with_source(self):
        result = map_files_to_tests(["src/ocd/config.py", "src/ocd/flush.py"])
        assert result == []

    def test_non_python_file_returns_empty(self):
        result = map_files_to_tests(["README.md"])
        assert result == []

    def test_deduplicates_test_files(self):
        result = map_files_to_tests(
            [
                "src/ocd/flush.py",
                "tests/test_flush.py",
            ]
        )
        assert result.count("tests/test_flush.py") == 1


class TestMainIntegration:
    """Integration tests for main() exit codes."""

    def test_no_origin_main_runs_full_suite(self, monkeypatch):
        calls = []

        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            r = MagicMock()
            if "rev-parse" in cmd:
                r.returncode = 1
            else:
                r.returncode = 0
            return r

        monkeypatch.setattr(subprocess, "run", fake_run)
        from ocd.gates.pre_push import main

        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

    def test_changed_source_runs_subset(self, monkeypatch):
        calls = []

        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            r = MagicMock()
            r.stdout = ""
            r.returncode = 0
            if "merge-base" in cmd:
                r.stdout = "abc123\n"
            elif "diff" in cmd:
                r.stdout = "src/ocd/flush.py\n"
            return r

        monkeypatch.setattr(subprocess, "run", fake_run)
        from ocd.gates.pre_push import main

        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0
        pytest_cmd = [c for c in calls if "pytest" in c]
        assert any("test_flush" in str(c) for c in pytest_cmd)
