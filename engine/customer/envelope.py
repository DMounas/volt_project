"""VOLT Engine - Flexibility Envelope Engine.

Converts individual customer service requests into feasible flexibility envelopes.
Enforces non-shiftable emergency & priority reserves, customer opt-in requirements,
hard departure deadlines, and integer discrete pack constraints for battery swapping.
"""

from datetime import datetime, timedelta
import math
from typing import Optional

from engine.customer.models import (
    CustomerSegment,
    CustomerServiceRequest,
    FlexibilityEnvelope,
    FlexibilityReasonCode,
    ServiceType,
)

# Segment-level default assumptions (configurable via assumptions.yaml)
DEFAULT_FLEXIBLE_FRACTIONS = {
    CustomerSegment.EMERGENCY: 0.0,
    CustomerSegment.PRIORITY_FLEET: 0.0,
    CustomerSegment.RIDE_HAILING: 0.40,
    CustomerSegment.LOGISTICS_FLEET: 0.70,
    CustomerSegment.PRIVATE_EV: 0.50,
}

NOMINAL_CHARGER_POWER_KW = 50.0  # Standard DC Fast Charger rate


class FlexibilityEnvelopeEngine:
    """Deterministic engine evaluating customer request service feasibility and flexibility envelopes."""

    def __init__(
        self,
        flexible_fractions: Optional[dict[CustomerSegment, float]] = None,
        charger_power_kw: float = NOMINAL_CHARGER_POWER_KW,
    ):
        self.flexible_fractions = flexible_fractions or DEFAULT_FLEXIBLE_FRACTIONS
        self.charger_power_kw = charger_power_kw

    def compute_envelope(self, req: CustomerServiceRequest) -> FlexibilityEnvelope:
        """Compute the flexibility envelope for a customer service request."""
        arrival_slot = req.arrival_ts.strftime("%Y-%m-%dT%H:00:00+05:30")

        # 1. Physical duration & deadline slack
        if req.request_type == ServiceType.FAST_CHARGE:
            normal_duration_minutes = (req.requested_energy_kwh / self.charger_power_kw) * 60.0
        else:
            # Battery swap turnaround is instantaneous mechanically (approx 5 mins)
            normal_duration_minutes = 5.0

        earliest_start = req.arrival_ts
        earliest_normal_finish = earliest_start + timedelta(minutes=normal_duration_minutes)
        slack_minutes = max(0.0, (req.departure_deadline_ts - earliest_normal_finish).total_seconds() / 60.0)

        # Generate hourly eligible time slots
        eligible_slots = self._generate_eligible_slots(req.arrival_ts, req.departure_deadline_ts)

        # 2. Hard Rule 1: EMERGENCY requests are strictly non-shiftable
        if req.customer_segment == CustomerSegment.EMERGENCY:
            return self._build_non_shiftable_envelope(
                req=req,
                reason=FlexibilityReasonCode.EMERGENCY_NON_SHIFTABLE,
                eligible_slots=[arrival_slot],
                service_risk=0.0,
            )

        # 3. Hard Rule 2: PRIORITY_FLEET requests are strictly protected under 5% reserve
        if req.customer_segment == CustomerSegment.PRIORITY_FLEET:
            return self._build_non_shiftable_envelope(
                req=req,
                reason=FlexibilityReasonCode.PRIORITY_RESERVE_NON_SHIFTABLE,
                eligible_slots=[arrival_slot],
                service_risk=0.0,
            )

        # 4. Hard Rule 3: Customer must have explicitly opted in
        if not req.flexibility_opt_in:
            return self._build_non_shiftable_envelope(
                req=req,
                reason=FlexibilityReasonCode.NOT_OPTED_IN,
                eligible_slots=[arrival_slot],
                service_risk=0.0,
            )

        # 5. Hard Rule 4: Must have positive available slack beyond normal service duration
        max_feasible_deferral = min(req.max_deferral_minutes, slack_minutes)
        if max_feasible_deferral <= 0.0 or len(eligible_slots) <= 1:
            return self._build_non_shiftable_envelope(
                req=req,
                reason=FlexibilityReasonCode.DEADLINE_CONSTRAINED,
                eligible_slots=[arrival_slot],
                service_risk=0.4,
            )

        # 6. Modality-specific flexibility calculation
        if req.request_type == ServiceType.FAST_CHARGE:
            return self._evaluate_fast_charge(
                req=req,
                max_feasible_deferral=max_feasible_deferral,
                eligible_slots=eligible_slots,
                slack_minutes=slack_minutes,
            )
        else:
            return self._evaluate_battery_swap(
                req=req,
                max_feasible_deferral=max_feasible_deferral,
                eligible_slots=eligible_slots,
                slack_minutes=slack_minutes,
            )

    def _evaluate_fast_charge(
        self,
        req: CustomerServiceRequest,
        max_feasible_deferral: float,
        eligible_slots: list[str],
        slack_minutes: float,
    ) -> FlexibilityEnvelope:
        """Evaluate fast-charging flexible energy portion."""
        segment_frac = self.flexible_fractions.get(req.customer_segment, 0.40)
        
        # Upper bound on flexible energy respects minimum service requirement
        max_possible_flex = max(0.0, req.requested_energy_kwh - req.minimum_service_energy_kwh)
        tentative_flex = req.requested_energy_kwh * segment_frac
        flexible_kwh = round(min(tentative_flex, max_possible_flex), 3)
        non_shiftable_kwh = round(req.requested_energy_kwh - flexible_kwh, 3)

        if flexible_kwh <= 0.0:
            return self._build_non_shiftable_envelope(
                req=req,
                reason=FlexibilityReasonCode.DEADLINE_CONSTRAINED,
                eligible_slots=[eligible_slots[0]],
                service_risk=0.3,
            )

        reason = (
            FlexibilityReasonCode.FLEXIBLE_WITHIN_WINDOW
            if non_shiftable_kwh <= 0.0
            else FlexibilityReasonCode.PARTIALLY_FLEXIBLE
        )

        risk_score = min(1.0, max(0.0, 1.0 - (slack_minutes / max(30.0, req.max_deferral_minutes))))

        return FlexibilityEnvelope(
            request_id=req.request_id,
            cluster_id=req.cluster_id,
            request_type=req.request_type,
            customer_segment=req.customer_segment,
            arrival_ts=req.arrival_ts,
            earliest_start_ts=req.arrival_ts,
            deadline_ts=req.departure_deadline_ts,
            requested_energy_kwh=req.requested_energy_kwh,
            minimum_service_energy_kwh=req.minimum_service_energy_kwh,
            non_shiftable_energy_kwh=non_shiftable_kwh,
            flexible_energy_kwh=flexible_kwh,
            eligible_time_slots=eligible_slots,
            max_deferral_minutes=max_feasible_deferral,
            flexibility_opt_in=True,
            is_deferrable=True,
            reason_code=reason,
            service_risk_score=round(risk_score, 2),
            provenance="SYNTHETIC",
            assumption_reference="configs/assumptions.yaml:customer_flexibility",
        )

    def _evaluate_battery_swap(
        self,
        req: CustomerServiceRequest,
        max_feasible_deferral: float,
        eligible_slots: list[str],
        slack_minutes: float,
    ) -> FlexibilityEnvelope:
        """Evaluate battery-swap discrete pack flexibility (strictly discrete integer packs)."""
        segment_frac = self.flexible_fractions.get(req.customer_segment, 0.40)
        total_packs = req.requested_pack_count
        pack_cap = req.pack_capacity_kwh

        max_flex_packs = max(0, total_packs - req.minimum_pack_count)
        
        # Discrete pack logic
        if total_packs == 1:
            # Single pack: flexible if minimum_pack_count == 0 and segment_frac >= 0.50
            flex_packs = 1 if (max_flex_packs >= 1 and segment_frac >= 0.50) else 0
        else:
            tentative_flex = int(math.floor(total_packs * segment_frac))
            flex_packs = min(max_flex_packs, tentative_flex)

        non_shift_packs = total_packs - flex_packs
        flexible_kwh = round(flex_packs * pack_cap, 3)
        non_shift_kwh = round(non_shift_packs * pack_cap, 3)

        if flex_packs <= 0:
            return self._build_non_shiftable_envelope(
                req=req,
                reason=FlexibilityReasonCode.DEADLINE_CONSTRAINED,
                eligible_slots=[eligible_slots[0]],
                service_risk=0.2,
            )

        reason = (
            FlexibilityReasonCode.FLEXIBLE_WITHIN_WINDOW
            if non_shift_packs == 0
            else FlexibilityReasonCode.PARTIALLY_FLEXIBLE
        )

        risk_score = min(1.0, max(0.0, 1.0 - (slack_minutes / max(30.0, req.max_deferral_minutes))))

        return FlexibilityEnvelope(
            request_id=req.request_id,
            cluster_id=req.cluster_id,
            request_type=req.request_type,
            customer_segment=req.customer_segment,
            arrival_ts=req.arrival_ts,
            earliest_start_ts=req.arrival_ts,
            deadline_ts=req.departure_deadline_ts,
            requested_energy_kwh=round(total_packs * pack_cap, 3),
            minimum_service_energy_kwh=round(req.minimum_pack_count * pack_cap, 3),
            non_shiftable_energy_kwh=non_shift_kwh,
            flexible_energy_kwh=flexible_kwh,
            requested_pack_count=total_packs,
            minimum_pack_count=req.minimum_pack_count,
            non_shiftable_pack_count=non_shift_packs,
            flexible_pack_count=flex_packs,
            pack_capacity_kwh=pack_cap,
            eligible_time_slots=eligible_slots,
            max_deferral_minutes=max_feasible_deferral,
            flexibility_opt_in=True,
            is_deferrable=True,
            reason_code=reason,
            service_risk_score=round(risk_score, 2),
            provenance="SYNTHETIC",
            assumption_reference="configs/assumptions.yaml:customer_flexibility",
        )

    def _build_non_shiftable_envelope(
        self,
        req: CustomerServiceRequest,
        reason: FlexibilityReasonCode,
        eligible_slots: list[str],
        service_risk: float = 0.0,
    ) -> FlexibilityEnvelope:
        """Construct non-shiftable envelope conserving requested energy and packs."""
        if req.request_type == ServiceType.FAST_CHARGE:
            req_kwh = req.requested_energy_kwh
            min_kwh = req.minimum_service_energy_kwh
            req_packs = None
            min_packs = None
            pack_cap = None
        else:
            req_packs = req.requested_pack_count
            min_packs = req.minimum_pack_count
            pack_cap = req.pack_capacity_kwh
            req_kwh = round(req_packs * pack_cap, 3)
            min_kwh = round(min_packs * pack_cap, 3)

        return FlexibilityEnvelope(
            request_id=req.request_id,
            cluster_id=req.cluster_id,
            request_type=req.request_type,
            customer_segment=req.customer_segment,
            arrival_ts=req.arrival_ts,
            earliest_start_ts=req.arrival_ts,
            deadline_ts=req.departure_deadline_ts,
            requested_energy_kwh=req_kwh,
            minimum_service_energy_kwh=min_kwh,
            non_shiftable_energy_kwh=req_kwh,
            flexible_energy_kwh=0.0,
            requested_pack_count=req_packs,
            minimum_pack_count=min_packs,
            non_shiftable_pack_count=req_packs,
            flexible_pack_count=0 if req_packs is not None else None,
            pack_capacity_kwh=pack_cap,
            eligible_time_slots=eligible_slots,
            max_deferral_minutes=0.0,
            flexibility_opt_in=req.flexibility_opt_in,
            is_deferrable=False,
            reason_code=reason,
            service_risk_score=service_risk,
            provenance="SYNTHETIC",
            assumption_reference="configs/assumptions.yaml:customer_flexibility",
        )

    def _generate_eligible_slots(self, arrival: datetime, deadline: datetime) -> list[str]:
        """Generate ISO timestamps for hourly slots spanning from arrival up to deadline."""
        start_hour = arrival.replace(minute=0, second=0, microsecond=0)
        end_hour = deadline.replace(minute=0, second=0, microsecond=0)
        
        slots = []
        curr = start_hour
        while curr <= end_hour:
            slots.append(curr.strftime("%Y-%m-%dT%H:00:00+05:30"))
            curr += timedelta(hours=1)
        
        return slots or [arrival.strftime("%Y-%m-%dT%H:00:00+05:30")]
