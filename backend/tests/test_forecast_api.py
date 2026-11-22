"""Integration tests for Phase 3 forecasting API endpoints."""

from fastapi.testclient import TestClient
import pytest
from backend.app.main import app

client = TestClient(app)


@pytest.mark.api
def test_forecast_summary_endpoint():
    """Verify /api/v1/forecasts/summary returns target metadata and historical bounds."""
    response = client.get("/api/v1/forecasts/summary")
    assert response.status_code == 200
    data = response.json()

    assert "available_targets" in data
    assert len(data["available_targets"]) == 5
    target_names = {t["target_name"] for t in data["available_targets"]}
    assert "fast_charge_demand_mwh" in target_names
    assert "swap_demand_mwh" in target_names
    assert "solar_available_mwh" in target_names
    assert "wind_available_mwh" in target_names
    assert "iex_clearing_price_inr_mwh" in target_names

    assert data["training_date_range"]["start"].startswith("2021-01-01")
    assert data["test_date_range"]["end"].startswith("2025-12-31")
    assert data["provenance"] == "SYNTHETIC"


@pytest.mark.api
def test_forecast_latest_endpoint():
    """Verify /api/v1/forecasts/latest returns 24 horizons with non-crossing quantiles."""
    response = client.get(
        "/api/v1/forecasts/latest",
        params={"cluster_id": "delhi_ncr", "target_name": "fast_charge_demand_mwh"},
    )
    assert response.status_code == 200
    data = response.json()

    assert data["cluster_id"] == "delhi_ncr"
    assert data["target_name"] == "fast_charge_demand_mwh"
    assert len(data["horizons"]) == 24

    for h in data["horizons"]:
        assert h["horizon_hour"] in range(1, 25)
        # Non-crossing check
        assert h["p10"] <= h["p50"] <= h["p90"]
        # Non-negativity check
        assert h["p10"] >= 0.0


@pytest.mark.api
def test_forecast_run_endpoint():
    """Verify POST /api/v1/forecasts/run executes 24h forecast from valid origin."""
    payload = {
        "origin_timestamp": "2025-06-15T12:00:00+05:30",
        "cluster_id": "delhi_ncr",
        "target_name": "fast_charge_demand_mwh",
    }
    response = client.post("/api/v1/forecasts/run", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["cluster_id"] == "delhi_ncr"
    assert len(data["horizons"]) == 24
    assert data["horizons"][0]["horizon_hour"] == 1
    assert data["horizons"][-1]["horizon_hour"] == 24


@pytest.mark.api
def test_forecast_invalid_target_returns_400():
    """Verify unknown target name returns 400 Bad Request."""
    response = client.get(
        "/api/v1/forecasts/latest",
        params={"cluster_id": "delhi_ncr", "target_name": "nonexistent_target"},
    )
    assert response.status_code == 400


@pytest.mark.api
def test_forecast_metrics_endpoint():
    """Verify /api/v1/forecasts/metrics returns backtest metrics."""
    response = client.get("/api/v1/forecasts/metrics")
    assert response.status_code == 200
    data = response.json()

    assert data["evaluation_split"] == "TEST_2025_UNTOUCHED"
    assert "metrics" in data
    assert data["provenance"] == "SYNTHETIC"
