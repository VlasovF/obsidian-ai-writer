"""Tests for Ollama client."""

from unittest.mock import patch

import pytest
import requests

from src.core.exceptions import EmbeddingError, LLMGenerationError
from src.services.ollama_client import OllamaClient


def test_ollama_client_health_check():
    """Test health check."""
    client = OllamaClient()
    # Mock the response
    with patch.object(client.session, "get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"models": [{"name": "test-model"}]}
        assert client.health_check() is True


def test_ollama_client_health_check_failure():
    """Test health check failure."""
    client = OllamaClient()
    with patch.object(client.session, "get") as mock_get:
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection failed")
        assert client.health_check() is False


def test_ollama_client_get_embedding():
    """Test getting embedding."""
    client = OllamaClient()
    mock_embedding = [0.1, 0.2, 0.3]
    mock_response = {"embedding": mock_embedding}

    with patch.object(client.session, "post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = mock_response

        result = client.get_embedding("test text")
        assert result == mock_embedding


def test_ollama_client_get_embedding_error():
    """Test embedding error handling."""
    client = OllamaClient()
    with patch.object(client.session, "post") as mock_post:
        mock_post.side_effect = requests.exceptions.Timeout("Timeout")

        with pytest.raises(EmbeddingError):
            client.get_embedding("test text")


def test_ollama_client_generate_text():
    """Test text generation."""
    client = OllamaClient()
    mock_response = {"message": {"content": "Generated text"}}

    with patch.object(client.session, "post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = mock_response

        result = client.generate_text("prompt")
        assert result == "Generated text"


def test_ollama_client_generate_text_error():
    """Test generation error handling."""
    client = OllamaClient()
    with patch.object(client.session, "post") as mock_post:
        mock_post.side_effect = requests.exceptions.Timeout("Timeout")

        with pytest.raises(LLMGenerationError):
            client.generate_text("prompt")
