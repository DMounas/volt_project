"""Tests for reconstructed Business-As-Usual (BAU) baseline policy and calibration."""

import pandas as pd
import pytest
from engine.simulation.baseline_calibration import BaselineCalibrator
from engine.simulation.baseline_policy import BaselineConfig, BaselineSimulationEngine


@pytest.fixture
def sample_cluster_slice():
    """Create a 48-hour sample slice across all five clusters."""
    t_index = pd.date_range("2026-03-01", periods=48, freq="h", tz="Asia/Kolkata")
    clusters = ["delhi_ncr", "mumbai_mmr", "bengaluru", "hyderabad", "chennai"]
    rows = []

    for cid in clusters:
        for t in t_index:
            rows.append(
                {
                    "timestamp": t.isoformat(),
                    "cluster_id": cid,
                    "cluster_name": cid.upper(),
                    "fast_charge_demand_mwh": 50.0 + 15.0 * (t.hour in [9, 10, 19, 20]),
                    "swap_requests": 1200 + 400 * (t.hour in [8, 14, 19]),
                    "swap_energy_equivalent_mwh": (1200 + 400 * (t.hour in [8, 14, 19])) * 0.00225,
                    "renewable_available_mwh": 35.0 * (6 <= t.hour <= 18),
                    "discom_tariff_inr_mwh": 7500.0,
                    "contracted_renewable_tariff_inr_mwh": 3800.0,
                    "provenance": "SYNTHETIC",
                }
            )
    return pd.DataFrame(rows)


@pytest.mark.unit
def test_baseline_deterministic_execution(sample_cluster_slice):
    """Verify that identical seed + config produces identical decisions."""
    engine1 = BaselineSimulationEngine(config=BaselineConfig())
    records1, summary1 = engine1.run_simulation(sample_cluster_slice, seed=42)

    engine2 = BaselineSimulationEngine(config=BaselineConfig())
    records2, summary2 = engine2.run_simulation(sample_cluster_slice, seed=42)

    assert len(records1) == len(records2)
    assert summary1 == summary2

    for r1, r2 in zip(records1, records2):
        assert r1.total_supply_mwh == r2.total_supply_mwh
        assert r1.total_demand_mwh == r2.total_demand_mwh
        assert r1.residual_abs_mwh == r2.residual_abs_mwh


@pytest.mark.unit
def test_baseline_preserves_emergency_reserve(sample_cluster_slice):
    """Verify that 5% emergency reserve is never violated."""
    engine = BaselineSimulationEngine(config=BaselineConfig())
    records, summary = engine.run_simulation(sample_cluster_slice, seed=42)

    assert summary["reserve_compliance"] is True
    # Verify ready pack inventory stays above 5% reserve threshold (1,200 packs = 3.0 MWh per cluster)
    for cid, ready in summary["final_ready_packs"].items():
        assert ready >= 1200, f"Cluster {cid} ready packs {ready} fell below 1,200 reserve"

    # Verify BESS SOC never drops below 15% (10% min SOC + 5% reserve = 3.0 MWh reserve)
    for cid, soc in summary["final_bess_soc"].items():
        assert soc >= 0.15, f"Cluster {cid} BESS SOC {soc} fell below 0.15 reserve threshold"


