"""Pydantic schemas and typed data structures for the MILP optimization engine.

Maintains strict provenance tracking and dimensional contracts (MW, MWh, kWh, INR).
"""

from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field
from engine.provenance import Provenance


class OptimizationMode(str, Enum):
    """Execution mode for the optimization engine."""
    BAU_BASELINE = "BAU_BASELINE"
    DETERMINISTIC_P50 = "DETERMINISTIC_P50"
    RISK_AWARE_CVAR = "RISK_AWARE_CVAR"


class SolverStatus(str, Enum):
    """Solver termination and solution status."""
    OPTIMAL = "OPTIMAL"
    FEASIBLE_GAP = "FEASIBLE_GAP"
    INFEASIBLE = "INFEASIBLE"
    TIME_LIMIT = "TIME_LIMIT"
    SOLVER_UNAVAILABLE = "SOLVER_UNAVAILABLE"
    ERROR = "ERROR"
    FALLBACK_HEURISTIC = "FALLBACK_HEURISTIC"


class DynamicTariffTier(str, Enum):
    """Permitted regulatory tariff multiplier tiers."""
    TIER_80 = "0.80x"
    TIER_90 = "0.90x"
    TIER_100 = "1.00x"
    TIER_110 = "1.10x"
    TIER_120 = "1.20x"


# =====================================================================
# Inputs Schemas
# =====================================================================

class BESSInitialState(BaseModel):
    """Initial state for stationary BESS."""
    capacity_mwh: float = Field(60.0, description="Installed BESS energy capacity per cluster (MWh)")
    max_charge_power_mw: float = Field(30.0, description="Max charging power rating (MW)")
    max_discharge_power_mw: float = Field(30.0, description="Max discharging power rating (MW)")
    initial_soc_mwh: float = Field(30.0, description="Starting SOC at t=0 (MWh)")
    min_reserve_mwh: float = Field(3.0, description="Mandatory 5% emergency reserve (MWh)")
    max_soc_mwh: float = Field(54.0, description="Maximum operational SOC (90% capacity) (MWh)")
    charge_efficiency: float = Field(0.93, description="AC-to-DC charge efficiency")
    discharge_efficiency: float = Field(0.93, description="DC-to-AC discharge efficiency")
    degradation_cost_inr_per_mwh: float = Field(1250.0, description="Battery wear cost proxy (INR/MWh)")


class SwapInitialState(BaseModel):
    """Initial state for swappable battery pack inventory."""
    total_packs: int = Field(24000, description="Total cluster pack inventory count")
    ready_packs: int = Field(16800, description="Ready packs with SOC >= 90% at t=0 (70% fleet)")
    charging_packs: int = Field(4800, description="Packs currently in charging bays at t=0 (20% fleet)")
    depleted_packs: int = Field(2400, description="Depleted packs waiting for charging at t=0 (10% fleet)")
    min_reserve_packs: int = Field(1200, description="Mandatory 5% ready pack reserve (1,200 packs)")
    pack_nominal_kwh: float = Field(2.5, description="Nominal pack energy capacity (kWh)")
    pack_usable_kwh: float = Field(2.25, description="Usable energy delivered per swap (kWh)")
    charger_bay_power_mw: float = Field(96.0, description="Installed swap bay charger power (MW)")
    charge_efficiency: float = Field(0.90, description="Pack recharge efficiency")
    charge_duration_hours: int = Field(1, description="Standard charging turnaround duration (hours)")


class ClusterHorizonInput(BaseModel):
    """24-hour input vectors for a single metro cluster."""
    cluster_id: str
    hours: list[int] = Field(default_factory=lambda: list(range(24)))
    fast_charge_demand_mwh: list[float]
    swap_requests_count: list[int]
    swap_energy_mwh: list[float]
    solar_available_mwh: list[float]
    wind_available_mwh: list[float]
    discom_tariff_inr_per_mwh: list[float]
    iex_dam_price_inr_per_mwh: list[float]
    iex_procurement_cap_mw: list[float]
    previous_day_avg_tariff_inr_per_kwh: float = 11.20
    bess_state: BESSInitialState = Field(default_factory=BESSInitialState)
    swap_state: SwapInitialState = Field(default_factory=SwapInitialState)


class ScenarioWeight(BaseModel):
    """Scenario identifier with probability weight."""
    scenario_id: str
    probability: float
    description: str = ""
    provenance: Provenance = Provenance.SYNTHETIC


