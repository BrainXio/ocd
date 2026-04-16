"""Shared utilities for Claude Code lifecycle hooks."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Reuse path constants from config.py (scripts/ is sibling of hooks/)
_SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(_SCRIPTS_DIR))

from config import (  # noqa: E402
    CLAUDE_DIR,
    MAX_FLUSH_CONTEXT_CHARS,
    MAX_FLUSH_TURNS,
    MIN_TURNS_PRE_COMPACT,
    MIN_TURNS_SESSION_END,
    SCRIPTS_DIR,
    STATE_DIR,
)

# Re-export for callers
__all__ = [
    "MAX_FLUSH_CONTEXT_CHARS",
    "MAX_FLUSH_TURNS",
    "MIN_TURNS_PRE_COMPACT",
    "MIN_TURNS_SESSION_END",
    "extract_conversation_context",
    "read_stdin",
    "spawn_flush",
    "write_context_file",
]


def read_stdin() -> dict[str, Any]:
    """Read and parse JSON from stdin, with Windows backslash fix."""
    raw = sys.stdin.read()
    try:
        result: dict[str, Any] = json.loads(raw)
        return result
    except json.JSONDecodeError:
        fixed = re.sub(r'(?<!\\)\\(?!["\\])', r"\\\\", raw)
        result2: dict[str, Any] = json.loads(fixed)
        return result2


def extract_conversation_context(transcript_path: Path) -> tuple[str, int]:
    """Read JSONL transcript and extract last N conversation turns as markdown."""
    turns: list[str] = []

    with open(transcript_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            msg = entry.get("message", {})
            if isinstance(msg, dict):
                role = msg.get("role", "")
                content = msg.get("content", "")
            else:
                role = entry.get("role", "")
                content = entry.get("content", "")

            if role not in ("user", "assistant"):
                continue

            if isinstance(content, list):
                text_parts = []
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text_parts.append(block.get("text", ""))
                    elif isinstance(block, str):
                        text_parts.append(block)
                content = "\n".join(text_parts)

            if isinstance(content, str) and content.strip():
                label = "User" if role == "user" else "Assistant"
                turns.append(f"**{label}:** {content.strip()}\n")

    recent = turns[-MAX_FLUSH_TURNS:]
    context = "\n".join(recent)

    if len(context) > MAX_FLUSH_CONTEXT_CHARS:
        context = context[-MAX_FLUSH_CONTEXT_CHARS:]
        boundary = context.find("\n**")
        if boundary > 0:
            context = context[boundary + 1 :]

    return context, len(recent)


def spawn_flush(context_file: Path, session_id: str) -> None:
    """Spawn flush.py as a background process to extract knowledge."""
    flush_script = SCRIPTS_DIR / "flush.py"
    cmd = [
        "uv",
        "--directory",
        str(CLAUDE_DIR),
        "run",
        "python",
        str(flush_script),
        str(context_file),
        session_id,
    ]

    creation_flags = 0
    if sys.platform == "win32":
        creation_flags = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]

    try:
        subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creation_flags,
        )
    except Exception as e:
        import logging

        logging.error("Failed to spawn flush.py: %s", e)


def write_context_file(session_id: str, context: str, prefix: str = "flush-context") -> Path:
    """Write conversation context to a temp file for the background flush process."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).astimezone().strftime("%Y%m%d-%H%M%S")
    context_file = STATE_DIR / f"{prefix}-{session_id}-{timestamp}.md"
    context_file.write_text(context, encoding="utf-8")
    return context_file
