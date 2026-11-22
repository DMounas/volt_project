"""Unit tests for synthetic request disaggregation and reconciliation."""

import pandas as pd
import pytest

from engine.customer.models import CustomerSegment, ServiceType
from engine.customer.synthetic_requests import SyntheticRequestDisaggregator


@pytest.fixture
def sample_hourly_data():
    """Create a minimal 2-hour synthetic DataFrame for Delhi NCR and Mumbai MMR."""
    data = [
        {
            "timestamp": "2025-06-15T10:00:00+05:30",
            "cluster_id": "delhi_ncr",
            "fast_charge_requests": 20,
            "fast_charge_demand_mwh": 0.600,  # 600 kWh
            "swap_requests": 15,
            "swap_energy_equivalent_mwh": 0.050,  # 50 kWh = 20 packs @ 2.5 kWh
        },
        {
            "timestamp": "2025-06-15T11:00:00+05:30",
            "cluster_id": "delhi_ncr",
            "fast_charge_requests": 25,
            "fast_charge_demand_mwh": 0.750,  # 750 kWh
            "swap_requests": 18,
            "swap_energy_equivalent_mwh": 0.060,  # 60 kWh = 24 packs @ 2.5 kWh
        },
    ]
    return pd.DataFrame(data)


def test_fast_charge_exact_reconciliation(sample_hourly_data):
    disaggregator = SyntheticRequestDisaggregator(seed=42)
    requests, recon_df = disaggregator.disaggregate_hourly_demand(
        sample_hourly_data, demo_mode=False
    )

    fc_recon = recon_df[recon_df["modality"] == "FAST_CHARGE"]
    assert len(fc_recon) == 2
    for _, row in fc_recon.iterrows():
        assert row["reconciled"] is True
        assert row["error_pct"] < 0.01

    fc_reqs = [r for r in requests if r.request_type == ServiceType.FAST_CHARGE]
    assert len(fc_reqs) == 45  # 20 + 25

    # Sum of energy across all requests
    total_energy_kwh = sum(r.requested_energy_kwh for r in fc_reqs)
    expected_kwh = (0.600 + 0.750) * 1000.0
    assert abs(total_energy_kwh - expected_kwh) < 0.01


def test_swap_discrete_integer_packs(sample_hourly_data):
    disaggregator = SyntheticRequestDisaggregator(seed=42, pack_capacity_kwh=2.5)
    requests, recon_df = disaggregator.disaggregate_hourly_demand(
        sample_hourly_data, demo_mode=False
    )

    swap_reqs = [r for r in requests if r.request_type == ServiceType.BATTERY_SWAP]
    assert len(swap_reqs) == 33  # 15 + 18

    # All pack counts must be discrete integers
    for req in swap_reqs:
        assert isinstance(req.requested_pack_count, int)
        assert req.requested_pack_count in (1, 2, 3)
        assert req.minimum_pack_count <= req.requested_pack_count

    swap_recon = recon_df[recon_df["modality"] == "BATTERY_SWAP"]
    assert len(swap_recon) == 2
    for _, row in swap_recon.iterrows():
        assert row["reconciled"] is True


def test_disaggregation_determinism(sample_hourly_data):
    d1 = SyntheticRequestDisaggregator(seed=123)
    d2 = SyntheticRequestDisaggregator(seed=123)
    d3 = SyntheticRequestDisaggregator(seed=999)

    r1, _ = d1.disaggregate_hourly_demand(sample_hourly_data, demo_mode=False)
    r2, _ = d2.disaggregate_hourly_demand(sample_hourly_data, demo_mode=False)
    r3, _ = d3.disaggregate_hourly_demand(sample_hourly_data, demo_mode=False)

    assert len(r1) == len(r2)
    for i in range(len(r1)):
        assert r1[i].requested_energy_kwh == r2[i].requested_energy_kwh
        assert r1[i].customer_segment == r2[i].customer_segment
        assert r1[i].flexibility_opt_in == r2[i].flexibility_opt_in

    # Different seed produces different allocation
    different = any(r1[i].requested_energy_kwh != r3[i].requested_energy_kwh for i in range(len(r1)))
    assert different is True
