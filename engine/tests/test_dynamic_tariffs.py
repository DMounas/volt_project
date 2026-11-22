"""Unit tests for DynamicTariffPolicy."""

from datetime import datetime, timezone
import pytest

from engine.customer.models import ServiceType
from engine.customer.tariffs import DynamicTariffPolicy


@pytest.fixture
def policy():
    return DynamicTariffPolicy()


def test_tariff_upper_bound_clamping(policy):
    ts = datetime(2025, 6, 15, 18, 0, tzinfo=timezone.utc)
    prev_avg = 10.00
    # Extremely high procurement cost will drive raw tariff up
    rec = policy.evaluate_tariff(
        cluster_id="delhi_ncr",
        service_type=ServiceType.FAST_CHARGE,
        timestamp=ts,
        previous_day_average_tariff_inr_per_kwh=prev_avg,
        forecast_procurement_cost_inr_per_kwh=15.00,
        forecast_demand_mw=230.0,
        available_capacity_mw=240.0,
    )

    assert rec.tariff_min_inr_per_kwh == 8.00
    assert rec.tariff_max_inr_per_kwh == 12.00
    assert rec.raw_tariff_inr_per_kwh > 12.00
    assert rec.final_tariff_inr_per_kwh == 12.00
    assert rec.clamped is True
    assert rec.clamping_direction == "UPPER_BOUND"
    assert any("exceeded regulatory ceiling" in r for r in rec.adjustment_reasons)


def test_tariff_lower_bound_clamping(policy):
    ts = datetime(2025, 6, 15, 13, 0, tzinfo=timezone.utc)
    prev_avg = 10.00
    # Plentiful solar surplus and low procurement cost will drive raw tariff down
    rec = policy.evaluate_tariff(
        cluster_id="bengaluru",
        service_type=ServiceType.FAST_CHARGE,
        timestamp=ts,
        previous_day_average_tariff_inr_per_kwh=prev_avg,
        forecast_procurement_cost_inr_per_kwh=1.00,
        forecast_demand_mw=50.0,
        available_capacity_mw=240.0,
        forecast_solar_surplus_mw=50.0,
    )

    assert rec.tariff_min_inr_per_kwh == 8.00
    assert rec.tariff_max_inr_per_kwh == 12.00
    assert rec.raw_tariff_inr_per_kwh < 8.00
    assert rec.final_tariff_inr_per_kwh == 8.00
    assert rec.clamped is True
    assert rec.clamping_direction == "LOWER_BOUND"
    assert any("fell below regulatory floor" in r for r in rec.adjustment_reasons)


def test_tariff_within_bounds_unclamped(policy):
    ts = datetime(2025, 6, 15, 10, 0, tzinfo=timezone.utc)
    prev_avg = 10.00
    rec = policy.evaluate_tariff(
        cluster_id="mumbai_mmr",
        service_type=ServiceType.FAST_CHARGE,
        timestamp=ts,
        previous_day_average_tariff_inr_per_kwh=prev_avg,
        forecast_procurement_cost_inr_per_kwh=5.20,
    )

    assert rec.tariff_min_inr_per_kwh == 8.00
    assert rec.tariff_max_inr_per_kwh == 12.00
    assert rec.raw_tariff_inr_per_kwh == 10.00
    assert rec.final_tariff_inr_per_kwh == 10.00
    assert rec.clamped is False
    assert rec.clamping_direction == "NONE"


def test_zero_or_negative_previous_day_avg_rejected(policy):
    ts = datetime(2025, 6, 15, 10, 0, tzinfo=timezone.utc)
    with pytest.raises(ValueError):
        policy.evaluate_tariff(
            cluster_id="delhi_ncr",
            service_type=ServiceType.FAST_CHARGE,
            timestamp=ts,
            previous_day_average_tariff_inr_per_kwh=0.0,
        )
    with pytest.raises(ValueError):
        policy.evaluate_tariff(
            cluster_id="delhi_ncr",
            service_type=ServiceType.FAST_CHARGE,
            timestamp=ts,
            previous_day_average_tariff_inr_per_kwh=-5.0,
        )
