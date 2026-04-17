"""Path constants and configuration for the personal knowledge base."""

import os
import sys
from datetime import UTC, datetime
from pathlib import Path


def _find_project_root() -> Path:
    """Find project root by walking up from package location or CWD."""
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
CLAUDE_DIR = PROJECT_ROOT / ".claude"
AGENT_DIR = PROJECT_ROOT / ".agent"
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
LOG_FILE = KNOWLEDGE_DIR / "log.md"

# Flush thresholds
MIN_TURNS_SESSION_END = 1
MIN_TURNS_PRE_COMPACT = 5
MAX_FLUSH_CONTEXT_CHARS = 15_000
MAX_FLUSH_TURNS = 30

TIMEZONE = "UTC"


def now_iso() -> str:
    """Current time in ISO 8601 format."""
    return datetime.now(UTC).astimezone().isoformat(timespec="seconds")


def today_iso() -> str:
    """Current date in ISO 8601 format."""
    return datetime.now(UTC).astimezone().strftime("%Y-%m-%d")
