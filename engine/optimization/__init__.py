"""VOLT Engine - Optimization Module.

Responsibilities:
- Mixed-Integer Linear Programming (MILP) formulation for multi-cluster energy orchestration.
- Risk-aware objective combining expected operating cost and CVaR tail risk.
- Physical hard constraints: power balance, line import limits, storage dynamics, tariff guardrails, 5% emergency reserve.
- Safe heuristic fallback mechanism when solver exceeds time limit or encounters numerical infeasibility.
- Clear causality breakdown: Reason codes and binding constraint identification for each decision.
"""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class OptimizerProtocol(Protocol):
    """Protocol for the MILP energy orchestrator."""

    def build_model(self, parameters: dict[str, Any]) -> Any:
        """Construct the mathematical model for the planning horizon."""
        ...

    def solve(self, timeout_seconds: int = 60) -> dict[str, Any]:
        """Solve the optimization problem and return decision variables with explanations."""
        ...
