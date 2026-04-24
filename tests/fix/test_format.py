"""Tests for ocd.fix.format — formatter registry, tool detection, and result reporting."""

from unittest.mock import MagicMock, patch

from ocd.fix.format import (
    FORMATTERS,
    _config_present,
    _find_files,
    _format_install_hint,
    _has_matching_files,
    _tool_available,
    run_formatters,
)


class TestFormattersRegistry:
    def test_registry_not_empty(self):
        assert len(FORMATTERS) > 0

    def test_each_entry_has_six_fields(self):
        for entry in FORMATTERS:
            assert len(entry) == 6, f"Entry {entry[0]} has {len(entry)} fields, expected 6"

    def test_names_are_unique(self):
        names = [e[0] for e in FORMATTERS]
        assert len(names) == len(set(names))

    def test_python_formatters_present(self):
        names = {e[0] for e in FORMATTERS}
        assert "ruff-format" in names
        assert "ruff-fix" in names

    def test_mdformat_present(self):
        names = {e[0] for e in FORMATTERS}
        assert "mdformat" in names

    def test_commands_are_lists_or_callables(self):
        for entry in FORMATTERS:
            name, command = entry[0], entry[1]
            assert isinstance(command, list) or callable(command), (
                f"{name} command should be list or callable, got {type(command)}"
            )

    def test_stylelint_command_is_callable(self):
        names = {e[0]: e[1] for e in FORMATTERS}
        assert callable(names["stylelint"])


class TestFindFiles:
    def test_finds_python_files(self, monkeypatch, tmp_path):
        monkeypatch.setattr("ocd.fix.format.PROJECT_ROOT", tmp_path)
        (tmp_path / "src.py").write_text("pass")
        result = _find_files(str(tmp_path), ("py",))
        assert "src.py" in result

    def test_ignores_venv(self, monkeypatch, tmp_path):
        monkeypatch.setattr("ocd.fix.format.PROJECT_ROOT", tmp_path)
        venv = tmp_path / ".venv" / "lib"
        venv.mkdir(parents=True)
        (venv / "site.py").write_text("pass")
        result = _find_files(str(tmp_path), ("py",))
        assert "site.py" not in result

    def test_no_matching_files(self, monkeypatch, tmp_path):
        monkeypatch.setattr("ocd.fix.format.PROJECT_ROOT", tmp_path)
        result = _find_files(str(tmp_path), ("xyz",))
        assert result == []


class TestToolAvailable:
    def test_npx_available(self, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda cmd: "/usr/bin/npx" if cmd == "npx" else None)
        assert _tool_available(["npx", "prettier", "--write", "."]) is True

    def test_npx_unavailable(self, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda _: None)
        assert _tool_available(["npx", "prettier", "--write", "."]) is False

    def test_venv_tool(self, monkeypatch, tmp_path):
        """A binary in VENV_BIN should be found."""
        fake_bin = tmp_path / "ruff"
        fake_bin.write_text("")
        monkeypatch.setattr("ocd.fix.format.VENV_BIN", tmp_path)
        assert _tool_available(["ruff", "format", "src/"]) is True

    def test_missing_tool(self, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda _: None)
        fake_dir = MagicMock()
        fake_dir.__truediv__ = lambda s, o: MagicMock(exists=lambda: False)
        monkeypatch.setattr("ocd.fix.format.VENV_BIN", fake_dir)
        assert _tool_available(["nonexistent_tool_xyz"]) is False

    def test_callable_command_extracts_binary(self, monkeypatch):
        monkeypatch.setattr("shutil.which", lambda _: None)

        # A callable command — _tool_available should extract the binary name
        def fake_cmd(root: str) -> list[str]:
            return ["npx", "stylelint", "--fix"]

        assert _tool_available(fake_cmd) is False  # npx not available


class TestConfigPresent:
    def test_none_config_always_present(self):
        assert _config_present(None) is True

    def test_existing_config(self):
        assert _config_present(["pyproject.toml"]) is True

    def test_missing_config(self):
        assert _config_present(["nonexistent_config_xyz.yml"]) is False

    def test_any_config_sufficient(self):
        assert _config_present(["nonexistent_xyz.yml", "pyproject.toml"]) is True


class TestHasMatchingFiles:
    def test_none_extensions_always_true(self):
        assert _has_matching_files(None) is True

    def test_matching_extension_found(self):
        assert _has_matching_files(("py",)) is True

    def test_no_matching_extension(self, monkeypatch, tmp_path):
        monkeypatch.setattr("ocd.fix.format.PROJECT_ROOT", tmp_path)
        assert _has_matching_files(("xyz123",)) is False


class TestFormatInstallHint:
    def test_pip_hint(self):
        entry = ("ruff-format", ["ruff", "format", "src/", "tests/"], None, None, 30, "pip:ruff")
        result = _format_install_hint(entry)
        assert "uv" in result
        assert "ruff" in result

    def test_npm_hint(self):
        entry = (
            "prettier",
            ["npx", "prettier", "--write", "."],
            None,
            (".prettierrc",),
            30,
            "npm:prettier",
        )
        result = _format_install_hint(entry)
        assert "npm" in result
        assert "prettier" in result


class TestRunFormatters:
    def test_returns_zero_on_all_ok(self, monkeypatch, capsys):
        monkeypatch.setattr("ocd.fix.format._tool_available", lambda _: True)
        monkeypatch.setattr("ocd.fix.format._config_present", lambda _: True)
        monkeypatch.setattr("ocd.fix.format._has_matching_files", lambda _: True)
        with patch("subprocess.run", return_value=MagicMock(returncode=0, stdout="", stderr="")):
            result = run_formatters()
        assert result == 0

    def test_returns_one_on_error(self, monkeypatch, capsys):
        monkeypatch.setattr("ocd.fix.format._tool_available", lambda _: True)
        monkeypatch.setattr("ocd.fix.format._config_present", lambda _: True)
        monkeypatch.setattr("ocd.fix.format._has_matching_files", lambda _: True)
        with patch(
            "subprocess.run",
            return_value=MagicMock(returncode=1, stdout="error", stderr=""),
        ):
            result = run_formatters()
        assert result == 1

    def test_reports_missing_tools(self, monkeypatch, capsys):
        monkeypatch.setattr("ocd.fix.format._tool_available", lambda _: False)
        result = run_formatters()
        output = capsys.readouterr().out
        assert "skipped" in output
        assert result == 0

    def test_reports_missing_config(self, monkeypatch, capsys):
        monkeypatch.setattr("ocd.fix.format._tool_available", lambda _: True)
        monkeypatch.setattr("ocd.fix.format._config_present", lambda _: False)
        result = run_formatters()
        output = capsys.readouterr().out
        assert "no config" in output
        assert result == 0

    def test_skips_when_no_matching_files(self, monkeypatch, capsys):
        monkeypatch.setattr("ocd.fix.format._tool_available", lambda _: True)
        monkeypatch.setattr("ocd.fix.format._config_present", lambda _: True)
        monkeypatch.setattr("ocd.fix.format._has_matching_files", lambda _: False)
        result = run_formatters()
        output = capsys.readouterr().out
        assert "no matching files" in output
        assert result == 0
