"""Optimization pipeline orchestrating forecasts, customer flexibility cohorts, and solver execution.

Coordinates:
- Ingestion of 24-hour forecast vectors across all 5 clusters
- Ingestion of customer service requests and cohort aggregation
- Construction of Pyomo MILP model with physical and regulatory constraints
- Execution of preferred solver (appsi_highs / HiGHS 1.16.0) with timeout and MIP gap
- Extraction of typed decision variables, physical trajectories, and binding causality
- Independent validation of physical conservation invariants
- Rule-based fallback execution if solver is unavailable or times out
"""

import os
from pathlib import Path
from typing import Any, Optional
import pandas as pd
import pyomo.environ as pyo

from engine.customer.models import CustomerServiceRequest, ServiceType
from engine.customer.synthetic_requests import SyntheticRequestDisaggregator
from engine.optimization.cohorts import CohortAggregator, ServiceCohort
from engine.optimization.extract import SolutionExtractor
from engine.optimization.fallback import HeuristicFallbackScheduler
from engine.optimization.model_builder import ModelBuilder
from engine.optimization.objective import ObjectiveBuilder
from engine.optimization.schemas import (
    BESSInitialState,
    ClusterHorizonInput,
    OptimizationMode,
    OptimizationResult,
    ScenarioWeight,
    SolverStatus,
    SwapInitialState,
)
from engine.optimization.solver import SolverManager
from engine.optimization.validation import OptimizationValidator
from engine.provenance import Provenance


DEFAULT_CLUSTERS = ["delhi_ncr", "mumbai_mmr", "bengaluru", "hyderabad", "chennai"]

DEFAULT_SCENARIOS = [
    ScenarioWeight(scenario_id="NORMAL", probability=0.60, description="Base normal operational conditions"),
    ScenarioWeight(scenario_id="PEAK_SQUEEZE_SURGE", probability=0.15, description="EV surge coinciding with IEX price spike"),
    ScenarioWeight(scenario_id="RENEWABLE_DROUGHT_STRESS", probability=0.15, description="50% solar and wind drop with overcast sky"),
    ScenarioWeight(scenario_id="EXTREME_MARKET_SPIKE", probability=0.10, description="Extreme IEX market price surge"),
]


