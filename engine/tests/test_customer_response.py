"""Unit tests for CustomerResponseModel."""

from datetime import datetime, timedelta, timezone
import pytest

from engine.customer.envelope import FlexibilityEnvelopeEngine
from engine.customer.models import (
    CustomerSegment,
    CustomerServiceRequest,
    ServiceType,
)
from engine.customer.response_model import CustomerResponseModel

IST = timezone(timedelta(hours=5, minutes=30))


@pytest.fixture
def envelope_engine():
    return FlexibilityEnvelopeEngine()


@pytest.fixture
def response_model():
    return CustomerResponseModel()


def test_acceptance_probability_bounds(envelope_engine, response_model):
    arrival = datetime(2025, 6, 15, 10, 0, tzinfo=IST)
    deadline = arrival + timedelta(hours=3)

    req = CustomerServiceRequest(
        request_id="REQ-TEST-PROB",
        cluster_id="delhi_ncr",
        request_type=ServiceType.FAST_CHARGE,
        customer_segment=CustomerSegment.LOGISTICS_FLEET,
        arrival_ts=arrival,
        departure_deadline_ts=deadline,
        requested_energy_kwh=40.0,
        minimum_service_energy_kwh=10.0,
        max_wait_minutes=60.0,
        max_deferral_minutes=120.0,
        flexibility_opt_in=True,
        baseline_tariff_inr_per_kwh=11.50,
        previous_day_avg_tariff_inr_per_kwh=11.20,
    )

    env = envelope_engine.compute_envelope(req)

    # Test across various incentive rates
    for rate in [0.0, 1.0, 2.5, 10.0, 100.0]:
        res = response_model.evaluate_acceptance(req, env, incentive_rate_inr_per_kwh=rate)
        assert 0.0 <= res.acceptance_probability <= 1.0


def test_emergency_zero_acceptance(envelope_engine, response_model):
    arrival = datetime(2025, 6, 15, 10, 0, tzinfo=IST)
    deadline = arrival + timedelta(hours=3)

    req = CustomerServiceRequest(
        request_id="REQ-EMG-RESP",
        cluster_id="delhi_ncr",
        request_type=ServiceType.FAST_CHARGE,
        customer_segment=CustomerSegment.EMERGENCY,
        arrival_ts=arrival,
        departure_deadline_ts=deadline,
        requested_energy_kwh=40.0,
        minimum_service_energy_kwh=40.0,
        flexibility_opt_in=False,
        baseline_tariff_inr_per_kwh=11.50,
        previous_day_avg_tariff_inr_per_kwh=11.20,
    )

    env = envelope_engine.compute_envelope(req)
    res = response_model.evaluate_acceptance(req, env, incentive_rate_inr_per_kwh=10.0)
    assert res.acceptance_probability == 0.0
    assert res.stochastic_accepted is False
    assert res.expected_accepted_energy_kwh == 0.0


def test_non_opted_in_zero_acceptance(envelope_engine, response_model):
    arrival = datetime(2025, 6, 15, 10, 0, tzinfo=IST)
    deadline = arrival + timedelta(hours=3)

    req = CustomerServiceRequest(
        request_id="REQ-NOOPT-RESP",
        cluster_id="delhi_ncr",
        request_type=ServiceType.FAST_CHARGE,
        customer_segment=CustomerSegment.RIDE_HAILING,
        arrival_ts=arrival,
        departure_deadline_ts=deadline,
        requested_energy_kwh=40.0,
        minimum_service_energy_kwh=10.0,
        flexibility_opt_in=False,
        baseline_tariff_inr_per_kwh=11.50,
        previous_day_avg_tariff_inr_per_kwh=11.20,
    )

    env = envelope_engine.compute_envelope(req)
    res = response_model.evaluate_acceptance(req, env, incentive_rate_inr_per_kwh=5.0)
    assert res.acceptance_probability == 0.0
    assert res.stochastic_accepted is False


def test_incentive_monotonicity(envelope_engine, response_model):
    arrival = datetime(2025, 6, 15, 10, 0, tzinfo=IST)
    deadline = arrival + timedelta(hours=3)

    req = CustomerServiceRequest(
        request_id="REQ-MONO-RESP",
        cluster_id="bengaluru",
        request_type=ServiceType.FAST_CHARGE,
        customer_segment=CustomerSegment.RIDE_HAILING,
        arrival_ts=arrival,
        departure_deadline_ts=deadline,
        requested_energy_kwh=40.0,
        minimum_service_energy_kwh=10.0,
        max_wait_minutes=30.0,
        max_deferral_minutes=60.0,
        flexibility_opt_in=True,
        baseline_tariff_inr_per_kwh=11.50,
        previous_day_avg_tariff_inr_per_kwh=11.20,
    )

    env = envelope_engine.compute_envelope(req)
    res_low = response_model.evaluate_acceptance(req, env, incentive_rate_inr_per_kwh=0.50)
    res_med = response_model.evaluate_acceptance(req, env, incentive_rate_inr_per_kwh=2.00)
    res_high = response_model.evaluate_acceptance(req, env, incentive_rate_inr_per_kwh=4.00)

    assert res_low.acceptance_probability < res_med.acceptance_probability
    assert res_med.acceptance_probability < res_high.acceptance_probability


def test_reproducible_stochastic_simulation(envelope_engine, response_model):
    arrival = datetime(2025, 6, 15, 10, 0, tzinfo=IST)
    deadline = arrival + timedelta(hours=3)

    req = CustomerServiceRequest(
        request_id="REQ-SEED-TEST",
        cluster_id="mumbai_mmr",
        request_type=ServiceType.FAST_CHARGE,
        customer_segment=CustomerSegment.LOGISTICS_FLEET,
        arrival_ts=arrival,
        departure_deadline_ts=deadline,
        requested_energy_kwh=40.0,
        minimum_service_energy_kwh=10.0,
        max_wait_minutes=60.0,
        max_deferral_minutes=120.0,
        flexibility_opt_in=True,
        baseline_tariff_inr_per_kwh=11.50,
        previous_day_avg_tariff_inr_per_kwh=11.20,
    )

    env = envelope_engine.compute_envelope(req)
    res1 = response_model.evaluate_acceptance(req, env, incentive_rate_inr_per_kwh=1.5, random_seed=42)
    res2 = response_model.evaluate_acceptance(req, env, incentive_rate_inr_per_kwh=1.5, random_seed=42)

    assert res1.acceptance_probability == res2.acceptance_probability
    assert res1.stochastic_accepted == res2.stochastic_accepted
