"""Tests for ConfigService."""

import pytest
from backend.app.services.config_service import ConfigService


@pytest.mark.unit
def test_config_service_loads_files():
    service = ConfigService()
    case = service.get_raw_case_study()
    assumptions = service.get_raw_assumptions()
    scenarios = service.get_raw_scenarios()
    model = service.get_raw_model()

    assert case["case_metadata"]["title"] is not None
    assert assumptions["cluster_capacity_allocation"] is not None
    assert scenarios["scenarios"]["NORMAL"] is not None
    assert model["temporal_configuration"]["horizon_hours"] == 24


@pytest.mark.unit
def test_config_service_validates_case():
    service = ConfigService()
    case_config = service.get_case_config()
    assert case_config.installed_capacity.value == 1200.0
    assert case_config.storage_capacity.combined_storage_mwh == 600.0


@pytest.mark.unit
def test_config_service_nonexistent_dir():
    with pytest.raises(FileNotFoundError, match="Explicit configs directory not found"):
        ConfigService(config_dir="nonexistent_directory_abc123")
