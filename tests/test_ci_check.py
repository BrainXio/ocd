"""Tests for ocd.gates.ci_check — full CI mirror."""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock

from ocd.gates.ci_check import (
    _mdformat_check,
    _mypy,
    _ruff_check,
    _ruff_format_check,
    _scan_secrets_full,
    _shellcheck,
    _standards_verify,
    _verify_commit_messages,
    _yamllint,
)


class TestStandardsVerify:
    """_standards_verify() delegates to ocd.routing.standards."""

    def test_match(self, monkeypatch):
        monkeypatch.setattr(
            "ocd.routing.standards.verify_standards_hash",
            lambda: {"match": True, "version": "1.0", "computed_hash": "abc"},
        )
        passed, msg = _standards_verify()
        assert passed is True
        assert "abc" in msg

    def test_mismatch(self, monkeypatch):
        monkeypatch.setattr(
            "ocd.routing.standards.verify_standards_hash",
            lambda: {"match": False, "stored_hash": "old", "computed_hash": "new"},
        )
        passed, _msg = _standards_verify()
        assert passed is False


class TestVerifyCommitMessages:
    """_verify_commit_messages() delegates to ocd.gates.verify_commit."""

    def test_no_range_skips(self):
        passed, msg = _verify_commit_messages(None)
        assert passed is True
        assert "skipped" in msg

    def test_violations_found(self, monkeypatch):
        monkeypatch.setattr(
            "ocd.gates.verify_commit.check_commit_range",
            lambda r: [("abc1234", "^Co-Authored-By:", "Co-Authored-By: bot")],
        )
        passed, _msg = _verify_commit_messages("origin/main..HEAD")
        assert passed is False

    def test_no_violations(self, monkeypatch):
        monkeypatch.setattr(
            "ocd.gates.verify_commit.check_commit_range",
            lambda r: [],
        )
        passed, _msg = _verify_commit_messages("origin/main..HEAD")
        assert passed is True


class TestScanSecretsFull:
    """_scan_secrets_full() delegates to ocd.gates.scan_secrets."""

    def test_clean(self, monkeypatch):
        monkeypatch.setattr(
            "ocd.gates.scan_secrets.scan_secrets", lambda staged=False, source=".": 0
        )
        passed, _msg = _scan_secrets_full()
        assert passed is True

    def test_secrets_found(self, monkeypatch):
        monkeypatch.setattr(
            "ocd.gates.scan_secrets.scan_secrets", lambda staged=False, source=".": 1
        )
        passed, _msg = _scan_secrets_full()
        assert passed is False

    def test_not_installed(self, monkeypatch):
        monkeypatch.setattr(
            "ocd.gates.scan_secrets.scan_secrets", lambda staged=False, source=".": 2
        )
        passed, msg = _scan_secrets_full()
        assert passed is True
        assert "skipped" in msg


class TestToolChecks:
    """Tool-based checks gracefully skip when tools are unavailable."""

    def test_ruff_check_clean(self, monkeypatch):
        monkeypatch.setattr("ocd.gates.ci_check._tool_available", lambda _: True)
        monkeypatch.setattr(
            subprocess,
            "run",
            lambda *a, **kw: MagicMock(returncode=0, stdout="", stderr=""),
        )
        passed, _msg = _ruff_check()
        assert passed is True

    def test_ruff_format_check_clean(self, monkeypatch):
        monkeypatch.setattr("ocd.gates.ci_check._tool_available", lambda _: True)
        monkeypatch.setattr(
            subprocess,
            "run",
            lambda *a, **kw: MagicMock(returncode=0, stdout="", stderr=""),
        )
        passed, _msg = _ruff_format_check()
        assert passed is True

    def test_mypy_skipped(self, monkeypatch):
        monkeypatch.setattr("ocd.gates.ci_check._tool_available", lambda _: False)
        passed, msg = _mypy()
        assert passed is True
        assert "skipped" in msg

    def test_mdformat_skipped(self, monkeypatch):
        monkeypatch.setattr("ocd.gates.ci_check._tool_available", lambda _: False)
        passed, msg = _mdformat_check()
        assert passed is True
        assert "skipped" in msg

    def test_yamllint_skipped(self, monkeypatch):
        monkeypatch.setattr("ocd.gates.ci_check._tool_available", lambda _: False)
        passed, msg = _yamllint()
        assert passed is True
        assert "skipped" in msg

    def test_shellcheck_skipped(self, monkeypatch):
        monkeypatch.setattr("ocd.gates.ci_check._tool_available", lambda _: False)
        passed, msg = _shellcheck()
        assert passed is True
        assert "skipped" in msg
