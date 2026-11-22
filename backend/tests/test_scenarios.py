"""Tests for scenarios endpoint."""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


@pytest.mark.api
def test_scenarios_endpoint():
    response = client.get("/api/v1/scenarios")
    assert response.status_code == 200
    data = response.json()

    assert data["total_scenarios"] == 7
    assert data["provenance"] == "SYNTHETIC"

    scenario_ids = [s["scenario_id"] for s in data["scenarios"]]
    expected_ids = [
        "NORMAL",
        "DEMAND_PEAK",
        "RENEWABLE_DROP",
        "IEX_PRICE_SPIKE",
        "SWAP_SHORTAGE",
        "COMBINED_CRISIS",
        "RECOVERY",
    ]
    for expected in expected_ids:
        assert expected in scenario_ids

    # Check each scenario metadata has valid parameters and provenance
    for s in data["scenarios"]:
        assert s["provenance"] == "SYNTHETIC"
        assert s["demand_multiplier"] > 0
        assert s["renewable_multiplier"] > 0
        assert s["iex_price_multiplier"] > 0
        assert 0.0 <= s["initial_bess_soc"] <= 1.0
        assert 0.0 <= s["initial_pack_ready_fraction"] <= 1.0
        assert s["seed"] > 0
