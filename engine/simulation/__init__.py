"""VOLT Engine - Simulation & Digital Twin Module.

Responsibilities:
- High-fidelity hourly state simulation of the five-city network.
- Execution of first-interval decisions in simulated environment (charging deliveries, swap fulfillment, grid import).
- Tracking of observed state transitions, battery degradation, and queue waiting times.
- Deterministic seed execution enabling apples-to-apples comparison between operating policies.
"""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class DigitalTwinSimulationProtocol(Protocol):
    """Protocol for the digital-twin simulator."""

    def execute_step(self, decisions: dict[str, Any]) -> dict[str, Any]:
        """Execute dispatch decisions in simulation and return realized states."""
        ...
