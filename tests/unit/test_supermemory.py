"""
Unit tests for Supermemory v5 integration, mocked API workflows, and privacy safeguards.
All tests run 100% offline with zero paid API dependencies.
"""

from unittest.mock import MagicMock
import pytest
from restorelab.config import RestoreLabSettings
from restorelab.incidents.models import IncidentRecord
from restorelab.knowledge.provider import SearchResult
from restorelab.knowledge.sqlite_search import SQLiteKnowledgeProvider
from restorelab.knowledge.supermemory_adapter import SupermemoryAdapter


@pytest.fixture
def dummy_settings():
    return RestoreLabSettings(
        supermemory_enabled=True,
        supermemory_api_key="sm_test_mock_key_1234567890abcdef",
        supermemory_namespace="test-restorelab-ns",
        supermemory_api_url="https://api.supermemory.ai",
        restic_password="SecretPassphrase99!",
    )


@pytest.fixture
def sample_incident():
    return IncidentRecord(
        incident_id="INC-20261015-XYZ123",
        title="Failed backup of C:\\Users\\Administrator\\Payroll\\october.xlsx",
        severity="critical",
        category="security",
        operation_type="backup",
        symptoms=[
            "Authentication failed with secret SecretPassphrase99!",
            "Unable to write to C:\\Users\\Administrator\\Temp\\lock",
        ],
        verified_resolution="Updated repository password in environment.",
    )


def test_supermemory_configuration_loading(dummy_settings):
    """Test configuration fields are properly bound and namespace compliant."""
    adapter = SupermemoryAdapter(dummy_settings)
    assert adapter.is_available() is True
    assert adapter.namespace == "test-restorelab-ns"
    assert "Active [v5, ns: test-restorelab-ns]" in adapter.get_provider_name()


def test_privacy_sanitization_removes_secrets_and_paths(dummy_settings, sample_incident):
    """Verify passwords, API keys, and filesystem paths are scrubbed."""
    adapter = SupermemoryAdapter(dummy_settings)
    payload = adapter.preview_sanitized_payload(sample_incident)

    content = payload["content"]
    assert "SecretPassphrase99!" not in content
    assert "[REDACTED_PASSWORD]" in content

    # Check local paths
    assert "C:\\Users\\Administrator" not in content
    assert "[LOCAL_PATH]" in content

    # Check metadata
    assert payload["metadata"]["incident_id"] == "INC-20261015-XYZ123"
    assert payload["metadata"]["category"] == "security"
    assert payload["task_type"] == "memory"


def test_mocked_connection_test(dummy_settings):
    """Test connection probe with mocked client response."""
    mock_client = MagicMock()
    mock_client.search.return_value = MagicMock(results=[])

    adapter = SupermemoryAdapter(dummy_settings, client=mock_client)
    ok, msg = adapter.test_connection()

    assert ok is True
    assert "test-restorelab-ns" in msg
    mock_client.search.assert_called_once_with(
        "test-restorelab-ns",
        query="probe_connection",
        limit=1,
    )


def test_mocked_ingestion_workflow(dummy_settings, sample_incident):
    """Test adding incident via document workflow to Supermemory v5."""
    mock_client = MagicMock()
    mock_fallback = MagicMock(spec=SQLiteKnowledgeProvider)

    adapter = SupermemoryAdapter(
        dummy_settings,
        fallback_provider=mock_fallback,
        client=mock_client,
    )

    success = adapter.index_incident(sample_incident)

    assert success is True
    # Verify authoritative local SQLite persistence is always called
    mock_fallback.index_incident.assert_called_once_with(sample_incident)

    # Verify Supermemory v5 add was called with namespace and memory task
    mock_client.add.assert_called_once()
    kwargs = mock_client.add.call_args[1]
    assert mock_client.add.call_args[0][0] == "test-restorelab-ns"
    assert "INC-20261015-XYZ123" in kwargs["content"]
    assert kwargs["task_type"] == "memory"


def test_mocked_retrieval_workflow(dummy_settings):
    """Test searching related incidents with mocked v5 response."""
    mock_client = MagicMock()
    mock_item = MagicMock()
    mock_item.id = "doc-123"
    mock_item.content = "Incident summary: bit rot detected in restored block"
    mock_item.metadata = {
        "incident_id": "INC-20261010-AAA001",
        "category": "integrity",
        "verified_resolution": "Restored from snapshot 4a12bc",
    }
    mock_item.score = 0.94

    mock_client.search.return_value = MagicMock(results=[mock_item])

    adapter = SupermemoryAdapter(dummy_settings, client=mock_client)
    results = adapter.search("bit rot corruption", category="integrity", limit=3)

    assert len(results) == 1
    top = results[0]
    assert top.item_id == "doc-123"
    assert "INC-20261010-AAA001" in top.title
    assert "Matched semantic incident memory" in top.match_reason
    assert top.verified_resolution == "Restored from snapshot 4a12bc"


def test_offline_fallback_on_api_error(dummy_settings):
    """Test graceful fallback to local SQLite knowledge search when Supermemory raises error."""
    mock_client = MagicMock()
    mock_client.search.side_effect = RuntimeError("Network timeout or 503 Service Unavailable")

    mock_fallback = MagicMock(spec=SQLiteKnowledgeProvider)
    mock_fallback.search.return_value = [
        SearchResult(
            item_id="KB-LOCAL-001",
            title="Local SQLite Fallback Match",
            item_type="article",
            snippet="Local resolution snippet",
            match_reason="Fallback match",
        )
    ]

    adapter = SupermemoryAdapter(
        dummy_settings,
        fallback_provider=mock_fallback,
        client=mock_client,
    )

    results = adapter.search("wrong password")

    # Should not crash, and should return fallback results
    assert len(results) == 1
    assert results[0].item_id == "KB-LOCAL-001"
    mock_fallback.search.assert_called_once()


def test_api_key_not_leaked_in_error():
    """Verify that even when an exception contains the API key, it is redacted."""
    secret_key = "sm_secret_never_leak_this_key_99999"
    settings = RestoreLabSettings(
        supermemory_enabled=True,
        supermemory_api_key=secret_key,
    )
    adapter = SupermemoryAdapter(settings)
    err = adapter._safe_error(Exception(f"Connection failed to https://api.supermemory.ai with {secret_key}"))

    assert secret_key not in err
    assert "[REDACTED" in err
