"""Relevance-ranked knowledge base injection using TF-IDF.

Replaces the naive full-index dump with intelligent article selection.
Deterministic, cacheable, zero external dependencies.

Usage:
    ocd kb query --relevant-to "auth redirect"
    ocd kb query --relevant-to "format command" --top-k 5
    ocd kb query --build-index
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ocd.config import (
    INDEX_FILE,
    KB_INDEX_JSON,
    KB_INJECTION_COUNT,
    KNOWLEDGE_DIR,
    OCD_DB,
    STATE_DIR,
    VEC_WEIGHT_QUALITY,
    VEC_WEIGHT_TFIDF,
    VEC_WEIGHT_VECTOR,
)
from ocd.utils import file_hash, list_wiki_articles, load_state

# ── Stop words ──────────────────────────────────────────────────────────
# Minimal set: common English words that don't contribute to relevance.
_STOP_WORDS = frozenset(
    {
        "the",
        "be",
        "to",
        "of",
        "and",
        "a",
        "in",
        "that",
        "have",
        "i",
        "it",
        "for",
        "not",
        "on",
        "with",
        "he",
        "as",
        "you",
        "do",
        "at",
        "this",
        "but",
        "his",
        "by",
        "from",
        "they",
        "we",
        "say",
        "her",
        "she",
        "or",
        "an",
        "will",
        "my",
        "one",
        "all",
        "would",
        "there",
        "their",
        "what",
        "so",
        "up",
        "out",
        "if",
        "about",
        "who",
        "get",
        "which",
        "go",
        "me",
        "when",
        "make",
        "can",
        "like",
        "time",
        "no",
        "just",
        "him",
        "know",
        "take",
        "people",
        "into",
        "year",
        "your",
        "good",
        "some",
        "could",
        "them",
        "see",
        "other",
        "than",
        "then",
        "now",
        "look",
        "only",
        "come",
        "its",
        "over",
        "think",
        "also",
        "back",
        "after",
        "use",
        "two",
        "how",
        "our",
        "work",
        "first",
        "well",
        "way",
        "even",
        "new",
        "want",
        "because",
        "any",
        "these",
        "give",
        "day",
        "most",
        "us",
        "is",
        "are",
        "was",
        "were",
        "been",
        "has",
        "had",
        "did",
        "does",
        "am",
        "being",
        "having",
        "doing",
    }
)

# Minimum relevance score threshold — below this, fall back to recent articles
_MIN_SCORE = 0.1


# ── Tokenization ─────────────────────────────────────────────────────────


def tokenize(text: str) -> list[str]:
    """Extract lowercase word tokens from text, filtering stop words."""
    words = re.findall(r"\b[a-z]{2,}\b", text.lower())
    return [w for w in words if w not in _STOP_WORDS]


# ── TF-IDF ───────────────────────────────────────────────────────────────


def _term_freq(tokens: list[str]) -> dict[str, float]:
    """Compute normalized term frequency for a token list."""
    if not tokens:
        return {}
    counts: dict[str, int] = {}
    for t in tokens:
        counts[t] = counts.get(t, 0) + 1
    total = len(tokens)
    return {t: c / total for t, c in counts.items()}


def _idf(all_docs: list[dict[str, float]]) -> dict[str, float]:
    """Compute inverse document frequency across all document term-frequency dicts."""
    n = len(all_docs)
    if n == 0:
        return {}
    doc_freq: dict[str, int] = {}
    for doc in all_docs:
        for term in doc:
            doc_freq[term] = doc_freq.get(term, 0) + 1
    return {t: math.log(n / (1 + df)) for t, df in doc_freq.items()}


def _tfidf_vector(tf: dict[str, float], idf: dict[str, float]) -> dict[str, float]:
    """Compute TF-IDF vector by multiplying term freq by inverse doc freq."""
    return {t: tf[t] * idf.get(t, 0.0) for t in tf}


def _cosine_similarity(vec_a: dict[str, float], vec_b: dict[str, float]) -> float:
    """Compute cosine similarity between two sparse vectors represented as dicts."""
    common = set(vec_a) & set(vec_b)
    if not common:
        return 0.0
    dot = sum(vec_a[t] * vec_b[t] for t in common)
    mag_a = math.sqrt(sum(v * v for v in vec_a.values()))
    mag_b = math.sqrt(sum(v * v for v in vec_b.values()))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


# ── Article parsing ──────────────────────────────────────────────────────


def _parse_frontmatter(content: str) -> dict[str, Any]:
    """Extract YAML frontmatter fields from markdown content."""
    if not content.startswith("---"):
        return {}
    end = content.find("---", 3)
    if end == -1:
        return {}
    fm = content[3:end]
    result: dict[str, Any] = {}
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
        else:
            result[key] = val
    return result


def _extract_key_points(content: str) -> str:
    """Extract the Key Points section text from an article."""
    match = re.search(r"## Key Points\s*\n(.*?)(?=\n## |\Z)", content, re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""


def _extract_details(content: str) -> str:
    """Extract the first paragraph of the Details section."""
    match = re.search(r"## Details\s*\n\s*\n(.*?)(?=\n\n|\n## |\Z)", content, re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""


# ── Index building ───────────────────────────────────────────────────────


def _build_index_from_db() -> list[dict[str, Any]] | None:
    """Read articles from ocd.db and return TF-IDF-ready entries.

    Returns None if the database doesn't exist or has no articles.
    """
    import sqlite3

    if not OCD_DB.exists():
        return None

    db = sqlite3.connect(str(OCD_DB))
    try:
        rows = db.execute(
            "SELECT path, title, tags, aliases, sources, body, hash, updated FROM articles"
        ).fetchall()
    except sqlite3.OperationalError:
        db.close()
        return None
    db.close()

    if not rows:
        return None

    import json as _json

    articles = []
    all_tfs = []
    for row in rows:
        path, title, tags_json, aliases_json, sources_json, body, hash_val, updated = row
        tags = _json.loads(tags_json) if tags_json else []
        aliases = _json.loads(aliases_json) if aliases_json else []
        sources = _json.loads(sources_json) if sources_json else []

        searchable = " ".join(
            [str(title)]
            + (tags if isinstance(tags, list) else [str(tags)])
            + (aliases if isinstance(aliases, list) else [str(aliases)])
            + (sources if isinstance(sources, list) else [str(sources)])
            + [body]
        )
        tokens = tokenize(searchable)
        tf = _term_freq(tokens)

        summary = _find_summary(path, title)
        articles.append(
            {
                "path": path,
                "title": str(title),
                "summary": summary,
                "tags": tags,
                "aliases": aliases,
                "updated": str(updated),
                "tf": tf,
                "hash": hash_val,
            }
        )
        all_tfs.append(tf)

    return articles


def build_kb_index_json(use_db: bool = True) -> dict[str, Any]:
    """Scan all KB articles and build a search index with TF-IDF metadata.

    When use_db is True and ocd.db exists, reads articles from the database
    instead of flat files. Falls back to flat files when the database is
    unavailable.

    Returns a JSON-serializable dict with article entries containing:
    - path: relative path from knowledge dir
    - title: article title from frontmatter
    - summary: one-line summary from index table
    - tags: list of tags from frontmatter
    - aliases: list of aliases from frontmatter
    - updated: date string from frontmatter
    - tokens: tokenized content (title + key points + details)
    - hash: SHA-256 hash of the article file
    """
    articles: list[dict[str, Any]] = []
    all_tfs: list[dict[str, float]] = []

    # Try DB path first when requested
    db_articles = _build_index_from_db() if use_db else None
    if db_articles is not None:
        articles = db_articles
        all_tfs = [a["tf"] for a in articles]
    else:
        for article_path in list_wiki_articles():
            rel = str(article_path.relative_to(KNOWLEDGE_DIR))
            try:
                content = article_path.read_text(encoding="utf-8")
            except OSError:
                continue

            fm = _parse_frontmatter(content)
            key_points = _extract_key_points(content)
            details = _extract_details(content)

            # Combine title, tags, aliases, key points, and first details paragraph
            title = fm.get("title", "")
            tags = fm.get("tags", [])
            aliases = fm.get("aliases", [])
            searchable = " ".join(
                [str(title)]
                + (tags if isinstance(tags, list) else [str(tags)])
                + (aliases if isinstance(aliases, list) else [str(aliases)])
                + [key_points, details]
            )
            tokens = tokenize(searchable)
            tf = _term_freq(tokens)

            # Find summary from index table
            summary = _find_summary(rel, title)

            articles.append(
                {
                    "path": rel,
                    "title": str(title),
                    "summary": summary,
                    "tags": tags if isinstance(tags, list) else [str(tags)],
                    "aliases": aliases if isinstance(aliases, list) else [str(aliases)],
                    "updated": str(fm.get("updated", "")),
                    "tf": tf,
                    "hash": file_hash(article_path),
                }
            )
            all_tfs.append(tf)

    # Compute IDF across all articles
    idf = _idf(all_tfs)

    # Compute TF-IDF vectors and attach to entries
    for entry in articles:
        entry["tfidf"] = _tfidf_vector(entry["tf"], idf)

    # Get metadata
    state = load_state()
    article_count = len(articles)
    connection_count = sum(1 for a in articles if a["path"].startswith("connections/"))

    return {
        "version": 1,
        "built_at": datetime.now(UTC).astimezone().isoformat(timespec="seconds"),
        "article_count": article_count,
        "connection_count": connection_count,
        "last_compiled": state.get("ingested", {}),
        "idf": idf,
        "articles": [
            {
                "path": a["path"],
                "title": a["title"],
                "summary": a["summary"],
                "tags": a["tags"],
                "aliases": a["aliases"],
                "updated": a["updated"],
                "tfidf": a["tfidf"],
                "hash": a["hash"],
            }
            for a in articles
        ],
    }


def _find_summary(rel_path: str, title: str) -> str:
    """Find the summary line for an article from the index table."""
    if not INDEX_FILE.exists():
        return ""
    index_content = INDEX_FILE.read_text(encoding="utf-8")
    # Look for the article's row in the index table
    for line in index_content.splitlines():
        if f"[[{rel_path.replace('.md', '')}]]" in line or str(title) in line:
            # Extract summary from pipe-delimited table row
            parts = line.split("|")
            if len(parts) >= 4:
                return parts[2].strip()
    return ""


def save_kb_index(index: dict[str, Any]) -> Path:
    """Write the KB index JSON to disk."""
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    KB_INDEX_JSON.write_text(json.dumps(index, indent=2), encoding="utf-8")
    return KB_INDEX_JSON


def load_kb_index() -> dict[str, Any] | None:
    """Load the KB index JSON from disk, or None if it doesn't exist."""
    if not KB_INDEX_JSON.exists():
        return None
    try:
        data: dict[str, Any] | None = json.loads(KB_INDEX_JSON.read_text(encoding="utf-8"))
        return data
    except (json.JSONDecodeError, OSError):
        return None


