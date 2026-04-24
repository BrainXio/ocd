"""Semantic vector memory for the knowledge base.

Adds sqlite-vec virtual tables and fastembed embeddings to knowledge.db,
enabling hybrid search (vector + TF-IDF + quality scoring).

Requires optional ``vec`` extras: ``uv sync --extra vec``.
When extras are not installed, all functions degrade gracefully —
vector operations return None and search falls back to TF-IDF.

Usage:
    ocd vec rebuild            # regenerate all embeddings
    ocd vec rebuild --force    # force rebuild even if model changed
    ocd vec search <query>     # semantic search
    ocd vec status             # show vector index status
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ocd.config import VEC_DIMENSIONS, VEC_EMBEDDING_MODEL, WIKI_DB

# ── Schema ───────────────────────────────────────────────────────────────────

VEC_SCHEMA = """
CREATE TABLE IF NOT EXISTS vec_metadata(
    rowid INTEGER PRIMARY KEY,
    article_path TEXT NOT NULL UNIQUE,
    model_name TEXT NOT NULL,
    dims INTEGER NOT NULL,
    created TEXT NOT NULL
);
"""

# vec0 virtual table is created separately after loading the extension,
# because CREATE VIRTUAL TABLE requires the extension to be loaded first.

# ── Availability check ────────────────────────────────────────────────────────


def is_vec_available() -> bool:
    """Check whether both sqlite-vec and fastembed are importable."""
    try:
        import sqlite_vec  # type: ignore[import-not-found]  # noqa: F401
        from fastembed import TextEmbedding  # type: ignore[import-not-found]  # noqa: F401

        return True
    except ImportError:
        return False


# ── Lazy model singleton ─────────────────────────────────────────────────────

_model: Any = None


def _get_model() -> Any:
    """Lazy singleton for the embedding model.

    Returns None if fastembed is not installed.
    """
    global _model
    if _model is None:
        try:
            from fastembed import TextEmbedding

            _model = TextEmbedding(model_name=VEC_EMBEDDING_MODEL)
        except ImportError:
            return None
    return _model


# ── Schema creation ──────────────────────────────────────────────────────────


def ensure_vec_schema(db: sqlite3.Connection) -> bool:
    """Create vec_metadata table and knowledge_vectors virtual table.

    Returns True if vector support is available and schema was created,
    False if sqlite-vec is not available.
    """
    try:
        import sqlite_vec
    except ImportError:
        return False

    try:
        db.enable_load_extension(True)
        sqlite_vec.load(db)
        db.enable_load_extension(False)
    except sqlite3.OperationalError:
        return False

    db.executescript(VEC_SCHEMA)
    db.execute(
        "CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_vectors "
        f"USING vec0(embedding float[{VEC_DIMENSIONS}])",
    )
    db.commit()
    return True


# ── Embedding ────────────────────────────────────────────────────────────────


def embed_texts(texts: list[str]) -> list[list[float]] | None:
    """Generate embeddings for a list of texts.

    Returns a list of 384-dim float vectors, or None if fastembed
    is not installed.
    """
    model = _get_model()
    if model is None:
        return None

    embeddings = list(model.embed(texts))
    return [e.tolist() for e in embeddings]


# ── Insert vectors ───────────────────────────────────────────────────────────


def insert_vectors(
    db: sqlite3.Connection,
    rows: list[tuple[str, str]],
) -> int:
    """Embed and insert vectors for (article_path, text) pairs.

    Returns the number of vectors inserted, or 0 if unavailable.
    """
    try:
        import sqlite_vec
    except ImportError:
        return 0

    # Ensure extension is loaded
    try:
        db.enable_load_extension(True)
        sqlite_vec.load(db)
        db.enable_load_extension(False)
    except sqlite3.OperationalError:
        return 0

    embeddings = embed_texts([text for _, text in rows])
    if embeddings is None:
        return 0

    from sqlite_vec import serialize_float32

    now = datetime.now(UTC).isoformat(timespec="seconds")
    count = 0

    for (article_path, _text), embedding in zip(rows, embeddings, strict=True):
        vec_bytes = serialize_float32(embedding)

        # Delete existing row for this path if re-inserting
        existing = db.execute(
            "SELECT rowid FROM vec_metadata WHERE article_path = ?",
            (article_path,),
        ).fetchone()
        if existing is not None:
            db.execute("DELETE FROM knowledge_vectors WHERE rowid = ?", (existing[0],))
            db.execute("DELETE FROM vec_metadata WHERE article_path = ?", (article_path,))

        # Insert metadata first to get the rowid
        db.execute(
            "INSERT INTO vec_metadata(article_path, model_name, dims, created) VALUES (?, ?, ?, ?)",
            (article_path, VEC_EMBEDDING_MODEL, VEC_DIMENSIONS, now),
        )
        rowid = db.execute(
            "SELECT rowid FROM vec_metadata WHERE article_path = ?",
            (article_path,),
        ).fetchone()[0]

        # Insert vector with matching rowid
        db.execute(
            "INSERT INTO knowledge_vectors(rowid, embedding) VALUES (?, ?)",
            (rowid, vec_bytes),
        )
        count += 1

    db.commit()
    return count


# ── Search ───────────────────────────────────────────────────────────────────


def search_vectors(
    db: sqlite3.Connection,
    query_text: str,
    top_k: int = 10,
) -> list[tuple[str, float]] | None:
    """Search for articles similar to query_text using vector embeddings.

    Returns list of (article_path, cosine_distance) tuples sorted by
    similarity, or None if vector support is unavailable.
    """
    try:
        import sqlite_vec
    except ImportError:
        return None

    try:
        db.enable_load_extension(True)
        sqlite_vec.load(db)
        db.enable_load_extension(False)
    except sqlite3.OperationalError:
        return None

    embeddings = embed_texts([query_text])
    if embeddings is None:
        return None

    from sqlite_vec import serialize_float32

    query_vec = serialize_float32(embeddings[0])

    rows = db.execute(
        """
        SELECT vm.article_path, kv.distance
        FROM knowledge_vectors kv
        JOIN vec_metadata vm ON kv.rowid = vm.rowid
        WHERE kv.embedding MATCH ?
        ORDER BY kv.distance
        LIMIT ?
        """,
        (query_vec, top_k),
    ).fetchall()

    return [(row[0], row[1]) for row in rows]


# ── Rebuild ──────────────────────────────────────────────────────────────────


def rebuild_vectors(db_path: Path, force: bool = False) -> int:
    """Full rebuild of all vector embeddings from the articles table.

    Returns the number of vectors rebuilt.
    Raises ValueError if the embedding model has changed and force is False.
    """
    db = sqlite3.connect(str(db_path))
    try:
        if not ensure_vec_schema(db):
            db.close()
            return 0

        # Check model change gate
        existing = db.execute("SELECT DISTINCT model_name FROM vec_metadata").fetchall()
        if existing and existing[0][0] != VEC_EMBEDDING_MODEL and not force:
            db.close()
            msg = (
                f"Embedding model changed from '{existing[0][0]}' to "
                f"'{VEC_EMBEDDING_MODEL}'. Use --force to rebuild."
            )
            raise ValueError(msg)

        # Clear existing vectors
        db.execute("DELETE FROM knowledge_vectors")
        db.execute("DELETE FROM vec_metadata")
        db.commit()

        # Re-embed all articles
        rows = db.execute("SELECT path, body FROM articles").fetchall()
        if not rows:
            db.close()
            return 0

        count = insert_vectors(db, [(r[0], r[1]) for r in rows])
        db.close()
        return count
    except Exception:
        db.close()
        raise


# ── Status ───────────────────────────────────────────────────────────────────


def vec_status(db_path: Path) -> dict[str, Any]:
    """Return status information about the vector index."""
    available = is_vec_available()
    status: dict[str, Any] = {"available": available}

    if not available:
        return status

    if not db_path.exists():
        status["db_exists"] = False
        return status

    db = sqlite3.connect(str(db_path))
    try:
        count = db.execute("SELECT COUNT(*) FROM vec_metadata").fetchone()[0]
        model = db.execute("SELECT DISTINCT model_name FROM vec_metadata LIMIT 1").fetchone()
        status["db_exists"] = True
        status["embedding_count"] = count
        status["model"] = model[0] if model else None
    except sqlite3.OperationalError:
        status["db_exists"] = True
        status["embedding_count"] = 0
        status["model"] = None
    finally:
        db.close()

    return status


# ── CLI entry point ──────────────────────────────────────────────────────────


def main() -> None:
    """Entry point for ocd vec command."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        prog="ocd-vec",
        description="Vector embedding operations for the knowledge base",
    )
    sub = parser.add_subparsers(dest="vec_command", help="Vector subcommands")

    rebuild_parser = sub.add_parser("rebuild", help="Rebuild all vector embeddings")
    rebuild_parser.add_argument(
        "--force",
        action="store_true",
        help="Force rebuild even if embedding model changed",
    )

    search_parser = sub.add_parser("search", help="Search knowledge base with vectors")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of results (default: 5)",
    )

    sub.add_parser("status", help="Show vector index status")

    args = parser.parse_args()

    if args.vec_command == "rebuild":
        if not is_vec_available():
            print("Vector support not available. Install vec extras: uv sync --extra vec")
            sys.exit(1)
        try:
            count = rebuild_vectors(WIKI_DB, force=args.force)
            print(f"Rebuilt {count} vector embeddings")
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.vec_command == "search":
        if not is_vec_available():
            print("Vector support not available. Install vec extras: uv sync --extra vec")
            sys.exit(1)
        db = sqlite3.connect(str(WIKI_DB))
        try:
            results = search_vectors(db, args.query, top_k=args.top_k)
        except sqlite3.OperationalError:
            print("No vector index found. Run 'ocd vec rebuild' first.")
            db.close()
            sys.exit(1)
        db.close()
        if results:
            for path, dist in results:
                print(f"  {path} (distance={dist:.4f})")
        else:
            print("No results found.")

    elif args.vec_command == "status":
        info = vec_status(WIKI_DB)
        print(f"Vector support: {'available' if info['available'] else 'not installed'}")
        if info.get("db_exists"):
            print(f"  Embeddings: {info.get('embedding_count', 0)}")
            if info.get("model"):
                print(f"  Model: {info['model']}")
        elif info.get("available"):
            print("  No vector index found. Run 'ocd vec rebuild' to create one.")

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
