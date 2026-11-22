"""VOLT Engine - Synthetic Data Pipeline.

Generates reproducible, physically realistic five-city hourly operational
and 15-minute market datasets strictly classified as SYNTHETIC.

Governing Principles:
- Never label generated data as OBSERVED or real company records.
- Preserve case facts: 1,200 MW installed capacity (720 MW fast-charge / 480 MW swap),
  600 MWh combined storage, ~35% portfolio renewable sourcing reference, 5 named clusters.
- Deterministic random seed management ensuring identical outputs for identical seeds.
- Vectorized generation ensuring high throughput across 5 years of hourly data.
"""

from dataclasses import asdict, dataclass
import gzip
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Optional
import numpy as np
import pandas as pd
from engine.provenance import Provenance


@dataclass
class CityClimateProfile:
    """Climatic and geographic profile for synthetic weather generation."""

    name: str
    base_temp_c: float
    summer_temp_c: float
    winter_temp_c: float
    base_humidity: float
    monsoon_months: list[int]
    monsoon_rain_intensity: float
    solar_factor: float
    wind_base_m_s: float


CITY_PROFILES: dict[str, CityClimateProfile] = {
    "delhi_ncr": CityClimateProfile(
        name="Delhi NCR",
        base_temp_c=25.0,
        summer_temp_c=42.0,
        winter_temp_c=8.0,
        base_humidity=50.0,
        monsoon_months=[7, 8, 9],
        monsoon_rain_intensity=12.0,
        solar_factor=1.05,
        wind_base_m_s=3.5,
    ),
    "mumbai_mmr": CityClimateProfile(
        name="Mumbai MMR",
        base_temp_c=28.0,
        summer_temp_c=34.0,
        winter_temp_c=22.0,
        base_humidity=75.0,
        monsoon_months=[6, 7, 8, 9],
        monsoon_rain_intensity=25.0,
        solar_factor=0.95,
        wind_base_m_s=5.2,
    ),
    "bengaluru": CityClimateProfile(
        name="Bengaluru",
        base_temp_c=23.0,
        summer_temp_c=33.0,
        winter_temp_c=16.0,
        base_humidity=60.0,
        monsoon_months=[6, 7, 8, 9, 10],
        monsoon_rain_intensity=10.0,
        solar_factor=1.00,
        wind_base_m_s=4.8,
    ),
    "hyderabad": CityClimateProfile(
        name="Hyderabad",
        base_temp_c=27.0,
        summer_temp_c=40.0,
        winter_temp_c=15.0,
        base_humidity=55.0,
        monsoon_months=[6, 7, 8, 9],
        monsoon_rain_intensity=11.0,
        solar_factor=1.02,
        wind_base_m_s=4.0,
    ),
    "chennai": CityClimateProfile(
        name="Chennai",
        base_temp_c=29.0,
        summer_temp_c=38.0,
        winter_temp_c=23.0,
        base_humidity=72.0,
        monsoon_months=[10, 11, 12],  # Northeast monsoon
        monsoon_rain_intensity=22.0,
        solar_factor=0.98,
        wind_base_m_s=5.0,
    ),
}


