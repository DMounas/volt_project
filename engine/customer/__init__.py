"""VOLT Engine - Customer Flexibility Module.

Responsibilities:
- Customer request representation (arrival, deadline, required energy, priority class).
- Priority classification: Emergency, Priority Fleet, Commercial Logistics, Retail Flexible.
- Feasible flexibility envelopes and non-deferrable service bounds.
- Incentive response curves and opt-in demand shift modelling.
- Enforcement of customer tariff bounds [0.80x to 1.20x previous-day average].
"""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class CustomerFlexibilityProtocol(Protocol):
    """Protocol for customer demand flexibility and incentive response."""

    def evaluate_flexibility(self, request: dict[str, Any]) -> dict[str, Any]:
        """Compute permissible shifting window and associated incentive requirements."""
        ...
