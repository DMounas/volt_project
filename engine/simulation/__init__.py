"""VOLT Engine - Simulation & Digital Twin Module.

Responsibilities:
- High-fidelity hourly state simulation of the five-city network.
- Execution of first-interval decisions in simulated environment.
- Reconstructed Business-As-Usual (BAU) baseline policy and calibration routines.
- Energy meter-boundary reconciliation and reserve audit.
"""

from typing import Any, Protocol, runtime_checkable
from engine.simulation.baseline_calibration import (
    BaselineCalibrationReport,
    BaselineCalibrator,
    CalibrationParameterBounds,
)
from engine.simulation.baseline_policy import BaselineConfig, BaselineSimulationEngine


@runtime_checkable
class DigitalTwinSimulationProtocol(Protocol):
    """Protocol for the digital-twin simulator."""

    def execute_step(self, decisions: dict[str, Any]) -> dict[str, Any]:
        """Execute dispatch decisions in simulation and return realized states."""
        ...


__all__ = [
    "DigitalTwinSimulationProtocol",
    "BaselineConfig",
    "BaselineSimulationEngine",
    "BaselineCalibrator",
    "BaselineCalibrationReport",
    "CalibrationParameterBounds",
]
