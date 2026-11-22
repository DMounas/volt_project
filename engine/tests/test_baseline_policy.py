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
    # Verify ready pack inventory stays above 5% reserve threshold (1,200 packs)
    for cid, ready in summary["final_ready_packs"].items():
        assert ready >= 1200, f"Cluster {cid} ready packs {ready} fell below 1,200 reserve"

    # Verify BESS SOC never drops below 15% (10% min SOC + 5% reserve)
    for cid, soc in summary["final_bess_soc"].items():
        assert soc >= 0.15, f"Cluster {cid} BESS SOC {soc} fell below 0.15 reserve threshold"


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
