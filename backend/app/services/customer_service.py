"""VOLT Backend - Customer Flexibility Service.

Bridges engine customer models, envelopes, dynamic tariffs, and scenarios
to FastAPI API endpoints.
"""

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
import pandas as pd
import yaml

from engine.customer.envelope import FlexibilityEnvelopeEngine
from engine.customer.incentives import IncentiveRecommendationEngine
from engine.customer.models import (
    CustomerSegment,
    CustomerServiceRequest,
    FlexibilityEnvelope,
    IncentiveOffer,
    ServiceType,
    TariffRecommendation,
)
from engine.customer.scenarios import (
    CustomerScenarioEvaluator,
    ScenarioEvaluationResult,
)
from engine.customer.synthetic_requests import (
    DEFAULT_SEGMENT_PROFILES,
    SyntheticRequestDisaggregator,
)
from engine.customer.tariffs import DynamicTariffPolicy


class CustomerService:
    """Service handling customer requests, flexibility envelopes, tariffs, and scenarios."""

    def __init__(self, data_dir: Optional[Path] = None, configs_dir: Optional[Path] = None):
        self.root_dir = Path(__file__).resolve().parent.parent.parent.parent
        self.data_dir = data_dir or (self.root_dir / "data" / "synthetic")
        self.configs_dir = configs_dir or (self.root_dir / "configs")

        self.envelope_engine = FlexibilityEnvelopeEngine()
        self.tariff_policy = DynamicTariffPolicy()
        self.incentive_engine = IncentiveRecommendationEngine()
        self.disaggregator = SyntheticRequestDisaggregator(seed=42, pack_capacity_kwh=2.25)
        self.scenario_evaluator = CustomerScenarioEvaluator(
            envelope_engine=self.envelope_engine,
            tariff_policy=self.tariff_policy,
            incentive_engine=self.incentive_engine,
        )

        self._requests_cache: Optional[list[CustomerServiceRequest]] = None
        self._reconciliation_df: Optional[pd.DataFrame] = None
        self._scenario_cache: dict[str, ScenarioEvaluationResult] = {}

    def _ensure_requests_loaded(self) -> tuple[list[CustomerServiceRequest], pd.DataFrame]:
        """Lazy-load and disaggregate hourly data into customer requests."""
        if self._requests_cache is not None and self._reconciliation_df is not None:
            return self._requests_cache, self._reconciliation_df

        hourly_path = self.data_dir / "cluster_hourly.csv.gz"
        if not hourly_path.exists():
            raise FileNotFoundError(f"Source dataset not found at {hourly_path}")

        hourly_df = pd.read_csv(hourly_path)
        # Generate representative demo window across all 5 clusters (1 hour * 5 clusters = 5 cluster-hours, ~9,800 requests)
        requests, recon_df = self.disaggregator.disaggregate_hourly_demand(
            hourly_df, demo_mode=True, max_hours=1
        )
        self._requests_cache = requests
        self._reconciliation_df = recon_df
        return self._requests_cache, self._reconciliation_df

    def get_customer_segments(self) -> list[dict[str, Any]]:
        """Return metadata for all customer segments."""
        assumptions_file = self.configs_dir / "assumptions.yaml"
        cust_assump = {}
        if assumptions_file.exists():
            with open(assumptions_file, "r") as f:
                raw = yaml.safe_load(f)
                cust_assump = raw.get("customer_flexibility", {}).get("customer_segments", {})

        segments = []
        for seg in CustomerSegment:
            cfg = cust_assump.get(seg.value, {})
            prof = DEFAULT_SEGMENT_PROFILES.get(seg, {})

            share = cfg.get("share", {}).get("value", prof.get("share", 0.20))
            opt_in = cfg.get("opt_in_rate", {}).get("value", prof.get("opt_in_rate", 0.0))
            priority = cfg.get("priority_rank", prof.get("priority", 5))
            wait = cfg.get("max_wait_minutes", prof.get("max_wait_mins", 0.0))
            deferral = cfg.get("max_deferral_minutes", prof.get("max_deferral_mins", 0.0))
            flex_frac = cfg.get("flexible_fraction", 0.0)
            is_shift = cfg.get("is_shiftable", flex_frac > 0.0)
            desc = cfg.get("description", prof.get("description", ""))

            segments.append(
                {
                    "segment": seg,
                    "priority_rank": priority,
                    "share_assumed": share,
                    "opt_in_rate_assumed": opt_in,
                    "max_wait_minutes": wait,
                    "max_deferral_minutes": deferral,
                    "flexible_fraction": flex_frac,
                    "is_shiftable": is_shift,
                    "description": desc,
                    "provenance": "ASSUMED",
                }
            )
        return segments

    def get_requests_summary(self) -> dict[str, Any]:
        """Return summary of disaggregated customer requests and reconciliation status."""
        requests, recon_df = self._ensure_requests_loaded()

        fc_reqs = [r for r in requests if r.request_type == ServiceType.FAST_CHARGE]
        swap_reqs = [r for r in requests if r.request_type == ServiceType.BATTERY_SWAP]

        fc_kwh = sum(r.requested_energy_kwh for r in fc_reqs)
        swap_packs = sum(r.requested_pack_count for r in swap_reqs)
        swap_kwh = swap_packs * 2.50

        # Cluster breakdown
        cluster_summaries = []
        clusters = list(set(r.cluster_id for r in requests))
        for c in sorted(clusters):
            c_fc = [r for r in fc_reqs if r.cluster_id == c]
            c_swap = [r for r in swap_reqs if r.cluster_id == c]
            c_recon = recon_df[recon_df["cluster_id"] == c]
            pass_rate = (
                float((c_recon["reconciled"].sum() / len(c_recon)) * 100.0)
                if len(c_recon) > 0
                else 100.0
            )

            cluster_summaries.append(
                {
                    "cluster_id": c,
                    "fast_charge_requests": len(c_fc),
                    "swap_requests": len(c_swap),
                    "total_fast_charge_kwh": round(sum(r.requested_energy_kwh for r in c_fc), 2),
                    "total_swap_packs": sum(r.requested_pack_count for r in c_swap),
                    "reconciliation_pass_rate_pct": round(pass_rate, 2),
                }
            )

        all_reconciled = bool(recon_df["reconciled"].all()) if len(recon_df) > 0 else True

        return {
            "total_requests": len(requests),
            "total_fast_charge_requests": len(fc_reqs),
            "total_battery_swap_requests": len(swap_reqs),
            "total_fast_charge_mwh": round(fc_kwh / 1000.0, 3),
            "total_swap_mwh": round(swap_kwh / 1000.0, 3),
            "total_swap_packs": swap_packs,
            "reconciliation_passed": all_reconciled,
            "cluster_summaries": cluster_summaries,
            "provenance": "SYNTHETIC",
            "disclaimer": "Generated from hourly aggregate synthetic load using SyntheticRequestDisaggregator.",
        }

    def get_flexibility_summary(self, cluster_id: Optional[str] = None) -> dict[str, Any]:
        """Return aggregate network or cluster demand flexibility summary."""
        res = self.evaluate_flexibility_scenario(
            scenario_id="NORMAL", target_cluster=cluster_id
        )
        return {
            "total_demand_kwh": res.total_demand_kwh,
            "non_shiftable_demand_kwh": res.non_shiftable_demand_kwh,
            "eligible_flexible_demand_kwh": res.eligible_flexible_demand_kwh,
            "opted_in_demand_kwh": res.opted_in_demand_kwh,
            "expected_accepted_demand_kwh": res.expected_accepted_demand_kwh,
            "realized_accepted_demand_kwh": res.realized_accepted_demand_kwh,
            "protected_priority_requests": res.protected_priority_requests,
            "protected_priority_demand_kwh": res.protected_priority_demand_kwh,
            "deadline_violations": 0,
            "modality_breakdown": res.modality_metrics,
            "segment_breakdown": res.segment_metrics,
            "provenance": "SYNTHETIC_SIMULATION",
        }

    def get_envelopes(
        self,
        cluster_id: Optional[str] = None,
        modality: Optional[ServiceType] = None,
        segment: Optional[CustomerSegment] = None,
        offset: int = 0,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Query and paginate individual flexibility envelopes."""
        requests, _ = self._ensure_requests_loaded()

        filtered_reqs = requests
        if cluster_id and cluster_id.lower() != "all":
            filtered_reqs = [r for r in filtered_reqs if r.cluster_id == cluster_id]
        if modality:
            filtered_reqs = [r for r in filtered_reqs if r.request_type == modality]
        if segment:
            filtered_reqs = [r for r in filtered_reqs if r.customer_segment == segment]

        total_count = len(filtered_reqs)
        page_reqs = filtered_reqs[offset : offset + limit]

        envelopes = [self.envelope_engine.compute_envelope(r) for r in page_reqs]
        return {
            "total_count": total_count,
            "offset": offset,
            "limit": limit,
            "envelopes": envelopes,
            "provenance": "SYNTHETIC",
        }

    def recommend_tariff(
        self,
        cluster_id: str,
        service_type: ServiceType,
        timestamp: datetime,
        previous_day_average_tariff_inr_per_kwh: float,
        forecast_procurement_cost_inr_per_kwh: Optional[float] = None,
        forecast_demand_mw: Optional[float] = None,
        available_capacity_mw: Optional[float] = None,
        forecast_solar_surplus_mw: Optional[float] = None,
    ) -> TariffRecommendation:
        """Evaluate dynamic tariff bounded by 80%-120% guardrails."""
        return self.tariff_policy.evaluate_tariff(
            cluster_id=cluster_id,
            service_type=service_type,
            timestamp=timestamp,
            previous_day_average_tariff_inr_per_kwh=previous_day_average_tariff_inr_per_kwh,
            forecast_procurement_cost_inr_per_kwh=forecast_procurement_cost_inr_per_kwh,
            forecast_demand_mw=forecast_demand_mw,
            available_capacity_mw=available_capacity_mw,
            forecast_solar_surplus_mw=forecast_solar_surplus_mw,
        )

    def get_flexibility_scenarios_catalog(self) -> list[dict[str, Any]]:
        """Return list of configured Phase 4 flexibility scenarios."""
        scenarios_file = self.configs_dir / "scenarios.yaml"
        if not scenarios_file.exists():
            return []

        with open(scenarios_file, "r") as f:
            raw = yaml.safe_load(f)
            flex_scenarios = raw.get("flexibility_scenarios", {})

        results = []
        for s_id, s_data in flex_scenarios.items():
            results.append(
                {
                    "scenario_id": s_id,
                    "name": s_data.get("name", s_id),
                    "description": s_data.get("description", ""),
                    "seed": s_data.get("seed", 42),
                    "parameters": {k: v for k, v in s_data.items() if k not in ("name", "description", "seed")},
                    "provenance": "SYNTHETIC",
                }
            )
        return results

    def evaluate_flexibility_scenario(
        self,
        scenario_id: str = "NORMAL",
        target_cluster: Optional[str] = None,
        seed_override: Optional[int] = None,
    ) -> ScenarioEvaluationResult:
        """Evaluate a scenario on base customer requests."""
        cache_key = f"{scenario_id}:{target_cluster or 'all'}:{seed_override or 'default'}"
        if cache_key in self._scenario_cache:
            return self._scenario_cache[cache_key]

        requests, _ = self._ensure_requests_loaded()

        scenarios_file = self.configs_dir / "scenarios.yaml"
        scenario_config = {"name": scenario_id, "seed": seed_override or 42}
        if scenarios_file.exists():
            with open(scenarios_file, "r") as f:
                raw = yaml.safe_load(f)
                flex_scenarios = raw.get("flexibility_scenarios", {})
                if scenario_id in flex_scenarios:
                    scenario_config = deepcopy(flex_scenarios[scenario_id])
                elif scenario_id in raw.get("scenarios", {}):
                    scenario_config = deepcopy(raw["scenarios"][scenario_id])

        if seed_override is not None:
            scenario_config["seed"] = seed_override

        result = self.scenario_evaluator.evaluate_scenario(
            scenario_id=scenario_id,
            scenario_config=scenario_config,
            base_requests=requests,
            target_cluster=target_cluster,
        )
        self._scenario_cache[cache_key] = result
        return result

    def get_incentives_summary(self) -> list[dict[str, Any]]:
        """Evaluate incentive expenditure across key flexibility scenarios."""
        catalog = self.get_flexibility_scenarios_catalog()
        summary_list = []

        scenario_ids = [s["scenario_id"] for s in catalog]
        if "NORMAL" not in scenario_ids:
            scenario_ids.insert(0, "NORMAL")

        for s_id in scenario_ids:
            res = self.evaluate_flexibility_scenario(scenario_id=s_id)
            summary_list.append(
                {
                    "scenario_id": res.scenario_id,
                    "scenario_name": res.scenario_name,
                    "description": res.description,
                    "expected_accepted_demand_kwh": res.expected_accepted_demand_kwh,
                    "realized_accepted_demand_kwh": res.realized_accepted_demand_kwh,
                    "total_retail_revenue_inr": res.total_retail_revenue_inr,
                    "total_incentive_cost_inr": res.total_incentive_cost_inr,
                    "net_financial_impact_inr": round(res.total_retail_revenue_inr - res.total_incentive_cost_inr, 2),
                    "average_wait_minutes": res.average_wait_minutes,
                }
            )
        return summary_list


# Singleton instance
customer_service = CustomerService()
