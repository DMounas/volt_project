"""VOLT Engine - Forecasting Pipeline Orchestrator.

Responsibilities:
- Manages multi-vector probabilistic forecasting across the 5 canonical targets:
    1. fast_charge_demand_mwh (Fast-Charging Demand, MWh)
    2. swap_demand_mwh (Battery Swap Demand, MWh)
    3. solar_available_mwh (Solar Generation, MWh)
    4. wind_available_mwh (Wind Generation, MWh)
    5. iex_clearing_price_inr_mwh (IEX DAM Price, INR/MWh)
- Enforces strict chronological data splitting:
    * Train: 2021-01-01 to 2023-12-31 (3 years)
    * Validation: 2024-01-01 to 2024-12-31 (1 leap year)
    * Test: 2025-01-01 to 2025-12-31 (1 year, untouched final test)
- Orchestrates training, model persistence, and evaluation against baselines.
- Real-time rolling 24-hour forecast inference for API and UI.
"""

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any, Optional
import numpy as np
import pandas as pd
from engine.forecasting.baselines import SeasonalNaive24, SeasonalNaive168
from engine.forecasting.features import FeatureEngineer, ForecastFeatures
from engine.forecasting.metrics import ForecastEvaluationReport, evaluate_predictions
from engine.forecasting.quantile_model import TreeQuantileForecaster
from engine.provenance import Provenance

TARGET_SPECS = {
    "fast_charge_demand_mwh": {
        "display_name": "Fast-Charging Demand",
        "unit": "MWh",
        "scope": "cluster",
        "source_col": "fast_charge_demand_mwh",
        "source_file": "cluster_hourly.csv.gz",
        "non_negative": True,
    },
    "swap_demand_mwh": {
        "display_name": "Battery Swap Demand",
        "unit": "MWh",
        "scope": "cluster",
        "source_col": "swap_energy_equivalent_mwh",
        "source_file": "cluster_hourly.csv.gz",
        "non_negative": True,
    },
    "solar_available_mwh": {
        "display_name": "Solar Availability",
        "unit": "MWh",
        "scope": "cluster",
        "source_col": "solar_available_mwh",
        "source_file": "cluster_hourly.csv.gz",
        "non_negative": True,
    },
    "wind_available_mwh": {
        "display_name": "Wind Availability",
        "unit": "MWh",
        "scope": "cluster",
        "source_col": "wind_available_mwh",
        "source_file": "cluster_hourly.csv.gz",
        "non_negative": True,
    },
    "iex_clearing_price_inr_mwh": {
        "display_name": "IEX DAM Market Price",
        "unit": "INR/MWh",
        "scope": "national",
        "source_col": "clearing_price_inr_mwh",
        "source_file": "iex_hourly",  # Derived via adapter
        "non_negative": True,
    },
}


