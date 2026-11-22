"""VOLT Engine - Battery & Storage Module.

Responsibilities:
- Decoupled physical modelling for stationary BESS and swappable battery pack inventory.
- Stationary BESS: State of Charge (SOC), charge/discharge power limits, round-trip efficiency, degradation wear cost.
- Swappable pack inventory: Discrete pack status tracking (ready, charging, depleted, maintenance, emergency reserve).
- Strict enforcement of physical boundaries:
  * Swap packs NEVER discharge into the utility grid in the base design.
  * Stationary BESS MW power rating is independent of MWh capacity.
  * Mandatory 5% reserve remains uncommitted for emergency service.
"""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class BatteryModelProtocol(Protocol):
    """Protocol for battery state transition and inventory tracking."""

    def step(self, action: dict[str, Any], dt_hours: float) -> dict[str, Any]:
        """Update battery state of charge and pack inventory over time step dt."""
        ...
