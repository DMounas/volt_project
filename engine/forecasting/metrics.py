"""VOLT Engine - Forecasting Evaluation Metrics.

Responsibilities:
- Evaluate deterministic point accuracy: MAE, RMSE, WAPE (%).
- Evaluate probabilistic calibration & sharpness:
    * Pinball Loss (Quantile Loss) for P10, P50, and P90.
    * Empirical Coverage of the P10-P90 interval (nominal target: 80%).
    * Average Interval Width (sharpness).
- Horizon-bucket stratified evaluation:
    * Near-Term: 1 to 6 hours
    * Mid-Term: 7 to 12 hours
    * Day-Ahead: 13 to 24 hours
- Baseline-relative improvement comparison.
"""

from dataclasses import asdict, dataclass
from typing import Any, Optional
import numpy as np
import pandas as pd


@dataclass
class HorizonBucketMetrics:
    """Evaluation metrics for a specific forecast horizon bucket."""

    bucket_name: str
    horizon_range: str
    sample_count: int
    mae: float
    rmse: float
    wape_pct: float
    pinball_p10: float
    pinball_p50: float
    pinball_p90: float
    mean_pinball: float
    coverage_p10_p90_pct: float
    mean_interval_width: float
    baseline_mae: Optional[float] = None
    mae_improvement_pct: Optional[float] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ForecastEvaluationReport:
    """Comprehensive evaluation report for a forecasting target."""

    target_name: str
    target_unit: str
    cluster_id: str
    evaluation_split: str  # e.g., 'TEST_2025'
    sample_count: int
    overall_mae: float
    overall_rmse: float
    overall_wape_pct: float
    pinball_p10: float
    pinball_p50: float
    pinball_p90: float
    mean_pinball: float
    coverage_p10_p90_pct: float
    mean_interval_width: float
    baseline_name: str
    baseline_mae: float
    mae_improvement_pct: float
    horizon_buckets: dict[str, HorizonBucketMetrics]
    notes: str
    daylight_coverage_p10_p90_pct: Optional[float] = None

    def to_dict(self) -> dict[str, Any]:
        res = asdict(self)
        res["horizon_buckets"] = {k: v.to_dict() if hasattr(v, "to_dict") else v for k, v in self.horizon_buckets.items()}
        return res


def pinball_loss(y_true: np.ndarray, y_pred: np.ndarray, q: float) -> float:
    """Calculate average pinball loss for quantile q in (0, 1)."""
    err = y_true - y_pred
    return float(np.mean(np.maximum(q * err, (q - 1.0) * err)))


