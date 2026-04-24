"""Tests for ocd.gates.check — fast local quality gate."""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock

from ocd.gates.check import (
    _branch_protection,
    _no_local_config_staged,
    _scan_secrets_staged,
    _staged_files,
    _standards_verify,
    run_check,
)


class TestNoLocalConfigStaged:
    """_no_local_config_staged() blocks local config files from commits."""

    def test_allows_clean_staging(self, monkeypatch):
        monkeypatch.setattr(
            subprocess,
            "run",
            lambda *a, **kw: MagicMock(stdout="src/ocd/check.py\n", returncode=0),
        )
        passed, msg = _no_local_config_staged()
        assert passed is True
        assert "no local configs" in msg

    def test_rejects_settings_local_json(self, monkeypatch):
        monkeypatch.setattr(
            subprocess,
            "run",
            lambda *a, **kw: MagicMock(stdout=".claude/settings.local.json\n", returncode=0),
        )
        passed, msg = _no_local_config_staged()
        assert passed is False
        assert "settings.local.json" in msg


class TestBranchProtection:
    """_branch_protection() rejects commits on main."""

    def test_allows_feature_branch(self, monkeypatch):
        monkeypatch.setattr(
            subprocess,
            "run",
            lambda *a, **kw: MagicMock(stdout="feat/new-thing\n", returncode=0),
        )
        passed, msg = _branch_protection()
        assert passed is True
        assert "feat/new-thing" in msg

    def test_rejects_main(self, monkeypatch):
        monkeypatch.setattr(
            subprocess,
            "run",
            lambda *a, **kw: MagicMock(stdout="main\n", returncode=0),
        )
        passed, msg = _branch_protection()
        assert passed is False
        assert "main" in msg


class TestStagedFiles:
    """_staged_files() returns files matching the given extension."""

    def test_returns_matching_files(self, monkeypatch):
        monkeypatch.setattr(
            subprocess,
            "run",
            lambda *a, **kw: MagicMock(stdout="src/ocd/check.py\ntests/test.py\n"),
        )
        files = _staged_files(".py")
        assert "src/ocd/check.py" in files

    def test_returns_empty_list(self, monkeypatch):
        monkeypatch.setattr(
            subprocess,
            "run",
            lambda *a, **kw: MagicMock(stdout=""),
        )
        files = _staged_files(".py")
        assert files == []


class TestStandardsVerify:
    """_standards_verify() delegates to ocd.routing.standards."""

    def test_match_returns_true(self, monkeypatch):
        monkeypatch.setattr(
            "ocd.routing.standards.verify_standards_hash",
            lambda: {"match": True, "version": "1.0", "computed_hash": "abc123"},
        )
        passed, msg = _standards_verify()
        assert passed is True
        assert "abc123" in msg

    def test_mismatch_returns_false(self, monkeypatch):
        monkeypatch.setattr(
            "ocd.routing.standards.verify_standards_hash",
            lambda: {
                "match": False,
                "stored_hash": "old",
                "computed_hash": "new",
            },
        )
        passed, msg = _standards_verify()
        assert passed is False
        assert "mismatch" in msg

    def test_error_returns_false(self, monkeypatch):
        monkeypatch.setattr(
            "ocd.routing.standards.verify_standards_hash",
            lambda: {"match": False, "error": "not found"},
        )
        passed, _msg = _standards_verify()
        assert passed is False


class TestScanSecretsStaged:
    """_scan_secrets_staged() delegates to ocd.gates.scan_secrets."""

    def test_clean(self, monkeypatch):
        monkeypatch.setattr("ocd.gates.scan_secrets.scan_secrets", lambda staged=True: 0)
        passed, _msg = _scan_secrets_staged()
        assert passed is True

    def test_secrets_found(self, monkeypatch):
        monkeypatch.setattr("ocd.gates.scan_secrets.scan_secrets", lambda staged=True: 1)
        passed, _msg = _scan_secrets_staged()
        assert passed is False

    def test_not_installed_skips(self, monkeypatch):
        monkeypatch.setattr("ocd.gates.scan_secrets.scan_secrets", lambda staged=True: 2)
        passed, _msg = _scan_secrets_staged()
        assert passed is True


class TestRunCheck:
    """run_check() aggregates all checks."""

    def test_all_pass(self, monkeypatch):
        monkeypatch.setattr(
            subprocess, "run", lambda *a, **kw: MagicMock(stdout="feature\n", returncode=0)
        )
        monkeypatch.setattr(
            "ocd.routing.standards.verify_standards_hash",
            lambda: {"match": True, "version": "1.0", "computed_hash": "abc"},
        )
        monkeypatch.setattr("ocd.gates.scan_secrets.scan_secrets", lambda staged=True: 0)
        monkeypatch.setattr("ocd.gates.check._staged_files", lambda ext: [])
        monkeypatch.setattr("ocd.gates.check._no_local_config_staged", lambda: (True, "ok"))
        assert run_check() == 0

    def test_branch_failure_fails(self, monkeypatch):
        monkeypatch.setattr(
            subprocess, "run", lambda *a, **kw: MagicMock(stdout="main\n", returncode=0)
        )
        monkeypatch.setattr(
            "ocd.routing.standards.verify_standards_hash",
            lambda: {"match": True, "version": "1.0", "computed_hash": "abc"},
        )
        monkeypatch.setattr("ocd.gates.scan_secrets.scan_secrets", lambda staged=True: 0)
        monkeypatch.setattr("ocd.gates.check._staged_files", lambda ext: [])
        monkeypatch.setattr("ocd.gates.check._no_local_config_staged", lambda: (True, "ok"))
        assert run_check() == 1

    def test_local_config_failure_fails(self, monkeypatch):
        monkeypatch.setattr(
            subprocess, "run", lambda *a, **kw: MagicMock(stdout="feature\n", returncode=0)
        )
        monkeypatch.setattr(
            "ocd.routing.standards.verify_standards_hash",
            lambda: {"match": True, "version": "1.0", "computed_hash": "abc"},
        )
        monkeypatch.setattr("ocd.gates.scan_secrets.scan_secrets", lambda staged=True: 0)
        monkeypatch.setattr("ocd.gates.check._staged_files", lambda ext: [])
        monkeypatch.setattr(
            "ocd.gates.check._no_local_config_staged",
            lambda: (False, "local config staged"),
        )
        assert run_check() == 1
