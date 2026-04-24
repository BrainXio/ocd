"""Session state card — compact context snapshot for post-compaction recovery.

Auto-generates a 200-300 token session card after every file modification.
Captures: files modified, test results, lint status, KB health, current task.
Replaces full history replay after compaction (~15,000-20,000 tokens saved).

Size hard-capped at 1,200 chars (~300 tokens). FIFO eviction of oldest entries
when the card exceeds the cap.
"""

from __future__ import annotations

from datetime import UTC, datetime

from ocd.config import (
    KB_INDEX_JSON,
    MANIFEST_FILE,
    MAX_SESSION_CARD_CHARS,
    SESSION_CARD_FILE,
    STATE_DIR,
)
from ocd.kb.relevance import build_health_card, load_kb_index


def build_session_card() -> str:
    """Build a fresh session card from current project state.

    Gathers: KB health, standards reference, manifest reference.
    """
    parts: list[str] = []

    # KB health
    if KB_INDEX_JSON.exists():
        index = load_kb_index()
        if index is not None:
            health = build_health_card(index)
            if health:
                parts.append(health)

    # Standards reference
    from ocd.routing.standards import get_standards_reference

    ref = get_standards_reference()
    if ref:
        parts.append(ref)

    # Manifest reference
    if MANIFEST_FILE.exists():
        parts.append(f"Manifest: {MANIFEST_FILE.name}")

    return "\n".join(parts)


def update_session_card(file_path: str, action: str = "edit") -> None:
    """Update the session card after a file modification.

    Appends an entry for the file change. If the card exceeds
    MAX_SESSION_CARD_CHARS, evicts oldest entries (FIFO) until
    it fits.
    """
    STATE_DIR.mkdir(parents=True, exist_ok=True)

    # Read existing card
    existing = ""
    if SESSION_CARD_FILE.exists():
        existing = SESSION_CARD_FILE.read_text(encoding="utf-8")

    # Build new entry
    timestamp = datetime.now(UTC).strftime("%H:%M")
    entry = f"{timestamp} {action}: {file_path}"

    # Append entry
    lines = existing.splitlines() if existing else []
    lines.append(entry)

    # FIFO eviction: remove oldest entries until within size limit
    while len("\n".join(lines)) > MAX_SESSION_CARD_CHARS and len(lines) > 1:
        lines.pop(0)

    # Write back
    SESSION_CARD_FILE.write_text("\n".join(lines), encoding="utf-8")


def load_session_card() -> str | None:
    """Load the last session card, or None if missing."""
    if not SESSION_CARD_FILE.exists():
        return None
    content = SESSION_CARD_FILE.read_text(encoding="utf-8").strip()
    return content if content else None
