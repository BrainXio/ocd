"""Automatic code linting hook for Claude Code.

Runs in two modes:
  --edit   : PostToolUse mode, lints the file just edited
  --commit : PreToolUse mode, lints all staged files before a git commit

Reports linters that would apply but are missing (not installed or no config)
so the agent can inform the user about gaps in lint coverage.
"""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

# Recursion guard
if os.environ.get("CLAUDE_INVOKED_BY"):
    sys.exit(0)

# Reuse path constants from config.py
_SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(_SCRIPTS_DIR))

# isort: off
from config import PROJECT_ROOT, VENV_PYTHON  # noqa: E402
from hookslib import read_stdin  # noqa: E402
# isort: on

# Venv bin directory — prefer linters installed here over system PATH
VENV_BIN = VENV_PYTHON.parent

# ── Linter registry ──────────────────────────────────────────────────
# (extensions, command_template, config_files | None, is_blocking, timeout, scope,
#  install_hint)
#   extensions:      file extensions this linter handles (no dot)
#   command_template: shell command with {file} placeholder (omit for project-scope)
#   config_files:    list of project config paths required, or None for global tools
#   is_blocking:     True = errors block; False = advisory warnings only
#   timeout:         seconds before killing the subprocess
#   scope:           "file" or "project"
#   install_hint:    how to install the linter (package name or instruction)

LINTERS: list[tuple[Any, ...]] = [
    # Markdown
    (("md",), "mdformat --check {file}", None, True, 5, "file", "pip:mdformat"),
    # Python
    (("py",), "ruff check {file}", None, True, 8, "file", "pip:ruff"),
    (("py",), "mypy {file}", None, True, 10, "file", "pip:mypy"),
    # Shell
    (
        ("sh", "bash"),
        "shellcheck --severity=warning {file}",
        None,
        True,
        8,
        "file",
        "apt:shellcheck",
    ),
    # Rust
    (("rs",), "cargo clippy -- -D warnings", ("Cargo.toml",), True, 15, "project", "rustup:clippy"),
    # Go
    (("go",), "go vet {file}", None, True, 8, "file", "go:vet"),
    (("go",), "gofmt -d {file}", None, False, 5, "file", "go:gofmt"),
    # TypeScript
    (("ts", "tsx"), "tsc --noEmit", ("tsconfig.json",), True, 15, "project", "npm:typescript"),
    (
        ("ts", "tsx", "js", "jsx"),
        "eslint {file}",
        (
            ".eslintrc",
            ".eslintrc.js",
            ".eslintrc.json",
            ".eslintrc.yml",
            "eslint.config.js",
        ),
        True,
        8,
        "file",
        "npm:eslint",
    ),
    # Java
    (
        ("java",),
        "google-java-format --dry-run {file}",
        None,
        False,
        8,
        "file",
        "brew:google-java-format",
    ),
    # C/C++
    (
        ("c", "h", "cpp", "hpp"),
        "clang-format --dry-run {file}",
        (".clang-format",),
        True,
        8,
        "file",
        "apt:clang-format",
    ),
    # C#
    (
        ("cs",),
        "dotnet format --verify-no-changes {file}",
        (".csproj",),
        True,
        10,
        "file",
        "dotnet:format",
    ),
    # Ruby
    (("rb",), "rubocop {file}", ("Gemfile",), True, 10, "file", "gem:rubocop"),
    # YAML
    (
        ("yml", "yaml"),
        "yamllint -f parsable {file}",
        (".yamllint", ".yamllint.yaml", ".yamllint.yml"),
        False,
        8,
        "file",
        "pip:yamllint",
    ),
    # PHP
    (
        ("php",),
        "phpstan analyse {file}",
        ("phpstan.neon", "phpstan.neon.dist"),
        True,
        10,
        "file",
        "composer:phpstan",
    ),
    (
        ("php",),
        "php-cs-fixer fix --dry-run {file}",
        (
            ".php-cs-fixer.php",
            ".php-cs-fixer.dist.php",
        ),
        False,
        8,
        "file",
        "composer:php-cs-fixer",
    ),
]

