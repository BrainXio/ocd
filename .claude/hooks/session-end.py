"""
SessionEnd hook - captures conversation transcript for memory extraction.

When a Claude Code session ends, this hook reads the transcript path from
stdin, extracts conversation context, and spawns flush.py as a background
process to extract knowledge into the daily log.

The hook itself does NO API calls - only local file I/O for speed (<10s).
"""

from __future__ import annotations

import logging
import os
import sys

from hookslib import (
    MIN_TURNS_SESSION_END,
    extract_conversation_context,
    read_stdin,
    spawn_flush,
    write_context_file,
)

# Recursion guard: if we were spawned by flush.py (which calls Agent SDK,
# which runs Claude Code, which would fire this hook again), exit immediately.
if os.environ.get("CLAUDE_INVOKED_BY"):
    sys.exit(0)

# Set up file-based logging so we can verify the background process ran.
from config import FLUSH_LOG_FILE, STATE_DIR

STATE_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=str(FLUSH_LOG_FILE),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [hook] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def main() -> None:
    hook_input = read_stdin()

    session_id = hook_input.get("session_id", "unknown")
    source = hook_input.get("source", "unknown")
    transcript_path_str = hook_input.get("transcript_path", "")

    logging.info("SessionEnd fired: session=%s source=%s", session_id, source)

    if not transcript_path_str or not isinstance(transcript_path_str, str):
        logging.info("SKIP: no transcript path")
        return

    from pathlib import Path

    transcript_path = Path(transcript_path_str)
    if not transcript_path.exists():
        logging.info("SKIP: transcript missing: %s", transcript_path_str)
        return

    try:
        context, turn_count = extract_conversation_context(transcript_path)
    except Exception as e:
        logging.error("Context extraction failed: %s", e)
        return

    if not context.strip():
        logging.info("SKIP: empty context")
        return

    if turn_count < MIN_TURNS_SESSION_END:
        logging.info("SKIP: only %d turns (min %d)", turn_count, MIN_TURNS_SESSION_END)
        return

    context_file = write_context_file(
        session_id, context, prefix="session-flush"
    )
    spawn_flush(context_file, session_id)
    logging.info(
        "Spawned flush.py for session %s (%d turns, %d chars)",
        session_id, turn_count, len(context),
    )


if __name__ == "__main__":
    main()
