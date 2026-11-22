"""VOLT Engine - Data Module.

Responsibilities:
- Ingestion of raw historical files (weather, demand, swap logs, IEX prices, renewables, battery SOH).
- Adapter for IEX 15-minute market blocks to hourly aggregated representations.
- Data validation and assignment of provenance labels (OBSERVED, ASSUMED, SYNTHETIC).
- Feature engineering pipeline for downstream forecasting and digital twin models.
"""

from typing import Any, Protocol, runtime_checkable
from engine.provenance import Provenance


@runtime_checkable
class DataLoaderProtocol(Protocol):
    """Protocol for dataset loaders with provenance enforcement."""

    def load_dataset(self, source_path: str) -> Any:
        """Load and return dataset."""
        ...

    def get_provenance(self) -> Provenance:
        """Return the provenance class of the dataset."""
        ...
