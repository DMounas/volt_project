"""Pydantic schemas for Phase 6 Digital Twin and Rolling MPC API endpoints."""

from typing import Any, Optional
from pydantic import BaseModel, Field

from engine.provenance import Provenance
from engine.twin.schemas import (
    DecisionExplanation,
    DigitalTwinKPIs,
    EBITDAEvaluation,
    ShockScenarioType,
    SimulationPolicy,
)


class SimulationRunRequest(BaseModel):
    """Payload to trigger a closed-loop or benchmark digital twin simulation."""
    scenario_id: str = Field("NORMAL_OPERATION", description="Shock or disturbance scenario identifier")
    policy: SimulationPolicy = Field(
        SimulationPolicy.CLOSED_LOOP_MPC_P50,
        description="Dispatch policy: BAU_BASELINE, OPEN_LOOP_P50, OPEN_LOOP_CVAR, CLOSED_LOOP_MPC_P50, CLOSED_LOOP_MPC_CVAR"
    )
    horizon_hours: int = Field(24, ge=1, le=48, description="Simulation horizon in hours (1-48)")
    clusters: Optional[list[str]] = Field(None, description="Optional target metro clusters (defaults to all 5)")
    seed: int = Field(42, description="Random seed for reproducibility")
    time_limit_per_step: float = Field(25.0, ge=1.0, le=120.0, description="MIP solve timeout per step (seconds)")
    mip_gap: float = Field(0.01, ge=0.001, le=0.10, description="Relative MIP optimality gap tolerance")


class ScenarioItem(BaseModel):
    """Scenario metadata item in catalog."""
    id: str
    name: str
    description: str
    severity: str
    start_hour: int
    duration_hours: int
    affected_clusters: list[str]
    forecast_visibility: str
    multipliers: dict[str, Any]


class SimulationScenariosCatalogResponse(BaseModel):
    """Catalog of all 10 YAML crisis and disturbance scenarios."""
    scenarios: list[ScenarioItem]
    count: int
    provenance: Provenance = Provenance.SYNTHETIC


class SimulationRunResponse(BaseModel):
    """Summary response for an executed simulation run."""
    run_id: str
    scenario_id: str
    policy: SimulationPolicy
    horizon_hours: int
    seed: int
    clusters: list[str]
    kpis: DigitalTwinKPIs
    ebitda: EBITDAEvaluation
    invariants_verified: dict[str, bool]
    provenance: Provenance = Provenance.SYNTHETIC
    disclaimer: str


class SimulationTimelineResponse(BaseModel):
    """Time-series trajectory of states and decisions for an executed run."""
    run_id: str
    scenario_id: str
    policy: SimulationPolicy
    timeline: list[dict[str, Any]]
    provenance: Provenance = Provenance.SYNTHETIC


class SimulationExplainabilityResponse(BaseModel):
    """Step-by-step causality and explainability log."""
    run_id: str
    explanations: list[DecisionExplanation]
    provenance: Provenance = Provenance.SYNTHETIC


class SimulationEventsResponse(BaseModel):
    """Shock and disturbance details for a simulation run."""
    run_id: str
    scenario_id: str
    scenario_details: dict[str, Any]
    provenance: Provenance = Provenance.SYNTHETIC


class PolicyComparisonMetric(BaseModel):
    """Summary metrics for a specific policy variant."""
    policy: str
    service_reliability_pct: float
    energy_loss_pct: float
    renewable_share_pct: float
    total_energy_served_mwh: float
    procurement_cost_inr: float
    retail_revenue_inr: float
    net_operating_contribution_inr: float
    fallback_events_count: int
    ebitda_status: str = "NOT_EVALUABLE"


class SimulationComparisonResponse(BaseModel):
    """Comparative performance across BAU baseline, Open-Loop MILP, and Closed-Loop MPC."""
    run_id: str
    scenario_id: str
    horizon_hours: int
    policies: dict[str, PolicyComparisonMetric]
    cost_saving_mpc_vs_bau_pct: float
    service_uplift_mpc_vs_bau_pct: float
    loss_reduction_mpc_vs_bau_pct: float
    ebitda_disclosure: EBITDAEvaluation
    provenance: Provenance = Provenance.SYNTHETIC


class MPCStatusResponse(BaseModel):
    """Operational status and telemetry of the MPC controller and solver engine."""
    controller_status: str = "HEALTHY"
    preferred_solver: str
    available_solvers: list[str]
    default_horizon_hours: int = 24
    control_step_hours: int = 1
    receding_horizon: bool = True
    invariants_enforced: list[str]
    timestamp: str
