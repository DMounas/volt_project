"""Tests for unit conversion utilities in engine.units."""

import pytest
from engine.units import (
    energy_to_power_mw,
    fraction_to_percent,
    inr_per_kwh_to_inr_per_mwh,
    inr_per_mwh_to_inr_per_kwh,
    kwh_to_mwh,
    mw_to_kw,
    mwh_to_kwh,
    percent_to_fraction,
    power_to_energy_mwh,
)


@pytest.mark.unit
def test_mw_to_kw():
    assert mw_to_kw(0.0) == 0.0
    assert mw_to_kw(1.0) == 1000.0
    assert mw_to_kw(1200.0) == 1200000.0
    with pytest.raises(ValueError, match="Power cannot be negative"):
        mw_to_kw(-10.0)


@pytest.mark.unit
def test_mwh_to_kwh():
    assert mwh_to_kwh(0.0) == 0.0
    assert mwh_to_kwh(1.0) == 1000.0
    assert mwh_to_kwh(600.0) == 600000.0
    with pytest.raises(ValueError, match="Energy cannot be negative"):
        mwh_to_kwh(-5.0)


@pytest.mark.unit
def test_kwh_to_mwh():
    assert kwh_to_mwh(0.0) == 0.0
    assert kwh_to_mwh(1000.0) == 1.0
    assert kwh_to_mwh(2500.0) == 2.5
    with pytest.raises(ValueError, match="Energy cannot be negative"):
        kwh_to_mwh(-100.0)


@pytest.mark.unit
def test_inr_conversions():
    # 5,000 INR/MWh = 5.0 INR/kWh
    assert inr_per_mwh_to_inr_per_kwh(5000.0) == 5.0
    assert inr_per_kwh_to_inr_per_mwh(5.0) == 5000.0

    # Case study tariffs
    assert inr_per_kwh_to_inr_per_mwh(11.5) == 11500.0
    assert inr_per_mwh_to_inr_per_kwh(11500.0) == 11.5

    with pytest.raises(ValueError, match="Price cannot be negative"):
        inr_per_mwh_to_inr_per_kwh(-10.0)
    with pytest.raises(ValueError, match="Price cannot be negative"):
        inr_per_kwh_to_inr_per_mwh(-1.0)


@pytest.mark.unit
def test_power_energy_duration_conversions():
    # 100 MW power for 2 hours = 200 MWh
    assert power_to_energy_mwh(100.0, 2.0) == 200.0
    # 200 MWh energy over 2 hours = 100 MW average power
    assert energy_to_power_mw(200.0, 2.0) == 100.0

    with pytest.raises(ValueError, match="Duration must be strictly positive"):
        energy_to_power_mw(100.0, 0.0)
    with pytest.raises(ValueError, match="Power cannot be negative"):
        power_to_energy_mwh(-50.0, 1.0)


@pytest.mark.unit
def test_percentage_fraction_conversions():
    assert fraction_to_percent(0.897) == pytest.approx(89.7)
    assert percent_to_fraction(89.7) == pytest.approx(0.897)
    assert fraction_to_percent(0.05) == pytest.approx(5.0)

    with pytest.raises(ValueError, match="Fraction must be in"):
        fraction_to_percent(1.5)
    with pytest.raises(ValueError, match="Percentage must be in"):
        percent_to_fraction(110.0)
