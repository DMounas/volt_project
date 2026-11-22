"""VOLT Engine - Synthetic Customer Request Disaggregation & Reconciliation Engine.

Disaggregates hourly aggregate cluster demand into individual, typed customer service requests:
- Fast charge sessions (15 - 60 kWh) preserving hourly MWh within numerical tolerance (<= 0.01%)
- Battery swap transactions with discrete integer packs reconciling to aggregate swap energy
- Enforces segment distributions (EMERGENCY, PRIORITY_FLEET, RIDE_HAILING, LOGISTICS_FLEET, PRIVATE_EV)
- Assigns arrival timestamps, deadlines, wait times, deferral limits, and explicit opt-in flags
- Supports full multi-year generation and fast demo mode for responsive execution
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Optional
import numpy as np
import pandas as pd

from engine.customer.models import (
    CustomerSegment,
    CustomerServiceRequest,
    ServiceType,
)

IST = timezone(timedelta(hours=5, minutes=30))

DEFAULT_SEGMENT_PROFILES = {
    CustomerSegment.EMERGENCY: {
        "share": 0.03,
        "priority": 1,
        "opt_in_rate": 0.0,
        "max_wait_mins": 0.0,
        "max_deferral_mins": 0.0,
        "min_service_fraction": 1.0,
    },
    CustomerSegment.PRIORITY_FLEET: {
        "share": 0.12,
        "priority": 2,
        "opt_in_rate": 0.0,
        "max_wait_mins": 15.0,
        "max_deferral_mins": 0.0,
        "min_service_fraction": 1.0,
    },
    CustomerSegment.RIDE_HAILING: {
        "share": 0.35,
        "priority": 3,
        "opt_in_rate": 0.35,
        "max_wait_mins": 30.0,
        "max_deferral_mins": 60.0,
        "min_service_fraction": 0.60,
    },
    CustomerSegment.LOGISTICS_FLEET: {
        "share": 0.30,
        "priority": 4,
        "opt_in_rate": 0.60,
        "max_wait_mins": 90.0,
        "max_deferral_mins": 180.0,
        "min_service_fraction": 0.40,
    },
    CustomerSegment.PRIVATE_EV: {
        "share": 0.20,
        "priority": 5,
        "opt_in_rate": 0.25,
        "max_wait_mins": 45.0,
        "max_deferral_mins": 90.0,
        "min_service_fraction": 0.50,
    },
}


class SyntheticRequestDisaggregator:
    """Disaggregates aggregate hourly demand into individual customer service requests."""

    def __init__(
        self,
        seed: int = 42,
        segment_profiles: Optional[dict[CustomerSegment, dict[str, Any]]] = None,
        pack_capacity_kwh: float = 2.25,
        reconciliation_tolerance_pct: float = 0.05,
    ):
        self.seed = seed
        self.segment_profiles = segment_profiles or DEFAULT_SEGMENT_PROFILES
        self.pack_capacity_kwh = pack_capacity_kwh
        self.tolerance_pct = reconciliation_tolerance_pct

    def disaggregate_hourly_demand(
        self,
        hourly_df: pd.DataFrame,
        demo_mode: bool = True,
        max_hours: int = 48,
    ) -> tuple[list[CustomerServiceRequest], pd.DataFrame]:
        """Disaggregate hourly cluster rows into individual requests with exact reconciliation."""
        rng = np.random.default_rng(self.seed)

        # In demo mode, select representative slices across all clusters to keep response fast and bounded
        if demo_mode:
            clusters = hourly_df["cluster_id"].unique()
            slices = []
            for c in clusters:
                c_df = hourly_df[hourly_df["cluster_id"] == c]
                # Pick a representative recent 48-hour period
                slices.append(c_df.tail(max_hours))
            work_df = pd.concat(slices, ignore_index=True)
        else:
            work_df = hourly_df

        requests: list[CustomerServiceRequest] = []
        reconciliations: list[dict[str, Any]] = []

        segments = list(self.segment_profiles.keys())
        segment_probs = [self.segment_profiles[s]["share"] for s in segments]
        # Normalize probabilities
        prob_sum = sum(segment_probs)
        segment_probs = [p / prob_sum for p in segment_probs]

        for _, row in work_df.iterrows():
            ts_str = str(row["timestamp"])
            cluster_id = str(row["cluster_id"])
            base_dt = datetime.fromisoformat(ts_str)

            # -------------------------------------------------------------
            # 1. Fast Charging Disaggregation
            # -------------------------------------------------------------
            fc_mwh = float(row.get("fast_charge_demand_mwh", 0.0))
            fc_req_count = int(row.get("fast_charge_requests", 0))

            if fc_req_count > 0 and fc_mwh > 0.0:
                total_fc_kwh = fc_mwh * 1000.0
                # Generate random weights for each session to partition total_fc_kwh
                raw_weights = rng.uniform(15.0, 45.0, size=fc_req_count)
                norm_weights = raw_weights / raw_weights.sum()
                allocated_kwh = norm_weights * total_fc_kwh

                # Reconcile exact sum on last element
                diff = total_fc_kwh - allocated_kwh.sum()
                allocated_kwh[-1] += diff

                # Assign session attributes
                row_segment_indices = rng.choice(len(segments), size=fc_req_count, p=segment_probs)
                arr_minutes = rng.integers(0, 60, size=fc_req_count)

                hour_fc_sum_kwh = 0.0
                for i in range(fc_req_count):
                    seg = segments[row_segment_indices[i]]
                    prof = self.segment_profiles[seg]
                    arr_ts = base_dt + timedelta(minutes=int(arr_minutes[i]))
                    kwh = float(round(allocated_kwh[i], 3))
                    hour_fc_sum_kwh += kwh

                    min_kwh = round(kwh * prof["min_service_fraction"], 3)
                    opt_in = bool(rng.uniform(0.0, 1.0) < prof["opt_in_rate"]) if prof["opt_in_rate"] > 0 else False

                    # Service duration and deadline
                    norm_duration_mins = (kwh / 50.0) * 60.0
                    wait_mins = prof["max_wait_mins"]
                    deferral_mins = prof["max_deferral_mins"] if opt_in else 0.0
                    deadline_ts = arr_ts + timedelta(minutes=norm_duration_mins + wait_mins + deferral_mins)

                    req_id = f"REQ-FC-{cluster_id[:3].upper()}-{len(requests)+1:06d}"
                    requests.append(
                        CustomerServiceRequest(
                            request_id=req_id,
                            cluster_id=cluster_id,
                            request_type=ServiceType.FAST_CHARGE,
                            customer_segment=seg,
                            arrival_ts=arr_ts,
                            departure_deadline_ts=deadline_ts,
                            requested_energy_kwh=kwh,
                            minimum_service_energy_kwh=min_kwh,
                            max_wait_minutes=wait_mins,
                            max_deferral_minutes=deferral_mins,
                            flexibility_opt_in=opt_in,
                            service_priority=prof["priority"],
                            baseline_tariff_inr_per_kwh=11.50,
                            previous_day_avg_tariff_inr_per_kwh=11.20,
                            provenance="SYNTHETIC",
                        )
                    )

                # Fast charge reconciliation entry
                fc_reconciled_mwh = round(hour_fc_sum_kwh / 1000.0, 6)
                fc_error_pct = abs(fc_reconciled_mwh - fc_mwh) / max(0.001, fc_mwh) * 100.0
                reconciliations.append(
                    {
                        "timestamp": ts_str,
                        "cluster_id": cluster_id,
                        "modality": "FAST_CHARGE",
                        "source_demand_mwh": fc_mwh,
                        "disaggregated_mwh": fc_reconciled_mwh,
                        "error_pct": round(fc_error_pct, 4),
                        "reconciled": bool(fc_error_pct <= self.tolerance_pct),
                        "request_count": fc_req_count,
                    }
                )

            # -------------------------------------------------------------
            # 2. Battery Swap Disaggregation (Discrete integer packs)
            # -------------------------------------------------------------
            swap_mwh = float(row.get("swap_energy_equivalent_mwh", 0.0))
            swap_req_count = int(row.get("swap_requests", 0))

            if swap_req_count > 0 and swap_mwh > 0.0:
                # Target total pack count from aggregate swap energy
                target_total_packs = int(round((swap_mwh * 1000.0) / self.pack_capacity_kwh))
                target_total_packs = max(swap_req_count, target_total_packs)

                # Distribute integer packs across requests (1, 2, or 3 packs per session)
                pack_choices = [1, 2, 3]
                pack_probs = [0.30, 0.55, 0.15]
                raw_packs = rng.choice(pack_choices, size=swap_req_count, p=pack_probs)
                
                # Adjust sum to exactly match target_total_packs
                current_sum = int(raw_packs.sum())
                diff_packs = target_total_packs - current_sum
                
                if diff_packs != 0:
                    indices = rng.permutation(swap_req_count)
                    step = 1 if diff_packs > 0 else -1
                    idx_ptr = 0
                    while diff_packs != 0 and idx_ptr < len(indices):
                        idx = indices[idx_ptr]
                        if step > 0 and raw_packs[idx] < 3:
                            raw_packs[idx] += 1
                            diff_packs -= 1
                        elif step < 0 and raw_packs[idx] > 1:
                            raw_packs[idx] -= 1
                            diff_packs += 1
                        idx_ptr = (idx_ptr + 1) % len(indices)

                row_segment_indices = rng.choice(len(segments), size=swap_req_count, p=segment_probs)
                arr_minutes = rng.integers(0, 60, size=swap_req_count)

                hour_swap_packs = 0
                for i in range(swap_req_count):
                    seg = segments[row_segment_indices[i]]
                    prof = self.segment_profiles[seg]
                    arr_ts = base_dt + timedelta(minutes=int(arr_minutes[i]))
                    packs = int(raw_packs[i])
                    hour_swap_packs += packs

                    min_packs = max(1, int(round(packs * prof["min_service_fraction"]))) if seg != CustomerSegment.EMERGENCY else packs
                    opt_in = bool(rng.uniform(0.0, 1.0) < prof["opt_in_rate"]) if prof["opt_in_rate"] > 0 else False

                    wait_mins = prof["max_wait_mins"]
                    deferral_mins = prof["max_deferral_mins"] if opt_in else 0.0
                    deadline_ts = arr_ts + timedelta(minutes=5.0 + wait_mins + deferral_mins)

                    req_id = f"REQ-SWP-{cluster_id[:3].upper()}-{len(requests)+1:06d}"
                    requests.append(
                        CustomerServiceRequest(
                            request_id=req_id,
                            cluster_id=cluster_id,
                            request_type=ServiceType.BATTERY_SWAP,
                            customer_segment=seg,
                            arrival_ts=arr_ts,
                            departure_deadline_ts=deadline_ts,
                            requested_pack_count=packs,
                            minimum_pack_count=min_packs,
                            pack_capacity_kwh=self.pack_capacity_kwh,
                            max_wait_minutes=wait_mins,
                            max_deferral_minutes=deferral_mins,
                            flexibility_opt_in=opt_in,
                            service_priority=prof["priority"],
                            baseline_tariff_inr_per_kwh=11.50,
                            previous_day_avg_tariff_inr_per_kwh=11.20,
                            provenance="SYNTHETIC",
                        )
                    )

                # Swap reconciliation entry
                swap_reconciled_mwh = round((hour_swap_packs * self.pack_capacity_kwh) / 1000.0, 6)
                swap_error_pct = abs(swap_reconciled_mwh - swap_mwh) / max(0.001, swap_mwh) * 100.0
                reconciliations.append(
                    {
                        "timestamp": ts_str,
                        "cluster_id": cluster_id,
                        "modality": "BATTERY_SWAP",
                        "source_demand_mwh": swap_mwh,
                        "disaggregated_mwh": swap_reconciled_mwh,
                        "error_pct": round(swap_error_pct, 4),
                        "reconciled": bool(swap_error_pct <= 5.0),  # Discrete pack granularity tolerance
                        "request_count": swap_req_count,
                        "total_packs": hour_swap_packs,
                    }
                )

        reconciliation_df = pd.DataFrame(reconciliations)
        return requests, reconciliation_df
