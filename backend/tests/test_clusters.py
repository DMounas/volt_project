"""Tests for clusters endpoint."""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


@pytest.mark.api
def test_clusters_endpoint():
    response = client.get("/api/v1/clusters")
    assert response.status_code == 200
    data = response.json()

    assert data["total_clusters"] == 5
    assert data["provenance"] == "OBSERVED"
    cluster_names = [c["name"] for c in data["clusters"]]
    expected_names = ["Delhi NCR", "Mumbai MMR", "Bengaluru", "Hyderabad", "Chennai"]
    assert cluster_names == expected_names

    # Check each cluster has observed provenance for existence, but ASSUMED for capacity share
    for c in data["clusters"]:
        assert c["provenance"] == "OBSERVED"
        assert c["capacity_provenance"] == "ASSUMED"
        assert c["installed_capacity_share_assumed"] == 0.20
        assert c["installed_capacity_mw_assumed"] == 240.0