class ForecastingPipeline:
    """End-to-end pipeline for training, evaluating, and serving multi-vector forecasts."""

    def __init__(
        self,
        data_dir: Path = Path("data/synthetic"),
        models_dir: Path = Path("models/forecasting"),
        seed: int = 42,
    ):
        self.data_dir = Path(data_dir)
        self.models_dir = Path(models_dir)
        self.seed = seed
        self.feature_engineer = FeatureEngineer(seed=seed)
        self.models: dict[str, TreeQuantileForecaster] = {}
        self.evaluation_reports: dict[str, ForecastEvaluationReport] = {}

    def _get_model_key(self, target_name: str, cluster_id: str) -> str:
        return f"{target_name}_{cluster_id}"

    def train_and_evaluate_all(
        self,
        stride_train: int = 4,
        stride_eval: int = 6,
    ) -> dict[str, Any]:
        """Train quantile models on 2021-2023, validate on 2024, test on 2025.

        Args:
            stride_train: Step stride in hours for training set extraction (4 for fast training).
            stride_eval: Step stride in hours for evaluation set extraction.

        Returns:
            Dictionary mapping target_cluster to evaluation metrics dictionary.
        """
        self.models_dir.mkdir(parents=True, exist_ok=True)

        # 1. Load cluster hourly dataset
        cluster_file = self.data_dir / "cluster_hourly.csv.gz"
        if not cluster_file.exists():
            raise FileNotFoundError(f"Cluster dataset not found at {cluster_file}")
        cluster_df = pd.read_csv(cluster_file, compression="gzip")
        cluster_df["dt"] = pd.to_datetime(cluster_df["timestamp"])

        # 2. Load and aggregate IEX 15-minute dataset to hourly
        iex_file = self.data_dir / "iex_dam_15min.csv.gz"
        if not iex_file.exists():
            raise FileNotFoundError(f"IEX dataset not found at {iex_file}")
        iex_15min_df = pd.read_csv(iex_file, compression="gzip")

        from engine.data.iex_adapter import IEXMarketAdapter
        adapter = IEXMarketAdapter()
        iex_hourly_df, _ = adapter.aggregate_15min_to_hourly(iex_15min_df)
        iex_hourly_df["dt"] = pd.to_datetime(iex_hourly_df["timestamp"])
        iex_hourly_df["cluster_id"] = "national"

        # Define chronological split masks
        # Train: 2021-01-01 to 2023-12-31
        # Validation: 2024-01-01 to 2024-12-31
        # Test: 2025-01-01 to 2025-12-31
        train_mask_c = cluster_df["dt"] < "2024-01-01"
        test_mask_c = (cluster_df["dt"] >= "2025-01-01") & (cluster_df["dt"] <= "2025-12-31 23:00:00")

        train_mask_i = iex_hourly_df["dt"] < "2024-01-01"
        test_mask_i = (iex_hourly_df["dt"] >= "2025-01-01") & (iex_hourly_df["dt"] <= "2025-12-31 23:00:00")

        results = {}

        for target_name, spec in TARGET_SPECS.items():
            is_national = spec["scope"] == "national"
            source_df = iex_hourly_df if is_national else cluster_df
            train_mask = train_mask_i if is_national else train_mask_c
            test_mask = test_mask_i if is_national else test_mask_c

            train_df = source_df[train_mask].copy().reset_index(drop=True)
            test_df = source_df[test_mask].copy().reset_index(drop=True)

            clusters = ["national"] if is_national else list(cluster_df["cluster_id"].unique())

            for cid in clusters:
                m_key = self._get_model_key(target_name, cid)
                sub_train = train_df if is_national else train_df[train_df["cluster_id"] == cid]
                sub_test = test_df if is_national else test_df[test_df["cluster_id"] == cid]

                # Extract training features
                feat_train = self.feature_engineer.extract_features(
                    sub_train,
                    target_col=spec["source_col"],
                    cluster_id_col="cluster_id",
                    horizons=list(range(1, 25)),
                    stride=stride_train,
                    add_nwp_noise=True,
                )

                # Extract test features (untouched chronological test)
                feat_test = self.feature_engineer.extract_features(
                    sub_test,
                    target_col=spec["source_col"],
                    cluster_id_col="cluster_id",
                    horizons=list(range(1, 25)),
                    stride=stride_eval,
                    add_nwp_noise=True,
                )

                if feat_train.X.empty or feat_test.X.empty:
                    continue

                # Train quantile model
                forecaster = TreeQuantileForecaster(
                    target_name=target_name,
                    target_unit=spec["unit"],
                    cluster_id=cid,
                    quantiles=[0.10, 0.50, 0.90],
                    max_iter=60,
                    seed=self.seed,
                    non_negative=spec["non_negative"],
                )
                forecaster.fit(
                    feat_train.X,
                    feat_train.y,
                    train_start="2021-01-01",
                    train_end="2023-12-31",
                )
                forecaster.save(self.models_dir)
                self.models[m_key] = forecaster

                # Predict on test set
                preds = forecaster.predict(feat_test.X)

                # Baseline comparison: Seasonal-Naive 24h
                base_model = SeasonalNaive24(non_negative=spec["non_negative"])
                base_preds = base_model.predict(feat_test.X)

                # Evaluate metrics
                report = evaluate_predictions(
                    y_true=feat_test.y.values,
                    p10=preds["p10"],
                    p50=preds["p50"],
                    p90=preds["p90"],
                    target_name=target_name,
                    target_unit=spec["unit"],
                    cluster_id=cid,
                    evaluation_split="TEST_2025_UNTOUCHED",
                    baseline_p50=base_preds["p50"],
                    baseline_name="SeasonalNaive24",
                    horizons=feat_test.horizons.values,
                )
                self.evaluation_reports[m_key] = report
                results[m_key] = report.to_dict()

        # Save all reports to metrics JSON
        metrics_file = self.models_dir / "evaluation_metrics.json"
        with open(metrics_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)

        return results

    def load_models(self) -> None:
        """Load all persisted model artifacts from models_dir."""
        if not self.models_dir.exists():
            return

        for pkl_file in self.models_dir.glob("*.pkl"):
            forecaster = TreeQuantileForecaster.load(pkl_file)
            m_key = self._get_model_key(forecaster.target_name, forecaster.cluster_id)
            self.models[m_key] = forecaster

        metrics_file = self.models_dir / "evaluation_metrics.json"
        if metrics_file.exists():
            with open(metrics_file, "r", encoding="utf-8") as f:
                raw_reports = json.load(f)
                for k, v in raw_reports.items():
                    self.evaluation_reports[k] = ForecastEvaluationReport(**v)

    def predict_24h(
        self,
        origin_timestamp: str,
        cluster_id: str,
        target_name: str,
    ) -> dict[str, Any]:
        """Generate rolling 24-hour ahead P10, P50, and P90 forecast starting at origin_timestamp.

        Args:
            origin_timestamp: ISO timestamp string (e.g., '2025-06-15T12:00:00+05:30').
            cluster_id: Cluster key or 'national'.
            target_name: Canonical target name.

        Returns:
            Dictionary with 24 horizon steps, quantiles, and metadata.
        """
        spec = TARGET_SPECS.get(target_name)
        if not spec:
            raise ValueError(f"Unknown forecast target '{target_name}'")

        is_national = spec["scope"] == "national"
        effective_cid = "national" if is_national else cluster_id
        m_key = self._get_model_key(target_name, effective_cid)

        if m_key not in self.models:
            model_file = self.models_dir / f"{target_name}_{effective_cid}.pkl"
            if model_file.exists():
                self.models[m_key] = TreeQuantileForecaster.load(model_file)
            else:
                raise FileNotFoundError(f"Trained model for '{m_key}' not found in {self.models_dir}")

        forecaster = self.models[m_key]

        # Load required history leading up to origin_timestamp (at least 168 hours)
        origin_dt = pd.to_datetime(origin_timestamp)
        hist_start_dt = origin_dt - pd.Timedelta(hours=200)

        source_file = self.data_dir / (
            "iex_dam_15min.csv.gz" if is_national else "cluster_hourly.csv.gz"
        )
        if not source_file.exists():
            raise FileNotFoundError(f"Data file not found at {source_file}")

        if is_national:
            from engine.data.iex_adapter import IEXMarketAdapter
            raw_iex = pd.read_csv(source_file, compression="gzip")
            adapter = IEXMarketAdapter()
            hist_df, _ = adapter.aggregate_15min_to_hourly(raw_iex)
            hist_df["dt"] = pd.to_datetime(hist_df["timestamp"])
            hist_df["cluster_id"] = "national"
        else:
            hist_df = pd.read_csv(source_file, compression="gzip")
            hist_df["dt"] = pd.to_datetime(hist_df["timestamp"])
            hist_df = hist_df[hist_df["cluster_id"] == effective_cid]

        # Filter window [hist_start_dt, origin_dt + 24h]
        window_df = hist_df[
            (hist_df["dt"] >= hist_start_dt) & (hist_df["dt"] <= origin_dt + pd.Timedelta(hours=24))
        ].copy().sort_values("dt").reset_index(drop=True)

        if window_df.empty:
            raise ValueError(f"No historical observations found near origin {origin_timestamp}")

        # Find origin row index
        match_idx = np.where(window_df["dt"] == origin_dt)[0]
        if len(match_idx) == 0:
            # Nearest timestamp prior to origin
            prior = np.where(window_df["dt"] <= origin_dt)[0]
            if len(prior) == 0:
                raise ValueError(f"Origin timestamp {origin_timestamp} precedes available data")
            origin_idx = prior[-1]
        else:
            origin_idx = match_idx[0]

        # Extract features for horizons 1..24 from origin_idx
        feat = self.feature_engineer.extract_features(
            window_df,
            target_col=spec["source_col"],
            cluster_id_col="cluster_id",
            horizons=list(range(1, 25)),
            stride=1,
            add_nwp_noise=False,
        )

        # Filter features where origin matches origin_dt
        # Note: timestamps in feat correspond to (T + h)
        expected_horizons = list(range(1, 25))
        sub_X = feat.X.iloc[:24].copy()

        preds = forecaster.predict(sub_X)

        horizons_data = []
        for h in range(1, 25):
            t_future = origin_dt + pd.Timedelta(hours=h)
            h_idx = h - 1
            horizons_data.append(
                {
                    "horizon_hour": h,
                    "target_timestamp": t_future.isoformat(),
                    "p10": round(float(preds["p10"][h_idx]), 3),
                    "p50": round(float(preds["p50"][h_idx]), 3),
                    "p90": round(float(preds["p90"][h_idx]), 3),
                }
            )

        # Retrieve evaluation summary if available
        eval_metrics = None
        if m_key in self.evaluation_reports:
            eval_metrics = self.evaluation_reports[m_key].to_dict()

        return {
            "origin_timestamp": origin_dt.isoformat(),
            "target_name": target_name,
            "target_display_name": spec["display_name"],
            "target_unit": spec["unit"],
            "cluster_id": effective_cid,
            "model_family": forecaster.metadata.model_family if forecaster.metadata else "HistGradientBoostingRegressor",
            "training_date_range": forecaster.metadata.train_date_range if forecaster.metadata else {"start": "2021-01-01", "end": "2023-12-31"},
            "provenance": Provenance.SYNTHETIC.value,
            "horizons": horizons_data,
            "evaluation_metrics": eval_metrics,
        }
