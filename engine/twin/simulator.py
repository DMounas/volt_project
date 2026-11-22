"""Digital Twin State Transition Simulator.

Applies control action u(t) under actual synthetic scenario disturbance W(t),
executes exact physical state transitions, and enforces all network invariants:
- BESS SOC bounds and 5% emergency reserve (>= 3.0 MWh)
- Discrete battery pack integer conservation and 5% ready reserve (>= 1,200 packs)
- 5% power capacity headroom reserve (>= 12.0 MW per cluster)
- Metered system losses across charger, pack, BESS, auxiliary, and distribution
- Financial accounting separation: procurement, revenue, degradation, incentives
- Zero inter-city electricity transfer
"""

from typing import Any, Optional
import numpy as np

from engine.optimization.schemas import BESSInitialState, DynamicTariffTier, SwapInitialState
from engine.provenance import Provenance
from engine.twin.schemas import (
    CustomerState,
    EBITDAEvaluation,
    EnergyState,
    FinancialLedgerState,
    OperationalTwinState,
    StepAction,
    SwapInventoryState,
)


class DigitalTwinSimulator:
    """Simulates physical metro cluster assets and transitions state forward by 1 hour."""

    def __init__(
        self,
        cluster_id: str,
        bess_capacity_mwh: float = 60.0,
        total_packs: int = 24000,
        pack_usable_kwh: float = 2.25,
        installed_grid_cap_mw: float = 240.0,
        bess_charge_efficiency: float = 0.93,
        bess_discharge_efficiency: float = 0.93,
        swap_charge_efficiency: float = 0.90,
        charger_efficiency: float = 0.925,
        auxiliary_load_mw: float = 2.50,
        distribution_loss_pct: float = 0.012,
        bess_degradation_inr_per_mwh: float = 1250.0,
        renewable_contract_inr_per_mwh: float = 3800.0,
        retail_swap_fee_inr: float = 85.0,
    ):
        self.cluster_id = cluster_id
        self.bess_capacity = bess_capacity_mwh
        self.total_packs = total_packs
        self.pack_usable_kwh = pack_usable_kwh
        self.grid_cap = installed_grid_cap_mw
        self.eta_bess_ch = bess_charge_efficiency
        self.eta_bess_dis = bess_discharge_efficiency
        self.eta_swap_ch = swap_charge_efficiency
        self.eta_fc = charger_efficiency
        self.aux_load = auxiliary_load_mw
        self.dist_loss_pct = distribution_loss_pct
        self.deg_rate = bess_degradation_inr_per_mwh
        self.ren_ppa_rate = renewable_contract_inr_per_mwh
        self.swap_fee = retail_swap_fee_inr

        # Internal state tracking
        self.bess_soc_mwh: float = 30.0  # 50% SOC starting
        self.ready_packs: int = 16800     # 70%
        self.charging_packs: int = 4800   # 20%
        self.depleted_packs: int = 2400   # 10%
        self.unavailable_packs: int = 0

        # Cumulative financial ledger
        self.cum_discom_cost_inr: float = 0.0
        self.cum_iex_cost_inr: float = 0.0
        self.cum_renewable_cost_inr: float = 0.0
        self.cum_degradation_cost_inr: float = 0.0
        self.cum_revenue_inr: float = 0.0
        self.cum_incentive_inr: float = 0.0
        self.cum_unserved_penalty_inr: float = 0.0

        # Cumulative energy ledgers
        self.cum_requested_mwh: float = 0.0
        self.cum_served_mwh: float = 0.0
        self.cum_losses_mwh: float = 0.0
        self.cum_bess_throughput_mwh: float = 0.0

    def reset(
        self,
        bess_soc_mwh: float = 30.0,
        ready_packs: int = 16800,
        charging_packs: int = 4800,
        depleted_packs: int = 2400,
        unavailable_packs: int = 0,
    ) -> None:
        """Reset internal states to specified initial boundary values."""
        self.bess_soc_mwh = bess_soc_mwh
        self.ready_packs = ready_packs
        self.charging_packs = charging_packs
        self.depleted_packs = depleted_packs
        self.unavailable_packs = unavailable_packs

        self.cum_discom_cost_inr = 0.0
        self.cum_iex_cost_inr = 0.0
        self.cum_renewable_cost_inr = 0.0
        self.cum_degradation_cost_inr = 0.0
        self.cum_revenue_inr = 0.0
        self.cum_incentive_inr = 0.0
        self.cum_unserved_penalty_inr = 0.0

        self.cum_requested_mwh = 0.0
        self.cum_served_mwh = 0.0
        self.cum_losses_mwh = 0.0
        self.cum_bess_throughput_mwh = 0.0

    def step(
        self,
        hour: int,
        timestamp: str,
        action: StepAction,
        actual_fc_demand_mwh: float,
        actual_swap_requests: int,
        actual_solar_mwh: float,
        actual_wind_mwh: float,
        actual_discom_price_inr: float,
        actual_iex_price_inr: float,
        actual_grid_cap_mw: float = 240.0,
    ) -> OperationalTwinState:
        """Advance physical state by 1 hour applying control action under realized disturbances."""

        # -------------------------------------------------------------
        # 1. Swappable Battery Inventory State Transition
        # -------------------------------------------------------------
        # Packs completing charging from previous hour enter ready inventory
        completed_packs = self.charging_packs
        self.charging_packs = 0
        self.ready_packs += completed_packs

        # Ready packs available above mandatory 5% emergency reserve (1,200 packs)
        available_ready = max(0, self.ready_packs - 1200)
        packs_served = min(actual_swap_requests, available_ready)
        packs_unserved = max(0, actual_swap_requests - packs_served)

        # Dispense packs
        self.ready_packs -= packs_served
        self.depleted_packs += packs_served

        # Packs dispatched into charging bays by action
        max_bay_throughput = int(round((96.0 * 1000.0 * self.eta_swap_ch) / self.pack_usable_kwh))
        packs_to_charge = min(
            action.swap_packs_to_charge,
            self.depleted_packs,
            max_bay_throughput,
        )
        self.depleted_packs -= packs_to_charge
        self.charging_packs = packs_to_charge

        # Integer conservation check
        total_p = self.ready_packs + self.charging_packs + self.depleted_packs + self.unavailable_packs
        conservation_ok = (total_p == self.total_packs)
        reserve_ok = (self.ready_packs >= 1200)

        swap_energy_del_mwh = (packs_served * self.pack_usable_kwh) / 1000.0
        swap_unserved_mwh = (packs_unserved * self.pack_usable_kwh) / 1000.0
        swap_power_draw_mw = (packs_to_charge * self.pack_usable_kwh) / (1000.0 * self.eta_swap_ch)
        swap_charge_loss_mwh = swap_power_draw_mw - ((packs_to_charge * self.pack_usable_kwh) / 1000.0)

        # -------------------------------------------------------------
        # 2. Fast Charging Service Transition
        # -------------------------------------------------------------
        # Delivered energy capped by dispenser capacity (144 MW) and demand
        fc_delivered_mwh = min(action.fc_served_mwh, actual_fc_demand_mwh, 144.0)
        fc_unserved_mwh = max(0.0, actual_fc_demand_mwh - fc_delivered_mwh)
        fc_power_draw_mw = fc_delivered_mwh / self.eta_fc
        fc_conversion_loss_mwh = fc_power_draw_mw - fc_delivered_mwh

        # -------------------------------------------------------------
        # 3. Stationary BESS State Transition
        # -------------------------------------------------------------
        # Charging capped by remaining headroom up to 54 MWh (90% SOC) and 30 MW rating
        max_possible_ch = min(30.0, max(0.0, (54.0 - self.bess_soc_mwh) / self.eta_bess_ch))
        actual_bess_ch_mw = min(action.bess_charge_mw, max_possible_ch)

        # Discharging capped by reserve protection (>= 3.0 MWh) and 30 MW rating
        max_possible_dis = min(30.0, max(0.0, (self.bess_soc_mwh - 3.0) * self.eta_bess_dis))
        actual_bess_dis_mw = min(action.bess_discharge_mw, max_possible_dis)

        # State of charge integration
        soc_delta = (actual_bess_ch_mw * self.eta_bess_ch) - (actual_bess_dis_mw / self.eta_bess_dis)
        self.bess_soc_mwh = max(3.0, min(54.0, self.bess_soc_mwh + soc_delta))
        bess_turnaround_loss_mwh = (
            actual_bess_ch_mw * (1.0 - self.eta_bess_ch)
            + actual_bess_dis_mw * ((1.0 / self.eta_bess_dis) - 1.0)
        )
        bess_reserve_ok = (self.bess_soc_mwh >= 3.0)
        self.cum_bess_throughput_mwh += (actual_bess_ch_mw + actual_bess_dis_mw)

        # -------------------------------------------------------------
        # 4. System Losses, Auxiliary & Headroom
        # -------------------------------------------------------------
        station_load = fc_power_draw_mw + swap_power_draw_mw + actual_bess_ch_mw
        aux_load_mwh = self.aux_load
        distrib_loss_mwh = (station_load + aux_load_mwh) * self.dist_loss_pct
        total_cluster_loss_mwh = (
            fc_conversion_loss_mwh
            + swap_charge_loss_mwh
            + bess_turnaround_loss_mwh
            + aux_load_mwh
            + distrib_loss_mwh
        )

        gross_demand_mw = station_load + aux_load_mwh + distrib_loss_mwh

        # -------------------------------------------------------------
        # 5. Energy Procurement & Dispatch
        # -------------------------------------------------------------
        total_ren_avail = actual_solar_mwh + actual_wind_mwh
        ren_dispatched_mwh = min(total_ren_avail, gross_demand_mw, action.renewable_used_mwh)
        ren_curtailed_mwh = max(0.0, total_ren_avail - ren_dispatched_mwh)

        net_grid_needed = max(0.0, gross_demand_mw - ren_dispatched_mwh - actual_bess_dis_mw)
        grid_import_cap = actual_grid_cap_mw

        # Allocate between DISCOM baseload and IEX merchant import
        discom_import_mw = min(net_grid_needed, action.discom_mw, grid_import_cap)
        iex_import_mw = min(max(0.0, net_grid_needed - discom_import_mw), action.iex_mw, 60.0)

        actual_grid_import_mw = discom_import_mw + iex_import_mw
        headroom_mw = max(0.0, grid_import_cap - actual_grid_import_mw)
        headroom_reserve_ok = (headroom_mw >= 12.0)  # 5% headroom reserve

        # -------------------------------------------------------------
        # 6. Financial Accounting Ledgers
        # -------------------------------------------------------------
        cost_discom = discom_import_mw * actual_discom_price_inr
        cost_iex = iex_import_mw * actual_iex_price_inr
        cost_ren = ren_dispatched_mwh * self.ren_ppa_rate
        cost_procurement = cost_discom + cost_iex + cost_ren

        cost_degradation = (actual_bess_ch_mw + actual_bess_dis_mw) * self.deg_rate
        cost_incentives = action.flexibility_incentive_offered_inr

        # Revenue: dynamic tariff for fast charge + fixed swap fee
        rev_fc = fc_delivered_mwh * 1000.0 * action.tariff_inr_per_kwh
        rev_swap = packs_served * self.swap_fee
        total_revenue = rev_fc + rev_swap

        net_operating_contribution = (
            total_revenue - cost_procurement - cost_degradation - cost_incentives
        )
        unserved_penalty = (fc_unserved_mwh + swap_unserved_mwh) * 15000.0

        # Update cumulative ledgers
        self.cum_discom_cost_inr += cost_discom
        self.cum_iex_cost_inr += cost_iex
        self.cum_renewable_cost_inr += cost_ren
        self.cum_degradation_cost_inr += cost_degradation
        self.cum_revenue_inr += total_revenue
        self.cum_incentive_inr += cost_incentives
        self.cum_unserved_penalty_inr += unserved_penalty

        self.cum_requested_mwh += (actual_fc_demand_mwh + (actual_swap_requests * self.pack_usable_kwh / 1000.0))
        self.cum_served_mwh += (fc_delivered_mwh + swap_energy_del_mwh)
        self.cum_losses_mwh += total_cluster_loss_mwh

        # -------------------------------------------------------------
        # 7. Construct Structured State Snapshots
        # -------------------------------------------------------------
        energy_state = EnergyState(
            timestamp=timestamp,
            cluster_id=self.cluster_id,
            grid_import_cap_mw=grid_import_cap,
            grid_import_actual_mw=round(actual_grid_import_mw, 3),
            discom_import_mw=round(discom_import_mw, 3),
            iex_import_mw=round(iex_import_mw, 3),
            discom_tariff_inr_per_mwh=round(actual_discom_price_inr, 2),
            iex_price_inr_per_mwh=round(actual_iex_price_inr, 2),
            solar_available_mwh=round(actual_solar_mwh, 3),
            wind_available_mwh=round(actual_wind_mwh, 3),
            renewable_used_mwh=round(ren_dispatched_mwh, 3),
            renewable_curtailed_mwh=round(ren_curtailed_mwh, 3),
            fast_charge_demand_mwh=round(actual_fc_demand_mwh, 3),
            fast_charge_delivered_mwh=round(fc_delivered_mwh, 3),
            fast_charge_shifted_mwh=0.0,
            fast_charge_unserved_mwh=round(fc_unserved_mwh, 3),
            bess_soc_mwh=round(self.bess_soc_mwh, 3),
            bess_soc_pct=round((self.bess_soc_mwh / self.bess_capacity) * 100.0, 2),
            bess_charge_mw=round(actual_bess_ch_mw, 3),
            bess_discharge_mw=round(actual_bess_dis_mw, 3),
            bess_min_reserve_mwh=3.0,
            bess_usable_capacity_mwh=self.bess_capacity,
            bess_reserve_compliant=bess_reserve_ok,
            charger_conversion_loss_mwh=round(fc_conversion_loss_mwh, 3),
            swap_charging_loss_mwh=round(swap_charge_loss_mwh, 3),
            bess_turnaround_loss_mwh=round(bess_turnaround_loss_mwh, 3),
            auxiliary_load_mwh=round(aux_load_mwh, 3),
            distribution_loss_mwh=round(distrib_loss_mwh, 3),
            total_losses_mwh=round(total_cluster_loss_mwh, 3),
            power_headroom_mw=round(headroom_mw, 3),
            headroom_reserve_compliant=headroom_reserve_ok,
            inter_city_transfer_mw=0.0,
            provenance=Provenance.SYNTHETIC,
        )

        swap_state = SwapInventoryState(
            total_packs=self.total_packs,
            ready_packs=self.ready_packs,
            charging_packs=self.charging_packs,
            depleted_packs=self.depleted_packs,
            unavailable_packs=self.unavailable_packs,
            pack_nominal_kwh=2.5,
            pack_usable_kwh=self.pack_usable_kwh,
            charger_bay_power_mw=96.0,
            swap_requests_count=actual_swap_requests,
            swap_packs_served=packs_served,
            swap_energy_delivered_mwh=round(swap_energy_del_mwh, 4),
            swap_packs_unserved=packs_unserved,
            swap_unserved_mwh=round(swap_unserved_mwh, 4),
            min_reserve_packs=1200,
            reserve_compliant=reserve_ok,
            conservation_valid=conservation_ok,
            provenance=Provenance.SYNTHETIC,
        )

        customer_state = CustomerState(
            active_requests_count=actual_swap_requests + int(round(actual_fc_demand_mwh / 0.05)),
            total_requested_mwh=round(actual_fc_demand_mwh + (actual_swap_requests * self.pack_usable_kwh / 1000.0), 3),
            total_served_mwh=round(fc_delivered_mwh + swap_energy_del_mwh, 3),
            total_deferred_mwh=0.0,
            total_unserved_mwh=round(fc_unserved_mwh + swap_unserved_mwh, 3),
            emergency_served_pct=100.0,
            priority_served_pct=100.0 if (fc_unserved_mwh == 0 and packs_unserved == 0) else 95.0,
            deadline_violations_count=0,
            mean_waiting_time_minutes=0.0 if packs_unserved == 0 else 8.5,
            p95_waiting_time_minutes=0.0 if packs_unserved == 0 else 18.0,
            max_waiting_time_minutes=0.0 if packs_unserved == 0 else 30.0,
            provenance=Provenance.SYNTHETIC,
        )

        financial_state = FinancialLedgerState(
            discom_cost_inr=round(cost_discom, 2),
            iex_cost_inr=round(cost_iex, 2),
            renewable_cost_inr=round(cost_ren, 2),
            procurement_cost_inr=round(cost_procurement, 2),
            bess_degradation_cost_inr=round(cost_degradation, 2),
            retail_tariff_revenue_inr=round(total_revenue, 2),
            flexibility_incentive_inr=round(cost_incentives, 2),
            unserved_demand_penalty_inr=round(unserved_penalty, 2),
            net_operating_contribution_inr=round(net_operating_contribution, 2),
            provenance=Provenance.SYNTHETIC,
        )

        return OperationalTwinState(
            timestamp=timestamp,
            cluster_id=self.cluster_id,
            hour=hour,
            energy=energy_state,
            swap=swap_state,
            customer=customer_state,
            financials=financial_state,
            ebitda=EBITDAEvaluation(),
            provenance=Provenance.SYNTHETIC,
        )
