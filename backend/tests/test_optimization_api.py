"""Integration tests for Phase 5 Optimization REST API endpoints."""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


@pytest.mark.api
def test_optimization_scenarios_catalog():
    """Test GET /api/v1/optimization/scenarios."""
    response = client.get("/api/v1/optimization/scenarios")
    assert response.status_code == 200
    data = response.json()
    assert len(data["scenarios"]) >= 4
    assert data["alpha_confidence"] == 0.95
    scenario_ids = [s["scenario_id"] for s in data["scenarios"]]
    assert "NORMAL" in scenario_ids
    assert "PEAK_SQUEEZE_SURGE" in scenario_ids


@pytest.mark.api
def test_optimization_run_deterministic():
    """Test POST /api/v1/optimization/run with deterministic mode."""
    payload = {
        "mode": "DETERMINISTIC_P50",
        "clusters": ["delhi_ncr"],
        "time_limit_seconds": 15.0,
        "mip_gap": 0.02,
        "seed": 42,
    }
    response = client.post("/api/v1/optimization/run", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["mode"] == "DETERMINISTIC_P50"
    assert "delhi_ncr" in data["clusters"]
    assert data["solver_metadata"]["solver_status"] in ("OPTIMAL", "FEASIBLE_GAP")
    assert data["kpis"]["service_reliability_pct"] > 0.0
    assert data["kpis"]["bess_emergency_reserve_compliant"] is True
    assert data["kpis"]["swap_emergency_reserve_compliant"] is True
    assert data["kpis"]["power_headroom_reserve_compliant"] is True


@pytest.mark.api
def test_optimization_latest_endpoint():
    """Test GET /api/v1/optimization/latest."""
    response = client.get("/api/v1/optimization/latest")
    assert response.status_code == 200
    data = response.json()
    assert "run_id" in data
    assert "solver_metadata" in data
    assert "kpis" in data


@pytest.mark.api
def test_optimization_summary_endpoint():
    """Test GET /api/v1/optimization/summary."""
    response = client.get("/api/v1/optimization/summary")
    assert response.status_code == 200
    data = response.json()
    assert "objective_value" in data
    assert "solver_status" in data
    assert "cluster_summaries" in data


@pytest.mark.api
def test_optimization_decisions_endpoint():
    """Test GET /api/v1/optimization/decisions."""
    response = client.get("/api/v1/optimization/decisions?cluster_id=delhi_ncr")
    assert response.status_code == 200
    data = response.json()
    assert data["cluster_id"] == "delhi_ncr"
    assert len(data["decisions"]) == 24
    first_dec = data["decisions"][0]
    assert "discom_mw" in first_dec
    assert "bess_soc_mwh" in first_dec
    assert "swap_packs_ready" in first_dec
    assert "tariff_inr_per_kwh" in first_dec


@pytest.mark.api
def test_optimization_compare_endpoint():
    """Test GET /api/v1/optimization/compare."""
    response = client.get("/api/v1/optimization/compare")
    assert response.status_code == 200
    data = response.json()
    assert "comparison_summary" in data
    assert "bau_baseline" in data["comparison_summary"]
    assert "deterministic_p50" in data["comparison_summary"]
    assert "risk_aware_cvar" in data["comparison_summary"]
    assert "invariants_verified" in data
    assert data["invariants_verified"]["all_modes_identical_demand"] is True
    assert data["invariants_verified"]["bess_reserve_maintained_all"] is True
