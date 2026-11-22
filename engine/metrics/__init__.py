"""VOLT Engine - Metrics & KPI Module.

Responsibilities:
- Calculation of case-aligned service reliability (baseline 78%, target 89.7%).
- Energy loss ratio accounting across chargers, BESS, swap charging, and distribution (baseline 10%, target 8%).
- Per-cluster and consolidated EBITDA margin calculation (target >12%).
- Degradation-adjusted economic contribution (EBITDA less modeled battery wear reserve).
- Constraint violation verification and emergency reserve audit.
"""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class MetricsCalculatorProtocol(Protocol):
    """Protocol for calculating network KPIs and accounting margins."""

    def calculate_reliability(
        self, served_energy_mwh: float, forecast_demand_mwh: float
    ) -> float:
        """Calculate energy-equivalent service reliability percentage."""
        ...

    def calculate_loss_ratio(
        self, total_losses_mwh: float, gross_input_mwh: float
    ) -> float:
        """Calculate system storage, conversion and distribution loss percentage."""
        ...

    def calculate_ebitda_margin(
        self, revenue_inr: float, operating_expenses_inr: float
    ) -> float:
        """Calculate operating EBITDA margin percentage."""
        ...
