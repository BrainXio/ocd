"""SessionStart hook - injects relevant knowledge base context into every conversation.

Uses TF-IDF relevance scoring to inject only the most pertinent articles
instead of the full KB index. Falls back to most recently updated articles
when no query is available.
"""

from __future__ import annotations

import json

from ocd.config import MAX_RELEVANT_CONTEXT_CHARS
from ocd.relevance import build_relevant_context


def main() -> None:
    context = build_relevant_context(
        query="",
        max_chars=MAX_RELEVANT_CONTEXT_CHARS,
    )

    output = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": context,
        }
    }

    print(json.dumps(output))


if __name__ == "__main__":
    main()
