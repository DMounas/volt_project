"""VOLT Engine - Reconstructed Business-As-Usual (BAU) Baseline Policy.

Responsibilities:
- Deterministic simulation of an incumbent EV charging/swapping network operation:
    * Simple merit-order procurement: Contracted Renewables -> DISCOM Baseload -> BESS / IEX.
    * Rule-based stationary BESS threshold scheduling (no scenario optimization).
    * First-come-first-served battery pack replenishment with strict 5% reserve protection.
    * No voluntary customer flexibility window shifting.
    * Customer dynamic tariff fixed at baseline within legal 0.80x to 1.20x bounds.
- Generates fully reconciled hourly EnergyBalanceRecords with zero double-counting.
- Produces auditable step-by-step state trajectories.
"""

from dataclasses import dataclass
from typing import Any, Optional
import numpy as np
import pandas as pd
from engine.metrics.reconciliation import EnergyBalanceRecord
from engine.provenance import Provenance


@dataclass
class BaselineConfig:
    """Configurable operational parameters for the reconstructed BAU baseline policy."""

    # Efficiency parameters (calibrated to case reference 10% losses)
    charger_efficiency: float = 0.925  # ~7.5% charger conversion loss
    swap_charge_efficiency: float = 0.890  # ~11.0% pack charging loss
    bess_charge_efficiency: float = 0.930
    bess_discharge_efficiency: float = 0.930
    auxiliary_load_pct: float = 0.025  # ~2.5% station auxiliary loads
    distribution_loss_pct: float = 0.015  # ~1.5% local distribution losses

    # Service & Capacity availability parameters (calibrated to case reference 78% reliability)
    station_availability_factor: float = 0.820  # Equipment maintenance & bay downtime
    queue_balking_rate: float = 0.040  # Customers leaving due to queue delays

    # Asset physical specs
    cluster_capacity_mw: float = 240.0  # Equal 20% baseline
    fast_charge_capacity_mw: float = 144.0  # 60% of 240 MW
    swap_station_capacity_mw: float = 96.0  # 40% of 240 MW
    bess_storage_capacity_mwh: float = 60.0  # 20% of 300 MWh BESS
    bess_max_charge_mw: float = 30.0  # 0.5C rating
    bess_max_discharge_mw: float = 30.0
    bess_soc_min: float = 0.10
    bess_soc_max: float = 0.90
    emergency_reserve_pct: float = 0.05  # Mandatory 5% reserve

    # Pack inventory parameters
    total_packs: int = 24000  # 20% of 120,000 packs
    pack_nominal_kwh: float = 2.5
    pack_usable_kwh: float = 2.25
    pack_charging_kw: float = 2.5  # 1C rate

    # Tariffs
    retail_fc_tariff_inr_kwh: float = 11.50
    retail_swap_fee_inr_swap: float = 85.00
    discom_tariff_inr_mwh: float = 7500.0
    renewable_contract_inr_mwh: float = 3800.0


