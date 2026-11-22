"""Unit tests for customer request and flexibility data models."""

from datetime import datetime, timedelta, timezone
import pytest
from pydantic import ValidationError

from engine.customer.models import (
    CustomerSegment,
    CustomerServiceRequest,
    FlexibilityEnvelope,
    FlexibilityReasonCode,
    ServiceType,
    TariffRecommendation,
)

IST = timezone(timedelta(hours=5, minutes=30))


def test_valid_fast_charge_request():
    arrival = datetime(2025, 6, 15, 10, 0, tzinfo=IST)
    deadline = arrival + timedelta(minutes=45)

    req = CustomerServiceRequest(
        request_id="REQ-DEL-0001",
        cluster_id="delhi_ncr",
        request_type=ServiceType.FAST_CHARGE,
        customer_segment=CustomerSegment.RIDE_HAILING,
        arrival_ts=arrival,
        departure_deadline_ts=deadline,
        requested_energy_kwh=32.5,
        minimum_service_energy_kwh=20.0,
        max_wait_minutes=30.0,
        max_deferral_minutes=60.0,
        flexibility_opt_in=True,
        baseline_tariff_inr_per_kwh=11.50,
        previous_day_avg_tariff_inr_per_kwh=11.20,
    )

    assert req.request_id == "REQ-DEL-0001"
    assert req.requested_energy_kwh == 32.5
    assert req.minimum_service_energy_kwh == 20.0
    assert req.flexibility_opt_in is True


def test_valid_battery_swap_request():
    arrival = datetime(2025, 6, 15, 14, 0, tzinfo=IST)
    deadline = arrival + timedelta(minutes=15)

    req = CustomerServiceRequest(
        request_id="REQ-MUM-0002",
        cluster_id="mumbai_mmr",
        request_type=ServiceType.BATTERY_SWAP,
        customer_segment=CustomerSegment.LOGISTICS_FLEET,
        arrival_ts=arrival,
        departure_deadline_ts=deadline,
        requested_pack_count=2,
        minimum_pack_count=1,
        pack_capacity_kwh=2.5,
        max_wait_minutes=20.0,
        max_deferral_minutes=30.0,
        flexibility_opt_in=True,
        baseline_tariff_inr_per_kwh=12.00,
        previous_day_avg_tariff_inr_per_kwh=11.50,
    )

    assert req.requested_pack_count == 2
    assert req.minimum_pack_count == 1
    assert req.pack_capacity_kwh == 2.5


def test_deadline_before_arrival_rejected():
    arrival = datetime(2025, 6, 15, 10, 0, tzinfo=IST)
    deadline = arrival - timedelta(minutes=10)

    with pytest.raises(ValidationError) as exc:
        CustomerServiceRequest(
            request_id="REQ-FAIL-01",
            cluster_id="delhi_ncr",
            request_type=ServiceType.FAST_CHARGE,
            customer_segment=CustomerSegment.PRIVATE_EV,
            arrival_ts=arrival,
            departure_deadline_ts=deadline,
            requested_energy_kwh=25.0,
            minimum_service_energy_kwh=15.0,
            baseline_tariff_inr_per_kwh=11.50,
            previous_day_avg_tariff_inr_per_kwh=11.20,
        )
    assert "Departure deadline" in str(exc.value)


def test_negative_energy_rejected():
    arrival = datetime(2025, 6, 15, 10, 0, tzinfo=IST)
    deadline = arrival + timedelta(minutes=30)

    with pytest.raises(ValidationError):
        CustomerServiceRequest(
            request_id="REQ-FAIL-02",
            cluster_id="delhi_ncr",
            request_type=ServiceType.FAST_CHARGE,
            customer_segment=CustomerSegment.PRIVATE_EV,
            arrival_ts=arrival,
            departure_deadline_ts=deadline,
            requested_energy_kwh=-10.0,
            baseline_tariff_inr_per_kwh=11.50,
            previous_day_avg_tariff_inr_per_kwh=11.20,
        )


def test_minimum_energy_exceeding_requested_rejected():
    arrival = datetime(2025, 6, 15, 10, 0, tzinfo=IST)
    deadline = arrival + timedelta(minutes=30)

    with pytest.raises(ValidationError):
        CustomerServiceRequest(
            request_id="REQ-FAIL-03",
            cluster_id="delhi_ncr",
            request_type=ServiceType.FAST_CHARGE,
            customer_segment=CustomerSegment.PRIVATE_EV,
            arrival_ts=arrival,
            departure_deadline_ts=deadline,
            requested_energy_kwh=20.0,
            minimum_service_energy_kwh=30.0,
            baseline_tariff_inr_per_kwh=11.50,
            previous_day_avg_tariff_inr_per_kwh=11.20,
        )


def test_emergency_cannot_opt_in():
    arrival = datetime(2025, 6, 15, 10, 0, tzinfo=IST)
    deadline = arrival + timedelta(minutes=10)

    with pytest.raises(ValidationError) as exc:
        CustomerServiceRequest(
            request_id="REQ-EMG-01",
            cluster_id="delhi_ncr",
            request_type=ServiceType.FAST_CHARGE,
            customer_segment=CustomerSegment.EMERGENCY,
            arrival_ts=arrival,
            departure_deadline_ts=deadline,
            requested_energy_kwh=40.0,
            minimum_service_energy_kwh=40.0,
            flexibility_opt_in=True,
            baseline_tariff_inr_per_kwh=11.50,
            previous_day_avg_tariff_inr_per_kwh=11.20,
        )
    assert "EMERGENCY customer requests cannot opt in" in str(exc.value)


def test_swap_pack_count_must_be_positive_integer():
    arrival = datetime(2025, 6, 15, 10, 0, tzinfo=IST)
    deadline = arrival + timedelta(minutes=10)

    with pytest.raises(ValidationError):
        CustomerServiceRequest(
            request_id="REQ-SWAP-FAIL",
            cluster_id="bengaluru",
            request_type=ServiceType.BATTERY_SWAP,
            customer_segment=CustomerSegment.LOGISTICS_FLEET,
            arrival_ts=arrival,
            departure_deadline_ts=deadline,
            requested_pack_count=0,
            baseline_tariff_inr_per_kwh=11.50,
            previous_day_avg_tariff_inr_per_kwh=11.20,
        )


def test_tariff_reference_must_be_positive():
    arrival = datetime(2025, 6, 15, 10, 0, tzinfo=IST)
    deadline = arrival + timedelta(minutes=30)

    with pytest.raises(ValidationError):
        CustomerServiceRequest(
            request_id="REQ-TARIFF-FAIL",
            cluster_id="chennai",
            request_type=ServiceType.FAST_CHARGE,
            customer_segment=CustomerSegment.RIDE_HAILING,
            arrival_ts=arrival,
            departure_deadline_ts=deadline,
            requested_energy_kwh=25.0,
            baseline_tariff_inr_per_kwh=-1.0,
            previous_day_avg_tariff_inr_per_kwh=11.20,
        )
