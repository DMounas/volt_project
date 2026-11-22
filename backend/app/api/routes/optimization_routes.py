"""FastAPI router for Phase 5 MILP Optimization endpoints.

Exposes:
- POST /api/v1/optimization/run: Execute selected policy and horizon
- GET  /api/v1/optimization/latest: Latest optimization schedule and solver status
- GET  /api/v1/optimization/summary: Consolidated KPIs, objective, and cluster metrics
- GET  /api/v1/optimization/decisions: 24-hour decision trajectories filtered by cluster
- GET  /api/v1/optimization/compare: Apples-to-apples comparison across BAU, Det P50, and CVaR
- GET  /api/v1/optimization/scenarios: Scenarios catalog and probability weights
"""

from fastapi import APIRouter, HTTPException, Query, status
from backend.app.schemas.optimization_schemas import (
    OptimizationCompareResponse,
    OptimizationDecisionsResponse,
    OptimizationRunRequest,
    OptimizationRunResponse,
    OptimizationScenariosCatalogResponse,
    OptimizationSummaryResponse,
)
from backend.app.services.optimization_service import OptimizationService

router = APIRouter(prefix="/optimization", tags=["Phase 5: MILP Optimization"])


@router.post(
    "/run",
    response_model=OptimizationRunResponse,
    status_code=status.HTTP_200_OK,
    summary="Run MILP Energy & Flexibility Optimization",
    description="Executes Pyomo MILP optimization (BAU / Deterministic P50 / Risk-Aware CVaR) with HiGHS solver.",
)
def run_optimization(request: OptimizationRunRequest) -> OptimizationRunResponse:
    try:
        service = OptimizationService.get_instance()
        return service.run_optimization(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Optimization failed: {str(e)}")


@router.get(
    "/latest",
    response_model=OptimizationRunResponse,
    summary="Get Latest Optimization Result",
    description="Retrieves the most recent optimization result, solver metadata, and KPI metrics.",
)
def get_latest_optimization() -> OptimizationRunResponse:
    try:
        service = OptimizationService.get_instance()
        return service.get_latest()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve latest optimization: {str(e)}")


@router.get(
    "/summary",
    response_model=OptimizationSummaryResponse,
    summary="Get Optimization Summary & KPIs",
    description="Retrieves consolidated system KPIs, solver gap, and cluster-level summaries.",
)
def get_optimization_summary() -> OptimizationSummaryResponse:
    try:
        service = OptimizationService.get_instance()
        return service.get_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve summary: {str(e)}")


@router.get(
    "/decisions",
    response_model=OptimizationDecisionsResponse,
    summary="Get Hourly Dispatch Decisions",
    description="Retrieves 24-hour hourly decision variables (MW, MWh, SOC, tariffs, packs) for a specific cluster.",
)
def get_hourly_decisions(
    cluster_id: str = Query("delhi_ncr", description="Cluster ID (delhi_ncr, mumbai_mmr, etc.)"),
) -> OptimizationDecisionsResponse:
    try:
        service = OptimizationService.get_instance()
        return service.get_decisions(cluster_id=cluster_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve decisions: {str(e)}")


@router.get(
    "/compare",
    response_model=OptimizationCompareResponse,
    summary="Compare BAU vs. Deterministic vs. Risk-Aware Policies",
    description="Provides apples-to-apples performance comparisons across policies on identical scenario conditions.",
)
def compare_dispatch_policies() -> OptimizationCompareResponse:
    try:
        service = OptimizationService.get_instance()
        return service.get_comparison()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to compute policy comparisons: {str(e)}")


@router.get(
    "/scenarios",
    response_model=OptimizationScenariosCatalogResponse,
    summary="Get Optimization Scenarios Catalog",
    description="Retrieves catalogue of supported disturbance scenarios and probability weights for CVaR.",
)
def get_scenarios_catalog() -> OptimizationScenariosCatalogResponse:
    try:
        service = OptimizationService.get_instance()
        return service.get_scenarios()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve scenarios catalog: {str(e)}")
