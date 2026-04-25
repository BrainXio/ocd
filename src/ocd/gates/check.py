"""Fast local quality gate for pre-commit.

Runs: branch protection, standards verify, staged secret scan,
      staged mdformat check, staged ruff check.
Target: < 10 seconds for typical commits.
"""

from __future__ import annotations

import os
import subprocess
import sys

from ocd.config import PROJECT_ROOT, VENV_BIN

_CLAUDE_DIR = ".claude"


def _no_local_config_staged() -> tuple[bool, str]:
    """Block local-only config files from being committed."""
    LOCAL_CONFIGS = [f"{_CLAUDE_DIR}/settings.local.json"]
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
    )
    staged = [f for f in result.stdout.strip().splitlines() if f]
    found = [f for f in staged if f in LOCAL_CONFIGS]
    if found:
        return False, f"local config staged: {', '.join(found)} — these must not be committed"
    return True, "no local configs staged"


def _branch_protection() -> tuple[bool, str]:
    """Check that we are not committing directly to main."""
    result = subprocess.run(
        ["git", "symbolic-ref", "--short", "HEAD"],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
    )
    branch = result.stdout.strip()
    if branch == "main":
        return False, "commits on main are prohibited — create a feature branch first"
    return True, f"branch: {branch}"


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
        f"computed={result['computed_hash']}) — run 'ocd standards --update'"
    )


def _scan_secrets_staged() -> tuple[bool, str]:
    """Scan staged changes for secrets."""
    from ocd.gates.scan_secrets import scan_secrets

    rc = scan_secrets(staged=True)
    if rc == 0:
        return True, "gitleaks: no secrets detected (staged)"
    if rc == 2:
        return True, "gitleaks: skipped (not installed)"
    return False, "gitleaks: detected potential secrets in staged changes"


def _staged_files(extension: str) -> list[str]:
    """Return staged files matching the given extension."""
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM", f"*{extension}"],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
    )
    return [f for f in result.stdout.strip().splitlines() if f]


def _run_tool(cmd: list[str], label: str) -> tuple[bool, str]:
    """Run a tool command, return (success, summary)."""
    env = os.environ.copy()
    venv_str = str(VENV_BIN)
    if venv_str not in env.get("PATH", ""):
        env["PATH"] = f"{venv_str}:{env.get('PATH', '')}"

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            env=env,
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        return False, f"{label}: timed out"
    except FileNotFoundError:
        return True, f"{label}: skipped (not installed)"

    output = (result.stderr + result.stdout).strip()
    if result.returncode == 0:
        return True, f"{label}: ok"
    return False, f"{label}: issues found\n{output}"


def _mdformat_check_staged() -> tuple[bool, str]:
    """Run mdformat --check on staged markdown files."""
    md_files = _staged_files(".md")
    if not md_files:
        return True, "mdformat: no staged markdown files"
    return _run_tool(["mdformat", "--check", *md_files], "mdformat")


def _ruff_check_staged() -> tuple[bool, str]:
    """Run ruff check on staged Python files."""
    py_files = _staged_files(".py")
    if not py_files:
        return True, "ruff: no staged Python files"
    return _run_tool(["ruff", "check", *py_files], "ruff")


def run_check() -> int:
    """Run all fast local quality checks.

    Returns 0 if all checks pass, 1 if any fail.
    """
    checks = [
        ("branch-protection", _branch_protection),
        ("local-config-guard", _no_local_config_staged),
        ("standards-verify", _standards_verify),
        ("secret-scan", _scan_secrets_staged),
        ("mdformat-check", _mdformat_check_staged),
        ("ruff-check", _ruff_check_staged),
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
        print("All checks passed.")
        return 0
    print("Some checks failed. Fix issues before committing.", file=sys.stderr)
    return 1


def main() -> None:
    """Entry point for ocd check."""
    sys.exit(run_check())
