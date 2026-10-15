"""
RestoreLab REST API Unit Tests
Tests system status, dashboard metrics, backup operations, incident triage,
and Supermemory endpoints with mocked services.
"""

import pytest
from fastapi.testclient import TestClient

from restorelab.api.main import app, app_ctx


@pytest.fixture
def client():
    return TestClient(app)


def test_api_system_status(client):
    response = client.get("/api/system/status")
    assert response.status_code == 200
    data = response.json()
    assert "restic_installed" in data
    assert "repository_path" in data
    assert "database_path" in data
    assert "supermemory_namespace" in data


def test_api_dashboard_metrics(client):
    response = client.get("/api/dashboard")
    assert response.status_code == 200
    data = response.json()
    assert "total_backups" in data
    assert "total_restores" in data
    assert "verification_ratio" in data
    assert "open_incidents_count" in data


def test_api_settings_view(client):
    response = client.get("/api/settings")
    assert response.status_code == 200
    data = response.json()
    assert "restic_binary_path" in data
    assert "supermemory_namespace" in data
    assert "command_timeout_seconds" in data
    # Ensure raw secret is not leaked in settings response
    assert "supermemory_api_key" not in data
    assert "supermemory_key_configured" in data


def test_api_experiments_list(client):
    response = client.get("/api/experiments")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 7
    first = data[0]
    assert "id" in first
    assert "title" in first
    assert "deterministic_rule" in first


def test_api_incidents_list(client):
    response = client.get("/api/incidents")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_api_knowledge_search_empty(client):
    response = client.get("/api/knowledge/search?query=")
    assert response.status_code == 200
    assert response.json() == []


def test_api_knowledge_search_query(client):
    response = client.get("/api/knowledge/search?query=corruption")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_api_serves_frontend_html(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "RestoreLab" in response.text
    assert "<div id=\"root\"></div>" in response.text


def test_api_generate_sample_data(client):
    response = client.post("/api/backups/generate-sample")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["file_count"] > 0
    assert data["total_bytes"] > 0


