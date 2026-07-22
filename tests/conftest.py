"""Pytest configuration and fixtures."""

import shutil
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    tmp = tempfile.mkdtemp()
    yield Path(tmp)
    shutil.rmtree(tmp)


@pytest.fixture
def sample_markdown():
    """Return sample markdown content."""
    return """# Test Note

This is a test note for the Obsidian AI Writer.

## Section 1

Some content here.

## Section 2

More content with **bold** and *italic* text.
"""


@pytest.fixture
def temp_inbox():
    """Create temporary inbox with test files."""
    with tempfile.TemporaryDirectory() as tmp:
        inbox = Path(tmp) / "Inbox"
        inbox.mkdir()
        # Create test files
        (inbox / "note1.md").write_text("# First note")
        (inbox / "note2.txt").write_text("Second note")
        (inbox / "image.png").write_text("fake")
        (inbox / "subfolder").mkdir()
        (inbox / "subfolder" / "sub.md").write_text("sub note")
        yield inbox
