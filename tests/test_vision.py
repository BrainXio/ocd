"""Tests for vision — VISION.md parsing and context injection."""

from pathlib import Path

import pytest

from ocd.vision import (
    Story,
    _extract_referenced_files,
    _load_referenced_file,
    _truncate_with_marker,
    build_vision_context,
    parse_vision,
    select_next_story,
)

# ── Sample content ──────────────────────────────────────────────────────

_TWO_STORIES = """\
# O.C.D. Product Vision & Roadmap

Some intro text.

### 1. First Story ✅ DONE

First story content.

### 2. Second Story

Second story content.
"""

_ALL_DONE = """\
### 1. Done Story ✅ DONE

Content 1.

### 2. Also Done ✅ DONE

Content 2.
"""

_REFS_STORY = """\
### 3. Story With References

Check `agent-sdk.md` and `path/to/config.yaml` for details.
Also see `not a file` and `some word`.
"""

_SEPARATOR_STORY = """\
### 4. Story With Separator

Content before separator.

________________________________________________________________________

### 5. After Separator

Content after separator.
"""


# ── Fixtures ────────────────────────────────────────────────────────────


@pytest.fixture
def vision_file(mock_config_paths):
    """Factory fixture that creates a VISION.md file."""

    def _create(content: str) -> Path:
        path = mock_config_paths / "VISION.md"
        path.write_text(content, encoding="utf-8")
        return path

    return _create


# ── TestParseVision ─────────────────────────────────────────────────────


class TestParseVision:
    def test_parses_done_story(self):
        result = parse_vision(_TWO_STORIES)
        assert len(result.stories) == 2
        assert result.stories[0].done is True
        assert result.stories[0].number == 1
        assert result.stories[0].title == "First Story"

    def test_parses_undone_story(self):
        result = parse_vision(_TWO_STORIES)
        assert result.stories[1].done is False
        assert result.stories[1].number == 2
        assert result.stories[1].title == "Second Story"

    def test_extracts_story_text(self):
        result = parse_vision(_TWO_STORIES)
        assert "First story content" in result.stories[0].text
        assert "Second story content" in result.stories[1].text

    def test_extracts_header(self):
        result = parse_vision(_TWO_STORIES)
        assert "O.C.D. Product Vision" in result.header
        assert "Some intro text" in result.header

    def test_empty_content(self):
        result = parse_vision("")
        assert result.stories == ()
        assert result.header == ""

    def test_whitespace_only(self):
        result = parse_vision("   \n  \n")
        assert result.stories == ()

    def test_no_story_headings(self):
        result = parse_vision("Just some text without headings.")
        assert result.stories == ()
        assert "Just some text" in result.header

    def test_separator_stops_story(self):
        result = parse_vision(_SEPARATOR_STORY)
        assert len(result.stories) == 2
        assert "Content before separator" in result.stories[0].text
        assert "Content after separator" in result.stories[1].text
        assert "___" not in result.stories[0].text

    def test_multiple_stories(self):
        result = parse_vision(_TWO_STORIES + _ALL_DONE)
        # _TWO_STORIES has stories 1-2, _ALL_DONE reuses 1-2
        # But since they're concatenated, we get 4 stories
        assert len(result.stories) == 4


# ── TestSelectNextStory ────────────────────────────────────────────────


class TestSelectNextStory:
    def test_returns_first_undone(self):
        stories = (
            Story(number=1, title="Done", done=True, text=""),
            Story(number=2, title="Next", done=False, text="content"),
            Story(number=3, title="Later", done=False, text=""),
        )
        result = select_next_story(stories)
        assert result is not None
        assert result.number == 2
        assert result.title == "Next"

    def test_returns_none_if_all_done(self):
        stories = (
            Story(number=1, title="A", done=True, text=""),
            Story(number=2, title="B", done=True, text=""),
        )
        assert select_next_story(stories) is None

    def test_returns_none_if_empty(self):
        assert select_next_story(()) is None

    def test_first_story_is_undone(self):
        stories = (Story(number=1, title="First", done=False, text="x"),)
        result = select_next_story(stories)
        assert result is not None
        assert result.number == 1


# ── TestExtractReferencedFiles ─────────────────────────────────────────


class TestExtractReferencedFiles:
    def test_extracts_backtick_file_paths(self):
        text = "Check `agent-sdk.md` and `config.yaml` for details."
        result = _extract_referenced_files(text)
        assert "agent-sdk.md" in result
        assert "config.yaml" in result

    def test_extracts_paths_with_slashes(self):
        text = "See `.claude/hooks/session-start.md` for config."
        result = _extract_referenced_files(text)
        assert ".claude/hooks/session-start.md" in result

    def test_ignores_non_file_backticks(self):
        text = "Use `some word` and `another thing` here."
        result = _extract_referenced_files(text)
        assert result == []

    def test_ignores_empty_backticks(self):
        assert _extract_referenced_files("``") == []

    def test_mixed_references(self):
        text = "Read `README.md`, follow `path/to/guide.md`, skip `not a file`."
        result = _extract_referenced_files(text)
        assert "README.md" in result
        assert "path/to/guide.md" in result


