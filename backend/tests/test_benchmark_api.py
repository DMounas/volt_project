"""API integration tests for Phase 7 Benchmark & Metric Registry endpoints."""

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)


def test_metrics_registry_endpoint():
    """Verify that /api/v1/benchmarks/metrics/registry returns all canonical metrics."""
    resp = client.get("/api/v1/benchmarks/metrics/registry")
    assert resp.status_code == 200
    data = resp.json()
    assert "metrics" in data
    assert "policies" in data
    assert "ebitda_missing_data" in data

    keys = [m["key"] for m in data["metrics"]]
    assert "energy_service_reliability_pct" in keys
    assert "fast_charge_fill_rate_pct" in keys
    assert "swap_pack_fill_rate_pct" in keys
    assert "energy_loss_ratio_pct" in keys
    assert "renewable_share_pct" in keys
    assert "ebitda_disclosure" in keys

    # Verify policies list contains canonical semantics
    assert "CALIBRATED_BAU" in data["policies"]
    assert "FALLBACK_HEURISTIC" in data["policies"]
    assert "OPEN_LOOP_MILP" in data["policies"]
    assert "CLOSED_LOOP_MPC" in data["policies"]


def test_benchmark_summary_endpoint():
    """Verify /api/v1/benchmarks/summary returns benchmark data."""
    resp = client.get("/api/v1/benchmarks/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert "policy_summary" in data or "status" in data


def test_ablations_and_sensitivities_endpoint():
    """Verify /api/v1/benchmarks/ablations returns ablations and sensitivities."""
    resp = client.get("/api/v1/benchmarks/ablations")
    assert resp.status_code == 200
    data = resp.json()
    assert "ablations" in data
    assert "sensitivities" in data
    assert data["ebitda_status"] == "NOT_EVALUABLE"
