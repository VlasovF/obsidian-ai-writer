"""Tests for configuration loading."""

import os
from pathlib import Path

from src.config import settings


def test_settings_defaults():
    """Test that settings have correct default values."""
    assert settings.ollama_host == "http://ollama:11434"
    assert settings.ollama_embed_model == "mxbai-embed-large:335m"
    assert settings.qdrant_port == 6333
    assert settings.redis_port == 6379
    assert settings.max_files_per_batch == 10
    assert settings.similarity_threshold == 0.7
    assert settings.duplicate_threshold == 0.95
    assert settings.embedding_dimension_min == 1024


def test_settings_from_env():
    """Test that settings can be overridden by environment variables."""
    original_host = os.environ.get("OLLAMA_HOST")
    os.environ["OLLAMA_HOST"] = "http://test:11434"

    try:
        from src.config import Settings

        test_settings = Settings()
        assert test_settings.ollama_host == "http://test:11434"
    finally:
        if original_host is not None:
            os.environ["OLLAMA_HOST"] = original_host
        else:
            os.environ.pop("OLLAMA_HOST", None)


def test_redis_url_property():
    """Test that redis_url property builds correctly."""
    assert (
        settings.redis_url
        == f"redis://{settings.redis_host}:{settings.redis_port}/{settings.redis_db}"
    )


def test_qdrant_url_property():
    """Test that qdrant_url property builds correctly."""
    assert settings.qdrant_url == f"http://{settings.qdrant_host}:{settings.qdrant_port}"


def test_paths_are_path_objects():
    """Test that path fields are Path objects."""
    assert isinstance(settings.vault_path, Path)
    assert isinstance(settings.inbox_path, Path)
    assert isinstance(settings.templates_path, Path)
    assert isinstance(settings.archive_path, Path)
