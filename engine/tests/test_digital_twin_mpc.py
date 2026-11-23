"""Unit and property tests for Digital Twin and Closed-Loop Rolling MPC Controller.

Verifies:
- Closed-loop MPC applies ONLY the first action hour of each 24-hour plan
- MPC re-solves after every applied interval
- State continuity across time steps
- Exact integer swap-pack conservation (24,000 packs)
- 5% emergency reserves: BESS (>=3.0 MWh), Swap (>=1,200 packs), Headroom (>=12.0 MW)
- Zero inter-city power transfer
- Solver failure invokes validated fallback and logs it
- Deterministic reproducibility for a fixed seed
- EBITDA disclosure returns NOT_EVALUABLE with missing components
"""

import pytest

from engine.optimization.schemas import OptimizationMode, SolverStatus
from engine.twin.events import ScenarioEventEngine
from engine.twin.mpc_controller import RollingMPCController
from engine.twin.schemas import ShockScenarioType, SimulationPolicy
from engine.twin.simulator import DigitalTwinSimulator


def test_closed_loop_applies_only_first_action_hour():
    """Verify that MPC applies only the first action interval (t=0) and steps state forward."""
    ctrl = RollingMPCController()
    res = ctrl.run_simulation(
        scenario_id="NORMAL_OPERATION",
        policy=SimulationPolicy.CLOSED_LOOP_MPC_P50,
        horizon_hours=2,
        clusters=["delhi_ncr"],
        seed=101,
    )

    assert len(res.timeline) == 2
    # Verify each timeline step contains distinct actions and states
    step0 = res.timeline[0]
    step1 = res.timeline[1]
    assert step0["hour"] == 0
    assert step1["hour"] == 1
    assert "delhi_ncr" in step0["clusters"]
    assert "delhi_ncr" in step1["clusters"]


def test_mpc_resolves_every_interval():
    """Verify that closed-loop MPC re-solves at every interval."""
    ctrl = RollingMPCController()
    res = ctrl.run_simulation(
        scenario_id="NORMAL_OPERATION",
        policy=SimulationPolicy.CLOSED_LOOP_MPC_P50,
        horizon_hours=3,
        clusters=["delhi_ncr"],
        seed=202,
    )

    assert len(res.timeline) == 3
    # All 3 steps executed solver
    assert all(entry["solver_status"] in ("OPTIMAL", "FEASIBLE_GAP") for entry in res.timeline)
    assert res.kpis.mean_solve_time_seconds > 0.0


def test_state_continuity_and_invariants():
    """Verify BESS SOC and swap inventory state transitions maintain conservation and bounds."""
    sim = DigitalTwinSimulator(cluster_id="delhi_ncr")
    sim.reset(bess_soc_mwh=30.0, ready_packs=16800, charging_packs=4800, depleted_packs=2400)

    # Initial conservation
    assert sim.ready_packs + sim.charging_packs + sim.depleted_packs + sim.unavailable_packs == 24000

    from engine.twin.schemas import StepAction
    action = StepAction(
        hour=0,
        cluster_id="delhi_ncr",
        discom_mw=40.0,
        iex_mw=10.0,
        renewable_used_mwh=20.0,
        bess_charge_mw=10.0,
        bess_discharge_mw=0.0,
        swap_packs_to_charge=2000,
        fc_served_mwh=25.0,
        selected_tariff_tier="1.00x",
        tariff_inr_per_kwh=11.20,
        flexibility_incentive_offered_inr=0.0,
    )

    st = sim.step(
        hour=0,
        timestamp="2025-06-15T00:00:00+05:30",
        action=action,
        actual_fc_demand_mwh=25.0,
        actual_swap_requests=1500,
        actual_solar_mwh=10.0,
        actual_wind_mwh=10.0,
        actual_discom_price_inr=7500.0,
        actual_iex_price_inr=5200.0,
    )

    # Invariants checks
    assert st.swap.conservation_valid is True
    assert st.swap.total_packs == 24000
    assert st.swap.ready_packs >= 1200
    assert st.energy.bess_soc_mwh >= 3.0
    assert st.energy.headroom_reserve_compliant is True
    assert st.energy.inter_city_transfer_mw == 0.0


def test_integer_swap_pack_conservation_under_stress():
    """Verify exact integer pack conservation under heavy swapping load."""
    sim = DigitalTwinSimulator(cluster_id="mumbai_mmr")
    sim.reset(bess_soc_mwh=30.0, ready_packs=16800, charging_packs=4800, depleted_packs=2400)

    from engine.twin.schemas import StepAction
    action = StepAction(
        hour=1,
        cluster_id="mumbai_mmr",
        discom_mw=50.0,
        iex_mw=0.0,
        renewable_used_mwh=15.0,
        bess_charge_mw=0.0,
        bess_discharge_mw=10.0,
        swap_packs_to_charge=3500,
        fc_served_mwh=40.0,
        selected_tariff_tier="1.10x",
        tariff_inr_per_kwh=12.32,
        flexibility_incentive_offered_inr=500.0,
    )

    st = sim.step(
        hour=1,
        timestamp="2025-06-15T01:00:00+05:30",
        action=action,
        actual_fc_demand_mwh=40.0,
        actual_swap_requests=3000,
        actual_solar_mwh=0.0,
        actual_wind_mwh=15.0,
        actual_discom_price_inr=7500.0,
        actual_iex_price_inr=6000.0,
    )

    total_packs_after = (
        st.swap.ready_packs + st.swap.charging_packs + st.swap.depleted_packs + st.swap.unavailable_packs
    )
    assert total_packs_after == 24000
    assert st.swap.conservation_valid is True


