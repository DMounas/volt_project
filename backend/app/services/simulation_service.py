"""Simulation service providing caching, execution orchestration, and comparison for Phase 6.

Manages Digital Twin runs, receding-horizon MPC steps, and apples-to-apples comparisons.
"""

from datetime import datetime, timezone
from typing import Any, Optional

from backend.app.schemas.simulation_schemas import (
    MPCStatusResponse,
    PolicyComparisonMetric,
    ScenarioItem,
    SimulationComparisonResponse,
    SimulationEventsResponse,
    SimulationExplainabilityResponse,
    SimulationRunRequest,
    SimulationRunResponse,
    SimulationScenariosCatalogResponse,
    SimulationTimelineResponse,
)
from engine.optimization.pipeline import DEFAULT_CLUSTERS
from engine.provenance import Provenance
from engine.twin.events import ScenarioEventEngine
from engine.twin.mpc_controller import RollingMPCController
from engine.twin.schemas import EBITDAEvaluation, SimulationPolicy, SimulationRunSummary


class SimulationService:
    """Singleton service managing digital twin simulations and benchmarks."""

    _instance: Optional["SimulationService"] = None

    def __init__(self):
        self.controller = RollingMPCController()
        self.event_engine = ScenarioEventEngine()
        self._runs_cache: dict[str, SimulationRunSummary] = {}
        self._latest_run_id: Optional[str] = None
        self._comparison_cache: dict[str, SimulationComparisonResponse] = {}

    @classmethod
    def get_instance(cls) -> "SimulationService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def list_scenarios(self) -> SimulationScenariosCatalogResponse:
        """Return catalog of all 10 YAML crisis and disturbance scenarios."""
        raw_scenarios = self.event_engine.list_scenarios()
        items = [
            ScenarioItem(
                id=sc["id"],
                name=sc["name"],
                description=sc["description"],
                severity=sc.get("severity", "MEDIUM"),
                start_hour=sc.get("start_hour", 0),
                duration_hours=sc.get("duration_hours", 24),
                affected_clusters=sc.get("affected_clusters", ["ALL"]),
                forecast_visibility=sc.get("forecast_visibility", "ZERO_AHEAD"),
                multipliers=sc.get("multipliers", {}),
            )
            for sc in raw_scenarios
        ]
        return SimulationScenariosCatalogResponse(
            scenarios=items,
            count=len(items),
            provenance=Provenance.SYNTHETIC,
        )

    def run_simulation(self, request: SimulationRunRequest) -> SimulationRunResponse:
        """Execute a digital twin simulation run."""
        summary = self.controller.run_simulation(
            scenario_id=request.scenario_id,
            policy=request.policy,
            horizon_hours=request.horizon_hours,
            clusters=request.clusters or DEFAULT_CLUSTERS,
            seed=request.seed,
            time_limit_per_step=request.time_limit_per_step,
            mip_gap=request.mip_gap,
        )

        self._runs_cache[summary.run_id] = summary
        self._latest_run_id = summary.run_id

        return SimulationRunResponse(
            run_id=summary.run_id,
            scenario_id=summary.scenario_id,
            policy=summary.policy,
            horizon_hours=summary.horizon_hours,
            seed=summary.seed,
            clusters=summary.clusters,
            kpis=summary.kpis,
            ebitda=summary.ebitda,
            invariants_verified=summary.invariants_verified,
            provenance=summary.provenance,
            disclaimer=summary.disclaimer,
        )

    def get_latest_run(self) -> SimulationRunResponse:
        """Return the most recently executed simulation run or initialize default."""
        if not self._runs_cache:
            # Run quick 6-hour baseline
            return self.run_simulation(
                SimulationRunRequest(
                    scenario_id="NORMAL_OPERATION",
                    policy=SimulationPolicy.CLOSED_LOOP_MPC_P50,
                    horizon_hours=6,
                )
            )
        assert self._latest_run_id is not None
        summary = self._runs_cache[self._latest_run_id]
        return SimulationRunResponse(
            run_id=summary.run_id,
            scenario_id=summary.scenario_id,
            policy=summary.policy,
            horizon_hours=summary.horizon_hours,
            seed=summary.seed,
            clusters=summary.clusters,
            kpis=summary.kpis,
            ebitda=summary.ebitda,
            invariants_verified=summary.invariants_verified,
            provenance=summary.provenance,
            disclaimer=summary.disclaimer,
        )

    def get_run(self, run_id: str) -> Optional[SimulationRunResponse]:
        """Retrieve simulation summary by run_id."""
        if run_id not in self._runs_cache:
            return None
        summary = self._runs_cache[run_id]
        return SimulationRunResponse(
            run_id=summary.run_id,
            scenario_id=summary.scenario_id,
            policy=summary.policy,
            horizon_hours=summary.horizon_hours,
            seed=summary.seed,
            clusters=summary.clusters,
            kpis=summary.kpis,
            ebitda=summary.ebitda,
            invariants_verified=summary.invariants_verified,
            provenance=summary.provenance,
            disclaimer=summary.disclaimer,
        )

    def get_timeline(self, run_id: str) -> Optional[SimulationTimelineResponse]:
        """Retrieve step-by-step physical and decision timeline."""
        if run_id not in self._runs_cache:
            if self._runs_cache:
                run_id = list(self._runs_cache.keys())[-1]
            else:
                self.get_latest_run()
                run_id = list(self._runs_cache.keys())[-1]

        summary = self._runs_cache[run_id]
        return SimulationTimelineResponse(
            run_id=summary.run_id,
            scenario_id=summary.scenario_id,
            policy=summary.policy,
            timeline=summary.timeline,
            provenance=summary.provenance,
        )

    def get_explainability(self, run_id: str) -> Optional[SimulationExplainabilityResponse]:
        """Retrieve decision explanation logs."""
        if run_id not in self._runs_cache:
            if self._runs_cache:
                run_id = list(self._runs_cache.keys())[-1]
            else:
                self.get_latest_run()
                run_id = list(self._runs_cache.keys())[-1]

        summary = self._runs_cache[run_id]
        return SimulationExplainabilityResponse(
            run_id=summary.run_id,
            explanations=summary.explanations,
            provenance=summary.provenance,
        )

    def get_events(self, run_id: str) -> Optional[SimulationEventsResponse]:
        """Retrieve scenario event configuration."""
        if run_id not in self._runs_cache:
            if self._runs_cache:
                run_id = list(self._runs_cache.keys())[-1]
            else:
                self.get_latest_run()
                run_id = list(self._runs_cache.keys())[-1]

        summary = self._runs_cache[run_id]
        sc_spec = self.event_engine.get_scenario(summary.scenario_id)
        return SimulationEventsResponse(
            run_id=summary.run_id,
            scenario_id=summary.scenario_id,
            scenario_details=sc_spec,
            provenance=summary.provenance,
        )

    def get_comparison(
        self,
        scenario_id: str = "NORMAL_OPERATION",
        horizon_hours: int = 12,
        seed: int = 42,
    ) -> SimulationComparisonResponse:
        """Run controlled comparison of BAU, Open-Loop MILP, and Closed-Loop MPC."""
        cache_key = f"{scenario_id}:{horizon_hours}:{seed}"
        if cache_key in self._comparison_cache:
            return self._comparison_cache[cache_key]

        # 1. Run BAU Baseline
        bau = self.controller.run_simulation(
            scenario_id=scenario_id,
            policy=SimulationPolicy.BAU_BASELINE,
            horizon_hours=horizon_hours,
            seed=seed,
        )

        # 2. Run Open-Loop MILP (Deterministic P50)
        ol = self.controller.run_simulation(
            scenario_id=scenario_id,
            policy=SimulationPolicy.OPEN_LOOP_P50,
            horizon_hours=horizon_hours,
            seed=seed,
        )

        # 3. Run Closed-Loop Rolling MPC (Deterministic P50)
        mpc = self.controller.run_simulation(
            scenario_id=scenario_id,
            policy=SimulationPolicy.CLOSED_LOOP_MPC_P50,
            horizon_hours=horizon_hours,
            seed=seed,
        )

        def make_metric(res: SimulationRunSummary) -> PolicyComparisonMetric:
            return PolicyComparisonMetric(
                policy=res.policy.value,
                service_reliability_pct=res.kpis.service_reliability_pct,
                energy_loss_pct=res.kpis.energy_loss_pct,
                renewable_share_pct=res.kpis.renewable_utilization_pct,
                total_energy_served_mwh=res.kpis.total_energy_served_mwh,
                procurement_cost_inr=res.kpis.procurement_cost_inr,
                retail_revenue_inr=res.kpis.retail_tariff_revenue_inr,
                net_operating_contribution_inr=res.kpis.net_operating_contribution_inr,
                fallback_events_count=res.kpis.fallback_events_count,
                ebitda_status="NOT_EVALUABLE",
            )

        bau_m = make_metric(bau)
        ol_m = make_metric(ol)
        mpc_m = make_metric(mpc)

        # Cost savings vs BAU
        base_cost = abs(bau_m.procurement_cost_inr) if abs(bau_m.procurement_cost_inr) > 1.0 else 1.0
        cost_saving_pct = round(((bau_m.procurement_cost_inr - mpc_m.procurement_cost_inr) / base_cost) * 100.0, 2)
        rel_uplift = round(mpc_m.service_reliability_pct - bau_m.service_reliability_pct, 2)
        loss_red = round(bau_m.energy_loss_pct - mpc_m.energy_loss_pct, 2)

        resp = SimulationComparisonResponse(
            run_id=f"CMP-{scenario_id[:6]}-{seed}",
            scenario_id=scenario_id,
            horizon_hours=horizon_hours,
            policies={
                "bau_baseline": bau_m,
                "open_loop_milp": ol_m,
                "closed_loop_mpc": mpc_m,
            },
            cost_saving_mpc_vs_bau_pct=cost_saving_pct,
            service_uplift_mpc_vs_bau_pct=rel_uplift,
            loss_reduction_mpc_vs_bau_pct=loss_red,
            ebitda_disclosure=EBITDAEvaluation(),
            provenance=Provenance.SYNTHETIC,
        )

        self._comparison_cache[cache_key] = resp
        return resp

    def get_mpc_status(self) -> MPCStatusResponse:
        """Return controller health and solver capability telemetry."""
        solver_mgr = self.controller.pipeline.solver_manager
        solver, name = solver_mgr.find_available_solver()
        available = ["appsi_highs", "highs", "glpk", "cbc"]

        return MPCStatusResponse(
            controller_status="HEALTHY",
            preferred_solver=name,
            available_solvers=available,
            default_horizon_hours=24,
            control_step_hours=1,
            receding_horizon=True,
            invariants_enforced=[
                "bess_emergency_reserve_5pct",
                "swap_ready_reserve_5pct",
                "power_headroom_reserve_5pct",
                "integer_swap_pack_conservation",
                "zero_inter_city_transfer",
                "zero_emergency_violations",
                "regulatory_tariff_bounds_0.8x_1.2x",
            ],
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