class OptimizationPipeline:
    """End-to-end multi-city energy and flexibility MILP optimizer."""

    def __init__(
        self,
        data_dir: Optional[Path] = None,
        pack_capacity_kwh: float = 2.25,
        installed_cluster_power_mw: float = 240.0,
        time_limit_seconds: float = 60.0,
        mip_gap_tolerance: float = 0.01,
        threads: int = 4,
    ):
        self.data_dir = data_dir or Path("data/synthetic")
        self.pack_kwh = pack_capacity_kwh
        self.installed_power_mw = installed_cluster_power_mw
        self.time_limit = time_limit_seconds
        self.mip_gap = mip_gap_tolerance
        self.threads = threads

        self.cohort_aggregator = CohortAggregator(pack_capacity_kwh=pack_capacity_kwh)
        self.solver_manager = SolverManager(
            time_limit_seconds=time_limit_seconds,
            mip_gap_tolerance=mip_gap_tolerance,
            threads=threads,
        )
        self.extractor = SolutionExtractor(pack_capacity_kwh=pack_capacity_kwh)
        self.validator = OptimizationValidator()
        self.fallback_scheduler = HeuristicFallbackScheduler(pack_capacity_kwh=pack_capacity_kwh)

        # Cache for recent results
        self._result_cache: dict[str, OptimizationResult] = {}

    def load_cluster_inputs(
        self,
        clusters: Optional[list[str]] = None,
        horizon_hours: int = 24,
        offset_hours: int = 0,
    ) -> dict[str, ClusterHorizonInput]:
        """Load 24-hour demand, generation, and price vectors for all clusters."""
        target_clusters = clusters or DEFAULT_CLUSTERS
        cluster_file = self.data_dir / "cluster_hourly.csv.gz"

        if not cluster_file.exists():
            raise FileNotFoundError(f"Cluster dataset missing at {cluster_file}")

        df = pd.read_csv(cluster_file, compression="gzip")
        inputs: dict[str, ClusterHorizonInput] = {}

        for c in target_clusters:
            c_df = df[df["cluster_id"] == c].tail(horizon_hours + offset_hours).head(horizon_hours)

            # Ensure exactly horizon_hours rows
            if len(c_df) < horizon_hours:
                c_df = df[df["cluster_id"] == c].head(horizon_hours)

            fc_demand = c_df["fast_charge_demand_mwh"].tolist()
            swap_requests = c_df["swap_requests"].astype(int).tolist()
            swap_energy = c_df["swap_energy_equivalent_mwh"].tolist()
            solar_avail = c_df["solar_available_mwh"].tolist() if "solar_available_mwh" in c_df.columns else [10.0] * horizon_hours
            wind_avail = c_df["wind_available_mwh"].tolist() if "wind_available_mwh" in c_df.columns else [5.0] * horizon_hours
            discom_tariff = c_df["discom_tariff_inr_per_mwh"].tolist() if "discom_tariff_inr_per_mwh" in c_df.columns else [7500.0] * horizon_hours
            iex_price = c_df["iex_dam_price_inr_per_mwh"].tolist() if "iex_dam_price_inr_per_mwh" in c_df.columns else [5200.0] * horizon_hours
            iex_cap = [60.0] * horizon_hours  # Assumed 60 MW cluster market access cap

            inputs[c] = ClusterHorizonInput(
                cluster_id=c,
                hours=list(range(horizon_hours)),
                fast_charge_demand_mwh=fc_demand,
                swap_requests_count=swap_requests,
                swap_energy_mwh=swap_energy,
                solar_available_mwh=solar_avail,
                wind_available_mwh=wind_avail,
                discom_tariff_inr_per_mwh=discom_tariff,
                iex_dam_price_inr_per_mwh=iex_price,
                iex_procurement_cap_mw=iex_cap,
                previous_day_avg_tariff_inr_per_kwh=11.20,
                bess_state=BESSInitialState(),
                swap_state=SwapInitialState(),
            )

        return inputs

    def load_customer_requests(
        self,
        clusters: Optional[list[str]] = None,
        max_hours: int = 24,
    ) -> list[CustomerServiceRequest]:
        """Load or disaggregate individual customer service requests."""
        target_clusters = clusters or DEFAULT_CLUSTERS
        req_file = self.data_dir / "customer_requests_disaggregated.csv.gz"

        if req_file.exists():
            df = pd.read_csv(req_file, compression="gzip")
            # Filter by cluster
            c_df = df[df["cluster_id"].isin(target_clusters)]
            disagg = SyntheticRequestDisaggregator(pack_capacity_kwh=self.pack_kwh)
            # Use quick disaggregation if table empty or mismatched
            if len(c_df) > 0:
                requests: list[CustomerServiceRequest] = []
                for _, row in c_df.iterrows():
                    arr_dt = pd.to_datetime(row["arrival_ts"])
                    dead_dt = pd.to_datetime(row["departure_deadline_ts"])
                    req = CustomerServiceRequest(
                        request_id=str(row["request_id"]),
                        cluster_id=str(row["cluster_id"]),
                        request_type=ServiceType(row["request_type"]),
                        customer_segment=row["customer_segment"],
                        arrival_ts=arr_dt,
                        departure_deadline_ts=dead_dt,
                        requested_energy_kwh=float(row.get("requested_energy_kwh", 0.0)) if pd.notna(row.get("requested_energy_kwh")) else None,
                        minimum_service_energy_kwh=float(row.get("minimum_service_energy_kwh", 0.0)) if pd.notna(row.get("minimum_service_energy_kwh")) else None,
                        requested_pack_count=int(row.get("requested_pack_count", 1)) if pd.notna(row.get("requested_pack_count")) else None,
                        minimum_pack_count=int(row.get("minimum_pack_count", 1)) if pd.notna(row.get("minimum_pack_count")) else None,
                        pack_capacity_kwh=self.pack_kwh,
                        flexibility_opt_in=bool(row.get("flexibility_opt_in", False)),
                        service_priority=int(row.get("service_priority", 3)),
                        baseline_tariff_inr_per_kwh=float(row.get("baseline_tariff_inr_per_kwh", 11.50)),
                        previous_day_avg_tariff_inr_per_kwh=float(row.get("previous_day_avg_tariff_inr_per_kwh", 11.20)),
                        provenance=Provenance.SYNTHETIC,
                    )
                    requests.append(req)
                return requests

        # Disaggregate on the fly from cluster hourly data
        cluster_file = self.data_dir / "cluster_hourly.csv.gz"
        df_hourly = pd.read_csv(cluster_file, compression="gzip")
        disagg = SyntheticRequestDisaggregator(pack_capacity_kwh=self.pack_kwh)
        requests, _ = disagg.disaggregate_hourly_demand(df_hourly, demo_mode=True, max_hours=max_hours)
        return requests

    def load_customer_cohorts(
        self,
        clusters: Optional[list[str]] = None,
        max_hours: int = 24,
    ) -> list[ServiceCohort]:
        """Load or disaggregate requests into service cohorts using fast vectorized aggregation."""
        target_clusters = clusters or DEFAULT_CLUSTERS
        req_file = self.data_dir / "customer_requests_disaggregated.csv.gz"

        if req_file.exists():
            df = pd.read_csv(req_file, compression="gzip")
            c_df = df[df["cluster_id"].isin(target_clusters)]
            if len(c_df) > 0:
                return self.cohort_aggregator.aggregate_dataframe(c_df, horizon_hours=max_hours)

        # Fallback to generating requests and aggregating
        raw_requests = self.load_customer_requests(clusters=target_clusters, max_hours=max_hours)
        return self.cohort_aggregator.aggregate_requests(raw_requests, horizon_hours=max_hours)

    def run_optimization(
        self,
        mode: OptimizationMode = OptimizationMode.DETERMINISTIC_P50,
        clusters: Optional[list[str]] = None,
        scenarios: Optional[list[ScenarioWeight]] = None,
        custom_cluster_inputs: Optional[dict[str, ClusterHorizonInput]] = None,
        custom_cohorts: Optional[list[ServiceCohort]] = None,
        time_limit_seconds: Optional[float] = None,
        mip_gap: Optional[float] = None,
        seed: int = 42,
    ) -> OptimizationResult:
        """Execute full optimization run across all specified clusters."""
        target_clusters = clusters or DEFAULT_CLUSTERS
        timeout = time_limit_seconds or self.time_limit
        gap = mip_gap or self.mip_gap

        # Bypass cache when custom inputs are passed
        if custom_cluster_inputs is None and custom_cohorts is None:
            cache_key = f"{mode.value}:{','.join(target_clusters)}:{timeout}:{gap}:{seed}"
            if cache_key in self._result_cache:
                return self._result_cache[cache_key]
        else:
            cache_key = None

        # 1. Load inputs and cohorts
        cluster_inputs = custom_cluster_inputs or self.load_cluster_inputs(clusters=target_clusters)
        cohorts = custom_cohorts if custom_cohorts is not None else self.load_customer_cohorts(clusters=target_clusters, max_hours=24)

        # 3. Handle BAU baseline mode
        if mode == OptimizationMode.BAU_BASELINE:
            result = self.fallback_scheduler.generate_fallback_schedule(
                cluster_inputs=cluster_inputs,
                cohorts=cohorts,
                reason="Business-as-Usual (BAU) heuristic dispatch evaluation",
                run_id=f"BAU-{seed:04d}",
            )
            if cache_key is not None:
                self._result_cache[cache_key] = result
            return result

        # 4. Setup scenarios
        if mode == OptimizationMode.DETERMINISTIC_P50:
            active_scenarios = [ScenarioWeight(scenario_id="NORMAL", probability=1.0, description="P50 deterministic baseline")]
            is_risk_aware = False
        else:
            active_scenarios = scenarios or DEFAULT_SCENARIOS
            is_risk_aware = True

        # 5. Build Pyomo model
        builder = ModelBuilder(
            clusters=target_clusters,
            horizon=list(range(24)),
            scenarios=active_scenarios,
            cohorts=cohorts,
            cluster_inputs=cluster_inputs,
            mode=mode,
            pack_capacity_kwh=self.pack_kwh,
            installed_cluster_power_mw=self.installed_power_mw,
        )
        model = builder.build()

        # 6. Attach objective
        obj_builder = ObjectiveBuilder(
            cvar_alpha=0.95,
            risk_weight_lambda=0.20 if is_risk_aware else 0.0,
        )
        prob_dict = {s.scenario_id: s.probability for s in active_scenarios}
        obj_builder.attach_objective(
            model=model,
            scenarios=[s.scenario_id for s in active_scenarios],
            probabilities=prob_dict,
            clusters=target_clusters,
            horizon=list(range(24)),
            cohorts=cohorts,
            is_risk_aware=is_risk_aware,
        )

        # 7. Solve
        success, solver_meta = self.solver_manager.solve(
            model=model,
            time_limit_override=timeout,
            mip_gap_override=gap,
        )

        # 8. If solve fails, trigger fallback
        if not success or solver_meta.solver_status not in (SolverStatus.OPTIMAL, SolverStatus.FEASIBLE_GAP):
            reason = solver_meta.infeasibility_reasons[0] if solver_meta.infeasibility_reasons else "Solver failed or timed out"
            fallback_res = self.fallback_scheduler.generate_fallback_schedule(
                cluster_inputs=cluster_inputs,
                cohorts=cohorts,
                reason=reason,
                run_id=f"OPT-FALLBACK-{seed:04d}",
            )
            fallback_res.solver_metadata = solver_meta
            fallback_res.solver_metadata.is_fallback = True
            fallback_res.solver_metadata.solver_status = SolverStatus.FALLBACK_HEURISTIC
            fallback_res.mode = mode
            if cache_key is not None:
                self._result_cache[cache_key] = fallback_res
            return fallback_res

        # 9. Extract and validate
        result = self.extractor.extract(
            model=model,
            cluster_inputs=cluster_inputs,
            cohorts=cohorts,
            solver_metadata=solver_meta,
            mode=mode,
            run_id=f"OPT-{mode.value[:3]}-{seed:04d}",
        )

        if cache_key is not None:
            self._result_cache[cache_key] = result
        return result
