"""Case configuration schemas with rigorous provenance tagging."""

from typing import Any, Optional
from pydantic import BaseModel, Field
from engine.provenance import Provenance


class MetricItem(BaseModel):
    """A typed value with unit and provenance."""

    value: float
    unit: str
    provenance: Provenance
    percentage: Optional[float] = None
    description: Optional[str] = None


class CapacityMixItem(BaseModel):
    """Modality capacity share."""

    share: float
    percentage: float
    aggregate_capacity_mw: float
    unit: str
    provenance: Provenance
    description: str


class StorageCapacityFact(BaseModel):
    """Storage capacity fact from case study."""

    combined_storage_mwh: float
    unit: str
    provenance: Provenance
    asset_split_known: bool
    description: str


class ReliabilityBenchmark(BaseModel):
    """Reliability benchmark definitions."""

    current_reference: float
    current_percentage: float
    target: float
    target_percentage: float
    relative_increase_percent: float
    unit: str
    provenance: Provenance
    description: str


class EnergyLossBenchmark(BaseModel):
    """Energy loss benchmark definitions."""

    current_reference: float
    current_percentage: float
    target: float
    target_percentage: float
    relative_reduction_percent: float
    unit: str
    provenance: Provenance
    description: str


class EbitdaBenchmark(BaseModel):
    """EBITDA benchmark definitions."""

    target: float
    target_percentage: float
    operator: str
    scope: str
    unit: str
    provenance: Provenance
    description: str


class EmergencyReserveGuardrail(BaseModel):
    """Emergency reserve constraints."""

    value: float
    percentage: float
    unit: str
    scope: str
    constraint_type: str
    provenance: Provenance
    description: str


class CustomerTariffGuardrail(BaseModel):
    """Customer dynamic pricing bound."""

    min_multiplier: float
    max_multiplier: float
    reference_base: str
    provenance: Provenance
    description: str


class UnknownAssumptionDisclosure(BaseModel):
    """Explicit disclosure of parameters unsupplied by case study."""

    parameter: str
    case_fact_status: str
    assumed_value: Any
    unit: str
    provenance: Provenance = Provenance.ASSUMED
    rationale: str


class CaseConfigResponse(BaseModel):
    """Complete source-provided case configuration with explicit provenance."""

    title: str
    specification_version: str
    currency: str
    clusters: list[str]
    cluster_count: int
    cluster_provenance: Provenance

    installed_capacity: MetricItem
    capacity_mix: dict[str, CapacityMixItem]
    storage_capacity: StorageCapacityFact
    renewable_sourcing_reference: MetricItem

    kpi_benchmarks: dict[str, Any]
    operating_guardrails: dict[str, Any]

    historical_data_specification: dict[str, Any]

    unknown_assumptions: list[UnknownAssumptionDisclosure] = Field(
        ...,
        description="Explicit register of unknown parameters configured in assumptions.yaml",
    )
