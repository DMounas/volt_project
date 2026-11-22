"""Optimization Service providing business logic and caching for Phase 5 REST endpoints.

Coordinates:
- Ingestion and execution of MILP orchestration runs
- Policy comparison across BAU, Deterministic P50, and Risk-Aware CVaR
- Hourly decisions retrieval filtered by cluster
- Scenarios catalog retrieval
"""

from typing import Any, Optional
from backend.app.schemas.optimization_schemas import (
    OptimizationCompareResponse,
    OptimizationDecisionsResponse,
    OptimizationRunRequest,
    OptimizationRunResponse,
    OptimizationScenariosCatalogResponse,
    OptimizationSummaryResponse,
    ScenarioCatalogItem,
)
from engine.optimization.comparison import PolicyComparisonEngine
from engine.optimization.pipeline import (
    DEFAULT_CLUSTERS,
    DEFAULT_SCENARIOS,
    OptimizationPipeline,
)
from engine.optimization.schemas import OptimizationMode, OptimizationResult
from engine.provenance import Provenance


class OptimizationService:
    """Singleton service wrapping the optimization engine and comparison evaluator."""

    _instance: Optional["OptimizationService"] = None

    def __init__(self):
        self.pipeline = OptimizationPipeline()
        self.comparison_engine = PolicyComparisonEngine()
        self._latest_result: Optional[OptimizationResult] = None
        self._comparison_cache: Optional[dict[str, Any]] = None

    @classmethod
    def get_instance(cls) -> "OptimizationService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def run_optimization(self, request: OptimizationRunRequest) -> OptimizationRunResponse:
        """Run optimization for requested mode and clusters."""
        result = self.pipeline.run_optimization(
            mode=request.mode,
            clusters=request.clusters or DEFAULT_CLUSTERS,
            time_limit_seconds=request.time_limit_seconds,
            mip_gap=request.mip_gap,
            seed=request.seed,
        )
        self._latest_result = result

        return OptimizationRunResponse(
            run_id=result.run_id,
            mode=result.mode,
            timestamp=result.timestamp,
            clusters=result.clusters,
            scenarios_evaluated=result.scenarios_evaluated,
            solver_metadata=result.solver_metadata,
            kpis=result.kpis,
            provenance=result.provenance,
            disclaimer=result.disclaimer,
        )

    def get_latest(self) -> OptimizationRunResponse:
        """Get latest optimization result, executing default if none run yet."""
        if self._latest_result is None:
            # Run quick deterministic solve
            self.run_optimization(OptimizationRunRequest(mode=OptimizationMode.DETERMINISTIC_P50))

        res = self._latest_result
        return OptimizationRunResponse(
            run_id=res.run_id,
            mode=res.mode,
            timestamp=res.timestamp,
            clusters=res.clusters,
            scenarios_evaluated=res.scenarios_evaluated,
            solver_metadata=res.solver_metadata,
            kpis=res.kpis,
            provenance=res.provenance,
            disclaimer=res.disclaimer,
        )

    def get_summary(self) -> OptimizationSummaryResponse:
        """Get consolidated KPI summary across clusters."""
        if self._latest_result is None:
            self.get_latest()

        res = self._latest_result
        cluster_sums: dict[str, dict[str, Any]] = {}
        for cid, sched in res.cluster_schedules.items():
            cluster_sums[cid] = {
                "service_reliability_pct": sched.service_reliability_pct,
                "total_energy_served_mwh": sched.total_energy_served_mwh,
                "net_operating_cost_inr": sched.net_operating_cost_inr,
                "renewable_utilization_pct": sched.renewable_utilization_pct,
                "energy_loss_pct": sched.energy_loss_pct,
            }

        return OptimizationSummaryResponse(
            run_id=res.run_id,
            mode=res.mode,
            solver_status=res.solver_metadata.solver_status,
            solve_time_seconds=res.solver_metadata.solve_time_seconds,
            mip_gap=res.solver_metadata.mip_gap,
            objective_value=res.solver_metadata.objective_value,
            kpis=res.kpis,
            cluster_summaries=cluster_sums,
            provenance=res.provenance,
        )

    def get_decisions(self, cluster_id: str = "delhi_ncr") -> OptimizationDecisionsResponse:
        """Get 24-hour decision trajectories for a specific cluster."""
        if self._latest_result is None:
            self.get_latest()

        res = self._latest_result
        if cluster_id not in res.cluster_schedules:
            cluster_id = "delhi_ncr"

        sched = res.cluster_schedules[cluster_id]
        return OptimizationDecisionsResponse(
            cluster_id=cluster_id,
            mode=res.mode,
            decisions=sched.hourly_decisions,
            provenance=res.provenance,
        )

    def get_comparison(self) -> OptimizationCompareResponse:
        """Get apples-to-apples performance comparisons across policies."""
        if self._comparison_cache is None:
            bau = self.pipeline.run_optimization(mode=OptimizationMode.BAU_BASELINE)
            det = self.pipeline.run_optimization(mode=OptimizationMode.DETERMINISTIC_P50)
            cvar = self.pipeline.run_optimization(mode=OptimizationMode.RISK_AWARE_CVAR)
            self._comparison_cache = self.comparison_engine.compare_runs(bau, det, cvar)

        return OptimizationCompareResponse(
            comparison_summary=self._comparison_cache["comparison_summary"],
            invariants_verified=self._comparison_cache["invariants_verified"],
            provenance=Provenance.SYNTHETIC,
        )

    def get_scenarios(self) -> OptimizationScenariosCatalogResponse:
        """Get catalogue of supported scenario profiles."""
        items = [
            ScenarioCatalogItem(
                scenario_id=s.scenario_id,
                probability=s.probability,
                description=s.description,
                provenance=s.provenance,
            )
            for s in DEFAULT_SCENARIOS
        ]
        return OptimizationScenariosCatalogResponse(
            scenarios=items,
            alpha_confidence=0.95,
            provenance=Provenance.SYNTHETIC,
        )
