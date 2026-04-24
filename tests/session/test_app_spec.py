"""Tests for app_spec — app_spec.txt reading and context injection."""

from pathlib import Path

from ocd.session.app_spec import build_app_spec_context

# ── TestBuildAppSpecContext ─────────────────────────────────────────────


class TestBuildAppSpecContext:
    def test_returns_none_when_no_file(self, mock_config_paths, monkeypatch):
        monkeypatch.setattr(
            "ocd.session.app_spec.APP_SPEC_FILE",
            mock_config_paths / "nonexistent" / "app_spec.txt",
        )
        result = build_app_spec_context()
        assert result is None

    def test_returns_content_when_file_exists(self, mock_config_paths, monkeypatch):
        app_spec_path = mock_config_paths.parent / "app_spec.txt"
        app_spec_path.write_text("My app specification text", encoding="utf-8")
        monkeypatch.setattr("ocd.session.app_spec.APP_SPEC_FILE", app_spec_path)
        result = build_app_spec_context()
        assert result is not None
        assert "My app specification text" in result
        assert "## App Spec" in result

    def test_returns_none_for_empty_file(self, mock_config_paths, monkeypatch):
        app_spec_path = mock_config_paths.parent / "app_spec.txt"
        app_spec_path.write_text("   \n  \n", encoding="utf-8")
        monkeypatch.setattr("ocd.session.app_spec.APP_SPEC_FILE", app_spec_path)
        result = build_app_spec_context()
        assert result is None

    def test_truncates_long_content(self, mock_config_paths, monkeypatch):
        app_spec_path = mock_config_paths.parent / "app_spec.txt"
        long_content = "x" * 5000
        app_spec_path.write_text(long_content, encoding="utf-8")
        monkeypatch.setattr("ocd.session.app_spec.APP_SPEC_FILE", app_spec_path)
        result = build_app_spec_context(max_chars=200)
        assert result is not None
        assert len(result) <= 200
        assert "truncated" in result

    def test_preserves_content_under_limit(self, mock_config_paths, monkeypatch):
        app_spec_path = mock_config_paths.parent / "app_spec.txt"
        content = "Short app spec"
        app_spec_path.write_text(content, encoding="utf-8")
        monkeypatch.setattr("ocd.session.app_spec.APP_SPEC_FILE", app_spec_path)
        result = build_app_spec_context(max_chars=4000)
        assert result is not None
        assert content in result
        assert "truncated" not in result

    def test_returns_none_on_oserror(self, mock_config_paths, monkeypatch):
        app_spec_path = mock_config_paths.parent / "app_spec.txt"
        app_spec_path.write_text("Content", encoding="utf-8")
        monkeypatch.setattr("ocd.session.app_spec.APP_SPEC_FILE", app_spec_path)
        # Make read_text raise OSError to simulate file disappearing between checks

        def _raise_oserror(self, *args, **kwargs):
            raise OSError("gone")

        monkeypatch.setattr(Path, "read_text", _raise_oserror)
        result = build_app_spec_context()
        assert result is None
