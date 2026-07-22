"""File hashing utilities for deduplication."""

import hashlib
from pathlib import Path


class FileHasher:
    """Computes MD5 hash of file content for deduplication."""

    @staticmethod
    def compute_hash(content: str | bytes) -> str:
        """Compute MD5 hash of content.

        Args:
            content: String or bytes content to hash.

        Returns:
            MD5 hash as hexadecimal string.
        """
        if isinstance(content, str):
            content = content.encode("utf-8")
        return hashlib.md5(content).hexdigest()

    @staticmethod
    def compute_file_hash(file_path: Path) -> str:
        """Compute MD5 hash of file content.

        Args:
            file_path: Path to the file.

        Returns:
            MD5 hash as hexadecimal string.

        Raises:
            FileNotFoundError: If file does not exist.
            OSError: If file cannot be read.
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        with open(file_path, "rb") as f:
            content = f.read()
        return FileHasher.compute_hash(content)
