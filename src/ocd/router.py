"""Lightweight task router — maps user requests to optimal agents.

Replaces main LLM agent-selection reasoning with a deterministic keyword
matcher. Scores a user query against agent manifest keywords and returns
the top 1-3 agents. Zero tokens, zero API calls, <50ms.

Usage:
    ocd-route "find dead code and unused imports"
    ocd-route "security scan" --max 3
    ocd-route --build-manifest
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ocd.config import AGENTS_DIR, MANIFEST_FILE, STATE_DIR
from ocd.relevance import tokenize

# ── Manifest building ───────────────────────────────────────────────────


def _parse_agent_frontmatter(content: str) -> dict[str, Any]:
    """Extract YAML frontmatter from an agent .md file."""
    if not content.startswith("---"):
        return {}
    end = content.find("---", 3)
    if end == -1:
        return {}
    fm = content[3:end]
    result: dict[str, Any] = {}
    # Fields that should be parsed as lists even without brackets
    list_fields = {"tools", "tags", "aliases"}
    for line in fm.strip().splitlines():
        line = line.strip()
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if val.startswith("[") and val.endswith("]"):
            items = [v.strip().strip('"').strip("'") for v in val[1:-1].split(",")]
            result[key] = [i for i in items if i]
        elif key in list_fields and "," in val:
            result[key] = [v.strip().strip('"').strip("'") for v in val.split(",") if v.strip()]
        else:
            result[key] = val
    return result


def _extract_scope_summary(content: str) -> str:
    """Extract the first sentence of the Scope section for keyword derivation."""
    match = re.search(r"## Scope\s*\n(.*?)(?=\n## |\Z)", content, re.DOTALL)
    if not match:
        return ""
    scope_text = match.group(1).strip()
    # Take first sentence (up to first period or newline)
    first_sentence = re.split(r"\.\s|\n", scope_text, maxsplit=1)[0]
    return first_sentence.strip()


def _extract_keywords(description: str, scope_summary: str) -> list[str]:
    """Derive keywords from description and scope summary via tokenization."""
    combined = f"{description} {scope_summary}"
    tokens = tokenize(combined)
    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for t in tokens:
        if t not in seen:
            seen.add(t)
            unique.append(t)
    return unique


def build_manifest() -> dict[str, Any]:
    """Scan .claude/agents/ and build a keyword-indexed agent manifest.

    Returns a JSON-serializable dict with one entry per agent containing
    name, description, keywords, tools, and scope_summary.
    """
    agents_dir = AGENTS_DIR
    if not agents_dir.exists():
        return {"version": 1, "built_at": "", "agents": []}

    agents: list[dict[str, Any]] = []
    for md_file in sorted(agents_dir.glob("*.md")):
        try:
            content = md_file.read_text(encoding="utf-8")
        except OSError:
            continue

        fm = _parse_agent_frontmatter(content)
        name = str(fm.get("name", md_file.stem))
        description = str(fm.get("description", ""))
        tools_raw = fm.get("tools", "")
        if isinstance(tools_raw, str):
            tools = [t.strip() for t in tools_raw.split(",") if t.strip()]
        else:
            tools = list(tools_raw)

        scope_summary = _extract_scope_summary(content)
        keywords = _extract_keywords(description, scope_summary)

        agents.append(
            {
                "name": name,
                "description": description,
                "keywords": keywords,
                "tools": tools,
                "scope_summary": scope_summary,
            }
        )

    return {
        "version": 1,
        "built_at": datetime.now(UTC).astimezone().isoformat(timespec="seconds"),
        "agents": agents,
    }


def save_manifest(manifest: dict[str, Any]) -> Path:
    """Write the manifest JSON to disk."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST_FILE.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return Path(MANIFEST_FILE)


def load_manifest() -> dict[str, Any] | None:
    """Load the manifest JSON from disk, or None if missing."""
    if not MANIFEST_FILE.exists():
        return None
    try:
        data: dict[str, Any] | None = json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
        return data
    except (json.JSONDecodeError, OSError):
        return None


# ── Routing ───────────────────────────────────────────────────────────────


def route_query(query: str, manifest: dict[str, Any], max_agents: int = 3) -> list[dict[str, Any]]:
    """Score agents against a query and return the top matches.

    Each agent's score is the count of query tokens that appear in its
    keyword list. Agents with score 0 are excluded. Returns up to
    max_agents sorted by score descending.
    """
    if not query or not manifest.get("agents"):
        return []

    query_tokens = set(tokenize(query))
    if not query_tokens:
        return []

    scored: list[dict[str, Any]] = []
    for agent in manifest["agents"]:
        agent_keywords = set(agent.get("keywords", []))
        hits = len(query_tokens & agent_keywords)
        if hits > 0:
            scored.append(
                {
                    "name": agent["name"],
                    "description": agent.get("description", ""),
                    "score": hits,
                    "tools": agent.get("tools", []),
                }
            )

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:max_agents]


# ── CLI ──────────────────────────────────────────────────────────────────


def main() -> None:
    """Entry point for ocd-route command."""
    parser = argparse.ArgumentParser(description="Route a user request to the optimal agent(s)")
    parser.add_argument("query", nargs="?", help="User request to route")
    parser.add_argument(
        "--max",
        type=int,
        default=3,
        help="Maximum number of agents to return (default: 3)",
    )
    parser.add_argument(
        "--build-manifest",
        action="store_true",
        help="Rebuild the agent manifest and exit",
    )
    args = parser.parse_args()

    if args.build_manifest:
        print("Building agent manifest...")
        manifest = build_manifest()
        path = save_manifest(manifest)
        print(f"Manifest saved to {path} ({len(manifest['agents'])} agents)")
        return

    if not args.query:
        parser.error("query is required unless --build-manifest is used")

    loaded = load_manifest()
    if loaded is None:
        print("Building agent manifest (first time)...", file=sys.stderr)
        loaded = build_manifest()
        save_manifest(loaded)

    results = route_query(args.query, loaded, args.max)

    if not results:
        print("No matching agents found.")
        return

    for entry in results:
        print(f"  {entry['name']} (score: {entry['score']})")


if __name__ == "__main__":
    main()
