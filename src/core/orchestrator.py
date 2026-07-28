"""Orchestrator - core business logic for note processing."""

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from src.config import settings
from src.core.deduplication import DeduplicationGuard
from src.core.exceptions import (
    DeduplicationError,
    EmbeddingError,
    FileProcessingError,
    LLMGenerationError,
    QdrantError,
)
from src.infrastructure.inbox_manager import InboxManager
from src.infrastructure.vault_scanner import VaultScanner
from src.services.embedding_service import EmbeddingService
from src.services.ollama_client import OllamaClient
from src.services.qdrant_client import QdrantClient

logger = logging.getLogger(__name__)


class Orchestrator:
    """Orchestrator for note processing pipeline."""

    def __init__(
        self,
        embedding_service: EmbeddingService,
        qdrant_client: QdrantClient,
        ollama_client: OllamaClient,
        inbox_manager: InboxManager,
        vault_scanner: VaultScanner,
    ):
        """Initialize orchestrator.

        Args:
            embedding_service: Service for generating embeddings.
            qdrant_client: Qdrant vector database client.
            ollama_client: Ollama API client.
            inbox_manager: Manager for inbox files.
            vault_scanner: Scanner for vault notes.
        """
        self.embedding_service = embedding_service
        self.qdrant_client = qdrant_client
        self.ollama_client = ollama_client
        self.inbox_manager = inbox_manager
        self.vault_scanner = vault_scanner
        self.dedup_guard = DeduplicationGuard(qdrant_client, embedding_service)

        # Ensure collection exists
        self.qdrant_client.ensure_collection()

    def process_inbox(self) -> dict[str, Any]:
        """Process all pending files in inbox.

        Returns:
            Dictionary with processing results.
        """
        logger.info("Starting inbox processing")

        # Get pending files
        files = self.inbox_manager.list_pending(limit=settings.max_files_per_batch)

        if not files:
            logger.info("No pending files in inbox")
            return {"status": "success", "files_processed": 0, "message": "No files to process"}

        logger.info(f"Found {len(files)} files to process")

        results: dict[str, Any] = {
            "total": len(files),
            "processed": 0,
            "failed": 0,
            "skipped": 0,
            "details": [],
        }

        for file_path in files:
            try:
                logger.info(f"Processing file: {file_path.name}")
                result = self.process_file(file_path)

                # Check if it was a duplicate
                if result.get("status") == "duplicate":
                    results["skipped"] += 1
                    results["details"].append(
                        {
                            "file": str(file_path),
                            "status": "skipped",
                            "reason": result.get("message", "Duplicate detected"),
                        }
                    )
                else:
                    results["processed"] += 1
                    results["details"].append(
                        {"file": str(file_path), "status": "success", "result": result}
                    )

            except DeduplicationError as e:
                logger.warning(f"Skipped duplicate: {file_path.name} - {str(e)}")
                results["skipped"] += 1
                results["details"].append(
                    {"file": str(file_path), "status": "skipped", "reason": str(e)}
                )
                # Delete skipped file from inbox
                self.inbox_manager.safe_delete(file_path)
            except Exception as e:
                logger.error(f"Failed to process {file_path.name}: {str(e)}", exc_info=True)
                results["failed"] += 1
                results["details"].append(
                    {"file": str(file_path), "status": "failed", "error": str(e)}
                )

        return results

    def process_file(self, file_path: Path) -> dict[str, Any]:
        """Process a single file from inbox.

        Args:
            file_path: Path to the file to process.

        Returns:
            Dictionary with processing results.

        Raises:
            FileProcessingError: If file processing fails.
            DeduplicationError: If duplicate detected.
        """
        logger.info(f"Processing file: {file_path.name}")

        # 1. Read file content
        try:
            content = self.inbox_manager.read_file(file_path)
            file_hash = self.inbox_manager.get_file_metadata(file_path)["hash"]
            logger.debug(f"File hash: {file_hash}")
        except Exception as e:
            raise FileProcessingError(f"Failed to read file {file_path.name}: {str(e)}") from e

        # 2. Check for duplicates
        try:
            is_duplicate, existing_id, similarity = self.dedup_guard.check_duplicate(content)
            if is_duplicate:
                if existing_id is not None:
                    self._append_to_existing_note(existing_id, file_path.name, file_hash)
                    self.inbox_manager.safe_delete(file_path)
                    return {
                        "status": "duplicate",
                        "message": f"Content appended to existing note {existing_id}",
                        "similarity": similarity,
                        "existing_id": existing_id,
                    }
                else:
                    logger.warning("Duplicate detected but existing_id is None, skipping")
                    self.inbox_manager.safe_delete(file_path)
                    return {
                        "status": "duplicate",
                        "message": "Duplicate detected but could not append to existing note",
                        "similarity": similarity,
                    }
        except Exception as e:
            raise DeduplicationError(f"Duplicate check failed: {str(e)}") from e

        # 3. Get embedding for content
        try:
            embedding = self.embedding_service.embed_text(content)
            logger.debug(f"Embedding generated, dimension: {len(embedding)}")
        except EmbeddingError as e:
            raise FileProcessingError(f"Failed to generate embedding: {str(e)}") from e

        # 4. Search for similar notes
        try:
            similar_notes = self.qdrant_client.search(
                vector=embedding,
                limit=3,
                score_threshold=settings.similarity_threshold,
            )
            logger.info(f"Found {len(similar_notes)} similar notes")
        except QdrantError as e:
            raise FileProcessingError(f"Failed to search similar notes: {str(e)}") from e

        # 5. Build prompt with context
        prompt = self._build_prompt(content, similar_notes)

        # 6. Generate text
        try:
            system_prompt = self._get_system_prompt()
            generated_text = self.ollama_client.generate_text(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.7,
                max_tokens=2000,
            )
            logger.debug("Text generated successfully")
        except LLMGenerationError as e:
            raise FileProcessingError(f"Failed to generate text: {str(e)}") from e

        # 7. Parse and save note
        try:
            parsed_content = self._parse_response(generated_text, file_path.name)
            saved_path = self.inbox_manager.save_note(parsed_content)
            logger.info(f"Note saved to: {saved_path}")

            # 8. Add to Qdrant index
            note_id = saved_path.stem
            self.qdrant_client.add_point(
                point_id=note_id,
                vector=embedding,
                payload={
                    "text": parsed_content,
                    "source": str(saved_path),
                    "hash": file_hash,
                    "created_at": datetime.now().isoformat(),
                },
            )
            logger.info(f"Vector added to Qdrant with ID: {note_id}")

            # 9. Delete from inbox
            self.inbox_manager.safe_delete(file_path)

            return {
                "status": "success",
                "message": "Note created successfully",
                "path": str(saved_path),
                "similar_notes": len(similar_notes),
            }

        except Exception as e:
            raise FileProcessingError(f"Failed to save note: {str(e)}") from e

    def _build_prompt(self, content: str, similar_notes: list[dict[str, Any]]) -> str:
        """Build prompt with context from similar notes.

        Args:
            content: Original content from inbox.
            similar_notes: List of similar notes from Qdrant.

        Returns:
            Prompt string.
        """
        prompt_parts = [
            "Here is a new note idea from my Obsidian inbox:",
            "",
            "--- NEW NOTE CONTENT ---",
            content,
            "",
        ]

        if similar_notes:
            prompt_parts.append("--- SIMILAR EXISTING NOTES (for context) ---")
            for i, note in enumerate(similar_notes, 1):
                note_text = note.get("payload", {}).get("text", "")
                score = note.get("score", 0)
                note_id = note.get("id", "unknown")
                prompt_parts.append(f"\nNote {i} (similarity: {score:.2f}, ID: {note_id}):")
                prompt_parts.append(note_text[:500] + "..." if len(note_text) > 500 else note_text)

        prompt_parts.extend(
            [
                "",
                "--- INSTRUCTIONS ---",
                "Please create a well-structured markdown note based on the new content and context from similar notes.",
                "The note should have:",
                "1. A clear title (# Title)",
                "2. Main thoughts section (## Thoughts)",
                "3. Connections section linking to similar notes (## Connections)",
                "",
                "Format your response as valid markdown.",
            ]
        )

        return "\n".join(prompt_parts)

    def _get_system_prompt(self) -> str:
        """Get system prompt for LLM.

        Returns:
            System prompt string.
        """
        return """You are an AI assistant for Obsidian Zettelkasten notes.
Your task is to create structured, connected notes that integrate well with existing knowledge.
Use markdown formatting. Include references to similar notes when relevant."""

    def _parse_response(self, response: str, original_filename: str) -> str:
        """Parse and clean LLM response.

        Args:
            response: Raw LLM response.
            original_filename: Original filename for fallback.

        Returns:
            Cleaned markdown content.
        """
        # Remove any code blocks if present
        content = re.sub(r"```markdown\n(.*?)\n```", r"\1", response, flags=re.DOTALL)
        content = re.sub(r"```\n(.*?)\n```", r"\1", content, flags=re.DOTALL)

        # Ensure there's a title
        if not re.search(r"^#\s+", content, re.MULTILINE):
            # Generate title from filename or first line
            title = original_filename.replace(".md", "").replace("_", " ").title()
            content = f"# {title}\n\n{content}"

        # Ensure required sections
        if "## Thoughts" not in content and "## Мысли" not in content:
            content += "\n\n## Thoughts\n\nAdd your thoughts here."

        if "## Connections" not in content and "## Связи" not in content:
            content += "\n\n## Connections\n\nAdd connections to related notes."

        return content.strip()

    def _append_to_existing_note(self, note_id: str, source_file: str, file_hash: str) -> None:
        """Append source filename to existing note."""
        if note_id is None:
            logger.warning("Cannot append to note: note_id is None")
            return

        try:
            # Get existing point with vectors
            point = self.qdrant_client.get_point(note_id, is_uuid=True, with_vectors=True)
            if not point:
                logger.warning(f"Note {note_id} not found in Qdrant")
                return

            vector = point.get("vector")
            if not vector:
                logger.warning(f"Note {note_id} has no vector, skipping append")
                return

            existing_text = point.get("payload", {}).get("text", "")
            if not existing_text:
                logger.warning(f"Note {note_id} has no text payload, skipping append")
                return

            # Check if this source was already appended
            if f"**Источник:** {source_file}" in existing_text:
                logger.debug(f"Source {source_file} already appended to note {note_id}")
                return

            # Append source reference
            new_text = (
                existing_text + f"\n\n---\n**Источник:** {source_file} (обработан как дубликат)\n"
            )

            # Update in Qdrant using upsert with existing vector
            self.qdrant_client.add_point(
                point_id=note_id,
                vector=vector,
                payload={
                    "text": new_text,
                    "source": point.get("payload", {}).get("source", ""),
                    "hash": point.get("payload", {}).get("hash", file_hash),
                    "updated_at": datetime.now().isoformat(),
                    "appended_from": source_file,
                },
            )
            logger.info(f"Appended source {source_file} to existing note: {note_id}")

            # Also update the actual file in vault
            source_path = point.get("payload", {}).get("source", "")
            if source_path:
                try:
                    import os

                    if os.path.exists(source_path):
                        with open(source_path, "w", encoding="utf-8") as f:
                            f.write(new_text)
                        logger.info(f"Updated file: {source_path}")
                except Exception as e:
                    logger.error(f"Failed to update file {source_path}: {str(e)}")

        except Exception as e:
            logger.error(f"Failed to append to existing note {note_id}: {str(e)}")
            raise QdrantError(f"Failed to append to existing note {note_id}: {str(e)}") from e
