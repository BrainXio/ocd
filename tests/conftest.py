"""Shared test fixtures for O.C.D. test suite."""

import json
import os
from pathlib import Path

import pytest

# flush.py sets CLAUDE_INVOKED_BY at import time — clear before importing
# so the recursion guard in main() doesn't skip hook logic during tests.
os.environ.pop("CLAUDE_INVOKED_BY", None)

import ocd.config
import ocd.fix.autofix
import ocd.fix.cycle
import ocd.fix.format
import ocd.gates.check
import ocd.gates.ci_check
import ocd.gates.scan_secrets
import ocd.gates.verify_commit
import ocd.hooks.hookslib
import ocd.hooks.lint_work
import ocd.hooks.pre_compact
import ocd.hooks.session_end
import ocd.hooks.session_start
import ocd.kb.export
import ocd.kb.ingest
import ocd.kb.relevance
import ocd.kb.vec
import ocd.routing.router
import ocd.routing.standards
import ocd.session.app_spec
import ocd.session.flush
import ocd.session.session_card
import ocd.utils
import ocd.worktree

# flush.py sets CLAUDE_INVOKED_BY at import time — clear again so
# tests don't see a stale value.
os.environ.pop("CLAUDE_INVOKED_BY", None)

# ── Path fixtures ──────────────────────────────────────────────────────


@pytest.fixture
def tmp_agent_dir(tmp_path):
    """Create a temporary USER/ directory tree matching production layout."""
    (tmp_path / "state").mkdir()
    (tmp_path / "logs" / "daily").mkdir(parents=True)
    knowledge = tmp_path / "knowledge"
    (knowledge / "concepts").mkdir(parents=True)
    (knowledge / "connections").mkdir(parents=True)
    (knowledge / "resources").mkdir(parents=True)
    (knowledge / "index.md").write_text(
        "# Knowledge Base Index\n\n"
        "| Article | Summary | Compiled From | Updated |\n"
        "|---------|---------|---------------|---------|"
    )
    (knowledge / "log.md").write_text("# Build Log\n")
    (tmp_path / "reports").mkdir()
    (tmp_path / "cache").mkdir()
    (tmp_path / "agents" / "tasks").mkdir(parents=True)
    (tmp_path / "agents" / "runtime").mkdir(parents=True)
    return tmp_path


@pytest.fixture
def state_file(tmp_agent_dir):
    """Path to a temporary state.json with default content."""
    sf = tmp_agent_dir / "state" / "state.json"
    sf.write_text(
        json.dumps({"ingested": {}, "query_count": 0, "last_lint": None, "total_cost": 0.0})
    )
    return sf


@pytest.fixture
def flush_state_file(tmp_agent_dir):
    """Path to a temporary last-flush.json."""
    fsf = tmp_agent_dir / "state" / "last-flush.json"
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
    state_dir = tmp_agent_dir / "state"

    patches = {
        "USER_DIR": tmp_agent_dir,
        "AGENTS_DIR": tmp_agent_dir.parent / ".claude" / "agents",
        "DAILY_DIR": tmp_agent_dir / "logs" / "daily",
        "KNOWLEDGE_DIR": knowledge_dir,
        "CONCEPTS_DIR": knowledge_dir / "concepts",
        "CONNECTIONS_DIR": knowledge_dir / "connections",
        "QA_DIR": knowledge_dir / "qa",
        "RESOURCES_DIR": knowledge_dir / "resources",
        "KNOWLEDGE_DB": tmp_agent_dir / "knowledge.db",
        "REPORTS_DIR": tmp_agent_dir / "reports",
        "STATE_DIR": state_dir,
        "STATE_FILE": state_dir / "state.json",
        "FLUSH_STATE_FILE": state_dir / "last-flush.json",
        "FLUSH_LOG_FILE": state_dir / "flush.log",
        "INDEX_FILE": knowledge_dir / "index.md",
        "VEC_DIMENSIONS": 384,
        "VEC_EMBEDDING_MODEL": "BAAI/bge-small-en-v1.5",
        "VEC_WEIGHT_TFIDF": 0.4,
        "VEC_WEIGHT_VECTOR": 0.4,
        "VEC_WEIGHT_QUALITY": 0.2,
        "KB_INDEX_JSON": state_dir / "kb-index.json",
        "MANIFEST_FILE": state_dir / "manifest.json",
        "SKILLS_DIR": tmp_agent_dir.parent / ".claude" / "skills" / "ocd",
        "STANDARDS_FILE": tmp_agent_dir.parent / ".claude" / "skills" / "ocd" / "standards.md",
        "SESSION_CARD_FILE": state_dir / "session-card.md",
        "WORKTREES_DIR": tmp_agent_dir.parent / ".claude" / "worktrees",
        "AUTOFIX_LOG": state_dir / "autofix-loop.jsonl",
        "APP_SPEC_FILE": tmp_agent_dir.parent / "app_spec.txt",
        "MAX_APP_SPEC_CHARS": 4000,
        "COMMIT_KNOWLEDGE_DIR": tmp_agent_dir.parent / "docs" / "knowledge",
    }

    # Patch the canonical source
    for name, value in patches.items():
        monkeypatch.setattr(ocd.config, name, value)

    # Patch modules that imported these names directly
    for module in (
        ocd.fix.autofix,
        ocd.fix.cycle,
        ocd.fix.format,
        ocd.gates.check,
        ocd.gates.ci_check,
        ocd.gates.scan_secrets,
        ocd.gates.verify_commit,
        ocd.hooks.hookslib,
        ocd.session.flush,
        ocd.hooks.session_start,
        ocd.hooks.session_end,
        ocd.hooks.pre_compact,
        ocd.hooks.lint_work,
        ocd.kb.export,
        ocd.kb.ingest,
        ocd.kb.relevance,
        ocd.kb.vec,
        ocd.session.session_card,
        ocd.routing.standards,
        ocd.session.app_spec,
        ocd.utils,
        ocd.worktree,
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
def tmp_raw_kb(tmp_agent_dir, mock_config_paths):
    """Factory fixture that creates sample wiki articles in knowledge/ subdirs."""

    def _create(subdir: str, name: str, content: str) -> Path:
        path = tmp_agent_dir / "knowledge" / subdir / f"{name}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    return _create


@pytest.fixture
def daily_log(tmp_agent_dir, mock_config_paths):
    """Factory fixture that creates a daily log file on disk."""

    def _create(date_str: str, content: str) -> Path:
        path = tmp_agent_dir / "logs" / "daily" / f"{date_str}.md"
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


# ── Git repo fixture ───────────────────────────────────────────────────────


@pytest.fixture
def tmp_git_repo(tmp_path):
    """Create a minimal git repo with one commit, for worktree tests."""
    import subprocess

    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=str(repo), check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=str(repo),
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=str(repo),
        check=True,
        capture_output=True,
    )
    (repo / "README.md").write_text("# test\n")
    subprocess.run(["git", "add", "README.md"], cwd=str(repo), check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "initial"],
        cwd=str(repo),
        check=True,
        capture_output=True,
    )
    return repo


# ── Recursion guard ─────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def clear_recursion_guard(monkeypatch):
    """Ensure CLAUDE_INVOKED_BY is not set during tests.

    Hooks check this env var in main() and return early if set.
    """
    monkeypatch.delenv("CLAUDE_INVOKED_BY", raising=False)
