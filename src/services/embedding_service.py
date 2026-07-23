"""Embedding service with caching and business logic."""

import logging

from cachetools import LRUCache

from src.services.ollama_client import OllamaClient

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for managing embeddings with caching."""

    def __init__(self, client: OllamaClient | None = None, cache_size: int = 1024):
        """Initialize embedding service.

        Args:
            client: Ollama client instance. Creates new if not provided.
            cache_size: LRU cache size for embeddings.
        """
        self.client = client or OllamaClient()
        self.cache_size = cache_size
        self._cache: LRUCache[str, list[float]] = LRUCache(maxsize=cache_size)

    def embed_text(self, text: str) -> list[float]:
        """Get embedding for a single text with caching.

        Args:
            text: Input text.

        Returns:
            Embedding vector as list of floats.
        """
        if text not in self._cache:
            self._cache[text] = self.client.get_embedding(text)
        return self._cache[text]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Get embeddings for multiple texts.

        Args:
            texts: List of input texts.

        Returns:
            List of embedding vectors.
        """
        return [self.embed_text(text) for text in texts]

    def get_embedding_dimension(self) -> int:
        """Get dimension of embedding vectors.

        Returns:
            Dimension of embedding vector.
        """
        # Get a sample embedding to determine dimension
        sample = self.embed_text("test")
        return len(sample)

    def clear_cache(self) -> None:
        """Clear the embedding cache."""
        self._cache.clear()
        logger.info("Embedding cache cleared")

    def get_cache_stats(self) -> dict[str, int]:
        """Get cache statistics.

        Returns:
            Dictionary with cache size and maxsize.
        """
        return {
            "current_size": len(self._cache),
            "max_size": int(self._cache.maxsize),
        }
