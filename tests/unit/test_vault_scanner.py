"""Tests for VaultScanner."""

import tempfile
from pathlib import Path

import pytest

from src.infrastructure.vault_scanner import VaultScanner


@pytest.fixture
def temp_vault():
    """Create temporary vault structure."""
    with tempfile.TemporaryDirectory() as tmp:
        vault = Path(tmp)
        # Create some files
        (vault / "note1.md").write_text("# Note 1")
        (vault / "note2.txt").write_text("Plain text")
        (vault / "note3.markdown").write_text("# Note 3")
        (vault / "image.png").write_text("fake image")
        (vault / ".hidden.md").write_text("hidden")
        (vault / "_Archive").mkdir()
        (vault / "_Archive" / "archived.md").write_text("archived")
        (vault / "Templates").mkdir()
        (vault / "Templates" / "template.md").write_text("template")
        yield vault


def test_scan_text_files(temp_vault):
    """Test scanning for text files."""
    scanner = VaultScanner(vault_path=temp_vault)
    files = scanner.scan()

    # Should find .md, .txt, .markdown but not images or hidden
    assert len(files) == 3
    assert any(f.name == "note1.md" for f in files)
    assert any(f.name == "note2.txt" for f in files)
    assert any(f.name == "note3.markdown" for f in files)


def test_scan_ignores_archive(temp_vault):
    """Test that _Archive folder is ignored."""
    scanner = VaultScanner(vault_path=temp_vault)
    files = scanner.scan()
    assert not any("_Archive" in str(f) for f in files)


def test_scan_ignores_templates(temp_vault):
    """Test that Templates folder is ignored."""
    scanner = VaultScanner(vault_path=temp_vault)
    files = scanner.scan()
    assert not any("Templates" in str(f) for f in files)


def test_scan_ignores_hidden(temp_vault):
    """Test that hidden files are ignored."""
    scanner = VaultScanner(vault_path=temp_vault)
    files = scanner.scan()
    assert not any(".hidden" in str(f) for f in files)


def test_read_note(temp_vault):
    """Test reading note content."""
    scanner = VaultScanner(vault_path=temp_vault)
    content = scanner.read_note(temp_vault / "note1.md")
    assert content == "# Note 1"


def test_read_note_not_found(temp_vault):
    """Test reading non-existent note."""
    scanner = VaultScanner(vault_path=temp_vault)
    with pytest.raises(FileNotFoundError):
        scanner.read_note(temp_vault / "nonexistent.md")


def test_extract_frontmatter():
    """Test extracting text without frontmatter."""
    scanner = VaultScanner()

    content = """---
title: Test
date: 2024-01-01
---
# Actual Content
Some text here."""
    result = scanner.extract_text_without_frontmatter(content)
    assert "# Actual Content" in result
    assert "title: Test" not in result
    assert result.strip() == "# Actual Content\nSome text here."


def test_extract_no_frontmatter():
    """Test content without frontmatter."""
    scanner = VaultScanner()
    content = "# Just a note\nNo frontmatter here."
    result = scanner.extract_text_without_frontmatter(content)
    assert result == content
