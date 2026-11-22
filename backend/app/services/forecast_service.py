"""FastAPI Service for Phase 3 Probabilistic Forecasting."""

from pathlib import Path
from typing import Any, Optional
import json
from backend.app.schemas.forecast_schemas import (
    ForecastMetricsResponse,
    ForecastResponse,
    ForecastSummaryResponse,
    TargetMetadataSchema,
)
from engine.forecasting.pipeline import ForecastingPipeline, TARGET_SPECS
from engine.provenance import Provenance


class ForecastService:
    """Service providing probabilistic multi-vector forecast execution and cached metrics."""

    def __init__(
        self,
        data_dir: Path = Path("data/synthetic"),
        models_dir: Path = Path("models/forecasting"),
    ):
        self.data_dir = Path(data_dir)
        self.models_dir = Path(models_dir)
        self.pipeline = ForecastingPipeline(data_dir=self.data_dir, models_dir=self.models_dir)
        self._initialized = False

    def _ensure_initialized(self) -> None:
        if not self._initialized:
            self.pipeline.load_models()
            self._initialized = True

    def get_summary(self) -> ForecastSummaryResponse:
        """Return model inventory, supported targets, and historical training bounds."""
        self._ensure_initialized()

        target_list = [
            TargetMetadataSchema(
                target_name=k,
                display_name=v["display_name"],
                unit=v["unit"],
                scope=v["scope"],
                non_negative=v["non_negative"],
            )
            for k, v in TARGET_SPECS.items()
        ]

        clusters = ["delhi_ncr", "mumbai_mmr", "bengaluru", "hyderabad", "chennai", "national"]

        return ForecastSummaryResponse(
            available_targets=target_list,
            available_clusters=clusters,
            training_date_range={"start": "2021-01-01T00:00:00+05:30", "end": "2023-12-31T23:00:00+05:30"},
            validation_date_range={"start": "2024-01-01T00:00:00+05:30", "end": "2024-12-31T23:00:00+05:30"},
            test_date_range={"start": "2025-01-01T00:00:00+05:30", "end": "2025-12-31T23:00:00+05:30"},
            model_family="HistGradientBoostingRegressor (P10, P50, P90)",
            provenance=Provenance.SYNTHETIC,
            total_models_trained=len(self.pipeline.models),
        )

    def get_latest_forecast(
        self,
        cluster_id: str = "delhi_ncr",
        target_name: str = "fast_charge_demand_mwh",
    ) -> ForecastResponse:
        """Return the latest available 24-hour forecast from sample or disk."""
        self._ensure_initialized()

        # If sample file exists, return matching sample
        sample_file = Path("data/forecasts/latest_forecast_sample.json")
        sample_key = f"{target_name}_{cluster_id}"
        if sample_file.exists():
            with open(sample_file, "r", encoding="utf-8") as f:
                samples = json.load(f)
                if sample_key in samples:
                    return ForecastResponse(**samples[sample_key])

        # Otherwise generate dynamically from mid-2025 anchor timestamp
        anchor_origin = "2025-06-15T12:00:00+05:30"
        return self.run_forecast(
            origin_timestamp=anchor_origin,
            cluster_id=cluster_id,
            target_name=target_name,
        )

    def run_forecast(
        self,
        origin_timestamp: str,
        cluster_id: str = "delhi_ncr",
        target_name: str = "fast_charge_demand_mwh",
    ) -> ForecastResponse:
        """Execute rolling 24-hour ahead quantile forecast from specified origin."""
        self._ensure_initialized()

        result = self.pipeline.predict_24h(
            origin_timestamp=origin_timestamp,
            cluster_id=cluster_id,
            target_name=target_name,
        )
        return ForecastResponse(**result)

    def get_metrics(
        self,
        target_name: Optional[str] = None,
        cluster_id: Optional[str] = None,
    ) -> ForecastMetricsResponse:
        """Return backtest evaluation metrics."""
        self._ensure_initialized()

        metrics_file = self.models_dir / "evaluation_metrics.json"
        all_metrics = {}
        if metrics_file.exists():
            with open(metrics_file, "r", encoding="utf-8") as f:
                all_metrics = json.load(f)

        filtered = {}
        for k, v in all_metrics.items():
            t_match = target_name is None or v.get("target_name") == target_name
            c_match = cluster_id is None or v.get("cluster_id") == cluster_id
            if t_match and c_match:
                filtered[k] = v

        return ForecastMetricsResponse(
            evaluation_split="TEST_2025_UNTOUCHED",
            metrics=filtered,
            provenance=Provenance.SYNTHETIC,
        )


forecast_service = ForecastService()
