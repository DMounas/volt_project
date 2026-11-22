"""Unit tests for FlexibilityEnvelopeEngine."""

from datetime import datetime, timedelta, timezone
import pytest

from engine.customer.envelope import FlexibilityEnvelopeEngine
from engine.customer.models import (
    CustomerSegment,
    CustomerServiceRequest,
    FlexibilityReasonCode,
    ServiceType,
)

IST = timezone(timedelta(hours=5, minutes=30))


@pytest.fixture
def engine():
    return FlexibilityEnvelopeEngine()


def test_emergency_never_shiftable(engine):
    arrival = datetime(2025, 6, 15, 12, 0, tzinfo=IST)
    deadline = arrival + timedelta(hours=3)

    req = CustomerServiceRequest(
        request_id="REQ-EMG-TEST",
        cluster_id="delhi_ncr",
        request_type=ServiceType.FAST_CHARGE,
        customer_segment=CustomerSegment.EMERGENCY,
        arrival_ts=arrival,
        departure_deadline_ts=deadline,
        requested_energy_kwh=45.0,
        minimum_service_energy_kwh=45.0,
        max_wait_minutes=0.0,
        max_deferral_minutes=0.0,
        flexibility_opt_in=False,
        baseline_tariff_inr_per_kwh=11.50,
        previous_day_avg_tariff_inr_per_kwh=11.20,
    )

    env = engine.compute_envelope(req)
    assert env.is_deferrable is False
    assert env.flexible_energy_kwh == 0.0
    assert env.non_shiftable_energy_kwh == 45.0
    assert env.reason_code == FlexibilityReasonCode.EMERGENCY_NON_SHIFTABLE


def test_priority_fleet_never_shiftable(engine):
    arrival = datetime(2025, 6, 15, 8, 0, tzinfo=IST)
    deadline = arrival + timedelta(hours=2)

    req = CustomerServiceRequest(
        request_id="REQ-PRI-TEST",
        cluster_id="mumbai_mmr",
        request_type=ServiceType.FAST_CHARGE,
        customer_segment=CustomerSegment.PRIORITY_FLEET,
        arrival_ts=arrival,
        departure_deadline_ts=deadline,
        requested_energy_kwh=30.0,
        minimum_service_energy_kwh=30.0,
        max_wait_minutes=15.0,
        max_deferral_minutes=0.0,
        flexibility_opt_in=False,
        baseline_tariff_inr_per_kwh=11.50,
        previous_day_avg_tariff_inr_per_kwh=11.20,
    )

    env = engine.compute_envelope(req)
    assert env.is_deferrable is False
    assert env.flexible_energy_kwh == 0.0
    assert env.non_shiftable_energy_kwh == 30.0
    assert env.reason_code == FlexibilityReasonCode.PRIORITY_RESERVE_NON_SHIFTABLE


def test_non_opted_in_rejected(engine):
    arrival = datetime(2025, 6, 15, 9, 0, tzinfo=IST)
    deadline = arrival + timedelta(hours=3)

    req = CustomerServiceRequest(
        request_id="REQ-OPT-TEST",
        cluster_id="bengaluru",
        request_type=ServiceType.FAST_CHARGE,
        customer_segment=CustomerSegment.LOGISTICS_FLEET,
        arrival_ts=arrival,
        departure_deadline_ts=deadline,
        requested_energy_kwh=40.0,
        minimum_service_energy_kwh=10.0,
        max_wait_minutes=60.0,
        max_deferral_minutes=120.0,
        flexibility_opt_in=False,  # Not opted in
        baseline_tariff_inr_per_kwh=11.50,
        previous_day_avg_tariff_inr_per_kwh=11.20,
    )

    env = engine.compute_envelope(req)
    assert env.is_deferrable is False
    assert env.flexible_energy_kwh == 0.0
    assert env.non_shiftable_energy_kwh == 40.0
    assert env.reason_code == FlexibilityReasonCode.NOT_OPTED_IN


