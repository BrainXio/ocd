"""Secret scanning via gitleaks.

Single source of truth for secret scanning, used by both
the pre-commit hook and CI secret-scan job.
"""

from __future__ import annotations

import shutil
import subprocess
import sys

from ocd.config import PROJECT_ROOT

_GITLEAKS_CONFIG = PROJECT_ROOT / ".gitleaks.toml"


def scan_secrets(staged: bool = False, source: str = ".") -> int:
    """Run gitleaks scan.

    Args:
        staged: If True, use ``protect --staged`` (pre-commit mode).
                If False, use ``detect --source`` (CI mode).
        source: Path to scan (for detect mode). Defaults to ``"."``.

    Returns:
        0 if clean, 1 if secrets detected, 2 if gitleaks not installed.
    """
    if not shutil.which("gitleaks"):
        print("warning: gitleaks not installed, skipping secret scanning", file=sys.stderr)
        print("  Install: https://github.com/gitleaks/gitleaks#installing", file=sys.stderr)
        return 2

    config_args = ["-c", str(_GITLEAKS_CONFIG)] if _GITLEAKS_CONFIG.exists() else []

    if staged:
        cmd = ["gitleaks", "protect", "--staged", *config_args]
    else:
        cmd = ["gitleaks", "detect", "--source", source, *config_args]

    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT))

    if result.returncode != 0:
        if staged:
            print(
                "error: gitleaks detected potential secrets in staged changes",
                file=sys.stderr,
            )
            print(
                "  If this is a false positive, add an allowlist entry to .gitleaks.toml",
                file=sys.stderr,
            )
        else:
            print("error: gitleaks detected potential secrets", file=sys.stderr)
        return 1

    return 0


def main() -> None:
    """Entry point for ocd scan-secrets."""
    import argparse

    parser = argparse.ArgumentParser(description="Scan for secrets using gitleaks")
    parser.add_argument(
        "--staged",
        action="store_true",
        help="Scan staged changes only (pre-commit mode)",
    )
    parser.add_argument(
        "--source",
        default=".",
        help="Path to scan (default: current directory)",
    )
    args = parser.parse_args()

    rc = scan_secrets(staged=args.staged, source=args.source)
    sys.exit(rc)