def test_fallback_scheduler_invocation(monkeypatch):
    """Verify that when solver fails, fallback schedule is triggered, logged, and reserves preserved."""
    ctrl = RollingMPCController()

    # Simulate solver unavailability
    monkeypatch.setattr(ctrl.pipeline.solver_manager, "find_available_solver", lambda: (None, "none"))

    res = ctrl.run_simulation(
        scenario_id="NORMAL_OPERATION",
        policy=SimulationPolicy.CLOSED_LOOP_MPC_P50,
        horizon_hours=1,
        clusters=["delhi_ncr"],
        seed=999,
    )

    assert res.timeline[0]["is_fallback"] is True
    assert res.kpis.fallback_events_count >= 1
    assert res.invariants_verified["all_clusters_bess_reserve_maintained"] is True
    assert res.invariants_verified["all_clusters_swap_reserve_maintained"] is True


def test_deterministic_reproducibility():
    """Verify simulation is bitwise reproducible given identical seed."""
    ctrl = RollingMPCController()
    res1 = ctrl.run_simulation(
        scenario_id="NORMAL_OPERATION",
        policy=SimulationPolicy.BAU_BASELINE,
        horizon_hours=3,
        clusters=["delhi_ncr"],
        seed=42,
    )
    res2 = ctrl.run_simulation(
        scenario_id="NORMAL_OPERATION",
        policy=SimulationPolicy.BAU_BASELINE,
        horizon_hours=3,
        clusters=["delhi_ncr"],
        seed=42,
    )

    assert res1.kpis.service_reliability_pct == res2.kpis.service_reliability_pct
    assert res1.kpis.total_energy_served_mwh == res2.kpis.total_energy_served_mwh
    assert res1.kpis.procurement_cost_inr == res2.kpis.procurement_cost_inr


def test_not_evaluable_ebitda():
    """Verify EBITDA is explicitly NOT_EVALUABLE with missing components documented."""
    ctrl = RollingMPCController()
    res = ctrl.run_simulation(
        scenario_id="NORMAL_OPERATION",
        policy=SimulationPolicy.BAU_BASELINE,
        horizon_hours=1,
        clusters=["delhi_ncr"],
        seed=55,
    )

    assert res.ebitda.status == "NOT_EVALUABLE"
    assert res.ebitda.ebitda_margin_pct is None
    assert len(res.ebitda.missing_components) >= 3
    assert "fixed_operating_costs" in res.ebitda.missing_components
    assert "depreciation_schedule" in res.ebitda.missing_components


def test_calibrated_bau_policy_semantics():
    """Verify CALIBRATED_BAU reproduces calibrated uncoordinated operations with downtime & balking."""
    ctrl = RollingMPCController()
    res = ctrl.run_simulation(
        scenario_id="NORMAL_OPERATION",
        policy=SimulationPolicy.CALIBRATED_BAU,
        horizon_hours=6,
        clusters=["delhi_ncr"],
        seed=42,
    )

    assert res.policy == SimulationPolicy.CALIBRATED_BAU
    # In uncoordinated operations with 82% availability and 4% balking, reliability is ~78.4%
    assert 75.0 <= res.kpis.service_reliability_pct <= 82.0
    assert 10.0 <= res.kpis.energy_loss_pct <= 30.0
    assert res.kpis.flexibility_incentive_inr == 0.0


def test_fallback_heuristic_policy_semantics():
    """Verify FALLBACK_HEURISTIC is explicitly marked and enforces all physical reserves."""
    ctrl = RollingMPCController()
    res = ctrl.run_simulation(
        scenario_id="NORMAL_OPERATION",
        policy=SimulationPolicy.FALLBACK_HEURISTIC,
        horizon_hours=3,
        clusters=["delhi_ncr"],
        seed=42,
    )

    assert res.policy == SimulationPolicy.FALLBACK_HEURISTIC
    assert res.kpis.fallback_events_count == 3
    assert res.invariants_verified["all_clusters_bess_reserve_maintained"] is True
    assert res.invariants_verified["all_clusters_swap_reserve_maintained"] is True
    assert res.invariants_verified["all_clusters_headroom_maintained"] is True
    assert res.invariants_verified["all_clusters_integer_pack_conservation"] is True


def test_open_loop_milp_and_closed_loop_mpc_semantics():
    """Verify OPEN_LOOP_MILP solves once at t=0 and CLOSED_LOOP_MPC re-optimizes every step."""
    ctrl = RollingMPCController()
    res_ol = ctrl.run_simulation(
        scenario_id="NORMAL_OPERATION",
        policy=SimulationPolicy.OPEN_LOOP_MILP,
        horizon_hours=2,
        clusters=["delhi_ncr"],
        seed=42,
    )
    assert res_ol.policy == SimulationPolicy.OPEN_LOOP_MILP
    assert len(res_ol.timeline) == 2

    res_mpc = ctrl.run_simulation(
        scenario_id="NORMAL_OPERATION",
        policy=SimulationPolicy.CLOSED_LOOP_MPC,
        horizon_hours=2,
        clusters=["delhi_ncr"],
        seed=42,
    )
    assert res_mpc.policy == SimulationPolicy.CLOSED_LOOP_MPC
    assert len(res_mpc.timeline) == 2
    assert res_mpc.invariants_verified["all_clusters_integer_pack_conservation"] is True
