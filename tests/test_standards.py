"""Tests for standards — hash-gated access to the Nine Standards."""

from pathlib import Path

from ocd.standards import (
    _extract_frontmatter_and_body,
    compute_hash,
    compute_standards_hash,
    get_standards_reference,
    get_standards_version,
    update_standards_hash,
    verify_standards_hash,
)

SAMPLE_STANDARDS = """\
---
version: "1.0"
hash: "abc123def45678"
---

### 1. No Dead Code

Every line must be reachable.

### 2. Single Source of Truth

Every fact lives in exactly one place.
"""


class TestExtractFrontmatterAndBody:
    def test_basic(self):
        meta, body = _extract_frontmatter_and_body(SAMPLE_STANDARDS)
        assert meta["version"] == "1.0"
        assert meta["hash"] == "abc123def45678"
        assert "No Dead Code" in body

    def test_no_frontmatter(self):
        meta, body = _extract_frontmatter_and_body("Just body text")
        assert meta == {}
        assert body == "Just body text"

    def test_unclosed_frontmatter(self):
        meta, body = _extract_frontmatter_and_body("---\nversion: 1.0\nNo closing")
        assert meta == {}
        assert "No closing" in body


class TestComputeHash:
    def test_deterministic(self):
        h1 = compute_hash("hello world")
        h2 = compute_hash("hello world")
        assert h1 == h2

    def test_different_inputs(self):
        h1 = compute_hash("hello")
        h2 = compute_hash("world")
        assert h1 != h2

    def test_length(self):
        h = compute_hash("test")
        assert len(h) == 16


class TestComputeStandardsHash:
    def test_with_real_file(self, mock_config_paths, tmp_path):
        skills_dir = tmp_path / ".claude" / "skills" / "ocd"
        skills_dir.mkdir(parents=True)
        std_file = skills_dir / "standards.md"
        std_file.write_text(SAMPLE_STANDARDS)

        import ocd.standards

        prev = ocd.standards.STANDARDS_FILE
        ocd.standards.STANDARDS_FILE = std_file
        try:
            h = compute_standards_hash()
            assert h is not None
            assert len(h) == 16
        finally:
            ocd.standards.STANDARDS_FILE = prev

    def test_missing_file(self, mock_config_paths, monkeypatch):
        monkeypatch.setattr("ocd.standards.STANDARDS_FILE", Path("/nonexistent/standards.md"))
        assert compute_standards_hash() is None


class TestGetStandardsVersion:
    def test_with_real_file(self, mock_config_paths, tmp_path):
        skills_dir = tmp_path / ".claude" / "skills" / "ocd"
        skills_dir.mkdir(parents=True)
        std_file = skills_dir / "standards.md"
        std_file.write_text(SAMPLE_STANDARDS)

        import ocd.standards

        prev = ocd.standards.STANDARDS_FILE
        ocd.standards.STANDARDS_FILE = std_file
        try:
            version = get_standards_version()
            assert version == "1.0"
        finally:
            ocd.standards.STANDARDS_FILE = prev

    def test_missing_file(self, mock_config_paths, monkeypatch):
        monkeypatch.setattr("ocd.standards.STANDARDS_FILE", Path("/nonexistent/standards.md"))
        assert get_standards_version() is None


class TestGetStandardsReference:
    def test_with_real_file(self, mock_config_paths, tmp_path):
        skills_dir = tmp_path / ".claude" / "skills" / "ocd"
        skills_dir.mkdir(parents=True)
        std_file = skills_dir / "standards.md"
        std_file.write_text(SAMPLE_STANDARDS)

        import ocd.standards

        prev = ocd.standards.STANDARDS_FILE
        ocd.standards.STANDARDS_FILE = std_file
        try:
            ref = get_standards_reference()
            assert ref.startswith("ocd-standards:v1.0 [")
            assert ref.endswith("]")
        finally:
            ocd.standards.STANDARDS_FILE = prev

    def test_missing_file(self, mock_config_paths, monkeypatch):
        monkeypatch.setattr("ocd.standards.STANDARDS_FILE", Path("/nonexistent/standards.md"))
        assert get_standards_reference() == ""


class TestVerifyStandardsHash:
    def test_matching_hash(self, mock_config_paths, tmp_path):
        skills_dir = tmp_path / ".claude" / "skills" / "ocd"
        skills_dir.mkdir(parents=True)
        std_file = skills_dir / "standards.md"
        std_file.write_text(SAMPLE_STANDARDS)

        import ocd.standards

        prev = ocd.standards.STANDARDS_FILE
        ocd.standards.STANDARDS_FILE = std_file
        try:
            # First update hash so it matches
            update_standards_hash()
            result = verify_standards_hash()
            assert result["match"] is True
            assert result["stored_hash"] == result["computed_hash"]
            assert result["version"] == "1.0"
        finally:
            ocd.standards.STANDARDS_FILE = prev

    def test_mismatched_hash(self, mock_config_paths, tmp_path):
        skills_dir = tmp_path / ".claude" / "skills" / "ocd"
        skills_dir.mkdir(parents=True)
        std_file = skills_dir / "standards.md"
        std_file.write_text(SAMPLE_STANDARDS)

        import ocd.standards

        prev = ocd.standards.STANDARDS_FILE
        ocd.standards.STANDARDS_FILE = std_file
        try:
            # SAMPLE_STANDARDS has hash "abc123def45678" which doesn't match body
            result = verify_standards_hash()
            assert result["match"] is False
            assert result["stored_hash"] == "abc123def45678"
            assert result["computed_hash"] != "abc123def45678"
        finally:
            ocd.standards.STANDARDS_FILE = prev

    def test_missing_file(self, mock_config_paths, monkeypatch):
        monkeypatch.setattr("ocd.standards.STANDARDS_FILE", Path("/nonexistent/standards.md"))
        result = verify_standards_hash()
        assert result["match"] is False
        assert "error" in result


class TestUpdateStandardsHash:
    def test_updates_hash(self, mock_config_paths, tmp_path):
        skills_dir = tmp_path / ".claude" / "skills" / "ocd"
        skills_dir.mkdir(parents=True)
        std_file = skills_dir / "standards.md"
        std_file.write_text(SAMPLE_STANDARDS)

        import ocd.standards

        prev = ocd.standards.STANDARDS_FILE
        ocd.standards.STANDARDS_FILE = std_file
        try:
            new_hash = update_standards_hash()
            assert new_hash is not None
            # Verify the file was updated
            content = std_file.read_text()
            assert new_hash in content
            # Verify hash now matches
            result = verify_standards_hash()
            assert result["match"] is True
        finally:
            ocd.standards.STANDARDS_FILE = prev

    def test_missing_file(self, mock_config_paths, monkeypatch):
        monkeypatch.setattr("ocd.standards.STANDARDS_FILE", Path("/nonexistent/standards.md"))
        assert update_standards_hash() is None
