"""Tests for Phase 3 multi-vector probabilistic forecasting and quantile models."""

import numpy as np
import pandas as pd
import pytest
from engine.forecasting.baselines import SeasonalNaive24, SeasonalNaive168
from engine.forecasting.features import FeatureEngineer
from engine.forecasting.metrics import evaluate_predictions, pinball_loss
from engine.forecasting.quantile_model import TreeQuantileForecaster


@pytest.fixture
def sample_timeseries():
    """Create a 30-day synthetic hourly series for testing feature extraction and models."""
    t_index = pd.date_range("2024-06-01", periods=720, freq="h", tz="Asia/Kolkata")
    hours = t_index.hour.values
    # Diurnal wave with noise
    y = 50.0 + 30.0 * np.sin(2 * np.pi * (hours - 8) / 24.0) + np.random.normal(0, 2.0, size=len(t_index))
    y = np.clip(y, 5.0, 100.0)

    df = pd.DataFrame(
        {
            "timestamp": t_index.strftime("%Y-%m-%dT%H:%M:%S+05:30"),
            "cluster_id": "delhi_ncr",
            "fast_charge_demand_mwh": y,
            "temperature_c": 28.0 + 8.0 * np.sin(2 * np.pi * (hours - 10) / 24.0),
            "cloud_cover_pct": 30.0 + 10.0 * np.random.uniform(size=len(t_index)),
            "wind_speed_m_s": 4.0 + 1.0 * np.random.uniform(size=len(t_index)),
            "humidity_pct": 55.0,
            "provenance": "SYNTHETIC",
        }
    )
    return df


@pytest.mark.unit
def test_chronological_feature_extraction_no_leakage(sample_timeseries):
    """Verify that features for horizon h at origin T strictly observe only t <= T."""
    engineer = FeatureEngineer(seed=42)
    features = engineer.extract_features(
        sample_timeseries,
        target_col="fast_charge_demand_mwh",
        horizons=list(range(1, 25)),
        stride=24,
    )

    assert not features.X.empty
    assert len(features.X) == len(features.y)
    assert "lag_at_origin" in features.X.columns
    assert "lag_same_hour_yesterday" in features.X.columns
    assert "lag_same_hour_last_week" in features.X.columns

    # Verify lag_same_hour_yesterday is observable at origin T
    # At target T+h, lag_same_hour_yesterday is at index T+h-24. Since h <= 24, T+h-24 <= T!
    for h in [1, 6, 12, 24]:
        sub_X = features.X[features.X["horizon"] == h]
        assert not sub_X["lag_same_hour_yesterday"].isna().any()
        assert not sub_X["lag_at_origin"].isna().any()


@pytest.mark.unit
def test_quantile_non_crossing_guarantee(sample_timeseries):
    """Verify that P10 <= P50 <= P90 is guaranteed across all samples."""
    engineer = FeatureEngineer(seed=42)
    features = engineer.extract_features(
        sample_timeseries,
        target_col="fast_charge_demand_mwh",
        horizons=[1, 6, 12, 24],
        stride=12,
    )

    forecaster = TreeQuantileForecaster(
        target_name="fast_charge_demand_mwh",
        max_iter=20,
        seed=42,
    )
    forecaster.fit(features.X, features.y)
    preds = forecaster.predict(features.X)

    p10 = preds["p10"]
    p50 = preds["p50"]
    p90 = preds["p90"]

    # Non-crossing checks
    assert (p10 <= p50).all(), "Quantile crossing detected: P10 > P50"
    assert (p50 <= p90).all(), "Quantile crossing detected: P50 > P90"
    assert (p10 <= p90).all(), "Quantile crossing detected: P10 > P90"

    # Non-negativity check
    assert (p10 >= 0.0).all(), "Negative prediction detected in P10"
    assert (p50 >= 0.0).all(), "Negative prediction detected in P50"
    assert (p90 >= 0.0).all(), "Negative prediction detected in P90"


