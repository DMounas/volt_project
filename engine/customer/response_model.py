"""VOLT Engine - Customer Acceptance & Response Model.

Implements a bounded logistic customer acceptance model:
p_accept = sigmoid(beta_0 + beta_1 * incentive_signal + beta_2 * notice_hours + beta_3 * slack_hours + segment_effect)

Strictly enforces:
- Zero acceptance for EMERGENCY, PRIORITY_FLEET, and non-opted-in requests
- Bounded probabilities in [0.0, 1.0]
- Deterministic expected acceptance and seeded stochastic Monte Carlo realizations
- Provenance tagged as ASSUMED (not trained on actual driver telemetry)
"""

from dataclasses import dataclass
import math
from typing import Optional
import numpy as np

from engine.customer.models import (
    CustomerSegment,
    CustomerServiceRequest,
    FlexibilityEnvelope,
)

DEFAULT_SEGMENT_EFFECTS = {
    CustomerSegment.EMERGENCY: -999.0,
    CustomerSegment.PRIORITY_FLEET: -999.0,
    CustomerSegment.RIDE_HAILING: 0.00,
    CustomerSegment.LOGISTICS_FLEET: 0.50,
    CustomerSegment.PRIVATE_EV: -0.20,
}


@dataclass
class LogisticAcceptanceConfig:
    """Configurable coefficients for customer acceptance logistic curve."""
    beta_0: float = -1.50   # Baseline intercept
    beta_1: float = 0.80    # Incentive elasticity per INR/kWh
    beta_2: float = 0.30    # Notice time sensitivity (per advance hour)
    beta_3: float = 0.40    # Available schedule slack sensitivity (per hour)
    segment_effects: Optional[dict[CustomerSegment, float]] = None


@dataclass
class CustomerResponseResult:
    """Evaluation result of customer acceptance model."""
    request_id: str
    acceptance_probability: float
    stochastic_accepted: bool
    linear_score: float
    expected_accepted_energy_kwh: float
    realized_accepted_energy_kwh: float
    expected_accepted_packs: Optional[float]
    realized_accepted_packs: Optional[int]
    provenance: str = "ASSUMED"


class CustomerResponseModel:
    """Bounded logistic response model for customer demand flexibility offers."""

    def __init__(self, config: Optional[LogisticAcceptanceConfig] = None):
        self.config = config or LogisticAcceptanceConfig()
        self.segment_effects = self.config.segment_effects or DEFAULT_SEGMENT_EFFECTS

    @staticmethod
    def _sigmoid(x: float) -> float:
        """Numerically stable sigmoid function."""
        if x >= 40.0:
            return 1.0
        if x <= -40.0:
            return 0.0
        return 1.0 / (1.0 + math.exp(-x))

    def evaluate_acceptance(
        self,
        req: CustomerServiceRequest,
        envelope: FlexibilityEnvelope,
        incentive_rate_inr_per_kwh: float,
        notice_hours: float = 1.0,
        random_seed: Optional[int] = None,
    ) -> CustomerResponseResult:
        """Evaluate customer acceptance probability and realized stochastic acceptance."""
        # 1. Hard exclusions: Emergency, Priority Fleet, and non-opted-in customers
        if (
            req.customer_segment in (CustomerSegment.EMERGENCY, CustomerSegment.PRIORITY_FLEET)
            or not req.flexibility_opt_in
            or not envelope.is_deferrable
            or envelope.flexible_energy_kwh <= 0.0
        ):
            return CustomerResponseResult(
                request_id=req.request_id,
                acceptance_probability=0.0,
                stochastic_accepted=False,
                linear_score=-999.0,
                expected_accepted_energy_kwh=0.0,
                realized_accepted_energy_kwh=0.0,
                expected_accepted_packs=0.0 if envelope.flexible_pack_count is not None else None,
                realized_accepted_packs=0 if envelope.flexible_pack_count is not None else None,
                provenance="ASSUMED",
            )

        # 2. Slack hours
        slack_hours = envelope.max_deferral_minutes / 60.0
        segment_effect = self.segment_effects.get(req.customer_segment, 0.0)

        # 3. Linear combination
        linear_score = (
            self.config.beta_0
            + self.config.beta_1 * max(0.0, incentive_rate_inr_per_kwh)
            + self.config.beta_2 * max(0.0, notice_hours)
            + self.config.beta_3 * max(0.0, slack_hours)
            + segment_effect
        )

        prob = self._sigmoid(linear_score)
        prob = float(np.clip(prob, 0.0, 1.0))

        # 4. Stochastic simulation trial
        if random_seed is not None:
            rng = np.random.default_rng(random_seed)
            stochastic_accepted = bool(rng.uniform(0.0, 1.0) < prob)
        else:
            stochastic_accepted = bool(prob >= 0.50)

        # 5. Energy and pack quantities
        expected_kwh = round(prob * envelope.flexible_energy_kwh, 3)
        realized_kwh = envelope.flexible_energy_kwh if stochastic_accepted else 0.0

        if envelope.flexible_pack_count is not None:
            expected_packs = round(prob * envelope.flexible_pack_count, 2)
            realized_packs = envelope.flexible_pack_count if stochastic_accepted else 0
        else:
            expected_packs = None
            realized_packs = None

        return CustomerResponseResult(
            request_id=req.request_id,
            acceptance_probability=round(prob, 4),
            stochastic_accepted=stochastic_accepted,
            linear_score=round(linear_score, 4),
            expected_accepted_energy_kwh=expected_kwh,
            realized_accepted_energy_kwh=realized_kwh,
            expected_accepted_packs=expected_packs,
            realized_accepted_packs=realized_packs,
            provenance="ASSUMED",
        )
