"""Tests for health endpoint."""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


@pytest.mark.api
def test_health_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "app_name" in data
    assert "timestamp" in data
    assert data["database"] in ["connected", "disconnected"]


@pytest.mark.api
def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["platform"] == "VOLT"
    assert data["api_v1"] == "/api/v1"
