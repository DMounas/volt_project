"""Digital Twin typed state schemas, invariants, and step models for Phase 6.

All fields carry explicit units (MW, MWh, kWh, INR, packs, pct) and provenance
tags (SYNTHETIC, ASSUMED, OBSERVED). Follows the case study specifications:
- 5 metro clusters: Delhi NCR, Mumbai MMR, Bengaluru, Hyderabad, Chennai
- 240 MW grid import capacity per cluster (1,200 MW network-wide)
- 60 MWh stationary BESS per cluster with 5% emergency reserve (>= 3.0 MWh)
- 24,000 swappable battery packs per cluster with 5% ready reserve (>= 1,200 packs)
- 5% power capacity headroom reserve (>= 12.0 MW per cluster, >= 60.0 MW network)
- Zero inter-city electricity transfer
- EBITDA reported as NOT_EVALUABLE when corporate OpEx is unavailable.
"""

from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field

from engine.provenance import Provenance


class ShockScenarioType(str, Enum):
    """Catalog of disturbance and shock scenarios."""
    NORMAL_OPERATION = "NORMAL_OPERATION"
    EVENING_DEMAND_SURGE = "EVENING_DEMAND_SURGE"
    SOLAR_CLOUD_DROP = "SOLAR_CLOUD_DROP"
    WIND_LULL = "WIND_LULL"
    IEX_PRICE_SPIKE = "IEX_PRICE_SPIKE"
    GRID_IMPORT_RESTRICTION = "GRID_IMPORT_RESTRICTION"
    SWAP_INVENTORY_SHORTAGE = "SWAP_INVENTORY_SHORTAGE"
    HEATWAVE_COMPOUND = "HEATWAVE_COMPOUND"
    COMBINED_MULTI_CITY_CRISIS = "COMBINED_MULTI_CITY_CRISIS"
    RECOVERY_AFTER_CRISIS = "RECOVERY_AFTER_CRISIS"


class SimulationPolicy(str, Enum):
    """Control and optimization policy variants with audited comparison semantics."""
    # Canonical audited policy semantics
    CALIBRATED_BAU = "CALIBRATED_BAU"              # Uncoordinated operations simulator (downtime & balking)
    FALLBACK_HEURISTIC = "FALLBACK_HEURISTIC"      # Rule-based safe scheduler when solver unavailable
    OPEN_LOOP_MILP = "OPEN_LOOP_MILP"              # Open-loop 24-hour MILP optimization schedule
    CLOSED_LOOP_MPC = "CLOSED_LOOP_MPC"            # Receding-horizon MPC (applies t=0, re-optimizes)

    # Specific scenario / backward-compatible variants
    BAU_BASELINE = "BAU_BASELINE"
    OPEN_LOOP_P50 = "OPEN_LOOP_P50"
    OPEN_LOOP_CVAR = "OPEN_LOOP_CVAR"
    CLOSED_LOOP_MPC_P50 = "CLOSED_LOOP_MPC_P50"
    CLOSED_LOOP_MPC_CVAR = "CLOSED_LOOP_MPC_CVAR"


# =====================================================================
# State Models
# =====================================================================