def test_fast_charge_conservation_and_partial_flexibility(engine):
    arrival = datetime(2025, 6, 15, 10, 0, tzinfo=IST)
    deadline = arrival + timedelta(hours=3)

    req = CustomerServiceRequest(
        request_id="REQ-FC-TEST",
        cluster_id="delhi_ncr",
        request_type=ServiceType.FAST_CHARGE,
        customer_segment=CustomerSegment.RIDE_HAILING,  # 40% flexible fraction
        arrival_ts=arrival,
        departure_deadline_ts=deadline,
        requested_energy_kwh=50.0,
        minimum_service_energy_kwh=20.0,
        max_wait_minutes=30.0,
        max_deferral_minutes=60.0,
        flexibility_opt_in=True,
        baseline_tariff_inr_per_kwh=11.50,
        previous_day_avg_tariff_inr_per_kwh=11.20,
    )

    env = engine.compute_envelope(req)
    assert env.is_deferrable is True
    # Energy conservation
    assert abs(env.requested_energy_kwh - (env.non_shiftable_energy_kwh + env.flexible_energy_kwh)) < 1e-5
    # 40% of 50.0 is 20.0 flexible kWh
    assert env.flexible_energy_kwh == 20.0
    assert env.non_shiftable_energy_kwh == 30.0
    assert env.reason_code == FlexibilityReasonCode.PARTIALLY_FLEXIBLE
    # Slots must span up to deadline hour
    assert len(env.eligible_time_slots) >= 2


def test_battery_swap_discrete_integer_packs(engine):
    arrival = datetime(2025, 6, 15, 11, 0, tzinfo=IST)
    deadline = arrival + timedelta(hours=2)

    req = CustomerServiceRequest(
        request_id="REQ-SWP-INT",
        cluster_id="hyderabad",
        request_type=ServiceType.BATTERY_SWAP,
        customer_segment=CustomerSegment.LOGISTICS_FLEET,  # 70% flexible
        arrival_ts=arrival,
        departure_deadline_ts=deadline,
        requested_pack_count=3,
        minimum_pack_count=1,
        pack_capacity_kwh=2.5,
        max_wait_minutes=60.0,
        max_deferral_minutes=90.0,
        flexibility_opt_in=True,
        baseline_tariff_inr_per_kwh=11.50,
        previous_day_avg_tariff_inr_per_kwh=11.20,
    )

    env = engine.compute_envelope(req)
    assert env.is_deferrable is True
    # Packs must be strictly integer
    assert isinstance(env.flexible_pack_count, int)
    assert isinstance(env.non_shiftable_pack_count, int)
    assert env.requested_pack_count == env.flexible_pack_count + env.non_shiftable_pack_count
    # floor(3 * 0.70) = 2 packs flexible
    assert env.flexible_pack_count == 2
    assert env.non_shiftable_pack_count == 1
    # Energy equivalent matches packs * capacity
    assert env.flexible_energy_kwh == 2 * 2.5
    assert env.non_shiftable_energy_kwh == 1 * 2.5
    assert env.requested_energy_kwh == 3 * 2.5


def test_deadline_constrained_zero_slack(engine):
    arrival = datetime(2025, 6, 15, 10, 0, tzinfo=IST)
    # Normal charging duration for 50 kWh @ 50 kW is 60 minutes
    # If deadline is 60 mins from arrival, available slack is 0
    deadline = arrival + timedelta(minutes=60)

    req = CustomerServiceRequest(
        request_id="REQ-TIGHT",
        cluster_id="chennai",
        request_type=ServiceType.FAST_CHARGE,
        customer_segment=CustomerSegment.PRIVATE_EV,
        arrival_ts=arrival,
        departure_deadline_ts=deadline,
        requested_energy_kwh=50.0,
        minimum_service_energy_kwh=20.0,
        max_wait_minutes=15.0,
        max_deferral_minutes=60.0,
        flexibility_opt_in=True,
        baseline_tariff_inr_per_kwh=11.50,
        previous_day_avg_tariff_inr_per_kwh=11.20,
    )

    env = engine.compute_envelope(req)
    assert env.is_deferrable is False
    assert env.flexible_energy_kwh == 0.0
    assert env.reason_code == FlexibilityReasonCode.DEADLINE_CONSTRAINED
