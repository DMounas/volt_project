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
        gen1 = SyntheticDataGenerator(seed=42, start_date="2022-01-01", end_date="2022-01-03 23:00:00")
        manifest1 = gen1.generate_all(output_dir=Path(tmp1), demo_mode=True)

        gen2 = SyntheticDataGenerator(seed=42, start_date="2022-01-01", end_date="2022-01-03 23:00:00")
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
        gen1 = SyntheticDataGenerator(seed=42, start_date="2022-01-01", end_date="2022-01-03 23:00:00")
        manifest1 = gen1.generate_all(output_dir=Path(tmp1), demo_mode=True)

        gen2 = SyntheticDataGenerator(seed=999, start_date="2022-01-01", end_date="2022-01-03 23:00:00")
        manifest2 = gen2.generate_all(output_dir=Path(tmp2), demo_mode=True)

        assert (
            manifest1["files"]["cluster_hourly.csv.gz"]["sha256"]
            != manifest2["files"]["cluster_hourly.csv.gz"]["sha256"]
        )


@pytest.mark.unit
def test_synthetic_data_structure_and_bounds():
    """Verify structural validity, physical non-negativity and night solar cutoff."""
    with tempfile.TemporaryDirectory() as tmp:
        gen = SyntheticDataGenerator(seed=123, start_date="2022-01-01", end_date="2022-01-03 23:00:00")
        gen.generate_all(output_dir=Path(tmp), demo_mode=True)

        df = pd.read_csv(Path(tmp) / "cluster_hourly.csv.gz", compression="gzip")

        # 5 clusters present
        expected_clusters = {"delhi_ncr", "mumbai_mmr", "bengaluru", "hyderabad", "chennai"}
        assert set(df["cluster_id"].unique()) == expected_clusters

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


@pytest.mark.unit
def test_leap_year_calendar():
    """Verify 2024 leap year produces 8,784 hours, not 8,760."""
    t_index = pd.date_range("2024-01-01", "2024-12-31 23:00:00", freq="h", tz="Asia/Kolkata")
    assert len(t_index) == 8784
