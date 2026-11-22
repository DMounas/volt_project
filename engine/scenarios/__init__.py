"""VOLT Engine - Scenarios Module.

Responsibilities:
- Generation of correlated multi-vector uncertainty scenarios (demand, renewable, price).
- Stress-testing disturbance generators (e.g., heatwave demand peak, monsoon cloud cover, IEX price surge).
- Preservation of joint empirical residuals across energy vectors.
- Reproducible random seed management for deterministic policy comparison.
"""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ScenarioGeneratorProtocol(Protocol):
    """Protocol for correlated scenario generation."""

    def generate_scenarios(self, count: int, seed: int) -> list[dict[str, Any]]:
        """Generate a bundle of correlated operational disturbance scenarios."""
        ...
