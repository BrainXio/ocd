"""PreCompact hook — captures conversation transcript before auto-compaction.

When Claude Code's context window fills up, it auto-compacts (summarizes and
discards detail). This hook fires BEFORE that happens, extracting conversation
context and spawning flush to extract knowledge that would otherwise
be lost to summarization.

Invoked via `ocd hook pre-compact`.

The hook itself does NO API calls - only local file I/O for speed (<10s).
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from ocd.config import FLUSH_LOG_FILE, MIN_TURNS_PRE_COMPACT, STATE_DIR
from ocd.hooks.hookslib import (
    extract_conversation_context,
    parse_stdin_json,
    spawn_flush,
    write_context_file,
)

_log: logging.Logger = logging.getLogger(__name__)


def main() -> None:
    # Recursion guard: if spawned by flush (which calls Agent SDK → Claude Code → hooks)
    if os.environ.get("CLAUDE_INVOKED_BY"):
        return

    STATE_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=str(FLUSH_LOG_FILE),
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [pre-compact] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    hook_input = parse_stdin_json()

    session_id = hook_input.get("session_id", "unknown")
    transcript_path_str = hook_input.get("transcript_path", "")

    logging.info("PreCompact fired: session=%s", session_id)

    if not transcript_path_str or not isinstance(transcript_path_str, str):
        logging.info("SKIP: no transcript path")
        return

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

    if turn_count < MIN_TURNS_PRE_COMPACT:
        logging.info("SKIP: only %d turns (min %d)", turn_count, MIN_TURNS_PRE_COMPACT)
        return

    context_file = write_context_file(session_id, context, prefix="flush-context")
    spawn_flush(context_file, session_id)
    logging.info(
        "Spawned flush for session %s (%d turns, %d chars)",
        session_id,
        turn_count,
        len(context),
    )


if __name__ == "__main__":
    main()
