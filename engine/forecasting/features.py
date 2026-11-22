"""VOLT Engine - Forecasting Feature Engineering.

Responsibilities:
- Build leakage-free feature representations for rolling 24-hour ahead quantile forecasting.
- Enforce strict temporal ordering: at forecast origin T, only observations from t <= T are observable.
- Feature families:
    1. Calendar & Astronomical: hour of day, day of week, month, weekend flag, diurnal sine/cosine, solar zenith proxy.
    2. Horizon: forecast lead time h in [1, 24] hours.
    3. Observable Lags at Origin T:
        - y_T (lag h relative to target T+h)
        - y_{T-1}, y_{T-2} (short-term momentum at origin)
        - y_{T+h-24} (same hour previous day, observable for all h in [1, 24])
        - y_{T+h-168} (same hour previous week, capturing 7-day seasonality)
        - 24-hour rolling mean, std, min, max at origin T
    4. Weather Covariates:
        - Observed weather at origin T: temperature, cloud cover, humidity, wind speed
        - Operational NWP forecast proxy for target hour T+h with lead-time dependent error
- Robust handling of missing history and edge-of-dataset boundaries.
"""

from dataclasses import dataclass
from typing import Optional
import numpy as np
import pandas as pd


@dataclass
class ForecastFeatures:
    """Container for feature matrix X, target y, and metadata alignment."""

    X: pd.DataFrame
    y: Optional[pd.Series]
    timestamps: pd.Series
    cluster_ids: pd.Series
    horizons: pd.Series
    feature_names: list[str]


