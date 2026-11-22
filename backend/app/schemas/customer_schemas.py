"""VOLT Backend - Customer Flexibility API Schemas."""

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field

from engine.customer.models import (
    CustomerSegment,
    FlexibilityEnvelope,
    IncentiveOffer,
    ServiceType,
    TariffRecommendation,
)


class SegmentInfo(BaseModel):
    """Specification of a customer classification segment."""
    segment: CustomerSegment
    priority_rank: int
    share_assumed: float
    opt_in_rate_assumed: float
    max_wait_minutes: float
    max_deferral_minutes: float
    flexible_fraction: float
    is_shiftable: bool
    description: str
    provenance: str = "ASSUMED"


class CustomerSegmentsResponse(BaseModel):
    """List of all customer segments and their behavioural assumptions."""
    total_segments: int
    segments: list[SegmentInfo]
    provenance: str = "ASSUMED"
    disclaimer: str = "Customer segments and opt-in parameters are synthetic model assumptions for engineering demonstration."


class RequestClusterSummary(BaseModel):
    """Summary of disaggregated requests for a metro cluster."""
    cluster_id: str
    fast_charge_requests: int
    swap_requests: int
    total_fast_charge_kwh: float
    total_swap_packs: int
    reconciliation_pass_rate_pct: float


class CustomerRequestsSummaryResponse(BaseModel):
    """Summary statistics and reconciliation status of generated customer requests."""
    total_requests: int
    total_fast_charge_requests: int
    total_battery_swap_requests: int
    total_fast_charge_mwh: float
    total_swap_mwh: float
    total_swap_packs: int
    reconciliation_passed: bool
    cluster_summaries: list[RequestClusterSummary]
    provenance: str = "SYNTHETIC"
    disclaimer: str = "Generated from hourly aggregate synthetic load using SyntheticRequestDisaggregator."


class FlexibilitySummaryResponse(BaseModel):
    """Aggregate demand flexibility breakdown across the active network."""
    total_demand_kwh: float
    non_shiftable_demand_kwh: float
    eligible_flexible_demand_kwh: float
    opted_in_demand_kwh: float
    expected_accepted_demand_kwh: float
    realized_accepted_demand_kwh: float
    protected_priority_requests: int
    protected_priority_demand_kwh: float
    deadline_violations: int = 0
    modality_breakdown: dict[str, Any]
    segment_breakdown: dict[str, Any]
    provenance: str = "SYNTHETIC_SIMULATION"


class FlexibilityEnvelopesResponse(BaseModel):
    """Paginated list of customer flexibility envelopes."""
    total_count: int
    offset: int
    limit: int
    envelopes: list[FlexibilityEnvelope]
    provenance: str = "SYNTHETIC"


class FlexibilityEvaluateRequest(BaseModel):
    """Input payload to trigger customer scenario flexibility evaluation."""
    scenario_id: str = Field("NORMAL", description="Scenario identifier (e.g. HIGH_OPT_IN, TIGHT_DEADLINES)")
    cluster_id: Optional[str] = Field(None, description="Optional cluster filter (or None for all)")
    seed: Optional[int] = Field(None, description="Optional random seed override")


class TariffRecommendRequest(BaseModel):
    """Input payload for dynamic tariff recommendation."""
    cluster_id: str = Field("delhi_ncr", description="Cluster identifier")
    service_type: ServiceType = Field(ServiceType.FAST_CHARGE, description="Service modality")
    timestamp: datetime = Field(default_factory=datetime.now, description="Evaluation timestamp")
    previous_day_average_tariff_inr_per_kwh: float = Field(11.50, gt=0.0, description="Previous day average reference tariff")
    forecast_procurement_cost_inr_per_kwh: Optional[float] = Field(None, ge=0.0, description="Forecast wholesale IEX/procurement rate")
    forecast_demand_mw: Optional[float] = Field(None, ge=0.0, description="Forecast cluster demand in MW")
    available_capacity_mw: Optional[float] = Field(None, gt=0.0, description="Available cluster power capacity in MW")
    forecast_solar_surplus_mw: Optional[float] = Field(None, ge=0.0, description="Surplus solar availability in MW")


class ScenarioIncentiveSummary(BaseModel):
    """Incentive and financial impact summary for a single scenario."""
    scenario_id: str
    scenario_name: str
    description: str
    expected_accepted_demand_kwh: float
    realized_accepted_demand_kwh: float
    total_retail_revenue_inr: float
    total_incentive_cost_inr: float
    net_financial_impact_inr: float
    average_wait_minutes: float


class IncentivesSummaryResponse(BaseModel):
    """Overview of voluntary flexibility incentives across evaluated scenarios."""
    scenarios: list[ScenarioIncentiveSummary]
    provenance: str = "ASSUMED_SIMULATION"
    disclaimer: str = "Flexibility incentives are modeled as separate operating costs, completely decoupled from retail tariff revenue."


class FlexibilityScenarioMetadata(BaseModel):
    """Metadata describing a customer flexibility scenario."""
    scenario_id: str
    name: str
    description: str
    seed: int
    parameters: dict[str, Any]
    provenance: str = "SYNTHETIC"


class FlexibilityScenariosResponse(BaseModel):
    """Catalog of all configured customer flexibility and disturbance scenarios."""
    total_scenarios: int
    scenarios: list[FlexibilityScenarioMetadata]
    provenance: str = "SYNTHETIC"
