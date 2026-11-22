"""Tests for IEX 15-minute to hourly market data adapter."""

import numpy as np
import pandas as pd
import pytest
from engine.data.iex_adapter import IEXAdapterDiagnostics, IEXMarketAdapter


@pytest.fixture
def adapter():
    return IEXMarketAdapter(timezone="Asia/Kolkata")


@pytest.fixture
def sample_complete_hour_df():
    """Create a single complete hour (4 15-minute blocks) with explicit MW and MWh."""
    return pd.DataFrame(
        {
            "timestamp": [
                "2025-03-01T10:00:00+05:30",
                "2025-03-01T10:15:00+05:30",
                "2025-03-01T10:30:00+05:30",
                "2025-03-01T10:45:00+05:30",
            ],
            "clearing_price_inr_mwh": [4000.0, 5000.0, 6000.0, 5000.0],
            "cleared_volume_mw": [400.0, 800.0, 1200.0, 1600.0],
            "cleared_energy_mwh": [100.0, 200.0, 300.0, 400.0],
            "provenance": "SYNTHETIC",
        }
    )


@pytest.mark.unit
def test_iex_volume_weighted_aggregation(adapter, sample_complete_hour_df):
    """Verify volume-weighted calculation: sum(P * E) / sum(E)."""
    # Sum(P * E) = 4000*100 + 5000*200 + 6000*300 + 5000*400 = 5,200,000
    # Total Energy = 100 + 200 + 300 + 400 = 1000 MWh
    # Expected Price = 5,200,000 / 1000 = 5200.0 INR/MWh
    hourly_df, diag = adapter.aggregate_15min_to_hourly(
        sample_complete_hour_df,
        price_col="clearing_price_inr_mwh",
        energy_mwh_col="cleared_energy_mwh",
    )

    assert len(hourly_df) == 1
    row = hourly_df.iloc[0]
    assert row["price_inr_mwh"] == 5200.0
    assert row["cleared_energy_mwh"] == 1000.0
    assert row["cleared_average_power_mw"] == 1000.0
    assert row["aggregation_method"] == "VOLUME_WEIGHTED"
    assert row["block_count"] == 4
    assert diag.complete_hours_count == 1
    assert diag.incomplete_hours_count == 0
    assert diag.total_cleared_energy_mwh == 1000.0


@pytest.mark.unit
def test_iex_dimensional_consistency_4blocks(adapter):
    """Verify dimensional consistency: 4 blocks of 4,000 MW power over 15 min equals 4,000 MWh energy.

    CRITICAL DIMENSIONAL CHECK:
    - 4,000 MW power held for 15 minutes (0.25 hours) produces 1,000 MWh per block.
    - 4 consecutive blocks of 4,000 MW produce 4 * 1,000 MWh = 4,000 MWh total energy.
    - Simple sum of 4 * 4,000 MW = 16,000 MW-readings MUST NEVER be reported as 16,000 MWh!
    """
    four_blocks_df = pd.DataFrame(
        {
            "timestamp": [
                "2025-06-15T14:00:00+05:30",
                "2025-06-15T14:15:00+05:30",
                "2025-06-15T14:30:00+05:30",
                "2025-06-15T14:45:00+05:30",
            ],
            "clearing_price_inr_mwh": [5420.50, 5580.00, 5610.25, 5515.00],
            "cleared_volume_mw": [4210.0, 4350.0, 4400.0, 4280.0],
            "provenance": "SYNTHETIC",
        }
    )

    hourly_df, diag = adapter.aggregate_15min_to_hourly(
        four_blocks_df,
        price_col="clearing_price_inr_mwh",
        volume_power_mw_col="cleared_volume_mw",
        energy_mwh_col=None,
    )

    assert len(hourly_df) == 1
    row = hourly_df.iloc[0]

    # Power sum is 4210 + 4350 + 4400 + 4280 = 17,240 MW
    # True energy is 17,240 * 0.25 = 4,310 MWh
    expected_energy_mwh = 17240.0 * 0.25  # 4,310.0 MWh
    expected_avg_power_mw = 17240.0 / 4.0  # 4,310.0 MW

    assert row["cleared_energy_mwh"] == pytest.approx(expected_energy_mwh, abs=0.01)
    assert row["cleared_energy_mwh"] != 17240.0  # Catch the exact 4x dimensional error
    assert row["cleared_average_power_mw"] == pytest.approx(expected_avg_power_mw, abs=0.01)
    assert diag.total_cleared_energy_mwh == pytest.approx(expected_energy_mwh, abs=0.01)

    # Weighted price:
    # sum(P_i * MW_i) / sum(MW_i)
    weighted_p = (
        5420.50 * 4210.0 + 5580.00 * 4350.0 + 5610.25 * 4400.0 + 5515.00 * 4280.0
    ) / 17240.0
    assert row["clearing_price_inr_mwh"] == pytest.approx(round(weighted_p, 2), abs=0.01)


