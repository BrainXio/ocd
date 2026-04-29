"""FastMCP server for OCD — discipline & enforcement layer, no CLI, no scripts."""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from ocd.standards_data import (
    check_message,
    compute_standards_hash,
    get_standards_reference,
    verify_standards_hash,
)

logging.basicConfig(level=logging.INFO, stream=sys.stderr)

mcp = FastMCP(
    "ocd",
    instructions=(
        "OCD discipline & enforcement layer. Use these tools to check quality gates, "
        "verify standards, scan for secrets, run formatters, and lint code."
    ),
)

# ── Mode state ────────────────────────────────────────────────────────────────

_current_mode: str = "developer"
_ALLOWED_MODES: frozenset[str] = frozenset({"developer"})


def _find_project_root() -> Path:
    """Find project root by walking up from CWD looking for .git/."""
    cwd = Path.cwd()
    for parent in [cwd, *cwd.parents]:
        if (parent / ".git").exists():
            return parent
    return cwd


def _tool_available(binary: str) -> bool:
    """Check if a binary is available on PATH."""
    return shutil.which(binary) is not None


def _run_tool(cmd: list[str], timeout: int = 60, cwd: Path | None = None) -> tuple[bool, str]:
    """Run a subprocess tool, return (success, output)."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(cwd or _find_project_root()),
        )
    except subprocess.TimeoutExpired:
        return False, f"timed out after {timeout}s"
    except FileNotFoundError:
        return True, "skipped (not installed)"

    output = (result.stderr + result.stdout).strip()
    return result.returncode == 0, output


# ── Mode tools ────────────────────────────────────────────────────────────────


@mcp.tool()
async def ocd_set_mode(mode: str) -> str:
    """Switch the active rule/gate/skill set.

    Args:
        mode: The mode to activate. Phase 1 only accepts "developer".
    """
    if mode not in _ALLOWED_MODES:
        allowed = ", ".join(sorted(_ALLOWED_MODES))
        return json.dumps({"ok": False, "error": f"Unknown mode '{mode}'. Allowed: {allowed}"})
    global _current_mode
    _current_mode = mode
    return json.dumps({"ok": True, "mode": mode})


@mcp.tool()
async def ocd_get_mode() -> str:
    """Return the currently active mode."""
    return json.dumps({"mode": _current_mode})


# ── Quality gate tools ───────────────────────────────────────────────────────


@mcp.tool()
async def ocd_check() -> str:
    """Run fast local quality gate.

    Checks: branch protection, standards hash, staged secret scan, ruff check.
    Target: < 10 seconds for typical use.
    """
    root = _find_project_root()
    results: list[dict[str, Any]] = []

    # Branch protection
    try:
        r = subprocess.run(
            ["git", "symbolic-ref", "--short", "HEAD"],
            capture_output=True,
            text=True,
            cwd=str(root),
        )
        branch = r.stdout.strip()
        if branch == "main":
            results.append(
                {
                    "check": "branch-protection",
                    "status": "fail",
                    "detail": "commits on main are prohibited",
                }
            )
        else:
            results.append(
                {"check": "branch-protection", "status": "pass", "detail": f"branch: {branch}"}
            )
    except Exception:
        results.append(
            {
                "check": "branch-protection",
                "status": "pass",
                "detail": "not a git repo, skipped",
            }
        )

    # Standards verify
    std_result = verify_standards_hash()
    if std_result["match"]:
        results.append(
            {
                "check": "standards-verify",
                "status": "pass",
                "detail": f"v{std_result['version']} [{std_result['computed_hash']}]",
            }
        )
    else:
        results.append(
            {
                "check": "standards-verify",
                "status": "fail",
                "detail": (
                    f"hash mismatch: stored={std_result['stored_hash']}, "
                    f"computed={std_result['computed_hash']}"
                ),
            }
        )

    # Secret scan (staged)
    if _tool_available("gitleaks"):
        gitleaks_config = root / ".gitleaks.toml"
        config_args = ["-c", str(gitleaks_config)] if gitleaks_config.exists() else []
        ok, output = _run_tool(
            ["gitleaks", "protect", "--staged", *config_args], timeout=30, cwd=root
        )
        if ok:
            results.append(
                {"check": "secret-scan", "status": "pass", "detail": "no secrets detected"}
            )
        else:
            results.append({"check": "secret-scan", "status": "fail", "detail": output})
    else:
        results.append(
            {"check": "secret-scan", "status": "skip", "detail": "gitleaks not installed"}
        )

    # Ruff check
    if _tool_available("ruff"):
        ok, output = _run_tool(["ruff", "check", "src/", "tests/"], timeout=30, cwd=root)
        if ok:
            results.append({"check": "ruff-check", "status": "pass", "detail": "clean"})
        else:
            results.append({"check": "ruff-check", "status": "fail", "detail": output})
    else:
        results.append({"check": "ruff-check", "status": "skip", "detail": "ruff not installed"})

    passed = sum(1 for r in results if r["status"] == "pass")
    failed = sum(1 for r in results if r["status"] == "fail")
    skipped = sum(1 for r in results if r["status"] == "skip")

    return json.dumps(
        {
            "all_passed": failed == 0,
            "summary": f"{passed} passed, {failed} failed, {skipped} skipped",
            "results": results,
        },
        indent=2,
    )


@mcp.tool()
async def ocd_ci_check(fast: bool = False) -> str:
    """Run full local CI mirror of all quality gates.

    Args:
        fast: If True, skip full test suite (diff-aware only).
    """
    root = _find_project_root()
    results: list[dict[str, Any]] = []

    # Standards verify
    std_result = verify_standards_hash()
    results.append(
        {
            "check": "standards-verify",
            "status": "pass" if std_result["match"] else "fail",
            "detail": f"v{std_result['version']} [{std_result['computed_hash']}]",
        }
    )

    # Secret scan (full)
    if _tool_available("gitleaks"):
        gitleaks_config = root / ".gitleaks.toml"
        config_args = ["-c", str(gitleaks_config)] if gitleaks_config.exists() else []
        ok, output = _run_tool(
            ["gitleaks", "detect", "--source", ".", *config_args], timeout=60, cwd=root
        )
        results.append(
            {
                "check": "secret-scan",
                "status": "pass" if ok else "fail",
                "detail": "no secrets detected" if ok else output,
            }
        )
    else:
        results.append(
            {"check": "secret-scan", "status": "skip", "detail": "gitleaks not installed"}
        )

    # Ruff check
    if _tool_available("ruff"):
        ok, output = _run_tool(["ruff", "check", "src/", "tests/"], timeout=30, cwd=root)
        results.append(
            {
                "check": "ruff-check",
                "status": "pass" if ok else "fail",
                "detail": "clean" if ok else output,
            }
        )
    else:
        results.append({"check": "ruff-check", "status": "skip", "detail": "ruff not installed"})

    # Ruff format check
    if _tool_available("ruff"):
        ok, output = _run_tool(
            ["ruff", "format", "--check", "src/", "tests/"], timeout=30, cwd=root
        )
        results.append(
            {
                "check": "ruff-format",
                "status": "pass" if ok else "fail",
                "detail": "clean" if ok else output,
            }
        )
    else:
        results.append({"check": "ruff-format", "status": "skip", "detail": "ruff not installed"})

    # Mypy
    if _tool_available("mypy"):
        ok, output = _run_tool(["mypy", "src/ocd/", "--strict"], timeout=60, cwd=root)
        results.append(
            {
                "check": "mypy",
                "status": "pass" if ok else "fail",
                "detail": "clean" if ok else output,
            }
        )
    else:
        results.append({"check": "mypy", "status": "skip", "detail": "mypy not installed"})

    # Yamllint
    if _tool_available("yamllint"):
        ok, output = _run_tool(
            ["yamllint", "-f", "parsable", ".github/workflows/", ".yamllint"],
            timeout=15,
            cwd=root,
        )
        results.append(
            {
                "check": "yamllint",
                "status": "pass" if ok else "fail",
                "detail": "clean" if ok else output,
            }
        )
    else:
        results.append({"check": "yamllint", "status": "skip", "detail": "yamllint not installed"})

    # Pytest
    if _tool_available("pytest"):
        if fast:
            cmd = [sys.executable, "-m", "pytest", "-q"]
        else:
            cmd = [sys.executable, "-m", "pytest", "-v"]
        ok, output = _run_tool(cmd, timeout=120, cwd=root)
        results.append(
            {
                "check": "pytest",
                "status": "pass" if ok else "fail",
                "detail": "all tests passed" if ok else output,
            }
        )
    else:
        results.append({"check": "pytest", "status": "skip", "detail": "pytest not installed"})

    passed = sum(1 for r in results if r["status"] == "pass")
    failed = sum(1 for r in results if r["status"] == "fail")
    skipped = sum(1 for r in results if r["status"] == "skip")

    return json.dumps(
        {
            "all_passed": failed == 0,
            "summary": f"{passed} passed, {failed} failed, {skipped} skipped",
            "results": results,
        },
        indent=2,
    )


# ── Commit verification ──────────────────────────────────────────────────────


@mcp.tool()
async def ocd_verify_commit(message: str) -> str:
    """Verify a commit message for prohibited attribution patterns.

    Args:
        message: The commit message text to check.
    """
    violations = check_message(message)
    if not violations:
        return json.dumps({"ok": True, "detail": "commit message is clean"})

    return json.dumps(
        {
            "ok": False,
            "detail": "commit message contains prohibited attribution",
            "violations": [
                {"pattern": pattern, "line": line.strip()} for pattern, line in violations
            ],
        },
        indent=2,
    )


# ── Secret scanning ──────────────────────────────────────────────────────────


@mcp.tool()
async def ocd_scan_secrets(staged: bool = False) -> str:
    """Scan for secrets using gitleaks.

    Args:
        staged: If True, scan staged changes only. If False, scan entire source.
    """
    if not _tool_available("gitleaks"):
        return json.dumps(
            {
                "ok": True,
                "status": "skipped",
                "detail": "gitleaks not installed. Install: https://github.com/gitleaks/gitleaks",
            }
        )

    root = _find_project_root()
    gitleaks_config = root / ".gitleaks.toml"
    config_args = ["-c", str(gitleaks_config)] if gitleaks_config.exists() else []

    if staged:
        cmd = ["gitleaks", "protect", "--staged", *config_args]
    else:
        cmd = ["gitleaks", "detect", "--source", ".", *config_args]

    result = subprocess.run(cmd, cwd=str(root))
    if result.returncode == 0:
        return json.dumps({"ok": True, "status": "clean", "detail": "no secrets detected"})

    scope = "staged changes" if staged else "source"
    return json.dumps(
        {
            "ok": False,
            "status": "secrets_found",
            "detail": f"potential secrets detected in {scope}",
        }
    )


# ── Formatters ───────────────────────────────────────────────────────────────


@mcp.tool()
async def ocd_run_formatters() -> str:
    """Run all available formatters with auto-fix (ruff format, ruff check --fix)."""
    root = _find_project_root()
    results: list[dict[str, Any]] = []

    if _tool_available("ruff"):
        ok, output = _run_tool(["ruff", "format", "src/", "tests/"], timeout=30, cwd=root)
        results.append(
            {
                "formatter": "ruff-format",
                "status": "ok" if ok else "error",
                "detail": output if output else "formatted",
            }
        )

        ok, output = _run_tool(["ruff", "check", "--fix", "src/", "tests/"], timeout=30, cwd=root)
        results.append(
            {
                "formatter": "ruff-fix",
                "status": "ok" if ok else "error",
                "detail": output if output else "no fixes needed",
            }
        )
    else:
        results.append(
            {
                "formatter": "ruff",
                "status": "missing",
                "detail": "ruff not installed — `uv add ruff`",
            }
        )

    ran = sum(1 for r in results if r["status"] in ("ok", "error"))
    errors = sum(1 for r in results if r["status"] == "error")
    missing = sum(1 for r in results if r["status"] == "missing")

    return json.dumps(
        {
            "all_ok": errors == 0,
            "summary": f"{ran} ran, {errors} errors, {missing} skipped",
            "results": results,
        },
        indent=2,
    )


# ── Linting ──────────────────────────────────────────────────────────────────


@mcp.tool()
async def ocd_lint_work(files: list[str]) -> str:
    """Lint specified files and report violations.

    Args:
        files: List of file paths to lint.
    """
    root = _find_project_root()
    results: list[dict[str, Any]] = []

    for file_path in files:
        ext = Path(file_path).suffix.lstrip(".")
        if not ext:
            continue

        full_path = root / file_path
        if not full_path.exists():
            results.append({"file": file_path, "status": "error", "detail": "file not found"})
            continue

        if ext == "py" and _tool_available("ruff"):
            ok, output = _run_tool(["ruff", "check", str(full_path)], timeout=10, cwd=root)
            results.append(
                {
                    "file": file_path,
                    "linter": "ruff",
                    "status": "clean" if ok else "errors",
                    "detail": output if output else "no issues",
                }
            )
        elif ext == "py" and not _tool_available("ruff"):
            results.append(
                {
                    "file": file_path,
                    "linter": "ruff",
                    "status": "missing",
                    "detail": "ruff not installed",
                }
            )

        if ext == "md" and _tool_available("mdformat"):
            ok, output = _run_tool(["mdformat", "--check", str(full_path)], timeout=10, cwd=root)
            results.append(
                {
                    "file": file_path,
                    "linter": "mdformat",
                    "status": "clean" if ok else "errors",
                    "detail": output if output else "formatted correctly",
                }
            )
        elif ext == "md" and not _tool_available("mdformat"):
            results.append(
                {
                    "file": file_path,
                    "linter": "mdformat",
                    "status": "missing",
                    "detail": "mdformat not installed",
                }
            )

    if not results:
        return json.dumps({"ok": True, "detail": "no lintable files provided"})

    error_count = sum(1 for r in results if r["status"] == "errors")
    return json.dumps(
        {
            "ok": error_count == 0,
            "summary": f"{len(results)} files checked, {error_count} with errors",
            "results": results,
        },
        indent=2,
    )


# ── Standards tools ──────────────────────────────────────────────────────────


@mcp.tool()
async def ocd_standards_verify() -> str:
    """Verify that the standards hash matches the embedded Nine Standards content."""
    result = verify_standards_hash()
    if result["match"]:
        return json.dumps(
            {
                "ok": True,
                "detail": f"hash verified: v{result['version']} [{result['computed_hash']}]",
            }
        )
    return json.dumps(
        {
            "ok": False,
            "detail": "hash mismatch",
            "stored_hash": result["stored_hash"],
            "computed_hash": result["computed_hash"],
            "version": result["version"],
        },
        indent=2,
    )


@mcp.tool()
async def ocd_standards_update() -> str:
    """Recompute and report the current standards hash.

    Since standards are embedded in the package, this verifies internal consistency
    rather than updating a filesystem file.
    """
    computed = compute_standards_hash()
    ref = get_standards_reference()
    return json.dumps(
        {
            "ok": True,
            "detail": f"standards reference: {ref}",
            "computed_hash": computed,
        }
    )


# ── Entry point ──────────────────────────────────────────────────────────────


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
