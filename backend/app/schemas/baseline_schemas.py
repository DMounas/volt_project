"""Schemas for IEX adapter and baseline policy endpoints."""

from typing import Any, Optional
from pydantic import BaseModel, Field
from engine.provenance import Provenance


class IEXDiagnosticsResponse(BaseModel):
    """Schema for IEX adapter diagnostic report."""

    total_15min_records_read: int
    total_hours_produced: int
    aggregation_method_used: str
    complete_hours_count: int
    incomplete_hours_count: int
    duplicate_blocks_count: int
    out_of_order_blocks_count: int
    missing_blocks_details: list[dict[str, Any]]
    min_hourly_price_inr_mwh: float
    max_hourly_price_inr_mwh: float
    mean_hourly_price_inr_mwh: float
    provenance: Provenance = Provenance.SYNTHETIC


class BaselineCalibrationResponse(BaseModel):
    """Schema for baseline policy calibration audit."""

    target_service_reliability_pct: float
    target_energy_loss_pct: float
    measured_service_reliability_pct: float
    measured_energy_loss_pct: float
    residual_reliability_pct: float
    residual_loss_pct: float
    total_objective_error: float
    calibrated_parameters: dict[str, Any]
    parameter_bounds: dict[str, Any]
    calibration_sample_hours: int
    energy_reconciliation_pass_rate_pct: float
    max_energy_residual_mwh: float
    status: str
    provenance: str = "SYNTHETIC_CALIBRATION"
    notes: str


class BaselineSimulationResponse(BaseModel):
    """Schema for baseline simulation execution audit."""

    total_intervals_audited: int
    reconciled_intervals_count: int
    reconciliation_pass_rate_pct: float
    is_fully_reconciled: bool
    measured_kpis: dict[str, float]
    residuals: dict[str, float]
    energy_accounting_mwh: dict[str, Any]
    renewable_accounting_mwh: dict[str, Any]
    reserve_compliance: bool
    no_double_counting_audit: str
    provenance: Provenance = Provenance.SYNTHETIC
