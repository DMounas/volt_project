"""VOLT Engine - IEX 15-Minute to Hourly Market Data Adapter.

Responsibilities:
- Ingestion and structural validation of 15-minute IEX Day-Ahead Market (DAM) records.
- Validation of complete hours (strictly 4 expected 15-minute blocks per hour).
- Rigorous aggregation to 1-hour model intervals:
  * Volume-Weighted Average Price when volume exists: sum(P_i * V_i) / sum(V_i).
  * Time-Weighted Equal Block Mean when volume is unavailable: mean(P_i).
- Diagnostic auditing for missing blocks, duplicates, timestamps, and out-of-order sequences.
- Never fills missing price blocks with zero.
- Preserves original 15-minute granularity and provenance metadata.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Optional
import numpy as np
import pandas as pd
from engine.provenance import Provenance


@dataclass
class IEXAdapterDiagnostics:
    """Diagnostic report from 15-minute to hourly aggregation."""

    total_15min_records_read: int = 0
    total_hours_produced: int = 0
    aggregation_method_used: str = "UNKNOWN"
    complete_hours_count: int = 0
    incomplete_hours_count: int = 0
    duplicate_blocks_count: int = 0
    out_of_order_blocks_count: int = 0
    missing_blocks_details: list[dict[str, Any]] = field(default_factory=list)
    volume_weighted_hours_count: int = 0
    time_weighted_hours_count: int = 0
    min_hourly_price_inr_mwh: float = 0.0
    max_hourly_price_inr_mwh: float = 0.0
    mean_hourly_price_inr_mwh: float = 0.0
    provenance: str = Provenance.SYNTHETIC.value

    def to_dict(self) -> dict[str, Any]:
        """Convert diagnostic dataclass to dictionary."""
        return asdict(self)


class IEXMarketAdapter:
    """Adapter transforming 15-minute DAM market intervals to hourly decision blocks."""

    def __init__(self, timezone: str = "Asia/Kolkata"):
        self.timezone = timezone

    def aggregate_15min_to_hourly(
        self,
        df_15min: pd.DataFrame,
        price_col: str = "clearing_price_inr_mwh",
        volume_col: Optional[str] = "cleared_volume_mwh",
        timestamp_col: str = "timestamp",
        drop_incomplete_hours: bool = True,
    ) -> tuple[pd.DataFrame, IEXAdapterDiagnostics]:
        """Aggregate 15-minute market records to 1-hour intervals.

        Args:
            df_15min: Input DataFrame containing 15-minute market records.
            price_col: Column name for electricity price (INR/MWh).
            volume_col: Column name for cleared volume (MWh), if present.
            timestamp_col: Column name for ISO or datetime timestamps.
            drop_incomplete_hours: If True, exclude hours with fewer than 4 blocks.

        Returns:
            Tuple of (hourly DataFrame, IEXAdapterDiagnostics report).
        """
        if df_15min.empty:
            raise ValueError("Input DataFrame is empty")

        if price_col not in df_15min.columns:
            raise ValueError(f"Price column '{price_col}' not found in DataFrame")

        df = df_15min.copy()

        # Parse and localize timestamps
        if not pd.api.types.is_datetime64_any_dtype(df[timestamp_col]):
            df["dt"] = pd.to_datetime(df[timestamp_col])
        else:
            df["dt"] = df[timestamp_col]

        if df["dt"].dt.tz is None:
            df["dt"] = df["dt"].dt.tz_localize(self.timezone)
        else:
            df["dt"] = df["dt"].dt.tz_convert(self.timezone)

        # Sort and inspect chronological order
        is_sorted = df["dt"].is_monotonic_increasing
        out_of_order_count = 0
        if not is_sorted:
            # Count out-of-order inversions
            diffs = df["dt"].diff()
            out_of_order_count = int((diffs < pd.Timedelta(0)).sum())
            df = df.sort_values("dt").reset_index(drop=True)

        # Check duplicates
        duplicate_count = int(df.duplicated(subset=["dt"]).sum())
        if duplicate_count > 0:
            df = df.drop_duplicates(subset=["dt"], keep="first").reset_index(drop=True)

        # Floor timestamps to the hour for grouping
        df["hour_dt"] = df["dt"].dt.floor("h")

        # Determine volume presence
        has_volume = (
            volume_col is not None
            and volume_col in df.columns
            and df[volume_col].notna().any()
            and (df[volume_col] > 0).any()
        )

        diagnostics = IEXAdapterDiagnostics(
            total_15min_records_read=len(df_15min),
            duplicate_blocks_count=duplicate_count,
            out_of_order_blocks_count=out_of_order_count,
            aggregation_method_used="VOLUME_WEIGHTED" if has_volume else "TIME_WEIGHTED_EQUAL_BLOCK_MEAN",
            provenance=(
                str(df["provenance"].iloc[0])
                if "provenance" in df.columns
                else Provenance.SYNTHETIC.value
            ),
        )

        hourly_records = []
        missing_details = []

        grouped = df.groupby("hour_dt", sort=True)

        for hour_ts, group in grouped:
            n_blocks = len(group)
            expected_minutes = {0, 15, 30, 45}
            actual_minutes = set(group["dt"].dt.minute.values)
            missing_min = sorted(list(expected_minutes - actual_minutes))

            if n_blocks != 4 or missing_min:
                diagnostics.incomplete_hours_count += 1
                missing_info = {
                    "hour": hour_ts.isoformat(),
                    "blocks_found": n_blocks,
                    "missing_minutes": missing_min,
                }
                missing_details.append(missing_info)
                if drop_incomplete_hours:
                    continue
                # If not dropping, flag status as INCOMPLETE
                hour_status = "INCOMPLETE"
            else:
                diagnostics.complete_hours_count += 1
                hour_status = "COMPLETE"

            prices = group[price_col].values
            if (prices < 0).any():
                raise ValueError(
                    f"Negative electricity price detected at {hour_ts}: {prices[prices < 0]}"
                )

            # Check if valid volume weighting can be performed for this specific hour
            hour_has_valid_vol = (
                has_volume
                and group[volume_col].notna().all()
                and (group[volume_col] > 0).any()
                and group[volume_col].sum() > 0
            )

            if hour_has_valid_vol:
                volumes = group[volume_col].values
                total_vol = float(np.sum(volumes))
                hourly_price = float(np.sum(prices * volumes) / total_vol)
                method = "VOLUME_WEIGHTED"
                diagnostics.volume_weighted_hours_count += 1
            else:
                hourly_price = float(np.mean(prices))
                total_vol = (
                    float(group[volume_col].sum())
                    if has_volume and volume_col in group.columns
                    else 0.0
                )
                method = "TIME_WEIGHTED_EQUAL_BLOCK_MEAN"
                diagnostics.time_weighted_hours_count += 1

            record = {
                "timestamp": hour_ts.isoformat(),
                "market": "DAM",
                "price_inr_mwh": round(hourly_price, 2),
                "volume_mwh": round(total_vol, 2),
                "aggregation_method": method,
                "block_count": n_blocks,
                "status": hour_status,
                "provenance": diagnostics.provenance,
            }
            hourly_records.append(record)

        diagnostics.missing_blocks_details = missing_details[:20]  # Cap details to first 20

        if not hourly_records:
            return pd.DataFrame(), diagnostics

        out_df = pd.DataFrame(hourly_records)
        diagnostics.total_hours_produced = len(out_df)
        diagnostics.min_hourly_price_inr_mwh = float(out_df["price_inr_mwh"].min())
        diagnostics.max_hourly_price_inr_mwh = float(out_df["price_inr_mwh"].max())
        diagnostics.mean_hourly_price_inr_mwh = float(out_df["price_inr_mwh"].mean())

        return out_df, diagnostics
