"""Tests for FastAPI Simulation and MPC endpoints."""

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_simulation_scenarios_endpoint():
    """Verify scenarios catalog returns all 10 scenarios."""
    resp = client.get("/api/v1/simulation/scenarios")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 10
    sc_ids = [s["id"] for s in data["scenarios"]]
    assert "NORMAL_OPERATION" in sc_ids
    assert "HEATWAVE_COMPOUND" in sc_ids
    assert "COMBINED_MULTI_CITY_CRISIS" in sc_ids


def test_mpc_status_endpoint():
    """Verify MPC controller health and solver telemetry."""
    resp = client.get("/api/v1/mpc/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["controller_status"] == "HEALTHY"
    assert data["receding_horizon"] is True
    assert "appsi_highs" in data["available_solvers"] or "highs" in data["available_solvers"]
    assert len(data["invariants_enforced"]) >= 5


def test_simulation_run_endpoint():
    """Verify POST /api/v1/simulation/run executes and returns valid summary and KPIs."""
    payload = {
        "scenario_id": "NORMAL_OPERATION",
        "policy": "BAU_BASELINE",
        "horizon_hours": 2,
        "clusters": ["delhi_ncr"],
        "seed": 42,
    }
    resp = client.post("/api/v1/simulation/run", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "run_id" in data
    assert data["scenario_id"] == "NORMAL_OPERATION"
    assert data["policy"] == "BAU_BASELINE"
    assert "kpis" in data
    assert data["kpis"]["service_reliability_pct"] >= 0.0
    assert data["ebitda"]["status"] == "NOT_EVALUABLE"

    run_id = data["run_id"]

    # Test GET /api/v1/simulation/runs/{run_id}
    resp_get = client.get(f"/api/v1/simulation/runs/{run_id}")
    assert resp_get.status_code == 200
    assert resp_get.json()["run_id"] == run_id

    # Test GET /api/v1/simulation/runs/{run_id}/timeline
    resp_tl = client.get(f"/api/v1/simulation/runs/{run_id}/timeline")
    assert resp_tl.status_code == 200
    assert len(resp_tl.json()["timeline"]) == 2

    # Test GET /api/v1/simulation/runs/{run_id}/explainability
    resp_ex = client.get(f"/api/v1/simulation/runs/{run_id}/explainability")
    assert resp_ex.status_code == 200
    assert len(resp_ex.json()["explanations"]) >= 2

    # Test GET /api/v1/simulation/runs/{run_id}/events
    resp_ev = client.get(f"/api/v1/simulation/runs/{run_id}/events")
    assert resp_ev.status_code == 200
    assert resp_ev.json()["scenario_id"] == "NORMAL_OPERATION"


def test_simulation_run_not_found():
    """Verify 404 for unknown run_id."""
    resp = client.get("/api/v1/simulation/runs/NON_EXISTENT_RUN_999")
    assert resp.status_code == 404
