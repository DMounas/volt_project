"""Tests for validation helpers in engine.validation."""

import pytest
from engine.provenance import Provenance
from engine.validation import (
    validate_capacity,
    validate_percentage,
    validate_provenance,
    validate_reserve_percentage,
    validate_tariff_bounds,
    validate_unit,
)


@pytest.mark.unit
def test_validate_unit():
    assert validate_unit("MW") == "MW"
    assert validate_unit("  MWh  ") == "MWh"
    assert validate_unit("INR/kWh") == "INR/kWh"

    with pytest.raises(ValueError, match="Unit cannot be empty"):
        validate_unit("")
    with pytest.raises(ValueError, match="Unit cannot be empty"):
        validate_unit(None)
    with pytest.raises(ValueError, match="Unrecognized unit"):
        validate_unit("gallons")


@pytest.mark.unit
def test_validate_percentage():
    assert validate_percentage(78.0, is_fraction=False) == 78.0
    assert validate_percentage(0.78, is_fraction=True) == 0.78

    with pytest.raises(ValueError, match="must be between 0.0% and 100.0%"):
        validate_percentage(105.0, is_fraction=False)
    with pytest.raises(ValueError, match="must be between 0.0 and 1.0"):
        validate_percentage(1.05, is_fraction=True)
    with pytest.raises(ValueError, match="must be between 0.0% and 100.0%"):
        validate_percentage(-2.0, is_fraction=False)


@pytest.mark.unit
def test_validate_capacity():
    assert validate_capacity(1200.0, "MW") == 1200.0
    assert validate_capacity(600.0, "MWh") == 600.0
    assert validate_capacity(0.0, "MW") == 0.0

    with pytest.raises(ValueError, match="cannot be negative"):
        validate_capacity(-100.0, "MW")
    with pytest.raises(ValueError, match="Unrecognized unit"):
        validate_capacity(100.0, "invalid_unit")


@pytest.mark.unit
def test_validate_reserve_percentage():
    # 5% reserve fraction (0.05) is valid
    assert validate_reserve_percentage(0.05, is_fraction=True) == 0.05
    assert validate_reserve_percentage(5.0, is_fraction=False) == 5.0

    # 0% reserve is invalid (operator cannot operate with 0% emergency buffer)
    with pytest.raises(ValueError, match="must be strictly positive"):
        validate_reserve_percentage(0.0, is_fraction=True)

    # 100% reserve is invalid (no schedulable capacity)
    with pytest.raises(ValueError, match="must be strictly less than"):
        validate_reserve_percentage(1.0, is_fraction=True)
    with pytest.raises(ValueError, match="must be strictly less than"):
        validate_reserve_percentage(100.0, is_fraction=False)


@pytest.mark.unit
def test_validate_tariff_bounds():
    # Case facts: 0.80 and 1.20
    min_m, max_m = validate_tariff_bounds(0.80, 1.20)
    assert min_m == 0.80
    assert max_m == 1.20

    with pytest.raises(ValueError, match="Minimum tariff multiplier must be positive"):
        validate_tariff_bounds(-0.1, 1.20)
    with pytest.raises(ValueError, match="Minimum tariff multiplier cannot exceed 1.0"):
        validate_tariff_bounds(1.1, 1.20)
    with pytest.raises(ValueError, match="Maximum tariff multiplier cannot be less than 1.0"):
        validate_tariff_bounds(0.8, 0.95)
    with pytest.raises(ValueError, match="must be strictly less than maximum"):
        validate_tariff_bounds(1.0, 1.0)


@pytest.mark.unit
def test_validate_provenance():
    assert validate_provenance("OBSERVED") == Provenance.OBSERVED
    assert validate_provenance("assumed") == Provenance.ASSUMED
    assert validate_provenance(Provenance.SYNTHETIC) == Provenance.SYNTHETIC

    with pytest.raises(ValueError, match="Invalid provenance value"):
        validate_provenance("UNKNOWN_PROVENANCE")
