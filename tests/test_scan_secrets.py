"""Tests for ocd.scan_secrets — gitleaks wrapper."""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock

from ocd.scan_secrets import scan_secrets


class TestScanSecrets:
    """scan_secrets() runs gitleaks in protect or detect mode."""

    def test_staged_mode_uses_protect(self, monkeypatch):
        calls = []

        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            r = MagicMock()
            r.returncode = 0
            return r

        monkeypatch.setattr(subprocess, "run", fake_run)
        monkeypatch.setattr("shutil.which", lambda _: "/usr/bin/gitleaks")
        scan_secrets(staged=True)
        assert any("protect" in c for c in calls)
        assert any("--staged" in c for c in calls)

    def test_detect_mode_uses_source(self, monkeypatch):
        calls = []

        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            r = MagicMock()
            r.returncode = 0
            return r

        monkeypatch.setattr(subprocess, "run", fake_run)
        monkeypatch.setattr("shutil.which", lambda _: "/usr/bin/gitleaks")
        scan_secrets(staged=False, source=".")
        assert any("detect" in c for c in calls)
        assert any("--source" in c for c in calls)

    def test_returns_0_when_clean(self, monkeypatch):
        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: MagicMock(returncode=0))
        monkeypatch.setattr("shutil.which", lambda _: "/usr/bin/gitleaks")
        assert scan_secrets(staged=True) == 0

    def test_returns_1_when_secrets_found(self, monkeypatch):
        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: MagicMock(returncode=1))
        monkeypatch.setattr("shutil.which", lambda _: "/usr/bin/gitleaks")
        assert scan_secrets(staged=True) == 1

    def test_returns_2_when_not_installed(self, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda _: None)
        assert scan_secrets(staged=True) == 2

    def test_includes_config_flag(self, monkeypatch, tmp_path):
        config = tmp_path / ".gitleaks.toml"
        config.write_text("[extend]\n")
        calls = []

        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            return MagicMock(returncode=0)

        monkeypatch.setattr(subprocess, "run", fake_run)
        monkeypatch.setattr("shutil.which", lambda _: "/usr/bin/gitleaks")
        monkeypatch.setattr("ocd.scan_secrets._GITLEAKS_CONFIG", config)
        scan_secrets(staged=True)
        assert any("-c" in c for c in calls[0])
