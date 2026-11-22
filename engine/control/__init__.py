"""VOLT Engine - Control & MPC Module.

Responsibilities:
- Rolling-horizon Model Predictive Control (MPC) orchestration loop.
- Execution sequence: Read observed state -> update rolling 24h forecasts -> optimize -> publish interval 1 actions.
- Integration of observed state feedback from the digital-twin simulator.
- Safe-mode dispatch triggers upon solver infeasibility or unexpected grid events.
"""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class MPCControllerProtocol(Protocol):
    """Protocol for rolling-horizon MPC orchestration."""

    def step_cycle(self, current_state: dict[str, Any]) -> dict[str, Any]:
        """Execute one complete rolling MPC iteration and return immediate interval actions."""
        ...
