"""Tests for Forecast Origin Integrity and Uncertainty Injection.

Acceptance criteria:
- Forecast origins never access future actual observations
- Scenario actuals differ from forecasts where uncertainty is injected
"""

import pytest

from engine.optimization.pipeline import OptimizationPipeline
from engine.twin.events import ScenarioEventEngine


def test_forecast_origin_never_accesses_future_shock():
    """Verify that under ZERO_AHEAD visibility, forecast before shock origin has zero future leakage."""
    event_engine = ScenarioEventEngine()
    pipeline = OptimizationPipeline()
    baseline = pipeline.load_cluster_inputs(clusters=["delhi_ncr"])

    # EVENING_DEMAND_SURGE starts at hour 17
    sc = event_engine.get_scenario("EVENING_DEMAND_SURGE")
    assert sc["start_hour"] == 17
    assert sc["forecast_visibility"] == "ZERO_AHEAD"

    actuals = event_engine.generate_actual_realization("EVENING_DEMAND_SURGE", baseline, seed=42)

    # Forecast requested at t0 = 10 (well before shock starts at 17)
    fc_t10 = event_engine.generate_forecast_expectation(
        scenario_id="EVENING_DEMAND_SURGE",
        baseline_inputs=baseline,
        actual_realizations=actuals,
        forecast_origin_hour=10,
        horizon_hours=24,
        seed=42,
    )

    # Hour 17 in the forecast is step index (17 - 10) = 7
    step_at_17 = 7
    # Under ZERO_AHEAD, forecast for hour 17 at t0=10 MUST equal the baseline demand, NOT the shock actual!
    expected_baseline_fc = baseline["delhi_ncr"].fast_charge_demand_mwh[17]
    forecasted_fc = fc_t10["delhi_ncr"].fast_charge_demand_mwh[step_at_17]
    actual_shock_fc = actuals["delhi_ncr"].fast_charge_demand_mwh[17]

    assert forecasted_fc == pytest.approx(expected_baseline_fc, rel=1e-2)
    assert actual_shock_fc > forecasted_fc * 1.30  # Actual experienced +50% surge


def test_scenario_actuals_differ_from_forecasts_where_uncertainty_injected():
    """Verify that actual synthetic realization diverges from forecast expectations during shock."""
    event_engine = ScenarioEventEngine()
    pipeline = OptimizationPipeline()
    baseline = pipeline.load_cluster_inputs(clusters=["delhi_ncr"])

    # SOLAR_CLOUD_DROP from 11:00 to 15:00
    actuals = event_engine.generate_actual_realization("SOLAR_CLOUD_DROP", baseline, seed=42)

    fc_t8 = event_engine.generate_forecast_expectation(
        scenario_id="SOLAR_CLOUD_DROP",
        baseline_inputs=baseline,
        actual_realizations=actuals,
        forecast_origin_hour=8,
        horizon_hours=24,
        seed=42,
    )

    # At hour 12 (step index 4):
    step_at_12 = 4
    actual_solar = actuals["delhi_ncr"].solar_available_mwh[12]
    forecast_solar = fc_t8["delhi_ncr"].solar_available_mwh[step_at_12]

    # Actual solar dropped by ~70%, while forecast at t=8 did not know
    assert actual_solar < forecast_solar * 0.50