class EnergyState(BaseModel):
    """Energy and network physical state for a cluster at a single time step."""
    timestamp: str = Field(..., description="Timestamp in Asia/Kolkata ISO 8601")
    cluster_id: str = Field(..., description="Metro cluster identifier")
    
    # Grid & Market
    grid_import_cap_mw: float = Field(240.0, description="Feeder import capacity rating (MW)")
    grid_import_actual_mw: float = Field(..., description="Actual power drawn from grid (MW)")
    discom_import_mw: float = Field(..., description="Baseload DISCOM power drawn (MW)")
    iex_import_mw: float = Field(..., description="Merchant IEX market power drawn (MW)")
    discom_tariff_inr_per_mwh: float = Field(..., description="Current DISCOM tariff (INR/MWh)")
    iex_price_inr_per_mwh: float = Field(..., description="Current IEX clearing price (INR/MWh)")
    
    # Renewable Generation
    solar_available_mwh: float = Field(..., description="Available solar generation (MWh)")
    wind_available_mwh: float = Field(..., description="Available wind generation (MWh)")
    renewable_used_mwh: float = Field(..., description="Renewable energy dispatched into load/BESS (MWh)")
    renewable_curtailed_mwh: float = Field(..., description="Renewable energy curtailed (MWh)")
    
    # Fast Charging Load
    fast_charge_demand_mwh: float = Field(..., description="Realized fast-charge demand arrival (MWh)")
    fast_charge_delivered_mwh: float = Field(..., description="Delivered fast-charge energy (MWh)")
    fast_charge_shifted_mwh: float = Field(0.0, description="Flexible demand deferred into window (MWh)")
    fast_charge_unserved_mwh: float = Field(0.0, description="Unserved fast-charge demand (MWh)")
    
    # Stationary BESS
    bess_soc_mwh: float = Field(..., description="Stationary BESS stored energy (MWh)")
    bess_soc_pct: float = Field(..., description="BESS state of charge (percentage)")
    bess_charge_mw: float = Field(0.0, description="BESS charging power (MW)")
    bess_discharge_mw: float = Field(0.0, description="BESS discharging power (MW)")
    bess_min_reserve_mwh: float = Field(3.0, description="Mandatory 5% emergency reserve (MWh)")
    bess_usable_capacity_mwh: float = Field(60.0, description="Installed BESS capacity (MWh)")
    bess_reserve_compliant: bool = Field(True, description="True if SOC >= 3.0 MWh")
    
    # System Losses & Auxiliary
    charger_conversion_loss_mwh: float = Field(0.0, description="AC-DC fast-charger conversion losses (MWh)")
    swap_charging_loss_mwh: float = Field(0.0, description="Pack charging conversion and thermal losses (MWh)")
    bess_turnaround_loss_mwh: float = Field(0.0, description="BESS charge/discharge conversion losses (MWh)")
    auxiliary_load_mwh: float = Field(2.5, description="Station auxiliary and cooling load (MWh)")
    distribution_loss_mwh: float = Field(..., description="Local distribution and cabling losses (MWh)")
    total_losses_mwh: float = Field(..., description="Total system energy losses this interval (MWh)")
    
    # Headroom Reserve
    power_headroom_mw: float = Field(..., description="Unused import capacity headroom (MW)")
    headroom_reserve_compliant: bool = Field(True, description="True if headroom >= 12.0 MW (5%)")
    
    # Inter-city isolation
    inter_city_transfer_mw: float = Field(0.0, description="Inter-city electricity transfer (strictly 0.0 MW)")
    
    provenance: Provenance = Field(Provenance.SYNTHETIC, description="Data provenance label")


class SwapInventoryState(BaseModel):
    """Swappable battery pack discrete inventory state for a cluster."""
    total_packs: int = Field(24000, description="Total physical pack inventory in cluster")
    ready_packs: int = Field(..., description="Ready packs with SOC >= 90% available for swap")
    charging_packs: int = Field(..., description="Packs currently in replenishment bays")
    depleted_packs: int = Field(..., description="Depleted packs awaiting charging slot")
    unavailable_packs: int = Field(0, description="Packs in maintenance or degradation retirement")
    
    # Pack Specs
    pack_nominal_kwh: float = Field(2.5, description="Nominal pack energy capacity (kWh)")
    pack_usable_kwh: float = Field(2.25, description="Usable energy delivered per swap (kWh)")
    charger_bay_power_mw: float = Field(96.0, description="Installed bay charger capacity (MW)")
    
    # Service Throughput
    swap_requests_count: int = Field(..., description="Arrived swap requests in current interval")
    swap_packs_served: int = Field(..., description="Packs successfully dispensed to drivers")
    swap_energy_delivered_mwh: float = Field(..., description="Energy delivered via swapping (MWh)")
    swap_packs_unserved: int = Field(0, description="Balked or unserved swap requests")
    swap_unserved_mwh: float = Field(0.0, description="Unserved energy equivalent (MWh)")
    
    # Invariant Checks
    min_reserve_packs: int = Field(1200, description="Mandatory 5% ready pack reserve (1,200 packs)")
    reserve_compliant: bool = Field(True, description="True if ready_packs >= 1,200")
    conservation_valid: bool = Field(
        True,
        description="True if ready + charging + depleted + unavailable == total_packs"
    )
    
    provenance: Provenance = Field(Provenance.SYNTHETIC, description="Data provenance label")