def is_kb_index_stale(index: dict[str, Any] | None) -> bool:
    """Check if the KB index needs rebuilding (missing, stale, or hashes mismatched)."""
    if index is None:
        return True
    # Check if any article has changed since the index was built
    indexed_hashes = {a["path"]: a["hash"] for a in index.get("articles", [])}
    for article_path in list_wiki_articles():
        rel = str(article_path.relative_to(KNOWLEDGE_DIR))
        if rel not in indexed_hashes or indexed_hashes[rel] != file_hash(article_path):
            return True
    # Check if articles have been added or removed
    indexed_paths = set(indexed_hashes.keys())
    current_paths = {str(p.relative_to(KNOWLEDGE_DIR)) for p in list_wiki_articles()}
    return indexed_paths != current_paths


# ── Scoring ───────────────────────────────────────────────────────────────


def score_articles(
    query: str, index: dict[str, Any], top_k: int = KB_INJECTION_COUNT
) -> list[dict[str, Any]]:
    """Score articles against a query and return the top_k most relevant.

    Returns a list of dicts with: path, title, summary, score.
    Falls back to most-recently-updated articles if no article scores
    above _MIN_SCORE.
    """
    if not query or not index.get("articles"):
        return _fallback_recent(index, top_k)

    query_tokens = tokenize(query)
    if not query_tokens:
        return _fallback_recent(index, top_k)

    query_tf = _term_freq(query_tokens)
    idf = index.get("idf", {})
    query_tfidf = _tfidf_vector(query_tf, idf)

    scored = []
    for article in index["articles"]:
        article_tfidf = article.get("tfidf", {})
        if not article_tfidf:
            continue
        score = _cosine_similarity(query_tfidf, article_tfidf)
        scored.append(
            {
                "path": article["path"],
                "title": article["title"],
                "summary": article.get("summary", ""),
                "score": score,
            }
        )

    scored.sort(key=lambda x: x["score"], reverse=True)
    top = scored[:top_k]

    # If best score is below threshold, fall back to recent articles
    if not top or top[0]["score"] < _MIN_SCORE:
        return _fallback_recent(index, top_k)

    return top