@pytest.mark.unit
def test_iex_time_weighted_mean_without_volume(adapter, sample_complete_hour_df):
    """Verify arithmetic mean when volume data is absent."""
    df_no_vol = sample_complete_hour_df.drop(columns=["cleared_volume_mw", "cleared_energy_mwh"])
    hourly_df, diag = adapter.aggregate_15min_to_hourly(
        df_no_vol,
        price_col="clearing_price_inr_mwh",
        volume_power_mw_col=None,
        energy_mwh_col=None,
    )

    assert len(hourly_df) == 1
    row = hourly_df.iloc[0]
    assert row["clearing_price_inr_mwh"] == 5000.0
    assert row["cleared_energy_mwh"] is None
    assert row["aggregation_method"] == "TIME_WEIGHTED_EQUAL_BLOCK_MEAN"
    assert diag.aggregation_method_used == "TIME_WEIGHTED_EQUAL_BLOCK_MEAN"


@pytest.mark.unit
def test_iex_missing_block_handling(adapter, sample_complete_hour_df):
    """Verify missing blocks detection and incomplete hour policy."""
    # Drop the 10:30 block
    incomplete_df = sample_complete_hour_df.drop(index=2).reset_index(drop=True)

    # With drop_incomplete_hours=True (default), hour is excluded
    hourly_df, diag = adapter.aggregate_15min_to_hourly(
        incomplete_df,
        drop_incomplete_hours=True,
    )
    assert len(hourly_df) == 0
    assert diag.incomplete_hours_count == 1
    assert len(diag.missing_blocks_details) == 1
    assert diag.missing_blocks_details[0]["blocks_found"] == 3
    assert diag.missing_blocks_details[0]["missing_minutes"] == [30]

    # With drop_incomplete_hours=False, hour is included but flagged INCOMPLETE
    # and cleared_energy_mwh is None while partial_cleared_energy_mwh is populated
    hourly_df_kept, diag_kept = adapter.aggregate_15min_to_hourly(
        incomplete_df,
        drop_incomplete_hours=False,
    )
    assert len(hourly_df_kept) == 1
    row = hourly_df_kept.iloc[0]
    assert row["status"] == "INCOMPLETE"
    assert row["cleared_energy_mwh"] is None  # Never silently report partial energy as full
    assert row["partial_cleared_energy_mwh"] is not None
    assert row["completeness_pct"] == 75.0


@pytest.mark.unit
def test_iex_duplicate_and_out_of_order_blocks(adapter):
    """Verify out-of-order blocks are sorted and duplicates are deduplicated."""
    df_messy = pd.DataFrame(
        {
            "timestamp": [
                "2025-03-01T10:45:00+05:30",
                "2025-03-01T10:00:00+05:30",
                "2025-03-01T10:15:00+05:30",
                "2025-03-01T10:15:00+05:30",  # Duplicate!
                "2025-03-01T10:30:00+05:30",
            ],
            "clearing_price_inr_mwh": [5000.0, 4000.0, 5000.0, 5000.0, 6000.0],
            "cleared_volume_mw": [1600.0, 400.0, 800.0, 800.0, 1200.0],
            "cleared_energy_mwh": [400.0, 100.0, 200.0, 200.0, 300.0],
        }
    )

    hourly_df, diag = adapter.aggregate_15min_to_hourly(df_messy)
    assert len(hourly_df) == 1
    assert diag.duplicate_blocks_count == 1
    assert diag.out_of_order_blocks_count > 0
    assert hourly_df.iloc[0]["block_count"] == 4


@pytest.mark.unit
def test_iex_negative_price_rejected(adapter, sample_complete_hour_df):
    """Verify negative price raises ValueError."""
    bad_df = sample_complete_hour_df.copy()
    bad_df.loc[1, "clearing_price_inr_mwh"] = -100.0

    with pytest.raises(ValueError, match="Negative electricity price detected"):
        adapter.aggregate_15min_to_hourly(bad_df)
