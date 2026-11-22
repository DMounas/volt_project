"""Cohort aggregation engine for customer fast-charging and battery-swapping service requests.

Aggregates individual session requests into tractable hourly service cohorts
while strictly preserving:
- Total requested energy (MWh / kWh) and discrete pack counts
- Non-shiftable vs flexible energy delineation
- Explicit opt-in and customer priority status
- Emergency non-shiftability and 5% priority fleet reserve protection
- Hard arrival times and departure deadlines
"""

from dataclasses import dataclass
from typing import Optional
import pandas as pd

from engine.customer.models import (
    CustomerSegment,
    CustomerServiceRequest,
    ServiceType,
)


@dataclass
class ServiceCohort:
    """Aggregated service cohort for MILP scheduling."""
    cohort_id: str
    cluster_id: str
    modality: ServiceType
    segment: CustomerSegment
    arrival_hour: int
    deadline_hour: int
    flexibility_opt_in: bool
    total_energy_mwh: float
    non_shiftable_mwh: float
    flexible_mwh: float
    total_packs: int = 0
    non_shiftable_packs: int = 0
    flexible_packs: int = 0
    requests_count: int = 0
    is_emergency: bool = False
    is_priority_reserve: bool = False

    @property
    def allowable_hours(self) -> list[int]:
        """Hours during which this cohort may be served."""
        return list(range(self.arrival_hour, min(24, self.deadline_hour + 1)))


