"""Standards-as-Reference — hash-gated access to the Nine Standards.

Replaces full standards text (~7,678 chars / ~1,919 tokens) with a short
version+hash reference (~15 tokens). The full text lives in
.claude/skills/ocd/stand.md and is injected on demand via `Read`.

Usage:
    ocd-standards              # print the current reference line
    ocd-standards --verify     # verify hash matches content, warn on mismatch
    ocd-standards --update     # recompute and update the hash in frontmatter
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from typing import Any

from ocd.config import STANDARDS_FILE


def _extract_frontmatter_and_body(content: str) -> tuple[dict[str, str], str]:
    """Parse YAML frontmatter from a markdown file. Returns (metadata, body)."""
    if not content.startswith("---"):
        return {}, content
    end = content.find("---", 3)
    if end == -1:
        return {}, content
    fm_text = content[3:end].strip()
    meta: dict[str, str] = {}
    for line in fm_text.splitlines():
        line = line.strip()
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        meta[key.strip()] = val.strip().strip('"').strip("'")
    body = content[end + 3 :].strip()
    return meta, body


def compute_hash(text: str) -> str:
    """Compute SHA-256 hash of text, truncated to 16 hex chars."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def compute_standards_hash() -> str | None:
    """Read standards.md and compute hash of the body (excluding frontmatter).

    Returns None if standards.md doesn't exist.
    """
    if not STANDARDS_FILE.exists():
        return None
    content = STANDARDS_FILE.read_text(encoding="utf-8")
    _, body = _extract_frontmatter_and_body(content)
    return compute_hash(body)


def get_standards_version() -> str | None:
    """Read the version from standards.md frontmatter.

    Returns None if standards.md doesn't exist.
    """
    if not STANDARDS_FILE.exists():
        return None
    content = STANDARDS_FILE.read_text(encoding="utf-8")
    meta, _ = _extract_frontmatter_and_body(content)
    return meta.get("version")


def get_standards_reference() -> str:
    """Return a one-line reference like 'ocd-standards:v1.0 [abc123...]'.

    Returns an empty string if standards.md doesn't exist.
    """
    version = get_standards_version()
    hash_val = compute_standards_hash()
    if version is None or hash_val is None:
        return ""
    return f"ocd-standards:v{version} [{hash_val}]"


def verify_standards_hash() -> dict[str, Any]:
    """Verify that the hash in frontmatter matches the actual content hash.

    Returns a dict with:
      - 'match': bool — whether the stored and computed hashes match
      - 'stored_hash': the hash stored in frontmatter (or None)
      - 'computed_hash': the hash computed from the content
      - 'version': the version from frontmatter
    """
    if not STANDARDS_FILE.exists():
        return {
            "match": False,
            "stored_hash": None,
            "computed_hash": None,
            "version": None,
            "error": "standards.md not found",
        }

    content = STANDARDS_FILE.read_text(encoding="utf-8")
    meta, body = _extract_frontmatter_and_body(content)
    stored_hash = meta.get("hash", "")
    computed_hash = compute_hash(body)
    version = meta.get("version", "")

    return {
        "match": stored_hash == computed_hash,
        "stored_hash": stored_hash,
        "computed_hash": computed_hash,
        "version": version,
    }


def update_standards_hash() -> str | None:
    """Recompute hash of standards.md body and update the frontmatter.

    Returns the new hash, or None if standards.md doesn't exist.
    """
    if not STANDARDS_FILE.exists():
        return None

    content = STANDARDS_FILE.read_text(encoding="utf-8")
    meta, body = _extract_frontmatter_and_body(content)
    new_hash = compute_hash(body)
    version = meta.get("version", "1.0")

    # Rebuild file with updated hash
    new_frontmatter = f'---\nversion: "{version}"\nhash: "{new_hash}"\n---\n\n{body}\n'
    STANDARDS_FILE.write_text(new_frontmatter, encoding="utf-8")
    return new_hash


def main() -> None:
    """Entry point for ocd-standards command."""
    parser = argparse.ArgumentParser(description="Manage OCD standards hash reference")
    parser.add_argument(
        "--verify", action="store_true", help="Verify hash matches content, warn on mismatch"
    )
    parser.add_argument(
        "--update", action="store_true", help="Recompute and update the hash in frontmatter"
    )
    args = parser.parse_args()

    if args.update:
        new_hash = update_standards_hash()
        if new_hash is None:
            print("Error: standards.md not found", file=sys.stderr)
            sys.exit(1)
        version = get_standards_version()
        print(f"Standards hash updated: ocd-standards:v{version} [{new_hash}]")
        return

    if args.verify:
        result = verify_standards_hash()
        if result.get("error"):
            print(f"Error: {result['error']}", file=sys.stderr)
            sys.exit(1)
        if result["match"]:
            print(f"Hash verified: ocd-standards:v{result['version']} [{result['computed_hash']}]")
        else:
            print(
                f"WARNING: Hash mismatch! "
                f"Stored: {result['stored_hash']}, "
                f"Computed: {result['computed_hash']}",
                file=sys.stderr,
            )
            print("Run 'ocd-standards --update' to fix.", file=sys.stderr)
            sys.exit(1)
        return

    # Default: print reference line
    ref = get_standards_reference()
    if not ref:
        print("Error: standards.md not found", file=sys.stderr)
        sys.exit(1)
    print(ref)


if __name__ == "__main__":
    main()
