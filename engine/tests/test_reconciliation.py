"""Tests for energy meter-boundary reconciliation and validation."""

import pytest
from engine.metrics.reconciliation import EnergyBalanceRecord, EnergyReconciliationAuditor


@pytest.fixture
def sample_balanced_record():
    """Create a physically balanced energy record."""
    return EnergyBalanceRecord(
        timestamp="2026-03-01T12:00:00+05:30",
        cluster_id="delhi_ncr",
        renewable_used_mwh=40.0,
        discom_import_mwh=50.0,
        iex_import_mwh=15.0,
        bess_discharge_mwh=5.0,
        # Total supply = 40 + 50 + 15 + 5 = 110.0 MWh
        fast_charge_input_mwh=60.0,
        swap_pack_charge_input_mwh=35.0,
        bess_charge_mwh=10.0,
        auxiliary_load_mwh=3.0,
        distribution_loss_mwh=2.0,
        export_mwh=0.0,
        # Total demand = 60 + 35 + 10 + 3 + 2 = 110.0 MWh
        fast_charge_delivered_mwh=55.5,
        swap_energy_equivalent_delivered_mwh=31.15,
        charger_conversion_loss_mwh=4.5,
        swap_pack_charging_loss_mwh=3.85,
        bess_loss_mwh=0.7,
        renewable_available_mwh=45.0,
        renewable_curtailed_mwh=5.0,
    )


@pytest.mark.unit
def test_energy_balance_exact_reconciliation(sample_balanced_record):
    """Verify that a balanced record computes zero residual and is marked reconciled."""
    rec = sample_balanced_record.compute_balance(tolerance_abs_mwh=0.005)
    assert rec.total_supply_mwh == 110.0
    assert rec.total_demand_mwh == 110.0
    assert rec.residual_abs_mwh == 0.0
    assert rec.residual_pct == 0.0
    assert rec.is_reconciled is True


@pytest.mark.unit
def test_energy_balance_detects_unreconciled_leak():
    """Verify that unaccounted energy is detected as an audit failure."""
    leaky_record = EnergyBalanceRecord(
        timestamp="2026-03-01T13:00:00+05:30",
        cluster_id="mumbai_mmr",
        renewable_used_mwh=30.0,
        discom_import_mwh=70.0,
        iex_import_mwh=0.0,
        bess_discharge_mwh=0.0,
        # Supply = 100.0 MWh
        fast_charge_input_mwh=60.0,
        swap_pack_charge_input_mwh=30.0,
        bess_charge_mwh=0.0,
        auxiliary_load_mwh=2.0,
        distribution_loss_mwh=1.0,
        # Demand = 93.0 MWh -> 7.0 MWh unaccounted leak!
        export_mwh=0.0,
    )

    rec = leaky_record.compute_balance(tolerance_abs_mwh=0.005)
    assert rec.total_supply_mwh == 100.0
    assert rec.total_demand_mwh == 93.0
    assert rec.residual_abs_mwh == 7.0
    assert rec.is_reconciled is False


@pytest.mark.unit
def test_no_double_counting_rule(sample_balanced_record):
    """Verify mandatory no-double-counting rule between swap delivery and pack recharge."""
    auditor = EnergyReconciliationAuditor()
    report = auditor.audit_run([sample_balanced_record])

    acc = report["energy_accounting_mwh"]
    # Customer delivered energy equivalent includes swap usable energy
    assert acc["customer_swap_energy_equivalent_delivered"] == 31.15
    # Total served equivalent does NOT double count the electrical recharging load
    assert acc["total_served_energy_equivalent"] == round(55.5 + 31.15, 2)
    # The electrical pack recharge (35.0 MWh) is part of gross electrical input/demand
    assert acc["gross_energy_consumed"] == 110.0
    assert "PASSED" in report["no_double_counting_audit"]
