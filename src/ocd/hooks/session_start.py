"""SessionStart hook — injects relevant knowledge base context into every conversation.

Uses TF-IDF relevance scoring to inject only the most pertinent articles
instead of the full KB index. Falls back to most recently updated articles
when no query is available. Also injects app spec, standards hash reference,
and session state card for post-compaction recovery.

Invoked via `ocd hook session-start`.
"""

from __future__ import annotations

import json
import sys

from ocd.config import MAX_CONTEXT_CHARS, MAX_RELEVANT_CONTEXT_CHARS
from ocd.kb.relevance import build_relevant_context
from ocd.routing.standards import get_standards_reference, verify_standards_hash
from ocd.session.app_spec import build_app_spec_context
from ocd.session.session_card import load_session_card


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

    # Inject app spec
    app_spec = build_app_spec_context()
    if app_spec:
        context = f"{context}\n\n---\n\n{app_spec}"

    # Inject last session card for post-compaction recovery
    card = load_session_card()
    if card:
        context = f"{context}\n\n---\n\n## Last Session\n{card}"

    # Hard-cap safety net
    if len(context) > MAX_CONTEXT_CHARS:
        context = context[:MAX_CONTEXT_CHARS] + "\n\n...(truncated)"

    output = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": context,
        }
    }

    print(json.dumps(output))


if __name__ == "__main__":
    main()
