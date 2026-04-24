"""Tests for ocd.worktree — git worktree lifecycle management."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from ocd.worktree import (
    WorktreeInfo,
    _branch_to_slug,
    list_worktrees,
    new_worktree,
    remove_worktree,
    worktree_status,
)

# ── Unit tests ────────────────────────────────────────────────────────────────


class TestBranchToSlug:
    """Slug conversion replaces / with + in branch names."""

    def test_feat_branch(self) -> None:
        assert _branch_to_slug("feat/add-search") == "feat+add-search"

    def test_fix_branch(self) -> None:
        assert _branch_to_slug("fix/parse-error") == "fix+parse-error"

    def test_nested_slashes(self) -> None:
        assert _branch_to_slug("feat/add/search") == "feat+add+search"

    def test_no_slash(self) -> None:
        assert _branch_to_slug("main") == "main"


class TestWorktreeInfo:
    """Frozen dataclass holds path, branch, and slug."""

    def test_frozen(self) -> None:
        wt = WorktreeInfo(path=Path("/tmp/test"), branch="feat/test", slug="feat+test")
        with pytest.raises(AttributeError):
            wt.branch = "other"  # type: ignore[misc]

    def test_fields(self) -> None:
        wt = WorktreeInfo(path=Path("/tmp/test"), branch="feat/test", slug="feat+test")
        assert wt.path == Path("/tmp/test")
        assert wt.branch == "feat/test"
        assert wt.slug == "feat+test"


# ── Integration tests (require git) ───────────────────────────────────────────


@pytest.fixture
def worktree_env(tmp_git_repo: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Set up a temporary git repo with worktree support for testing."""
    worktrees_dir = tmp_git_repo / ".claude" / "worktrees"
    worktrees_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("ocd.worktree.WORKTREES_DIR", worktrees_dir)
    monkeypatch.setattr("ocd.worktree.PROJECT_ROOT", tmp_git_repo)
    return tmp_git_repo


class TestNewWorktree:
    """Creating a new worktree adds branch and directory."""

    def test_creates_branch_and_directory(
        self, worktree_env: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        result = new_worktree("add-search", prefix="feat")
        expected_path = worktree_env / ".claude" / "worktrees" / "feat+add-search"
        assert result.path == expected_path
        assert result.branch == "feat/add-search"
        assert result.slug == "feat+add-search"
        assert expected_path.is_dir()

        # Verify the branch exists
        branches = subprocess.run(
            ["git", "branch", "--list", "feat/add-search"],
            cwd=str(worktree_env),
            capture_output=True,
            text=True,
        )
        assert "feat/add-search" in branches.stdout

    def test_default_prefix_is_feat(self, worktree_env: Path) -> None:
        result = new_worktree("new-feature")
        assert result.branch == "feat/new-feature"

    def test_custom_prefix(self, worktree_env: Path) -> None:
        result = new_worktree("parse-bug", prefix="fix")
        assert result.branch == "fix/parse-bug"
        assert result.slug == "fix+parse-bug"

    def test_rejects_nested_worktree(
        self, worktree_env: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Simulate being inside a worktree by making _is_in_worktree return True
        monkeypatch.setattr("ocd.worktree._is_in_worktree", lambda: True)
        with pytest.raises(SystemExit):
            new_worktree("nested-branch")

    def test_rejects_invalid_prefix(self, worktree_env: Path) -> None:
        with pytest.raises(SystemExit):
            new_worktree("bad-branch", prefix="invalid")

    def test_rejects_duplicate_worktree(self, worktree_env: Path) -> None:
        new_worktree("existing-branch")
        with pytest.raises(SystemExit):
            new_worktree("existing-branch")

    def test_slug_replaces_slash_with_plus(self, worktree_env: Path) -> None:
        result = new_worktree("some-feature", prefix="refactor")
        assert result.slug == "refactor+some-feature"


class TestListWorktrees:
    """Listing worktrees discovers those under .claude/worktrees/."""

    def test_list_empty(self, worktree_env: Path) -> None:
        result = list_worktrees()
        assert result == []

    def test_list_returns_created_worktree(self, worktree_env: Path) -> None:
        created = new_worktree("test-feature", prefix="feat")
        listed = list_worktrees()
        assert len(listed) == 1
        assert listed[0].slug == created.slug
        assert listed[0].branch == created.branch

    def test_list_multiple_worktrees(self, worktree_env: Path) -> None:
        new_worktree("feature-a", prefix="feat")
        new_worktree("bug-b", prefix="fix")
        listed = list_worktrees()
        assert len(listed) == 2
        slugs = {wt.slug for wt in listed}
        assert "feat+feature-a" in slugs
        assert "fix+bug-b" in slugs


class TestRemoveWorktree:
    """Removing a worktree cleans up directory and branch."""

    def test_remove_worktree_cleans_up(self, worktree_env: Path) -> None:
        created = new_worktree("to-remove", prefix="feat")
        assert created.path.is_dir()

        ok = remove_worktree("feat+to-remove")
        assert ok is True
        assert not created.path.exists()

    def test_remove_worktree_force(self, worktree_env: Path) -> None:
        created = new_worktree("dirty-work", prefix="feat")

        # Create a dirty file in the worktree
        (created.path / "dirty.txt").write_text("uncommitted")

        ok = remove_worktree("feat+dirty-work", force=True)
        assert ok is True

    def test_remove_not_found(self, worktree_env: Path) -> None:
        ok = remove_worktree("nonexistent-slug")
        assert ok is False


class TestWorktreeStatus:
    """Status reports main or worktree context."""

    def test_status_on_main(self, worktree_env: Path) -> None:
        info = worktree_status()
        assert info["location"] == "main"
        assert "branch" in info

    def test_status_shows_branch(self, worktree_env: Path) -> None:
        info = worktree_status()
        assert "branch" in info
