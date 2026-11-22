"""VOLT Engine - Forecasting Module.

Responsibilities:
- Forecasting cluster-level fast-charge demand (MWh).
- Forecasting cluster-level battery swap requests (pack count).
- Forecasting open-access renewable generation (solar and wind MWh availability).
- Forecasting IEX Day-Ahead Market clearing price distribution (INR/MWh).
- Providing point estimates (P50) and uncertainty bands (P10, P90).
- Chronological rolling-origin backtesting against seasonal-naive baselines.
"""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ForecasterProtocol(Protocol):
    """Protocol for probabilistic time series forecasters."""

    def train(self, historical_data: Any) -> None:
        """Train forecasting model using time-ordered historical data."""
        ...

    def predict(self, horizon_hours: int = 24) -> dict[str, Any]:
        """Generate rolling P10, P50, and P90 forecasts for the horizon."""
        ...
