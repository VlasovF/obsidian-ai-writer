"""Integration tests for Orchestrator."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.core.orchestrator import Orchestrator
from src.infrastructure.inbox_manager import InboxManager
from src.infrastructure.vault_scanner import VaultScanner
from src.services.embedding_service import EmbeddingService
from src.services.ollama_client import OllamaClient
from src.services.qdrant_client import QdrantClient


@pytest.fixture
def temp_vault():
    """Create temporary vault with inbox."""
    with tempfile.TemporaryDirectory() as tmp:
        vault = Path(tmp)
        inbox = vault / "Inbox"
        inbox.mkdir()
        yield vault, inbox


@pytest.fixture
def mock_services():
    """Create mock services for testing."""
    embedding_service = MagicMock(spec=EmbeddingService)
    qdrant_client = MagicMock(spec=QdrantClient)
    ollama_client = MagicMock(spec=OllamaClient)
    inbox_manager = MagicMock(spec=InboxManager)
    vault_scanner = MagicMock(spec=VaultScanner)

    return {
        "embedding_service": embedding_service,
        "qdrant_client": qdrant_client,
        "ollama_client": ollama_client,
        "inbox_manager": inbox_manager,
        "vault_scanner": vault_scanner,
    }


def test_orchestrator_process_inbox_empty(temp_vault, mock_services):
    """Test processing empty inbox."""
    vault, inbox = temp_vault

    mock_services["inbox_manager"].list_pending.return_value = []
    mock_services["inbox_manager"].inbox_path = inbox

    orchestrator = Orchestrator(**mock_services)
    result = orchestrator.process_inbox()

    assert result["status"] == "success"
    assert result["files_processed"] == 0


def test_orchestrator_process_inbox_with_files(temp_vault, mock_services):
    """Test processing inbox with files."""
    vault, inbox = temp_vault

    # Create test file
    test_file = inbox / "test.md"
    test_file.write_text("# Test Note\n\nThis is a test note.")

    # Mock services
    mock_services["inbox_manager"].list_pending.return_value = [test_file]
    mock_services["inbox_manager"].read_file.return_value = test_file.read_text()
    mock_services["inbox_manager"].get_file_metadata.return_value = {"hash": "abc123"}
    mock_services["inbox_manager"].inbox_path = inbox
    mock_services["inbox_manager"].save_note.return_value = vault / "Test Note.md"

    mock_services["embedding_service"].embed_text.return_value = [0.1] * 1024

    mock_services["qdrant_client"].search.return_value = []
    mock_services["qdrant_client"].add_point.return_value = True

    mock_services["ollama_client"].generate_text.return_value = """# Test Note

## Thoughts

This is a generated thought.

## Connections

No connections found."""

    orchestrator = Orchestrator(**mock_services)
    result = orchestrator.process_inbox()

    # Check that process_inbox returns the expected structure
    assert result["total"] == 1
    assert result["processed"] == 1
    assert result["failed"] == 0
    assert result["skipped"] == 0
    assert len(result["details"]) == 1
    assert result["details"][0]["status"] == "success"


def test_orchestrator_process_file_success(temp_vault, mock_services):
    """Test successful file processing."""
    vault, inbox = temp_vault
    test_file = inbox / "test.md"
    test_file.write_text("# Test Note\n\nThis is a test note.")

    mock_services["inbox_manager"].read_file.return_value = test_file.read_text()
    mock_services["inbox_manager"].get_file_metadata.return_value = {"hash": "abc123"}
    mock_services["inbox_manager"].inbox_path = inbox
    mock_services["inbox_manager"].save_note.return_value = vault / "Test Note.md"

    mock_services["embedding_service"].embed_text.return_value = [0.1] * 1024

    mock_services["qdrant_client"].search.return_value = []
    mock_services["qdrant_client"].add_point.return_value = True

    mock_services["ollama_client"].generate_text.return_value = """# Test Note

## Thoughts

Generated thought.

## Connections

No connections."""

    orchestrator = Orchestrator(**mock_services)
    result = orchestrator.process_file(test_file)

    assert result["status"] == "success"
    assert "path" in result


def test_orchestrator_process_file_duplicate(temp_vault, mock_services):
    """Test duplicate file detection."""
    vault, inbox = temp_vault
    test_file = inbox / "test.md"
    test_file.write_text("# Test Note")

    mock_services["inbox_manager"].read_file.return_value = test_file.read_text()
    mock_services["inbox_manager"].get_file_metadata.return_value = {"hash": "abc123"}
    mock_services["inbox_manager"].inbox_path = inbox

    mock_services["embedding_service"].embed_text.return_value = [0.1] * 1024
    mock_services["qdrant_client"].search.return_value = [
        {"id": "existing_note", "score": 0.96, "payload": {"text": "Existing content"}}
    ]

    orchestrator = Orchestrator(**mock_services)

    # Mock the dedup_guard check
    with patch.object(
        orchestrator.dedup_guard, "check_duplicate", return_value=(True, "existing_note", 0.96)
    ):
        result = orchestrator.process_file(test_file)

        assert result["status"] == "duplicate"
        assert result["existing_id"] == "existing_note"
        assert mock_services["inbox_manager"].safe_delete.called


def test_orchestrator_process_inbox_with_duplicate(temp_vault, mock_services):
    """Test processing inbox with duplicate file."""
    vault, inbox = temp_vault

    # Create test file
    test_file = inbox / "test.md"
    test_file.write_text("# Test Note")

    mock_services["inbox_manager"].list_pending.return_value = [test_file]
    mock_services["inbox_manager"].read_file.return_value = test_file.read_text()
    mock_services["inbox_manager"].get_file_metadata.return_value = {"hash": "abc123"}
    mock_services["inbox_manager"].inbox_path = inbox

    mock_services["embedding_service"].embed_text.return_value = [0.1] * 1024

    orchestrator = Orchestrator(**mock_services)

    # Mock dedup_guard to return duplicate
    with patch.object(
        orchestrator.dedup_guard, "check_duplicate", return_value=(True, "existing_note", 0.96)
    ):
        result = orchestrator.process_inbox()

        assert result["total"] == 1
        assert result["processed"] == 0
        assert result["failed"] == 0
        assert result["skipped"] == 1
        assert result["details"][0]["status"] == "skipped"


def test_orchestrator_process_inbox_with_failure(temp_vault, mock_services):
    """Test processing inbox with failing file."""
    vault, inbox = temp_vault

    # Create test file
    test_file = inbox / "test.md"
    test_file.write_text("# Test Note")

    mock_services["inbox_manager"].list_pending.return_value = [test_file]
    mock_services["inbox_manager"].read_file.side_effect = Exception("Read error")
    mock_services["inbox_manager"].inbox_path = inbox

    orchestrator = Orchestrator(**mock_services)
    result = orchestrator.process_inbox()

    assert result["total"] == 1
    assert result["processed"] == 0
    assert result["failed"] == 1
    assert result["skipped"] == 0
    assert result["details"][0]["status"] == "failed"
    assert "Read error" in str(result["details"][0]["error"])
