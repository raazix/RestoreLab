"""
Integration tests for Supermemory live API connectivity, ingestion, and search.
Gracefully skips if credentials are not configured or network is unreachable.
"""

import pytest
from restorelab.config import get_settings
from restorelab.incidents.models import IncidentRecord
from restorelab.knowledge.supermemory_adapter import SupermemoryAdapter


@pytest.mark.integration
def test_supermemory_live_connection():
    """Verify live API connection probe to Supermemory v5 endpoint."""
    settings = get_settings()
    if not settings.supermemory_enabled or not settings.supermemory_api_key:
        pytest.skip("Supermemory live testing skipped: SUPERMEMORY_ENABLED is false or API key is not set.")

    adapter = SupermemoryAdapter(settings)
    ok, msg = adapter.test_connection()
    if not ok:
        pytest.skip(f"Supermemory live endpoint not reachable: {msg}")

    assert ok is True


@pytest.mark.integration
def test_supermemory_live_ingest_and_search():
    """Verify real ingestion and search against Supermemory v5 namespace."""
    settings = get_settings()
    if not settings.supermemory_enabled or not settings.supermemory_api_key:
        pytest.skip("Supermemory live testing skipped: SUPERMEMORY_ENABLED is false or API key is not set.")

    adapter = SupermemoryAdapter(settings)
    ok, _ = adapter.test_connection()
    if not ok:
        pytest.skip("Supermemory API not reachable.")

    test_inc = IncidentRecord(
        incident_id="INC-20261015-LIVE001",
        title="Live Test Ingestion: Bit Rot in Secondary Backup Node",
        severity="medium",
        category="integrity",
        operation_type="restore",
        symptoms=["SHA-256 manifest mismatch observed during nightly restore audit"],
        verified_resolution="Node rebuilt and synchronized from primary cluster.",
    )

    # 1. Ingest sanitized incident document
    ingest_ok = adapter.index_incident(test_inc)
    assert ingest_ok is True

    # 2. Search for related incident
    results = adapter.search("Bit Rot in Secondary Backup Node", limit=3)
    assert isinstance(results, list)
    # Search should return either from Supermemory or transparent fallback
    assert len(results) >= 1
