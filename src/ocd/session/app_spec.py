"""App spec injection for session initialization.

Reads app_spec.txt from the project root and injects it into the
session-start hook context. Skips silently when the file does not exist.

Phase 1: Simple text injection. No parsing required.
"""

from __future__ import annotations

from ocd.config import APP_SPEC_FILE, MAX_APP_SPEC_CHARS


def build_app_spec_context(max_chars: int = MAX_APP_SPEC_CHARS) -> str | None:
    """Build app spec context string for session-start injection.

    Returns None if app_spec.txt does not exist. Otherwise returns the
    file content, truncated to max_chars with a safe truncation marker.
    """
    if not APP_SPEC_FILE.is_file():
        return None

    try:
        content = APP_SPEC_FILE.read_text(encoding="utf-8")
    except OSError:
        return None

    if not content.strip():
        return None

    header = "## App Spec\n\n"
    result = f"{header}{content}"
    if len(result) <= max_chars:
        return result

    marker = "\n\n...(truncated)"
    budget = max_chars - len(header) - len(marker)
    return f"{header}{content[:budget]}{marker}"
