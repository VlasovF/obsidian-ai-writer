"""Tests for QdrantClient wrapper."""

import pytest

from src.core.exceptions import ServiceUnavailableError
from src.services.qdrant_client import QdrantClient


def test_qdrant_client_connection_failure():
    """Test connection failure handling."""
    client = QdrantClient(host="nonexistent-host", port=6333)
    with pytest.raises(ServiceUnavailableError):
        client.client.get_collections()  # This will trigger connection


def test_qdrant_client_ensure_collection():
    """Test collection creation."""
    try:
        client = QdrantClient()
        client.ensure_collection()
        assert client.collection_name in [
            c.name for c in client.client.get_collections().collections
        ]
    except ServiceUnavailableError:
        pytest.skip("Qdrant not available")


def test_qdrant_client_add_point():
    """Test adding a point."""
    try:
        client = QdrantClient()
        client.ensure_collection()
        # Clean up before test
        client.delete_point("test_point_1")

        result = client.add_point(
            point_id="test_point_1",
            vector=[0.1] * 1000,  # Minimum dimension
            payload={"text": "test", "source": "test"},
        )
        assert result is True

        # Verify point exists
        point = client.get_point("test_point_1")
        assert point is not None
        # ID is UUID, not the original string
        assert len(point["id"]) == 36  # UUID length
        assert "text" in point["payload"]

        # Clean up
        client.delete_point("test_point_1")
    except ServiceUnavailableError:
        pytest.skip("Qdrant not available")


def test_qdrant_client_search():
    """Test searching for similar vectors."""
    try:
        client = QdrantClient()
        client.ensure_collection()

        # Add test points
        test_points = [
            ("search_test_1", [0.1] * 1000, {"text": "first"}),
            ("search_test_2", [0.2] * 1000, {"text": "second"}),
            ("search_test_3", [0.9] * 1000, {"text": "third"}),
        ]

        for pid, vec, payload in test_points:
            client.delete_point(pid)
            client.add_point(pid, vec, payload)

        # Search with vector close to first
        results = client.search(
            vector=[0.11] * 1000,
            limit=2,
            score_threshold=0.0,
        )

        assert len(results) <= 2
        if results:
            assert "id" in results[0]
            assert "score" in results[0]
            assert "payload" in results[0]
            # ID should be UUID
            assert len(results[0]["id"]) == 36

        # Clean up
        for pid, _, _ in test_points:
            client.delete_point(pid)
    except ServiceUnavailableError:
        pytest.skip("Qdrant not available")


def test_qdrant_client_delete_point():
    """Test deleting a point."""
    try:
        client = QdrantClient()
        client.ensure_collection()

        client.add_point("delete_test", [0.5] * 1000, {"text": "delete me"})
        assert client.get_point("delete_test") is not None

        result = client.delete_point("delete_test")
        assert result is True
        assert client.get_point("delete_test") is None
    except ServiceUnavailableError:
        pytest.skip("Qdrant not available")


def test_qdrant_client_count_points():
    """Test counting points."""
    try:
        client = QdrantClient()
        client.ensure_collection()

        # Count before
        count_before = client.count_points()

        # Add a point
        client.add_point("count_test", [0.5] * 1000, {"text": "count me"})

        # Count after
        count_after = client.count_points()
        assert count_after == count_before + 1

        # Clean up
        client.delete_point("count_test")
    except ServiceUnavailableError:
        pytest.skip("Qdrant not available")
