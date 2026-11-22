"""VOLT Engine - Forecasting Baselines.

Responsibilities:
- Provide transparent, reproducible statistical benchmarks:
    1. Seasonal-Naive 24h: Same hour previous day (y_{T+h-24}).
    2. Seasonal-Naive 168h: Same hour previous week (y_{T+h-168}).
    3. Moving Average 24h: Rolling 24-hour mean prior to origin T.
- Produce point predictions and empirical quantile intervals.
- Non-negativity enforcement for physical energy targets.
"""

from typing import Any, Optional
import numpy as np
import pandas as pd


class SeasonalNaive24:
    """Seasonal-naive baseline using the same hour of the previous day (y_{T+h-24})."""

    def __init__(self, non_negative: bool = True):
        self.non_negative = non_negative

    def predict(self, X: pd.DataFrame) -> dict[str, np.ndarray]:
        """Predict P10, P50, and P90 using same hour yesterday.

        Args:
            X: Feature matrix containing 'lag_same_hour_yesterday' and 'roll_std_24_at_origin'.

        Returns:
            Dictionary with 'p10', 'p50', 'p90' arrays.
        """
        p50 = X["lag_same_hour_yesterday"].values.copy()
        if self.non_negative:
            p50 = np.clip(p50, 0.0, None)

        # Estimate empirical uncertainty using rolling standard deviation at origin
        # Under normal distribution: P10 = P50 - 1.28*std, P90 = P50 + 1.28*std
        std = X.get("roll_std_24_at_origin", pd.Series(0.15 * p50)).values
        p10 = p50 - 1.28 * std
        p90 = p50 + 1.28 * std

        if self.non_negative:
            p10 = np.clip(p10, 0.0, None)
            p90 = np.clip(p90, 0.0, None)

        return {"p10": p10, "p50": p50, "p90": p90}


class SeasonalNaive168:
    """Seasonal-naive baseline using the same hour of the previous week (y_{T+h-168})."""

    def __init__(self, non_negative: bool = True):
        self.non_negative = non_negative

    def predict(self, X: pd.DataFrame) -> dict[str, np.ndarray]:
        """Predict P10, P50, and P90 using same hour last week."""
        p50 = X["lag_same_hour_last_week"].values.copy()
        if self.non_negative:
            p50 = np.clip(p50, 0.0, None)

        std = X.get("roll_std_24_at_origin", pd.Series(0.15 * p50)).values
        p10 = p50 - 1.28 * std
        p90 = p50 + 1.28 * std

        if self.non_negative:
            p10 = np.clip(p10, 0.0, None)
            p90 = np.clip(p90, 0.0, None)

        return {"p10": p10, "p50": p50, "p90": p90}
