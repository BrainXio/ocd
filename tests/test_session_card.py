"""Tests for ocd.session_card module."""

import json

import ocd.config
import ocd.session_card


class TestBuildSessionCard:
    """Tests for build_session_card()."""

    def test_empty_state(self, mock_config_paths):
        card = ocd.session_card.build_session_card()
        assert card == ""

    def test_with_manifest(self, mock_config_paths):
        ocd.session_card.MANIFEST_FILE.write_text(json.dumps({"version": 1, "agents": []}))
        card = ocd.session_card.build_session_card()
        assert "Manifest: manifest.json" in card

    def test_with_kb_index(self, mock_config_paths):
        index = {
            "version": 1,
            "articles": [
                {
                    "title": "test",
                    "file": "concepts/test.md",
                    "summary": "A test article",
                    "keywords": ["test"],
                    "updated": "2026-04-21",
                }
            ],
        }
        ocd.session_card.KB_INDEX_JSON.write_text(json.dumps(index))
        card = ocd.session_card.build_session_card()
        assert "KB:" in card or "articles" in card.lower()

    def test_with_all_sources(self, mock_config_paths):
        index = {
            "version": 1,
            "articles": [
                {
                    "title": "test",
                    "file": "concepts/test.md",
                    "summary": "A test",
                    "keywords": ["test"],
                    "updated": "2026-04-21",
                }
            ],
        }
        ocd.session_card.KB_INDEX_JSON.write_text(json.dumps(index))
        ocd.session_card.MANIFEST_FILE.write_text(json.dumps({"version": 1, "agents": []}))
        card = ocd.session_card.build_session_card()
        assert "Manifest: manifest.json" in card


class TestUpdateSessionCard:
    """Tests for update_session_card()."""

    def test_creates_card_file(self, mock_config_paths):
        sf = ocd.session_card.SESSION_CARD_FILE
        assert not sf.exists()
        ocd.session_card.update_session_card("src/foo.py")
        assert sf.exists()

    def test_appends_entry(self, mock_config_paths):
        sf = ocd.session_card.SESSION_CARD_FILE
        ocd.session_card.update_session_card("src/foo.py", action="edit")
        ocd.session_card.update_session_card("src/bar.py", action="edit")
        content = sf.read_text()
        assert "edit: src/foo.py" in content
        assert "edit: src/bar.py" in content

    def test_default_action_is_edit(self, mock_config_paths):
        sf = ocd.session_card.SESSION_CARD_FILE
        ocd.session_card.update_session_card("src/baz.py")
        content = sf.read_text()
        assert "edit: src/baz.py" in content

    def test_fifo_eviction(self, mock_config_paths):
        max_chars = ocd.session_card.MAX_SESSION_CARD_CHARS
        sf = ocd.session_card.SESSION_CARD_FILE

        for i in range(100):
            ocd.session_card.update_session_card(f"src/file_{i:03d}.py")
        content = sf.read_text()
        assert len(content) <= max_chars
        assert "file_000.py" not in content
        assert "file_099.py" in content

    def test_timestamp_format(self, mock_config_paths):
        sf = ocd.session_card.SESSION_CARD_FILE
        ocd.session_card.update_session_card("src/timed.py")
        content = sf.read_text()
        parts = content.strip().split(" ", 1)
        assert len(parts) == 2
        time_part = parts[0]
        assert len(time_part) == 5
        assert time_part[2] == ":"


class TestLoadSessionCard:
    """Tests for load_session_card()."""

    def test_returns_none_when_missing(self, mock_config_paths):
        result = ocd.session_card.load_session_card()
        assert result is None

    def test_returns_none_when_empty(self, mock_config_paths):
        ocd.session_card.SESSION_CARD_FILE.write_text("")
        result = ocd.session_card.load_session_card()
        assert result is None

    def test_returns_content(self, mock_config_paths):
        ocd.session_card.SESSION_CARD_FILE.write_text(
            "09:30 edit: src/foo.py\n09:35 edit: src/bar.py"
        )
        result = ocd.session_card.load_session_card()
        assert "foo.py" in result
        assert "bar.py" in result

    def test_strips_whitespace(self, mock_config_paths):
        ocd.session_card.SESSION_CARD_FILE.write_text("  \n09:30 edit: src/foo.py\n  ")
        result = ocd.session_card.load_session_card()
        assert result is not None
        assert "foo.py" in result
