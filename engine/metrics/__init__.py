"""VOLT Engine - Metrics & KPI Module.

Responsibilities:
- Calculation of case-aligned service reliability (baseline 78%, target 89.7%).
- Energy loss ratio accounting across chargers, BESS, swap charging, and distribution (baseline 10%, target 8%).
- Per-cluster and consolidated EBITDA margin calculation (target >12%).
- Energy reconciliation and meter-boundary integrity validation.
"""

from typing import Any, Protocol, runtime_checkable
from engine.metrics.reconciliation import EnergyBalanceRecord, EnergyReconciliationAuditor


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


class MetricCalculator:
    """Production implementation of KPI calculations and business margin formulas."""

    def calculate_reliability(
        self, served_energy_mwh: float, forecast_demand_mwh: float
    ) -> float:
        """Calculate case-aligned service reliability percentage.

        Formula: 100 * served_energy_equivalent_mwh / forecast_energy_equivalent_demand_mwh
        """
        if forecast_demand_mwh <= 0:
            return 100.0 if served_energy_mwh >= 0 else 0.0
        return round(100.0 * float(served_energy_mwh) / float(forecast_demand_mwh), 2)

    def calculate_loss_ratio(
        self, total_losses_mwh: float, gross_input_mwh: float
    ) -> float:
        """Calculate system loss ratio percentage.

        Formula: 100 * metered_storage_conversion_distribution_losses_mwh / gross_energy_input_mwh
        """
        if gross_input_mwh <= 0:
            return 0.0
        return round(100.0 * float(total_losses_mwh) / float(gross_input_mwh), 2)

    def calculate_ebitda_margin(
        self, revenue_inr: float, operating_expenses_inr: float
    ) -> float:
        """Calculate operating EBITDA margin percentage.

        Formula: 100 * (revenue - operating_expenses) / revenue
        """
        if revenue_inr <= 0:
            return 0.0
        return round(100.0 * (float(revenue_inr) - float(operating_expenses_inr)) / float(revenue_inr), 2)


metric_calculator = MetricCalculator()

__all__ = [
    "MetricsCalculatorProtocol",
    "MetricCalculator",
    "metric_calculator",
    "EnergyBalanceRecord",
    "EnergyReconciliationAuditor",
]
