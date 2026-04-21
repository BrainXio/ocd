"""Path constants and configuration for the personal knowledge base."""

from __future__ import annotations

import os
import sys
from datetime import UTC, datetime
from pathlib import Path


def _find_project_root() -> Path:
    """Find project root by walking up from package location or CWD.

    Strategy order:
    1. OCD_PROJECT_ROOT env var (set in devcontainer)
    2. Walk up from __file__ looking for .git/ (works in dev; fails silently
       when package is installed in /opt/ocd/venv/ since no .git/ above site-packages)
    3. Walk up from CWD looking for .git/ (works when CWD is inside the project)
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
    return Path.cwd()


PROJECT_ROOT = _find_project_root()
AGENT_DIR = PROJECT_ROOT / ".agent"
AGENTS_DIR = PROJECT_ROOT / ".claude" / "agents"
VENV_BIN = Path(sys.executable).parent

DAILY_DIR = AGENT_DIR / "daily"
KNOWLEDGE_DIR = AGENT_DIR / "knowledge"
CONCEPTS_DIR = KNOWLEDGE_DIR / "concepts"
CONNECTIONS_DIR = KNOWLEDGE_DIR / "connections"
QA_DIR = KNOWLEDGE_DIR / "qa"
REPORTS_DIR = AGENT_DIR / "reports"

STATE_DIR = AGENT_DIR / ".state"
STATE_FILE = STATE_DIR / "state.json"
FLUSH_STATE_FILE = STATE_DIR / "last-flush.json"
FLUSH_LOG_FILE = STATE_DIR / "flush.log"

INDEX_FILE = KNOWLEDGE_DIR / "index.md"

DEFAULT_INDEX_CONTENT = (
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
KB_INDEX_JSON = STATE_DIR / "kb-index.json"
KB_INJECTION_COUNT = 3
MAX_RELEVANT_CONTEXT_CHARS = 8000

# Agent routing
MANIFEST_FILE = STATE_DIR / "manifest.json"

# Standards-as-reference
SKILLS_DIR = PROJECT_ROOT / ".claude" / "skills" / "ocd"
STANDARDS_FILE = SKILLS_DIR / "standards.md"

# Session state card
SESSION_CARD_FILE = STATE_DIR / "session-card.md"
MAX_SESSION_CARD_CHARS = 1200


def now_iso() -> str:
    """Current time in ISO 8601 format."""
    return datetime.now(UTC).astimezone().isoformat(timespec="seconds")


def today_iso() -> str:
    """Current date in ISO 8601 format."""
    return datetime.now(UTC).astimezone().strftime("%Y-%m-%d")
