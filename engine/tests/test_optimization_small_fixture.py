"""Hand-solvable 1-city, 2-hour tiny fixture test verifying exact analytical solution.

Analytical Benchmark:
- Fast charge demand: 10.0 MWh requested at t=0 with deadline t=1.
- Non-shiftable minimum: 2.0 MWh (must be served at t=0).
- Flexible shiftable: 8.0 MWh (can be shifted to t=1).
- Electricity price: Hour 0 = 8,500 INR/MWh (peak), Hour 1 = 4,200 INR/MWh (off-peak).
- Analytical decision:
  * Optimal policy MUST schedule exactly 2.0 MWh at t=0 (non-shiftable)
  * Optimal policy MUST shift 8.0 MWh to t=1 (off-peak economic arbitrage)
  * Avoided procurement cost = 8.0 * (8,500 - 4,200) = 34,400 INR gross saving.
"""

import pytest
import pyomo.environ as pyo

from engine.customer.models import CustomerSegment, ServiceType
from engine.optimization.cohorts import ServiceCohort
from engine.optimization.model_builder import ModelBuilder
from engine.optimization.objective import ObjectiveBuilder
from engine.optimization.schemas import (
    BESSInitialState,
    ClusterHorizonInput,
    OptimizationMode,
    ScenarioWeight,
    SolverStatus,
    SwapInitialState,
)
from engine.optimization.solver import SolverManager


@pytest.fixture
def tiny_fixture():
    """Create minimal 1-city, 2-hour inputs."""
    cluster_id = "delhi_ncr"
    horizon = [0, 1]

    cohort = ServiceCohort(
        cohort_id="COHORT-TINY-001",
        cluster_id=cluster_id,
        modality=ServiceType.FAST_CHARGE,
        segment=CustomerSegment.LOGISTICS_FLEET,
        arrival_hour=0,
        deadline_hour=1,
        flexibility_opt_in=True,
        total_energy_mwh=10.0,
        non_shiftable_mwh=2.0,
        flexible_mwh=8.0,
        requests_count=5,
    )

    c_input = ClusterHorizonInput(
        cluster_id=cluster_id,
        hours=horizon,
        fast_charge_demand_mwh=[10.0, 0.0],
        swap_requests_count=[0, 0],
        swap_energy_mwh=[0.0, 0.0],
        solar_available_mwh=[0.0, 0.0],
        wind_available_mwh=[0.0, 0.0],
        discom_tariff_inr_per_mwh=[8500.0, 4200.0],  # Hour 0 peak, Hour 1 off-peak
        iex_dam_price_inr_per_mwh=[8500.0, 4200.0],
        iex_procurement_cap_mw=[0.0, 0.0],
        previous_day_avg_tariff_inr_per_kwh=11.20,
        bess_state=BESSInitialState(capacity_mwh=60.0, initial_soc_mwh=3.0, min_reserve_mwh=3.0),
        swap_state=SwapInitialState(ready_packs=1200, min_reserve_packs=1200),
    )

    scenario = ScenarioWeight(scenario_id="NORMAL", probability=1.0)

    return {
        "cluster_id": cluster_id,
        "horizon": horizon,
        "cohorts": [cohort],
        "cluster_inputs": {cluster_id: c_input},
        "scenarios": [scenario],
    }


def test_tiny_fixture_analytical_solution(tiny_fixture):
    """Verify that Pyomo MILP solves tiny model and produces exact analytical arbitrage."""
    data = tiny_fixture

    builder = ModelBuilder(
        clusters=[data["cluster_id"]],
        horizon=data["horizon"],
        scenarios=data["scenarios"],
        cohorts=data["cohorts"],
        cluster_inputs=data["cluster_inputs"],
        aux_station_load_mw=0.0,
        distribution_loss_factor=0.0,
    )
    model = builder.build()

    obj_builder = ObjectiveBuilder()
    obj_builder.attach_objective(
        model=model,
        scenarios=["NORMAL"],
        probabilities={"NORMAL": 1.0},
        clusters=[data["cluster_id"]],
        horizon=data["horizon"],
        cohorts=data["cohorts"],
        is_risk_aware=False,
    )

    solver_mgr = SolverManager(time_limit_seconds=15.0)
    success, meta = solver_mgr.solve(model)

    assert success is True
    assert meta.solver_status == SolverStatus.OPTIMAL

    # Check decisions
    c = data["cluster_id"]
    e_served_h0 = pyo.value(model.e_cohort_served["COHORT-TINY-001", 0, "NORMAL"])
    e_served_h1 = pyo.value(model.e_cohort_served["COHORT-TINY-001", 1, "NORMAL"])

    # Non-shiftable 2.0 MWh served at Hour 0
    assert abs(e_served_h0 - 2.0) < 1e-3, f"Expected 2.0 MWh in Hour 0, got {e_served_h0}"

    # Flexible 8.0 MWh shifted to Hour 1 (cheaper price)
    assert abs(e_served_h1 - 8.0) < 1e-3, f"Expected 8.0 MWh in Hour 1, got {e_served_h1}"

    # Total served must be 10.0 MWh with 0 slack
    assert abs((e_served_h0 + e_served_h1) - 10.0) < 1e-3
    assert pyo.value(model.u_slack_crit["COHORT-TINY-001", "NORMAL"]) < 1e-4
    assert pyo.value(model.u_slack_flex["COHORT-TINY-001", "NORMAL"]) < 1e-4
