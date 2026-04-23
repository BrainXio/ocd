"""VISION.md parsing and context injection for session initialization.

Reads USER/VISION.md, identifies the next unfinished story, and builds
a compact context string for the session-start hook. Includes a status
table of all stories plus full text of the highest-priority unfinished
story, with budget-aware truncation and optional referenced-file loading.

Also injects USER/STANDARDS.md when it exists alongside VISION.md.

Phase 1: Simple markdown parsing. No Claude Agent SDK required.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from ocd.config import (
    MAX_VISION_CONTEXT_CHARS,
    USER_DIR,
    USER_STANDARDS_FILE,
    VISION_FILE,
    VISION_LOG_FILE,
)

_STORY_HEADING_RE = re.compile(
    r"^###\s+(\d+)\.\s+(.+?)(?:\s+✅\s*DONE)?$",
    re.MULTILINE,
)

_REF_FILE_RE = re.compile(r"`([^`]+[./][^`]+)`")

_TRUNCATION_MARKER = "\n\n...(truncated)"


@dataclass(frozen=True)
class Story:
    """A parsed story from VISION.md."""

    number: int
    title: str
    done: bool
    text: str


@dataclass(frozen=True)
class VisionParseResult:
    """Result of parsing VISION.md."""

    stories: tuple[Story, ...]
    header: str


def parse_vision(content: str) -> VisionParseResult:
    """Parse VISION.md content into structured stories.

    Recognizes story headings in the format:
        ### N. Title   or   ### N. Title ✅ DONE

    Content between headings (up to the next ### or ______) belongs
    to the preceding heading.
    """
    if not content.strip():
        return VisionParseResult(stories=(), header="")

    headings = list(_STORY_HEADING_RE.finditer(content))
    if not headings:
        return VisionParseResult(stories=(), header=content.strip())

    header = content[: headings[0].start()].strip()

    stories: list[Story] = []
    for i, match in enumerate(headings):
        number = int(match.group(1))
        title = match.group(2).strip()
        done = "DONE" in match.group(0)

        start = match.end()
        end = headings[i + 1].start() if i + 1 < len(headings) else len(content)
        section = content[start:end]

        # Truncate at thematic break separator
        sep_match = re.search(r"^_{4,}", section, re.MULTILINE)
        if sep_match:
            section = section[: sep_match.start()]

        stories.append(Story(number=number, title=title, done=done, text=section.strip()))

    return VisionParseResult(stories=tuple(stories), header=header)


def select_next_story(stories: tuple[Story, ...]) -> Story | None:
    """Select the highest-priority unfinished story.

    Returns the first story (by number) that is not DONE, or None
    if all stories are complete.
    """
    for story in stories:
        if not story.done:
            return story
    return None


def _extract_referenced_files(story_text: str) -> list[str]:
    """Extract backtick-wrapped file paths from story text.

    Returns paths that look like file references (contain a dot or slash).
    """
    candidates = _REF_FILE_RE.findall(story_text)
    return [c for c in candidates if "." in c or "/" in c]


def _load_referenced_file(path: str, user_dir: Path | None = None) -> str | None:
    """Load a referenced file if it exists under USER/.

    Returns None if the file does not exist or resolves outside USER/.
    """
    base = user_dir if user_dir is not None else USER_DIR
    target = (base / path).resolve()
    if not target.is_relative_to(base.resolve()):
        return None
    if not target.is_file():
        return None
    try:
        return target.read_text(encoding="utf-8")
    except OSError:
        return None


def _truncate_with_marker(text: str, max_chars: int) -> str:
    """Truncate text to max_chars with a truncation marker if needed."""
    if len(text) <= max_chars:
        return text
    marker_len = len(_TRUNCATION_MARKER)
    return text[: max_chars - marker_len] + _TRUNCATION_MARKER


def _log_vision_activity(message: str) -> None:
    """Append a timestamped log line to VISION_LOG_FILE."""
    from datetime import UTC, datetime

    timestamp = datetime.now(UTC).astimezone().isoformat(timespec="seconds")
    line = f"{timestamp} {message}\n"
    try:
        VISION_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(VISION_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line)
    except OSError:
        pass


def build_vision_context(max_chars: int = MAX_VISION_CONTEXT_CHARS) -> str | None:
    """Build vision context string for session-start injection.

    Returns None if VISION.md does not exist or all stories are DONE.
    Otherwise returns a string containing:
      - A status table of all stories
      - The full text of the next unfinished story
      - Content of referenced files (if they exist under USER/)
      - Content of USER/STANDARDS.md (if it exists)
    Truncated to max_chars with a safe truncation marker.
    """
    if not VISION_FILE.is_file():
        return None

    try:
        content = VISION_FILE.read_text(encoding="utf-8")
    except OSError:
        return None

    result = parse_vision(content)
    next_story = select_next_story(result.stories)

    if next_story is None:
        _log_vision_activity("all stories DONE")
        return None

    _log_vision_activity(f"selected story {next_story.number}: {next_story.title}")

    # Build status table
    table_rows = ["| # | Title | Status |", "|---|-------|--------|"]
    for story in result.stories:
        status = "DONE" if story.done else "TODO"
        table_rows.append(f"| {story.number} | {story.title} | {status} |")
    table = "\n".join(table_rows)

    # Start building context
    parts: list[str] = [f"## Vision Roadmap\n\n{table}"]
    parts.append(f"### Next: Story {next_story.number} — {next_story.title}\n\n{next_story.text}")

    # Budget-aware assembly of remaining sections
    remaining = max_chars - len(parts[0]) - len(parts[1]) - 6  # 6 for separators
    if remaining < 100:
        return _truncate_with_marker("\n\n---\n\n".join(parts), max_chars)

    # Referenced files
    refs = _extract_referenced_files(next_story.text)
    if refs:
        ref_parts: list[str] = []
        for ref_path in refs:
            ref_content = _load_referenced_file(ref_path)
            if ref_content is not None:
                entry = f"#### {ref_path}\n\n{ref_content}"
                if len("\n".join(ref_parts) + "\n" + entry) < remaining - 30:
                    ref_parts.append(entry)
        if ref_parts:
            parts.append("### Referenced Files\n\n" + "\n\n".join(ref_parts))
            remaining -= len(parts[-1]) + 6

    # USER/STANDARDS.md
    if remaining > 100 and USER_STANDARDS_FILE.is_file():
        try:
            standards_content = USER_STANDARDS_FILE.read_text(encoding="utf-8")
            if len(standards_content) < remaining - 30:
                parts.append(f"### User Standards\n\n{standards_content}")
        except OSError:
            pass

    return _truncate_with_marker("\n\n---\n\n".join(parts), max_chars)
