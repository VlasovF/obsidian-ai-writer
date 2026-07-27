"""API endpoints for the application."""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from src.infrastructure.celery_app import celery_app
from src.infrastructure.tasks import process_inbox_task, rebuild_index_task

logger = logging.getLogger(__name__)

router = APIRouter()


class IngestRequest(BaseModel):
    """Request model for ingestion endpoint."""

    file_path: str | None = Field(
        default=None,
        description="Path to specific file to process (if not set, processes all pending)",
    )
    max_files: int | None = Field(
        default=None,
        description="Maximum number of files to process",
        ge=1,
        le=100,
    )


class IngestResponse(BaseModel):
    """Response model for ingestion endpoint."""

    task_id: str = Field(description="Celery task ID")
    status: str = Field(description="Task status")
    message: str = Field(description="Human-readable message")


@router.post("/ingest", response_model=IngestResponse, status_code=status.HTTP_202_ACCEPTED)
async def ingest(request: IngestRequest) -> dict[str, Any]:
    """Start processing of inbox files.

    Args:
        request: Ingest request parameters.

    Returns:
        Task ID and status.

    Raises:
        HTTPException: If task submission fails.
    """
    try:
        # Submit task to Celery
        task = process_inbox_task.delay()

        return {
            "task_id": task.id,
            "status": "submitted",
            "message": "Inbox processing task submitted",
        }

    except Exception as e:
        logger.error(f"Failed to submit ingest task: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit task: {str(e)}",
        ) from e


@router.post("/rebuild-index", response_model=IngestResponse, status_code=status.HTTP_202_ACCEPTED)
async def rebuild_index() -> dict[str, Any]:
    """Rebuild Qdrant index from all vault notes.

    Returns:
        Task ID and status.

    Raises:
        HTTPException: If task submission fails.
    """
    try:
        task = rebuild_index_task.delay()

        return {
            "task_id": task.id,
            "status": "submitted",
            "message": "Index rebuild task submitted",
        }

    except Exception as e:
        logger.error(f"Failed to submit rebuild task: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit task: {str(e)}",
        ) from e


@router.get("/task/{task_id}")
async def get_task_status(task_id: str) -> dict[str, Any]:
    """Get status of a Celery task.

    Args:
        task_id: Celery task ID.

    Returns:
        Task status and result.

    Raises:
        HTTPException: If task not found.
    """
    try:
        task_result = celery_app.AsyncResult(task_id)

        if task_result.state == "PENDING":
            return {"state": "pending", "status": "Task is waiting to be processed"}

        if task_result.state == "STARTED":
            return {"state": "started", "status": "Task is running"}

        if task_result.state == "SUCCESS":
            return {
                "state": "success",
                "status": "Task completed successfully",
                "result": task_result.result,
            }

        if task_result.state == "FAILURE":
            return {
                "state": "failed",
                "status": "Task failed",
                "error": str(task_result.result),
            }

        return {"state": task_result.state, "status": "Unknown state"}

    except Exception as e:
        logger.error(f"Failed to get task status: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get task status: {str(e)}",
        ) from e


@router.post("/task/{task_id}/revoke")
async def revoke_task(task_id: str, terminate: bool = False) -> dict[str, str]:
    """Revoke a Celery task.

    Args:
        task_id: Celery task ID.
        terminate: Whether to terminate the task.

    Returns:
        Status message.

    Raises:
        HTTPException: If revocation fails.
    """
    try:
        celery_app.control.revoke(task_id, terminate=terminate, signal="SIGTERM")
        return {"status": "revoked", "message": f"Task {task_id} revoked"}

    except Exception as e:
        logger.error(f"Failed to revoke task: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to revoke task: {str(e)}",
        ) from e
