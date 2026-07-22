"""Tests for InboxManager."""

import tempfile
from pathlib import Path

import pytest

from src.core.exceptions import FileProcessingError
from src.infrastructure.inbox_manager import InboxManager


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


def test_list_pending(temp_inbox):
    """Test listing pending files."""
    manager = InboxManager(inbox_path=temp_inbox)
    files = manager.list_pending()
    # Should find .md and .txt but not images or subfolder files
    assert len(files) == 2
    assert any(f.name == "note1.md" for f in files)
    assert any(f.name == "note2.txt" for f in files)


def test_list_pending_limit(temp_inbox):
    """Test limiting pending files."""
    manager = InboxManager(inbox_path=temp_inbox)
    files = manager.list_pending(limit=1)
    assert len(files) == 1


def test_read_file(temp_inbox):
    """Test reading file content."""
    manager = InboxManager(inbox_path=temp_inbox)
    content = manager.read_file(temp_inbox / "note1.md")
    assert content == "# First note"


def test_read_file_not_found(temp_inbox):
    """Test reading non-existent file."""
    manager = InboxManager(inbox_path=temp_inbox)
    with pytest.raises(FileNotFoundError):
        manager.read_file(temp_inbox / "nonexistent.md")


def test_safe_delete(temp_inbox):
    """Test safe deletion of file."""
    manager = InboxManager(inbox_path=temp_inbox)
    file_path = temp_inbox / "note1.md"
    assert file_path.exists()
    result = manager.safe_delete(file_path)
    assert result is True
    assert not file_path.exists()


def test_safe_delete_not_in_inbox(temp_inbox):
    """Test deleting file not in Inbox."""
    manager = InboxManager(inbox_path=temp_inbox)
    with tempfile.NamedTemporaryFile() as f:
        file_path = Path(f.name)
        with pytest.raises(FileProcessingError):
            manager.safe_delete(file_path)


def test_get_file_metadata(temp_inbox):
    """Test getting file metadata."""
    manager = InboxManager(inbox_path=temp_inbox)
    file_path = temp_inbox / "note1.md"
    metadata = manager.get_file_metadata(file_path)
    assert "path" in metadata
    assert "name" in metadata
    assert "size" in metadata
    assert "created_at" in metadata
    assert "hash" in metadata
    assert metadata["name"] == "note1.md"


def test_save_note(temp_inbox):
    """Test saving a note."""
    manager = InboxManager(inbox_path=temp_inbox)
    content = "# New Note\nContent here."
    vault_path = temp_inbox.parent / "Vault"
    vault_path.mkdir()

    saved_path = manager.save_note(content, vault_path)
    assert saved_path.exists()
    assert saved_path.parent == vault_path
    assert saved_path.name.startswith("New Note")
    assert saved_path.suffix == ".md"


def test_save_note_no_heading():
    """Test saving note without heading."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        inbox = tmp_path / "Inbox"
        inbox.mkdir()
        manager = InboxManager(inbox_path=inbox)

        content = "Just some text without heading."
        vault_path = tmp_path / "Vault"
        vault_path.mkdir()

        saved_path = manager.save_note(content, vault_path)
        assert saved_path.exists()
        assert saved_path.parent == vault_path
        assert saved_path.name.startswith("note_")
