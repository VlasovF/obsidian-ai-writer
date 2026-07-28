"""Deduplication guard for notes."""

import logging

from src.config import settings
from src.core.exceptions import QdrantError
from src.services.embedding_service import EmbeddingService
from src.services.qdrant_client import QdrantClient

logger = logging.getLogger(__name__)


class DeduplicationGuard:
    """Guard against duplicate notes."""

    def __init__(self, qdrant_client: QdrantClient, embedding_service: EmbeddingService):
        """Initialize deduplication guard.

        Args:
            qdrant_client: Qdrant vector database client.
            embedding_service: Service for generating embeddings.
        """
        self.qdrant_client = qdrant_client
        self.embedding_service = embedding_service
        self.duplicate_threshold = settings.duplicate_threshold

    def check_duplicate(self, content: str) -> tuple[bool, str | None, float | None]:
        """Check if content is a duplicate of an existing note.

        Args:
            content: Content to check.

        Returns:
            Tuple of (is_duplicate, existing_id, similarity_score).
        """
        try:
            # Get embedding for content
            embedding = self.embedding_service.embed_text(content)

            # Search for similar notes
            results = self.qdrant_client.search(
                vector=embedding,
                limit=1,
                score_threshold=self.duplicate_threshold,
            )

            if results and results[0]["score"] >= self.duplicate_threshold:
                return True, results[0]["id"], results[0]["score"]

            return False, None, None

        except QdrantError as e:
            logger.warning(f"Qdrant search failed during deduplication: {str(e)}")
            return False, None, None
        except Exception as e:
            logger.error(f"Unexpected error during deduplication: {str(e)}")
            return False, None, None

    def is_duplicate(self, content: str) -> bool:
        """Check if content is a duplicate.

        Args:
            content: Content to check.

        Returns:
            True if duplicate.
        """
        is_dup, _, _ = self.check_duplicate(content)
        return is_dup
