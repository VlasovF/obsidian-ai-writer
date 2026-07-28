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
        client.delete_point("test_point_1")

        result = client.add_point(
            point_id="test_point_1",
            vector=[0.1] * 1024,  # 1000 -> 1024
            payload={"text": "test", "source": "test"},
        )
        assert result is True

        point = client.get_point("test_point_1")
        assert point is not None
        assert len(point["id"]) == 36
        assert "text" in point["payload"]

        client.delete_point("test_point_1")
    except ServiceUnavailableError:
        pytest.skip("Qdrant not available")


def test_qdrant_client_search():
    """Test searching for similar vectors."""
    try:
        client = QdrantClient()
        client.ensure_collection()

        test_points = [
            ("search_test_1", [0.1] * 1024, {"text": "first"}),  # 1000 -> 1024
            ("search_test_2", [0.2] * 1024, {"text": "second"}),  # 1000 -> 1024
            ("search_test_3", [0.9] * 1024, {"text": "third"}),  # 1000 -> 1024
        ]

        for pid, vec, payload in test_points:
            client.delete_point(pid)
            client.add_point(pid, vec, payload)

        results = client.search(
            vector=[0.11] * 1024,  # 1000 -> 1024
            limit=2,
            score_threshold=0.0,
        )

        assert len(results) <= 2
        if results:
            assert "id" in results[0]
            assert "score" in results[0]
            assert "payload" in results[0]
            assert len(results[0]["id"]) == 36

        for pid, _, _ in test_points:
            client.delete_point(pid)
    except ServiceUnavailableError:
        pytest.skip("Qdrant not available")


def test_qdrant_client_delete_point():
    """Test deleting a point."""
    try:
        client = QdrantClient()
        client.ensure_collection()

        client.add_point("delete_test", [0.5] * 1024, {"text": "delete me"})  # 1000 -> 1024
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

        count_before = client.count_points()

        client.add_point("count_test", [0.5] * 1024, {"text": "count me"})  # 1000 -> 1024

        count_after = client.count_points()
        assert count_after == count_before + 1

        client.delete_point("count_test")
    except ServiceUnavailableError:
        pytest.skip("Qdrant not available")
