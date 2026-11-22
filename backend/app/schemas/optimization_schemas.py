"""Pydantic schemas for the Phase 5 Optimization REST API.

Enforces:
- Strict unit tagging and provenance tracking
- Decoupled retail tariff revenue from flexibility incentives
- Transparent solver metadata and infeasibility diagnostics
"""

from typing import Any, Optional
from pydantic import BaseModel, Field
from engine.optimization.schemas import (
    ClusterDailySchedule,
    HourlyClusterDecision,
    OptimizationKPIs,
    OptimizationMode,
    ScenarioWeight,
    SolverMetadata,
    SolverStatus,
)
from engine.provenance import Provenance


class OptimizationRunRequest(BaseModel):
    """Payload to trigger an optimization run."""
    mode: OptimizationMode = Field(OptimizationMode.DETERMINISTIC_P50, description="Optimization policy mode")
    clusters: Optional[list[str]] = Field(None, description="Subset of clusters (defaults to all 5)")
    time_limit_seconds: Optional[float] = Field(30.0, description="Solver time limit (seconds)")
    mip_gap: Optional[float] = Field(0.01, description="Relative MIP gap tolerance")
    seed: int = Field(42, description="Random seed for reproducible scenario disturbances")


class OptimizationRunResponse(BaseModel):
    """Response payload for an optimization run."""
    run_id: str
    mode: OptimizationMode
    timestamp: str
    clusters: list[str]
    scenarios_evaluated: list[str]
    solver_metadata: SolverMetadata
    kpis: OptimizationKPIs
    provenance: Provenance = Provenance.SYNTHETIC
    disclaimer: str


class OptimizationSummaryResponse(BaseModel):
    """Consolidated KPIs and high-level performance metrics."""
    run_id: str
    mode: OptimizationMode
    solver_status: SolverStatus
    solve_time_seconds: float
    mip_gap: Optional[float]
    objective_value: float
    kpis: OptimizationKPIs
    cluster_summaries: dict[str, dict[str, Any]]
    provenance: Provenance = Provenance.SYNTHETIC


class OptimizationDecisionsResponse(BaseModel):
    """Hourly decisions for a specific cluster."""
    cluster_id: str
    mode: OptimizationMode
    decisions: list[HourlyClusterDecision]
    provenance: Provenance = Provenance.SYNTHETIC


class OptimizationCompareResponse(BaseModel):
    """Apples-to-apples performance comparison across BAU, Deterministic, and Risk-Aware policies."""
    comparison_summary: dict[str, Any]
    invariants_verified: dict[str, bool]
    provenance: Provenance = Provenance.SYNTHETIC


class ScenarioCatalogItem(BaseModel):
    """Scenario description and default probability."""
    scenario_id: str
    probability: float
    description: str
    provenance: Provenance = Provenance.SYNTHETIC


class OptimizationScenariosCatalogResponse(BaseModel):
    """Catalog of available scenario profiles."""
    scenarios: list[ScenarioCatalogItem]
    alpha_confidence: float = 0.95
    provenance: Provenance = Provenance.SYNTHETIC
