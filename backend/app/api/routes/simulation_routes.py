"""FastAPI endpoints for Phase 6 Digital Twin and Closed-Loop Rolling MPC."""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query

from backend.app.schemas.simulation_schemas import (
    MPCStatusResponse,
    SimulationComparisonResponse,
    SimulationEventsResponse,
    SimulationExplainabilityResponse,
    SimulationRunRequest,
    SimulationRunResponse,
    SimulationScenariosCatalogResponse,
    SimulationTimelineResponse,
)
from backend.app.services.simulation_service import SimulationService

router = APIRouter(tags=["Digital Twin Simulation & MPC"])
service = SimulationService.get_instance()


@router.get(
    "/simulation/scenarios",
    response_model=SimulationScenariosCatalogResponse,
    summary="List available crisis and disturbance scenarios",
)
def list_scenarios():
    """Retrieve catalog of all 10 YAML crisis and disturbance scenarios."""
    return service.list_scenarios()


@router.post(
    "/simulation/run",
    response_model=SimulationRunResponse,
    summary="Execute a closed-loop or benchmark simulation run",
)
def run_simulation(request: SimulationRunRequest):
    """Run rolling MPC or benchmark simulation across specified horizon and scenario."""
    return service.run_simulation(request)


@router.get(
    "/simulation/latest",
    response_model=SimulationRunResponse,
    summary="Get most recent simulation run summary",
)
def get_latest_run():
    """Retrieve summary of the latest executed simulation run."""
    return service.get_latest_run()


@router.get(
    "/simulation/runs/{run_id}",
    response_model=SimulationRunResponse,
    summary="Get simulation summary by run_id",
)
def get_run(run_id: str):
    """Retrieve KPIs, reserves, and accounting summary for a specific run."""
    run = service.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Simulation run '{run_id}' not found")
    return run


@router.get(
    "/simulation/runs/{run_id}/timeline",
    response_model=SimulationTimelineResponse,
    summary="Get hourly dispatch and state trajectories",
)
def get_timeline(run_id: str):
    """Retrieve step-by-step physical state and control action trajectory."""
    timeline = service.get_timeline(run_id)
    if not timeline:
        raise HTTPException(status_code=404, detail=f"Timeline for run '{run_id}' not found")
    return timeline


@router.get(
    "/simulation/runs/{run_id}/explainability",
    response_model=SimulationExplainabilityResponse,
    summary="Get decision causality and explainability logs",
)
def get_explainability(run_id: str):
    """Retrieve step-by-step causality, binding constraints, and reasonings."""
    expl = service.get_explainability(run_id)
    if not expl:
        raise HTTPException(status_code=404, detail=f"Explainability log for run '{run_id}' not found")
    return expl


@router.get(
    "/simulation/runs/{run_id}/events",
    response_model=SimulationEventsResponse,
    summary="Get shock and disturbance event configuration",
)
def get_events(run_id: str):
    """Retrieve disturbance details and multipliers applied in run."""
    events = service.get_events(run_id)
    if not events:
        raise HTTPException(status_code=404, detail=f"Events for run '{run_id}' not found")
    return events


@router.get(
    "/simulation/runs/{run_id}/comparison",
    response_model=SimulationComparisonResponse,
    summary="Get comparative evaluation across dispatch policies",
)
def get_comparison(
    run_id: str,
    scenario_id: str = Query("NORMAL_OPERATION", description="Scenario identifier"),
    horizon_hours: int = Query(12, ge=1, le=24, description="Horizon length for comparison"),
    seed: int = Query(42, description="Random seed"),
):
    """Compare performance across BAU baseline, Open-Loop MILP, and Closed-Loop MPC."""
    return service.get_comparison(scenario_id=scenario_id, horizon_hours=horizon_hours, seed=seed)


@router.get(
    "/mpc/status",
    response_model=MPCStatusResponse,
    summary="Get MPC controller operational health and solver status",
)
def get_mpc_status():
    """Retrieve solver telemetry, receding horizon configuration, and invariant protections."""
    return service.get_mpc_status()
