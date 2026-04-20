"""Run all formatters with auto-fix.

Discovers available formatters, runs them on matching files, and reports
results including missing formatters.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from typing import Any

from ocd.config import PROJECT_ROOT, VENV_BIN

# ── Formatter registry ───────────────────────────────────────────────
# (name, command, extensions | None, config_files | None, timeout, install_hint)
#   name:          display name
#   command:       shell command (auto-fix mode, runs from project root)
#   extensions:    file extensions this formatter handles (no dot), or None if
#                  the formatter discovers files itself (e.g. prettier --write .)
#   config_files:  required project config paths, or None
#   timeout:       seconds before killing subprocess
#   install_hint:  package install instruction

FORMATTERS: list[tuple[Any, ...]] = [
    # Python
    ("ruff-format", "ruff format src/ tests/", None, None, 30, "pip:ruff"),
    ("ruff-fix", "ruff check --fix src/ tests/", None, None, 30, "pip:ruff"),
    # Markdown
    ("mdformat", "mdformat README.md docs/ .claude/skills/", None, None, 15, "pip:mdformat"),
    # JSON / CSS / HTML — prettier discovers files via its config
    (
        "prettier",
        "npx prettier --write .",
        None,
        (
            ".prettierrc",
            ".prettierrc.js",
            ".prettierrc.json",
            ".prettierrc.yml",
            "prettier.config.js",
        ),
        30,
        "npm:prettier",
    ),
    # CSS — only runs when .css files exist
    (
        "stylelint",
        'npx stylelint --fix "**/*.css"',
        ("css", "scss", "sass"),
        (
            ".stylelintrc",
            ".stylelintrc.js",
            ".stylelintrc.json",
            ".stylelintrc.yml",
            "stylelint.config.js",
        ),
        30,
        "npm:stylelint",
    ),
    # SQL (optional — requires sql extra) — only runs when .sql files exist
    (
        "sqlfluff-fix",
        "sqlfluff fix --force",
        ("sql",),
        (".sqlfluff", ".sqlfluff.ini", "pyproject.toml"),
        30,
        "pip:sqlfluff",
    ),
]


def _tool_available(command: str) -> bool:
    """Check if a tool binary is available in venv or on PATH."""
    binary = command.split()[0]
    if binary == "npx":
        return shutil.which("npx") is not None
    return (VENV_BIN / binary).exists() or shutil.which(binary) is not None


def _config_present(config_files: list[str] | None) -> bool:
    """Check if at least one required config file exists."""
    if config_files is None:
        return True
    return any((PROJECT_ROOT / cfg).exists() for cfg in config_files)


_IGNORED_DIRS = {".git", ".venv", "node_modules", "__pycache__", ".mypy_cache", ".ruff_cache"}


def _has_matching_files(extensions: tuple[str, ...] | None) -> bool:
    """Check if any files with the given extensions exist in the project."""
    if extensions is None:
        return True
    for ext in extensions:
        for path in PROJECT_ROOT.rglob(f"*.{ext}"):
            if not any(part in _IGNORED_DIRS for part in path.parts):
                return True
    return False


def _format_install_hint(entry: tuple[Any, ...]) -> str:
    """Format install hint from registry entry."""
    hint = entry[5]
    if hint.startswith("pip:"):
        return f"`uv add {hint[4:]}`"
    if hint.startswith(("apt:", "brew:", "npm:", "gem:", "composer:", "dotnet:")):
        manager = hint.split(":")[0]
        package = hint.split(":", 1)[1]
        return f"`{manager} install {package}`"
    return f"install {entry[1].split()[0]}"


def run_formatters() -> int:
    """Run all available formatters and report results.

    Returns exit code: 0 if all formatters succeeded or skipped, 1 if any failed.
    """
    results: list[dict[str, Any]] = []

    env = os.environ.copy()
    venv_bin_str = str(VENV_BIN)
    if venv_bin_str not in env.get("PATH", ""):
        env["PATH"] = f"{venv_bin_str}:{env.get('PATH', '')}"

    for entry in FORMATTERS:
        name, command, extensions, config_files, timeout, _install_hint = entry

        if not _tool_available(command):
            results.append(
                {
                    "name": name,
                    "status": "missing",
                    "reason": "not_installed",
                    "install_hint": _format_install_hint(entry),
                }
            )
            continue

        if not _config_present(config_files):
            results.append({"name": name, "status": "missing", "reason": "no_config"})
            continue

        if not _has_matching_files(extensions):
            results.append({"name": name, "status": "skip", "reason": "no_files"})
            continue

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(PROJECT_ROOT),
                env=env,
            )
            output = (result.stderr + result.stdout).strip()
            if result.returncode == 0:
                results.append({"name": name, "status": "ok", "output": output})
            else:
                results.append(
                    {
                        "name": name,
                        "status": "error",
                        "output": output,
                        "returncode": result.returncode,
                    }
                )
        except subprocess.TimeoutExpired:
            results.append(
                {
                    "name": name,
                    "status": "error",
                    "output": f"timed out after {timeout}s",
                }
            )
        except Exception as e:
            results.append({"name": name, "status": "error", "output": str(e)})

    ok = [r for r in results if r["status"] == "ok"]
    errors = [r for r in results if r["status"] == "error"]
    missing = [r for r in results if r["status"] == "missing"]
    skipped = [r for r in results if r["status"] == "skip"]

    for r in ok:
        if r.get("output"):
            print(f"  \u2713 {r['name']}: {r['output']}")
        else:
            print(f"  \u2713 {r['name']}")

    for r in errors:
        print(f"  \u2717 {r['name']}: {r['output']}", file=sys.stderr)

    for r in missing:
        if r.get("reason") == "no_config":
            print(f"  \u2298 {r['name']}: no config file found")
        else:
            print(f"  \u2298 {r['name']}: not installed \u2014 {r['install_hint']}")

    for r in skipped:
        print(f"  \u2298 {r['name']}: no matching files")

    ran = len(ok) + len(errors)
    not_ran = len(missing) + len(skipped)
    print(f"\n{ran} formatter{'s' if ran != 1 else ''} ran, {not_ran} skipped.")

    return 1 if errors else 0


def main() -> None:
    """Entry point for ocd format command."""
    sys.exit(run_formatters())