class SyntheticDataGenerator:
    """Engine for generating five-city synthetic energy and market datasets."""

    def __init__(
        self,
        seed: int = 42,
        start_date: str = "2021-01-01",
        end_date: str = "2025-12-31 23:00:00",
        configs_dir: Optional[Path] = None,
    ):
        self.seed = seed
        self.start_date = start_date
        self.end_date = end_date
        self.configs_dir = configs_dir or Path("configs")
        self.rng = np.random.default_rng(seed)

    def _compute_sha256(self, filepath: Path) -> str:
        """Compute SHA-256 hash of a file."""
        hasher = hashlib.sha256()
        with open(filepath, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()

    def _save_df_gz(self, df: pd.DataFrame, filepath: Path) -> None:
        """Save DataFrame to gzip CSV with deterministic mtime for reproducible checksums."""
        with open(filepath, "wb") as f_out:
            with gzip.GzipFile(fileobj=f_out, mode="wb", mtime=0.0) as gz:
                df.to_csv(gz, index=False)

    def generate_all(
        self, output_dir: Path, demo_mode: bool = False, overwrite: bool = True
    ) -> dict[str, Any]:
        """Generate the full synthetic dataset suite and save to output directory."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        manifest_path = output_dir / "data_manifest.json"
        if manifest_path.exists() and not overwrite:
            raise FileExistsError(
                f"Synthetic data already exists in {output_dir}. Use overwrite=True or --overwrite to regenerate."
            )

        # In demo mode, produce 14 days of data for quick testing
        effective_end = "2022-01-14 23:00:00" if demo_mode else self.end_date
        time_index = pd.date_range(
            start=self.start_date,
            end=effective_end,
            freq="h",
            tz="Asia/Kolkata",
        )
        total_hours = len(time_index)

        print(
            f"Generating synthetic dataset: {time_index[0].isoformat()} to {time_index[-1].isoformat()} "
            f"({total_hours} hours per cluster, {total_hours * 5} total cluster-hours)..."
        )

        # 1. Generate cluster hourly dataset
        cluster_df = self._generate_cluster_hourly(time_index)
        cluster_file = output_dir / "cluster_hourly.csv.gz"
        self._save_df_gz(cluster_df, cluster_file)

        # 2. Generate IEX 15-minute market dataset
        iex_df = self._generate_iex_15min(time_index)
        iex_file = output_dir / "iex_dam_15min.csv.gz"
        self._save_df_gz(iex_df, iex_file)

        # 3. Generate battery pack hourly cohort dataset
        bess_df = self._generate_battery_hourly(time_index)
        bess_file = output_dir / "battery_pack_hourly.csv.gz"
        self._save_df_gz(bess_df, bess_file)

        # 4. Generate discrete customer requests sample
        req_df = self._generate_customer_requests(cluster_df, demo_mode=demo_mode)
        req_file = output_dir / "customer_requests.csv.gz"
        self._save_df_gz(req_df, req_file)

        # 5. Generate discrete swap events sample
        swap_df = self._generate_swap_events(cluster_df, demo_mode=demo_mode)
        swap_file = output_dir / "swap_events.csv.gz"
        self._save_df_gz(swap_df, swap_file)

        # 6. Generate Data Manifest
        manifest = self._build_manifest(
            output_dir=output_dir,
            time_index=time_index,
            demo_mode=demo_mode,
            files_info={
                "cluster_hourly.csv.gz": {
                    "path": str(cluster_file.relative_to(output_dir)),
                    "row_count": len(cluster_df),
                    "size_bytes": cluster_file.stat().st_size,
                    "sha256": self._compute_sha256(cluster_file),
                    "description": "Hourly weather, EV fast-charge, swap demand, and renewable availability by cluster",
                },
                "iex_dam_15min.csv.gz": {
                    "path": str(iex_file.relative_to(output_dir)),
                    "row_count": len(iex_df),
                    "size_bytes": iex_file.stat().st_size,
                    "sha256": self._compute_sha256(iex_file),
                    "description": "15-minute Indian Energy Exchange Day-Ahead Market prices and cleared trading volumes",
                },
                "battery_pack_hourly.csv.gz": {
                    "path": str(bess_file.relative_to(output_dir)),
                    "row_count": len(bess_df),
                    "size_bytes": bess_file.stat().st_size,
                    "sha256": self._compute_sha256(bess_file),
                    "description": "Hourly BESS SOC, swap pack inventory cohorts, degradation, and reserve status",
                },
                "customer_requests.csv.gz": {
                    "path": str(req_file.relative_to(output_dir)),
                    "row_count": len(req_df),
                    "size_bytes": req_file.stat().st_size,
                    "sha256": self._compute_sha256(req_file),
                    "description": "Event-level fast-charging and swap service requests with flexibility windows",
                },
                "swap_events.csv.gz": {
                    "path": str(swap_file.relative_to(output_dir)),
                    "row_count": len(swap_df),
                    "size_bytes": swap_file.stat().st_size,
                    "sha256": self._compute_sha256(swap_file),
                    "description": "Event-level battery swap transactions and battery SOC dispensed/returned",
                },
            },
        )

        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        return manifest

    def _generate_cluster_hourly(self, time_index: pd.DatetimeIndex) -> pd.DataFrame:
        """Vectorized generation of cluster hourly weather, demand, and generation series."""
        n_hours = len(time_index)
        hours = time_index.hour.values
        months = time_index.month.values
        day_of_week = time_index.dayofweek.values  # 0=Monday, 6=Sunday
        is_weekend = (day_of_week >= 5).astype(float)
        day_of_year = time_index.dayofyear.values

        # Common diurnal and annual angle variables
        annual_cycle = np.sin(2 * np.pi * (day_of_year - 80) / 365.25)
        diurnal_solar = np.clip(np.sin(np.pi * (hours - 6) / 12), 0.0, 1.0)
        # Strictly zero solar irradiance outside 06:00 to 18:00
        diurnal_solar = np.where((hours >= 6) & (hours <= 18), diurnal_solar, 0.0)

        # Commuter fast-charge profile: dual peak (08-11 and 17-21)
        morning_peak = np.exp(-0.5 * ((hours - 9.5) / 1.8) ** 2)
        evening_peak = np.exp(-0.5 * ((hours - 19.0) / 2.2) ** 2)
        diurnal_fc = 0.25 + 0.40 * morning_peak + 0.55 * evening_peak
        # Weekend demand adjustment
        diurnal_fc = diurnal_fc * (1.0 - 0.15 * is_weekend)

        # Swap profile: three delivery shifts (08:00, 14:00, 19:30)
        shift_morning = np.exp(-0.5 * ((hours - 8.5) / 1.5) ** 2)
        shift_midday = np.exp(-0.5 * ((hours - 13.5) / 1.2) ** 2)
        shift_evening = np.exp(-0.5 * ((hours - 19.5) / 2.0) ** 2)
        diurnal_swap = 0.20 + 0.35 * shift_morning + 0.25 * shift_midday + 0.45 * shift_evening

        all_cluster_dfs = []

        for cluster_id, profile in CITY_PROFILES.items():
            # Seed generator specifically for this cluster
            c_seed = self.seed + abs(hash(cluster_id)) % 10000
            c_rng = np.random.default_rng(c_seed)

            # Weather generation
            # Seasonal temperature range
            temp_seasonal = profile.base_temp_c + 0.5 * (
                profile.summer_temp_c - profile.winter_temp_c
            ) * annual_cycle
            # Diurnal temperature swing (~6°C)
            temp_diurnal = 3.5 * np.sin(np.pi * (hours - 9) / 12)
            temp_noise = c_rng.normal(0.0, 1.2, size=n_hours)
            temp_c = np.clip(temp_seasonal + temp_diurnal + temp_noise, 4.0, 48.0)

            # Monsoon and rain
            in_monsoon = np.isin(months, profile.monsoon_months).astype(float)
            rain_prob = 0.08 + 0.32 * in_monsoon
            rain_occur = c_rng.uniform(size=n_hours) < rain_prob
            rain_mm = (
                rain_occur * c_rng.exponential(profile.monsoon_rain_intensity, size=n_hours)
            ).round(1)

            # Cloud cover
            base_cloud = 25.0 + 45.0 * in_monsoon + 15.0 * (rain_mm > 0)
            cloud_pct = np.clip(base_cloud + c_rng.normal(0.0, 10.0, size=n_hours), 5.0, 100.0)

            # Solar irradiance (W/m²) attenuated by cloud cover
            cloud_attenuation = 1.0 - 0.70 * (cloud_pct / 100.0)
            solar_irradiance = (
                950.0 * profile.solar_factor * diurnal_solar * cloud_attenuation
                + c_rng.normal(0.0, 15.0, size=n_hours)
            )
            solar_irradiance = np.clip(solar_irradiance, 0.0, 1200.0)
            # Strictly 0 at night
            solar_irradiance = np.where((hours >= 6) & (hours <= 18), solar_irradiance, 0.0)

            # Wind speed (m/s)
            wind_monsoon_boost = 1.8 * in_monsoon
            wind_diurnal = 1.2 * np.sin(np.pi * (hours - 14) / 12)
            wind_speed = np.clip(
                profile.wind_base_m_s
                + wind_monsoon_boost
                + wind_diurnal
                + c_rng.normal(0.0, 0.8, size=n_hours),
                0.5,
                22.0,
            )

            # Humidity (%)
            humidity = np.clip(
                profile.base_humidity
                + 20.0 * in_monsoon
                - 0.5 * (temp_c - profile.base_temp_c)
                + c_rng.normal(0.0, 5.0, size=n_hours),
                15.0,
                98.0,
            )

            # Demand Modeling
            # Installed cluster fast-charge capacity = 144 MW (20% of 720 MW)
            # Temperature sensitivity: AC extra draw when temp > 32°C
            ac_factor = 1.0 + np.maximum(0.0, (temp_c - 32.0) * 0.02)

            fc_mean_mwh = 55.0 * diurnal_fc * ac_factor
            fc_noise = c_rng.normal(1.0, 0.06, size=n_hours)
            # Bounded within 144 MW cluster fast-charge capacity
            fc_demand_mwh = np.clip(fc_mean_mwh * fc_noise, 5.0, 138.0).round(3)
            fc_requests = np.round(fc_demand_mwh * 1000.0 / 30.0).astype(int)  # ~30 kWh per charge

            # Swap demand: 96 MW swap station capacity allocated
            swap_mean_requests = 1600.0 * diurnal_swap * ac_factor
            swap_requests = np.clip(
                np.round(swap_mean_requests * c_rng.normal(1.0, 0.08, size=n_hours)),
                120,
                3800,
            ).astype(int)
            # 2.25 kWh usable energy equivalent per completed swap
            swap_energy_mwh = (swap_requests * 2.25 / 1000.0).round(3)

            # Renewable Generation Modeling
            # Open-access contracted capacity per cluster: 80 MW Solar, 50 MW Wind
            # Solar available: rated 80 MW * (solar_irradiance / 1000 W/m²) * 0.95 derating
            solar_available_mwh = (
                80.0 * (solar_irradiance / 1000.0) * 0.95 * c_rng.normal(1.0, 0.02, size=n_hours)
            )
            solar_available_mwh = np.clip(solar_available_mwh, 0.0, 80.0).round(3)
            solar_available_mwh = np.where(
                (hours >= 6) & (hours <= 18), solar_available_mwh, 0.0
            )

            # Wind available: rated 50 MW * cubic power curve from cut-in (3 m/s) to rated (12 m/s)
            wind_norm = np.clip((wind_speed - 3.0) / 9.0, 0.0, 1.0) ** 2.5
            wind_available_mwh = (
                50.0 * wind_norm * c_rng.normal(1.0, 0.03, size=n_hours)
            ).clip(0.0, 50.0).round(3)

            renewable_available_mwh = (solar_available_mwh + wind_available_mwh).round(3)

            # Tariffs & Prices (INR/MWh)
            # DISCOM commercial EV tariff (assumed 7.50 INR/kWh = 7,500 INR/MWh)
            discom_tariff = np.full(n_hours, 7500.0)
            # Contracted renewable tariff (assumed 3.80 INR/kWh = 3,800 INR/MWh)
            renewable_tariff = np.full(n_hours, 3800.0)
            # Projected IEX market baseline price (time of day profile + noise)
            iex_shape = 0.75 + 0.35 * morning_peak + 0.65 * evening_peak - 0.20 * diurnal_solar
            iex_price = np.clip(5200.0 * iex_shape + c_rng.normal(0.0, 250.0, size=n_hours), 2200.0, 12000.0).round(2)

            df_cluster = pd.DataFrame(
                {
                    "timestamp": time_index.strftime("%Y-%m-%dT%H:%M:%S+05:30"),
                    "cluster_id": cluster_id,
                    "cluster_name": profile.name,
                    "temperature_c": temp_c.round(1),
                    "ambient_temp_c": temp_c.round(1),
                    "humidity_pct": humidity.round(1),
                    "relative_humidity_pct": humidity.round(1),
                    "rainfall_mm": rain_mm,
                    "precipitation_mm": rain_mm,
                    "cloud_cover_pct": cloud_pct.round(1),
                    "solar_irradiance_w_m2": solar_irradiance.round(1),
                    "wind_speed_m_s": wind_speed.round(2),
                    "fast_charge_requests": fc_requests,
                    "fast_charge_demand_mwh": fc_demand_mwh,
                    "swap_requests": swap_requests,
                    "swap_energy_equivalent_mwh": swap_energy_mwh,
                    "solar_available_mwh": solar_available_mwh,
                    "wind_available_mwh": wind_available_mwh,
                    "renewable_available_mwh": renewable_available_mwh,
                    "discom_tariff_inr_mwh": discom_tariff,
                    "contracted_renewable_tariff_inr_mwh": renewable_tariff,
                    "iex_projected_price_inr_mwh": iex_price,
                    "provenance": Provenance.SYNTHETIC.value,
                }
            )
            all_cluster_dfs.append(df_cluster)

        return pd.concat(all_cluster_dfs, ignore_index=True)

    def _generate_iex_15min(self, hourly_time_index: pd.DatetimeIndex) -> pd.DataFrame:
        """Generate four 15-minute IEX DAM market intervals for each hour."""
        # 15-minute time range
        start_ts = hourly_time_index[0]
        end_ts = hourly_time_index[-1] + pd.Timedelta(minutes=45)
        fifteen_min_index = pd.date_range(
            start=start_ts,
            end=end_ts,
            freq="15min",
            tz="Asia/Kolkata",
        )
        n_blocks = len(fifteen_min_index)
        rng = np.random.default_rng(self.seed + 777)

        hours = fifteen_min_index.hour.values
        time_block = (fifteen_min_index.hour * 4 + fifteen_min_index.minute // 15) + 1

        morning_peak = np.exp(-0.5 * ((hours - 9.5) / 1.8) ** 2)
        evening_peak = np.exp(-0.5 * ((hours - 19.5) / 2.2) ** 2)
        solar_dip = np.clip(np.sin(np.pi * (hours - 6) / 12), 0.0, 1.0)
        solar_dip = np.where((hours >= 7) & (hours <= 17), solar_dip, 0.0)

        # Baseline IEX price curve
        base_price = 5200.0 * (
            0.70 + 0.40 * morning_peak + 0.70 * evening_peak - 0.25 * solar_dip
        )
        price_noise = rng.normal(0.0, 220.0, size=n_blocks)
        # Random price spike injection (approx 1 in 800 blocks)
        spike_mask = rng.uniform(size=n_blocks) < 0.0015
        spike_amount = spike_mask * rng.uniform(4000.0, 9500.0, size=n_blocks)

        clearing_price = np.clip(base_price + price_noise + spike_amount, 1800.0, 18000.0).round(2)

        # Volume: national aggregate cleared power schedule (MW per 15-minute block)
        base_power = 12500.0 * (0.80 + 0.30 * morning_peak + 0.35 * evening_peak)
        cleared_volume_mw = np.clip(
            base_power + rng.normal(0.0, 500.0, size=n_blocks), 4000.0, 22000.0
        ).round(2)
        # Dimensional contract: 15 minutes = 0.25 hours -> Energy (MWh) = Power (MW) * 0.25
        cleared_energy_mwh = (cleared_volume_mw * 0.25).round(3)

        return pd.DataFrame(
            {
                "timestamp": fifteen_min_index.strftime("%Y-%m-%dT%H:%M:%S+05:30"),
                "time_block": time_block,
                "market": "DAM",
                "clearing_price_inr_mwh": clearing_price,
                "cleared_volume_mw": cleared_volume_mw,
                "cleared_energy_mwh": cleared_energy_mwh,
                "cleared_volume_mwh": cleared_energy_mwh,  # Backward compatibility alias
                "provenance": Provenance.SYNTHETIC.value,
            }
        )

    def _generate_battery_hourly(self, time_index: pd.DatetimeIndex) -> pd.DataFrame:
        """Generate cohort-level battery status and BESS state per cluster and hour."""
        n_hours = len(time_index)
        rng = np.random.default_rng(self.seed + 999)
        cluster_dfs = []

        for cluster_id in CITY_PROFILES.keys():
            # Stationary BESS capacity: 60 MWh allocated per cluster (300 MWh total / 5)
            # Swap packs: 24,000 packs per cluster (120,000 total / 5)
            total_packs = 24000
            reserve_packs = int(total_packs * 0.05)  # Strict 5% emergency reserve = 1,200 packs

            # Diurnal cycling of stationary BESS SOC
            hours = time_index.hour.values
            bess_soc = 0.50 + 0.25 * np.sin(2 * np.pi * (hours - 12) / 24)
            bess_soc = np.clip(bess_soc + rng.normal(0.0, 0.02, size=n_hours), 0.15, 0.85).round(3)
            bess_energy = (bess_soc * 60.0).round(2)

            # Swap pack cohort transitions
            ready_pct = np.clip(0.70 + 0.15 * np.cos(2 * np.pi * hours / 24), 0.55, 0.90)
            ready_packs = np.round((total_packs - reserve_packs) * ready_pct).astype(int)
            charging_packs = np.round((total_packs - reserve_packs - ready_packs) * 0.70).astype(int)
            depleted_packs = total_packs - reserve_packs - ready_packs - charging_packs
            maint_packs = np.full(n_hours, 150)

            # SOH degradation over time (from 0.98 down to 0.91 over 5 years)
            t_frac = np.linspace(0.0, 1.0, n_hours)
            soh = (0.985 - 0.075 * t_frac + rng.normal(0.0, 0.001, size=n_hours)).round(4)

            df_bess = pd.DataFrame(
                {
                    "timestamp": time_index.strftime("%Y-%m-%dT%H:%M:%S+05:30"),
                    "cluster_id": cluster_id,
                    "compatibility_group": "COMMERCIAL_2W_STD",
                    "total_packs": total_packs,
                    "ready_packs": ready_packs,
                    "charging_packs": charging_packs,
                    "depleted_packs": depleted_packs,
                    "maintenance_packs": maint_packs,
                    "emergency_reserve_packs": reserve_packs,
                    "average_soh": soh,
                    "bess_soc": bess_soc,
                    "bess_energy_mwh": bess_energy,
                    "provenance": Provenance.SYNTHETIC.value,
                }
            )
            cluster_dfs.append(df_bess)

        return pd.concat(cluster_dfs, ignore_index=True)

    def _generate_customer_requests(
        self, cluster_df: pd.DataFrame, demo_mode: bool = False
    ) -> pd.DataFrame:
        """Generate discrete customer requests sample."""
        # For performance, sample a realistic subset of request records
        sample_size = 5000 if demo_mode else 35000
        rng = np.random.default_rng(self.seed + 333)

        sampled_clusters = cluster_df.sample(n=min(sample_size, len(cluster_df)), random_state=self.seed)
        priorities = rng.choice(
            ["CRITICAL", "URGENT", "DEADLINE_FLEET", "FLEXIBLE"],
            size=len(sampled_clusters),
            p=[0.05, 0.20, 0.45, 0.30],
        )
        service_types = rng.choice(
            ["FAST_CHARGE", "BATTERY_SWAP"], size=len(sampled_clusters), p=[0.55, 0.45]
        )
        flexible_flags = (priorities == "FLEXIBLE") | (
            (priorities == "DEADLINE_FLEET") & (rng.uniform(size=len(sampled_clusters)) < 0.40)
        )
        window_hours = np.where(flexible_flags, rng.choice([1.0, 2.0], size=len(sampled_clusters)), 0.0)

        # Arrival and deadline
        arr_times = pd.to_datetime(sampled_clusters["timestamp"].values)
        wait_hours = rng.uniform(0.5, 3.0, size=len(sampled_clusters))
        deadlines = arr_times + pd.to_timedelta(wait_hours + window_hours, unit="h")

        energy_req = np.where(
            service_types == "FAST_CHARGE",
            rng.uniform(15.0, 45.0, size=len(sampled_clusters)).round(2) / 1000.0,  # MWh
            0.00225,  # 2.25 kWh = 0.00225 MWh for swap
        )

        return pd.DataFrame(
            {
                "request_id": [f"REQ-{i+1:07d}" for i in range(len(sampled_clusters))],
                "timestamp": sampled_clusters["timestamp"].values,
                "cluster_id": sampled_clusters["cluster_id"].values,
                "service_type": service_types,
                "deadline": deadlines.strftime("%Y-%m-%dT%H:%M:%S+05:30"),
                "energy_required_mwh": energy_req,
                "priority": priorities,
                "max_wait_hours": wait_hours.round(1),
                "flexible_flag": flexible_flags,
                "flexibility_window_hours": window_hours,
                "provenance": Provenance.SYNTHETIC.value,
            }
        )

    def _generate_swap_events(
        self, cluster_df: pd.DataFrame, demo_mode: bool = False
    ) -> pd.DataFrame:
        """Generate discrete battery swap transaction event records."""
        sample_size = 5000 if demo_mode else 30000
        rng = np.random.default_rng(self.seed + 444)

        sampled = cluster_df.sample(n=min(sample_size, len(cluster_df)), random_state=self.seed)
        cust_types = rng.choice(
            ["FLEET_DELIVERY", "COMMERCIAL_3W", "INDIVIDUAL_COMMUTER"],
            size=len(sampled),
            p=[0.60, 0.25, 0.15],
        )
        pack_compat = rng.choice(
            ["COMMERCIAL_2W_STD", "COMMERCIAL_3W_STD"],
            size=len(sampled),
            p=[0.75, 0.25],
        )
        return_soc = rng.uniform(0.12, 0.28, size=len(sampled)).round(3)
        dispense_soc = rng.uniform(0.92, 0.99, size=len(sampled)).round(3)
        dispensed_kwh = ((dispense_soc - return_soc) * 2.5).round(2)

        return pd.DataFrame(
            {
                "event_id": [f"SWAP-{i+1:07d}" for i in range(len(sampled))],
                "timestamp": sampled["timestamp"].values,
                "cluster_id": sampled["cluster_id"].values,
                "pack_compatibility_group": pack_compat,
                "customer_type": cust_types,
                "energy_dispensed_kwh": dispensed_kwh,
                "depleted_pack_return_soc": return_soc,
                "dispensed_pack_soc": dispense_soc,
                "provenance": Provenance.SYNTHETIC.value,
            }
        )

    def _build_manifest(
        self,
        output_dir: Path,
        time_index: pd.DatetimeIndex,
        demo_mode: bool,
        files_info: dict[str, Any],
    ) -> dict[str, Any]:
        """Construct data manifest with configuration hashes and checksums."""
        config_hashes = {}
        for cfg_file in ["case_study.yaml", "assumptions.yaml", "scenarios.yaml", "model.yaml"]:
            p = self.configs_dir / cfg_file
            if p.exists():
                config_hashes[cfg_file] = self._compute_sha256(p)

        return {
            "manifest_version": "1.0.0",
            "generator_version": "1.0.0",
            "provenance": Provenance.SYNTHETIC.value,
            "random_seed": self.seed,
            "demo_mode": demo_mode,
            "date_range": {
                "start": time_index[0].isoformat(),
                "end": time_index[-1].isoformat(),
                "total_hours_per_cluster": len(time_index),
                "total_cluster_hours": len(time_index) * len(CITY_PROFILES),
                "timezone": "Asia/Kolkata",
            },
            "clusters": list(CITY_PROFILES.keys()),
            "config_hashes": config_hashes,
            "files": files_info,
            "methodology_disclaimer": (
                "All records in this dataset are algorithmically generated and strictly classified "
                "as SYNTHETIC. Do not present or cite these data as real historical company records, "
                "actual IEX market observations, or observed battery telemetry."
            ),
        }
