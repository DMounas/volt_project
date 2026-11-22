"""VOLT Engine - Customer Flexibility Data Models.

Defines strictly typed, validated models for:
- Customer service requests (fast charging and battery swapping)
- Customer flexibility envelopes
- Dynamic tariff recommendations with 80%-120% regulatory clipping
- Incentive offers with operational cost-benefit separation
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field, model_validator


class CustomerSegment(str, Enum):
    """Customer segments with distinct operational priorities and elasticity."""
    EMERGENCY = "EMERGENCY"
    PRIORITY_FLEET = "PRIORITY_FLEET"
    RIDE_HAILING = "RIDE_HAILING"
    LOGISTICS_FLEET = "LOGISTICS_FLEET"
    PRIVATE_EV = "PRIVATE_EV"


class ServiceType(str, Enum):
    """Physical EV energy delivery modality."""
    FAST_CHARGE = "FAST_CHARGE"
    BATTERY_SWAP = "BATTERY_SWAP"


class FlexibilityReasonCode(str, Enum):
    """Human-readable explainability reason codes for flexibility and tariffs."""
    EMERGENCY_NON_SHIFTABLE = "EMERGENCY_NON_SHIFTABLE"
    PRIORITY_RESERVE_NON_SHIFTABLE = "PRIORITY_RESERVE_NON_SHIFTABLE"
    NOT_OPTED_IN = "NOT_OPTED_IN"
    DEADLINE_CONSTRAINED = "DEADLINE_CONSTRAINED"
    PARTIALLY_FLEXIBLE = "PARTIALLY_FLEXIBLE"
    FLEXIBLE_WITHIN_WINDOW = "FLEXIBLE_WITHIN_WINDOW"
    TARIFF_BOUND_ENFORCED = "TARIFF_BOUND_ENFORCED"
    NOT_EVALUABLE = "NOT_EVALUABLE"
    INSUFFICIENT_BENEFIT = "INSUFFICIENT_BENEFIT"


class CustomerServiceRequest(BaseModel):
    """Typed representation of an individual customer charging or swap session request."""
    request_id: str = Field(..., description="Unique synthetic request ID (no PII)")
    cluster_id: str = Field(..., description="Metro cluster identifier (e.g. delhi_ncr)")
    request_type: ServiceType = Field(..., description="Service modality (FAST_CHARGE or BATTERY_SWAP)")
    customer_segment: CustomerSegment = Field(..., description="Customer classification segment")
    arrival_ts: datetime = Field(..., description="Arrival timestamp with timezone")
    departure_deadline_ts: datetime = Field(..., description="Mandatory departure deadline")
    
    # Fast-charging fields
    requested_energy_kwh: float = Field(0.0, description="Requested fast charge energy in kWh")
    minimum_service_energy_kwh: float = Field(0.0, description="Minimum acceptable energy for trip continuation in kWh")
    
    # Battery swapping fields
    requested_pack_count: int = Field(0, description="Discrete integer pack count requested")
    minimum_pack_count: int = Field(0, description="Minimum discrete integer packs required")
    pack_capacity_kwh: float = Field(2.5, description="Nominal capacity per battery pack in kWh")
    
    # Service flexibility parameters
    max_wait_minutes: float = Field(0.0, ge=0.0, description="Maximum acceptable queue/wait time in minutes")
    max_deferral_minutes: float = Field(0.0, ge=0.0, description="Maximum deferral slack beyond normal charging duration")
    flexibility_opt_in: bool = Field(False, description="Explicit voluntary opt-in state (never inferred from segment)")
    maximum_detour_km: Optional[float] = Field(None, ge=0.0, description="Max acceptable detour distance (ASSUMED)")
    service_priority: int = Field(5, ge=1, le=5, description="Priority rank (1=Emergency, 2=Priority, 3=Ride, 4=Logistics, 5=Private)")
    
    # Tariff references
    baseline_tariff_inr_per_kwh: float = Field(..., gt=0.0, description="Base applicable retail tariff in INR/kWh")
    previous_day_avg_tariff_inr_per_kwh: float = Field(..., gt=0.0, description="Previous day average tariff reference in INR/kWh")
    
    # Provenance
    provenance: str = Field("SYNTHETIC", description="Provenance tag: SYNTHETIC")
    assumption_reference: str = Field("customer_flexibility_assumptions_v1", description="Assumptions register reference")

    @model_validator(mode="after")
    def validate_request_integrity(self) -> "CustomerServiceRequest":
        # Deadline must not be before arrival
        if self.departure_deadline_ts < self.arrival_ts:
            raise ValueError(
                f"Departure deadline {self.departure_deadline_ts} cannot be before arrival time {self.arrival_ts}"
            )
        
        # Fast-charging validation
        if self.request_type == ServiceType.FAST_CHARGE:
            if self.requested_energy_kwh <= 0.0:
                raise ValueError("Fast charge request must specify positive requested_energy_kwh (> 0)")
            if self.minimum_service_energy_kwh < 0.0:
                raise ValueError("minimum_service_energy_kwh cannot be negative")
            if self.minimum_service_energy_kwh > self.requested_energy_kwh:
                raise ValueError(
                    f"minimum_service_energy_kwh ({self.minimum_service_energy_kwh}) cannot exceed "
                    f"requested_energy_kwh ({self.requested_energy_kwh})"
                )
        
        # Battery-swap validation
        if self.request_type == ServiceType.BATTERY_SWAP:
            if self.requested_pack_count <= 0:
                raise ValueError("Battery swap request must specify positive integer requested_pack_count (> 0)")
            if self.pack_capacity_kwh <= 0.0:
                raise ValueError("pack_capacity_kwh must be positive")
            if self.minimum_pack_count < 0:
                raise ValueError("minimum_pack_count cannot be negative")
            if self.minimum_pack_count > self.requested_pack_count:
                raise ValueError(
                    f"minimum_pack_count ({self.minimum_pack_count}) cannot exceed "
                    f"requested_pack_count ({self.requested_pack_count})"
                )
        
        # Emergency and Priority Fleet integrity rules
        if self.customer_segment == CustomerSegment.EMERGENCY:
            if self.flexibility_opt_in:
                raise ValueError("EMERGENCY customer requests cannot opt in to demand deferral")
            if self.service_priority != 1:
                self.service_priority = 1
        
        return self


class FlexibilityEnvelope(BaseModel):
    """Deterministic flexibility envelope bounding feasible service shifting."""
    request_id: str
    cluster_id: str
    request_type: ServiceType
    customer_segment: CustomerSegment
    arrival_ts: datetime
    earliest_start_ts: datetime
    deadline_ts: datetime
    
    # Energy metrics
    requested_energy_kwh: float
    minimum_service_energy_kwh: float
    non_shiftable_energy_kwh: float
    flexible_energy_kwh: float
    
    # Discrete pack metrics (battery swap)
    requested_pack_count: Optional[int] = None
    minimum_pack_count: Optional[int] = None
    non_shiftable_pack_count: Optional[int] = None
    flexible_pack_count: Optional[int] = None
    pack_capacity_kwh: Optional[float] = None
    
    # Scheduling boundaries
    eligible_time_slots: list[str] = Field(default_factory=list, description="List of ISO 8601 hour/slot timestamps within envelope")
    max_deferral_minutes: float
    flexibility_opt_in: bool
    is_deferrable: bool
    reason_code: FlexibilityReasonCode
    service_risk_score: float = Field(0.0, ge=0.0, le=1.0, description="Risk index (0=safe, 1=high risk)")
    
    # Metadata
    provenance: str = "SYNTHETIC"
    assumption_reference: str = "configs/assumptions.yaml:customer_flexibility"


class TariffRecommendation(BaseModel):
    """Dynamic tariff recommendation bounded to [0.80x, 1.20x] previous day average."""
    cluster_id: str
    service_type: ServiceType
    timestamp: datetime
    previous_day_average_tariff_inr_per_kwh: float = Field(..., gt=0.0)
    tariff_min_inr_per_kwh: float = Field(..., gt=0.0)
    tariff_max_inr_per_kwh: float = Field(..., gt=0.0)
    raw_tariff_inr_per_kwh: float = Field(..., gt=0.0)
    final_tariff_inr_per_kwh: float = Field(..., gt=0.0)
    clamped: bool
    clamping_direction: str = Field("NONE", description="LOWER_BOUND, UPPER_BOUND, or NONE")
    pricing_factors: dict[str, float] = Field(default_factory=dict)
    adjustment_reasons: list[str] = Field(default_factory=list)
    provenance: str = "ASSUMED_POLICY"


class IncentiveOffer(BaseModel):
    """Separate voluntary incentive offer evaluated against operational benefit."""
    offer_id: str
    request_id: str
    cluster_id: str
    customer_segment: CustomerSegment
    service_type: ServiceType
    
    # Proposed shift parameters
    proposed_shift_kwh: float
    proposed_shift_packs: Optional[int] = None
    proposed_slots: list[str] = Field(default_factory=list)
    
    # Decoupled financial components
    baseline_tariff_inr_per_kwh: float
    effective_tariff_inr_per_kwh: float  # Bounded retail tariff
    incentive_amount_inr: float          # Separate operational incentive payment
    incentive_rate_inr_per_kwh: float
    
    # Acceptance expectations
    expected_acceptance_probability: float = Field(..., ge=0.0, le=1.0)
    expected_accepted_energy_kwh: float
    expected_accepted_packs: Optional[int] = None
    stochastic_realized_acceptance: Optional[bool] = None
    realized_accepted_energy_kwh: Optional[float] = None
    
    # Cost-benefit analysis
    estimated_incentive_cost_inr: float
    estimated_operational_benefit_inr: Optional[float] = None
    net_expected_value_inr: Optional[float] = None
    evaluable: bool = True
    status: str = "RECOMMENDED"
    reason_codes: list[FlexibilityReasonCode] = Field(default_factory=list)
    offer_expiration_ts: datetime
    provenance: str = "ASSUMED_SIMULATION"
