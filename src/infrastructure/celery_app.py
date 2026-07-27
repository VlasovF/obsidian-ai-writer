"""Celery application configuration."""

import logging
from typing import Any

from celery import Celery
from celery.signals import setup_logging

from src.config import settings

logger = logging.getLogger(__name__)

# Create Celery app
celery_app = Celery(
    "obsidian_ai_writer",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["src.infrastructure.tasks"],
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes
    task_soft_time_limit=240,  # 4 minutes
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_default_queue="notes",
    task_default_exchange="notes",
    task_default_routing_key="notes",
    result_expires=3600,  # 1 hour
    broker_connection_retry_on_startup=True,
)

# Configure queues
celery_app.conf.task_queues = {
    "notes": {"exchange": "notes", "routing_key": "notes"},
    "index": {"exchange": "index", "routing_key": "index"},
}


@setup_logging.connect  # type: ignore[untyped-decorator]
def setup_celery_logging(**kwargs: Any) -> None:
    """Configure logging for Celery workers."""
    from src.config import setup_logging as configure_logging

    configure_logging()


def get_celery_app() -> Celery:
    """Get Celery app instance.

    Returns:
        Celery application instance.
    """
    return celery_app