class FeatureEngineer:
    """Generates strictly leakage-free tabular features for multi-step quantile models."""

    def __init__(self, seed: int = 42):
        self.seed = seed
        self.rng = np.random.default_rng(seed)

    def extract_features(
        self,
        df: pd.DataFrame,
        target_col: str,
        cluster_id_col: str = "cluster_id",
        timestamp_col: str = "timestamp",
        horizons: Optional[list[int]] = None,
        stride: int = 1,
        add_nwp_noise: bool = True,
    ) -> ForecastFeatures:
        """Extract multi-horizon training or inference features across all clusters.

        Args:
            df: Historical time series dataframe sorted chronologically.
            target_col: Target variable name (e.g., 'fast_charge_demand_mwh').
            cluster_id_col: Column for cluster identifier (or dummy if national market).
            timestamp_col: Column for ISO timestamps.
            horizons: List of horizon hours to forecast (default: 1..24).
            stride: Sampling stride in hours for training set generation (e.g., 1 for every hour).
            add_nwp_noise: If True, adds realistic lead-time dependent error to weather forecast proxies.

        Returns:
            ForecastFeatures dataclass with feature matrix X and metadata.
        """
        if horizons is None:
            horizons = list(range(1, 25))

        data = df.copy()
        if not pd.api.types.is_datetime64_any_dtype(data[timestamp_col]):
            data["dt"] = pd.to_datetime(data[timestamp_col])
        else:
            data["dt"] = data[timestamp_col]

        # Ensure single cluster column if not present
        if cluster_id_col not in data.columns:
            data[cluster_id_col] = "national"

        feature_rows = []
        target_values = []
        target_timestamps = []
        target_clusters = []
        target_horizons = []

        # Process each cluster independently to avoid inter-city leakage
        for cid, cluster_group in data.groupby(cluster_id_col, sort=False):
            cg = cluster_group.sort_values("dt").reset_index(drop=True)
            n_rows = len(cg)
            if n_rows < 168 + 24:
                # Need at least 1 week of history for lags
                continue

            # Pre-extract series arrays for vectorized speed
            dt_series = cg["dt"]
            hours = dt_series.dt.hour.values
            dayofweek = dt_series.dt.dayofweek.values
            months = dt_series.dt.month.values
            is_weekend = (dayofweek >= 5).astype(float)
            dayofyear = dt_series.dt.dayofyear.values

            y_arr = cg[target_col].values.astype(float)

            # Weather variables if available
            has_weather = "temperature_c" in cg.columns or "ambient_temp_c" in cg.columns
            temp_col = "temperature_c" if "temperature_c" in cg.columns else "ambient_temp_c"
            temp_arr = cg[temp_col].values.astype(float) if has_weather else np.zeros(n_rows)

            has_cloud = "cloud_cover_pct" in cg.columns
            cloud_arr = cg["cloud_cover_pct"].values.astype(float) if has_cloud else np.zeros(n_rows)

            has_wind = "wind_speed_m_s" in cg.columns
            wind_arr = cg["wind_speed_m_s"].values.astype(float) if has_wind else np.zeros(n_rows)

            has_humidity = "humidity_pct" in cg.columns or "relative_humidity_pct" in cg.columns
            hum_col = "humidity_pct" if "humidity_pct" in cg.columns else "relative_humidity_pct"
            hum_arr = cg[hum_col].values.astype(float) if has_humidity else np.zeros(n_rows)

            # Rolling 24-hour mean and std computed strictly on past y
            # Series rolling shift(0) means including current index
            y_series = pd.Series(y_arr)
            roll_mean_24 = y_series.rolling(24, min_periods=6).mean().values
            roll_std_24 = y_series.rolling(24, min_periods=6).std().fillna(0.0).values
            roll_max_24 = y_series.rolling(24, min_periods=6).max().values
            roll_min_24 = y_series.rolling(24, min_periods=6).min().values

            # Origin indices T range from 168 to n_rows - max(horizons)
            min_T = 168  # 1 week of lag history
            max_T = n_rows - max(horizons)

            for T in range(min_T, max_T, stride):
                # Origin values observable at time T
                y_T = y_arr[T]
                y_T_minus_1 = y_arr[T - 1]
                y_T_minus_2 = y_arr[T - 2]
                roll_m = roll_mean_24[T]
                roll_s = roll_std_24[T]
                roll_mx = roll_max_24[T]
                roll_mn = roll_min_24[T]

                temp_T = temp_arr[T]
                cloud_T = cloud_arr[T]
                wind_T = wind_arr[T]
                hum_T = hum_arr[T]

                for h in horizons:
                    idx = T + h
                    target_h = hours[idx]
                    target_dow = dayofweek[idx]
                    target_mon = months[idx]
                    target_wkd = is_weekend[idx]
                    target_doy = dayofyear[idx]

                    # Astronomical zenith angle proxy (deterministic calendar calculation)
                    # Solar noon approx at hour 12:00
                    solar_zenith = np.sin(np.pi * np.clip((target_h - 6.0) / 12.0, 0.0, 1.0))
                    solar_zenith = solar_zenith if (6 <= target_h <= 18) else 0.0

                    # Observable lags at origin T for horizon h:
                    # Same hour yesterday: index (T + h - 24).
                    # Since h <= 24, (T + h - 24) <= T, so strictly observable!
                    lag_24 = y_arr[T + h - 24]

                    # Same hour last week: index (T + h - 168). Strictly observable!
                    lag_168 = y_arr[T + h - 168]

                    # NWP Day-Ahead Weather Forecast Proxy for target time (T + h)
                    # Realistic operational forecast: NWP error increases slightly with lead time h
                    if add_nwp_noise:
                        temp_err = self.rng.normal(0.0, 0.20 + 0.03 * h)
                        cloud_err = self.rng.normal(0.0, 2.0 + 0.40 * h)
                        wind_err = self.rng.normal(0.0, 0.15 + 0.02 * h)
                    else:
                        temp_err = 0.0
                        cloud_err = 0.0
                        wind_err = 0.0

                    nwp_temp = float(np.clip(temp_arr[idx] + temp_err, -5.0, 52.0))
                    nwp_cloud = float(np.clip(cloud_arr[idx] + cloud_err, 0.0, 100.0))
                    nwp_wind = float(np.clip(wind_arr[idx] + wind_err, 0.0, 35.0))

                    feat = {
                        "horizon": h,
                        "target_hour": target_h,
                        "target_dayofweek": target_dow,
                        "target_month": target_mon,
                        "target_is_weekend": target_wkd,
                        "sin_hour": float(np.sin(2 * np.pi * target_h / 24.0)),
                        "cos_hour": float(np.cos(2 * np.pi * target_h / 24.0)),
                        "sin_dayofweek": float(np.sin(2 * np.pi * target_dow / 7.0)),
                        "cos_dayofweek": float(np.cos(2 * np.pi * target_dow / 7.0)),
                        "sin_month": float(np.sin(2 * np.pi * target_mon / 12.0)),
                        "cos_month": float(np.cos(2 * np.pi * target_mon / 12.0)),
                        "solar_zenith_proxy": float(solar_zenith),
                        # Observable Target Lags
                        "lag_at_origin": float(y_T),
                        "lag_origin_minus_1": float(y_T_minus_1),
                        "lag_origin_minus_2": float(y_T_minus_2),
                        "lag_same_hour_yesterday": float(lag_24),
                        "lag_same_hour_last_week": float(lag_168),
                        # Rolling Statistics at Origin T
                        "roll_mean_24_at_origin": float(roll_m),
                        "roll_std_24_at_origin": float(roll_s),
                        "roll_max_24_at_origin": float(roll_mx),
                        "roll_min_24_at_origin": float(roll_mn),
                        # Observable Weather at Origin T
                        "temp_at_origin": float(temp_T),
                        "cloud_at_origin": float(cloud_T),
                        "wind_at_origin": float(wind_T),
                        "humidity_at_origin": float(hum_T),
                        # NWP Forecast Covariates for Target Hour
                        "nwp_forecast_temp": nwp_temp,
                        "nwp_forecast_cloud": nwp_cloud,
                        "nwp_forecast_wind": nwp_wind,
                    }
                    feature_rows.append(feat)
                    target_values.append(y_arr[idx])
                    target_timestamps.append(dt_series.iloc[idx])
                    target_clusters.append(cid)
                    target_horizons.append(h)

        if not feature_rows:
            return ForecastFeatures(
                X=pd.DataFrame(),
                y=pd.Series(dtype=float),
                timestamps=pd.Series(dtype="datetime64[ns]"),
                cluster_ids=pd.Series(dtype=str),
                horizons=pd.Series(dtype=int),
                feature_names=[],
            )

        X_df = pd.DataFrame(feature_rows)
        return ForecastFeatures(
            X=X_df,
            y=pd.Series(target_values, dtype=float),
            timestamps=pd.Series(target_timestamps),
            cluster_ids=pd.Series(target_clusters),
            horizons=pd.Series(target_horizons),
            feature_names=list(X_df.columns),
        )