def _fallback_recent(index: dict[str, Any], top_k: int) -> list[dict[str, Any]]:
    """Return the most recently updated articles as a fallback."""
    articles = index.get("articles", [])
    sorted_articles = sorted(articles, key=lambda a: a.get("updated", ""), reverse=True)
    return [
        {
            "path": a["path"],
            "title": a["title"],
            "summary": a.get("summary", ""),
            "score": 0.0,
        }
        for a in sorted_articles[:top_k]
    ]


def hybrid_score_articles(
    query: str,
    index: dict[str, Any],
    db_path: Path | None = None,
    top_k: int = KB_INJECTION_COUNT,
) -> list[dict[str, Any]]:
    """Score articles using hybrid TF-IDF + vector + quality weighting.

    When vector support is available and ocd.db exists, combines three
    signals: TF-IDF cosine similarity, vector semantic similarity, and
    the OCD quality score. Falls back to TF-IDF + quality when vectors
    are unavailable.
    """
    import sqlite3

    # 1. Get TF-IDF scores (always available)
    tfidf_results = score_articles(query, index, top_k=min(top_k * 3, 50))

    # Build a dict of path -> tfidf_score for merging
    tfidf_scores: dict[str, float] = {r["path"]: r["score"] for r in tfidf_results}

    # 2. Get vector scores (optional)
    vec_scores: dict[str, float] = {}
    vec_available = False
    try:
        from ocd.vec import is_vec_available, search_vectors

        if is_vec_available() and db_path and db_path.exists():
            db = sqlite3.connect(str(db_path))
            try:
                results = search_vectors(db, query, top_k=min(top_k * 3, 50))
                if results:
                    # Convert cosine distance to similarity: similarity = 1 - distance
                    vec_scores = {path: 1.0 - dist for path, dist in results}
                    vec_available = True
            except sqlite3.OperationalError:
                pass
            db.close()
    except ImportError:
        pass  # vec extras not installed

    # 3. Get quality scores from articles table (optional)
    quality_scores: dict[str, float] = {}
    if db_path and db_path.exists():
        db = sqlite3.connect(str(db_path))
        try:
            rows = db.execute("SELECT path, score FROM articles").fetchall()
            quality_scores = {r[0]: r[1] for r in rows}
        except sqlite3.OperationalError:
            pass
        db.close()

    # 4. Collect all candidate paths
    all_paths = set(tfidf_scores) | set(vec_scores) | set(quality_scores)

    # 5. Determine weights (redistribute if a signal is missing)
    w_tfidf = VEC_WEIGHT_TFIDF
    w_vec = VEC_WEIGHT_VECTOR
    w_quality = VEC_WEIGHT_QUALITY

    if not vec_available:
        # Redistribute vector weight to TF-IDF and quality
        w_tfidf = VEC_WEIGHT_TFIDF + VEC_WEIGHT_VECTOR * 0.5
        w_quality = VEC_WEIGHT_QUALITY + VEC_WEIGHT_VECTOR * 0.5
        w_vec = 0.0

    # 6. Normalize each signal to [0, 1] and compute weighted scores
    def _normalize(scores: dict[str, float]) -> dict[str, float]:
        if not scores:
            return {}
        max_val = max(scores.values())
        if max_val == 0:
            return {k: 0.0 for k in scores}
        return {k: v / max_val for k, v in scores.items()}

    norm_tfidf = _normalize(tfidf_scores)
    norm_vec = _normalize(vec_scores)
    norm_quality = _normalize(quality_scores)

    # Merge article metadata from index for title/summary
    index_lookup: dict[str, dict[str, Any]] = {a["path"]: a for a in index.get("articles", [])}

    merged = []
    for path in all_paths:
        info = index_lookup.get(path, {})
        final_score = (
            w_tfidf * norm_tfidf.get(path, 0.0)
            + w_vec * norm_vec.get(path, 0.0)
            + w_quality * norm_quality.get(path, 0.0)
        )
        merged.append(
            {
                "path": path,
                "title": info.get("title", path.split("/")[-1].replace(".md", "")),
                "summary": info.get("summary", ""),
                "score": final_score,
            }
        )

    merged.sort(key=lambda x: x["score"], reverse=True)
    return merged[:top_k]


