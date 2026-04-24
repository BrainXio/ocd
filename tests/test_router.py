"""Tests for router — agent routing via keyword matching."""

from typing import Any

from ocd.config import MANIFEST_FILE
from ocd.routing.router import (
    _extract_keywords,
    _parse_agent_frontmatter,
    build_manifest,
    load_manifest,
    route_query,
    save_manifest,
)

# ── Frontmatter parsing ──────────────────────────────────────────────────


class TestParseAgentFrontmatter:
    def test_basic(self):
        content = "---\nname: test-agent\ndescription: 'Find issues'\ntools: Glob, Grep\n---\nBody"
        fm = _parse_agent_frontmatter(content)
        assert fm["name"] == "test-agent"
        assert fm["description"] == "Find issues"
        assert fm["tools"] == ["Glob", "Grep"]

    def test_quoted_description(self):
        content = '---\nname: x\ndescription: "Long desc"\n---\nBody'
        fm = _parse_agent_frontmatter(content)
        assert fm["description"] == "Long desc"

    def test_no_frontmatter(self):
        assert _parse_agent_frontmatter("Just body") == {}


# ── Keyword extraction ──────────────────────────────────────────────────


class TestExtractKeywords:
    def test_basic(self):
        keywords = _extract_keywords("Find dead code and unused functions", "")
        assert "dead" in keywords
        assert "code" in keywords
        assert "unused" in keywords
        assert "functions" in keywords

    def test_deduplicates(self):
        keywords = _extract_keywords("code code code review review", "")
        assert keywords.count("code") == 1
        assert keywords.count("review") == 1

    def test_with_scope(self):
        keywords = _extract_keywords("security scanner", "Check for OWASP vulnerabilities")
        assert "security" in keywords
        assert "owasp" in keywords
        assert "vulnerabilities" in keywords


# ── Manifest building ───────────────────────────────────────────────────


class TestBuildManifest:
    def test_builds_from_agents_dir(self, mock_config_paths, monkeypatch, tmp_path):
        agents_dir = tmp_path / "agents"
        agents_dir.mkdir(exist_ok=True)
        (agents_dir / "dead-code-hunter.md").write_text(
            "---\nname: dead-code-hunter\n"
            "description: 'Find dead code per standard'\n"
            "tools: Glob, Grep, Read\n---\n"
            "## Scope\n1. Find unused functions\n2. Find unused vars\n"
        )
        monkeypatch.setattr("ocd.routing.router.AGENTS_DIR", agents_dir)

        manifest = build_manifest()
        assert manifest["version"] == 1
        assert len(manifest["agents"]) == 1
        assert manifest["agents"][0]["name"] == "dead-code-hunter"
        assert "dead" in manifest["agents"][0]["keywords"]
        assert manifest["agents"][0]["tools"] == ["Glob", "Grep", "Read"]

    def test_empty_agents_dir(self, mock_config_paths, monkeypatch, tmp_path):
        agents_dir = tmp_path / "empty_agents"
        agents_dir.mkdir()
        monkeypatch.setattr("ocd.routing.router.AGENTS_DIR", agents_dir)

        manifest = build_manifest()
        assert manifest["agents"] == []


class TestSaveLoadManifest:
    def test_round_trip(self, mock_config_paths):
        manifest = {
            "version": 1,
            "built_at": "2026-04-21T00:00:00",
            "agents": [{"name": "test", "keywords": ["test"]}],
        }
        save_manifest(manifest)
        loaded = load_manifest()
        assert loaded is not None
        assert loaded["agents"][0]["name"] == "test"

    def test_load_missing(self, mock_config_paths):
        if MANIFEST_FILE.exists():
            MANIFEST_FILE.unlink()
        assert load_manifest() is None


# ── Routing ───────────────────────────────────────────────────────────────


class TestRouteQuery:
    def _make_manifest(self, agents: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "version": 1,
            "built_at": "2026-04-21T00:00:00",
            "agents": agents,
        }

    def test_dead_code_query(self):
        manifest = self._make_manifest(
            [
                {
                    "name": "dead-code-hunter",
                    "keywords": ["dead", "code", "unused", "unreachable", "orphan"],
                    "tools": ["Glob", "Grep", "Read"],
                },
                {
                    "name": "owasp-scanner",
                    "keywords": ["security", "owasp", "xss", "injection", "csrf"],
                    "tools": ["Glob", "Grep", "Read"],
                },
            ]
        )
        results = route_query("find dead code and unused functions", manifest)
        assert len(results) >= 1
        assert results[0]["name"] == "dead-code-hunter"
        assert results[0]["score"] > 0

    def test_security_query(self):
        manifest = self._make_manifest(
            [
                {
                    "name": "dead-code-hunter",
                    "keywords": ["dead", "code", "unused"],
                    "tools": ["Glob", "Grep", "Read"],
                },
                {
                    "name": "owasp-scanner",
                    "keywords": ["security", "owasp", "xss", "injection"],
                    "tools": ["Glob", "Grep", "Read"],
                },
            ]
        )
        results = route_query("security scan for injection vulnerabilities", manifest)
        assert len(results) >= 1
        assert results[0]["name"] == "owasp-scanner"

    def test_multi_topic(self):
        manifest = self._make_manifest(
            [
                {
                    "name": "dead-code-hunter",
                    "keywords": ["dead", "code", "unused"],
                    "tools": [],
                },
                {
                    "name": "owasp-scanner",
                    "keywords": ["security", "owasp", "injection"],
                    "tools": [],
                },
                {
                    "name": "lint-status",
                    "keywords": ["lint", "linter", "format", "triad"],
                    "tools": [],
                },
            ]
        )
        results = route_query("lint dead code security", manifest, max_agents=3)
        assert len(results) <= 3
        # All results should have score > 0
        assert all(r["score"] > 0 for r in results)

    def test_no_match(self):
        manifest = self._make_manifest(
            [
                {
                    "name": "dead-code-hunter",
                    "keywords": ["dead", "code", "unused"],
                    "tools": [],
                },
            ]
        )
        results = route_query("quantum physics astronomy", manifest)
        assert results == []

    def test_empty_query(self):
        manifest = self._make_manifest([{"name": "test", "keywords": ["test"], "tools": []}])
        results = route_query("", manifest)
        assert results == []

    def test_max_agents_limit(self):
        manifest = self._make_manifest(
            [{"name": f"agent-{i}", "keywords": ["code", "test"], "tools": []} for i in range(10)]
        )
        results = route_query("code test", manifest, max_agents=2)
        assert len(results) == 2
