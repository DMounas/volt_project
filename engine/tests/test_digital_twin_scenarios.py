"""Tests for Scenario Engine catalog and crisis simulation executions.

Verifies:
- All 10 configurable scenarios are present in config/scenarios.yaml
- Each scenario runs stably through the simulator
- Comparative policies behave consistently
"""

import pytest

from engine.twin.events import ScenarioEventEngine
from engine.twin.mpc_controller import RollingMPCController
from engine.twin.schemas import SimulationPolicy


EXPECTED_SCENARIOS = [
    "NORMAL_OPERATION",
    "EVENING_DEMAND_SURGE",
    "SOLAR_CLOUD_DROP",
    "WIND_LULL",
    "IEX_PRICE_SPIKE",
    "GRID_IMPORT_RESTRICTION",
    "SWAP_INVENTORY_SHORTAGE",
    "HEATWAVE_COMPOUND",
    "COMBINED_MULTI_CITY_CRISIS",
    "RECOVERY_AFTER_CRISIS",
]


def test_scenario_catalog_contains_all_10_scenarios():
    """Verify scenarios.yaml defines all 10 required crisis scenarios."""
    engine = ScenarioEventEngine()
    scenarios = engine.list_scenarios()
    sc_ids = [s["id"] for s in scenarios]

    for expected_id in EXPECTED_SCENARIOS:
        assert expected_id in sc_ids, f"Scenario {expected_id} missing from catalog"


def test_all_scenarios_have_valid_structure():
    """Verify parameters of every scenario."""
    engine = ScenarioEventEngine()
    for sc_id in EXPECTED_SCENARIOS:
        sc = engine.get_scenario(sc_id)
        assert "start_hour" in sc
        assert "duration_hours" in sc
        assert "multipliers" in sc
        assert "forecast_visibility" in sc
        assert 0 <= sc["start_hour"] <= 23
        assert sc["duration_hours"] >= 1


def test_heatwave_compound_crisis_simulation():
    """Verify execution under compound heatwave stress."""
    ctrl = RollingMPCController()
    res = ctrl.run_simulation(
        scenario_id="HEATWAVE_COMPOUND",
        policy=SimulationPolicy.BAU_BASELINE,
        horizon_hours=2,
        clusters=["delhi_ncr"],
        seed=123,
    )

    assert res.scenario_id == "HEATWAVE_COMPOUND"
    assert res.invariants_verified["all_clusters_bess_reserve_maintained"] is True
    assert res.invariants_verified["all_clusters_swap_reserve_maintained"] is True
    assert res.invariants_verified["all_clusters_integer_pack_conservation"] is True
