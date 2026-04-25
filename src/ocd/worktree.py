"""Git worktree lifecycle management for isolated development.

Provides `ocd worktree new/list/remove/status` commands. Worktrees live
under `.claude/worktrees/` with conventional branch names and slug-based
directory names (branch `feat/add-search` → directory `feat+add-search`).

This module is separate from `ocd.fix.autofix`, which has its own
worktree lifecycle for autonomous fix loops (timestamp branches,
BRANCH.md metadata, intent tracking).
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from ocd.config import PROJECT_ROOT, WORKTREES_DIR

_VALID_PREFIXES = ("feat", "fix", "refactor", "experiment", "docs", "test", "ci", "chore")


@dataclass(frozen=True)
class WorktreeInfo:
    """Metadata for a managed worktree."""

    path: Path
    branch: str
    slug: str


def run_git(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run a git command in the given directory."""
    return subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        cwd=str(cwd),
        timeout=30,
    )


def _is_in_worktree() -> bool:
    """Check if the current working directory is inside a git worktree."""
    result = run_git("rev-parse", "--is-inside-work-tree", cwd=PROJECT_ROOT)
    if result.returncode != 0:
        return False
    # In a worktree, the git dir contains "worktrees" in its path
    dir_result = run_git("rev-parse", "--git-dir", cwd=PROJECT_ROOT)
    if dir_result.returncode != 0:
        return False
    return ".claude/worktrees" in dir_result.stdout or "/worktrees/" in dir_result.stdout


def _branch_to_slug(branch: str) -> str:
    """Convert a branch name to a directory slug (replace / with +)."""
    return branch.replace("/", "+")


def new_worktree(description: str, *, prefix: str = "feat") -> WorktreeInfo:
    """Create a new git worktree for development.

    Args:
        description: Short kebab-case description (e.g., "add-search-index").
        prefix: Conventional branch prefix (feat, fix, refactor, etc.).

    Returns:
        WorktreeInfo with the new worktree's path, branch, and slug.

    Raises:
        SystemExit: If already in a worktree, branch exists, or git fails.
    """
    if _is_in_worktree():
        print(
            "Error: already inside a worktree — nested worktrees are not allowed.", file=sys.stderr
        )
        sys.exit(1)

    if prefix not in _VALID_PREFIXES:
        print(
            f"Error: invalid prefix '{prefix}'. Must be one of: {', '.join(_VALID_PREFIXES)}",
            file=sys.stderr,
        )
        sys.exit(1)

    branch = f"{prefix}/{description}"
    slug = _branch_to_slug(branch)
    worktree_path = WORKTREES_DIR / slug

    if worktree_path.exists():
        print(f"Error: worktree directory already exists: {worktree_path}", file=sys.stderr)
        sys.exit(1)

    WORKTREES_DIR.mkdir(parents=True, exist_ok=True)

    result = run_git("worktree", "add", "-b", branch, str(worktree_path), "HEAD", cwd=PROJECT_ROOT)
    if result.returncode != 0:
        print(f"Error: git worktree add failed:\n{result.stderr.strip()}", file=sys.stderr)
        sys.exit(1)

    print(f"Created worktree: {worktree_path}")
    print(f"Branch: {branch}")
    print(f"cd {worktree_path}")

    return WorktreeInfo(path=worktree_path, branch=branch, slug=slug)


def list_worktrees() -> list[WorktreeInfo]:
    """List all managed worktrees under WORKTREES_DIR.

    Uses `git worktree list --porcelain` for reliable discovery.
    """
    result = run_git("worktree", "list", "--porcelain", cwd=PROJECT_ROOT)
    if result.returncode != 0:
        return []

    worktrees: list[WorktreeInfo] = []
    current_path: Path | None = None
    current_branch: str = ""

    for line in result.stdout.strip().splitlines():
        if line.startswith("worktree "):
            current_path = Path(line[len("worktree ") :])
            current_branch = ""
        elif line.startswith("branch ") and current_path is not None:
            refs_prefix = "refs/heads/"
            raw = line[len("branch ") :]
            current_branch = raw[len(refs_prefix) :] if raw.startswith(refs_prefix) else raw
        elif line == "" and current_path is not None:
            if current_path.is_relative_to(WORKTREES_DIR):
                slug = current_path.name
                worktrees.append(WorktreeInfo(path=current_path, branch=current_branch, slug=slug))
            current_path = None
            current_branch = ""

    # Handle last entry if file doesn't end with blank line
    if current_path is not None and current_path.is_relative_to(WORKTREES_DIR):
        slug = current_path.name
        worktrees.append(WorktreeInfo(path=current_path, branch=current_branch, slug=slug))

    return worktrees


def remove_worktree(slug: str, *, force: bool = False) -> bool:
    """Remove a worktree and its branch by slug.

    Args:
        slug: Worktree directory name (e.g., "feat+add-search").
        force: Force removal even if the worktree has uncommitted changes.

    Returns:
        True if removal succeeded, False otherwise.
    """
    worktree_path = WORKTREES_DIR / slug
    if not worktree_path.exists():
        print(f"Error: worktree not found: {slug}", file=sys.stderr)
        return False

    # Find the branch name from git worktree list
    branch = ""
    for wt in list_worktrees():
        if wt.slug == slug:
            branch = wt.branch
            break

    force_args = ["--force"] if force else []
    result = run_git("worktree", "remove", *force_args, str(worktree_path), cwd=PROJECT_ROOT)
    if result.returncode != 0:
        print(f"Error: {result.stderr.strip()}", file=sys.stderr)
        return False

    if branch:
        run_git("branch", "-D", branch, cwd=PROJECT_ROOT)

    print(f"Removed worktree: {slug} (branch: {branch})")
    return True


def worktree_status() -> dict[str, str]:
    """Show the current worktree context.

    Returns a dict with 'location', 'branch', and 'path' keys.
    """
    branch_result = run_git("rev-parse", "--abbrev-ref", "HEAD", cwd=PROJECT_ROOT)
    branch = branch_result.stdout.strip() if branch_result.returncode == 0 else "unknown"

    toplevel_result = run_git("rev-parse", "--show-toplevel", cwd=PROJECT_ROOT)
    toplevel = toplevel_result.stdout.strip() if toplevel_result.returncode == 0 else ""

    in_worktree = WORKTREES_DIR in Path(toplevel).parents or Path(toplevel).is_relative_to(
        WORKTREES_DIR.parent
    )

    if in_worktree:
        return {"location": "worktree", "branch": branch, "path": toplevel}

    return {"location": "main", "branch": branch, "path": str(PROJECT_ROOT)}
