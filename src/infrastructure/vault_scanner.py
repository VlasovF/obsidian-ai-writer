"""Vault scanning utilities."""

import re
from pathlib import Path

from src.config import settings


class VaultScanner:
    """Scans and reads notes from Obsidian vault."""

    def __init__(
        self,
        vault_path: Path | None = None,
        ignore_patterns: list[str] | None = None,
    ):
        """Initialize vault scanner.

        Args:
            vault_path: Path to vault root. Defaults to settings.vault_path.
            ignore_patterns: List of regex patterns for files to ignore.
        """
        self.vault_path = vault_path or settings.vault_path
        self.ignore_patterns = ignore_patterns or [
            r"^\.",  # Hidden files
            r"_Archive",  # Archive folder
            r"Templates",  # Templates folder
            r"\.(png|jpg|jpeg|gif|svg|pdf|mp3|wav|mp4|mov)$",  # Media files
            r"\.(exe|dll|so|dylib)$",  # Binaries
        ]

    def scan(self, path: Path | None = None) -> list[Path]:
        """Recursively scan for markdown and text files.

        Args:
            path: Directory to scan. Defaults to vault_path.

        Returns:
            List of file paths.
        """
        scan_path = path or self.vault_path
        if not scan_path.exists():
            return []

        files = []
        for item in scan_path.rglob("*"):
            if not item.is_file():
                continue

            if self._should_ignore(item):
                continue

            if self._is_text_file(item):
                files.append(item)

        return sorted(files)

    def _should_ignore(self, file_path: Path) -> bool:
        """Check if file should be ignored based on patterns.

        Args:
            file_path: Path to check.

        Returns:
            True if file should be ignored.
        """
        # Check if any parent directory matches ignore patterns
        for parent in file_path.parents:
            for pattern in self.ignore_patterns:
                if re.search(pattern, str(parent.name)):
                    return True

        # Check filename
        for pattern in self.ignore_patterns:
            if re.search(pattern, file_path.name):
                return True

        return False

    @staticmethod
    def _is_text_file(file_path: Path) -> bool:
        """Check if file is a text file (md, txt, markdown).

        Args:
            file_path: Path to check.

        Returns:
            True if file is a text file.
        """
        extensions = {".md", ".markdown", ".txt", ".text"}
        return file_path.suffix.lower() in extensions

    def read_note(self, file_path: Path) -> str:
        """Read note content from file.

        Args:
            file_path: Path to the note file.

        Returns:
            Content of the note as string.

        Raises:
            FileNotFoundError: If file does not exist.
            UnicodeDecodeError: If file cannot be decoded as UTF-8.
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Note file not found: {file_path}")

        with open(file_path, encoding="utf-8") as f:
            return f.read()

    def extract_text_without_frontmatter(self, content: str) -> str:
        """Remove frontmatter (YAML header) from note content.

        Args:
            content: Full note content.

        Returns:
            Content without frontmatter.
        """
        lines = content.splitlines()
        if not lines:
            return content

        # Check for frontmatter start
        if lines[0].strip() == "---":
            for i in range(1, len(lines)):
                if lines[i].strip() == "---":
                    return "\n".join(lines[i + 1 :])

        return content
