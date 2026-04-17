"""Tests for ocd.utils — pure functions and filesystem utilities."""

import json

import pytest

import ocd.config as config
import ocd.utils as utils


class TestSlugify:
    def test_lowercase_conversion(self):
        assert utils.slugify("Hello World") == "hello-world"

    def test_special_characters_removed(self):
        assert utils.slugify("Hello, World!") == "hello-world"

    def test_underscores_to_hyphens(self):
        assert utils.slugify("hello_world") == "hello-world"

    def test_multiple_hyphens_collapsed(self):
        assert utils.slugify("hello---world") == "hello-world"

    def test_leading_trailing_hyphens_stripped(self):
        assert utils.slugify("--hello--") == "hello"

    def test_unicode_handled(self):
        result = utils.slugify("cafe mole")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_empty_string(self):
        assert utils.slugify("") == ""

    def test_all_special_characters(self):
        assert utils.slugify("@#$%") == ""


class TestExtractWikilinks:
    def test_single_wikilink(self):
        assert utils.extract_wikilinks("See [[concepts/foo]] for details") == ["concepts/foo"]

    def test_multiple_wikilinks(self):
        result = utils.extract_wikilinks("See [[foo]] and [[bar]] then [[baz]]")
        assert result == ["foo", "bar", "baz"]

    def test_no_wikilinks(self):
        assert utils.extract_wikilinks("No links here") == []

    def test_single_brackets_not_matched(self):
        assert utils.extract_wikilinks("[link]") == []

    def test_empty_brackets(self):
        result = utils.extract_wikilinks("[[]]")
        assert result == []


class TestBuildIndexEntry:
    def test_produces_table_row(self):
        result = utils.build_index_entry(
            "concepts/foo.md", "A summary", "daily/2026-04-17.md", "2026-04-17"
        )
        assert "concepts/foo" in result
        assert "A summary" in result
        assert "2026-04-17" in result

    def test_pipe_separated_columns(self):
        result = utils.build_index_entry("a.md", "b", "c", "d")
        assert result.count("|") >= 4


class TestLoadState:
    def test_missing_file_returns_default(self, mock_config_paths):
        state = utils.load_state()
        assert state == {
            "ingested": {},
            "query_count": 0,
            "last_lint": None,
            "total_cost": 0.0,
        }

    def test_existing_file_returns_parsed_content(self, state_file, mock_config_paths):
        state = utils.load_state()
        assert state["query_count"] == 0
        assert "ingested" in state

    def test_corrupt_json_raises(self, mock_config_paths):
        config.STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        config.STATE_FILE.write_text("{invalid json")
        with pytest.raises(json.JSONDecodeError):
            utils.load_state()


class TestSaveState:
    def test_creates_parent_directory(self, mock_config_paths):
        utils.save_state({"test": True})
        assert config.STATE_FILE.exists()

    def test_writes_valid_json(self, mock_config_paths):
        utils.save_state({"query_count": 42, "total_cost": 1.5})
        loaded = utils.load_state()
        assert loaded["query_count"] == 42

    def test_roundtrip(self, mock_config_paths):
        original = {"ingested": {"log.md": {"hash": "abc123"}}, "total_cost": 0.5}
        utils.save_state(original)
        loaded = utils.load_state()
        assert loaded == original


class TestFileHash:
    def test_returns_16_char_hex_string(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello")
        result = utils.file_hash(f)
        assert isinstance(result, str)
        assert len(result) == 16
        assert all(c in "0123456789abcdef" for c in result)

    def test_deterministic(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello")
        assert utils.file_hash(f) == utils.file_hash(f)

    def test_different_content_different_hash(self, tmp_path):
        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.txt"
        f1.write_text("hello")
        f2.write_text("world")
        assert utils.file_hash(f1) != utils.file_hash(f2)


class TestWikiArticleExists:
    def test_exists_when_article_present(self, mock_config_paths, wiki_article):
        wiki_article("concepts/test-concept", "Content")
        assert utils.wiki_article_exists("concepts/test-concept") is True

    def test_not_exists_when_article_absent(self, mock_config_paths):
        assert utils.wiki_article_exists("concepts/nonexistent") is False


class TestReadWikiIndex:
    def test_reads_existing_index(self, mock_config_paths):
        result = utils.read_wiki_index()
        assert "Knowledge Base Index" in result

    def test_returns_default_when_file_missing(self, tmp_path, monkeypatch):
        knowledge = tmp_path / "k"
        knowledge.mkdir()
        monkeypatch.setattr(config, "KNOWLEDGE_DIR", knowledge)
        monkeypatch.setattr(config, "INDEX_FILE", knowledge / "index.md")
        result = utils.read_wiki_index()
        assert "Knowledge Base Index" in result
        assert "| Article |" in result


class TestReadAllWikiContent:
    def test_returns_index_when_no_articles(self, mock_config_paths):
        result = utils.read_all_wiki_content()
        assert "INDEX" in result

    def test_includes_article_content(self, mock_config_paths, wiki_article):
        wiki_article("concepts/test", "Unique test content here")
        result = utils.read_all_wiki_content()
        assert "Unique test content here" in result


class TestListWikiArticles:
    def test_empty_when_no_articles(self, mock_config_paths):
        assert utils.list_wiki_articles() == []

    def test_returns_articles_from_all_subdirs(self, mock_config_paths, wiki_article):
        wiki_article("concepts/alpha", "Alpha")
        wiki_article("connections/beta", "Beta")
        articles = utils.list_wiki_articles()
        names = [a.name for a in articles]
        assert "alpha.md" in names
        assert "beta.md" in names


class TestListRawFiles:
    def test_returns_daily_log_files(self, mock_config_paths, daily_log):
        daily_log("2026-04-16", "# Log content")
        files = utils.list_raw_files()
        assert len(files) == 1
        assert files[0].name == "2026-04-16.md"


class TestCountInboundLinks:
    def test_zero_when_no_links(self, mock_config_paths, wiki_article):
        wiki_article("concepts/alpha", "No links here")
        assert utils.count_inbound_links("concepts/alpha") == 0

    def test_counts_inbound_links(self, mock_config_paths, wiki_article):
        wiki_article("concepts/alpha", "See [[concepts/beta]] for more")
        wiki_article("concepts/beta", "No outbound links")
        assert utils.count_inbound_links("concepts/beta") == 1


class TestGetArticleWordCount:
    def test_counts_words_without_frontmatter(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("Hello world this is a test")
        assert utils.get_article_word_count(f) == 6

    def test_strips_frontmatter(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("---\ntitle: Test\n---\nContent words here")
        assert utils.get_article_word_count(f) == 3

    def test_empty_file(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("")
        assert utils.get_article_word_count(f) == 0