# ── Health card ──────────────────────────────────────────────────────────


def build_health_card(index: dict[str, Any]) -> str:
    """Build a compact one-line KB health summary for context injection."""
    article_count = index.get("article_count", 0)
    connection_count = index.get("connection_count", 0)
    built_at = index.get("built_at", "unknown")[:10]  # Just the date part

    # Check for lint warnings from state
    state = load_state()
    last_lint = state.get("last_lint")
    warning_count = 0
    if last_lint and isinstance(last_lint, dict):
        warning_count = last_lint.get("warning_count", 0)

    return (
        f"KB: {article_count} articles, {connection_count} connections, "
        f"last compiled {built_at}, {warning_count} lint warnings"
    )


# ── Article loading ──────────────────────────────────────────────────────


def load_articles_for_injection(scored: list[dict[str, Any]], max_chars: int = 8000) -> str:
    """Load the full text of scored articles for context injection.

    Reads only the article files that were selected by score_articles,
    not the entire KB. Truncates to max_chars if needed.
    """
    parts = []
    total = 0

    for entry in scored:
        path = KNOWLEDGE_DIR / entry["path"]
        if not path.exists():
            # Try adding .md extension
            path = KNOWLEDGE_DIR / f"{entry['path']}.md"
        if not path.exists():
            continue

        try:
            content = path.read_text(encoding="utf-8")
        except OSError:
            continue

        # Include the article with its path as header
        header = f"## {entry['path'].replace('.md', '')}"
        if entry.get("score", 0) > 0:
            header += f" (relevance: {entry['score']:.2f})"
        elif entry.get("summary"):
            header += f" — {entry['summary']}"

        article_text = f"{header}\n\n{content}"
        if total + len(article_text) > max_chars:
            # Truncate this article to fit
            remaining = max_chars - total
            if remaining > 200:
                article_text = article_text[:remaining] + "\n\n...(truncated)"
                parts.append(article_text)
            break
        parts.append(article_text)
        total += len(article_text)

    return "\n\n---\n\n".join(parts)


