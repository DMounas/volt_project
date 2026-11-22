"""Tests for Phase 2 API endpoints: data manifest, summary, hourly, IEX diagnostics, calibration."""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


@pytest.mark.api
def test_data_manifest_endpoint():
    response = client.get("/api/v1/data/manifest")
    assert response.status_code == 200
    data = response.json()

    assert data["generator_version"] == "1.0.0"
    assert data["provenance"] == "SYNTHETIC"
    assert data["random_seed"] == 42
    assert len(data["clusters"]) == 5
    assert "cluster_hourly.csv.gz" in data["files"]
    assert "iex_dam_15min.csv.gz" in data["files"]
    assert data["files"]["cluster_hourly.csv.gz"]["row_count"] == 219120


@pytest.mark.api
def test_data_summary_endpoint():
    response = client.get("/api/v1/data/summary")
    assert response.status_code == 200
    data = response.json()

    assert data["total_clusters"] == 5
    assert data["provenance"] == "SYNTHETIC"
    assert len(data["cluster_summaries"]) == 5

    cluster_ids = [c["cluster_id"] for c in data["cluster_summaries"]]
    for expected in ["delhi_ncr", "mumbai_mmr", "bengaluru", "hyderabad", "chennai"]:
        assert expected in cluster_ids

    for c in data["cluster_summaries"]:
        assert c["mean_fast_charge_demand_mwh"] > 0
        assert c["mean_swap_requests"] > 0
        assert c["mean_renewable_available_mwh"] > 0
        assert c["hours_count"] == 43824


@pytest.mark.api
def test_data_hourly_endpoint():
    response = client.get("/api/v1/data/hourly?cluster_id=delhi_ncr&limit=24&offset=0")
    assert response.status_code == 200
    data = response.json()

    assert data["cluster_id"] == "delhi_ncr"
    assert len(data["data"]) == 24
    assert data["limit"] == 24
    assert data["provenance"] == "SYNTHETIC"

    first_pt = data["data"][0]
    assert "timestamp" in first_pt
    assert first_pt["fast_charge_demand_mwh"] >= 0
    assert first_pt["swap_requests"] >= 0


@pytest.mark.api
def test_iex_diagnostics_endpoint():
    response = client.get("/api/v1/data/iex/diagnostics?sample_records=400")
    assert response.status_code == 200
    data = response.json()

    assert data["total_15min_records_read"] == 400
    assert data["complete_hours_count"] == 100  # 400 / 4 = 100 hours
    assert data["aggregation_method_used"] == "VOLUME_WEIGHTED"
    assert data["duplicate_blocks_count"] == 0
    assert data["min_hourly_price_inr_mwh"] > 0


@pytest.mark.api
def test_baseline_calibration_endpoint():
    response = client.get("/api/v1/baseline/calibration")
    assert response.status_code == 200
    data = response.json()

    assert data["target_service_reliability_pct"] == 78.0
    assert data["target_energy_loss_pct"] == 10.0
    assert data["status"] in ["CALIBRATED", "BOUNDED_APPROXIMATION"]
    assert data["provenance"] == "SYNTHETIC_CALIBRATION"
    assert data["energy_reconciliation_pass_rate_pct"] == 100.0

    # Measured values must be actual computed floats
    assert isinstance(data["measured_service_reliability_pct"], float)
    assert isinstance(data["measured_energy_loss_pct"], float)
    assert abs(data["residual_reliability_pct"]) < 2.0
    assert abs(data["residual_loss_pct"]) < 2.0


@pytest.mark.api
def test_baseline_simulation_endpoint():
    response = client.get("/api/v1/baseline/simulation?sample_hours=24")
    assert response.status_code == 200
    data = response.json()

    assert data["total_intervals_audited"] == 120  # 24 hours * 5 clusters
    assert data["reconciliation_pass_rate_pct"] == 100.0
    assert data["is_fully_reconciled"] is True
    assert data["reserve_compliance"] is True
    assert data["residuals"]["max_absolute_residual_mwh"] <= 0.005
