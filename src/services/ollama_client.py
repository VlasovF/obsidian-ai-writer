"""Ollama API client for embeddings and LLM."""

import json
import logging
from typing import Any

import requests
from requests.exceptions import ConnectionError

from src.config import settings
from src.core.exceptions import EmbeddingError, LLMGenerationError, ServiceUnavailableError

logger = logging.getLogger(__name__)


class OllamaClient:
    """HTTP client for Ollama API."""

    def __init__(
        self,
        host: str | None = None,
        embed_model: str | None = None,
        llm_model: str | None = None,
        timeout: int | None = None,
    ):
        """Initialize Ollama client.

        Args:
            host: Ollama API host. Defaults to settings.ollama_host.
            embed_model: Embedding model name. Defaults to settings.ollama_embed_model.
            llm_model: LLM model name. Defaults to settings.ollama_llm_model.
            timeout: Request timeout in seconds. Defaults to settings.ollama_timeout.
        """
        self.host = (host or settings.ollama_host).rstrip("/")
        self.embed_model = embed_model or settings.ollama_embed_model
        self.llm_model = llm_model or settings.ollama_llm_model
        self.timeout = timeout or settings.ollama_timeout

        self._session: requests.Session | None = None

    @property
    def session(self) -> requests.Session:
        """Get or create requests session."""
        if self._session is None:
            self._session = requests.Session()
            self._session.headers.update({"Content-Type": "application/json"})
        return self._session

    def _check_connection(self) -> None:
        """Check if Ollama is reachable."""
        try:
            resp = self.session.get(f"{self.host}/api/tags", timeout=5)
            resp.raise_for_status()
            models = [m.get("name", "") for m in resp.json().get("models", [])]

            # Check if embed model exists
            if not any(self.embed_model in m for m in models):
                logger.warning(f"Embedding model {self.embed_model} not found in Ollama")

            # Check if LLM model exists
            if not any(self.llm_model in m for m in models):
                logger.warning(f"LLM model {self.llm_model} not found in Ollama")

            logger.info(f"Connected to Ollama at {self.host}")
        except ConnectionError as e:
            raise ServiceUnavailableError(
                service="Ollama", reason=f"Connection failed: {str(e)}"
            ) from e
        except Exception as e:
            raise ServiceUnavailableError(
                service="Ollama", reason=f"Unexpected error: {str(e)}"
            ) from e

    def health_check(self) -> bool:
        """Check if Ollama is healthy.

        Returns:
            True if healthy.
        """
        try:
            resp = self.session.get(f"{self.host}/api/tags", timeout=5)
            return resp.status_code == 200
        except Exception:
            return False

    def get_embedding(self, text: str) -> list[float]:
        """Get embedding vector for a single text.

        Args:
            text: Input text.

        Returns:
            Embedding vector as list of floats.

        Raises:
            EmbeddingError: If embedding generation fails.
        """
        try:
            resp = self.session.post(
                f"{self.host}/api/embeddings",
                json={"model": self.embed_model, "prompt": text},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data: dict[str, Any] = resp.json()
            embedding = data.get("embedding")

            if not embedding:
                raise EmbeddingError("Empty embedding returned from Ollama")

            return embedding  # type: ignore[no-any-return]
        except requests.exceptions.Timeout as e:
            raise EmbeddingError(f"Timeout getting embedding: {str(e)}") from e
        except requests.exceptions.RequestException as e:
            raise EmbeddingError(f"Request failed: {str(e)}") from e
        except json.JSONDecodeError as e:
            raise EmbeddingError(f"Invalid JSON response: {str(e)}") from e

    def generate_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> str:
        """Generate text using LLM.

        Args:
            prompt: User prompt.
            system_prompt: System instruction.
            temperature: Temperature parameter (0.0 to 1.0).
            max_tokens: Maximum tokens to generate.

        Returns:
            Generated text.

        Raises:
            LLMGenerationError: If generation fails.
        """
        try:
            messages: list[dict[str, str]] = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            payload: dict[str, Any] = {
                "model": self.llm_model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                },
            }

            resp = self.session.post(
                f"{self.host}/api/chat",
                json=payload,
                timeout=self.timeout * 2,
            )
            resp.raise_for_status()
            data: dict[str, Any] = resp.json()
            response = data.get("message", {}).get("content", "")

            if not response:
                raise LLMGenerationError("Empty response from Ollama")

            return response  # type: ignore[no-any-return]
        except requests.exceptions.Timeout as e:
            raise LLMGenerationError(f"Timeout generating text: {str(e)}") from e
        except requests.exceptions.RequestException as e:
            raise LLMGenerationError(f"Request failed: {str(e)}") from e
        except json.JSONDecodeError as e:
            raise LLMGenerationError(f"Invalid JSON response: {str(e)}") from e

    def get_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
        """Get embeddings for multiple texts.

        Args:
            texts: List of input texts.

        Returns:
            List of embedding vectors.

        Raises:
            EmbeddingError: If embedding generation fails.
        """
        # Ollama doesn't support batch embeddings natively, so we do sequential
        # with a small delay to avoid rate limiting
        embeddings = []
        for text in texts:
            embedding = self.get_embedding(text)
            embeddings.append(embedding)
            # Small delay between requests
            if len(texts) > 1:
                import time

                time.sleep(0.1)
        return embeddings
