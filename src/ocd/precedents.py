"""Precedent system — learn from past failures, prevent repetitions.

Stores recorded issue patterns in a repo-local `.ocd-precedents.json`.
Each precedent has a shell check command that returns 0 if the issue is
present (meaning it would fail in CI) and non-zero if absent.

Escalation: after a precedent hits 2 times, its effective severity
bumps by one level (warning -> error, error -> fatal). This prevents
agents from repeatedly pushing the same broken pattern.
"""

from __future__ import annotations

import json
import secrets
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PRECEDENTS_FILENAME = ".brainxio/ocd/precedents.json"

# Severity ordering for escalation
_SEVERITY_ORDER = ["info", "warning", "error", "fatal"]


def _find_precedents_file(root: Path | None = None) -> Path | None:
    """Locate `.ocd-precedents.json` in project root or ancestors."""
    cwd = root or Path.cwd()
    for parent in [cwd, *cwd.parents]:
        candidate = parent / PRECEDENTS_FILENAME
        if candidate.exists():
            return candidate
        if (parent / ".git").exists():
            # Stop at repo boundary
            candidate = parent / PRECEDENTS_FILENAME
            if candidate.exists():
                return candidate
            break
    return None


def _load_precedents(path: Path) -> dict[str, Any]:
    """Load and validate precedents JSON."""
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {"version": 1, "precedents": []}

    if not isinstance(data, dict):
        return {"version": 1, "precedents": []}

    precedents = data.get("precedents", [])
    if not isinstance(precedents, list):
        precedents = []

    # Normalize each entry
    normalized: list[dict[str, Any]] = []
    for p in precedents:
        if not isinstance(p, dict):
            continue
        np = {
            "id": p.get("id") or secrets.token_hex(4),
            "description": p.get("description", ""),
            "check": p.get("check", ""),
            "fix": p.get("fix", ""),
            "scope": p.get("scope", "both"),
            "severity": p.get("severity", "warning"),
            "discovered": p.get("discovered", datetime.now(timezone.utc).isoformat()),
            "hits": int(p.get("hits", 0)),
            "last_hit": p.get("last_hit"),
        }
        normalized.append(np)

    return {"version": data.get("version", 1), "precedents": normalized}


def _effective_severity(prec: dict[str, Any]) -> str:
    """Return severity with escalation applied."""
    base = prec.get("severity", "warning")
    hits = prec.get("hits", 0)
    if hits < 2:
        return base
    try:
        idx = _SEVERITY_ORDER.index(base)
    except ValueError:
        idx = 0
    return _SEVERITY_ORDER[min(idx + 1, len(_SEVERITY_ORDER) - 1)]


def _run_check(cmd: str, cwd: Path, timeout: int = 30) -> tuple[bool, str]:
    """Run a shell check command. Returns (hit_present, output)."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(cwd),
        )
    except subprocess.TimeoutExpired:
        return False, f"timed out after {timeout}s"
    except Exception as e:
        return False, f"exception: {e}"

    # Return code 0 means the issue IS present (check matched)
    hit = result.returncode == 0
    output = (result.stdout + result.stderr).strip()
    return hit, output


def check_precedents(
    scope: str = "both", root: Path | None = None
) -> dict[str, Any]:
    """Run all precedent checks for the given scope.

    Returns a dict with overall status and per-precedent results.
    """
    prec_file = _find_precedents_file(root)
    if prec_file is None:
        return {"status": "pass", "detail": "no precedents file", "hits": []}

    data = _load_precedents(prec_file)
    cwd = prec_file.parent

    results: list[dict[str, Any]] = []
    hit_count = 0
    error_count = 0

    for prec in data["precedents"]:
        p_scope = prec.get("scope", "both")
        if p_scope != "both" and p_scope != scope:
            continue

        check_cmd = prec.get("check", "")
        if not check_cmd:
            continue

        hit, output = _run_check(check_cmd, cwd)
        eff_sev = _effective_severity(prec)

        if hit:
            hit_count += 1
            if eff_sev in ("error", "fatal"):
                error_count += 1
            # Update hit counters
            prec["hits"] = prec.get("hits", 0) + 1
            prec["last_hit"] = datetime.now(timezone.utc).isoformat()

        results.append(
            {
                "id": prec["id"],
                "description": prec["description"],
                "severity": eff_sev,
                "hit": hit,
                "output": output[:500] if output else "",
                "fix": prec.get("fix", ""),
            }
        )

    # Write back updated hit counts
    if hit_count > 0:
        try:
            with prec_file.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
                f.write("\n")
        except OSError:
            pass

    status = "fail" if error_count > 0 else ("warn" if hit_count > 0 else "pass")
    return {
        "status": status,
        "summary": f"{hit_count} hit(s), {error_count} error-level",
        "hits": results,
        "file": str(prec_file),
    }


def remember_issue(
    description: str,
    check: str,
    fix: str,
    scope: str = "both",
    severity: str = "warning",
    root: Path | None = None,
) -> dict[str, Any]:
    """Record a new precedent. Returns the recorded entry."""
    cwd = root or _find_precedents_file(root)
    if cwd is None:
        cwd = Path.cwd()
        # Try to find repo root
        for parent in [cwd, *cwd.parents]:
            if (parent / ".git").exists():
                cwd = parent
                break

    prec_file = cwd / PRECEDENTS_FILENAME
    data = _load_precedents(prec_file) if prec_file.exists() else {"version": 1, "precedents": []}

    new_prec = {
        "id": secrets.token_hex(4),
        "description": description,
        "check": check,
        "fix": fix,
        "scope": scope,
        "severity": severity,
        "discovered": datetime.now(timezone.utc).isoformat(),
        "hits": 0,
        "last_hit": None,
    }

    # Prevent exact duplicates by check command
    existing_checks = {p.get("check", "") for p in data["precedents"]}
    if check in existing_checks:
        return {"ok": False, "error": "precedent with identical check already exists", "id": None}

    data["precedents"].append(new_prec)

    try:
        with prec_file.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
    except OSError as e:
        return {"ok": False, "error": f"failed to write {prec_file}: {e}", "id": None}

    return {"ok": True, "id": new_prec["id"], "file": str(prec_file)}


def list_precedents(
    scope: str | None = None, min_hits: int = 0, root: Path | None = None
) -> dict[str, Any]:
    """List recorded precedents with optional filters."""
    prec_file = _find_precedents_file(root)
    if prec_file is None:
        return {"precedents": [], "count": 0}

    data = _load_precedents(prec_file)
    filtered: list[dict[str, Any]] = []

    for prec in data["precedents"]:
        if scope and prec.get("scope", "both") != scope and prec.get("scope", "both") != "both":
            continue
        if prec.get("hits", 0) < min_hits:
            continue
        filtered.append(
            {
                "id": prec["id"],
                "description": prec["description"],
                "scope": prec.get("scope", "both"),
                "severity": prec.get("severity", "warning"),
                "effective_severity": _effective_severity(prec),
                "hits": prec.get("hits", 0),
                "discovered": prec.get("discovered", ""),
                "last_hit": prec.get("last_hit"),
            }
        )

    # Sort by hits desc, then by description
    filtered.sort(key=lambda p: (-p["hits"], p["description"]))

    return {
        "precedents": filtered,
        "count": len(filtered),
        "file": str(prec_file),
    }
