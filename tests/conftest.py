"""Shared test fixtures for O.C.D. test suite."""

import json
import os
from pathlib import Path

import pytest

# flush.py sets CLAUDE_INVOKED_BY at import time — clear before importing
# so the recursion guard in main() doesn't skip hook logic during tests.
os.environ.pop("CLAUDE_INVOKED_BY", None)

import ocd.config
import ocd.flush
import ocd.hooks.hookslib
import ocd.hooks.lint_work
import ocd.hooks.pre_compact
import ocd.hooks.session_end
import ocd.hooks.session_start
import ocd.relevance
import ocd.utils

# flush.py sets CLAUDE_INVOKED_BY at import time — clear again so
# tests don't see a stale value.
os.environ.pop("CLAUDE_INVOKED_BY", None)

# ── Path fixtures ──────────────────────────────────────────────────────


@pytest.fixture
def tmp_agent_dir(tmp_path):
    """Create a temporary .agent/ directory tree matching production layout."""
    (tmp_path / ".state").mkdir()
    (tmp_path / "daily").mkdir()
    knowledge = tmp_path / "knowledge"
    (knowledge / "concepts").mkdir(parents=True)
    (knowledge / "connections").mkdir(parents=True)
    (knowledge / "qa").mkdir(parents=True)
    (knowledge / "index.md").write_text(
        "# Knowledge Base Index\n\n"
        "| Article | Summary | Compiled From | Updated |\n"
        "|---------|---------|---------------|---------|"
    )
    (knowledge / "log.md").write_text("# Build Log\n")
    (tmp_path / "reports").mkdir()
    return tmp_path


@pytest.fixture
def state_file(tmp_agent_dir):
    """Path to a temporary state.json with default content."""
    sf = tmp_agent_dir / ".state" / "state.json"
    sf.write_text(
        json.dumps({"ingested": {}, "query_count": 0, "last_lint": None, "total_cost": 0.0})
    )
    return sf


@pytest.fixture
def flush_state_file(tmp_agent_dir):
    """Path to a temporary last-flush.json."""
    fsf = tmp_agent_dir / ".state" / "last-flush.json"
    fsf.write_text("{}")
    return fsf


# ── Config mocking ─────────────────────────────────────────────────────


@pytest.fixture
def mock_config_paths(tmp_agent_dir, monkeypatch):
    """Patch ocd.config path constants to point at tmp_agent_dir.

    Also patches the same names in modules that imported them directly
    so that monkeypatch actually affects the code under test.
    """
    knowledge_dir = tmp_agent_dir / "knowledge"
    state_dir = tmp_agent_dir / ".state"

    patches = {
        "AGENT_DIR": tmp_agent_dir,
        "DAILY_DIR": tmp_agent_dir / "daily",
        "KNOWLEDGE_DIR": knowledge_dir,
        "CONCEPTS_DIR": knowledge_dir / "concepts",
        "CONNECTIONS_DIR": knowledge_dir / "connections",
        "QA_DIR": knowledge_dir / "qa",
        "REPORTS_DIR": tmp_agent_dir / "reports",
        "STATE_DIR": state_dir,
        "STATE_FILE": state_dir / "state.json",
        "FLUSH_STATE_FILE": state_dir / "last-flush.json",
        "FLUSH_LOG_FILE": state_dir / "flush.log",
        "INDEX_FILE": knowledge_dir / "index.md",
        "KB_INDEX_JSON": state_dir / "kb-index.json",
    }

    # Patch the canonical source
    for name, value in patches.items():
        monkeypatch.setattr(ocd.config, name, value)

    # Patch modules that imported these names directly
    for module in (
        ocd.utils,
        ocd.hooks.hookslib,
        ocd.flush,
        ocd.hooks.session_start,
        ocd.hooks.session_end,
        ocd.hooks.pre_compact,
        ocd.hooks.lint_work,
        ocd.relevance,
    ):
        for name, value in patches.items():
            if hasattr(module, name):
                monkeypatch.setattr(module, name, value)

    return tmp_agent_dir


# ── Knowledge base fixtures ────────────────────────────────────────────


@pytest.fixture
def wiki_article(tmp_agent_dir, mock_config_paths):
    """Factory fixture that creates a wiki article on disk."""

    def _create(rel_path: str, content: str, frontmatter: bool = True) -> Path:
        full = f"---\ntitle: {rel_path.split('/')[-1]}\n---\n\n{content}"
        if not frontmatter:
            full = content
        path = tmp_agent_dir / "knowledge" / f"{rel_path}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(full)
        return path

    return _create


@pytest.fixture
def daily_log(tmp_agent_dir, mock_config_paths):
    """Factory fixture that creates a daily log file on disk."""

    def _create(date_str: str, content: str) -> Path:
        path = tmp_agent_dir / "daily" / f"{date_str}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    return _create


# ── Transcript fixtures ────────────────────────────────────────────────


@pytest.fixture
def sample_transcript(tmp_path):
    """Create a sample JSONL transcript file for hookslib testing."""
    lines = [
        json.dumps({"message": {"role": "user", "content": "Hello"}}),
        json.dumps({"message": {"role": "assistant", "content": "Hi there!"}}),
        json.dumps({"message": {"role": "user", "content": "How are you?"}}),
        json.dumps(
            {
                "message": {
                    "role": "assistant",
                    "content": [{"type": "text", "text": "I'm fine!"}],
                }
            }
        ),
    ]
    path = tmp_path / "transcript.jsonl"
    path.write_text("\n".join(lines))
    return path


# ── Recursion guard ─────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def clear_recursion_guard(monkeypatch):
    """Ensure CLAUDE_INVOKED_BY is not set during tests.

    Hooks check this env var in main() and return early if set.
    """
    monkeypatch.delenv("CLAUDE_INVOKED_BY", raising=False)
