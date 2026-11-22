"""Central Unit Conversion Utilities for VOLT.

Converts consistently across power (MW, kW), energy (MWh, kWh),
and currency tariffs (INR/MWh, INR/kWh).
Enforces physical non-negativity and dimension consistency.
"""


def mw_to_kw(mw: float) -> float:
    """Convert power from Megawatts (MW) to Kilowatts (kW)."""
    if mw < 0:
        raise ValueError(f"Power cannot be negative: {mw} MW")
    return float(mw) * 1000.0


def kw_to_mw(kw: float) -> float:
    """Convert power from Kilowatts (kW) to Megawatts (MW)."""
    if kw < 0:
        raise ValueError(f"Power cannot be negative: {kw} kW")
    return float(kw) / 1000.0


def mwh_to_kwh(mwh: float) -> float:
    """Convert energy from Megawatt-hours (MWh) to Kilowatt-hours (kWh)."""
    if mwh < 0:
        raise ValueError(f"Energy cannot be negative: {mwh} MWh")
    return float(mwh) * 1000.0


def kwh_to_mwh(kwh: float) -> float:
    """Convert energy from Kilowatt-hours (kWh) to Megawatt-hours (MWh)."""
    if kwh < 0:
        raise ValueError(f"Energy cannot be negative: {kwh} kWh")
    return float(kwh) / 1000.0


def inr_per_mwh_to_inr_per_kwh(inr_mwh: float) -> float:
    """Convert electricity rate from INR/MWh to INR/kWh.

    Since 1 MWh = 1000 kWh, INR/kWh = (INR/MWh) / 1000.
    """
    if inr_mwh < 0:
        raise ValueError(f"Price cannot be negative: {inr_mwh} INR/MWh")
    return float(inr_mwh) / 1000.0


def inr_per_kwh_to_inr_per_mwh(inr_kwh: float) -> float:
    """Convert electricity rate from INR/kWh to INR/MWh.

    Since 1 MWh = 1000 kWh, INR/MWh = (INR/kWh) * 1000.
    """
    if inr_kwh < 0:
        raise ValueError(f"Price cannot be negative: {inr_kwh} INR/kWh")
    return float(inr_kwh) * 1000.0


def power_to_energy_mwh(power_mw: float, duration_hours: float) -> float:
    """Calculate energy in MWh delivered at constant power (MW) over duration (hours)."""
    if power_mw < 0:
        raise ValueError(f"Power cannot be negative: {power_mw} MW")
    if duration_hours < 0:
        raise ValueError(f"Duration cannot be negative: {duration_hours} hours")
    return float(power_mw) * float(duration_hours)


def energy_to_power_mw(energy_mwh: float, duration_hours: float) -> float:
    """Calculate average power in MW for an energy volume (MWh) over duration (hours)."""
    if energy_mwh < 0:
        raise ValueError(f"Energy cannot be negative: {energy_mwh} MWh")
    if duration_hours <= 0:
        raise ValueError(f"Duration must be strictly positive: {duration_hours} hours")
    return float(energy_mwh) / float(duration_hours)


def fraction_to_percent(fraction: float) -> float:
    """Convert decimal fraction (0.0 to 1.0) to percentage (0.0 to 100.0)."""
    if not 0.0 <= fraction <= 1.0:
        raise ValueError(f"Fraction must be in [0.0, 1.0], got {fraction}")
    return float(fraction) * 100.0


def percent_to_fraction(percent: float) -> float:
    """Convert percentage (0.0 to 100.0) to decimal fraction (0.0 to 1.0)."""
    if not 0.0 <= percent <= 100.0:
        raise ValueError(f"Percentage must be in [0.0, 100.0], got {percent}")
    return float(percent) / 100.0