# Build extension → linters lookup
_EXT_MAP: dict[str, list[tuple[Any, ...]]] = {}
for entry in LINTERS:
    for ext in entry[0]:
        _EXT_MAP.setdefault(ext, []).append(entry)


def _tool_available(command: str) -> bool:
    """Check if the linter binary is available in venv or on PATH."""
    binary = command.split()[0]
    return (VENV_BIN / binary).exists() or shutil.which(binary) is not None


def _config_present(config_files: list[str] | None) -> bool:
    """Check if at least one required project config file exists."""
    if config_files is None:
        return True
    return any((PROJECT_ROOT / cfg).exists() for cfg in config_files)


def _ext_from_path(file_path: str) -> str | None:
    """Extract extension without dot. Returns None for no extension."""
    stem = Path(file_path).suffix
    return stem.lstrip(".") if stem else None


def _format_install_hint(entry: tuple[Any, ...]) -> str:
    """Format an install hint from the linter registry entry."""
    binary = entry[1].split()[0]
    hint = entry[6] if len(entry) > 6 else ""
    if hint.startswith("pip:"):
        return f"`uv --directory .claude add {hint[4:]}`"
    if hint.startswith(("apt:", "brew:", "npm:", "gem:", "composer:", "dotnet:")):
        manager = hint.split(":")[0]
        package = hint.split(":", 1)[1]
        return f"`{manager} install {package}` (for {binary})"
    if hint.startswith("rustup:"):
        return f"`rustup component add clippy` (for {binary})"
    if hint.startswith("go:"):
        return f"part of Go toolchain (for {binary})"
    return f"install {binary}"


def run_linter(entry: tuple[Any, ...], file_path: str) -> tuple[bool, str]:
    """Run a single linter. Returns (has_errors, output_text)."""
    _, command_template, config_files, _is_blocking, timeout, scope, *_ = entry

    if not _tool_available(command_template):
        return False, ""

    if not _config_present(config_files):
        return False, ""

    # Build command
    if scope == "project" or "{file}" not in command_template:
        command = command_template
    else:
        command = command_template.format(file=file_path)

    # Ensure venv bin is on PATH so linters can find venv-installed tools
    env = os.environ.copy()
    existing_path = env.get("PATH", "")
    venv_bin_str = str(VENV_BIN)
    if venv_bin_str not in existing_path:
        env["PATH"] = f"{venv_bin_str}:{existing_path}"

    # Ensure mypy can find local modules (config, utils, hookslib)
    scripts_dir = str(_SCRIPTS_DIR)
    if "MYPYPATH" not in env:
        env["MYPYPATH"] = scripts_dir
    elif scripts_dir not in env["MYPYPATH"]:
        env["MYPYPATH"] = f"{scripts_dir}{os.pathsep}{env['MYPYPATH']}"

    try:
        result = subprocess.run(
            shlex.split(command),
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(PROJECT_ROOT),
            env=env,
        )
    except subprocess.TimeoutExpired:
        binary = command.split()[0]
        return False, f"[{binary}] timed out after {timeout}s"
    except Exception as e:
        binary = command.split()[0]
        return False, f"[{binary}] failed: {e}"

    output = (result.stderr + result.stdout).strip()
    has_errors = result.returncode != 0
    return has_errors, output


