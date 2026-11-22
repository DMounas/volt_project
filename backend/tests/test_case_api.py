"""Tests for case configuration endpoint."""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


@pytest.mark.api
def test_case_config_endpoint():
    response = client.get("/api/v1/config/case")
    assert response.status_code == 200
    data = response.json()

    # Clusters: 5 clusters
    assert data["cluster_count"] == 5
    assert len(data["clusters"]) == 5
    expected_clusters = ["Delhi NCR", "Mumbai MMR", "Bengaluru", "Hyderabad", "Chennai"]
    for c in expected_clusters:
        assert c in data["clusters"]
    assert data["cluster_provenance"] == "OBSERVED"

    # Installed capacity: 1,200 MW
    assert data["installed_capacity"]["value"] == 1200.0
    assert data["installed_capacity"]["unit"] == "MW"
    assert data["installed_capacity"]["provenance"] == "OBSERVED"

    # Capacity mix: 60% fast charging (720 MW), 40% battery swapping (480 MW)
    cap_mix = data["capacity_mix"]
    assert cap_mix["fast_charging"]["percentage"] == 60.0
    assert cap_mix["fast_charging"]["aggregate_capacity_mw"] == 720.0
    assert cap_mix["fast_charging"]["provenance"] == "OBSERVED"

    assert cap_mix["battery_swapping"]["percentage"] == 40.0
    assert cap_mix["battery_swapping"]["aggregate_capacity_mw"] == 480.0
    assert cap_mix["battery_swapping"]["provenance"] == "OBSERVED"

    # Storage: 600 MWh combined, asset split is NOT known
    storage = data["storage_capacity"]
    assert storage["combined_storage_mwh"] == 600.0
    assert storage["unit"] == "MWh"
    assert storage["asset_split_known"] is False
    assert storage["provenance"] == "OBSERVED"

    # Renewable sourcing: 35% portfolio reference
    ren = data["renewable_sourcing_reference"]
    assert ren["percentage"] == 35.0
    assert ren["provenance"] == "OBSERVED"

    # KPI benchmarks
    kpis = data["kpi_benchmarks"]
    assert kpis["service_reliability"]["current_percentage"] == 78.0
    assert kpis["service_reliability"]["target_percentage"] == 89.7
    assert kpis["service_reliability"]["provenance"] == "OBSERVED"

    assert kpis["energy_losses"]["current_percentage"] == 10.0
    assert kpis["energy_losses"]["target_percentage"] == 8.0
    assert kpis["energy_losses"]["provenance"] == "OBSERVED"

    assert kpis["ebitda_margin"]["target_percentage"] == 12.0
    assert kpis["ebitda_margin"]["operator"] == ">"
    assert kpis["ebitda_margin"]["provenance"] == "OBSERVED"

    # Operating guardrails
    guardrails = data["operating_guardrails"]
    assert guardrails["emergency_reserve"]["percentage"] == 5.0
    assert guardrails["emergency_reserve"]["constraint_type"] == "hard_constraint"

    assert guardrails["customer_tariff_bound"]["min_multiplier"] == 0.80
    assert guardrails["customer_tariff_bound"]["max_multiplier"] == 1.20

    # Unknown assumptions register
    unknowns = data["unknown_assumptions"]
    assert len(unknowns) >= 2
    for u in unknowns:
        assert u["provenance"] == "ASSUMED"
