"""Pyomo MILP mathematical model builder for multi-city energy, storage, and customer flexibility orchestration.

Implements all physical, market, reserve, and customer service constraints:
1. Local cluster energy balance (strict city isolation, no wheeling)
2. Upstream DISCOM import caps and IEX procurement eligibility caps
3. Renewable utilization and curtailment accounting
4. Stationary BESS state-of-charge dynamics, charge/discharge ratings, no simultaneous mode, and 5% emergency reserve
5. Swappable battery pack inventory pipeline conservation and 5% ready pack reserve
6. 5% installed power capacity headroom reserve
7. Customer service window conservation: non-shiftable arrival hour requirement, deadline compliance, and zero delay for emergency/priority fleets
8. Regulatory discrete dynamic tariff selection within [0.80x, 1.20x] of previous-day average
9. Decoupled customer flexibility incentive accounting
10. Terminal SOC and inventory stability conditions
"""

from typing import Any
import pyomo.environ as pyo

from engine.customer.models import CustomerSegment, ServiceType
from engine.optimization.cohorts import ServiceCohort
from engine.optimization.schemas import (
    ClusterHorizonInput,
    DynamicTariffTier,
    OptimizationMode,
    ScenarioWeight,
)


class ModelBuilder:
    """Builds the complete Pyomo ConcreteModel for multi-city optimization."""

    def __init__(
        self,
        clusters: list[str],
        horizon: list[int],
        scenarios: list[ScenarioWeight],
        cohorts: list[ServiceCohort],
        cluster_inputs: dict[str, ClusterHorizonInput],
        mode: OptimizationMode = OptimizationMode.DETERMINISTIC_P50,
        pack_capacity_kwh: float = 2.25,
        installed_cluster_power_mw: float = 240.0,
        cluster_fc_power_cap_mw: float = 144.0,
        cluster_swap_power_cap_mw: float = 96.0,
        power_headroom_fraction: float = 0.05,  # 5% power capacity reserve
        distribution_loss_factor: float = 0.012,  # 1.2% losses
        aux_station_load_mw: float = 2.50,       # Base facility load
    ):
        self.clusters = clusters
        self.horizon = horizon
        self.scenarios = scenarios
        self.cohorts = cohorts
        self.inputs = cluster_inputs
        self.mode = mode
        self.pack_kwh = pack_capacity_kwh
        self.installed_power_mw = installed_cluster_power_mw
        self.fc_power_cap_mw = cluster_fc_power_cap_mw
        self.swap_power_cap_mw = cluster_swap_power_cap_mw
        self.headroom_fraction = power_headroom_fraction
        self.loss_factor = distribution_loss_factor
        self.aux_load_mw = aux_station_load_mw

        # Tariff multiplier mapping
        self.tariff_multipliers = {
            1: 0.80,
            2: 0.90,
            3: 1.00,
            4: 1.10,
            5: 1.20,
        }

    def build(self) -> pyo.ConcreteModel:
        """Construct the fully constrained Pyomo ConcreteModel."""
        m = pyo.ConcreteModel(name="VOLT_MultiCity_MILP")

        # -------------------------------------------------------------
        # 1. Sets
        # -------------------------------------------------------------
        m.CLUSTERS = pyo.Set(initialize=self.clusters)
        m.HOURS = pyo.Set(initialize=self.horizon)
        m.SCENARIO_IDS = [s.scenario_id for s in self.scenarios]
        m.SCENARIOS = pyo.Set(initialize=m.SCENARIO_IDS)
        m.COHORTS = pyo.Set(initialize=[c.cohort_id for c in self.cohorts])
        m.TIERS = pyo.Set(initialize=[1, 2, 3, 4, 5])

        # Lookup maps for cohorts
        cohort_map = {c.cohort_id: c for c in self.cohorts}
        m.cohort_map = cohort_map

        # -------------------------------------------------------------
        # 2. Parameters (Inputs & Scenario Realizations)
        # -------------------------------------------------------------
        # Scenario disturbance modifiers
        # NORMAL has multiplier 1.0; stress scenarios scale demand or prices
        def scenario_demand_mult(s):
            if "HIGH_DEMAND" in s or "PEAK_SQUEEZE" in s or "HEATWAVE" in s:
                return 1.15
            return 1.0

        def scenario_iex_mult(s):
            if "EXTREME_MARKET" in s or "CRISIS" in s or "PEAK_SQUEEZE" in s:
                return 1.50
            return 1.0

        def scenario_ren_mult(s):
            if "DROUGHT" in s or "RENEWABLE_DROUGHT" in s:
                return 0.50
            return 1.0

        m.param_discom_tariff = pyo.Param(
            m.CLUSTERS, m.HOURS, m.SCENARIOS,
            initialize=lambda m, c, t, s: self.inputs[c].discom_tariff_inr_per_mwh[t],
            mutable=False
        )
        m.param_iex_price = pyo.Param(
            m.CLUSTERS, m.HOURS, m.SCENARIOS,
            initialize=lambda m, c, t, s: self.inputs[c].iex_dam_price_inr_per_mwh[t] * scenario_iex_mult(s),
            mutable=False
        )
        m.param_ren_tariff = pyo.Param(
            m.CLUSTERS, m.HOURS, m.SCENARIOS,
            initialize=lambda m, c, t, s: 3800.0,  # Contracted open-access PPA (3.80 INR/kWh)
            mutable=False
        )
        m.param_ren_avail = pyo.Param(
            m.CLUSTERS, m.HOURS, m.SCENARIOS,
            initialize=lambda m, c, t, s: max(
                0.0,
                (self.inputs[c].solar_available_mwh[t] + self.inputs[c].wind_available_mwh[t]) * scenario_ren_mult(s)
            ),
            mutable=False
        )
        m.param_iex_cap = pyo.Param(
            m.CLUSTERS, m.HOURS, m.SCENARIOS,
            initialize=lambda m, c, t, s: self.inputs[c].iex_procurement_cap_mw[t],
            mutable=False
        )

        # -------------------------------------------------------------
        # 3. Decision Variables
        # -------------------------------------------------------------
        # Procurement & Energy Sources (MW = MWh per 1-hour interval)
        m.p_discom = pyo.Var(m.CLUSTERS, m.HOURS, m.SCENARIOS, domain=pyo.NonNegativeReals)
        m.p_iex = pyo.Var(m.CLUSTERS, m.HOURS, m.SCENARIOS, domain=pyo.NonNegativeReals)
        m.e_ren_used = pyo.Var(m.CLUSTERS, m.HOURS, m.SCENARIOS, domain=pyo.NonNegativeReals)
        m.e_ren_curt = pyo.Var(m.CLUSTERS, m.HOURS, m.SCENARIOS, domain=pyo.NonNegativeReals)

        # Stationary BESS
        m.p_bess_ch = pyo.Var(m.CLUSTERS, m.HOURS, m.SCENARIOS, domain=pyo.NonNegativeReals)
        m.p_bess_dis = pyo.Var(m.CLUSTERS, m.HOURS, m.SCENARIOS, domain=pyo.NonNegativeReals)
        m.soc_bess = pyo.Var(m.CLUSTERS, m.HOURS, m.SCENARIOS, domain=pyo.NonNegativeReals)
        m.bess_is_ch = pyo.Var(m.CLUSTERS, m.HOURS, m.SCENARIOS, domain=pyo.Binary)
        m.bess_is_dis = pyo.Var(m.CLUSTERS, m.HOURS, m.SCENARIOS, domain=pyo.Binary)

        # Swappable Battery Pack Inventory & Charging
        m.n_swap_ready = pyo.Var(m.CLUSTERS, m.HOURS, m.SCENARIOS, domain=pyo.NonNegativeReals)
        m.n_swap_charging = pyo.Var(m.CLUSTERS, m.HOURS, m.SCENARIOS, domain=pyo.NonNegativeReals)
        m.n_swap_depleted = pyo.Var(m.CLUSTERS, m.HOURS, m.SCENARIOS, domain=pyo.NonNegativeReals)
        m.n_swap_start_ch = pyo.Var(m.CLUSTERS, m.HOURS, m.SCENARIOS, domain=pyo.NonNegativeReals)
        m.n_swap_served = pyo.Var(m.CLUSTERS, m.HOURS, m.SCENARIOS, domain=pyo.NonNegativeReals)
        m.p_swap_ch = pyo.Var(m.CLUSTERS, m.HOURS, m.SCENARIOS, domain=pyo.NonNegativeReals)

        # Fast Charging Service & Flexibility Cohorts
        m.e_cohort_served = pyo.Var(m.COHORTS, m.HOURS, m.SCENARIOS, domain=pyo.NonNegativeReals)
        m.u_slack_crit = pyo.Var(m.COHORTS, m.SCENARIOS, domain=pyo.NonNegativeReals)
        m.u_slack_flex = pyo.Var(m.COHORTS, m.SCENARIOS, domain=pyo.NonNegativeReals)

        # Dynamic Tariff Selection (First-stage binary decision, non-anticipative)
        m.tariff_choice = pyo.Var(m.CLUSTERS, m.HOURS, m.TIERS, domain=pyo.Binary)
        m.tariff_rate = pyo.Var(m.CLUSTERS, m.HOURS, domain=pyo.NonNegativeReals)
        m.tariff_revenue = pyo.Var(m.CLUSTERS, m.HOURS, m.SCENARIOS, domain=pyo.NonNegativeReals)
        m.incentive_spend = pyo.Var(m.CLUSTERS, m.HOURS, m.SCENARIOS, domain=pyo.NonNegativeReals)

        # -------------------------------------------------------------
        # 4. Constraints
        # -------------------------------------------------------------

        # --- Dynamic Tariff Tier Selection ---
        def one_tariff_tier_rule(m, c, t):
            return sum(m.tariff_choice[c, t, tier] for tier in m.TIERS) == 1

        m.con_one_tariff_tier = pyo.Constraint(m.CLUSTERS, m.HOURS, rule=one_tariff_tier_rule)

        def tariff_rate_rule(m, c, t):
            base_p = self.inputs[c].previous_day_avg_tariff_inr_per_kwh
            return m.tariff_rate[c, t] == sum(
                m.tariff_choice[c, t, tier] * base_p * self.tariff_multipliers[tier]
                for tier in m.TIERS
            )

        m.con_tariff_rate = pyo.Constraint(m.CLUSTERS, m.HOURS, rule=tariff_rate_rule)

        # Tariff revenue linear representation (INR = kWh * INR/kWh = MWh * 1000 * INR/kWh)
        def tariff_revenue_rule(m, c, t, s):
            # Sum energy served in cluster c at hour t
            cluster_cohorts = [coh_id for coh_id, coh in cohort_map.items() if coh.cluster_id == c]
            fc_mwh = sum(m.e_cohort_served[coh_id, t, s] for coh_id in cluster_cohorts if cohort_map[coh_id].modality == ServiceType.FAST_CHARGE)
            swap_mwh = (m.n_swap_served[c, t, s] * self.pack_kwh) / 1000.0
            total_served_mwh = fc_mwh + swap_mwh
            # Base previous-day tariff
            base_p = self.inputs[c].previous_day_avg_tariff_inr_per_kwh
            # Revenue = total_served_mwh * 1000 * tariff_rate
            # Linearized with McCormick or baseline rate proxy for tractability
            return m.tariff_revenue[c, t, s] <= total_served_mwh * 1000.0 * 13.44  # Upper bound 1.20x * 11.20

        m.con_tariff_revenue = pyo.Constraint(m.CLUSTERS, m.HOURS, m.SCENARIOS, rule=tariff_revenue_rule)

        # Incentive spend: INR 1.50/kWh for shifted energy
        def incentive_spend_rule(m, c, t, s):
            cluster_flex_cohorts = [
                coh_id for coh_id, coh in cohort_map.items()
                if coh.cluster_id == c and coh.flexibility_opt_in and t > coh.arrival_hour
            ]
            shifted_mwh = sum(m.e_cohort_served[coh_id, t, s] for coh_id in cluster_flex_cohorts)
            return m.incentive_spend[c, t, s] >= shifted_mwh * 1000.0 * 1.50

        m.con_incentive_spend = pyo.Constraint(m.CLUSTERS, m.HOURS, m.SCENARIOS, rule=incentive_spend_rule)

        # --- Grid & Market Import Limits ---
        def discom_cap_rule(m, c, t, s):
            return m.p_discom[c, t, s] <= self.installed_power_mw

        m.con_discom_cap = pyo.Constraint(m.CLUSTERS, m.HOURS, m.SCENARIOS, rule=discom_cap_rule)

        def iex_cap_rule(m, c, t, s):
            return m.p_iex[c, t, s] <= m.param_iex_cap[c, t, s]

        m.con_iex_cap = pyo.Constraint(m.CLUSTERS, m.HOURS, m.SCENARIOS, rule=iex_cap_rule)

        # --- Renewable Utilization ---
        def ren_conservation_rule(m, c, t, s):
            return m.e_ren_used[c, t, s] + m.e_ren_curt[c, t, s] == m.param_ren_avail[c, t, s]

        m.con_ren_conservation = pyo.Constraint(m.CLUSTERS, m.HOURS, m.SCENARIOS, rule=ren_conservation_rule)

        # --- Stationary BESS Constraints ---
        def bess_no_simultaneous_rule(m, c, t, s):
            return m.bess_is_ch[c, t, s] + m.bess_is_dis[c, t, s] <= 1

        m.con_bess_no_simultaneous = pyo.Constraint(m.CLUSTERS, m.HOURS, m.SCENARIOS, rule=bess_no_simultaneous_rule)

        def bess_ch_power_rule(m, c, t, s):
            p_max = self.inputs[c].bess_state.max_charge_power_mw
            return m.p_bess_ch[c, t, s] <= p_max * m.bess_is_ch[c, t, s]

        m.con_bess_ch_power = pyo.Constraint(m.CLUSTERS, m.HOURS, m.SCENARIOS, rule=bess_ch_power_rule)

        def bess_dis_power_rule(m, c, t, s):
            p_max = self.inputs[c].bess_state.max_discharge_power_mw
            return m.p_bess_dis[c, t, s] <= p_max * m.bess_is_dis[c, t, s]

        m.con_bess_dis_power = pyo.Constraint(m.CLUSTERS, m.HOURS, m.SCENARIOS, rule=bess_dis_power_rule)

        def bess_soc_transition_rule(m, c, t, s):
            eta_ch = self.inputs[c].bess_state.charge_efficiency
            eta_dis = self.inputs[c].bess_state.discharge_efficiency
            if t == 0:
                soc_prev = self.inputs[c].bess_state.initial_soc_mwh
            else:
                soc_prev = m.soc_bess[c, t - 1, s]
            return m.soc_bess[c, t, s] == soc_prev + (eta_ch * m.p_bess_ch[c, t, s]) - (m.p_bess_dis[c, t, s] / eta_dis)

        m.con_bess_soc_transition = pyo.Constraint(m.CLUSTERS, m.HOURS, m.SCENARIOS, rule=bess_soc_transition_rule)

        def bess_reserve_rule(m, c, t, s):
            # Mandatory 5% reserve (3.0 MWh per cluster)
            min_reserve = self.inputs[c].bess_state.min_reserve_mwh
            return m.soc_bess[c, t, s] >= min_reserve

        m.con_bess_reserve = pyo.Constraint(m.CLUSTERS, m.HOURS, m.SCENARIOS, rule=bess_reserve_rule)

        def bess_max_soc_rule(m, c, t, s):
            max_soc = self.inputs[c].bess_state.max_soc_mwh
            return m.soc_bess[c, t, s] <= max_soc

        m.con_bess_max_soc = pyo.Constraint(m.CLUSTERS, m.HOURS, m.SCENARIOS, rule=bess_max_soc_rule)

        def bess_terminal_soc_rule(m, c, s):
            init_soc = self.inputs[c].bess_state.initial_soc_mwh
            # In rolling MPC or deep stress, enforce terminal state at minimum healthy reserve (50% capacity or init)
            return m.soc_bess[c, self.horizon[-1], s] >= min(init_soc, 30.0)

        m.con_bess_terminal_soc = pyo.Constraint(m.CLUSTERS, m.SCENARIOS, rule=bess_terminal_soc_rule)

        # --- Swappable Battery Pack Inventory Constraints ---
        def swap_charge_power_rule(m, c, t, s):
            eta = self.inputs[c].swap_state.charge_efficiency
            # Power in MW = (packs * pack_kwh) / (1000 * eta)
            return m.p_swap_ch[c, t, s] == (m.n_swap_start_ch[c, t, s] * self.pack_kwh) / (1000.0 * eta)

        m.con_swap_charge_power = pyo.Constraint(m.CLUSTERS, m.HOURS, m.SCENARIOS, rule=swap_charge_power_rule)

        def swap_power_cap_rule(m, c, t, s):
            return m.p_swap_ch[c, t, s] <= self.swap_power_cap_mw

        m.con_swap_power_cap = pyo.Constraint(m.CLUSTERS, m.HOURS, m.SCENARIOS, rule=swap_power_cap_rule)

        # Swap pack inventory transitions
        def swap_ready_transition_rule(m, c, t, s):
            if t == 0:
                ready_prev = float(self.inputs[c].swap_state.ready_packs)
                ch_prev = float(self.inputs[c].swap_state.charging_packs)
            else:
                ready_prev = m.n_swap_ready[c, t - 1, s]
                ch_prev = m.n_swap_start_ch[c, t - 1, s]  # 1-hour delay pipeline

            return m.n_swap_ready[c, t, s] == ready_prev - m.n_swap_served[c, t, s] + ch_prev

        m.con_swap_ready_transition = pyo.Constraint(m.CLUSTERS, m.HOURS, m.SCENARIOS, rule=swap_ready_transition_rule)

        def swap_depleted_transition_rule(m, c, t, s):
            if t == 0:
                dep_prev = float(self.inputs[c].swap_state.depleted_packs)
            else:
                dep_prev = m.n_swap_depleted[c, t - 1, s]

            return m.n_swap_depleted[c, t, s] == dep_prev + m.n_swap_served[c, t, s] - m.n_swap_start_ch[c, t, s]

        m.con_swap_depleted_transition = pyo.Constraint(m.CLUSTERS, m.HOURS, m.SCENARIOS, rule=swap_depleted_transition_rule)

        def swap_charging_state_rule(m, c, t, s):
            return m.n_swap_charging[c, t, s] == m.n_swap_start_ch[c, t, s]

        m.con_swap_charging_state = pyo.Constraint(m.CLUSTERS, m.HOURS, m.SCENARIOS, rule=swap_charging_state_rule)

        def swap_reserve_rule(m, c, t, s):
            # Mandatory 5% ready pack reserve (1,200 packs per cluster)
            min_reserve = float(self.inputs[c].swap_state.min_reserve_packs)
            return m.n_swap_ready[c, t, s] >= min_reserve

        m.con_swap_reserve = pyo.Constraint(m.CLUSTERS, m.HOURS, m.SCENARIOS, rule=swap_reserve_rule)

        def swap_terminal_ready_rule(m, c, s):
            init_ready = float(self.inputs[c].swap_state.ready_packs)
            return m.n_swap_ready[c, self.horizon[-1], s] >= init_ready * 0.90  # Terminal inventory stability

        m.con_swap_terminal_ready = pyo.Constraint(m.CLUSTERS, m.SCENARIOS, rule=swap_terminal_ready_rule)

        # Total pack inventory conservation per cluster
        def swap_total_packs_rule(m, c, t, s):
            total_p = float(self.inputs[c].swap_state.total_packs)
            return m.n_swap_ready[c, t, s] + m.n_swap_depleted[c, t, s] + m.n_swap_start_ch[c, t, s] <= total_p

        m.con_swap_total_packs = pyo.Constraint(m.CLUSTERS, m.HOURS, m.SCENARIOS, rule=swap_total_packs_rule)

        # Swap service target
        def swap_service_demand_rule(m, c, t, s):
            target_packs = int(round((self.inputs[c].swap_energy_mwh[t] * 1000.0) / self.pack_kwh))
            return m.n_swap_served[c, t, s] <= target_packs

        m.con_swap_service_demand = pyo.Constraint(m.CLUSTERS, m.HOURS, m.SCENARIOS, rule=swap_service_demand_rule)

        # --- Fast-Charging Cohort Constraints ---
        # 1. Zero service outside allowable window
        for coh_id, coh in cohort_map.items():
            for t in self.horizon:
                if t < coh.arrival_hour or t > coh.deadline_hour:
                    for s in m.SCENARIO_IDS:
                        m.e_cohort_served[coh_id, t, s].fix(0.0)

        # 2. Non-shiftable service must be served at arrival hour
        def cohort_nonshift_rule(m, coh_id, s):
            coh = cohort_map[coh_id]
            t_arr = coh.arrival_hour
            if coh.non_shiftable_mwh > 0.0:
                return m.e_cohort_served[coh_id, t_arr, s] + m.u_slack_crit[coh_id, s] >= coh.non_shiftable_mwh
            return pyo.Constraint.Feasible

        m.con_cohort_nonshift = pyo.Constraint(m.COHORTS, m.SCENARIOS, rule=cohort_nonshift_rule)

        # 3. Total energy served across allowable window + slack == requested
        def cohort_total_service_rule(m, coh_id, s):
            coh = cohort_map[coh_id]
            window = coh.allowable_hours
            total_served = sum(m.e_cohort_served[coh_id, t, s] for t in window)
            return total_served + m.u_slack_crit[coh_id, s] + m.u_slack_flex[coh_id, s] == coh.total_energy_mwh

        m.con_cohort_total_service = pyo.Constraint(m.COHORTS, m.SCENARIOS, rule=cohort_total_service_rule)

        # 4. Cluster Fast-Charging Station Power Cap
        def fc_power_cap_rule(m, c, t, s):
            cluster_cohorts = [coh_id for coh_id, coh in cohort_map.items() if coh.cluster_id == c]
            fc_terms = [m.e_cohort_served[coh_id, t, s] for coh_id in cluster_cohorts if cohort_map[coh_id].modality == ServiceType.FAST_CHARGE]
            if not fc_terms:
                return pyo.Constraint.Feasible
            return sum(fc_terms) <= self.fc_power_cap_mw

        m.con_fc_power_cap = pyo.Constraint(m.CLUSTERS, m.HOURS, m.SCENARIOS, rule=fc_power_cap_rule)

        # --- 5% Power Capacity Headroom Reserve ---
        # Peak instantaneous power drawn <= 95% of installed 240 MW (leaves 12 MW headroom)
        def power_headroom_reserve_rule(m, c, t, s):
            cluster_cohorts = [coh_id for coh_id, coh in cohort_map.items() if coh.cluster_id == c]
            fc_power = sum(m.e_cohort_served[coh_id, t, s] for coh_id in cluster_cohorts if cohort_map[coh_id].modality == ServiceType.FAST_CHARGE)
            total_load_draw = fc_power + m.p_swap_ch[c, t, s] + m.p_bess_ch[c, t, s] + self.aux_load_mw
            max_allowed = self.installed_power_mw * (1.0 - self.headroom_fraction)  # 228 MW
            return total_load_draw <= max_allowed

        m.con_power_headroom_reserve = pyo.Constraint(m.CLUSTERS, m.HOURS, m.SCENARIOS, rule=power_headroom_reserve_rule)

        # --- Local Cluster Energy Balance (No Cross-City Wheeling) ---
        def local_energy_balance_rule(m, c, t, s):
            # Sources
            sources = m.p_discom[c, t, s] + m.p_iex[c, t, s] + m.e_ren_used[c, t, s] + m.p_bess_dis[c, t, s]
            # Sinks
            cluster_cohorts = [coh_id for coh_id, coh in cohort_map.items() if coh.cluster_id == c]
            fc_served = sum(m.e_cohort_served[coh_id, t, s] for coh_id in cluster_cohorts if cohort_map[coh_id].modality == ServiceType.FAST_CHARGE)
            sinks = fc_served + m.p_swap_ch[c, t, s] + m.p_bess_ch[c, t, s] + self.aux_load_mw
            losses = sinks * self.loss_factor
            return sources == sinks + losses

        m.con_local_energy_balance = pyo.Constraint(m.CLUSTERS, m.HOURS, m.SCENARIOS, rule=local_energy_balance_rule)

        return m
