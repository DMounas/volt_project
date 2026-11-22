"""Data Provenance Specifications for VOLT.

Defines the mandatory provenance classifications:
- OBSERVED: Verified source data from real-world operations or formal case facts.
- ASSUMED: Explicit, configurable engineering/modelling assumptions.
- SYNTHETIC: Algorithmically generated data for simulation and stress testing.
"""

from enum import Enum
from typing import Any, Generic, Optional, TypeVar
from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class Provenance(str, Enum):
    """Mandatory data provenance classification."""

    OBSERVED = "OBSERVED"
    ASSUMED = "ASSUMED"
    SYNTHETIC = "SYNTHETIC"

    @classmethod
    def from_str(cls, value: str) -> "Provenance":
        """Parse string to Provenance enum safely."""
        try:
            return cls(value.strip().upper())
        except (ValueError, KeyError, AttributeError):
            raise ValueError(
                f"Invalid provenance value: '{value}'. Expected one of: "
                f"{[p.value for p in cls]}"
            )


class ProvenanceTaggedValue(BaseModel, Generic[T]):
    """Wrapper that couples a data value with its provenance and audit metadata."""

    value: T
    unit: str
    provenance: Provenance
    source: Optional[str] = None
    rationale: Optional[str] = None
    model_config = ConfigDict(arbitrary_types_allowed=True)
