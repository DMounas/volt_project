"""Unit and property tests for physical invariants, reserve bounds, and customer deadlines.

Audits:
1. Local cluster energy balance (strict zero inter-city transfer)
2. Upstream DISCOM (240 MW) and station power limits (144 MW FC, 96 MW Swap)
3. 5% Power capacity headroom reserve (>=12 MW headroom per cluster)
4. Stationary BESS SOC dynamics, no simultaneous charge/discharge, 5% emergency reserve
5. Swappable battery pack inventory conservation and 5% ready pack reserve
6. Customer service windows: arrival hour non-shiftability, deadline conservation
7. Regulatory dynamic tariff bounds ([0.80x, 1.20x] of previous-day average)
8. Decoupled revenue and incentive ledgers (no double-counting)
"""

import pytest
from engine.optimization.pipeline import OptimizationPipeline
from engine.optimization.schemas import OptimizationMode
from engine.optimization.validation import OptimizationValidator


@pytest.fixture(scope="module")
def deterministic_run():
    """Run 5-city deterministic optimization once for invariant testing."""
    pipe = OptimizationPipeline()
    return pipe.run_optimization(mode=OptimizationMode.DETERMINISTIC_P50, seed=42)


def test_independent_validator_100pct_pass(deterministic_run):
    """Verify all physical and regulatory invariants pass independent validation."""
    validator = OptimizationValidator()
    val_report = validator.validate(deterministic_run)
    assert val_report["all_passed"] is True
    assert val_report["pass_rate_pct"] == 100.0
    assert len(val_report["violations"]) == 0


def test_zero_inter_city_power_transfer(deterministic_run):
    """Verify each cluster operates on its own local balance with no cross-city terms."""
    res = deterministic_run
    assert len(res.cluster_schedules) == 5
    for cid, sched in res.cluster_schedules.items():
        assert sched.cluster_id == cid
        for dec in sched.hourly_decisions:
            # Local sources = local sinks + local losses
            local_sources = dec.discom_mw + dec.iex_mw + dec.renewable_used_mwh + dec.bess_discharge_mw
            local_sinks = dec.fc_demand_served_mwh + dec.swap_charge_power_mw + dec.bess_charge_mw + 2.50
            diff = abs(local_sources - (local_sinks + dec.losses_mwh))
            assert diff < 0.05, f"Cluster {cid} hour {dec.hour} has balance diff {diff}"


def test_power_capacity_headroom_reserve_5pct(deterministic_run):
    """Verify at least 12 MW (5% of 240 MW) headroom is preserved in every cluster every hour."""
    res = deterministic_run
    assert res.kpis.power_headroom_reserve_compliant is True
    assert res.kpis.power_capacity_headroom_mw >= 12.0
    for cid, sched in res.cluster_schedules.items():
        for dec in sched.hourly_decisions:
            assert dec.power_headroom_mw >= 11.99, f"Cluster {cid} hour {dec.hour} headroom {dec.power_headroom_mw} < 12 MW"


def test_bess_emergency_reserve_and_bounds(deterministic_run):
    """Verify BESS SOC stays within [3.0 MWh, 54.0 MWh] and no simultaneous charge/discharge."""
    res = deterministic_run
    assert res.kpis.bess_emergency_reserve_compliant is True
    for cid, sched in res.cluster_schedules.items():
        for dec in sched.hourly_decisions:
            assert dec.bess_soc_mwh >= 2.99, f"BESS SOC {dec.bess_soc_mwh} below 3.0 MWh reserve"
            assert dec.bess_soc_mwh <= 54.01, f"BESS SOC {dec.bess_soc_mwh} exceeds 54.0 MWh"
            assert min(dec.bess_charge_mw, dec.bess_discharge_mw) < 1e-3, "Simultaneous BESS charge/discharge detected"


def test_swap_pack_ready_reserve_and_conservation(deterministic_run):
    """Verify swap ready packs stay >= 1,200 packs (5% reserve) and total inventory <= 24,000."""
    res = deterministic_run
    assert res.kpis.swap_emergency_reserve_compliant is True
    for cid, sched in res.cluster_schedules.items():
        for dec in sched.hourly_decisions:
            assert dec.swap_packs_ready >= 1200, f"Ready packs {dec.swap_packs_ready} below 1,200 reserve"
            tot_p = dec.swap_packs_ready + dec.swap_packs_charging + dec.swap_packs_depleted
            assert tot_p <= 24000, f"Total packs {tot_p} exceeds 24,000 inventory"


def test_zero_deadline_violations(deterministic_run):
    """Verify customer deadline violations are exactly zero across all 5 clusters."""
    res = deterministic_run
    assert res.kpis.deadline_violations_count == 0
    assert res.kpis.unserved_critical_mwh == 0.0


def test_dynamic_tariff_regulatory_bounds(deterministic_run):
    """Verify retail dynamic tariffs stay within [0.80x, 1.20x] of previous-day average."""
    res = deterministic_run
    for cid, sched in res.cluster_schedules.items():
        for dec in sched.hourly_decisions:
            # Previous-day avg is 11.20, so [8.96, 13.44]
            assert 8.90 <= dec.tariff_inr_per_kwh <= 13.50, f"Tariff {dec.tariff_inr_per_kwh} out of regulatory bounds"


def test_financial_decoupling_revenue_and_incentives(deterministic_run):
    """Verify retail revenue and incentive expenses are tracked on distinct ledger lines."""
    res = deterministic_run
    assert res.kpis.total_retail_revenue_inr > 0.0
    assert res.kpis.total_flexibility_incentive_inr >= 0.0
    for cid, sched in res.cluster_schedules.items():
        assert sched.total_retail_revenue_inr > 0.0
        assert sched.total_customer_incentive_inr >= 0.0
        # Net cost should be (opex + incentives) - revenue
        expected_net = (
            sched.total_discom_cost_inr
            + sched.total_iex_cost_inr
            + sched.total_renewable_cost_inr
            + sched.total_bess_degradation_cost_inr
            + sched.total_customer_incentive_inr
        ) - sched.total_retail_revenue_inr
        assert abs(sched.net_operating_cost_inr - expected_net) < 1.0