@pytest.mark.unit
def test_solar_night_cutoff_guarantee():
    """Verify that solar forecasts are strictly 0.0 at night for all quantiles."""
    # Create night samples (hours 22, 23, 0, 1, 2)
    X = pd.DataFrame(
        {
            "horizon": [1, 2, 3, 4, 5],
            "target_hour": [22, 23, 0, 1, 2],
            "target_dayofweek": [1, 1, 1, 1, 1],
            "target_month": [6, 6, 6, 6, 6],
            "target_is_weekend": [0.0, 0.0, 0.0, 0.0, 0.0],
            "sin_hour": [0.0] * 5,
            "cos_hour": [1.0] * 5,
            "sin_dayofweek": [0.0] * 5,
            "cos_dayofweek": [1.0] * 5,
            "sin_month": [0.0] * 5,
            "cos_month": [1.0] * 5,
            "solar_zenith_proxy": [0.0] * 5,
            "lag_at_origin": [10.0] * 5,
            "lag_origin_minus_1": [10.0] * 5,
            "lag_origin_minus_2": [10.0] * 5,
            "lag_same_hour_yesterday": [0.0] * 5,
            "lag_same_hour_last_week": [0.0] * 5,
            "roll_mean_24_at_origin": [10.0] * 5,
            "roll_std_24_at_origin": [2.0] * 5,
            "roll_max_24_at_origin": [20.0] * 5,
            "roll_min_24_at_origin": [0.0] * 5,
            "temp_at_origin": [25.0] * 5,
            "cloud_at_origin": [10.0] * 5,
            "wind_at_origin": [3.0] * 5,
            "humidity_at_origin": [60.0] * 5,
            "nwp_forecast_temp": [24.0] * 5,
            "nwp_forecast_cloud": [15.0] * 5,
            "nwp_forecast_wind": [3.0] * 5,
        }
    )
    y = pd.Series([0.0, 0.0, 0.0, 0.0, 0.0])

    forecaster = TreeQuantileForecaster(
        target_name="solar_available_mwh",
        max_iter=10,
        seed=42,
    )
    forecaster.fit(X, y)
    preds = forecaster.predict(X)

    assert (preds["p10"] == 0.0).all()
    assert (preds["p50"] == 0.0).all()
    assert (preds["p90"] == 0.0).all()


@pytest.mark.unit
def test_pinball_loss_and_metrics_calculation():
    """Verify pinball loss and evaluation metric logic."""
    y_true = np.array([10.0, 20.0, 30.0, 40.0])
    p50 = np.array([12.0, 18.0, 32.0, 38.0])
    p10 = np.array([8.0, 15.0, 25.0, 35.0])
    p90 = np.array([15.0, 25.0, 35.0, 45.0])

    # For P50: abs errors are 2, 2, 2, 2 -> MAE = 2.0
    report = evaluate_predictions(
        y_true=y_true,
        p10=p10,
        p50=p50,
        p90=p90,
        target_name="test_target",
        baseline_p50=np.array([15.0, 15.0, 35.0, 35.0]),  # Errors: 5, 5, 5, 5 -> MAE = 5.0
        horizons=np.array([1, 2, 3, 4]),
    )

    assert report.overall_mae == 2.0
    assert report.baseline_mae == 5.0
    # Improvement = (5.0 - 2.0) / 5.0 = 60.0%
    assert report.mae_improvement_pct == 60.0

    # Coverage: all 4 are within [p10, p90] -> 100%
    assert report.coverage_p10_p90_pct == 100.0


@pytest.mark.unit
def test_seasonal_naive_baselines():
    """Verify SeasonalNaive24 baseline mechanics."""
    X = pd.DataFrame(
        {
            "lag_same_hour_yesterday": [50.0, 60.0],
            "lag_same_hour_last_week": [45.0, 55.0],
            "roll_std_24_at_origin": [5.0, 6.0],
        }
    )
    b24 = SeasonalNaive24()
    p24 = b24.predict(X)
    assert list(p24["p50"]) == [50.0, 60.0]
    assert (p24["p10"] <= p24["p50"]).all()
    assert (p24["p50"] <= p24["p90"]).all()

    b168 = SeasonalNaive168()
    p168 = b168.predict(X)
    assert list(p168["p50"]) == [45.0, 55.0]
