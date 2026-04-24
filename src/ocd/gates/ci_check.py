"""Full local mirror of CI quality gates.

Runs all CI checks locally: standards verify, commit message check,
secret scan, ruff, mypy, mdformat, yamllint, shellcheck, semgrep, pytest.

Usage:
    ocd hook ci-check              # full suite
    ocd hook ci-check --fast       # skip full pytest, use diff-aware tests only
    ocd hook ci-check --commit-range origin/main..HEAD  # include AI attribution check
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from collections.abc import Callable

from ocd.config import PROJECT_ROOT, VENV_BIN


def _env_with_venv() -> dict[str, str]:
    """Build environment dict with venv bin on PATH."""
    env = dict(os.environ)
    venv_str = str(VENV_BIN)
    if venv_str not in env.get("PATH", ""):
        env["PATH"] = f"{venv_str}:{env.get('PATH', '')}"
    return env


def _tool_available(binary: str) -> bool:
    """Check if a tool is available in venv or on PATH."""
    return (VENV_BIN / binary).exists() or shutil.which(binary) is not None


def _standards_verify() -> tuple[bool, str]:
    """Verify standards hash matches content."""
    from ocd.routing.standards import verify_standards_hash

    result = verify_standards_hash()
    if result.get("error"):
        return False, f"standards: {result['error']}"
    if result["match"]:
        return True, f"standards: v{result['version']} [{result['computed_hash']}]"
    return False, (
        f"standards: hash mismatch (stored={result['stored_hash']}, "
        f"computed={result['computed_hash']})"
    )


def _verify_commit_messages(range_spec: str | None = None) -> tuple[bool, str]:
    """Check commit messages for AI attribution."""
    from ocd.gates.verify_commit import check_commit_range

    if not range_spec:
        return True, "commit-messages: skipped (no range specified)"
    violations = check_commit_range(range_spec)
    if violations:
        lines = [f"{h[:8]}: {line[:60]}" for h, _, line in violations[:5]]
        return False, "AI attribution found in commits:\n" + "\n".join(lines)
    return True, "commit-messages: no AI attribution"


def _scan_secrets_full() -> tuple[bool, str]:
    """Full repository secret scan."""
    from ocd.gates.scan_secrets import scan_secrets

    rc = scan_secrets(staged=False, source=".")
    if rc == 0:
        return True, "gitleaks: no secrets detected"
    if rc == 2:
        return True, "gitleaks: skipped (not installed)"
    return False, "gitleaks: detected potential secrets"


def _ruff_check() -> tuple[bool, str]:
    """Run ruff check on source and tests."""
    if not _tool_available("ruff"):
        return True, "ruff check: skipped (not installed)"
    result = subprocess.run(
        ["ruff", "check", "src/ocd/", "tests/"],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
        env=_env_with_venv(),
    )
    output = (result.stderr + result.stdout).strip()
    if result.returncode == 0:
        return True, "ruff check: clean"
    return False, f"ruff check: issues found\n{output}"


def _ruff_format_check() -> tuple[bool, str]:
    """Run ruff format --check on source and tests."""
    if not _tool_available("ruff"):
        return True, "ruff format: skipped (not installed)"
    result = subprocess.run(
        ["ruff", "format", "--check", "src/ocd/", "tests/"],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
        env=_env_with_venv(),
    )
    output = (result.stderr + result.stdout).strip()
    if result.returncode == 0:
        return True, "ruff format: clean"
    return False, f"ruff format: issues found\n{output}"


def _mypy() -> tuple[bool, str]:
    """Run mypy with strict checking."""
    if not _tool_available("mypy"):
        return True, "mypy: skipped (not installed)"
    result = subprocess.run(
        ["mypy", "src/ocd/", "--strict"],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
        env=_env_with_venv(),
    )
    output = (result.stderr + result.stdout).strip()
    if result.returncode == 0:
        return True, "mypy: clean"
    return False, f"mypy: type errors found\n{output}"


def _mdformat_check() -> tuple[bool, str]:
    """Run mdformat --check on documentation paths."""
    if not _tool_available("mdformat"):
        return True, "mdformat: skipped (not installed)"
    result = subprocess.run(
        [
            "mdformat",
            "--check",
            "README.md",
            "docs/",
            ".claude/skills/",
            ".claude/agents/",
            ".claude/rules/",
            "docs/reference/skills/",
            "docs/reference/agents/",
        ],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
        env=_env_with_venv(),
    )
    output = (result.stderr + result.stdout).strip()
    if result.returncode == 0:
        return True, "mdformat: all files formatted correctly"
    return False, f"mdformat: formatting issues\n{output}"


def _yamllint() -> tuple[bool, str]:
    """Run yamllint on workflow files."""
    if not _tool_available("yamllint"):
        return True, "yamllint: skipped (not installed)"
    result = subprocess.run(
        ["yamllint", "-f", "parsable", ".github/workflows/", ".yamllint"],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
    )
    output = (result.stderr + result.stdout).strip()
    if result.returncode == 0:
        return True, "yamllint: clean"
    return False, f"yamllint: issues found\n{output}"


def _shellcheck() -> tuple[bool, str]:
    """Run shellcheck on git hooks."""
    if not _tool_available("shellcheck"):
        return True, "shellcheck: skipped (not installed)"
    result = subprocess.run(
        [
            "shellcheck",
            ".githooks/commit-msg",
            ".githooks/pre-commit",
            ".githooks/pre-push",
            ".githooks/setup-hooks.sh",
        ],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
    )
    output = (result.stderr + result.stdout).strip()
    if result.returncode == 0:
        return True, "shellcheck: clean"
    return False, f"shellcheck: issues found\n{output}"


def _pytest(fast: bool = False) -> tuple[bool, str]:
    """Run pytest, either full suite or diff-aware subset."""
    if not _tool_available("pytest"):
        return True, "pytest: skipped (not installed)"

    if fast:
        from ocd.gates.pre_push import get_changed_files, map_files_to_tests

        remote_check = subprocess.run(
            ["git", "rev-parse", "--verify", "origin/main"],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
        )
        if remote_check.returncode != 0:
            return True, "pytest (fast): no origin/main, skipping delta tests"
        changed = get_changed_files("origin/main")
        if not changed:
            return True, "pytest (fast): no changed files detected"
        test_files = map_files_to_tests(changed)
        if not test_files:
            return True, "pytest (fast): infrastructure change, full suite recommended"
        cmd = [sys.executable, "-m", "pytest", "-q", *test_files]
    else:
        cmd = [sys.executable, "-m", "pytest", "-v"]

    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT), env=_env_with_venv())
    if result.returncode == 0:
        return True, "pytest: all tests passed"
    return False, "pytest: some tests failed"


def run_ci_check(fast: bool = False, commit_range: str | None = None) -> int:
    """Run all CI quality checks.

    Returns 0 if all checks pass, 1 if any fail.
    """
    checks: list[tuple[str, Callable[[], tuple[bool, str]]]] = [
        ("standards-verify", lambda: _standards_verify()),
        ("commit-messages", lambda: _verify_commit_messages(commit_range)),
        ("secret-scan", lambda: _scan_secrets_full()),
        ("ruff-check", lambda: _ruff_check()),
        ("ruff-format", lambda: _ruff_format_check()),
        ("mypy", lambda: _mypy()),
        ("mdformat-check", lambda: _mdformat_check()),
        ("yamllint", lambda: _yamllint()),
        ("shellcheck", lambda: _shellcheck()),
        ("pytest", lambda: _pytest(fast=fast)),
    ]

    all_passed = True
    for name, check_fn in checks:
        passed, message = check_fn()
        marker = "ok" if passed else "FAIL"
        print(f"  [{marker}] {name}: {message}")
        if not passed:
            all_passed = False

    print()
    if all_passed:
        print("All CI checks passed.")
        return 0
    print("Some CI checks failed.", file=sys.stderr)
    return 1


def main() -> None:
    """Entry point for ocd ci-check."""
    parser = argparse.ArgumentParser(description="Full local CI mirror")
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Skip full pytest, use diff-aware test selection",
    )
    parser.add_argument(
        "--commit-range",
        help="Git range for AI attribution check (e.g. origin/main..HEAD)",
    )
    args = parser.parse_args()
    sys.exit(run_ci_check(fast=args.fast, commit_range=args.commit_range))
