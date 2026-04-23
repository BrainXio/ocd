"""SessionStart hook — injects relevant knowledge base context into every conversation.

Uses TF-IDF relevance scoring to inject only the most pertinent articles
instead of the full KB index. Falls back to most recently updated articles
when no query is available. Also includes standards hash reference and
session state card for post-compaction recovery.

Invoked via `ocd hook session-start`.
"""

from __future__ import annotations

import json
import sys

from ocd.config import MAX_RELEVANT_CONTEXT_CHARS
from ocd.relevance import build_relevant_context
from ocd.session_card import load_session_card
from ocd.standards import get_standards_reference, verify_standards_hash


def main() -> None:
    context = build_relevant_context(
        query="",
        max_chars=MAX_RELEVANT_CONTEXT_CHARS,
    )

    # Verify standards hash and add reference line
    verification = verify_standards_hash()
    if verification.get("error"):
        pass
    elif not verification["match"]:
        print(
            f"WARNING: Standards hash mismatch! "
            f"Stored: {verification['stored_hash']}, "
            f"Computed: {verification['computed_hash']}. "
            f"Run 'ocd standards --update' to fix.",
            file=sys.stderr,
        )
    else:
        ref = get_standards_reference()
        if ref:
            context = f"{context}\n\n---\n\n{ref}"

    # Inject last session card for post-compaction recovery
    card = load_session_card()
    if card:
        context = f"{context}\n\n---\n\n## Last Session\n{card}"

    output = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": context,
        }
    }

    print(json.dumps(output))


if __name__ == "__main__":
    main()