# ── Context injection ───────────────────────────────────────────────────


def build_relevant_context(
    query: str = "",
    top_k: int = KB_INJECTION_COUNT,
    max_chars: int = 8000,
    use_vectors: bool = False,
) -> str:
    """Build the context string for session start injection.

    Uses relevance scoring if a query is provided, otherwise falls back
    to most recently updated articles. Includes a KB health card header.
    When use_vectors is True and vector support is available, uses hybrid
    scoring (TF-IDF + vector + quality) instead of TF-IDF alone.
    """
    from datetime import UTC, datetime

    index = load_kb_index()

    # Rebuild index if missing or stale
    if index is None or is_kb_index_stale(index):
        index = build_kb_index_json()
        save_kb_index(index)

    # Score articles — use hybrid search if requested
    if use_vectors:
        scored = hybrid_score_articles(query, index, db_path=OCD_DB, top_k=top_k)
    else:
        scored = score_articles(query, index, top_k)

    # Build health card
    health_card = build_health_card(index)
    today = datetime.now(UTC).astimezone().strftime("%A, %B %d, %Y")

    # Load article content
    article_content = load_articles_for_injection(scored, max_chars)

    # Assemble: date + health card + articles
    parts = [
        f"## Today\n{today}",
        health_card,
        article_content,
    ]
    context = "\n\n---\n\n".join(parts)

    # Hard cap
    if len(context) > max_chars:
        context = context[:max_chars] + "\n\n...(truncated)"

    return context


# ── CLI ──────────────────────────────────────────────────────────────────


def main() -> None:
    """Entry point for ocd kb query command."""
    parser = argparse.ArgumentParser(
        description="Query the knowledge base using TF-IDF relevance scoring"
    )
    parser.add_argument(
        "--relevant-to",
        type=str,
        required=True,
        help="Search query to find relevant articles",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=KB_INJECTION_COUNT,
        help=f"Number of articles to return (default: {KB_INJECTION_COUNT})",
    )
    parser.add_argument(
        "--build-index",
        action="store_true",
        help="Rebuild the KB index and exit",
    )
    args = parser.parse_args()

    if args.build_index:
        print("Building KB index...")
        index = build_kb_index_json()
        path = save_kb_index(index)
        print(f"Index saved to {path} ({len(index['articles'])} articles)")
        return

    loaded = load_kb_index()
    if loaded is None or is_kb_index_stale(loaded):
        print("Building KB index (first time or stale)...", file=sys.stderr)
        loaded = build_kb_index_json()
        save_kb_index(loaded)

    scored = score_articles(args.relevant_to, loaded, args.top_k)

    if not scored:
        print("No relevant articles found.")
        return

    print(f"Top {len(scored)} articles for: '{args.relevant_to}'\n")
    for entry in scored:
        score_str = f" ({entry['score']:.2f})" if entry.get("score", 0) > 0 else ""
        title = entry.get("title", entry["path"])
        summary = entry.get("summary", "")
        print(f"  {title}{score_str}")
        if summary:
            print(f"    {summary}")
        print(f"    → {entry['path']}")
        print()


if __name__ == "__main__":
    main()
