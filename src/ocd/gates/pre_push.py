"""Diff-aware pre-push test runner.

Runs only the test files relevant to changed source files, falling back
to the full suite when infrastructure files are modified.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# Files that affect all tests — if changed, run the full suite.
_FULL_SUITE_FILES: frozenset[str] = frozenset(
    {
        "pyproject.toml",
        "tests/conftest.py",
        "src/ocd/config.py",
        "src/ocd/__init__.py",
    }
)


def get_changed_files(base: str = "origin/main") -> list[str]:
    """Return files changed between HEAD and *base*.

    Uses ``git merge-base`` first so only divergent changes are
    included (not changes that also exist on the base branch).
    Falls back to a plain diff if merge-base fails.
    """
    merge = subprocess.run(
        ["git", "merge-base", base, "HEAD"],
        capture_output=True,
        text=True,
    )
    ref = merge.stdout.strip() if merge.returncode == 0 and merge.stdout.strip() else base

    result = subprocess.run(
        ["git", "diff", "--name-only", ref],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return []

    return [f for f in result.stdout.strip().splitlines() if f]


def map_files_to_tests(changed_files: list[str]) -> list[str]:
    """Map changed source files to their test files.

    Returns an empty list when the full suite should be run
    (infrastructure change or no mappings found).
    """
    for f in changed_files:
        if f in _FULL_SUITE_FILES:
            return []

    # Subpackage → test directory mapping
    _SUBPKG_MAP: dict[str, str] = {
        "fix": "fix",
        "gates": "gates",
        "hooks": "hooks",
        "kb": "kb",
        "packaging": "packaging",
        "routing": "routing",
        "session": "session",
    }

    test_files: set[str] = set()

    for f in changed_files:
        if f.startswith("src/ocd/"):
            parts = Path(f).parts
            module = Path(f).stem
            if len(parts) >= 3 and parts[2] in _SUBPKG_MAP:
                test_dir = _SUBPKG_MAP[parts[2]]
                test_files.add(f"tests/{test_dir}/test_{module}.py")
            elif f.endswith(".py"):
                test_files.add(f"tests/test_{module}.py")
        elif f.startswith("tests/") and f.endswith(".py"):
            test_files.add(f)

    return sorted(test_files)


def _run_tests(test_files: list[str]) -> int:
    """Run pytest with the given test files, or the full suite if empty."""
    cmd = [sys.executable, "-m", "pytest", "-q"]
    if test_files:
        cmd.extend(test_files)

    result = subprocess.run(cmd)
    return result.returncode


# ── Public API ────────────────────────────────────────────────────────────


def run_pre_push() -> int:
    """Run diff-aware tests before push.

    Returns:
        0 if tests pass, non-zero on failure.
    """
    # Verify origin/main exists
    remote_check = subprocess.run(
        ["git", "rev-parse", "--verify", "origin/main"],
        capture_output=True,
        text=True,
    )
    if remote_check.returncode != 0:
        print("pre-push: no origin/main, running full suite", file=sys.stderr)
        return _run_tests([])

    changed = get_changed_files("origin/main")
    if not changed:
        print("pre-push: could not determine changed files, running full suite", file=sys.stderr)
        return _run_tests([])

    test_files = map_files_to_tests(changed)
    if not test_files:
        print("pre-push: infrastructure change detected, running full suite", file=sys.stderr)
        return _run_tests([])

    print(
        f"pre-push: running {len(test_files)} test file(s) for {len(changed)} changed file(s)",
        file=sys.stderr,
    )
    rc = _run_tests(test_files)
    if rc != 0:
        print("error: tests failed — push aborted", file=sys.stderr)
    else:
        print("pre-push: tests passed", file=sys.stderr)
    return rc


# ── CLI ──────────────────────────────────────────────────────────────────


def main() -> None:
    """Entry point: run diff-aware tests before push."""
    sys.exit(run_pre_push())


if __name__ == "__main__":
    main()