def evaluate_predictions(
    y_true: np.ndarray,
    p10: np.ndarray,
    p50: np.ndarray,
    p90: np.ndarray,
    target_name: str,
    target_unit: str = "MWh",
    cluster_id: str = "all",
    evaluation_split: str = "TEST_2025",
    baseline_p50: Optional[np.ndarray] = None,
    baseline_name: str = "SeasonalNaive24",
    horizons: Optional[np.ndarray] = None,
) -> ForecastEvaluationReport:
    """Compute comprehensive point and quantile metrics with horizon stratification."""
    y = np.asarray(y_true, dtype=float)
    p10 = np.asarray(p10, dtype=float)
    p50 = np.asarray(p50, dtype=float)
    p90 = np.asarray(p90, dtype=float)

    n_samples = len(y)
    if n_samples == 0:
        raise ValueError("Cannot evaluate empty prediction arrays")

    # Point accuracy metrics on P50
    abs_errors = np.abs(y - p50)
    sq_errors = (y - p50) ** 2
    mae = float(np.mean(abs_errors))
    rmse = float(np.sqrt(np.mean(sq_errors)))

    # WAPE with zero denominator protection
    sum_actuals = float(np.sum(y))
    if sum_actuals > 1e-6:
        wape_pct = float(np.sum(abs_errors) / sum_actuals * 100.0)
    else:
        wape_pct = 0.0

    # Quantile pinball losses
    pb_10 = pinball_loss(y, p10, 0.10)
    pb_50 = pinball_loss(y, p50, 0.50)
    pb_90 = pinball_loss(y, p90, 0.90)
    mean_pb = float((pb_10 + pb_50 + pb_90) / 3.0)

    # Interval metrics
    in_interval = (y >= p10) & (y <= p90)
    coverage_pct = float(np.mean(in_interval) * 100.0)
    mean_width = float(np.mean(p90 - p10))

    # Daylight interval metrics (critical for solar where night zeros inflate all-hours coverage)
    daylight_cov_pct: Optional[float] = None
    daylight_mask = y > 0.05
    if np.any(daylight_mask) and ("solar" in target_name.lower() or np.sum(y == 0.0) > 0.3 * len(y)):
        daylight_cov_pct = round(float(np.mean(in_interval[daylight_mask]) * 100.0), 1)

    # Baseline comparison
    if baseline_p50 is not None:
        b_p50 = np.asarray(baseline_p50, dtype=float)
        b_mae = float(np.mean(np.abs(y - b_p50)))
        if b_mae > 1e-6:
            improvement_pct = float((b_mae - mae) / b_mae * 100.0)
        else:
            improvement_pct = 0.0
    else:
        b_mae = mae
        improvement_pct = 0.0

    # Horizon bucket stratification
    bucket_definitions = {
        "near_term": ("1-6h", [1, 2, 3, 4, 5, 6]),
        "mid_term": ("7-12h", [7, 8, 9, 10, 11, 12]),
        "day_ahead": ("13-24h", list(range(13, 25))),
    }

    horizon_metrics = {}
    if horizons is not None:
        h_arr = np.asarray(horizons, dtype=int)
        for b_key, (b_label, b_hours) in bucket_definitions.items():
            mask = np.isin(h_arr, b_hours)
            if np.any(mask):
                sub_y = y[mask]
                sub_p10 = p10[mask]
                sub_p50 = p50[mask]
                sub_p90 = p90[mask]

                sub_mae = float(np.mean(np.abs(sub_y - sub_p50)))
                sub_rmse = float(np.sqrt(np.mean((sub_y - sub_p50) ** 2)))
                sub_sum = float(np.sum(sub_y))
                sub_wape = float(np.sum(np.abs(sub_y - sub_p50)) / sub_sum * 100.0) if sub_sum > 1e-6 else 0.0

                sub_pb10 = pinball_loss(sub_y, sub_p10, 0.10)
                sub_pb50 = pinball_loss(sub_y, sub_p50, 0.50)
                sub_pb90 = pinball_loss(sub_y, sub_p90, 0.90)

                sub_cov = float(np.mean((sub_y >= sub_p10) & (sub_y <= sub_p90)) * 100.0)
                sub_width = float(np.mean(sub_p90 - sub_p10))

                sub_b_mae = None
                sub_imp = None
                if baseline_p50 is not None:
                    sub_b_p50 = b_p50[mask]
                    sub_b_mae = float(np.mean(np.abs(sub_y - sub_b_p50)))
                    sub_imp = float((sub_b_mae - sub_mae) / sub_b_mae * 100.0) if sub_b_mae > 1e-6 else 0.0

                horizon_metrics[b_key] = HorizonBucketMetrics(
                    bucket_name=b_key,
                    horizon_range=b_label,
                    sample_count=int(np.sum(mask)),
                    mae=round(sub_mae, 3),
                    rmse=round(sub_rmse, 3),
                    wape_pct=round(sub_wape, 2),
                    pinball_p10=round(sub_pb10, 3),
                    pinball_p50=round(sub_pb50, 3),
                    pinball_p90=round(sub_pb90, 3),
                    mean_pinball=round((sub_pb10 + sub_pb50 + sub_pb90) / 3.0, 3),
                    coverage_p10_p90_pct=round(sub_cov, 1),
                    mean_interval_width=round(sub_width, 3),
                    baseline_mae=round(sub_b_mae, 3) if sub_b_mae is not None else None,
                    mae_improvement_pct=round(sub_imp, 2) if sub_imp is not None else None,
                )

    return ForecastEvaluationReport(
        target_name=target_name,
        target_unit=target_unit,
        cluster_id=cluster_id,
        evaluation_split=evaluation_split,
        sample_count=n_samples,
        overall_mae=round(mae, 3),
        overall_rmse=round(rmse, 3),
        overall_wape_pct=round(wape_pct, 2),
        pinball_p10=round(pb_10, 3),
        pinball_p50=round(pb_50, 3),
        pinball_p90=round(pb_90, 3),
        mean_pinball=round(mean_pb, 3),
        coverage_p10_p90_pct=round(coverage_pct, 1),
        mean_interval_width=round(mean_width, 3),
        baseline_name=baseline_name,
        baseline_mae=round(b_mae, 3),
        mae_improvement_pct=round(improvement_pct, 2),
        horizon_buckets=horizon_metrics,
        notes=(
            f"Chronological evaluation on {evaluation_split}. Non-crossing quantiles enforced."
            + (f" Daylight-only coverage: {daylight_cov_pct}% (uninflated by night zeros)." if daylight_cov_pct is not None else "")
        ),
        daylight_coverage_p10_p90_pct=daylight_cov_pct,
    )
