"""VOLT Engine - Incentive Recommendation Policy.

Evaluates voluntary customer demand shift incentives against verifiable operational benefit proxies.
Enforces:
- Customer opt-in and feasible flexibility envelope preconditions
- Strict separation of customer retail tariff and separate cash/credit incentive expenditure
- Fallback to NOT_EVALUABLE if required cost inputs are missing (never fabricates positive business cases)
- Operational cost-benefit test (operational benefit must exceed incentive expenditure)
"""

from datetime import timedelta
from typing import Optional
import uuid

from engine.customer.models import (
    CustomerSegment,
    CustomerServiceRequest,
    FlexibilityEnvelope,
    FlexibilityReasonCode,
    IncentiveOffer,
    ServiceType,
    TariffRecommendation,
)
from engine.customer.response_model import CustomerResponseModel

DEFAULT_BASE_FC_INCENTIVE_INR_PER_KWH = 1.80
DEFAULT_BASE_SWAP_INCENTIVE_INR_PER_PACK = 25.00


class IncentiveRecommendationEngine:
    """Engine formulating voluntary customer flexibility offers evaluated against operational cost benefits."""

    def __init__(
        self,
        base_fc_incentive_inr_per_kwh: float = DEFAULT_BASE_FC_INCENTIVE_INR_PER_KWH,
        base_swap_incentive_inr_per_pack: float = DEFAULT_BASE_SWAP_INCENTIVE_INR_PER_PACK,
        response_model: Optional[CustomerResponseModel] = None,
    ):
        self.base_fc_incentive = base_fc_incentive_inr_per_kwh
        self.base_swap_incentive = base_swap_incentive_inr_per_pack
        self.response_model = response_model or CustomerResponseModel()

    def evaluate_offer(
        self,
        req: CustomerServiceRequest,
        envelope: FlexibilityEnvelope,
        tariff_rec: TariffRecommendation,
        forecast_procurement_peak_inr_per_kwh: Optional[float] = None,
        forecast_procurement_target_inr_per_kwh: Optional[float] = None,
        random_seed: Optional[int] = None,
    ) -> IncentiveOffer:
        """Formulate and evaluate a candidate flexibility incentive offer."""
        offer_id = f"OFFER-{uuid.uuid4().hex[:8].upper()}"
        expiration = req.arrival_ts + timedelta(minutes=15)

        # 1. Hard exclusion: Emergency and Priority Fleet
        if req.customer_segment in (CustomerSegment.EMERGENCY, CustomerSegment.PRIORITY_FLEET):
            reason = (
                FlexibilityReasonCode.EMERGENCY_NON_SHIFTABLE
                if req.customer_segment == CustomerSegment.EMERGENCY
                else FlexibilityReasonCode.PRIORITY_RESERVE_NON_SHIFTABLE
            )
            return IncentiveOffer(
                offer_id=offer_id,
                request_id=req.request_id,
                cluster_id=req.cluster_id,
                customer_segment=req.customer_segment,
                service_type=req.request_type,
                proposed_shift_kwh=0.0,
                proposed_shift_packs=0 if req.request_type == ServiceType.BATTERY_SWAP else None,
                proposed_slots=[],
                baseline_tariff_inr_per_kwh=req.baseline_tariff_inr_per_kwh,
                effective_tariff_inr_per_kwh=tariff_rec.final_tariff_inr_per_kwh,
                incentive_amount_inr=0.0,
                incentive_rate_inr_per_kwh=0.0,
                expected_acceptance_probability=0.0,
                expected_accepted_energy_kwh=0.0,
                expected_accepted_packs=0 if req.request_type == ServiceType.BATTERY_SWAP else None,
                estimated_incentive_cost_inr=0.0,
                estimated_operational_benefit_inr=0.0,
                net_expected_value_inr=0.0,
                evaluable=True,
                status="REJECTED_PROTECTED_SEGMENT",
                reason_codes=[reason],
                offer_expiration_ts=expiration,
            )

        # 2. Hard exclusion: Not opted in
        if not req.flexibility_opt_in:
            return IncentiveOffer(
                offer_id=offer_id,
                request_id=req.request_id,
                cluster_id=req.cluster_id,
                customer_segment=req.customer_segment,
                service_type=req.request_type,
                proposed_shift_kwh=0.0,
                proposed_shift_packs=0 if req.request_type == ServiceType.BATTERY_SWAP else None,
                proposed_slots=[],
                baseline_tariff_inr_per_kwh=req.baseline_tariff_inr_per_kwh,
                effective_tariff_inr_per_kwh=tariff_rec.final_tariff_inr_per_kwh,
                incentive_amount_inr=0.0,
                incentive_rate_inr_per_kwh=0.0,
                expected_acceptance_probability=0.0,
                expected_accepted_energy_kwh=0.0,
                expected_accepted_packs=0 if req.request_type == ServiceType.BATTERY_SWAP else None,
                estimated_incentive_cost_inr=0.0,
                estimated_operational_benefit_inr=0.0,
                net_expected_value_inr=0.0,
                evaluable=True,
                status="REJECTED_OPT_OUT",
                reason_codes=[FlexibilityReasonCode.NOT_OPTED_IN],
                offer_expiration_ts=expiration,
            )

        # 3. Hard exclusion: Zero flexible energy
        if envelope.flexible_energy_kwh <= 0.0 or not envelope.is_deferrable:
            return IncentiveOffer(
                offer_id=offer_id,
                request_id=req.request_id,
                cluster_id=req.cluster_id,
                customer_segment=req.customer_segment,
                service_type=req.request_type,
                proposed_shift_kwh=0.0,
                proposed_shift_packs=0 if req.request_type == ServiceType.BATTERY_SWAP else None,
                proposed_slots=[],
                baseline_tariff_inr_per_kwh=req.baseline_tariff_inr_per_kwh,
                effective_tariff_inr_per_kwh=tariff_rec.final_tariff_inr_per_kwh,
                incentive_amount_inr=0.0,
                incentive_rate_inr_per_kwh=0.0,
                expected_acceptance_probability=0.0,
                expected_accepted_energy_kwh=0.0,
                expected_accepted_packs=0 if req.request_type == ServiceType.BATTERY_SWAP else None,
                estimated_incentive_cost_inr=0.0,
                estimated_operational_benefit_inr=0.0,
                net_expected_value_inr=0.0,
                evaluable=True,
                status="DEADLINE_CONSTRAINED",
                reason_codes=[FlexibilityReasonCode.DEADLINE_CONSTRAINED],
                offer_expiration_ts=expiration,
            )

        # 4. Mandatory Fallback: NOT_EVALUABLE if required cost inputs are missing
        if (
            forecast_procurement_peak_inr_per_kwh is None
            or forecast_procurement_target_inr_per_kwh is None
        ):
            return IncentiveOffer(
                offer_id=offer_id,
                request_id=req.request_id,
                cluster_id=req.cluster_id,
                customer_segment=req.customer_segment,
                service_type=req.request_type,
                proposed_shift_kwh=envelope.flexible_energy_kwh,
                proposed_shift_packs=envelope.flexible_pack_count,
                proposed_slots=envelope.eligible_time_slots[1:] if len(envelope.eligible_time_slots) > 1 else envelope.eligible_time_slots,
                baseline_tariff_inr_per_kwh=req.baseline_tariff_inr_per_kwh,
                effective_tariff_inr_per_kwh=tariff_rec.final_tariff_inr_per_kwh,
                incentive_amount_inr=0.0,
                incentive_rate_inr_per_kwh=self.base_fc_incentive,
                expected_acceptance_probability=0.0,
                expected_accepted_energy_kwh=0.0,
                expected_accepted_packs=0 if envelope.flexible_pack_count is not None else None,
                estimated_incentive_cost_inr=0.0,
                estimated_operational_benefit_inr=None,
                net_expected_value_inr=None,
                evaluable=False,
                status="NOT_EVALUABLE",
                reason_codes=[FlexibilityReasonCode.NOT_EVALUABLE],
                offer_expiration_ts=expiration,
            )

        # 5. Financial Cost-Benefit Evaluation
        shift_kwh = envelope.flexible_energy_kwh
        shift_packs = envelope.flexible_pack_count

        if req.request_type == ServiceType.FAST_CHARGE:
            incentive_rate_per_kwh = self.base_fc_incentive
            total_incentive_inr = round(shift_kwh * incentive_rate_per_kwh, 2)
        else:
            pack_count = shift_packs or 1
            total_incentive_inr = round(pack_count * self.base_swap_incentive, 2)
            incentive_rate_per_kwh = round(total_incentive_inr / max(0.1, shift_kwh), 2)

        # Operational benefit proxy: avoided peak procurement cost differential
        procurement_spread = forecast_procurement_peak_inr_per_kwh - forecast_procurement_target_inr_per_kwh
        operational_benefit_inr = round(max(0.0, shift_kwh * procurement_spread), 2)

        # Evaluate response model
        response = self.response_model.evaluate_acceptance(
            req=req,
            envelope=envelope,
            incentive_rate_inr_per_kwh=incentive_rate_per_kwh,
            notice_hours=1.0,
            random_seed=random_seed,
        )

        p = response.acceptance_probability
        expected_kwh = response.expected_accepted_energy_kwh
        expected_packs = response.expected_accepted_packs
        expected_cost_inr = round(p * total_incentive_inr, 2)
        expected_benefit_inr = round(p * operational_benefit_inr, 2)
        net_ev_inr = round(expected_benefit_inr - expected_cost_inr, 2)

        # Reason code and status determination
        reasons = [envelope.reason_code]
        if expected_benefit_inr < expected_cost_inr or p < 0.05:
            status = "INSUFFICIENT_BENEFIT"
            reasons.append(FlexibilityReasonCode.INSUFFICIENT_BENEFIT)
        else:
            status = "RECOMMENDED"

        proposed_slots = envelope.eligible_time_slots[1:] if len(envelope.eligible_time_slots) > 1 else envelope.eligible_time_slots

        return IncentiveOffer(
            offer_id=offer_id,
            request_id=req.request_id,
            cluster_id=req.cluster_id,
            customer_segment=req.customer_segment,
            service_type=req.request_type,
            proposed_shift_kwh=shift_kwh,
            proposed_shift_packs=shift_packs,
            proposed_slots=proposed_slots,
            baseline_tariff_inr_per_kwh=req.baseline_tariff_inr_per_kwh,
            effective_tariff_inr_per_kwh=tariff_rec.final_tariff_inr_per_kwh,
            incentive_amount_inr=total_incentive_inr,
            incentive_rate_inr_per_kwh=incentive_rate_per_kwh,
            expected_acceptance_probability=p,
            expected_accepted_energy_kwh=expected_kwh,
            expected_accepted_packs=int(round(expected_packs)) if expected_packs is not None else None,
            stochastic_realized_acceptance=response.stochastic_accepted,
            realized_accepted_energy_kwh=response.realized_accepted_energy_kwh,
            estimated_incentive_cost_inr=expected_cost_inr,
            estimated_operational_benefit_inr=expected_benefit_inr,
            net_expected_value_inr=net_ev_inr,
            evaluable=True,
            status=status,
            reason_codes=reasons,
            offer_expiration_ts=expiration,
        )
