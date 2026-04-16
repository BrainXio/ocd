"""Path constants and configuration for the personal knowledge base."""

from datetime import datetime, timezone
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────
# .claude/scripts/config.py
#   parent = scripts/, parent.parent = .claude/
#   parent.parent.parent = project root
CLAUDE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = CLAUDE_DIR.parent
AGENT_DIR = PROJECT_ROOT / ".agent"

DAILY_DIR = AGENT_DIR / "daily"
KNOWLEDGE_DIR = AGENT_DIR / "knowledge"
CONCEPTS_DIR = KNOWLEDGE_DIR / "concepts"
CONNECTIONS_DIR = KNOWLEDGE_DIR / "connections"
QA_DIR = KNOWLEDGE_DIR / "qa"
REPORTS_DIR = AGENT_DIR / "reports"
SCRIPTS_DIR = CLAUDE_DIR / "scripts"
HOOKS_DIR = CLAUDE_DIR / "hooks"
VENV_PYTHON = CLAUDE_DIR / ".venv" / "bin" / "python"

STATE_DIR = AGENT_DIR / ".state"
STATE_FILE = STATE_DIR / "state.json"
FLUSH_STATE_FILE = STATE_DIR / "last-flush.json"
FLUSH_LOG_FILE = STATE_DIR / "flush.log"

INDEX_FILE = KNOWLEDGE_DIR / "index.md"
LOG_FILE = KNOWLEDGE_DIR / "log.md"

# ── Flush thresholds ──────────────────────────────────────────────────
# Minimum conversation turns to trigger a memory flush.
# Lower for session-end (capture everything), higher for pre-compact
# (only flush if there's enough context to be worth saving).
MIN_TURNS_SESSION_END = 1
MIN_TURNS_PRE_COMPACT = 5

MAX_FLUSH_CONTEXT_CHARS = 15_000
MAX_FLUSH_TURNS = 30

# ── Timezone ───────────────────────────────────────────────────────────
TIMEZONE = "UTC"


def now_iso() -> str:
    """Current time in ISO 8601 format."""
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def today_iso() -> str:
    """Current date in ISO 8601 format."""
    return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")
