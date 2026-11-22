"""VOLT Engine - Customer Flexibility Module.

Responsibilities:
- Customer request representation (arrival, deadline, required energy, priority class).
- Priority classification: Emergency, Priority Fleet, Commercial Logistics, Retail Flexible.
- Feasible flexibility envelopes and non-deferrable service bounds.
- Incentive response curves and opt-in demand shift modelling.
- Enforcement of customer tariff bounds [0.80x to 1.20x previous-day average].
"""

from typing import Any, Protocol, runtime_checkable

from engine.customer.envelope import FlexibilityEnvelopeEngine
from engine.customer.incentives import IncentiveRecommendationEngine
from engine.customer.models import (
    CustomerSegment,
    CustomerServiceRequest,
    FlexibilityEnvelope,
    FlexibilityReasonCode,
    IncentiveOffer,
    ServiceType,
    TariffRecommendation,
)
from engine.customer.response_model import (
    CustomerResponseModel,
    CustomerResponseResult,
    LogisticAcceptanceConfig,
)
from engine.customer.scenarios import (
    CustomerScenarioEvaluator,
    ScenarioEvaluationResult,
)
from engine.customer.synthetic_requests import SyntheticRequestDisaggregator
from engine.customer.tariffs import DynamicTariffPolicy


@runtime_checkable
class CustomerFlexibilityProtocol(Protocol):
    """Protocol for customer demand flexibility and incentive response."""

    def evaluate_flexibility(self, request: dict[str, Any]) -> dict[str, Any]:
        """Compute permissible shifting window and associated incentive requirements."""
        ...


__all__ = [
    "CustomerFlexibilityProtocol",
    "CustomerSegment",
    "ServiceType",
    "FlexibilityReasonCode",
    "CustomerServiceRequest",
    "FlexibilityEnvelope",
    "TariffRecommendation",
    "IncentiveOffer",
    "FlexibilityEnvelopeEngine",
    "DynamicTariffPolicy",
    "CustomerResponseModel",
    "CustomerResponseResult",
    "LogisticAcceptanceConfig",
    "IncentiveRecommendationEngine",
    "SyntheticRequestDisaggregator",
    "CustomerScenarioEvaluator",
    "ScenarioEvaluationResult",
]
