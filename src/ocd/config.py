"""Path constants and configuration.

Single source of truth for all directory layout.  Changing a top-level
name here propagates everywhere.
"""

from __future__ import annotations

import os
import sys
from datetime import UTC, datetime
from pathlib import Path

# ── Top-level directory names (change ONE place only) ─────────────────────
_RUNTIME_DIR_NAME: str = "USER"
_CLAUDE_DIR_NAME: str = ".claude"


def _find_project_root() -> Path:
    """Find project root by walking up from package location or CWD.

    Strategy order (works for both dev and installed-package use cases):
    1. OCD_PROJECT_ROOT env var (highest priority, set in devcontainer or by host project)
    2. Walk up from __file__ looking for .git/ (works in dev or editable install)
    3. Walk up from CWD looking for .git/ (works when running inside a host project)
    4. Fallback to CWD
    """
    env_root = os.environ.get("OCD_PROJECT_ROOT")
    if env_root:
        return Path(env_root).resolve()
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".git").is_dir():
            return parent
    current = Path.cwd()
    for parent in [current, *current.parents]:
        if (parent / ".git").is_dir():
            return parent
    return current


PROJECT_ROOT: Path = _find_project_root()

# ── Core paths (built from the single source above) ───────────────────────
USER_DIR: Path = PROJECT_ROOT / _RUNTIME_DIR_NAME
AGENTS_DIR: Path = PROJECT_ROOT / _CLAUDE_DIR_NAME / "agents"
VENV_BIN: Path = Path(sys.executable).parent

DAILY_DIR: Path = USER_DIR / "logs" / "daily"
KNOWLEDGE_DIR: Path = USER_DIR / "knowledge"
CONCEPTS_DIR: Path = KNOWLEDGE_DIR / "concepts"
CONNECTIONS_DIR: Path = KNOWLEDGE_DIR / "connections"
QA_DIR: Path = KNOWLEDGE_DIR / "qa"
REPORTS_DIR: Path = USER_DIR / "reports"

STATE_DIR: Path = USER_DIR / "state"
STATE_FILE: Path = STATE_DIR / "state.json"
FLUSH_STATE_FILE: Path = STATE_DIR / "last-flush.json"
FLUSH_LOG_FILE: Path = STATE_DIR / "flush.log"

INDEX_FILE: Path = KNOWLEDGE_DIR / "index.md"

DEFAULT_INDEX_CONTENT: str = (
    "# Knowledge Base Index\n\n"
    "| Article | Summary | Compiled From | Updated |\n"
    "|---------|---------|---------------|---------|"
)

# Flush thresholds
MIN_TURNS_SESSION_END = 1
MIN_TURNS_PRE_COMPACT = 5
MAX_FLUSH_CONTEXT_CHARS = 15_000
MAX_FLUSH_TURNS = 30

# Session start thresholds
MAX_CONTEXT_CHARS = 20_000
MAX_LOG_LINES = 30

# Compilation trigger
COMPILE_AFTER_HOUR = 18

# Relevance-based KB injection
KB_INDEX_JSON: Path = STATE_DIR / "kb-index.json"
KB_INJECTION_COUNT = 3
MAX_RELEVANT_CONTEXT_CHARS = 8000

# Agent routing
MANIFEST_FILE: Path = STATE_DIR / "manifest.json"

# Standards-as-reference
SKILLS_DIR: Path = PROJECT_ROOT / _CLAUDE_DIR_NAME / "skills" / "ocd"
STANDARDS_FILE: Path = SKILLS_DIR / "standards.md"

# Bundled content database (for release packaging)
BUNDLED_DB_PATH: Path = Path(__file__).parent / "data" / "content.db"

# Session state card
SESSION_CARD_FILE: Path = STATE_DIR / "session-card.md"
MAX_SESSION_CARD_CHARS = 1200

# Keep AGENT_DIR as an alias for USER_DIR for backward compatibility
# during migration (will be removed in a future release)
AGENT_DIR: Path = USER_DIR


def now_iso() -> str:
    """Current time in ISO 8601 format."""
    return datetime.now(UTC).astimezone().isoformat(timespec="seconds")


def today_iso() -> str:
    """Current date in ISO 8601 format."""
    return datetime.now(UTC).astimezone().strftime("%Y-%m-%d")

