"""Tests for ocd.config — path constants and date functions."""

import re
import sys
from pathlib import Path

from ocd import config


class TestPathConstants:
    """Path constants derive from _find_project_root() and must be internally consistent."""

    def test_project_root_contains_git(self):
        assert (config.PROJECT_ROOT / ".git").is_dir()

    def test_agent_dir_under_project_root(self):
        assert config.AGENT_DIR == config.PROJECT_ROOT / ".agent"

    def test_state_dir_under_agent_dir(self):
        assert config.STATE_DIR.parent == config.AGENT_DIR

    def test_knowledge_dir_under_agent_dir(self):
        assert config.KNOWLEDGE_DIR.parent == config.AGENT_DIR

    def test_subdirs_under_knowledge_dir(self):
        assert config.CONCEPTS_DIR.parent == config.KNOWLEDGE_DIR
        assert config.CONNECTIONS_DIR.parent == config.KNOWLEDGE_DIR
        assert config.QA_DIR.parent == config.KNOWLEDGE_DIR

    def test_venv_bin_is_executable_parent(self):
        assert Path(sys.executable).parent == config.VENV_BIN


class TestNowIso:
    """now_iso() must return valid ISO 8601 strings with timezone."""

    def test_returns_string(self):
        result = config.now_iso()
        assert isinstance(result, str)

    def test_format_contains_date_and_time(self):
        result = config.now_iso()
        assert "T" in result
        # ISO 8601 with timezone offset like +00:00 or Z
        assert re.search(r"[+-]\d{2}:\d{2}|Z$", result)


class TestTodayIso:
    """today_iso() must return YYYY-MM-DD format."""

    def test_returns_date_string(self):
        result = config.today_iso()
        assert isinstance(result, str)
        assert len(result) == 10
        assert result[4] == "-"
        assert result[7] == "-"

    def test_date_is_valid(self):
        result = config.today_iso()
        year, month, day = result.split("-")
        assert int(year) >= 2026
        assert 1 <= int(month) <= 12
        assert 1 <= int(day) <= 31