class CohortAggregator:
    """Aggregates individual requests into structured MILP service cohorts."""

    def __init__(self, pack_capacity_kwh: float = 2.25):
        self.pack_capacity_kwh = pack_capacity_kwh

    def aggregate_dataframe(
        self,
        df: pd.DataFrame,
        horizon_hours: int = 24,
    ) -> list[ServiceCohort]:
        """High-performance vectorized aggregation directly from DataFrame."""
        if df.empty:
            return []

        # Vectorized arrival & deadline hour extraction
        if "arrival_ts" in df.columns:
            arr_h = df["arrival_ts"].astype(str).str[11:13].astype(int)
        else:
            arr_h = pd.Series(0, index=df.index)

        if "departure_deadline_ts" in df.columns:
            dead_h = df["departure_deadline_ts"].astype(str).str[11:13].astype(int).clip(lower=arr_h, upper=horizon_hours - 1)
        else:
            dead_h = arr_h

        work_df = df.copy()
        work_df["arr_h"] = arr_h
        work_df["dead_h"] = dead_h
        work_df["is_flex"] = (
            work_df["flexibility_opt_in"].astype(bool)
            & ~work_df["customer_segment"].isin(["EMERGENCY", "PRIORITY_FLEET"])
        )

        agg = work_df.groupby(
            ["cluster_id", "request_type", "customer_segment", "arr_h", "dead_h", "is_flex"],
            as_index=False,
        ).agg(
            total_energy_kwh=("requested_energy_kwh", "sum"),
            min_energy_kwh=("minimum_service_energy_kwh", "sum"),
            total_packs=("requested_pack_count", "sum"),
            min_packs=("minimum_pack_count", "sum"),
            req_count=("request_id", "count"),
        )

        cohorts: list[ServiceCohort] = []
        for i, row in agg.iterrows():
            cid = f"COHORT-{str(row['cluster_id'])[:3].upper()}-{str(row['request_type'])[:3]}-A{row['arr_h']:02d}D{row['dead_h']:02d}-{i:04d}"
            is_emerg = row["customer_segment"] == "EMERGENCY"
            is_prio = row["customer_segment"] == "PRIORITY_FLEET"
            mod = ServiceType(row["request_type"])
            seg = CustomerSegment(row["customer_segment"])

            if mod == ServiceType.FAST_CHARGE:
                tot_mwh = round(float(row["total_energy_kwh"] or 0.0) / 1000.0, 6)
                if is_emerg or is_prio or not row["is_flex"] or row["arr_h"] == row["dead_h"]:
                    non_mwh = tot_mwh
                    flx_mwh = 0.0
                else:
                    non_mwh = round(float(row["min_energy_kwh"] or 0.0) / 1000.0, 6)
                    flx_mwh = max(0.0, tot_mwh - non_mwh)
                tot_p = 0
                non_p = 0
                flx_p = 0
            else:
                tot_p = int(row["total_packs"] or 0)
                tot_mwh = round(tot_p * self.pack_capacity_kwh / 1000.0, 6)
                if is_emerg or is_prio or not row["is_flex"] or row["arr_h"] == row["dead_h"]:
                    non_p = tot_p
                    flx_p = 0
                    non_mwh = tot_mwh
                    flx_mwh = 0.0
                else:
                    non_p = int(row["min_packs"] or 1)
                    flx_p = max(0, tot_p - non_p)
                    non_mwh = round(non_p * self.pack_capacity_kwh / 1000.0, 6)
                    flx_mwh = round(flx_p * self.pack_capacity_kwh / 1000.0, 6)

            cohorts.append(
                ServiceCohort(
                    cohort_id=cid,
                    cluster_id=str(row["cluster_id"]),
                    modality=mod,
                    segment=seg,
                    arrival_hour=int(row["arr_h"]),
                    deadline_hour=int(row["dead_h"]),
                    flexibility_opt_in=bool(row["is_flex"]),
                    total_energy_mwh=tot_mwh,
                    non_shiftable_mwh=non_mwh,
                    flexible_mwh=flx_mwh,
                    total_packs=tot_p,
                    non_shiftable_packs=non_p,
                    flexible_packs=flx_p,
                    requests_count=int(row["req_count"]),
                    is_emergency=is_emerg,
                    is_priority_reserve=is_prio,
                )
            )

        return cohorts

    def aggregate_requests(
        self,
        requests: list[CustomerServiceRequest],
        horizon_hours: int = 24,
    ) -> list[ServiceCohort]:
        """Group individual customer requests into compact hourly cohorts."""
        cohort_dict: dict[tuple, ServiceCohort] = {}

        for req in requests:
            arr_hour = req.arrival_ts.hour
            # Clamp deadline hour within the 24-hour horizon
            dead_hour = min(horizon_hours - 1, max(arr_hour, req.departure_deadline_ts.hour))

            is_emerg = req.customer_segment == CustomerSegment.EMERGENCY
            is_prio = req.customer_segment == CustomerSegment.PRIORITY_FLEET

            # Key for aggregation
            key = (
                req.cluster_id,
                req.request_type,
                req.customer_segment,
                arr_hour,
                dead_hour,
                req.flexibility_opt_in and not (is_emerg or is_prio),
            )

            if key not in cohort_dict:
                cid = f"COHORT-{req.cluster_id[:3].upper()}-{req.request_type.value[:3]}-A{arr_hour:02d}D{dead_hour:02d}-{len(cohort_dict)+1:04d}"
                cohort_dict[key] = ServiceCohort(
                    cohort_id=cid,
                    cluster_id=req.cluster_id,
                    modality=req.request_type,
                    segment=req.customer_segment,
                    arrival_hour=arr_hour,
                    deadline_hour=dead_hour,
                    flexibility_opt_in=key[5],
                    total_energy_mwh=0.0,
                    non_shiftable_mwh=0.0,
                    flexible_mwh=0.0,
                    total_packs=0,
                    non_shiftable_packs=0,
                    flexible_packs=0,
                    requests_count=0,
                    is_emergency=is_emerg,
                    is_priority_reserve=is_prio,
                )

            coh = cohort_dict[key]
            coh.requests_count += 1

            if req.request_type == ServiceType.FAST_CHARGE:
                kwh = req.requested_energy_kwh or 0.0
                mwh = kwh / 1000.0
                coh.total_energy_mwh += mwh

                if is_emerg or is_prio or not req.flexibility_opt_in or arr_hour == dead_hour:
                    # Non-shiftable
                    coh.non_shiftable_mwh += mwh
                else:
                    # Minimum energy is non-shiftable in arrival hour; remaining is flexible
                    min_mwh = (req.minimum_service_energy_kwh or 0.0) / 1000.0
                    coh.non_shiftable_mwh += min_mwh
                    coh.flexible_mwh += max(0.0, mwh - min_mwh)

            elif req.request_type == ServiceType.BATTERY_SWAP:
                packs = req.requested_pack_count or 1
                coh.total_packs += packs
                swap_mwh = (packs * self.pack_capacity_kwh) / 1000.0
                coh.total_energy_mwh += swap_mwh

                if is_emerg or is_prio or not req.flexibility_opt_in or arr_hour == dead_hour:
                    coh.non_shiftable_packs += packs
                    coh.non_shiftable_mwh += swap_mwh
                else:
                    min_packs = req.minimum_pack_count or 1
                    flex_packs = max(0, packs - min_packs)
                    coh.non_shiftable_packs += min_packs
                    coh.non_shiftable_mwh += (min_packs * self.pack_capacity_kwh) / 1000.0
                    coh.flexible_packs += flex_packs
                    coh.flexible_mwh += (flex_packs * self.pack_capacity_kwh) / 1000.0

        # Round values for numerical precision
        for coh in cohort_dict.values():
            coh.total_energy_mwh = round(coh.total_energy_mwh, 6)
            coh.non_shiftable_mwh = round(coh.non_shiftable_mwh, 6)
            coh.flexible_mwh = round(coh.flexible_mwh, 6)

        return list(cohort_dict.values())

    def verify_reconciliation(
        self,
        requests: list[CustomerServiceRequest],
        cohorts: list[ServiceCohort],
    ) -> dict[str, Any]:
        """Verify exact conservation of energy and requests between raw inputs and cohorts."""
        raw_fc_mwh = sum((r.requested_energy_kwh or 0.0) for r in requests if r.request_type == ServiceType.FAST_CHARGE) / 1000.0
        raw_swap_packs = sum((r.requested_pack_count or 0) for r in requests if r.request_type == ServiceType.BATTERY_SWAP)
        raw_swap_mwh = raw_swap_packs * self.pack_capacity_kwh / 1000.0

        coh_fc_mwh = sum(c.total_energy_mwh for c in cohorts if c.modality == ServiceType.FAST_CHARGE)
        coh_swap_packs = sum(c.total_packs for c in cohorts if c.modality == ServiceType.BATTERY_SWAP)
        coh_swap_mwh = sum(c.total_energy_mwh for c in cohorts if c.modality == ServiceType.BATTERY_SWAP)

        fc_diff = abs(coh_fc_mwh - raw_fc_mwh)
        swap_pack_diff = abs(coh_swap_packs - raw_swap_packs)
        swap_mwh_diff = abs(coh_swap_mwh - raw_swap_mwh)

        return {
            "reconciled": bool(fc_diff < 1e-4 and swap_pack_diff == 0 and swap_mwh_diff < 1e-4),
            "raw_fast_charge_mwh": round(raw_fc_mwh, 4),
            "cohort_fast_charge_mwh": round(coh_fc_mwh, 4),
            "fast_charge_diff_mwh": round(fc_diff, 6),
            "raw_swap_packs": raw_swap_packs,
            "cohort_swap_packs": coh_swap_packs,
            "swap_pack_diff": swap_pack_diff,
            "raw_requests_count": len(requests),
            "cohort_requests_count": sum(c.requests_count for c in cohorts),
            "cohorts_count": len(cohorts),
        }
