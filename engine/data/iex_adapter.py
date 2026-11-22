"""VOLT Engine - IEX 15-Minute to Hourly Market Data Adapter.

Responsibilities:
- Ingestion and structural validation of 15-minute IEX Day-Ahead Market (DAM) records.
- Explicit physical and dimensional units contract:
    * 15-minute block power is in MW (average active power schedule over 15-min interval).
    * 15-minute block energy is in MWh: block_energy_mwh = block_power_mw * 0.25 hours.
    * Hourly energy is strictly the sum of block energies: sum(block_energy_mwh) = 0.25 * sum(block_power_mw).
    * Volume-Weighted Average Price: sum(price_i * block_energy_i) / sum(block_energy_i).
    * Time-Weighted Equal Block Mean: mean(price_i) when volume is unmetered.
- Rejection of dimensional errors (never reports sum(MW) as MWh).
- Explicit incomplete hour policy (flagged as INCOMPLETE, partial energy never presented as full hour).
- Diagnostic auditing for missing blocks, duplicates, timestamps, and out-of-order sequences.
- Strict non-negative price enforcement (rejects clearing_price < 0).
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
    total_cleared_energy_mwh: float = 0.0
    average_cleared_power_mw: float = 0.0
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
        volume_power_mw_col: Optional[str] = "cleared_volume_mw",
        energy_mwh_col: Optional[str] = "cleared_energy_mwh",
        timestamp_col: str = "timestamp",
        drop_incomplete_hours: bool = True,
    ) -> tuple[pd.DataFrame, IEXAdapterDiagnostics]:
        """Aggregate 15-minute market records to 1-hour intervals.

        Physical Units Contract:
            - Block volume is either power in MW (volume_power_mw_col) or energy in MWh (energy_mwh_col).
            - If power in MW is supplied, energy per block = power_mw * 0.25 h.
            - Total hourly energy is sum(energy_mwh), NOT sum(power_mw).
            - Hourly average power is mean(power_mw) = total_energy_mwh / 1.0 h.
            - Hourly price = sum(price * energy) / sum(energy).

        Args:
            df_15min: Input DataFrame containing 15-minute market records.
            price_col: Column name for electricity price (INR/MWh).
            volume_power_mw_col: Column name for cleared power in MW over 15 min.
            energy_mwh_col: Column name for cleared energy in MWh over 15 min.
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
            diffs = df["dt"].diff()
            out_of_order_count = int((diffs < pd.Timedelta(0)).sum())
            df = df.sort_values("dt").reset_index(drop=True)

        # Check duplicates
        duplicate_count = int(df.duplicated(subset=["dt"]).sum())
        if duplicate_count > 0:
            df = df.drop_duplicates(subset=["dt"], keep="first").reset_index(drop=True)

        # Establish block power (MW) and block energy (MWh) series
        # Rule: Do not infer units solely from names; prioritize explicit columns
        has_energy_col = (
            energy_mwh_col is not None
            and energy_mwh_col in df.columns
            and df[energy_mwh_col].notna().any()
            and (df[energy_mwh_col] > 0).any()
        )
        has_power_col = (
            volume_power_mw_col is not None
            and volume_power_mw_col in df.columns
            and df[volume_power_mw_col].notna().any()
            and (df[volume_power_mw_col] > 0).any()
        )
        # Check backward-compatible legacy column "cleared_volume_mwh"
        legacy_vol_col = "cleared_volume_mwh"
        has_legacy_col = (
            not has_energy_col
            and not has_power_col
            and legacy_vol_col in df.columns
            and df[legacy_vol_col].notna().any()
            and (df[legacy_vol_col] > 0).any()
        )

        if has_energy_col:
            df["_block_energy_mwh"] = df[energy_mwh_col].astype(float)
            if has_power_col:
                df["_block_power_mw"] = df[volume_power_mw_col].astype(float)
            else:
                df["_block_power_mw"] = df["_block_energy_mwh"] / 0.25
            has_volume = True
        elif has_power_col:
            df["_block_power_mw"] = df[volume_power_mw_col].astype(float)
            # Dimensional conversion: 15 minutes = 0.25 hours
            df["_block_energy_mwh"] = df["_block_power_mw"] * 0.25
            has_volume = True
        elif has_legacy_col:
            # If labelled cleared_volume_mwh in legacy data, verify whether it represents MW or MWh
            # In IEX DAM convention, market cleared trade volume is power schedule in MW.
            # To be dimensionally safe, if average values exceed typical station sizes (e.g. thousands),
            # it represents grid-scale trade power schedule in MW.
            df["_block_power_mw"] = df[legacy_vol_col].astype(float)
            df["_block_energy_mwh"] = df["_block_power_mw"] * 0.25
            has_volume = True
        else:
            df["_block_power_mw"] = 0.0
            df["_block_energy_mwh"] = 0.0
            has_volume = False

        # Floor timestamps to the hour for grouping
        df["hour_dt"] = df["dt"].dt.floor("h")

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
                hour_status = "INCOMPLETE"
            else:
                diagnostics.complete_hours_count += 1
                hour_status = "COMPLETE"

            prices = group[price_col].values
            if (prices < 0).any():
                raise ValueError(
                    f"Negative electricity price detected at {hour_ts}: {prices[prices < 0]}"
                )

            # Energy and volume weighting
            hour_has_valid_vol = (
                has_volume
                and group["_block_energy_mwh"].notna().all()
                and (group["_block_energy_mwh"] > 0).any()
                and group["_block_energy_mwh"].sum() > 0
            )

            energies = group["_block_energy_mwh"].values
            powers = group["_block_power_mw"].values
            total_energy = float(np.sum(energies))
            avg_power = float(np.mean(powers))

            if hour_has_valid_vol:
                # Energy-weighted price: sum(P_i * E_i) / sum(E_i)
                # Since E_i = MW_i * 0.25, 0.25 cancels out giving identical price:
                hourly_price = float(np.sum(prices * energies) / total_energy)
                method = "VOLUME_WEIGHTED"
                diagnostics.volume_weighted_hours_count += 1
            else:
                hourly_price = float(np.mean(prices))
                method = "TIME_WEIGHTED_EQUAL_BLOCK_MEAN"
                diagnostics.time_weighted_hours_count += 1

            # Incomplete hour handling policy:
            # If hour is incomplete or unmetered, never report partial/unmetered energy as full-hour energy
            is_complete = hour_status == "COMPLETE"
            record = {
                "timestamp": hour_ts.isoformat(),
                "market": "DAM",
                "clearing_price_inr_mwh": round(hourly_price, 2),
                "price_inr_mwh": round(hourly_price, 2),  # Backward compatibility
                "cleared_energy_mwh": round(total_energy, 2) if is_complete and has_volume else None,
                "volume_mwh": round(total_energy, 2) if is_complete and has_volume else 0.0,  # Backward compatibility
                "cleared_average_power_mw": round(avg_power, 2) if has_volume else None,
                "partial_cleared_energy_mwh": round(total_energy, 2) if not is_complete and has_volume else None,
                "aggregation_method": method,
                "block_count": n_blocks,
                "completeness_pct": round((n_blocks / 4.0) * 100.0, 1),
                "status": hour_status,
                "provenance": diagnostics.provenance,
            }
            hourly_records.append(record)

        diagnostics.missing_blocks_details = missing_details[:20]

        if not hourly_records:
            return pd.DataFrame(), diagnostics

        out_df = pd.DataFrame(hourly_records)
        diagnostics.total_hours_produced = len(out_df)

        complete_df = out_df[out_df["status"] == "COMPLETE"]
        if not complete_df.empty:
            diagnostics.total_cleared_energy_mwh = round(float(complete_df["cleared_energy_mwh"].sum()), 2)
            diagnostics.average_cleared_power_mw = round(float(complete_df["cleared_average_power_mw"].mean()), 2)

        diagnostics.min_hourly_price_inr_mwh = float(out_df["clearing_price_inr_mwh"].min())
        diagnostics.max_hourly_price_inr_mwh = float(out_df["clearing_price_inr_mwh"].max())
        diagnostics.mean_hourly_price_inr_mwh = float(out_df["clearing_price_inr_mwh"].mean())

        return out_df, diagnostics