# ── TestLoadReferencedFile ─────────────────────────────────────────────


class TestLoadReferencedFile:
    def test_loads_existing_file_under_user(self, mock_config_paths):
        (mock_config_paths / "agent-sdk.md").write_text("SDK content", encoding="utf-8")
        result = _load_referenced_file("agent-sdk.md", user_dir=mock_config_paths)
        assert result == "SDK content"

    def test_returns_none_for_path_traversal(self, mock_config_paths):
        result = _load_referenced_file("../../etc/passwd", user_dir=mock_config_paths)
        assert result is None

    def test_returns_none_for_nonexistent_file(self, mock_config_paths):
        result = _load_referenced_file("nonexistent.md", user_dir=mock_config_paths)
        assert result is None

    def test_returns_none_for_absolute_path_outside_user(self, mock_config_paths):
        result = _load_referenced_file("/etc/passwd", user_dir=mock_config_paths)
        assert result is None


# ── TestTruncateWithMarker ─────────────────────────────────────────────


class TestTruncateWithMarker:
    def test_no_truncation_when_fits(self):
        result = _truncate_with_marker("hello", 100)
        assert result == "hello"

    def test_truncation_adds_marker(self):
        long_text = "x" * 200
        result = _truncate_with_marker(long_text, 100)
        assert len(result) == 100
        assert result.endswith("...(truncated)")

    def test_exact_fit(self):
        text = "hello"
        result = _truncate_with_marker(text, 5)
        assert result == "hello"


# ── TestBuildVisionContext ──────────────────────────────────────────────


class TestBuildVisionContext:
    def test_returns_none_when_no_vision_file(self, mock_config_paths):
        result = build_vision_context()
        assert result is None

    def test_returns_none_when_all_done(self, mock_config_paths, vision_file):
        vision_file(_ALL_DONE)
        result = build_vision_context()
        assert result is None

    def test_returns_context_with_next_story(self, mock_config_paths, vision_file):
        vision_file(_TWO_STORIES)
        result = build_vision_context()
        assert result is not None
        assert "Second Story" in result
        assert "Second story content" in result

    def test_context_contains_status_table(self, mock_config_paths, vision_file):
        vision_file(_TWO_STORIES)
        result = build_vision_context()
        assert result is not None
        assert "Vision Roadmap" in result
        assert "| # | Title | Status |" in result
        assert "DONE" in result
        assert "TODO" in result

    def test_context_contains_next_story_heading(self, mock_config_paths, vision_file):
        vision_file(_TWO_STORIES)
        result = build_vision_context()
        assert result is not None
        assert "Next: Story 2" in result

    def test_context_respects_max_chars(self, mock_config_paths, vision_file, monkeypatch):
        vision_file(_TWO_STORIES)
        # Monkeypatch a very small budget to force truncation
        from ocd import vision as vision_mod

        monkeypatch.setattr(vision_mod, "MAX_VISION_CONTEXT_CHARS", 200)
        result = build_vision_context(max_chars=200)
        assert result is not None
        assert len(result) <= 200

    def test_includes_referenced_files(self, mock_config_paths, vision_file):
        (mock_config_paths / "agent-sdk.md").write_text("SDK docs here", encoding="utf-8")
        vision_file(_REFS_STORY)
        result = build_vision_context()
        assert result is not None
        assert "agent-sdk.md" in result
        assert "SDK docs here" in result

    def test_skips_referenced_files_outside_user(self, mock_config_paths, vision_file):
        vision_file("### 1. Story\n\nSee `../../etc/passwd` for secrets.\n")
        result = build_vision_context()
        assert result is not None
        assert "Referenced Files" not in result

    def test_includes_user_standards(self, mock_config_paths, vision_file):
        (mock_config_paths / "STANDARDS.md").write_text(
            "# User Standards\n\nBe excellent.", encoding="utf-8"
        )
        vision_file(_TWO_STORIES)
        result = build_vision_context()
        assert result is not None
        assert "User Standards" in result
        assert "Be excellent" in result

    def test_skips_user_standards_when_absent(self, mock_config_paths, vision_file):
        vision_file(_TWO_STORIES)
        result = build_vision_context()
        assert result is not None
        assert "User Standards" not in result

    def test_logs_selection(self, mock_config_paths, vision_file):
        vision_file(_TWO_STORIES)
        build_vision_context()
        log_path = mock_config_paths / "logs" / "vision.log"
        assert log_path.exists()
        log_content = log_path.read_text(encoding="utf-8")
        assert "selected story 2" in log_content

    def test_logs_all_done(self, mock_config_paths, vision_file):
        vision_file(_ALL_DONE)
        build_vision_context()
        log_path = mock_config_paths / "logs" / "vision.log"
        assert log_path.exists()
        log_content = log_path.read_text(encoding="utf-8")
        assert "all stories DONE" in log_content

    def test_no_log_when_no_vision_file(self, mock_config_paths):
        build_vision_context()
        log_path = mock_config_paths / "logs" / "vision.log"
        assert not log_path.exists()
