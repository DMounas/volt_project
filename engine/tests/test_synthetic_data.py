"""Tests for synthetic data generation pipeline."""

import tempfile
from pathlib import Path
import pandas as pd
import pytest
from engine.data.synthetic_generator import SyntheticDataGenerator


@pytest.mark.unit
def test_synthetic_data_determinism():
    """Verify that identical seed + configs produces identical datasets."""
    with tempfile.TemporaryDirectory() as tmp1, tempfile.TemporaryDirectory() as tmp2:
        gen1 = SyntheticDataGenerator(seed=42, start_date="2021-01-01", end_date="2021-01-03 23:00:00")
        manifest1 = gen1.generate_all(output_dir=Path(tmp1), demo_mode=True)

        gen2 = SyntheticDataGenerator(seed=42, start_date="2021-01-01", end_date="2021-01-03 23:00:00")
        manifest2 = gen2.generate_all(output_dir=Path(tmp2), demo_mode=True)

        # Compare SHA-256 checksums of generated files
        for fname in manifest1["files"]:
            assert (
                manifest1["files"][fname]["sha256"] == manifest2["files"][fname]["sha256"]
            ), f"Checksum mismatch for {fname}"


@pytest.mark.unit
def test_synthetic_data_different_seed():
    """Verify that different seed produces different datasets."""
    with tempfile.TemporaryDirectory() as tmp1, tempfile.TemporaryDirectory() as tmp2:
        gen1 = SyntheticDataGenerator(seed=42, start_date="2021-01-01", end_date="2021-01-03 23:00:00")
        manifest1 = gen1.generate_all(output_dir=Path(tmp1), demo_mode=True)

        gen2 = SyntheticDataGenerator(seed=999, start_date="2021-01-01", end_date="2021-01-03 23:00:00")
        manifest2 = gen2.generate_all(output_dir=Path(tmp2), demo_mode=True)

        assert (
            manifest1["files"]["cluster_hourly.csv.gz"]["sha256"]
            != manifest2["files"]["cluster_hourly.csv.gz"]["sha256"]
        )


@pytest.mark.unit
def test_synthetic_data_structure_and_bounds():
    """Verify structural validity, weather covariates, physical non-negativity and night solar cutoff."""
    with tempfile.TemporaryDirectory() as tmp:
        gen = SyntheticDataGenerator(seed=123, start_date="2021-01-01", end_date="2021-01-03 23:00:00")
        gen.generate_all(output_dir=Path(tmp), demo_mode=True)

        df = pd.read_csv(Path(tmp) / "cluster_hourly.csv.gz", compression="gzip")

        # 5 clusters present
        expected_clusters = {"delhi_ncr", "mumbai_mmr", "bengaluru", "hyderabad", "chennai"}
        assert set(df["cluster_id"].unique()) == expected_clusters

        # Weather covariates verified
        expected_weather_cols = {
            "ambient_temp_c",
            "relative_humidity_pct",
            "cloud_cover_pct",
            "precipitation_mm",
            "solar_irradiance_w_m2",
            "wind_speed_m_s",
        }
        for col in expected_weather_cols:
            assert col in df.columns, f"Required weather covariate '{col}' missing from cluster_hourly"

        # No negative demand or energy
        assert (df["fast_charge_demand_mwh"] >= 0).all()
        assert (df["swap_energy_equivalent_mwh"] >= 0).all()
        assert (df["renewable_available_mwh"] >= 0).all()
        assert (df["solar_available_mwh"] >= 0).all()
        assert (df["wind_available_mwh"] >= 0).all()

        # Solar strictly zero at night (e.g. 00:00, 02:00, 23:00)
        df["dt"] = pd.to_datetime(df["timestamp"])
        night_df = df[df["dt"].dt.hour.isin([0, 1, 2, 3, 4, 21, 22, 23])]
        assert (night_df["solar_available_mwh"] == 0.0).all()

        # Provenance is strictly SYNTHETIC
        assert (df["provenance"] == "SYNTHETIC").all()

        # Inspect IEX 15-minute file schema and dimensional consistency
        iex_df = pd.read_csv(Path(tmp) / "iex_dam_15min.csv.gz", compression="gzip")
        assert "cleared_volume_mw" in iex_df.columns
        assert "cleared_energy_mwh" in iex_df.columns
        # Verify 15-min energy = power * 0.25 h
        expected_energy = (iex_df["cleared_volume_mw"] * 0.25).round(3)
        diff = (iex_df["cleared_energy_mwh"] - expected_energy).abs().max()
        assert diff < 0.002, f"Dimensional error in IEX 15-min file: max diff = {diff}"


@pytest.mark.unit
def test_leap_year_calendar():
    """Verify 2024 leap year produces 8,784 hours, not 8,760."""
    t_index = pd.date_range("2024-01-01", "2024-12-31 23:00:00", freq="h", tz="Asia/Kolkata")
    assert len(t_index) == 8784


@pytest.mark.unit
def test_completed_historical_window():
    """Verify default generator window is 2021-01-01 to 2025-12-31 with 43,824 hours per cluster."""
    gen = SyntheticDataGenerator()
    assert gen.start_date == "2021-01-01"
    assert gen.end_date == "2025-12-31 23:00:00"

    t_index = pd.date_range(gen.start_date, gen.end_date, freq="h", tz="Asia/Kolkata")
    # 4 non-leap years (365*4) + 1 leap year (366) = 1,826 days = 43,824 hours
    assert len(t_index) == 43824
