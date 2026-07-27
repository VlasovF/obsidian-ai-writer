"""Celery tasks for note processing."""

import logging
from typing import Any

from celery import Task

from src.core.exceptions import ServiceUnavailableError
from src.core.orchestrator import Orchestrator
from src.infrastructure.celery_app import celery_app
from src.infrastructure.inbox_manager import InboxManager
from src.infrastructure.vault_scanner import VaultScanner
from src.services.embedding_service import EmbeddingService
from src.services.ollama_client import OllamaClient
from src.services.qdrant_client import QdrantClient

logger = logging.getLogger(__name__)


class BaseTask(Task):  # type: ignore[misc]
    """Base task with automatic retry on service failures."""

    autoretry_for = (ServiceUnavailableError,)
    retry_kwargs = {"max_retries": 3, "countdown": 60}
    retry_backoff = True
    retry_backoff_max = 300
    retry_jitter = True


@celery_app.task(base=BaseTask, name="process_inbox", bind=True)  # type: ignore[untyped-decorator]
def process_inbox_task(self: Any) -> dict[str, Any]:
    """Process files from Inbox folder.

    Returns:
        Dictionary with processing results.
    """
    logger.info("Starting inbox processing")

    try:
        # Initialize services
        ollama_client = OllamaClient()
        embedding_service = EmbeddingService(client=ollama_client)
        qdrant_client = QdrantClient()
        inbox_manager = InboxManager()
        vault_scanner = VaultScanner()

        # Create orchestrator
        orchestrator = Orchestrator(
            embedding_service=embedding_service,
            qdrant_client=qdrant_client,
            ollama_client=ollama_client,
            inbox_manager=inbox_manager,
            vault_scanner=vault_scanner,
        )

        # Process inbox
        result = orchestrator.process_inbox()

        logger.info(f"Inbox processing completed: {result}")
        return result

    except Exception as e:
        logger.error(f"Inbox processing failed: {str(e)}", exc_info=True)
        raise


@celery_app.task(base=BaseTask, name="rebuild_index", bind=True)  # type: ignore[untyped-decorator]
def rebuild_index_task(self: Any) -> dict[str, Any]:
    """Rebuild Qdrant index from all vault notes.

    Returns:
        Dictionary with rebuild results.
    """
    logger.info("Starting index rebuild")

    try:
        # Initialize services
        ollama_client = OllamaClient()
        embedding_service = EmbeddingService(client=ollama_client)  # noqa: F841
        qdrant_client = QdrantClient()
        vault_scanner = VaultScanner()

        # Rebuild index
        count = qdrant_client.rebuild_index(vault_scanner)

        result = {"status": "completed", "points_added": count}
        logger.info(f"Index rebuild completed: {result}")
        return result

    except Exception as e:
        logger.error(f"Index rebuild failed: {str(e)}", exc_info=True)
        raise


@celery_app.task(base=BaseTask, name="check_ollama_health", bind=True)  # type: ignore[untyped-decorator]
def check_ollama_health_task(self: Any) -> dict[str, Any]:
    """Check Ollama health and models availability.

    Returns:
        Dictionary with health status.
    """
    logger.info("Checking Ollama health")

    try:
        client = OllamaClient()
        is_healthy = client.health_check()

        result = {
            "status": "healthy" if is_healthy else "unhealthy",
            "embed_model": client.embed_model,
            "llm_model": client.llm_model,
        }
        logger.info(f"Ollama health check: {result}")
        return result

    except Exception as e:
        logger.error(f"Ollama health check failed: {str(e)}", exc_info=True)
        return {"status": "unhealthy", "error": str(e)}