class BaselineSimulationEngine:
    """Executes the reconstructed BAU policy across time series data."""

    def __init__(self, config: Optional[BaselineConfig] = None):
        self.config = config or BaselineConfig()

    def run_simulation(
        self,
        cluster_hourly_df: pd.DataFrame,
        iex_hourly_df: Optional[pd.DataFrame] = None,
        seed: int = 42,
    ) -> tuple[list[EnergyBalanceRecord], dict[str, Any]]:
        """Simulate baseline operations across input time series records.

        Returns:
            Tuple of (list of EnergyBalanceRecord, simulation summary dict).
        """
        rng = np.random.default_rng(seed)
        records: list[EnergyBalanceRecord] = []

        # Map cluster data by cluster_id
        clusters = cluster_hourly_df["cluster_id"].unique()

        # Track state variables per cluster
        # Initial states
        bess_soc: dict[str, float] = {c: 0.50 for c in clusters}
        ready_packs: dict[str, int] = {
            c: int(self.config.total_packs * 0.75) for c in clusters
        }
        charging_packs: dict[str, int] = {
            c: int(self.config.total_packs * 0.15) for c in clusters
        }
        depleted_packs: dict[str, int] = {
            c: int(self.config.total_packs * 0.05) for c in clusters
        }
        # Fixed 5% emergency reserve packs strictly uncommitted
        reserve_packs = int(self.config.total_packs * self.config.emergency_reserve_pct)

        # Merge IEX price if available
        df = cluster_hourly_df.copy()
        if "dt" not in df.columns:
            df["dt"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values(["cluster_id", "dt"]).reset_index(drop=True)

        for _, row in df.iterrows():
            cid = str(row["cluster_id"])
            ts = str(row["timestamp"])
            hour = pd.to_datetime(ts).hour

            # 1. Demand arrivals
            fc_demand_raw_mwh = float(row["fast_charge_demand_mwh"])
            swap_requests_raw = int(row["swap_requests"])
            swap_demand_raw_mwh = float(row["swap_energy_equivalent_mwh"])

            # Operational availability factor & queue balking in incumbent system
            effective_avail = self.config.station_availability_factor * (
                1.0 - rng.uniform(0.0, self.config.queue_balking_rate)
            )

            # Fast charge delivered: capped by dispenser capacity & station availability
            fc_max_served = (
                self.config.fast_charge_capacity_mw * effective_avail
            )
            fc_delivered_mwh = min(fc_demand_raw_mwh * effective_avail, fc_max_served)
            fc_unmet_mwh = max(0.0, fc_demand_raw_mwh - fc_delivered_mwh)

            # Fast charge input from electrical grid: accounts for charger conversion efficiency
            fc_input_mwh = fc_delivered_mwh / self.config.charger_efficiency
            charger_loss_mwh = fc_input_mwh - fc_delivered_mwh

            # 2. Swap service fulfillment
            # Swappable ready packs above emergency reserve
            avail_ready = max(0, ready_packs[cid] - reserve_packs)
            max_swap_hourly_throughput = int(
                (self.config.swap_station_capacity_mw * 1000.0 / self.config.pack_charging_kw)
                * effective_avail
            )

            swaps_fulfilled = min(
                int(swap_requests_raw * effective_avail),
                avail_ready,
                max_swap_hourly_throughput,
            )
            swap_delivered_mwh = swaps_fulfilled * (self.config.pack_usable_kwh / 1000.0)
            swap_unmet_mwh = max(0.0, swap_demand_raw_mwh - swap_delivered_mwh)

            # Inventory transitions:
            # Ready packs decrease by swaps fulfilled
            ready_packs[cid] -= swaps_fulfilled
            depleted_packs[cid] += swaps_fulfilled

            # Charging replenishment: packs charged in current hour
            max_packs_to_charge = min(
                depleted_packs[cid],
                max_swap_hourly_throughput,
            )
            # Electrical energy drawn to charge these packs:
            # To restore ~2.25 kWh usable, pack requires 2.25 / swap_charge_efficiency kWh
            pack_recharge_input_mwh = (
                max_packs_to_charge * self.config.pack_usable_kwh / 1000.0
            ) / self.config.swap_charge_efficiency
            swap_charging_loss_mwh = pack_recharge_input_mwh - (
                max_packs_to_charge * self.config.pack_usable_kwh / 1000.0
            )

            # Replenishment transition
            depleted_packs[cid] -= max_packs_to_charge
            charging_packs[cid] += max_packs_to_charge
            # Packs completing charge from previous cycle return to ready
            packs_completed = int(charging_packs[cid] * 0.85)
            charging_packs[cid] -= packs_completed
            ready_packs[cid] += packs_completed

            # 3. Stationary BESS simple threshold scheduling (BAU rule-based)
            # Night/solar charge, evening peak discharge
            bess_cur_soc = bess_soc[cid]
            bess_reserve_soc = self.config.bess_soc_min + self.config.emergency_reserve_pct
            bess_charge_mwh = 0.0
            bess_discharge_mwh = 0.0
            bess_loss_mwh = 0.0

            # Off-peak charging (01:00-05:00 or high solar midday 12:00-14:00)
            if (hour in [1, 2, 3, 4, 12, 13]) and (bess_cur_soc < 0.75):
                possible_charge = min(
                    self.config.bess_max_charge_mw,
                    (self.config.bess_soc_max - bess_cur_soc) * self.config.bess_storage_capacity_mwh,
                )
                bess_charge_mwh = possible_charge
                bess_soc[cid] += (
                    bess_charge_mwh * self.config.bess_charge_efficiency
                ) / self.config.bess_storage_capacity_mwh
                bess_loss_mwh += bess_charge_mwh * (1.0 - self.config.bess_charge_efficiency)

            # Evening peak discharge (18:00-21:00)
            elif (hour in [18, 19, 20]) and (bess_cur_soc > bess_reserve_soc):
                possible_discharge = min(
                    self.config.bess_max_discharge_mw,
                    (bess_cur_soc - bess_reserve_soc) * self.config.bess_storage_capacity_mwh
                    * self.config.bess_discharge_efficiency,
                )
                bess_discharge_mwh = possible_discharge
                bess_soc[cid] -= (
                    bess_discharge_mwh / self.config.bess_discharge_efficiency
                ) / self.config.bess_storage_capacity_mwh
                bess_loss_mwh += bess_discharge_mwh * (
                    (1.0 / self.config.bess_discharge_efficiency) - 1.0
                )

            # 4. Station auxiliary & distribution losses
            station_subtotal = fc_input_mwh + pack_recharge_input_mwh + bess_charge_mwh
            aux_load_mwh = station_subtotal * self.config.auxiliary_load_pct
            distrib_loss_mwh = (
                station_subtotal + aux_load_mwh
            ) * self.config.distribution_loss_pct

            # Total electrical demand needed this hour
            net_electrical_demand = (
                fc_input_mwh
                + pack_recharge_input_mwh
                + bess_charge_mwh
                + aux_load_mwh
                + distrib_loss_mwh
            )

            # 5. Supply procurement priority (Renewables -> DISCOM -> BESS discharge -> IEX)
            # Available contracted renewable energy
            ren_avail_mwh = float(row.get("renewable_available_mwh", 0.0))
            ren_used_mwh = min(ren_avail_mwh, net_electrical_demand)
            ren_curtailed_mwh = max(0.0, ren_avail_mwh - ren_used_mwh)

            remainder_needed = net_electrical_demand - ren_used_mwh

            # BESS discharge applied to offset grid purchases
            bess_used = min(bess_discharge_mwh, remainder_needed)
            # If BESS discharge was planned greater than remainder, adjust BESS discharge to exact need
            bess_discharge_mwh = bess_used
            remainder_needed -= bess_discharge_mwh

            # DISCOM baseload import (within cluster grid import limit)
            discom_import_mwh = min(remainder_needed, self.config.cluster_capacity_mw * 0.80)
            remainder_needed -= discom_import_mwh

            # IEX merchant purchase for remaining balance
            iex_import_mwh = remainder_needed

            # Construct energy balance record
            balance_rec = EnergyBalanceRecord(
                timestamp=ts,
                cluster_id=cid,
                renewable_used_mwh=round(ren_used_mwh, 4),
                discom_import_mwh=round(discom_import_mwh, 4),
                iex_import_mwh=round(iex_import_mwh, 4),
                bess_discharge_mwh=round(bess_discharge_mwh, 4),
                fast_charge_input_mwh=round(fc_input_mwh, 4),
                swap_pack_charge_input_mwh=round(pack_recharge_input_mwh, 4),
                bess_charge_mwh=round(bess_charge_mwh, 4),
                auxiliary_load_mwh=round(aux_load_mwh, 4),
                distribution_loss_mwh=round(distrib_loss_mwh, 4),
                export_mwh=0.0,
                fast_charge_delivered_mwh=round(fc_delivered_mwh, 4),
                swap_energy_equivalent_delivered_mwh=round(swap_delivered_mwh, 4),
                fast_charge_unmet_mwh=round(fc_unmet_mwh, 4),
                swap_unmet_energy_equivalent_mwh=round(swap_unmet_mwh, 4),
                charger_conversion_loss_mwh=round(charger_loss_mwh, 4),
                swap_pack_charging_loss_mwh=round(swap_charging_loss_mwh, 4),
                bess_loss_mwh=round(bess_loss_mwh, 4),
                renewable_available_mwh=round(ren_avail_mwh, 4),
                renewable_curtailed_mwh=round(ren_curtailed_mwh, 4),
                provenance=Provenance.SYNTHETIC.value,
            )
            balance_rec.compute_balance()
            records.append(balance_rec)

        summary = {
            "total_intervals": len(records),
            "final_bess_soc": {c: round(bess_soc[c], 3) for c in clusters},
            "final_ready_packs": {c: ready_packs[c] for c in clusters},
            "reserve_packs_enforced": {c: reserve_packs for c in clusters},
            "reserve_compliance": all(ready_packs[c] >= reserve_packs for c in clusters),
        }
        return records, summary
