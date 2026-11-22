"""Pydantic schemas for data manifest, summaries, and time series endpoints."""

from typing import Any, Optional
from pydantic import BaseModel, Field
from engine.provenance import Provenance


class FileInfoSchema(BaseModel):
    """Metadata schema for a generated data file."""

    path: str
    row_count: int
    size_bytes: int
    sha256: str
    description: str


class DataManifestResponse(BaseModel):
    """Schema for the master data manifest."""

    manifest_version: str
    generator_version: str
    provenance: Provenance = Provenance.SYNTHETIC
    random_seed: int
    demo_mode: bool
    date_range: dict[str, Any]
    clusters: list[str]
    config_hashes: dict[str, str]
    files: dict[str, FileInfoSchema]
    methodology_disclaimer: str


class ClusterHourlySummaryItem(BaseModel):
    """Aggregated summary stats for one cluster over the dataset."""

    cluster_id: str
    cluster_name: str
    hours_count: int
    mean_temperature_c: float
    mean_fast_charge_demand_mwh: float
    max_fast_charge_demand_mwh: float
    mean_swap_requests: float
    max_swap_requests: int
    mean_renewable_available_mwh: float
    max_renewable_available_mwh: float
    provenance: Provenance = Provenance.SYNTHETIC


class DataSummaryResponse(BaseModel):
    """Summary representation across all five clusters."""

    total_clusters: int
    total_hours_per_cluster: int
    total_cluster_hours: int
    date_range: dict[str, str]
    cluster_summaries: list[ClusterHourlySummaryItem]
    provenance: Provenance = Provenance.SYNTHETIC


class HourlyDataPoint(BaseModel):
    """Individual hourly observation record."""

    timestamp: str
    cluster_id: str
    temperature_c: float
    fast_charge_demand_mwh: float
    swap_requests: int
    swap_energy_equivalent_mwh: float
    solar_available_mwh: float
    wind_available_mwh: float
    renewable_available_mwh: float
    discom_tariff_inr_mwh: float
    iex_projected_price_inr_mwh: float
    provenance: Provenance = Provenance.SYNTHETIC


class HourlyDataResponse(BaseModel):
    """Paginated hourly time series records."""

    cluster_id: str
    total_points: int
    limit: int
    offset: int
    data: list[HourlyDataPoint]
    provenance: Provenance = Provenance.SYNTHETIC
