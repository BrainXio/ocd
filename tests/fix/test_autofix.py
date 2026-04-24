"""Tests for ocd.fix.autofix — self-corrective fix loops in isolated worktrees."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from ocd.fix.autofix import (
    _GUARD_ENV,
    LoopResult,
    WorktreeInfo,
    _slugify,
    create_worktree,
    list_worktrees,
    main,
    merge_worktree,
    remove_worktree,
)
from ocd.fix.cycle import FixResult

# ── Unit tests (no git required) ────────────────────────────────────────────


class TestSlugify:
    def test_simple(self):
        assert _slugify("fix lint violations") == "fix-lint-violations"

    def test_special_chars(self):
        assert _slugify("Fix: ruff & mypy!!") == "fix-ruff-mypy"

    def test_long_text_truncated(self):
        assert len(_slugify("a" * 100)) == 40

    def test_empty(self):
        assert _slugify("") == ""


class TestWorktreeInfo:
    def test_frozen(self):
        info = WorktreeInfo(path=Path("/tmp/wt"), branch="autofix/test", intent="test")
        with pytest.raises(AttributeError):
            info.branch = "other"  # type: ignore[misc]

    def test_fields(self):
        info = WorktreeInfo(path=Path("/tmp/wt"), branch="autofix/test", intent="test")
        assert info.path == Path("/tmp/wt")
        assert info.branch == "autofix/test"
        assert info.intent == "test"


class TestLoopResult:
    def test_defaults(self):
        r = LoopResult()
        assert r.iterations == 0
        assert r.merged is False
        assert r.result.fixed == []
        assert r.result.remaining == []

    def test_to_json(self):
        r = LoopResult(iterations=3, merged=True, result=FixResult(fixed=["ruff-format"]))
        d = json.loads(r.to_json())
        assert d["iterations"] == 3
        assert d["merged"] is True
        assert d["result"]["fixed"] == ["ruff-format"]


class TestRecursionGuard:
    def test_main_returns_when_env_set(self, monkeypatch):
        monkeypatch.setenv(_GUARD_ENV, "1")
        # Should return immediately without error
        main()
        # If it didn't return early, it would try to parse args and fail
        monkeypatch.delenv(_GUARD_ENV, raising=False)


# ── Integration tests (require git) ──────────────────────────────────────────


class TestWorktreeLifecycle:
    """Tests that create/remove real git worktrees."""

    def test_create_worktree(self, tmp_git_repo, mock_config_paths, monkeypatch):
        # Point worktrees dir inside the temp git repo
        worktrees_dir = tmp_git_repo / ".claude" / "worktrees"
        worktrees_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr("ocd.fix.autofix.WORKTREES_DIR", worktrees_dir)
        monkeypatch.setattr("ocd.fix.autofix.PROJECT_ROOT", tmp_git_repo)

        wt = create_worktree("fix-lint", target="src/ocd/config.py")

        assert wt.branch.startswith("autofix/")
        assert "fix-lint" in wt.branch
        assert (wt.path / "BRANCH.md").exists()

        # Verify BRANCH.md content
        content = (wt.path / "BRANCH.md").read_text()
        assert "fix-lint" in content
        assert "fix-cycle" in content

        # Cleanup
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(wt.path)],
            cwd=str(tmp_git_repo),
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "branch", "-D", wt.branch],
            cwd=str(tmp_git_repo),
            check=True,
            capture_output=True,
        )

    def test_remove_worktree(self, tmp_git_repo, mock_config_paths, monkeypatch):
        worktrees_dir = tmp_git_repo / ".claude" / "worktrees"
        worktrees_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr("ocd.fix.autofix.WORKTREES_DIR", worktrees_dir)
        monkeypatch.setattr("ocd.fix.autofix.PROJECT_ROOT", tmp_git_repo)

        wt = create_worktree("remove-test", target="README.md")
        assert wt.path.is_dir()

        removed = remove_worktree(wt, force=True)
        assert removed is True
        assert not wt.path.is_dir()

    def test_list_worktrees(self, tmp_git_repo, mock_config_paths, monkeypatch):
        worktrees_dir = tmp_git_repo / ".claude" / "worktrees"
        worktrees_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr("ocd.fix.autofix.WORKTREES_DIR", worktrees_dir)
        monkeypatch.setattr("ocd.fix.autofix.PROJECT_ROOT", tmp_git_repo)

        # Initially empty
        assert list_worktrees() == []

        wt = create_worktree("list-test", target="README.md")
        found = list_worktrees()
        assert len(found) == 1
        assert found[0].intent == "list-test"

        # Cleanup
        remove_worktree(wt, force=True)

    def test_merge_worktree(self, tmp_git_repo, mock_config_paths, monkeypatch):
        worktrees_dir = tmp_git_repo / ".claude" / "worktrees"
        worktrees_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr("ocd.fix.autofix.WORKTREES_DIR", worktrees_dir)
        monkeypatch.setattr("ocd.fix.autofix.PROJECT_ROOT", tmp_git_repo)

        wt = create_worktree("merge-test", target="README.md")

        # Make a change in the worktree
        (wt.path / "README.md").write_text("# modified\n")
        subprocess.run(
            ["git", "add", "README.md"],
            cwd=str(wt.path),
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "update readme"],
            cwd=str(wt.path),
            check=True,
            capture_output=True,
        )

        merged = merge_worktree(wt)
        assert merged is True

        # Verify the main tree has the change
        assert (tmp_git_repo / "README.md").read_text() == "# modified\n"

        # Cleanup branch (may already be gone after merge)
        subprocess.run(
            ["git", "branch", "-D", wt.branch],
            cwd=str(tmp_git_repo),
            check=False,
            capture_output=True,
        )


class TestAutofixLog:
    def test_log_file_created(self, tmp_git_repo, mock_config_paths, monkeypatch):
        worktrees_dir = tmp_git_repo / ".claude" / "worktrees"
        worktrees_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.setattr("ocd.fix.autofix.WORKTREES_DIR", worktrees_dir)
        monkeypatch.setattr("ocd.fix.autofix.PROJECT_ROOT", tmp_git_repo)
        monkeypatch.setattr(
            "ocd.fix.autofix.AUTOFIX_LOG", mock_config_paths / "state" / "autofix-loop.jsonl"
        )

        wt = create_worktree("log-test", target="README.md")

        from ocd.fix.autofix import _log_iteration

        _log_iteration(
            "log-test",
            wt.branch,
            1,
            FixResult(fixed=["ruff-format"]),
            True,
            ".claude/worktrees/log-test",
            False,
        )

        log_path = mock_config_paths / "state" / "autofix-loop.jsonl"
        assert log_path.exists()
        lines = log_path.read_text().strip().splitlines()
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["intent"] == "log-test"
        assert entry["iteration"] == 1
        assert entry["converged"] is True
        assert entry["fixed"] == ["ruff-format"]

        # Cleanup
        remove_worktree(wt, force=True)
