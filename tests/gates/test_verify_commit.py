"""Tests for ocd.gates.verify_commit — AI attribution checker."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock

from ocd.gates.verify_commit import check_commit_range, check_message, load_patterns


class TestLoadPatterns:
    """load_patterns() reads patterns from ai-patterns.txt."""

    def test_loads_patterns_from_file(self, tmp_path):
        patterns_file = tmp_path / "ai-patterns.txt"
        patterns_file.write_text("^Co-Authored-By:\n^Generated (with|by|using)\n")
        result = load_patterns(patterns_file)
        assert len(result) == 2
        assert result[0] == "^Co-Authored-By:"
        assert result[1] == "^Generated (with|by|using)"

    def test_skips_blank_lines(self, tmp_path):
        patterns_file = tmp_path / "ai-patterns.txt"
        patterns_file.write_text("^Co-Authored-By:\n\n^Generated\n")
        result = load_patterns(patterns_file)
        assert len(result) == 2

    def test_skips_comments(self, tmp_path):
        patterns_file = tmp_path / "ai-patterns.txt"
        patterns_file.write_text("# comment\n^Co-Authored-By:\n")
        result = load_patterns(patterns_file)
        assert result == ["^Co-Authored-By:"]

    def test_returns_empty_for_missing_file(self):
        result = load_patterns(Path("/nonexistent/file"))
        assert result == []

    def test_strips_whitespace(self, tmp_path):
        patterns_file = tmp_path / "ai-patterns.txt"
        patterns_file.write_text("  ^Co-Authored-By:  \n")
        result = load_patterns(patterns_file)
        assert result == ["^Co-Authored-By:"]


class TestCheckMessage:
    """check_message() detects AI attribution in commit messages."""

    def test_clean_message(self):
        result = check_message("feat: add new feature", patterns=["^Co-Authored-By:"])
        assert result == []

    def test_co_authored_by(self):
        result = check_message(
            "Co-Authored-By: Claude <noreply@anthropic.com>",
            patterns=["^Co-Authored-By:"],
        )
        assert len(result) == 1
        assert result[0][0] == "^Co-Authored-By:"

    def test_generated_with(self):
        result = check_message(
            "Generated with Claude Code",
            patterns=["^Generated (with|by|using)"],
        )
        assert len(result) == 1

    def test_ai_tag(self):
        result = check_message("[AI] fix the bug", patterns=[r"^\[AI(-generated)?\]"])
        assert len(result) == 1

    def test_ai_generated_tag(self):
        result = check_message("[AI-generated] fix the bug", patterns=[r"^\[AI(-generated)?\]"])
        assert len(result) == 1

    def test_case_insensitive(self):
        result = check_message("co-authored-by: someone", patterns=["^Co-Authored-By:"])
        assert len(result) == 1

    def test_no_false_positive_mid_line(self):
        """Pattern anchored with ^ should not match mid-line."""
        result = check_message(
            "fix: co-authored-by should not match", patterns=["^Co-Authored-By:"]
        )
        assert result == []

    def test_uses_default_patterns(self, monkeypatch, tmp_path):
        """When patterns=None, load_patterns() is called with default file."""
        patterns_file = tmp_path / "ai-patterns.txt"
        patterns_file.write_text("^TEST-PATTERN\n")
        monkeypatch.setattr("ocd.gates.verify_commit._PATTERNS_FILE", patterns_file)
        result = check_message("TEST-PATTERN found here", patterns=None)
        assert len(result) == 1

    def test_multiple_violations(self):
        message = "Co-Authored-By: bot\n\n[AI] generated"
        result = check_message(message, patterns=["^Co-Authored-By:", r"^\[AI(-generated)?\]"])
        assert len(result) == 2


class TestCheckCommitRange:
    """check_commit_range() checks all commits in a git range."""

    def test_detects_violation_in_range(self, monkeypatch):
        def fake_run(cmd, **kwargs):
            r = MagicMock()
            r.returncode = 0
            if "rev-list" in cmd:
                r.stdout = "abc123\ndef456\n"
            elif "log" in cmd:
                r.stdout = "feat: good commit\n"
            return r

        monkeypatch.setattr(subprocess, "run", fake_run)
        result = check_commit_range("origin/main..HEAD")
        assert result == []

    def test_finds_ai_attribution(self, monkeypatch):
        def fake_run(cmd, **kwargs):
            r = MagicMock()
            r.returncode = 0
            if "rev-list" in cmd:
                r.stdout = "abc123\n"
            elif "log" in cmd:
                r.stdout = "Co-Authored-By: bot\n"
            return r

        monkeypatch.setattr(subprocess, "run", fake_run)
        monkeypatch.setattr(
            "ocd.gates.verify_commit.load_patterns",
            lambda: ["^Co-Authored-By:"],
        )
        result = check_commit_range("origin/main..HEAD")
        assert len(result) == 1
        assert result[0][0] == "abc123"

    def test_returns_empty_on_git_failure(self, monkeypatch):
        def fake_run(cmd, **kwargs):
            r = MagicMock()
            r.returncode = 128
            r.stdout = ""
            return r

        monkeypatch.setattr(subprocess, "run", fake_run)
        result = check_commit_range("origin/main..HEAD")
        assert result == []
