"""Integration tests for Customer Flexibility, Tariff, and Incentive APIs."""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_customer_segments_endpoint():
    res = client.get("/api/v1/customers/segments")
    assert res.status_code == 200
    data = res.json()
    assert data["total_segments"] == 5
    assert data["provenance"] == "ASSUMED"

    segments = {s["segment"]: s for s in data["segments"]}
    assert "EMERGENCY" in segments
    assert "PRIORITY_FLEET" in segments
    assert "RIDE_HAILING" in segments
    assert "LOGISTICS_FLEET" in segments
    assert "PRIVATE_EV" in segments

    # Emergency and Priority Fleet are strictly non-shiftable with 0 opt-in
    assert segments["EMERGENCY"]["is_shiftable"] is False
    assert segments["EMERGENCY"]["opt_in_rate_assumed"] == 0.0
    assert segments["PRIORITY_FLEET"]["is_shiftable"] is False
    assert segments["PRIORITY_FLEET"]["opt_in_rate_assumed"] == 0.0


def test_customer_requests_summary_endpoint():
    res = client.get("/api/v1/customers/requests/summary")
    assert res.status_code == 200
    data = res.json()
    assert data["total_requests"] > 0
    assert data["total_fast_charge_requests"] > 0
    assert data["total_battery_swap_requests"] > 0
    assert data["total_fast_charge_mwh"] > 0.0
    assert data["total_swap_mwh"] > 0.0
    assert data["reconciliation_passed"] is True
    assert len(data["cluster_summaries"]) == 5


def test_flexibility_summary_endpoint():
    res = client.get("/api/v1/flexibility/summary")
    assert res.status_code == 200
    data = res.json()
    assert data["total_demand_kwh"] > 0
    assert data["non_shiftable_demand_kwh"] > 0
    assert data["eligible_flexible_demand_kwh"] > 0
    assert data["deadline_violations"] == 0
    assert data["protected_priority_requests"] > 0
    assert "FAST_CHARGE" in data["modality_breakdown"]
    assert "BATTERY_SWAP" in data["modality_breakdown"]


def test_flexibility_envelopes_endpoint():
    res = client.get("/api/v1/flexibility/envelopes?limit=10&offset=0")
    assert res.status_code == 200
    data = res.json()
    assert data["total_count"] > 0
    assert len(data["envelopes"]) <= 10
    first = data["envelopes"][0]
    assert "request_id" in first
    assert "reason_code" in first
    assert "non_shiftable_energy_kwh" in first
    assert "flexible_energy_kwh" in first


def test_flexibility_evaluate_scenario_endpoint():
    payload = {
        "scenario_id": "TIGHT_DEADLINES",
        "seed": 42,
    }
    res = client.post("/api/v1/flexibility/evaluate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["scenario_id"] == "TIGHT_DEADLINES"
    assert data["deadline_violations"] == 0
    assert data["total_demand_kwh"] > 0
    assert data["total_retail_revenue_inr"] > 0
    assert "cluster_metrics" in data
    assert len(data["sample_envelopes"]) > 0


def test_dynamic_tariff_recommendation_bounds():
    # Normal case
    payload = {
        "cluster_id": "delhi_ncr",
        "service_type": "FAST_CHARGE",
        "previous_day_average_tariff_inr_per_kwh": 10.0,
        "forecast_procurement_cost_inr_per_kwh": 5.20,
    }
    res = client.post("/api/v1/tariffs/recommend", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["tariff_min_inr_per_kwh"] == 8.0
    assert data["tariff_max_inr_per_kwh"] == 12.0
    assert data["final_tariff_inr_per_kwh"] == 10.0

    # Ceiling clipping
    payload_high = {
        "cluster_id": "delhi_ncr",
        "service_type": "FAST_CHARGE",
        "previous_day_average_tariff_inr_per_kwh": 10.0,
        "forecast_procurement_cost_inr_per_kwh": 25.0,  # Extreme peak
        "forecast_demand_mw": 235.0,
        "available_capacity_mw": 240.0,
    }
    res_high = client.post("/api/v1/tariffs/recommend", json=payload_high)
    assert res_high.status_code == 200
    data_high = res_high.json()
    assert data_high["clamped"] is True
    assert data_high["clamping_direction"] == "UPPER_BOUND"
    assert data_high["final_tariff_inr_per_kwh"] == 12.0

    # Floor clipping
    payload_low = {
        "cluster_id": "delhi_ncr",
        "service_type": "FAST_CHARGE",
        "previous_day_average_tariff_inr_per_kwh": 10.0,
        "forecast_procurement_cost_inr_per_kwh": 1.0,
        "forecast_solar_surplus_mw": 50.0,
    }
    res_low = client.post("/api/v1/tariffs/recommend", json=payload_low)
    assert res_low.status_code == 200
    data_low = res_low.json()
    assert data_low["clamped"] is True
    assert data_low["clamping_direction"] == "LOWER_BOUND"
    assert data_low["final_tariff_inr_per_kwh"] == 8.0


def test_dynamic_tariff_invalid_inputs_rejected():
    payload = {
        "cluster_id": "delhi_ncr",
        "service_type": "FAST_CHARGE",
        "previous_day_average_tariff_inr_per_kwh": -5.0,  # Negative
    }
    res = client.post("/api/v1/tariffs/recommend", json=payload)
    assert res.status_code in (400, 422)


def test_incentives_summary_endpoint():
    res = client.get("/api/v1/incentives/summary")
    assert res.status_code == 200
    data = res.json()
    assert len(data["scenarios"]) >= 5
    for sc in data["scenarios"]:
        assert sc["total_retail_revenue_inr"] > 0
        assert sc["total_incentive_cost_inr"] >= 0
        assert sc["net_financial_impact_inr"] == round(
            sc["total_retail_revenue_inr"] - sc["total_incentive_cost_inr"], 2
        )


def test_flexibility_scenarios_catalog_endpoint():
    res = client.get("/api/v1/flexibility/scenarios")
    assert res.status_code == 200
    data = res.json()
    assert data["total_scenarios"] >= 9
    scenario_ids = [s["scenario_id"] for s in data["scenarios"]]
    assert "HIGH_EMERGENCY_SHARE" in scenario_ids
    assert "HIGH_OPT_IN" in scenario_ids
    assert "LOW_OPT_IN" in scenario_ids
    assert "HIGH_PRICE_SENSITIVITY" in scenario_ids
    assert "LOW_PRICE_SENSITIVITY" in scenario_ids
    assert "TIGHT_DEADLINES" in scenario_ids
    assert "FLEXIBLE_LOGISTICS_FLEET" in scenario_ids
    assert "CLUSTER_CONGESTION_ASYMMETRY" in scenario_ids
    assert "COMBINED_HIGH_DEMAND_IEX" in scenario_ids
