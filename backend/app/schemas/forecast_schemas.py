"""Pydantic schemas for Phase 3 forecasting API endpoints."""

from typing import Any, Optional
from pydantic import BaseModel, Field
from engine.provenance import Provenance


class TargetMetadataSchema(BaseModel):
    """Metadata describing a forecasting target."""

    target_name: str
    display_name: str
    unit: str
    scope: str
    non_negative: bool


class HorizonPointSchema(BaseModel):
    """Point and quantile forecast for one step in the horizon."""

    horizon_hour: int
    target_timestamp: str
    p10: float
    p50: float
    p90: float


class ForecastResponse(BaseModel):
    """Rolling 24-hour probabilistic forecast response."""

    origin_timestamp: str
    target_name: str
    target_display_name: str
    target_unit: str
    cluster_id: str
    model_family: str
    training_date_range: dict[str, str]
    provenance: Provenance = Provenance.SYNTHETIC
    horizons: list[HorizonPointSchema]
    evaluation_metrics: Optional[dict[str, Any]] = None


class ForecastRunRequest(BaseModel):
    """Request schema to compute a forecast from an origin timestamp."""

    origin_timestamp: str = Field(..., description="ISO timestamp (e.g., 2025-06-15T12:00:00+05:30)")
    cluster_id: str = Field("delhi_ncr", description="Cluster ID (or 'national' for IEX)")
    target_name: str = Field("fast_charge_demand_mwh", description="Canonical target name")


class ForecastSummaryResponse(BaseModel):
    """Model inventory, supported targets, and historical training bounds."""

    available_targets: list[TargetMetadataSchema]
    available_clusters: list[str]
    training_date_range: dict[str, str]
    validation_date_range: dict[str, str]
    test_date_range: dict[str, str]
    model_family: str
    provenance: Provenance = Provenance.SYNTHETIC
    total_models_trained: int


class ForecastMetricsResponse(BaseModel):
    """Chronological backtest evaluation metrics across targets and clusters."""

    evaluation_split: str
    metrics: dict[str, Any]
    provenance: Provenance = Provenance.SYNTHETIC
