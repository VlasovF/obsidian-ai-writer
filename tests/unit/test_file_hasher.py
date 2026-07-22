"""Tests for FileHasher."""

import tempfile
from pathlib import Path

import pytest

from src.infrastructure.file_hasher import FileHasher


def test_compute_hash_string():
    """Test computing hash from string."""
    content = "Hello, World!"
    hash1 = FileHasher.compute_hash(content)
    hash2 = FileHasher.compute_hash(content)
    assert hash1 == hash2
    assert len(hash1) == 32  # MD5 hex length


def test_compute_hash_bytes():
    """Test computing hash from bytes."""
    content = b"Hello, World!"
    hash1 = FileHasher.compute_hash(content)
    hash2 = FileHasher.compute_hash(b"Hello, World!")
    assert hash1 == hash2


def test_compute_file_hash():
    """Test computing hash from file."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
        f.write("Test content")
        file_path = Path(f.name)

    try:
        file_hash = FileHasher.compute_file_hash(file_path)
        content_hash = FileHasher.compute_hash("Test content")
        assert file_hash == content_hash
    finally:
        file_path.unlink()


def test_compute_file_hash_not_found():
    """Test hash computation on non-existent file."""
    with pytest.raises(FileNotFoundError):
        FileHasher.compute_file_hash(Path("/nonexistent/file.txt"))


def test_hash_different_content():
    """Test that different content produces different hashes."""
    hash1 = FileHasher.compute_hash("content1")
    hash2 = FileHasher.compute_hash("content2")
    assert hash1 != hash2
