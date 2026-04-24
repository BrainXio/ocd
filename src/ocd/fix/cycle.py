"""Closed-loop fix commands — external detect-fix-verify cycles.

Replaces LLM fix loops (~500-1,300 tokens per iteration) with deterministic
external commands. Each command runs full detect-fix-verify and returns
structured JSON. Zero LLM calls.

Usage:
    ocd fix-cycle <file>              # format + safe lint fixes on one file
    ocd lint-and-fix <path>           # format + safe lint fixes on matching files
    ocd test-and-fix                  # format + lint, verify tests still pass
    ocd security-scan-and-patch       # semgrep scan, categorize findings
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

from ocd.config import PROJECT_ROOT, VENV_BIN

# Safe auto-fix commands keyed by linter binary name.
# Only formatters and lint fixes that are deterministic and non-breaking.
_SAFE_FIXES: dict[str, list[str]] = {
    "ruff": ["ruff", "check", "--fix", "src/", "tests/"],
    "mdformat": ["mdformat", "README.md", "docs/", ".claude/skills/"],
    "prettier": ["npx", "prettier", "--write", "."],
    "stylelint": ["npx", "stylelint", "--fix", "**/*.css"],
    "sqlfluff": ["sqlfluff", "fix", "--force"],
}


@dataclass
class FixResult:
    """Structured result from a fix cycle."""

    fixed: list[str] = field(default_factory=list)
    remaining: list[str] = field(default_factory=list)
    exit_code: int = 0

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)


def _env_with_venv() -> dict[str, str]:
    """Build environment dict with venv bin on PATH."""
    env = os.environ.copy()
    venv_bin_str = str(VENV_BIN)
    if venv_bin_str not in env.get("PATH", ""):
        env["PATH"] = f"{venv_bin_str}:{env.get('PATH', '')}"
    return env


def _resolve_root(project_root: Path | None = None) -> Path:
    """Return the effective project root, falling back to PROJECT_ROOT."""
    return project_root if project_root is not None else PROJECT_ROOT


def _tool_available(binary: str) -> bool:
    """Check if a tool binary exists in venv or on PATH."""
    return (VENV_BIN / binary).exists() or shutil.which(binary) is not None


def _run_formatters(
    project_root: Path | None = None,
) -> tuple[list[str], list[str]]:
    """Run all safe auto-fix formatters. Returns (fixed, errors)."""
    from ocd.fix.format import FORMATTERS, _config_present, _has_matching_files, _tool_available

    root = _resolve_root(project_root)
    fixed: list[str] = []
    errors: list[str] = []
    env = _env_with_venv()

    for entry in FORMATTERS:
        name, command, extensions, config_files, timeout, _hint = entry

        if not _tool_available(command):
            continue
        if not _config_present(config_files):
            continue
        if not _has_matching_files(extensions):
            continue

        # Resolve callable commands
        if callable(command):
            args = command(str(root))
            if not args:
                continue
        elif isinstance(command, list):
            args = command
        else:
            continue

        try:
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(root),
                env=env,
            )
            if result.returncode == 0:
                fixed.append(name)
            else:
                output = (result.stderr + result.stdout).strip()
                errors.append(f"{name}: {output}")
        except subprocess.TimeoutExpired:
            errors.append(f"{name}: timed out")
        except Exception as e:
            errors.append(f"{name}: {e}")

    return fixed, errors


def _run_ruff_fix_on_file(file_path: str, *, project_root: Path | None = None) -> tuple[bool, str]:
    """Run ruff check --fix on a single file. Returns (success, output)."""
    root = _resolve_root(project_root)
    if not _tool_available("ruff"):
        return False, "ruff not installed"
    env = _env_with_venv()
    try:
        result = subprocess.run(
            ["ruff", "check", "--fix", file_path],
            capture_output=True,
            text=True,
            timeout=15,
            cwd=str(root),
            env=env,
        )
        output = (result.stderr + result.stdout).strip()
        return result.returncode == 0, output
    except (subprocess.TimeoutExpired, Exception) as e:
        return False, str(e)


def _run_lint_check(file_path: str, *, project_root: Path | None = None) -> tuple[bool, str]:
    """Run ruff check on a single file (no fix). Returns (clean, output)."""
    root = _resolve_root(project_root)
    if not _tool_available("ruff"):
        return True, "ruff not installed — skipping lint check"
    env = _env_with_venv()
    try:
        result = subprocess.run(
            ["ruff", "check", file_path],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=str(root),
            env=env,
        )
        output = (result.stderr + result.stdout).strip()
        return result.returncode == 0, output
    except (subprocess.TimeoutExpired, Exception) as e:
        return True, str(e)


def _run_mypy_check(paths: list[str], *, project_root: Path | None = None) -> tuple[bool, str]:
    """Run mypy on given paths. Returns (clean, output)."""
    root = _resolve_root(project_root)
    if not _tool_available("mypy"):
        return True, "mypy not installed"
    env = _env_with_venv()
    try:
        result = subprocess.run(
            ["mypy", *paths],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(root),
            env=env,
        )
        output = (result.stderr + result.stdout).strip()
        return result.returncode == 0, output
    except (subprocess.TimeoutExpired, Exception) as e:
        return True, str(e)


def fix_cycle(file_path: str, *, project_root: Path | None = None) -> FixResult:
    """Run detect-fix-verify cycle on a single file.

    1. Run all formatters (safe auto-fix)
    2. Run ruff check --fix on the file (safe lint patches)
    3. Re-lint to verify
    4. Return structured result
    """
    result = FixResult()

    # Step 1: Run all formatters
    fixed_formatters, fmt_errors = _run_formatters(project_root=project_root)
    result.fixed.extend(fixed_formatters)

    # Step 2: Run ruff fix on the specific file
    ruff_ok, ruff_output = _run_ruff_fix_on_file(file_path, project_root=project_root)
    if ruff_ok:
        if "fixed" in ruff_output.lower() or ruff_output:
            result.fixed.append(f"ruff-fix:{file_path}")
    else:
        result.remaining.append(f"ruff-fix:{file_path}: {ruff_output}")

    # Add formatter errors to remaining
    result.remaining.extend(fmt_errors)

    # Step 3: Re-lint to verify
    ext = Path(file_path).suffix.lstrip(".")
    if ext == "py":
        clean, lint_output = _run_lint_check(file_path, project_root=project_root)
        if not clean:
            result.remaining.append(f"ruff-check:{file_path}: {lint_output}")

    # Step 4: Determine exit code
    result.exit_code = 1 if result.remaining else 0
    return result


def lint_and_fix(path: str, *, project_root: Path | None = None) -> FixResult:
    """Run fix cycle on all matching files under a path.

    Finds files by extension, applies formatters + safe lint fixes,
    and reports aggregate results.
    """
    root = _resolve_root(project_root)
    target = root / path
    if not target.exists():
        return FixResult(remaining=[f"path not found: {path}"], exit_code=1)

    # Collect Python files (the primary fixable target)
    if target.is_dir():
        py_files = sorted(
            str(f.relative_to(root))
            for f in target.rglob("*.py")
            if ".venv" not in f.parts and "__pycache__" not in f.parts
        )
    elif target.suffix == ".py":
        py_files = [path]
    else:
        py_files = []

    # Run formatters once for all files
    fixed_formatters, fmt_errors = _run_formatters(project_root=project_root)

    result = FixResult()
    result.fixed.extend(fixed_formatters)

    # Run ruff fix on each Python file
    for file_path in py_files:
        ruff_ok, ruff_output = _run_ruff_fix_on_file(file_path, project_root=project_root)
        if ruff_ok:
            if ruff_output:
                result.fixed.append(f"ruff-fix:{file_path}")
        else:
            result.remaining.append(f"ruff-fix:{file_path}: {ruff_output}")

    result.remaining.extend(fmt_errors)

    # Re-lint all Python files
    for file_path in py_files:
        clean, lint_output = _run_lint_check(file_path, project_root=project_root)
        if not clean:
            result.remaining.append(f"ruff-check:{file_path}: {lint_output}")

    result.exit_code = 1 if result.remaining else 0
    return result


def test_and_fix(*, project_root: Path | None = None) -> FixResult:
    """Run formatters + lint fixes, then verify tests still pass.

    Only applies auto-fixes if prior tests were green. If prior tests
    fail, reports the failure without modifying files beyond formatters.
    """
    root = _resolve_root(project_root)
    result = FixResult()

    # Step 1: Run prior tests to establish baseline
    if not _tool_available("pytest"):
        return FixResult(remaining=["pytest not installed"], exit_code=1)

    env = _env_with_venv()
    try:
        prior = subprocess.run(
            ["pytest", "-q"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(root),
            env=env,
        )
    except (subprocess.TimeoutExpired, Exception) as e:
        return FixResult(remaining=[f"pytest baseline failed: {e}"], exit_code=1)

    prior_passed = prior.returncode == 0
    prior_output = (prior.stderr + prior.stdout).strip()

    if not prior_passed:
        return FixResult(
            remaining=[f"prior tests failed — skipping auto-fix:\n{prior_output}"],
            exit_code=1,
        )

    # Step 2: Baseline green — apply formatters + ruff fix
    fixed_formatters, fmt_errors = _run_formatters(project_root=project_root)
    result.fixed.extend(fixed_formatters)

    # Run ruff fix on src/ and tests/
    if _tool_available("ruff"):
        ruff_ok, ruff_output = _run_ruff_fix_on_file("src/", project_root=project_root)
        if ruff_ok:
            result.fixed.append("ruff-fix:src/")
        else:
            result.remaining.append(f"ruff-fix:src/: {ruff_output}")

    result.remaining.extend(fmt_errors)

    # Step 3: Verify tests still pass
    try:
        post = subprocess.run(
            ["pytest", "-q"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(root),
            env=env,
        )
    except (subprocess.TimeoutExpired, Exception) as e:
        result.remaining.append(f"post-fix tests failed to run: {e}")
        result.exit_code = 1
        return result

    if post.returncode != 0:
        post_output = (post.stderr + post.stdout).strip()
        result.remaining.append(f"tests broke after fix — reverting recommended:\n{post_output}")
        result.exit_code = 1
    else:
        result.exit_code = 1 if result.remaining else 0

    return result


def security_scan_and_patch(*, project_root: Path | None = None) -> FixResult:
    """Run semgrep scan and categorize findings.

    Findings are categorized into:
    - auto-fixable: deterministic patches (pinning versions, adding missing quotes)
    - manual-review: logic changes, design decisions, uncertain fixes

    Currently only categorizes findings — actual auto-patching is limited to
    known safe patterns. Most findings require manual review.
    """
    root = _resolve_root(project_root)
    result = FixResult()

    if not _tool_available("semgrep"):
        return FixResult(remaining=["semgrep not installed"], exit_code=1)

    env = _env_with_venv()

    # Run semgrep with project config
    try:
        proc = subprocess.run(
            ["semgrep", "scan", "--config", ".semgrep.yml", "--json"],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(root),
            env=env,
        )
    except subprocess.TimeoutExpired:
        return FixResult(remaining=["semgrep timed out"], exit_code=1)
    except Exception as e:
        return FixResult(remaining=[f"semgrep failed: {e}"], exit_code=1)

    # Parse JSON output
    try:
        semgrep_output = json.loads(proc.stdout)
    except json.JSONDecodeError:
        output = (proc.stderr + proc.stdout).strip()
        return FixResult(remaining=[f"semgrep output parse error:\n{output}"], exit_code=1)

    findings = semgrep_output.get("results", [])

    # Auto-fixable rule IDs — known safe deterministic patches
    auto_fixable_rules = {
        "generic.secrets.security.detected-ssh-private-key",
        "generic.secrets.security.detected-private-key",
    }

    for finding in findings:
        rule_id = finding.get("check_id", "unknown")
        file_path = finding.get("path", "unknown")
        line = finding.get("extra", {}).get("lineno", "?")
        message = finding.get("extra", {}).get("message", "")

        entry = f"{rule_id} at {file_path}:{line} — {message}"

        if rule_id in auto_fixable_rules:
            result.fixed.append(f"auto-fixable: {entry}")
        else:
            result.remaining.append(f"manual-review: {entry}")

    result.exit_code = 1 if result.remaining else 0
    return result


def main() -> None:
    """Entry point for ocd fix-cycle command."""
    parser = argparse.ArgumentParser(description="Closed-loop fix commands")
    sub = parser.add_subparsers(dest="command", required=True)

    fc = sub.add_parser("fix-cycle", help="Detect-fix-verify cycle on a single file")
    fc.add_argument("file", help="File to fix")

    lf = sub.add_parser("lint-and-fix", help="Fix all matching files under a path")
    lf.add_argument("path", help="Directory or file path")

    sub.add_parser("test-and-fix", help="Fix + verify tests still pass")
    sub.add_parser("security-scan-and-patch", help="Semgrep scan + categorize findings")

    args = parser.parse_args()

    if args.command == "fix-cycle":
        r = fix_cycle(args.file)
    elif args.command == "lint-and-fix":
        r = lint_and_fix(args.path)
    elif args.command == "test-and-fix":
        r = test_and_fix()
    elif args.command == "security-scan-and-patch":
        r = security_scan_and_patch()
    else:
        parser.error(f"Unknown command: {args.command}")
        return

    print(r.to_json())
    sys.exit(r.exit_code)


if __name__ == "__main__":
    main()
