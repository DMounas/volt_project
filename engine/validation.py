"""Validation Utilities for VOLT.

Enforces physical and domain constraints:
- Non-empty and valid dimensional units
- Valid percentage and fraction ranges [0, 100] or [0.0, 1.0]
- Non-negative power and energy capacities
- Physical reserve bounds (e.g., must be > 0 and < 100%)
- Valid customer tariff guardrails (min <= base <= max)
"""

from typing import Iterable, Optional
from engine.provenance import Provenance

ALLOWED_STANDARD_UNITS = {
    "MW",
    "kW",
    "MWh",
    "kWh",
    "INR",
    "INR/MWh",
    "INR/kWh",
    "INR/swap",
    "fraction",
    "percent",
    "packs",
    "swaps",
    "hour",
    "minute",
    "1/h",
}


def validate_unit(unit: Optional[str], allowed_units: Optional[Iterable[str]] = None) -> str:
    """Validate that a unit string is provided and recognized."""
    if unit is None or not str(unit).strip():
        raise ValueError("Unit cannot be empty or None")

    cleaned = str(unit).strip()
    valid_set = set(allowed_units) if allowed_units is not None else ALLOWED_STANDARD_UNITS
    if cleaned not in valid_set:
        raise ValueError(f"Unrecognized unit: '{cleaned}'. Allowed units: {sorted(valid_set)}")
    return cleaned


def validate_percentage(
    value: float,
    is_fraction: bool = False,
    field_name: str = "percentage",
) -> float:
    """Validate that a percentage or fraction lies within physical bounds.

    Args:
        value: Numeric value to check.
        is_fraction: True if value is decimal fraction [0.0, 1.0], False if [0.0, 100.0].
        field_name: Name of the field for descriptive error messages.
    """
    val = float(value)
    if is_fraction:
        if not (0.0 <= val <= 1.0):
            raise ValueError(
                f"{field_name} as fraction must be between 0.0 and 1.0, got: {val}"
            )
    else:
        if not (0.0 <= val <= 100.0):
            raise ValueError(
                f"{field_name} must be between 0.0% and 100.0%, got: {val}"
            )
    return val


def validate_capacity(
    capacity: float,
    unit: str,
    field_name: str = "capacity",
) -> float:
    """Validate that installed or operational capacity is strictly non-negative and has a valid unit."""
    validate_unit(unit, allowed_units={"MW", "kW", "MWh", "kWh", "packs"})
    cap = float(capacity)
    if cap < 0.0:
        raise ValueError(f"{field_name} cannot be negative: {cap} {unit}")
    return cap


def validate_reserve_percentage(
    reserve: float,
    is_fraction: bool = True,
    field_name: str = "emergency_reserve",
) -> float:
    """Validate emergency reserve fraction/percentage.

    Reserve must be strictly greater than 0% and strictly less than 100%
    (an operator cannot have 0% emergency buffer or lock 100% of capacity).
    Case study mandates exactly 5% (0.05).
    """
    val = float(reserve)
    upper_bound = 1.0 if is_fraction else 100.0
    if val <= 0.0:
        raise ValueError(
            f"{field_name} must be strictly positive (> 0), got: {val}"
        )
    if val >= upper_bound:
        raise ValueError(
            f"{field_name} must be strictly less than {upper_bound} (100%), got: {val}"
        )
    return val


def validate_tariff_bounds(
    min_multiplier: float,
    max_multiplier: float,
) -> tuple[float, float]:
    """Validate customer tariff guardrail bounds.

    The case study establishes a 0.80 to 1.20 range around previous-day average.
    """
    min_m = float(min_multiplier)
    max_m = float(max_multiplier)

    if min_m <= 0.0:
        raise ValueError(f"Minimum tariff multiplier must be positive, got: {min_m}")
    if min_m > 1.0:
        raise ValueError(f"Minimum tariff multiplier cannot exceed 1.0, got: {min_m}")
    if max_m < 1.0:
        raise ValueError(f"Maximum tariff multiplier cannot be less than 1.0, got: {max_m}")
    if min_m >= max_m:
        raise ValueError(
            f"Minimum tariff multiplier ({min_m}) must be strictly less than maximum ({max_m})"
        )
    return min_m, max_m


def validate_provenance(provenance_value: str | Provenance) -> Provenance:
    """Validate and normalize provenance tag."""
    if isinstance(provenance_value, Provenance):
        return provenance_value
    return Provenance.from_str(str(provenance_value))
