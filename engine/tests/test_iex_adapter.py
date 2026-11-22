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
    """Create a single complete hour (4 15-minute blocks)."""
    return pd.DataFrame(
        {
            "timestamp": [
                "2026-03-01T10:00:00+05:30",
                "2026-03-01T10:15:00+05:30",
                "2026-03-01T10:30:00+05:30",
                "2026-03-01T10:45:00+05:30",
            ],
            "clearing_price_inr_mwh": [4000.0, 5000.0, 6000.0, 5000.0],
            "cleared_volume_mwh": [100.0, 200.0, 300.0, 400.0],
            "provenance": "SYNTHETIC",
        }
    )


@pytest.mark.unit
def test_iex_volume_weighted_aggregation(adapter, sample_complete_hour_df):
    """Verify volume-weighted calculation: sum(P * V) / sum(V)."""
    # Sum(P * V) = 4000*100 + 5000*200 + 6000*300 + 5000*400
    # = 400,000 + 1,000,000 + 1,800,000 + 2,000,000 = 5,200,000
    # Total Volume = 100 + 200 + 300 + 400 = 1000 MWh
    # Expected Price = 5,200,000 / 1000 = 5200.0 INR/MWh
    hourly_df, diag = adapter.aggregate_15min_to_hourly(
        sample_complete_hour_df,
        price_col="clearing_price_inr_mwh",
        volume_col="cleared_volume_mwh",
    )

    assert len(hourly_df) == 1
    row = hourly_df.iloc[0]
    assert row["price_inr_mwh"] == 5200.0
    assert row["volume_mwh"] == 1000.0
    assert row["aggregation_method"] == "VOLUME_WEIGHTED"
    assert row["block_count"] == 4
    assert diag.complete_hours_count == 1
    assert diag.incomplete_hours_count == 0


@pytest.mark.unit
def test_iex_time_weighted_mean_without_volume(adapter, sample_complete_hour_df):
    """Verify arithmetic mean when volume data is absent."""
    df_no_vol = sample_complete_hour_df.drop(columns=["cleared_volume_mwh"])
    # Mean(4000, 5000, 6000, 5000) = 20000 / 4 = 5000.0
    hourly_df, diag = adapter.aggregate_15min_to_hourly(
        df_no_vol,
        price_col="clearing_price_inr_mwh",
        volume_col=None,
    )

    assert len(hourly_df) == 1
    row = hourly_df.iloc[0]
    assert row["price_inr_mwh"] == 5000.0
    assert row["volume_mwh"] == 0.0
    assert row["aggregation_method"] == "TIME_WEIGHTED_EQUAL_BLOCK_MEAN"
    assert diag.aggregation_method_used == "TIME_WEIGHTED_EQUAL_BLOCK_MEAN"


@pytest.mark.unit
def test_iex_missing_block_handling(adapter, sample_complete_hour_df):
    """Verify missing blocks detection (e.g. 3 blocks instead of 4)."""
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
    hourly_df_kept, diag_kept = adapter.aggregate_15min_to_hourly(
        incomplete_df,
        drop_incomplete_hours=False,
    )
    assert len(hourly_df_kept) == 1
    assert hourly_df_kept.iloc[0]["status"] == "INCOMPLETE"


@pytest.mark.unit
def test_iex_duplicate_and_out_of_order_blocks(adapter):
    """Verify out-of-order blocks are sorted and duplicates are deduplicated."""
    df_messy = pd.DataFrame(
        {
            "timestamp": [
                "2026-03-01T10:45:00+05:30",
                "2026-03-01T10:00:00+05:30",
                "2026-03-01T10:15:00+05:30",
                "2026-03-01T10:15:00+05:30",  # Duplicate!
                "2026-03-01T10:30:00+05:30",
            ],
            "clearing_price_inr_mwh": [5000.0, 4000.0, 5000.0, 5000.0, 6000.0],
            "cleared_volume_mwh": [400.0, 100.0, 200.0, 200.0, 300.0],
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
