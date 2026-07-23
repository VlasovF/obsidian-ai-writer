"""Qdrant vector storage client wrapper with gRPC support."""

import logging
import uuid
from typing import Any

from qdrant_client import QdrantClient as QdrantBaseClient
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.http.models import (
    Distance,
    PointStruct,
    UpdateStatus,
    VectorParams,
)

from src.config import settings
from src.core.exceptions import QdrantError, ServiceUnavailableError
from src.infrastructure.vault_scanner import VaultScanner

logger = logging.getLogger(__name__)


class QdrantClient:
    """Wrapper for Qdrant vector database operations with gRPC."""

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        grpc_port: int | None = None,
        collection_name: str | None = None,
        vector_size: int | None = None,
        prefer_grpc: bool = True,
    ):
        """Initialize Qdrant client with gRPC support.

        Args:
            host: Qdrant host. Defaults to settings.qdrant_host.
            port: Qdrant HTTP port. Defaults to settings.qdrant_port.
            grpc_port: Qdrant gRPC port. Defaults to settings.qdrant_grpc_port.
            collection_name: Collection name. Defaults to settings.qdrant_collection.
            vector_size: Vector dimension. Defaults to settings.embedding_dimension_min.
            prefer_grpc: Use gRPC protocol. Defaults to True.
        """
        self.host = host or settings.qdrant_host
        self.port = port or settings.qdrant_port
        self.grpc_port = grpc_port or settings.qdrant_grpc_port
        self.collection_name = collection_name or settings.qdrant_collection
        self.vector_size = vector_size or settings.embedding_dimension_min
        self.prefer_grpc = prefer_grpc

        self._client: QdrantBaseClient | None = None
        self._connected = False

    @property
    def client(self) -> QdrantBaseClient:
        """Get or create Qdrant client."""
        if self._client is None:
            self._connect()
        assert self._client is not None
        return self._client

    def _connect(self) -> None:
        """Establish connection to Qdrant via gRPC."""
        try:
            if self.prefer_grpc:
                self._client = QdrantBaseClient(
                    host=self.host,
                    grpc_port=self.grpc_port,
                    prefer_grpc=True,
                    timeout=10,
                    check_compatibility=False,
                )
                logger.info(f"Connected to Qdrant via gRPC at {self.host}:{self.grpc_port}")
            else:
                self._client = QdrantBaseClient(
                    host=self.host,
                    port=self.port,
                    timeout=10,
                    check_compatibility=False,
                )
                logger.info(f"Connected to Qdrant via HTTP at {self.host}:{self.port}")

            # Test connection
            self._client.get_collections()
            self._connected = True
        except Exception as e:
            raise ServiceUnavailableError(
                service="Qdrant", reason=f"Connection failed: {str(e)}"
            ) from e

    def _generate_uuid(self, point_id: str | None = None) -> str:
        """Generate UUID for point ID.

        Args:
            point_id: Optional string ID to use as base.

        Returns:
            UUID string.
        """
        if point_id:
            return str(uuid.uuid5(uuid.NAMESPACE_DNS, point_id))
        return str(uuid.uuid4())

    def ensure_collection(self) -> None:
        """Create collection if it doesn't exist."""
        try:
            collections = self.client.get_collections().collections
            exists = any(c.name == self.collection_name for c in collections)

            if not exists:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_size,
                        distance=Distance.COSINE,
                    ),
                )
                logger.info(f"Created collection: {self.collection_name}")
            else:
                logger.debug(f"Collection already exists: {self.collection_name}")
        except Exception as e:
            raise QdrantError(f"Failed to ensure collection: {str(e)}") from e

    def delete_collection(self) -> None:
        """Delete the collection."""
        try:
            self.client.delete_collection(self.collection_name)
            logger.info(f"Deleted collection: {self.collection_name}")
        except UnexpectedResponse as e:
            if "not found" in str(e).lower():
                logger.warning(f"Collection not found: {self.collection_name}")
            else:
                raise QdrantError(f"Failed to delete collection: {str(e)}") from e
        except Exception as e:
            raise QdrantError(f"Failed to delete collection: {str(e)}") from e

    def add_point(
        self,
        point_id: str,
        vector: list[float],
        payload: dict[str, Any],
    ) -> bool:
        """Add a single point to the collection.

        Args:
            point_id: Unique identifier for the point (will be converted to UUID).
            vector: Embedding vector.
            payload: Metadata payload.

        Returns:
            True if successful.

        Raises:
            QdrantError: If operation fails.
        """
        try:
            self.ensure_collection()
            uuid_id = self._generate_uuid(point_id)
            point = PointStruct(
                id=uuid_id,
                vector=vector,
                payload=payload,
            )
            result = self.client.upsert(
                collection_name=self.collection_name,
                points=[point],
            )
            success = result.status == UpdateStatus.COMPLETED
            if success:
                logger.debug(f"Added point: {point_id} (UUID: {uuid_id})")
            else:
                logger.warning(f"Failed to add point: {point_id}")
            return success
        except Exception as e:
            raise QdrantError(f"Failed to add point {point_id}: {str(e)}") from e

    def search(
        self,
        vector: list[float],
        limit: int = 5,
        score_threshold: float | None = None,
    ) -> list[dict[str, Any]]:
        """Search for similar vectors.

        Args:
            vector: Query embedding vector.
            limit: Maximum number of results.
            score_threshold: Minimum similarity score (0.0 to 1.0).

        Returns:
            List of search results with id, score, and payload.

        Raises:
            QdrantError: If search fails.
        """
        try:
            self.ensure_collection()
            results = self.client.query_points(
                collection_name=self.collection_name,
                query=vector,
                limit=limit,
                score_threshold=score_threshold,
            )

            return [
                {
                    "id": str(point.id),
                    "score": point.score,
                    "payload": point.payload or {},
                }
                for point in results.points
            ]
        except Exception as e:
            raise QdrantError(f"Search failed: {str(e)}") from e

    def delete_point(self, point_id: str) -> bool:
        """Delete a point by ID.

        Args:
            point_id: Point identifier (string ID).

        Returns:
            True if successful.

        Raises:
            QdrantError: If operation fails.
        """
        try:
            uuid_id = self._generate_uuid(point_id)
            result = self.client.delete(
                collection_name=self.collection_name,
                points_selector=[uuid_id],
            )
            return result.status == UpdateStatus.COMPLETED
        except Exception as e:
            raise QdrantError(f"Failed to delete point {point_id}: {str(e)}") from e

    def get_point(self, point_id: str) -> dict[str, Any] | None:
        """Retrieve a point by ID.

        Args:
            point_id: Point identifier (string ID).

        Returns:
            Point data or None if not found.

        Raises:
            QdrantError: If operation fails.
        """
        try:
            uuid_id = self._generate_uuid(point_id)
            result = self.client.retrieve(
                collection_name=self.collection_name,
                ids=[uuid_id],
            )
            if not result:
                return None
            point = result[0]
            return {
                "id": str(point.id),
                "vector": point.vector,
                "payload": point.payload or {},
            }
        except Exception as e:
            raise QdrantError(f"Failed to get point {point_id}: {str(e)}") from e

    def count_points(self) -> int:
        """Get total number of points in collection.

        Returns:
            Number of points.

        Raises:
            QdrantError: If operation fails.
        """
        try:
            result = self.client.count(
                collection_name=self.collection_name,
            )
            return result.count
        except Exception as e:
            raise QdrantError(f"Failed to count points: {str(e)}") from e

    def rebuild_index(self, vault_scanner: VaultScanner) -> int:
        """Rebuild index from all notes in vault.

        This is a placeholder - actual embedding generation will be added in stage 6.

        Args:
            vault_scanner: Scanner to get notes.

        Returns:
            Number of points added.
        """
        logger.info("Rebuild index not yet implemented (needs embedding service)")
        return 0

    def health_check(self) -> bool:
        """Check if Qdrant is healthy.

        Returns:
            True if healthy.
        """
        try:
            self.client.get_collections()
            return True
        except Exception:
            return False