# =====================================================================
# Decision & Schedule Schemas
# =====================================================================

class HourlyClusterDecision(BaseModel):
    """Decisions and physical state variables for a single cluster and hour."""
    cluster_id: str
    hour: int
    # Procurement (MW = MWh for 1-hour interval)
    discom_mw: float
    iex_mw: float
    renewable_used_mwh: float
    renewable_curtailed_mwh: float
    # Stationary BESS
    bess_charge_mw: float
    bess_discharge_mw: float
    bess_soc_mwh: float
    bess_reserve_compliant: bool = True
    # Battery Swapping
    swap_packs_served: int
    swap_packs_charging: int
    swap_packs_ready: int
    swap_packs_depleted: int
    swap_charge_power_mw: float
    swap_reserve_compliant: bool = True
    # Fast Charging & Flexibility
    fc_demand_requested_mwh: float
    fc_demand_served_mwh: float
    fc_demand_shifted_mwh: float
    fc_unserved_slack_mwh: float = 0.0
    # Tariffs & Incentives
    selected_tariff_tier: DynamicTariffTier
    tariff_inr_per_kwh: float
    tariff_revenue_inr: float
    incentive_spend_inr: float
    # Losses & Headroom
    losses_mwh: float
    power_headroom_mw: float
    power_headroom_compliant: bool = True
    # Binding constraints & causality
    binding_constraints: list[str] = Field(default_factory=list)


class ClusterDailySchedule(BaseModel):
    """Complete 24-hour schedule for one cluster."""
    cluster_id: str
    hourly_decisions: list[HourlyClusterDecision]
    total_energy_requested_mwh: float
    total_energy_served_mwh: float
    service_reliability_pct: float
    total_discom_cost_inr: float
    total_iex_cost_inr: float
    total_renewable_cost_inr: float
    total_bess_degradation_cost_inr: float
    total_customer_incentive_inr: float
    total_retail_revenue_inr: float
    net_operating_cost_inr: float
    renewable_utilization_pct: float
    energy_loss_pct: float


# =====================================================================
# Global Optimization Output & KPIs
# =====================================================================

class OptimizationKPIs(BaseModel):
    """High-level system KPIs across all five clusters."""
    service_reliability_pct: float = Field(..., description="Energy served / energy requested (%)")
    fast_charge_fill_rate_pct: float
    swap_pack_fill_rate_pct: float
    energy_loss_pct: float = Field(..., description="Energy losses / total throughput (%)")
    renewable_share_pct: float = Field(..., description="Renewable used / total procurement (%)")
    power_capacity_headroom_mw: float = Field(..., description="Minimum power headroom preserved (MW)")
    power_headroom_reserve_compliant: bool
    bess_emergency_reserve_compliant: bool
    swap_emergency_reserve_compliant: bool
    deadline_violations_count: int
    unserved_critical_mwh: float
    total_energy_requested_mwh: float
    total_energy_served_mwh: float
    total_procurement_cost_inr: float
    total_retail_revenue_inr: float
    total_flexibility_incentive_inr: float
    total_degradation_cost_inr: float
    net_operating_cost_inr: float
    cvar_tail_risk_cost_inr: float
    ebitda_operating_margin_pct: Optional[float] = None
    ebitda_status: str = Field("EBITDA_PROXY", description="EBITDA status (proxy or not evaluable without full corporate overhead)")


class SolverMetadata(BaseModel):
    """Metadata recorded by the optimization solver."""
    solver_name: str
    solver_version: str
    solver_status: SolverStatus
    termination_condition: str
    solve_time_seconds: float
    objective_value: float
    best_bound: Optional[float] = None
    mip_gap: Optional[float] = None
    iterations: Optional[int] = None
    variables_count: int = 0
    constraints_count: int = 0
    is_fallback: bool = False
    infeasibility_reasons: list[str] = Field(default_factory=list)


class OptimizationResult(BaseModel):
    """Master response payload for an optimization run."""
    run_id: str
    mode: OptimizationMode
    timestamp: str
    horizon_hours: int = 24
    clusters: list[str]
    scenarios_evaluated: list[str]
    solver_metadata: SolverMetadata
    kpis: OptimizationKPIs
    cluster_schedules: dict[str, ClusterDailySchedule]
    provenance: Provenance = Provenance.SYNTHETIC
    disclaimer: str = (
        "Decision-support simulation model output under rolling MPC assumptions. "
        "Not a live grid-control dispatch or binding IEX market bidding gateway."
    )
