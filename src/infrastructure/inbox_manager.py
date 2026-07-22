"""Inbox management utilities."""

from datetime import datetime
from pathlib import Path
from typing import Any

from src.config import settings
from src.core.exceptions import FileProcessingError
from src.infrastructure.file_hasher import FileHasher


class InboxManager:
    """Manages files in the Inbox folder."""

    def __init__(self, inbox_path: Path | None = None):
        """Initialize inbox manager.

        Args:
            inbox_path: Path to Inbox folder. Defaults to settings.inbox_path.
        """
        self.inbox_path = inbox_path or settings.inbox_path
        self._ensure_inbox_exists()

    def _ensure_inbox_exists(self) -> None:
        """Create Inbox directory if it doesn't exist."""
        self.inbox_path.mkdir(parents=True, exist_ok=True)

    def list_pending(self, limit: int | None = None) -> list[Path]:
        """List pending files sorted by creation date (oldest first).

        Args:
            limit: Maximum number of files to return.

        Returns:
            List of file paths sorted by creation time.
        """
        if not self.inbox_path.exists():
            return []

        files = []
        for item in self.inbox_path.iterdir():
            if not item.is_file():
                continue
            if self._is_text_file(item):
                files.append(item)

        # Sort by creation time (oldest first)
        files.sort(key=lambda p: p.stat().st_ctime)

        if limit and len(files) > limit:
            files = files[:limit]

        return files

    @staticmethod
    def _is_text_file(file_path: Path) -> bool:
        """Check if file is a text file."""
        extensions = {".md", ".markdown", ".txt", ".text"}
        return file_path.suffix.lower() in extensions

    def read_file(self, file_path: Path) -> str:
        """Read file content with UTF-8 encoding.

        Args:
            file_path: Path to the file.

        Returns:
            File content as string.

        Raises:
            FileNotFoundError: If file does not exist.
            UnicodeDecodeError: If file cannot be decoded.
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        with open(file_path, encoding="utf-8") as f:
            return f.read()

    def safe_delete(self, file_path: Path) -> bool:
        """Delete file with safety checks.

        Args:
            file_path: Path to the file.

        Returns:
            True if deleted successfully, False otherwise.

        Raises:
            FileNotFoundError: If file does not exist.
            PermissionError: If permission denied.
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if not file_path.is_file():
            raise FileProcessingError(f"Not a file: {file_path}")

        # Safety: check that file is in Inbox
        if not str(file_path.parent).endswith("Inbox"):
            raise FileProcessingError(f"File not in Inbox: {file_path}")

        file_path.unlink()
        return True

    def get_file_metadata(self, file_path: Path) -> dict[str, Any]:
        """Extract metadata from file.

        Args:
            file_path: Path to the file.

        Returns:
            Dictionary with file metadata.
        """
        stat = file_path.stat()
        content = self.read_file(file_path)
        file_hash = FileHasher.compute_hash(content)

        return {
            "path": str(file_path),
            "name": file_path.name,
            "size": stat.st_size,
            "created_at": datetime.fromtimestamp(stat.st_ctime),
            "modified_at": datetime.fromtimestamp(stat.st_mtime),
            "hash": file_hash,
        }

    def save_note(self, content: str, vault_path: Path | None = None) -> Path:
        """Save a new note to the vault.

        Args:
            content: Markdown content of the note.
            vault_path: Path to save note. Defaults to settings.vault_path.

        Returns:
            Path to the saved file.
        """
        target_path = vault_path or settings.vault_path
        target_path.mkdir(parents=True, exist_ok=True)

        # Generate filename from first heading or timestamp
        filename = self._generate_filename(content)
        file_path = target_path / filename

        # Avoid overwriting
        counter = 1
        while file_path.exists():
            stem = file_path.stem
            new_stem = f"{stem}_{counter}"
            file_path = file_path.with_stem(new_stem)
            counter += 1

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        return file_path

    @staticmethod
    def _generate_filename(content: str) -> str:
        """Generate filename from content.

        Args:
            content: Note content.

        Returns:
            Filename with .md extension.
        """
        lines = content.splitlines()
        for line in lines:
            if line.startswith("# "):
                # Remove # and trim whitespace, replace invalid chars
                name = line[2:].strip()
                # Replace invalid filename characters
                name = "".join(c for c in name if c.isalnum() or c in " -_")
                if name:
                    return f"{name}.md"

        # Fallback: use timestamp
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        return f"note_{timestamp}.md"