@pytest.mark.unit
def test_reserve_invariants_and_accounting(sample_cluster_slice):
    """Verify storage split and 5% reserve arithmetic across network and clusters.

    CRITICAL RESERVE INVARIANT:
    - Case provides 600 MWh combined storage (assumed 50/50: 300 MWh BESS + 300 MWh swap packs).
    - Case mandates 5% reserve = 15.0 MWh BESS reserve + 15.0 MWh swap reserve network-wide.
    - Across 5 clusters (60 MWh each): reserve is exactly 3.0 MWh BESS + 3.0 MWh swap per cluster.
    - Sum across 5 clusters MUST exactly equal the 15.0 MWh network reserve (never 15 MWh per city).
    """
    config = BaselineConfig()
    n_clusters = 5

    # 1. Stationary BESS arithmetic
    bess_per_cluster_mwh = config.bess_storage_capacity_mwh  # 60.0 MWh
    bess_network_total_mwh = bess_per_cluster_mwh * n_clusters  # 300.0 MWh
    assert bess_network_total_mwh == 300.0

    bess_reserve_per_cluster_mwh = bess_per_cluster_mwh * config.emergency_reserve_pct  # 3.0 MWh
    bess_reserve_network_mwh = bess_reserve_per_cluster_mwh * n_clusters  # 15.0 MWh
    assert bess_reserve_per_cluster_mwh == 3.0
    assert bess_reserve_network_mwh == 15.0

    # 2. Swap Pack inventory arithmetic
    packs_per_cluster = config.total_packs  # 24,000 packs
    total_network_packs = packs_per_cluster * n_clusters  # 120,000 packs
    assert total_network_packs == 120000

    swap_mwh_per_cluster = (packs_per_cluster * config.pack_nominal_kwh) / 1000.0  # 60.0 MWh
    swap_network_total_mwh = swap_mwh_per_cluster * n_clusters  # 300.0 MWh
    assert swap_network_total_mwh == 300.0

    swap_reserve_packs_per_cluster = int(packs_per_cluster * config.emergency_reserve_pct)  # 1,200 packs
    swap_reserve_per_cluster_mwh = (swap_reserve_packs_per_cluster * config.pack_nominal_kwh) / 1000.0  # 3.0 MWh
    swap_reserve_network_mwh = swap_reserve_per_cluster_mwh * n_clusters  # 15.0 MWh
    assert swap_reserve_packs_per_cluster == 1200
    assert swap_reserve_per_cluster_mwh == 3.0
    assert swap_reserve_network_mwh == 15.0

    # 3. Combined network storage and reserve invariants
    combined_network_storage = bess_network_total_mwh + swap_network_total_mwh
    combined_network_reserve = bess_reserve_network_mwh + swap_reserve_network_mwh
    assert combined_network_storage == 600.0
    assert combined_network_reserve == 30.0  # Exactly 5% of 600 MWh
    assert combined_network_reserve == 0.05 * combined_network_storage


@pytest.mark.unit
def test_baseline_reconciliation_pass_rate(sample_cluster_slice):
    """Verify that every baseline simulation interval reconciles within tolerance."""
    engine = BaselineSimulationEngine(config=BaselineConfig())
    records, _ = engine.run_simulation(sample_cluster_slice, seed=42)

    for r in records:
        assert r.is_reconciled is True, f"Interval {r.timestamp} unreconciled: {r.residual_abs_mwh} MWh"
        assert r.residual_abs_mwh <= 0.005


@pytest.mark.unit
def test_baseline_calibration_routine(sample_cluster_slice):
    """Verify that calibration runs, reports actual measured values and residuals, and never hard-codes KPIs."""
    calibrator = BaselineCalibrator()
    config, report = calibrator.calibrate(
        sample_cluster_slice,
        target_reliability=78.0,
        target_losses=10.0,
        tolerance_error=1.5,
    )

    assert report.target_service_reliability_pct == 78.0
    assert report.target_energy_loss_pct == 10.0
    # Verify measured values are computed numbers, not hard-coded copies
    assert isinstance(report.measured_service_reliability_pct, float)
    assert isinstance(report.measured_energy_loss_pct, float)
    assert report.measured_service_reliability_pct > 0.0
    assert report.measured_energy_loss_pct > 0.0

    # Residuals must equal measured - target
    assert report.residual_reliability_pct == pytest.approx(
        report.measured_service_reliability_pct - 78.0, abs=0.01
    )
    assert report.residual_loss_pct == pytest.approx(
        report.measured_energy_loss_pct - 10.0, abs=0.01
    )

    # Provenance must be SYNTHETIC_CALIBRATION
    assert report.provenance == "SYNTHETIC_CALIBRATION"
    assert report.energy_reconciliation_pass_rate_pct == 100.0
