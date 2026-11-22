"""Disturbance and Shock Event Engine for VOLT Digital Twin.

Loads scenario disturbances from config/scenarios.yaml and generates:
1. Actual ground truth realizations W(t) incorporating physical disturbances.
2. Forecast expectations W_hat(t | t0) available at forecast origin t0, strictly
   preventing future leakage (non-anticipative forecasting).
"""

import copy
from pathlib import Path
from typing import Any, Optional
import numpy as np
import yaml

from engine.optimization.schemas import ClusterHorizonInput
from engine.provenance import Provenance
from engine.twin.schemas import ShockScenarioType


class ScenarioEventEngine:
    """Manages shock definitions, deterministic perturbations, and forecast generation."""

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or (Path("config") / "scenarios.yaml")
        self._scenarios_cache: dict[str, dict[str, Any]] = {}
        self._load_config()

    def _load_config(self) -> None:
        """Parse scenarios from YAML file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Scenario configuration missing at {self.config_path}")

        with open(self.config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        for sc in data.get("scenarios", []):
            self._scenarios_cache[sc["id"]] = sc

    def list_scenarios(self) -> list[dict[str, Any]]:
        """Return full catalog of scenarios with metadata."""
        return list(self._scenarios_cache.values())

    def get_scenario(self, scenario_id: str) -> dict[str, Any]:
        """Retrieve single scenario configuration."""
        if scenario_id not in self._scenarios_cache:
            # Fallback to NORMAL_OPERATION
            return self._scenarios_cache.get(
                "NORMAL_OPERATION",
                {
                    "id": "NORMAL_OPERATION",
                    "name": "Normal Operational Day",
                    "severity": "LOW",
                    "start_hour": 0,
                    "duration_hours": 24,
                    "affected_clusters": ["ALL"],
                    "forecast_visibility": "FULL_AHEAD",
                    "multipliers": {
                        "fast_charge_demand": 1.0,
                        "swap_demand": 1.0,
                        "solar_generation": 1.0,
                        "wind_generation": 1.0,
                        "iex_price": 1.0,
                        "grid_import_cap_mw": 240.0,
                        "swap_bay_power_multiplier": 1.0,
                    },
                },
            )
        return self._scenarios_cache[scenario_id]

    def generate_actual_realization(
        self,
        scenario_id: str,
        baseline_inputs: dict[str, ClusterHorizonInput],
        seed: int = 42,
    ) -> dict[str, ClusterHorizonInput]:
        """Apply deterministic disturbance multipliers to baseline inputs to form ground-truth actuals."""
        sc = self.get_scenario(scenario_id)
        start_h = sc.get("start_hour", 0)
        end_h = start_h + sc.get("duration_hours", 24)
        aff_clusters = sc.get("affected_clusters", ["ALL"])
        mults = sc.get("multipliers", {})

        rng = np.random.default_rng(seed)
        actual_inputs: dict[str, ClusterHorizonInput] = {}

        for cid, b_input in baseline_inputs.items():
            # Deepcopy to preserve original
            actual = copy.deepcopy(b_input)
            is_affected = ("ALL" in aff_clusters) or (cid in aff_clusters)

            for t in range(len(actual.hours)):
                # Inject mild stochastic sensor noise in actuals (~1-2%)
                noise_dem = 1.0 + rng.normal(0.0, 0.015)
                noise_ren = 1.0 + rng.normal(0.0, 0.02)
                noise_px = 1.0 + rng.normal(0.0, 0.01)

                m_fc = 1.0
                m_swap = 1.0
                m_sol = 1.0
                m_wind = 1.0
                m_iex = 1.0
                grid_cap = 240.0

                if is_affected and (start_h <= t < end_h):
                    m_fc = float(mults.get("fast_charge_demand", 1.0))
                    m_swap = float(mults.get("swap_demand", 1.0))
                    m_sol = float(mults.get("solar_generation", 1.0))
                    m_wind = float(mults.get("wind_generation", 1.0))
                    m_iex = float(mults.get("iex_price", 1.0))
                    grid_cap = float(mults.get("grid_import_cap_mw", 240.0))

                actual.fast_charge_demand_mwh[t] = round(
                    max(0.0, b_input.fast_charge_demand_mwh[t] * m_fc * noise_dem), 3
                )
                actual.swap_requests_count[t] = int(
                    max(0, round(b_input.swap_requests_count[t] * m_swap * noise_dem))
                )
                actual.swap_energy_mwh[t] = round(
                    actual.swap_requests_count[t] * 2.25 / 1000.0, 4
                )
                actual.solar_available_mwh[t] = round(
                    max(0.0, b_input.solar_available_mwh[t] * m_sol * noise_ren), 3
                )
                actual.wind_available_mwh[t] = round(
                    max(0.0, b_input.wind_available_mwh[t] * m_wind * noise_ren), 3
                )
                actual.iex_dam_price_inr_per_mwh[t] = round(
                    min(10000.0, max(0.0, b_input.iex_dam_price_inr_per_mwh[t] * m_iex * noise_px)), 2
                )
                actual.iex_procurement_cap_mw[t] = min(60.0, grid_cap)

            actual_inputs[cid] = actual

        return actual_inputs

    def generate_forecast_expectation(
        self,
        scenario_id: str,
        baseline_inputs: dict[str, ClusterHorizonInput],
        actual_realizations: dict[str, ClusterHorizonInput],
        forecast_origin_hour: int,
        horizon_hours: int = 24,
        seed: int = 42,
    ) -> dict[str, ClusterHorizonInput]:
        """Generate 24-hour non-anticipative forecast vectors starting at forecast_origin_hour.

        Guarantees:
        - Information available at forecast_origin_hour respects scenario visibility:
          * ZERO_AHEAD: Before shock begins, forecast uses baseline nominal values.
            Once shock is active (t0 >= start_hour), forecast model updates based on
            observed condition.
          * PARTIAL_AHEAD: Forecast anticipates 50% of the shock magnitude.
          * FULL_AHEAD: Forecast anticipates 100% of the shock magnitude.
        - Strictly prevents future information leakage.
        """
        sc = self.get_scenario(scenario_id)
        start_h = sc.get("start_hour", 0)
        end_h = start_h + sc.get("duration_hours", 24)
        aff_clusters = sc.get("affected_clusters", ["ALL"])
        visibility = sc.get("forecast_visibility", "ZERO_AHEAD")
        mults = sc.get("multipliers", {})

        forecast_inputs: dict[str, ClusterHorizonInput] = {}

        for cid, b_input in baseline_inputs.items():
            actual = actual_realizations[cid]
            is_affected = ("ALL" in aff_clusters) or (cid in aff_clusters)

            # Construct vectors of length horizon_hours starting at forecast_origin_hour
            fc_fc: list[float] = []
            swap_cnt: list[int] = []
            swap_en: list[float] = []
            sol_fc: list[float] = []
            wind_fc: list[float] = []
            discom_fc: list[float] = []
            iex_fc: list[float] = []
            iex_cap: list[float] = []

            for step_idx in range(horizon_hours):
                target_t = (forecast_origin_hour + step_idx) % 24

                # Base expectation is baseline
                b_fc = b_input.fast_charge_demand_mwh[target_t]
                b_sw = b_input.swap_requests_count[target_t]
                b_sol = b_input.solar_available_mwh[target_t]
                b_wind = b_input.wind_available_mwh[target_t]
                b_dis = b_input.discom_tariff_inr_per_mwh[target_t]
                b_iex = b_input.iex_dam_price_inr_per_mwh[target_t]

                in_shock_window = is_affected and (start_h <= target_t < end_h)

                if not in_shock_window:
                    exp_fc = b_fc
                    exp_sw = b_sw
                    exp_sol = b_sol
                    exp_wind = b_wind
                    exp_iex = b_iex
                else:
                    m_fc = float(mults.get("fast_charge_demand", 1.0))
                    m_sw = float(mults.get("swap_demand", 1.0))
                    m_sol = float(mults.get("solar_generation", 1.0))
                    m_wind = float(mults.get("wind_generation", 1.0))
                    m_iex = float(mults.get("iex_price", 1.0))

                    if visibility == "FULL_AHEAD":
                        anticipation_factor = 1.0
                    elif visibility == "PARTIAL_AHEAD":
                        anticipation_factor = 0.50
                    else:  # ZERO_AHEAD
                        if forecast_origin_hour < start_h:
                            anticipation_factor = 0.0  # Surprise shock!
                        else:
                            # Shock already started, model observes state and adapts
                            anticipation_factor = 0.85

                    exp_fc = b_fc * (1.0 + (m_fc - 1.0) * anticipation_factor)
                    exp_sw = int(round(b_sw * (1.0 + (m_sw - 1.0) * anticipation_factor)))
                    exp_sol = b_sol * (1.0 + (m_sol - 1.0) * anticipation_factor)
                    exp_wind = b_wind * (1.0 + (m_wind - 1.0) * anticipation_factor)
                    exp_iex = b_iex * (1.0 + (m_iex - 1.0) * anticipation_factor)

                fc_fc.append(round(exp_fc, 3))
                swap_cnt.append(exp_sw)
                swap_en.append(round(exp_sw * 2.25 / 1000.0, 4))
                sol_fc.append(round(exp_sol, 3))
                wind_fc.append(round(exp_wind, 3))
                discom_fc.append(round(b_dis, 2))
                iex_fc.append(round(min(10000.0, max(0.0, exp_iex)), 2))
                iex_cap.append(60.0)

            forecast_inputs[cid] = ClusterHorizonInput(
                cluster_id=cid,
                hours=list(range(horizon_hours)),
                fast_charge_demand_mwh=fc_fc,
                swap_requests_count=swap_cnt,
                swap_energy_mwh=swap_en,
                solar_available_mwh=sol_fc,
                wind_available_mwh=wind_fc,
                discom_tariff_inr_per_mwh=discom_fc,
                iex_dam_price_inr_per_mwh=iex_fc,
                iex_procurement_cap_mw=iex_cap,
                previous_day_avg_tariff_inr_per_kwh=11.20,
                bess_state=actual.bess_state,
                swap_state=actual.swap_state,
            )

        return forecast_inputs
