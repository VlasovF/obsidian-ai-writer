"""Tests for EmbeddingService."""

from unittest.mock import patch

from src.services.embedding_service import EmbeddingService
from src.services.ollama_client import OllamaClient


def test_embedding_service_embed_text():
    """Test embedding single text."""
    service = EmbeddingService()
    mock_embedding = [0.1, 0.2, 0.3]

    with patch.object(OllamaClient, "get_embedding", return_value=mock_embedding):
        result = service.embed_text("test")
        assert result == mock_embedding


def test_embedding_service_embed_batch():
    """Test embedding multiple texts."""
    service = EmbeddingService()
    mock_embedding = [0.1, 0.2, 0.3]
    texts = ["text1", "text2", "text3"]

    with patch.object(OllamaClient, "get_embedding", return_value=mock_embedding):
        results = service.embed_batch(texts)
        assert len(results) == 3
        assert all(r == mock_embedding for r in results)


def test_embedding_service_cache():
    """Test embedding caching."""
    service = EmbeddingService(cache_size=2)

    with patch.object(OllamaClient, "get_embedding") as mock_get_embedding:
        mock_get_embedding.side_effect = [
            [0.1, 0.2, 0.3],
            [0.4, 0.5, 0.6],
            [0.7, 0.8, 0.9],
        ]

        # First call should call the client
        service.embed_text("test1")
        assert mock_get_embedding.call_count == 1

        # Second call with same text should use cache
        service.embed_text("test1")
        assert mock_get_embedding.call_count == 1

        # Call with different text
        service.embed_text("test2")
        assert mock_get_embedding.call_count == 2

        # Check cache stats
        stats = service.get_cache_stats()
        assert stats["current_size"] == 2


def test_embedding_service_cache_eviction():
    """Test cache eviction when limit is reached."""
    service = EmbeddingService(cache_size=2)

    with patch.object(OllamaClient, "get_embedding") as mock_get_embedding:
        mock_get_embedding.side_effect = [
            [0.1, 0.2, 0.3],
            [0.4, 0.5, 0.6],
            [0.7, 0.8, 0.9],
        ]

        # Fill cache beyond limit
        service.embed_text("test1")
        service.embed_text("test2")
        service.embed_text("test3")

        # Cache should still be limited to maxsize
        stats = service.get_cache_stats()
        assert stats["current_size"] == 2


def test_embedding_service_clear_cache():
    """Test clearing cache."""
    service = EmbeddingService()

    with patch.object(OllamaClient, "get_embedding") as mock_get_embedding:
        mock_get_embedding.return_value = [0.1, 0.2, 0.3]

        # Fill cache
        service.embed_text("test1")
        service.embed_text("test2")
        stats = service.get_cache_stats()
        assert stats["current_size"] == 2

        # Clear cache
        service.clear_cache()
        stats = service.get_cache_stats()
        assert stats["current_size"] == 0


def test_embedding_service_get_dimension():
    """Test getting embedding dimension."""
    service = EmbeddingService()
    mock_embedding = [0.1] * 1024

    with patch.object(OllamaClient, "get_embedding", return_value=mock_embedding):
        dim = service.get_embedding_dimension()
        assert dim == 1024
