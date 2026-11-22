"""Comparative evaluation engine comparing BAU Baseline vs. Deterministic P50 vs. Risk-Aware CVaR MILP.

Runs identical starting conditions, identical demand profiles, identical initial storage states,
and identical price/renewable realization scenarios to quantify exact mathematical improvements:
- Operating procurement cost reduction (INR)
- Service reliability uplift (% vs BAU 78.4% baseline)
- Peak grid demand shaving & power headroom preservation
- Renewable utilization uplift (%)
- Energy loss reduction (% vs BAU 10.18% baseline)
- Risk hedge under tail-risk market price spikes (CVaR alpha=0.95)
"""

from typing import Any
from engine.optimization.schemas import (
    OptimizationKPIs,
    OptimizationMode,
    OptimizationResult,
)


class PolicyComparisonEngine:
    """Computes apples-to-apples performance comparisons across dispatch policies."""

    def compare_runs(
        self,
        bau_result: OptimizationResult,
        det_result: OptimizationResult,
        cvar_result: OptimizationResult,
    ) -> dict[str, Any]:
        """Generate structured comparison table and uplift metrics."""

        bau_kpis = bau_result.kpis
        det_kpis = det_result.kpis
        cvar_kpis = cvar_result.kpis

        # Cost savings vs BAU (using absolute base for percentage)
        det_cost_saving_inr = bau_kpis.net_operating_cost_inr - det_kpis.net_operating_cost_inr
        cvar_cost_saving_inr = bau_kpis.net_operating_cost_inr - cvar_kpis.net_operating_cost_inr

        base_cost = abs(bau_kpis.net_operating_cost_inr) if abs(bau_kpis.net_operating_cost_inr) > 1.0 else 1.0
        det_cost_saving_pct = (det_cost_saving_inr / base_cost) * 100.0
        cvar_cost_saving_pct = (cvar_cost_saving_inr / base_cost) * 100.0

        # Reliability uplift
        det_rel_uplift_pct = det_kpis.service_reliability_pct - bau_kpis.service_reliability_pct
        cvar_rel_uplift_pct = cvar_kpis.service_reliability_pct - bau_kpis.service_reliability_pct

        # Renewable utilization
        det_ren_uplift_pct = det_kpis.renewable_share_pct - bau_kpis.renewable_share_pct
        cvar_ren_uplift_pct = cvar_kpis.renewable_share_pct - bau_kpis.renewable_share_pct

        # Loss reduction
        det_loss_reduction_pct = bau_kpis.energy_loss_pct - det_kpis.energy_loss_pct
        cvar_loss_reduction_pct = bau_kpis.energy_loss_pct - cvar_kpis.energy_loss_pct

        return {
            "comparison_summary": {
                "bau_baseline": {
                    "mode": "BAU_BASELINE",
                    "solver_status": bau_result.solver_metadata.solver_status.value,
                    "service_reliability_pct": bau_kpis.service_reliability_pct,
                    "energy_loss_pct": bau_kpis.energy_loss_pct,
                    "renewable_share_pct": bau_kpis.renewable_share_pct,
                    "net_operating_cost_inr": bau_kpis.net_operating_cost_inr,
                    "procurement_cost_inr": bau_kpis.total_procurement_cost_inr,
                    "retail_revenue_inr": bau_kpis.total_retail_revenue_inr,
                    "cvar_tail_risk_inr": bau_kpis.cvar_tail_risk_cost_inr,
                    "min_power_headroom_mw": bau_kpis.power_capacity_headroom_mw,
                },
                "deterministic_p50": {
                    "mode": "DETERMINISTIC_P50",
                    "solver_status": det_result.solver_metadata.solver_status.value,
                    "solve_time_seconds": det_result.solver_metadata.solve_time_seconds,
                    "mip_gap": det_result.solver_metadata.mip_gap,
                    "service_reliability_pct": det_kpis.service_reliability_pct,
                    "energy_loss_pct": det_kpis.energy_loss_pct,
                    "renewable_share_pct": det_kpis.renewable_share_pct,
                    "net_operating_cost_inr": det_kpis.net_operating_cost_inr,
                    "procurement_cost_inr": det_kpis.total_procurement_cost_inr,
                    "retail_revenue_inr": det_kpis.total_retail_revenue_inr,
                    "cvar_tail_risk_inr": det_kpis.cvar_tail_risk_cost_inr,
                    "min_power_headroom_mw": det_kpis.power_capacity_headroom_mw,
                    "cost_saving_inr": round(det_cost_saving_inr, 2),
                    "cost_saving_pct": round(det_cost_saving_pct, 2),
                    "reliability_uplift_pct": round(det_rel_uplift_pct, 2),
                },
                "risk_aware_cvar": {
                    "mode": "RISK_AWARE_CVAR",
                    "solver_status": cvar_result.solver_metadata.solver_status.value,
                    "solve_time_seconds": cvar_result.solver_metadata.solve_time_seconds,
                    "mip_gap": cvar_result.solver_metadata.mip_gap,
                    "service_reliability_pct": cvar_kpis.service_reliability_pct,
                    "energy_loss_pct": cvar_kpis.energy_loss_pct,
                    "renewable_share_pct": cvar_kpis.renewable_share_pct,
                    "net_operating_cost_inr": cvar_kpis.net_operating_cost_inr,
                    "procurement_cost_inr": cvar_kpis.total_procurement_cost_inr,
                    "retail_revenue_inr": cvar_kpis.total_retail_revenue_inr,
                    "cvar_tail_risk_inr": cvar_kpis.cvar_tail_risk_cost_inr,
                    "min_power_headroom_mw": cvar_kpis.power_capacity_headroom_mw,
                    "cost_saving_inr": round(cvar_cost_saving_inr, 2),
                    "cost_saving_pct": round(cvar_cost_saving_pct, 2),
                    "reliability_uplift_pct": round(cvar_rel_uplift_pct, 2),
                    "tail_risk_hedge_inr": round(det_kpis.cvar_tail_risk_cost_inr - cvar_kpis.cvar_tail_risk_cost_inr, 2),
                },
            },
            "invariants_verified": {
                "all_modes_identical_demand": bool(
                    abs(bau_kpis.total_energy_requested_mwh - det_kpis.total_energy_requested_mwh) < 1e-3
                    and abs(det_kpis.total_energy_requested_mwh - cvar_kpis.total_energy_requested_mwh) < 1e-3
                ),
                "bess_reserve_maintained_all": bool(
                    bau_kpis.bess_emergency_reserve_compliant
                    and det_kpis.bess_emergency_reserve_compliant
                    and cvar_kpis.bess_emergency_reserve_compliant
                ),
                "swap_reserve_maintained_all": bool(
                    bau_kpis.swap_emergency_reserve_compliant
                    and det_kpis.swap_emergency_reserve_compliant
                    and cvar_kpis.swap_emergency_reserve_compliant
                ),
                "power_headroom_maintained_all": bool(
                    bau_kpis.power_headroom_reserve_compliant
                    and det_kpis.power_headroom_reserve_compliant
                    and cvar_kpis.power_headroom_reserve_compliant
                ),
                "zero_deadline_violations_all": bool(
                    bau_kpis.deadline_violations_count == 0
                    and det_kpis.deadline_violations_count == 0
                    and cvar_kpis.deadline_violations_count == 0
                ),
            },
        }