def lint_file(file_path: str, include_project: bool = False) -> list[dict[str, Any]]:
    """Lint a single file with all applicable linters.

    Returns results with three possible statuses:
      "errors"   — linter ran and found problems (blocking)
      "clean"    — linter ran and passed (or has non-blocking warnings)
      "missing"  — linter would apply but is not installed or not configured
    """
    ext = _ext_from_path(file_path)
    if ext is None or ext not in _EXT_MAP:
        return []

    results = []
    for entry in _EXT_MAP[ext]:
        _, command_template, config_files, _, _, scope, *_ = entry
        binary = command_template.split()[0]

        # Skip project-scope linters in edit mode (too slow for real-time)
        if scope == "project" and not include_project:
            continue

        # Check availability
        if not _tool_available(command_template):
            results.append(
                {
                    "linter": binary,
                    "status": "missing",
                    "reason": "not_installed",
                    "install_hint": _format_install_hint(entry),
                }
            )
            continue

        if not _config_present(config_files):
            results.append(
                {
                    "linter": binary,
                    "status": "missing",
                    "reason": "no_config",
                    "install_hint": _format_install_hint(entry),
                }
            )
            continue

        has_errors, output = run_linter(entry, file_path)
        if has_errors:
            results.append(
                {
                    "linter": binary,
                    "status": "errors",
                    "output": output,
                }
            )
        elif output:
            results.append(
                {
                    "linter": binary,
                    "status": "clean",
                    "output": output,
                }
            )
        else:
            results.append(
                {
                    "linter": binary,
                    "status": "clean",
                }
            )

    return results


# ── PostToolUse: --edit mode ─────────────────────────────────────────


def edit_mode() -> None:
    """Lint the file just written/edited and feed results back."""
    hook_input = read_stdin()
    tool_input = hook_input.get("tool_input", {})
    file_path = tool_input.get("file_path", "")

    if not file_path:
        return

    ext = _ext_from_path(file_path)
    if ext is None or ext not in _EXT_MAP:
        return

    results = lint_file(file_path, include_project=False)

    errors = [r for r in results if r["status"] == "errors"]
    missing = [r for r in results if r["status"] == "missing"]
    clean = [r for r in results if r["status"] == "clean" and r.get("output")]

    if errors:
        parts = []
        for e in errors:
            parts.append(f"**{e['linter']}** found issues:\n{e['output']}")
        reason = "\n\n".join(parts)
        output: dict[str, object] = {"decision": "block", "reason": reason}
        print(json.dumps(output))
        return

    # Report missing linters and clean-pass warnings as additional context
    context_parts = []
    for m in missing:
        if m["reason"] == "not_installed":
            context_parts.append(f"**{m['linter']}** not installed — {m['install_hint']}")
        else:
            context_parts.append(f"**{m['linter']}** not configured — no config file found")

    for c in clean:
        context_parts.append(f"**{c['linter']}**:\n{c['output']}")

    if context_parts:
        context = "\n\n".join(context_parts)
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": context,
            }
        }
        print(json.dumps(output))


# ── PreToolUse: --commit mode ────────────────────────────────────────


def commit_mode() -> None:
    """Lint all staged files and block the commit if errors found."""
    hook_input = read_stdin()
    tool_input = hook_input.get("tool_input", {})
    command = tool_input.get("command", "")

    if "git commit" not in command:
        return

    # Check if we're in a git repo
    try:
        subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            check=True,
            cwd=str(PROJECT_ROOT),
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return  # Not a git repo, don't block

    # Get staged files
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
        )
        staged = [f for f in result.stdout.strip().splitlines() if f]
    except Exception:
        return

    if not staged:
        return

    # Filter to lintable files
    lintable = [f for f in staged if _ext_from_path(f) in _EXT_MAP]
    if not lintable:
        return

    all_errors: list[str] = []
    all_missing: list[str] = []
    for file_path in lintable:
        full_path = str(PROJECT_ROOT / file_path)
        results = lint_file(full_path, include_project=True)
        for r in results:
            if r["status"] == "errors":
                all_errors.append(f"**{r['linter']}** on {file_path}:\n{r['output']}")
            elif r["status"] == "missing" and r["reason"] == "not_installed":
                all_missing.append(f"**{r['linter']}** (missing) on {file_path}")

    if all_errors:
        report = "\n\n".join(all_errors)
        if all_missing:
            report += f"\n\nMissing linters (not blocking): {'; '.join(set(all_missing))}"
        print(f"Lint errors found — fix before committing:\n\n{report}", file=sys.stderr)
        sys.exit(2)


# ── Entry point ──────────────────────────────────────────────────────


def main() -> None:
    if "--edit" in sys.argv:
        edit_mode()
    elif "--commit" in sys.argv:
        commit_mode()


if __name__ == "__main__":
    main()