class CustomerState(BaseModel):
    """Customer cohort queue and service delivery state."""
    active_requests_count: int = Field(..., description="Number of customer requests active")
    total_requested_mwh: float = Field(..., description="Total requested energy (MWh)")
    total_served_mwh: float = Field(..., description="Total served energy (MWh)")
    total_deferred_mwh: float = Field(0.0, description="Flexible energy deferred to future intervals (MWh)")
    total_unserved_mwh: float = Field(0.0, description="Unserved demand (MWh)")
    
    # Priority & Emergency Integrity
    emergency_served_pct: float = Field(100.0, description="Emergency service delivery rate (must be 100%)")
    priority_served_pct: float = Field(100.0, description="Priority commercial fleet delivery rate")
    deadline_violations_count: int = Field(0, description="Customer deadline violations count")
    
    # Queue Latency
    mean_waiting_time_minutes: float = Field(0.0, description="Average customer wait time (minutes)")
    p95_waiting_time_minutes: float = Field(0.0, description="95th percentile wait time (minutes)")
    max_waiting_time_minutes: float = Field(0.0, description="Maximum wait time (minutes)")
    
    provenance: Provenance = Field(Provenance.SYNTHETIC, description="Data provenance label")


class FinancialLedgerState(BaseModel):
    """Financial accounting ledgers for procurement, revenue, and incentives."""
    discom_cost_inr: float = Field(..., description="DISCOM electricity procurement expense (INR)")
    iex_cost_inr: float = Field(..., description="IEX merchant market procurement expense (INR)")
    renewable_cost_inr: float = Field(..., description="Contracted renewable PPA expense (INR)")
    procurement_cost_inr: float = Field(..., description="Total wholesale procurement expense (INR)")
    
    bess_degradation_cost_inr: float = Field(..., description="BESS cycling degradation expense (INR)")
    retail_tariff_revenue_inr: float = Field(..., description="Retail dynamic tariff revenue (INR)")
    flexibility_incentive_inr: float = Field(..., description="Customer flexibility incentive payouts (INR)")
    
    # Unserved demand penalty is an optimization penalty term, not cash accounting expense
    unserved_demand_penalty_inr: float = Field(
        0.0,
        description="Optimization slack penalty term (INR); excluded from cash ledger"
    )
    
    net_operating_contribution_inr: float = Field(
        ...,
        description="Retail Revenue - Procurement - Degradation - Flexibility Incentives (INR)"
    )
    
    provenance: Provenance = Field(Provenance.SYNTHETIC, description="Data provenance label")


class EBITDAEvaluation(BaseModel):
    """Explicit disclosure on why EBITDA cannot be calculated without corporate OpEx."""
    status: str = Field("NOT_EVALUABLE", description="EBITDA calculation feasibility status")
    ebitda_margin_pct: Optional[float] = Field(None, description="EBITDA margin (None when not evaluable)")
    missing_components: list[str] = Field(
        default_factory=lambda: [
            "fixed_operating_costs",
            "station_land_leases",
            "corporate_sga",
            "depreciation_schedule",
            "debt_service_interest",
        ],
        description="Missing corporate expenditure components required for GAAP/IndAS EBITDA"
    )
    explanation: str = Field(
        "Full corporate EBITDA cannot be evaluated without corporate overhead, facility leases, "
        "SG&A, and asset depreciation schedules. Net operating contribution is reported separately.",
        description="Audit disclosure note"
    )
    provenance: Provenance = Field(Provenance.ASSUMED, description="Provenance classification")


class OperationalTwinState(BaseModel):
    """Complete snapshot of a single cluster digital twin at time t."""
    timestamp: str
    cluster_id: str
    hour: int
    energy: EnergyState
    swap: SwapInventoryState
    customer: CustomerState
    financials: FinancialLedgerState
    ebitda: EBITDAEvaluation = Field(default_factory=EBITDAEvaluation)
    provenance: Provenance = Field(Provenance.SYNTHETIC, description="Data provenance label")


# =====================================================================
# Decision, Action & Explanation Schemas
# =====================================================================

