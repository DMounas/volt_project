"""Configuration service for loading and validating VOLT YAML configurations."""

import os
from pathlib import Path
from typing import Any, Optional
import yaml

from backend.app.schemas.case_config import (
    CapacityMixItem,
    CaseConfigResponse,
    CustomerTariffGuardrail,
    EbitdaBenchmark,
    EmergencyReserveGuardrail,
    EnergyLossBenchmark,
    MetricItem,
    ReliabilityBenchmark,
    StorageCapacityFact,
    UnknownAssumptionDisclosure,
)
from backend.app.schemas.cluster import ClusterInfo, ClustersResponse
from backend.app.schemas.scenario import ScenarioMetadata, ScenariosResponse
from engine.provenance import Provenance
from engine.validation import (
    validate_capacity,
    validate_percentage,
    validate_reserve_percentage,
    validate_tariff_bounds,
)


class ConfigService:
    """Manages loading, parsing, validating and serving VOLT YAML configurations."""

    def __init__(self, config_dir: Optional[str] = None):
        self._config_dir = self._resolve_config_dir(config_dir)
        self._case_cache: Optional[dict[str, Any]] = None
        self._assumptions_cache: Optional[dict[str, Any]] = None
        self._scenarios_cache: Optional[dict[str, Any]] = None
        self._model_cache: Optional[dict[str, Any]] = None

    def _resolve_config_dir(self, explicit_dir: Optional[str]) -> Path:
        """Resolve the path to the configs directory."""
        if explicit_dir is not None:
            explicit_path = Path(explicit_dir)
            if not explicit_path.exists() or not explicit_path.is_dir():
                raise FileNotFoundError(
                    f"Explicit configs directory not found: {explicit_dir}"
                )
            if not (explicit_path / "case_study.yaml").exists():
                raise FileNotFoundError(
                    f"case_study.yaml not found in explicit configs directory: {explicit_dir}"
                )
            return explicit_path.resolve()

        candidates = []
        if os.getenv("CONFIG_DIR"):
            candidates.append(Path(os.getenv("CONFIG_DIR", "")))

        # Relative paths from working directory and file location
        candidates.append(Path("configs"))
        candidates.append(Path(__file__).resolve().parent.parent.parent.parent / "configs")

        for path in candidates:
            if path.exists() and path.is_dir() and (path / "case_study.yaml").exists():
                return path.resolve()

        raise FileNotFoundError(
            f"Could not locate VOLT configs directory. Checked: {[str(c) for c in candidates]}"
        )

    def _load_yaml(self, filename: str) -> dict[str, Any]:
        """Load and parse a YAML configuration file."""
        file_path = self._config_dir / filename
        if not file_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                if not isinstance(data, dict):
                    raise ValueError(
                        f"Expected YAML file {filename} to parse to a dictionary, got {type(data).__name__}"
                    )
                return data
        except yaml.YAMLError as e:
            raise ValueError(f"Failed to parse YAML file {filename}: {e}") from e

    def get_raw_case_study(self) -> dict[str, Any]:
        """Get raw parsed case study configuration."""
        if self._case_cache is None:
            self._case_cache = self._load_yaml("case_study.yaml")
        return self._case_cache

    def get_raw_assumptions(self) -> dict[str, Any]:
        """Get raw parsed assumptions register."""
        if self._assumptions_cache is None:
            self._assumptions_cache = self._load_yaml("assumptions.yaml")
        return self._assumptions_cache

    def get_raw_scenarios(self) -> dict[str, Any]:
        """Get raw parsed scenario definitions."""
        if self._scenarios_cache is None:
            self._scenarios_cache = self._load_yaml("scenarios.yaml")
        return self._scenarios_cache

    def get_raw_model(self) -> dict[str, Any]:
        """Get raw parsed mathematical model configuration."""
        if self._model_cache is None:
            self._model_cache = self._load_yaml("model.yaml")
        return self._model_cache

    def get_case_config(self) -> CaseConfigResponse:
        """Parse, strictly validate, and return the source case study configuration."""
        raw_case = self.get_raw_case_study()
        raw_assump = self.get_raw_assumptions()

        # Validate installed capacity
        inst_cap = raw_case["installed_capacity"]
        validate_capacity(inst_cap["value"], inst_cap["unit"], "installed_capacity")

        # Validate mix percentages
        fc = raw_case["capacity_mix"]["fast_charging"]
        sw = raw_case["capacity_mix"]["battery_swapping"]
        validate_percentage(fc["percentage"], is_fraction=False, field_name="fast_charging_share")
        validate_percentage(sw["percentage"], is_fraction=False, field_name="swap_share")

        if round(fc["share"] + sw["share"], 4) != 1.0:
            raise ValueError("Fast-charging and swap modality shares must sum to 1.0 (100%)")

        # Validate reserve
        em_res = raw_case["operating_guardrails"]["emergency_reserve"]
        validate_reserve_percentage(em_res["value"], is_fraction=True)

        # Validate tariff bounds
        tb = raw_case["operating_guardrails"]["customer_tariff_bound"]
        validate_tariff_bounds(tb["min_multiplier"], tb["max_multiplier"])

        # Unknown assumptions disclosures
        unknowns = [
            UnknownAssumptionDisclosure(
                parameter="Individual city capacity allocation",
                case_fact_status="Unknown in case study (only aggregate 1,200 MW supplied)",
                assumed_value=raw_assump.get("cluster_capacity_allocation", {}).get(
                    "method", "equal_share_baseline"
                ),
                unit="fraction/MW",
                provenance=Provenance.ASSUMED,
                rationale="Equal 20% (240 MW) per cluster baseline is configured in assumptions.yaml for simulation.",
            ),
            UnknownAssumptionDisclosure(
                parameter="600 MWh storage asset split (BESS vs swap packs)",
                case_fact_status="Unknown in case study (only aggregate 600 MWh combined supplied)",
                assumed_value="50% BESS (300 MWh) / 50% swap packs (300 MWh)",
                unit="fraction/MWh",
                provenance=Provenance.ASSUMED,
                rationale="50/50 baseline split configured in assumptions.yaml; subject to sensitivity testing.",
            ),
            UnknownAssumptionDisclosure(
                parameter="Stationary BESS power rating (MW)",
                case_fact_status="Unknown in case study (storage capacity MWh does not determine MW)",
                assumed_value=f"C-rate {raw_assump.get('stationary_bess_parameters', {}).get('c_rate', {}).get('value', 0.5)}C (150 MW)",
                unit="MW",
                provenance=Provenance.ASSUMED,
                rationale="Assumed 0.5C 2-hour duration rating for stationary BESS.",
            ),
        ]

        return CaseConfigResponse(
            title=raw_case["case_metadata"]["title"],
            specification_version=raw_case["case_metadata"]["specification_version"],
            currency=raw_case["case_metadata"]["currency"],
            clusters=raw_case["clusters"]["names"],
            cluster_count=raw_case["clusters"]["count"],
            cluster_provenance=Provenance(raw_case["clusters"]["provenance"]),
            installed_capacity=MetricItem(
                value=inst_cap["value"],
                unit=inst_cap["unit"],
                provenance=Provenance(inst_cap["provenance"]),
                description=inst_cap.get("description"),
            ),
            capacity_mix={
                "fast_charging": CapacityMixItem(
                    share=fc["share"],
                    percentage=fc["percentage"],
                    aggregate_capacity_mw=fc["aggregate_capacity_mw"],
                    unit=fc["unit"],
                    provenance=Provenance(fc["provenance"]),
                    description=fc["description"],
                ),
                "battery_swapping": CapacityMixItem(
                    share=sw["share"],
                    percentage=sw["percentage"],
                    aggregate_capacity_mw=sw["aggregate_capacity_mw"],
                    unit=sw["unit"],
                    provenance=Provenance(sw["provenance"]),
                    description=sw["description"],
                ),
            },
            storage_capacity=StorageCapacityFact(
                combined_storage_mwh=raw_case["storage_capacity"]["combined_storage_mwh"],
                unit=raw_case["storage_capacity"]["unit"],
                provenance=Provenance(raw_case["storage_capacity"]["provenance"]),
                asset_split_known=raw_case["storage_capacity"]["asset_split_known"],
                description=raw_case["storage_capacity"]["description"],
            ),
            renewable_sourcing_reference=MetricItem(
                value=raw_case["procurement_references"]["renewable_sourcing_share"]["value"],
                percentage=raw_case["procurement_references"]["renewable_sourcing_share"]["percentage"],
                unit=raw_case["procurement_references"]["renewable_sourcing_share"]["unit"],
                provenance=Provenance(
                    raw_case["procurement_references"]["renewable_sourcing_share"]["provenance"]
                ),
                description=raw_case["procurement_references"]["renewable_sourcing_share"]["description"],
            ),
            kpi_benchmarks=raw_case["kpi_benchmarks"],
            operating_guardrails=raw_case["operating_guardrails"],
            historical_data_specification=raw_case["historical_data_specification"],
            unknown_assumptions=unknowns,
        )

    def get_clusters(self) -> ClustersResponse:
        """Return the five configured metro clusters."""
        raw_case = self.get_raw_case_study()
        raw_assump = self.get_raw_assumptions()

        cluster_names = raw_case["clusters"]["names"]
        shares = raw_assump.get("cluster_capacity_allocation", {}).get("shares", {})

        cluster_list = []
        for name in cluster_names:
            slug = name.lower().replace(" ", "_").replace("-", "_")
            share_data = shares.get(name, {})
            share = share_data.get("share", 0.20)
            cap_mw = share_data.get("capacity_mw", 240.0)

            cluster_list.append(
                ClusterInfo(
                    cluster_id=slug,
                    name=name,
                    provenance=Provenance.OBSERVED,
                    installed_capacity_share_assumed=share,
                    installed_capacity_mw_assumed=cap_mw,
                    capacity_provenance=Provenance.ASSUMED,
                    grid_import_limit_mw_assumed=cap_mw,
                    status="active",
                )
            )

        return ClustersResponse(
            total_clusters=len(cluster_list),
            clusters=cluster_list,
            provenance=Provenance.OBSERVED,
        )

    def get_scenarios(self) -> ScenariosResponse:
        """Return configured scenario metadata."""
        raw_scenarios = self.get_raw_scenarios()
        scenarios_dict = raw_scenarios.get("scenarios", {})

        scenario_list = []
        for scenario_id, data in scenarios_dict.items():
            scenario_list.append(
                ScenarioMetadata(
                    scenario_id=scenario_id,
                    name=data["name"],
                    description=data["description"],
                    demand_multiplier=data["demand_multiplier"],
                    renewable_multiplier=data["renewable_multiplier"],
                    iex_price_multiplier=data["iex_price_multiplier"],
                    swap_demand_multiplier=data["swap_demand_multiplier"],
                    initial_pack_ready_fraction=data["initial_pack_ready_fraction"],
                    initial_bess_soc=data["initial_bess_soc"],
                    probability_weight=data["probability_weight"],
                    seed=data["seed"],
                    status=data.get("status", "configured"),
                    provenance=Provenance.SYNTHETIC,
                )
            )

        return ScenariosResponse(
            total_scenarios=len(scenario_list),
            scenarios=scenario_list,
            provenance=Provenance.SYNTHETIC,
        )


# Singleton instance
config_service = ConfigService()
