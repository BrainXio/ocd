"""PostToolUse auto-format hook for Claude Code.

Runs formatters in fix mode on the file just written/edited, preventing
formatting drift before the lint hook checks the file. Captures violations
to a JSONL log for knowledge base learning.

Invoked via `ocd hook format-work --edit`.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ocd.config import PROJECT_ROOT, STATE_DIR, VENV_BIN
from ocd.hooks.hookslib import parse_stdin_json
from ocd.session.session_card import update_session_card

VIOLATIONS_LOG = STATE_DIR / "format-violations.jsonl"

# ── Per-file formatter registry ────────────────────────────────────
# (extensions, command_fn, config_files | None, timeout, install_hint)
#   extensions:    file extensions this formatter handles (no dot)
#   command_fn:    callable(file_path) -> list[str]  (no shell=True)
#   config_files:  required project config paths, or None
#   timeout:       seconds before killing subprocess
#   install_hint:  package install instruction

FILE_FORMATTERS: list[tuple[Any, ...]] = [
    # Python
    (("py",), lambda f: ["ruff", "format", f], None, 10, "pip:ruff"),
    (("py",), lambda f: ["ruff", "check", "--fix", f], None, 10, "pip:ruff"),
    # Markdown
    (("md",), lambda f: ["mdformat", f], None, 10, "pip:mdformat"),
    # CSS
    (
        ("css", "scss", "sass"),
        lambda f: ["npx", "stylelint", "--fix", f],
        (
            ".stylelintrc",
            ".stylelintrc.js",
            ".stylelintrc.json",
            ".stylelintrc.yml",
            "stylelint.config.js",
        ),
        15,
        "npm:stylelint",
    ),
    # SQL
    (
        ("sql",),
        lambda f: ["sqlfluff", "fix", "--force", f],
        (".sqlfluff", ".sqlfluff.ini", "pyproject.toml"),
        15,
        "pip:sqlfluff",
    ),
    # Prettier excluded: --write works best project-wide, not per-file.
    # Prettier drift caught by lint hook; fixed with `ocd format`.
]

# Build extension -> formatters lookup
_EXT_MAP: dict[str, list[tuple[Any, ...]]] = {}
for entry in FILE_FORMATTERS:
    for ext in entry[0]:
        _EXT_MAP.setdefault(ext, []).append(entry)


def _ext_from_path(file_path: str) -> str | None:
    stem = Path(file_path).suffix
    return stem.lstrip(".") if stem else None


def _tool_available(command: list[str]) -> bool:
    binary = command[0]
    if binary == "npx":
        return shutil.which("npx") is not None
    return (VENV_BIN / binary).exists() or shutil.which(binary) is not None


def _config_present(config_files: list[str] | None) -> bool:
    if config_files is None:
        return True
    return any((PROJECT_ROOT / cfg).exists() for cfg in config_files)


def _file_hash(file_path: str) -> str | None:
    try:
        return str(Path(file_path).stat().st_mtime)
    except OSError:
        return None


def _log_violation(file_path: str, formatter_name: str, extension: str) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now(UTC).isoformat(timespec="seconds"),
        "file": file_path,
        "formatter": formatter_name,
        "extension": extension,
    }
    with open(VIOLATIONS_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")


def _format_install_hint(entry: tuple[Any, ...]) -> str:
    hint = entry[4]
    if hint.startswith("pip:"):
        return f"`uv add {hint[4:]}`"
    if hint.startswith(("apt:", "brew:", "npm:", "gem:", "composer:", "dotnet:")):
        manager = hint.split(":")[0]
        package = hint.split(":", 1)[1]
        return f"`{manager} install {package}`"
    return f"install {entry[1]([])[0]}"


def format_file(file_path: str) -> dict[str, object] | None:
    """Run applicable formatters on a single file (fix mode).

    Returns a hook output dict, or None if nothing to report.
    """
    ext = _ext_from_path(file_path)
    if ext is None or ext not in _EXT_MAP:
        return None

    env = os.environ.copy()
    env["OCD_FORMAT_WORK_RUNNING"] = "1"
    venv_bin_str = str(VENV_BIN)
    if venv_bin_str not in env.get("PATH", ""):
        env["PATH"] = f"{venv_bin_str}:{env.get('PATH', '')}"

    context_parts: list[str] = []
    missing_parts: list[str] = []

    for entry in _EXT_MAP[ext]:
        _extensions, command_fn, config_files, timeout, _install_hint = entry
        # Derive a display name from the command
        sample_cmd = command_fn("_")
        name = sample_cmd[0]
        if len(sample_cmd) > 1 and sample_cmd[1] not in {"--fix", "--force", "--write"}:
            name = f"{sample_cmd[0]}-{sample_cmd[1]}"

        if not _tool_available(sample_cmd):
            missing_parts.append(f"**{name}** not installed — {_format_install_hint(entry)}")
            continue

        if not _config_present(config_files):
            missing_parts.append(f"**{name}** not configured — no config file found")
            continue

        args = command_fn(file_path)

        # Snapshot file before formatting
        before = _file_hash(file_path)

        try:
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(PROJECT_ROOT),
                env=env,
            )
        except subprocess.TimeoutExpired:
            context_parts.append(f"**{name}** timed out after {timeout}s")
            continue
        except Exception as e:
            context_parts.append(f"**{name}** failed: {e}")
            continue

        if result.returncode != 0:
            output = (result.stderr + result.stdout).strip()
            return {"decision": "block", "reason": f"**{name}** failed:\n{output}"}

        # Check if file was modified
        after = _file_hash(file_path)
        if before != after:
            _log_violation(file_path, name, ext)
            context_parts.append(f"**{name}** auto-formatted {file_path}")

    if context_parts:
        return {
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": "\n\n".join(context_parts),
            }
        }

    if missing_parts:
        return {
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": "\n\n".join(missing_parts),
            }
        }

    return None


# ── PostToolUse: --edit mode ───────────────────────────────────────


def edit_mode() -> None:
    """Auto-format the file just written/edited."""
    hook_input = parse_stdin_json()
    tool_input = hook_input.get("tool_input", {})
    file_path = tool_input.get("file_path", "")

    if not file_path:
        return

    update_session_card(file_path)

    result = format_file(file_path)
    if result is not None:
        print(json.dumps(result))


# ── Entry point ────────────────────────────────────────────────────


def main() -> None:
    # Recursion guard: prevents infinite loop if hook triggers itself
    if os.environ.get("OCD_FORMAT_WORK_RUNNING"):
        return

    # Recursion guard for flush subprocesses
    if os.environ.get("CLAUDE_INVOKED_BY"):
        return

    if "--edit" in sys.argv:
        edit_mode()


if __name__ == "__main__":
    main()