class StepAction(BaseModel):
    """Control action applied at t=0 of the receding horizon."""
    hour: int
    cluster_id: str
    discom_mw: float
    iex_mw: float
    renewable_used_mwh: float
    bess_charge_mw: float
    bess_discharge_mw: float
    swap_packs_to_charge: int
    fc_served_mwh: float
    selected_tariff_tier: str
    tariff_inr_per_kwh: float
    flexibility_incentive_offered_inr: float
    provenance: Provenance = Field(Provenance.SYNTHETIC, description="Data provenance label")


class DecisionExplanation(BaseModel):
    """Structured explainability record for a single control step."""
    timestamp: str
    hour: int
    cluster_id: str
    detected_operating_condition: str
    binding_constraints: list[str]
    procurement_choice_reason: str
    storage_dispatch_reason: str
    flexible_demand_decision: str
    tariff_recommendation_reason: str
    headroom_reserve_status: str
    cost_decomposition: dict[str, float]
    solver_status: str
    is_fallback: bool = False
    fallback_reason: Optional[str] = None
    provenance: Provenance = Field(Provenance.SYNTHETIC, description="Data provenance label")


# =====================================================================
# Simulation Run Results & KPI Schemas
# =====================================================================

class DigitalTwinKPIs(BaseModel):
    """Consolidated performance KPIs across all clusters and simulation horizon."""
    # Service
    service_reliability_pct: float = Field(..., description="Energy served / energy requested (%)")
    fast_charge_fill_rate_pct: float
    swap_pack_fill_rate_pct: float
    swap_energy_fill_rate_pct: float
    emergency_service_violations_count: int = 0
    priority_service_violations_count: int = 0
    deadline_violations_count: int = 0
    mean_waiting_time_minutes: float = 0.0
    p95_waiting_time_minutes: float = 0.0
    max_waiting_time_minutes: float = 0.0
    deferred_energy_eventually_served_mwh: float
    deferred_energy_unserved_mwh: float = 0.0
    
    # Energy
    total_energy_requested_mwh: float
    total_energy_served_mwh: float
    total_discom_energy_mwh: float
    total_iex_energy_mwh: float
    total_renewable_energy_mwh: float
    renewable_utilization_pct: float
    renewable_curtailment_mwh: float
    bess_throughput_mwh: float
    bess_final_soc_mwh: float
    swap_final_ready_packs: int
    total_losses_mwh: float
    energy_loss_pct: float = Field(..., description="Total losses / gross input (%)")
    energy_balance_residual_mwh: float = Field(0.0, description="Numerical energy balance residual (MWh)")
    reserve_violations_count: int = Field(0, description="Must be 0 for valid simulation")
    
    # Economics
    procurement_cost_inr: float
    retail_tariff_revenue_inr: float
    flexibility_incentive_inr: float
    bess_degradation_cost_inr: float
    net_operating_contribution_inr: float
    ebitda_status: str = Field("NOT_EVALUABLE", description="EBITDA status (NOT_EVALUABLE)")
    
    # Robustness & Computation
    forecast_mae_demand_mwh: float = 0.0
    forecast_mae_renewable_mwh: float = 0.0
    forecast_mae_price_inr: float = 0.0
    mean_solve_time_seconds: float
    max_solve_time_seconds: float
    fallback_events_count: int = 0
    cvar_tail_risk_cost_inr: float = 0.0


class SimulationRunSummary(BaseModel):
    """End-to-end response payload for a closed-loop or benchmark simulation run."""
    run_id: str
    scenario_id: str
    policy: SimulationPolicy
    horizon_hours: int = 24
    seed: int = 42
    clusters: list[str]
    kpis: DigitalTwinKPIs
    ebitda: EBITDAEvaluation = Field(default_factory=EBITDAEvaluation)
    timeline: list[dict[str, Any]] = Field(default_factory=list, description="Hourly states and actions")
    explanations: list[DecisionExplanation] = Field(default_factory=list)
    invariants_verified: dict[str, bool] = Field(default_factory=dict)
    provenance: Provenance = Field(Provenance.SYNTHETIC, description="Data provenance label")
    disclaimer: str = Field(
        "Decision-support simulation model output under rolling MPC assumptions. "
        "Not a live grid-control dispatch or binding IEX market bidding gateway.",
        description="Mandatory compliance disclaimer"
    )
