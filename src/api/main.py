"""FastAPI application."""

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.endpoints import router
from src.config import setup_logging
from src.infrastructure.celery_app import celery_app
from src.services.ollama_client import OllamaClient
from src.services.qdrant_client import QdrantClient

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> Any:
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Obsidian AI Writer API")

    # Check service health
    services_healthy = True

    # Check Ollama
    try:
        ollama_client = OllamaClient()
        if not ollama_client.health_check():
            logger.warning("Ollama is not healthy")
            services_healthy = False
    except Exception as e:
        logger.warning(f"Failed to connect to Ollama: {str(e)}")
        services_healthy = False

    # Check Qdrant
    try:
        qdrant_client = QdrantClient()
        if not qdrant_client.health_check():
            logger.warning("Qdrant is not healthy")
            services_healthy = False
    except Exception as e:
        logger.warning(f"Failed to connect to Qdrant: {str(e)}")
        services_healthy = False

    if not services_healthy:
        logger.warning("Some services are not healthy. API may not work correctly.")

    yield

    # Shutdown
    logger.info("Shutting down Obsidian AI Writer API")


# Create FastAPI app
app = FastAPI(
    title="Obsidian AI Writer",
    description="Intelligent assistant for Zettelkasten with semantic search",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include router
app.include_router(router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/health/detailed")
async def detailed_health_check() -> dict[str, bool]:
    """Detailed health check for all services."""
    status = {}

    # Check Ollama
    try:
        ollama_client = OllamaClient()
        status["ollama"] = ollama_client.health_check()
    except Exception:
        status["ollama"] = False

    # Check Qdrant
    try:
        qdrant_client = QdrantClient()
        status["qdrant"] = qdrant_client.health_check()
    except Exception:
        status["qdrant"] = False

    # Check Redis (via Celery)
    try:
        celery_app.control.ping(timeout=1)
        status["redis"] = True
    except Exception:
        status["redis"] = False

    return status
