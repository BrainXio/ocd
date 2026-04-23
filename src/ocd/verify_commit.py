"""Verify commit messages for AI attribution patterns.

Single source of truth for AI pattern checks, used by both
the commit-msg hook and CI check-commit-messages job.

Invoked via `ocd hook verify-commit`.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from ocd.config import PROJECT_ROOT

_PATTERNS_FILE = PROJECT_ROOT / "git_hooks" / "ai-patterns.txt"


def load_patterns(patterns_file: Path | None = None) -> list[str]:
    """Load AI attribution patterns from the patterns file.

    Blank lines and lines starting with ``#`` are skipped.
    Returns an empty list if the file does not exist.
    """
    pfile = patterns_file or _PATTERNS_FILE
    if not pfile.exists():
        return []
    return [
        line.strip()
        for line in pfile.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]


def check_message(message: str, patterns: list[str] | None = None) -> list[tuple[str, str]]:
    """Check a commit message for AI attribution patterns.

    Returns a list of ``(pattern, matching_line)`` tuples for violations.
    An empty list means the message is clean.
    """
    if patterns is None:
        patterns = load_patterns()
    violations: list[tuple[str, str]] = []
    for line in message.splitlines():
        for pattern in patterns:
            if re.search(pattern, line, re.IGNORECASE):
                violations.append((pattern, line))
    return violations


def check_commit_range(range_spec: str) -> list[tuple[str, str, str]]:
    """Check all commits in a git range for AI attribution.

    Returns a list of ``(commit_hash, pattern, matching_line)`` tuples.
    Requires git to be available.
    """
    rev_result = subprocess.run(
        ["git", "rev-list", range_spec],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
    )
    if rev_result.returncode != 0:
        return []

    patterns = load_patterns()
    violations: list[tuple[str, str, str]] = []
    for commit_hash in rev_result.stdout.strip().splitlines():
        msg_result = subprocess.run(
            ["git", "log", "-1", "--format=%B", commit_hash],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
        )
        for pattern, line in check_message(msg_result.stdout, patterns):
            violations.append((commit_hash, pattern, line))
    return violations


def main() -> None:
    """Entry point for ocd verify-commit.

    Usage:
        ocd verify-commit <msg_file>          Check a commit message file (hook mode)
        ocd verify-commit --range <range>     Check a commit range (CI mode)
        ocd verify-commit --message <text>     Check a single message
    """
    import argparse

    parser = argparse.ArgumentParser(description="Verify commit messages for AI attribution")
    parser.add_argument("msg_file", nargs="?", help="Path to commit message file")
    parser.add_argument(
        "--range",
        dest="range_spec",
        help="Git commit range to check (e.g. origin/main..HEAD)",
    )
    parser.add_argument("--message", help="Direct commit message text to check")
    args = parser.parse_args()

    if args.range_spec:
        violations = check_commit_range(args.range_spec)
        if violations:
            for commit_hash, _pattern, line in violations:
                print(
                    f"error: commit {commit_hash[:8]} contains prohibited AI attribution: {line}",
                    file=sys.stderr,
                )
            print("", file=sys.stderr)
            print("Rejecting: commit messages contain AI attribution.", file=sys.stderr)
            print(
                "Remove Co-Authored-By lines, 'Generated with/by/using' lines,",
                file=sys.stderr,
            )
            print("or [AI] tags. Patterns: git_hooks/ai-patterns.txt", file=sys.stderr)
            sys.exit(1)
        else:
            print("ok: no AI attribution patterns found in commit range")

    elif args.message:
        msg_violations = check_message(args.message)
        if msg_violations:
            for pattern, line in msg_violations:
                print(
                    f"error: AI attribution pattern '{pattern}' found: {line}",
                    file=sys.stderr,
                )
            sys.exit(1)
        else:
            print("ok: commit message is clean")

    elif args.msg_file:
        msg = Path(args.msg_file).read_text(encoding="utf-8")
        msg_violations = check_message(msg)
        if msg_violations:
            for _pattern, line in msg_violations:
                print(
                    f"error: commit message contains AI attribution: {line}",
                    file=sys.stderr,
                )
            print("", file=sys.stderr)
            print("Remove the attribution line and retry. Policy prohibits:", file=sys.stderr)
            print("  - Co-Authored-By lines", file=sys.stderr)
            print("  - 'Generated with/by/using' attribution", file=sys.stderr)
            print("  - [AI] or [AI-generated] tags", file=sys.stderr)
            sys.exit(1)

    else:
        parser.print_help(sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
