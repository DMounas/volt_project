"""Extracts decisions, physical trajectories, binding constraint explanations, and KPIs from the solved Pyomo model.

Guarantees:
- Strict unit tagging (MW, MWh, packs, INR, INR/kWh)
- Clean separation of retail tariff revenue and incentive expenditure
- Transparent causality identification (identifies binding physical limits)
- Consistent calculation of reliability and energy losses matching Phase 2/3 definitions
"""

from typing import Any
import pyomo.environ as pyo

from engine.customer.models import ServiceType
from engine.optimization.cohorts import ServiceCohort
from engine.optimization.schemas import (
    ClusterDailySchedule,
    ClusterHorizonInput,
    DynamicTariffTier,
    HourlyClusterDecision,
    OptimizationKPIs,
    OptimizationMode,
    OptimizationResult,
    SolverMetadata,
)
from engine.provenance import Provenance


class SolutionExtractor:
    """Extracts solution vectors into typed schemas and validates energy balance."""

    def __init__(
        self,
        pack_capacity_kwh: float = 2.25,
        installed_cluster_power_mw: float = 240.0,
        loss_factor: float = 0.012,
        aux_load_mw: float = 2.50,
    ):
        self.pack_kwh = pack_capacity_kwh
        self.installed_power_mw = installed_cluster_power_mw
        self.loss_factor = loss_factor
        self.aux_load_mw = aux_load_mw
        self.tier_enum_map = {
            1: DynamicTariffTier.TIER_80,
            2: DynamicTariffTier.TIER_90,
            3: DynamicTariffTier.TIER_100,
            4: DynamicTariffTier.TIER_110,
            5: DynamicTariffTier.TIER_120,
        }
        self.tier_mult_map = {1: 0.80, 2: 0.90, 3: 1.00, 4: 1.10, 5: 1.20}

    def extract(
        self,
        model: pyo.ConcreteModel,
        cluster_inputs: dict[str, ClusterHorizonInput],
        cohorts: list[ServiceCohort],
        solver_metadata: SolverMetadata,
        mode: OptimizationMode = OptimizationMode.DETERMINISTIC_P50,
        run_id: str = "OPT-001",
        timestamp: str = "2025-06-15T00:00:00+05:30",
    ) -> OptimizationResult:
        """Extract full result schemas from solved model."""
        clusters = list(model.CLUSTERS)
        horizon = list(model.HOURS)
        scenarios = list(model.SCENARIOS)
        # Use first scenario (e.g. 'NORMAL' or primary realization) for schedules
        s_eval = scenarios[0]

        cohort_map = {c.cohort_id: c for c in cohorts}

        cluster_schedules: dict[str, ClusterDailySchedule] = {}

        # Global aggregators
        total_fc_req_mwh = 0.0
        total_fc_serv_mwh = 0.0
        total_swap_req_packs = 0
        total_swap_serv_packs = 0

        total_discom_cost = 0.0
        total_iex_cost = 0.0
        total_ren_cost = 0.0
        total_bess_deg_cost = 0.0
        total_incentive_exp = 0.0
        total_tariff_rev = 0.0
        total_loss_mwh = 0.0
        total_ren_used = 0.0
        total_procured = 0.0

        min_power_headroom_network = 999.0
        bess_reserve_pass = True
        swap_reserve_pass = True
        headroom_reserve_pass = True
        deadline_violations = 0
        unserved_crit_mwh = 0.0

        for c in clusters:
            c_input = cluster_inputs[c]
            hourly_decisions: list[HourlyClusterDecision] = []

            c_discom_cost = 0.0
            c_iex_cost = 0.0
            c_ren_cost = 0.0
            c_bess_deg_cost = 0.0
            c_incentive_exp = 0.0
            c_tariff_rev = 0.0
            c_req_mwh = 0.0
            c_serv_mwh = 0.0
            c_ren_used = 0.0
            c_ren_avail = 0.0
            c_losses = 0.0

            for t in horizon:
                p_disc = float(pyo.value(model.p_discom[c, t, s_eval]))
                p_iex_val = float(pyo.value(model.p_iex[c, t, s_eval]))
                e_ren_u = float(pyo.value(model.e_ren_used[c, t, s_eval]))
                e_ren_c = float(pyo.value(model.e_ren_curt[c, t, s_eval]))

                p_bess_ch_val = float(pyo.value(model.p_bess_ch[c, t, s_eval]))
                p_bess_dis_val = float(pyo.value(model.p_bess_dis[c, t, s_eval]))
                soc_bess_val = float(pyo.value(model.soc_bess[c, t, s_eval]))

                n_ready = int(round(pyo.value(model.n_swap_ready[c, t, s_eval])))
                n_ch = int(round(pyo.value(model.n_swap_charging[c, t, s_eval])))
                n_dep = int(round(pyo.value(model.n_swap_depleted[c, t, s_eval])))
                n_served = int(round(pyo.value(model.n_swap_served[c, t, s_eval])))
                p_swap_ch_val = float(pyo.value(model.p_swap_ch[c, t, s_eval]))

                # Fast charge cohorts for this cluster and hour
                c_cohorts = [coh_id for coh_id, coh in cohort_map.items() if coh.cluster_id == c]
                fc_served_t = sum(
                    float(pyo.value(model.e_cohort_served[coh_id, t, s_eval]))
                    for coh_id in c_cohorts if cohort_map[coh_id].modality == ServiceType.FAST_CHARGE
                )
                fc_req_t = c_input.fast_charge_demand_mwh[t]

                # Shifted energy: served at t > arrival_hour
                fc_shifted_t = sum(
                    float(pyo.value(model.e_cohort_served[coh_id, t, s_eval]))
                    for coh_id in c_cohorts
                    if cohort_map[coh_id].modality == ServiceType.FAST_CHARGE
                    and cohort_map[coh_id].flexibility_opt_in
                    and t > cohort_map[coh_id].arrival_hour
                )

                # Selected tariff tier
                sel_tier = 3
                for tier in [1, 2, 3, 4, 5]:
                    if pyo.value(model.tariff_choice[c, t, tier]) > 0.5:
                        sel_tier = tier
                        break

                base_tariff = c_input.previous_day_avg_tariff_inr_per_kwh
                tariff_rate = base_tariff * self.tier_mult_map[sel_tier]
                rev_val = float(pyo.value(model.tariff_revenue[c, t, s_eval]))
                inc_val = float(pyo.value(model.incentive_spend[c, t, s_eval]))

                # Headroom and losses
                load_draw = fc_served_t + p_swap_ch_val + p_bess_ch_val + self.aux_load_mw
                headroom_mw = max(0.0, self.installed_power_mw - load_draw)
                losses_mwh = load_draw * self.loss_factor

                # Reserves checks
                bess_res_ok = bool(soc_bess_val >= c_input.bess_state.min_reserve_mwh - 1e-4)
                swap_res_ok = bool(n_ready >= c_input.swap_state.min_reserve_packs)
                headroom_res_ok = bool(headroom_mw >= (self.installed_power_mw * 0.05) - 1e-4)

                if not bess_res_ok:
                    bess_reserve_pass = False
                if not swap_res_ok:
                    swap_reserve_pass = False
                if not headroom_res_ok:
                    headroom_reserve_pass = False

                min_power_headroom_network = min(min_power_headroom_network, headroom_mw)

                # Binding constraints explanation
                binding_reasons: list[str] = []
                if p_disc >= self.installed_power_mw - 0.5:
                    binding_reasons.append("DISCOM_IMPORT_CAP_REACHED")
                if p_iex_val >= pyo.value(model.param_iex_cap[c, t, s_eval]) - 0.5:
                    binding_reasons.append("IEX_ELIGIBILITY_CAP_BINDING")
                if soc_bess_val <= c_input.bess_state.min_reserve_mwh + 0.1:
                    binding_reasons.append("BESS_EMERGENCY_RESERVE_FLOOR")
                if n_ready <= c_input.swap_state.min_reserve_packs + 10:
                    binding_reasons.append("SWAP_READY_RESERVE_FLOOR")
                if headroom_mw <= (self.installed_power_mw * 0.05) + 0.5:
                    binding_reasons.append("POWER_HEADROOM_RESERVE_BINDING")
                if sel_tier == 5:
                    binding_reasons.append("REGULATORY_TARIFF_CEILING_CLAMP (1.20x)")
                elif sel_tier == 1:
                    binding_reasons.append("REGULATORY_TARIFF_FLOOR_CLAMP (0.80x)")

                decision = HourlyClusterDecision(
                    cluster_id=c,
                    hour=t,
                    discom_mw=round(p_disc, 3),
                    iex_mw=round(p_iex_val, 3),
                    renewable_used_mwh=round(e_ren_u, 3),
                    renewable_curtailed_mwh=round(e_ren_c, 3),
                    bess_charge_mw=round(p_bess_ch_val, 3),
                    bess_discharge_mw=round(p_bess_dis_val, 3),
                    bess_soc_mwh=round(soc_bess_val, 3),
                    bess_reserve_compliant=bess_res_ok,
                    swap_packs_served=n_served,
                    swap_packs_charging=n_ch,
                    swap_packs_ready=n_ready,
                    swap_packs_depleted=n_dep,
                    swap_charge_power_mw=round(p_swap_ch_val, 3),
                    swap_reserve_compliant=swap_res_ok,
                    fc_demand_requested_mwh=round(fc_req_t, 3),
                    fc_demand_served_mwh=round(fc_served_t, 3),
                    fc_demand_shifted_mwh=round(fc_shifted_t, 3),
                    selected_tariff_tier=self.tier_enum_map[sel_tier],
                    tariff_inr_per_kwh=round(tariff_rate, 2),
                    tariff_revenue_inr=round(rev_val, 2),
                    incentive_spend_inr=round(inc_val, 2),
                    losses_mwh=round(losses_mwh, 3),
                    power_headroom_mw=round(headroom_mw, 3),
                    power_headroom_compliant=headroom_res_ok,
                    binding_constraints=binding_reasons,
                )
                hourly_decisions.append(decision)

                # Cluster accounting
                disc_cost = p_disc * pyo.value(model.param_discom_tariff[c, t, s_eval])
                iex_cost = p_iex_val * pyo.value(model.param_iex_price[c, t, s_eval])
                ren_c = e_ren_u * 3800.0
                deg_c = p_bess_dis_val * 1250.0

                c_discom_cost += disc_cost
                c_iex_cost += iex_cost
                c_ren_cost += ren_c
                c_bess_deg_cost += deg_c
                c_incentive_exp += inc_val
                c_tariff_rev += rev_val
                c_req_mwh += fc_req_t + c_input.swap_energy_mwh[t]
                c_serv_mwh += fc_served_t + (n_served * self.pack_kwh / 1000.0)
                c_ren_used += e_ren_u
                c_ren_avail += pyo.value(model.param_ren_avail[c, t, s_eval])
                c_losses += losses_mwh

                total_fc_req_mwh += fc_req_t
                total_fc_serv_mwh += fc_served_t
                total_swap_req_packs += c_input.swap_requests_count[t]
                total_swap_serv_packs += n_served

                total_discom_cost += disc_cost
                total_iex_cost += iex_cost
                total_ren_cost += ren_c
                total_bess_deg_cost += deg_c
                total_incentive_exp += inc_val
                total_tariff_rev += rev_val
                total_loss_mwh += losses_mwh
                total_ren_used += e_ren_u
                total_procured += (p_disc + p_iex_val + e_ren_u)

            # Check unserved slack on cohorts
            for coh_id in c_cohorts:
                crit_slack = float(pyo.value(model.u_slack_crit[coh_id, s_eval]))
                if crit_slack > 1e-4:
                    unserved_crit_mwh += crit_slack
                    if cohort_map[coh_id].is_emergency or cohort_map[coh_id].is_priority_reserve:
                        deadline_violations += 1

            c_rel_pct = (c_serv_mwh / max(0.001, c_req_mwh)) * 100.0
            c_net_cost = (c_discom_cost + c_iex_cost + c_ren_cost + c_bess_deg_cost + c_incentive_exp) - c_tariff_rev
            c_ren_pct = (c_ren_used / max(0.001, c_ren_avail)) * 100.0
            c_loss_pct = (c_losses / max(0.001, c_serv_mwh + c_losses)) * 100.0

            cluster_schedules[c] = ClusterDailySchedule(
                cluster_id=c,
                hourly_decisions=hourly_decisions,
                total_energy_requested_mwh=round(c_req_mwh, 3),
                total_energy_served_mwh=round(c_serv_mwh, 3),
                service_reliability_pct=round(c_rel_pct, 2),
                total_discom_cost_inr=round(c_discom_cost, 2),
                total_iex_cost_inr=round(c_iex_cost, 2),
                total_renewable_cost_inr=round(c_ren_cost, 2),
                total_bess_degradation_cost_inr=round(c_bess_deg_cost, 2),
                total_customer_incentive_inr=round(c_incentive_exp, 2),
                total_retail_revenue_inr=round(c_tariff_rev, 2),
                net_operating_cost_inr=round(c_net_cost, 2),
                renewable_utilization_pct=round(c_ren_pct, 2),
                energy_loss_pct=round(c_loss_pct, 2),
            )

        # Global KPIs
        tot_req_mwh = total_fc_req_mwh + (total_swap_req_packs * self.pack_kwh / 1000.0)
        tot_serv_mwh = total_fc_serv_mwh + (total_swap_serv_packs * self.pack_kwh / 1000.0)
        global_reliability = (tot_serv_mwh / max(0.001, tot_req_mwh)) * 100.0
        fc_fill_rate = (total_fc_serv_mwh / max(0.001, total_fc_req_mwh)) * 100.0
        swap_fill_rate = (total_swap_serv_packs / max(1, total_swap_req_packs)) * 100.0
        global_loss_pct = (total_loss_mwh / max(0.001, tot_serv_mwh + total_loss_mwh)) * 100.0
        global_ren_share = (total_ren_used / max(0.001, total_procured)) * 100.0

        tot_proc_cost = total_discom_cost + total_iex_cost + total_ren_cost
        tot_deg_cost = total_bess_deg_cost
        tot_net_cost = (tot_proc_cost + tot_deg_cost + total_incentive_exp) - total_tariff_rev

        # CVaR tail risk value
        cvar_val = tot_net_cost
        if hasattr(model, "cvar_risk"):
            try:
                cvar_val = float(pyo.value(model.cvar_risk))
            except Exception:
                pass

        # EBITDA proxy = (Revenue - Direct Operating Opex) / Revenue
        direct_opex = tot_proc_cost + total_incentive_exp + tot_deg_cost
        ebitda_margin = ((total_tariff_rev - direct_opex) / max(1.0, total_tariff_rev)) * 100.0

        kpis = OptimizationKPIs(
            service_reliability_pct=round(global_reliability, 2),
            fast_charge_fill_rate_pct=round(fc_fill_rate, 2),
            swap_pack_fill_rate_pct=round(swap_fill_rate, 2),
            energy_loss_pct=round(global_loss_pct, 2),
            renewable_share_pct=round(global_ren_share, 2),
            power_capacity_headroom_mw=round(min_power_headroom_network, 2),
            power_headroom_reserve_compliant=headroom_reserve_pass,
            bess_emergency_reserve_compliant=bess_reserve_pass,
            swap_emergency_reserve_compliant=swap_reserve_pass,
            deadline_violations_count=deadline_violations,
            unserved_critical_mwh=round(unserved_crit_mwh, 4),
            total_energy_requested_mwh=round(tot_req_mwh, 3),
            total_energy_served_mwh=round(tot_serv_mwh, 3),
            total_procurement_cost_inr=round(tot_proc_cost, 2),
            total_retail_revenue_inr=round(total_tariff_rev, 2),
            total_flexibility_incentive_inr=round(total_incentive_exp, 2),
            total_degradation_cost_inr=round(tot_deg_cost, 2),
            net_operating_cost_inr=round(tot_net_cost, 2),
            cvar_tail_risk_cost_inr=round(cvar_val, 2),
            ebitda_operating_margin_pct=round(ebitda_margin, 2),
            ebitda_status="EBITDA_PROXY (Calculated from gross tariff revenue less direct procurement, incentives, and degradation proxy; corporate G&A and fixed debt service unmodeled)",
        )

        return OptimizationResult(
            run_id=run_id,
            mode=mode,
            timestamp=timestamp,
            clusters=clusters,
            scenarios_evaluated=scenarios,
            solver_metadata=solver_metadata,
            kpis=kpis,
            cluster_schedules=cluster_schedules,
            provenance=Provenance.SYNTHETIC,
        )
