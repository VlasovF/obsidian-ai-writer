"""Tests for configuration loading."""

import os
import tempfile
from pathlib import Path

from src.config import settings


def test_settings_defaults():
    """Test that settings have correct default values."""
    assert settings.ollama_host == "http://ollama:11434"
    assert settings.ollama_embed_model == "mxbai-embed-large"
    assert settings.qdrant_port == 6333
    assert settings.redis_port == 6379
    assert settings.max_files_per_batch == 10
    assert settings.similarity_threshold == 0.7
    assert settings.duplicate_threshold == 0.95
    assert settings.embedding_dimension_min == 1000


def test_settings_from_env():
    """Test that settings can be overridden by environment variables."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
        f.write("OLLAMA_HOST=http://test:11434\n")
        f.write("QDRANT_PORT=6335\n")
        f.write("MAX_FILES_PER_BATCH=5\n")
        env_file = f.name

    try:
        os.environ["ENV_FILE"] = env_file
        from src.config import Settings

        test_settings = Settings()
        assert test_settings.ollama_host == "http://test:11434"
        assert test_settings.qdrant_port == 6335
        assert test_settings.max_files_per_batch == 5
    finally:
        os.unlink(env_file)


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
