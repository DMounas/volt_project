"""VOLT Engine - Dynamic Tariff Policy (Phase 4 Reference Policy).

Implements the case study regulatory guardrail:
tariff_min = 0.80 * previous_day_average_tariff
tariff_max = 1.20 * previous_day_average_tariff
final_tariff = clip(raw_tariff, tariff_min, tariff_max)

Strictly uses only forecast information available at the decision timestamp.
Decouples retail billing tariff from separate flexibility incentive payments.
"""

from datetime import datetime
from typing import Optional

from engine.customer.models import (
    ServiceType,
    TariffRecommendation,
)

BENCHMARK_PROCUREMENT_COST_INR_PER_KWH = 5.20


class DynamicTariffPolicy:
    """Reference dynamic tariff policy strictly enforcing 80%-120% regulatory boundary."""

    def __init__(
        self,
        lower_bound_multiplier: float = 0.80,
        upper_bound_multiplier: float = 1.20,
    ):
        if lower_bound_multiplier <= 0.0 or upper_bound_multiplier <= lower_bound_multiplier:
            raise ValueError("Invalid tariff bound multipliers")
        self.lower_multiplier = lower_bound_multiplier
        self.upper_multiplier = upper_bound_multiplier

    def evaluate_tariff(
        self,
        cluster_id: str,
        service_type: ServiceType,
        timestamp: datetime,
        previous_day_average_tariff_inr_per_kwh: float,
        forecast_procurement_cost_inr_per_kwh: Optional[float] = None,
        forecast_demand_mw: Optional[float] = None,
        available_capacity_mw: Optional[float] = None,
        forecast_solar_surplus_mw: Optional[float] = None,
    ) -> TariffRecommendation:
        """Evaluate raw tariff recommendation and strictly enforce regulatory clipping."""
        # 1. Validation of reference inputs
        if previous_day_average_tariff_inr_per_kwh <= 0.0:
            raise ValueError(
                f"previous_day_average_tariff_inr_per_kwh must be positive, got {previous_day_average_tariff_inr_per_kwh}"
            )
        if forecast_procurement_cost_inr_per_kwh is not None and forecast_procurement_cost_inr_per_kwh < 0.0:
            raise ValueError("forecast_procurement_cost_inr_per_kwh cannot be negative")
        if forecast_demand_mw is not None and forecast_demand_mw < 0.0:
            raise ValueError("forecast_demand_mw cannot be negative")
        if available_capacity_mw is not None and available_capacity_mw <= 0.0:
            raise ValueError("available_capacity_mw must be positive")

        tariff_min = round(self.lower_multiplier * previous_day_average_tariff_inr_per_kwh, 2)
        tariff_max = round(self.upper_multiplier * previous_day_average_tariff_inr_per_kwh, 2)

        raw_tariff = previous_day_average_tariff_inr_per_kwh
        reasons = []
        factors: dict[str, float] = {
            "previous_day_average": previous_day_average_tariff_inr_per_kwh,
            "tariff_min": tariff_min,
            "tariff_max": tariff_max,
        }

        # 2. Wholesale procurement adjustment
        if forecast_procurement_cost_inr_per_kwh is not None:
            factors["forecast_procurement_cost"] = forecast_procurement_cost_inr_per_kwh
            procurement_delta = forecast_procurement_cost_inr_per_kwh - BENCHMARK_PROCUREMENT_COST_INR_PER_KWH
            if abs(procurement_delta) > 0.20:
                cost_adjustment = 0.50 * procurement_delta
                raw_tariff += cost_adjustment
                direction = "higher" if procurement_delta > 0 else "lower"
                reasons.append(
                    f"Procurement cost forecast ({forecast_procurement_cost_inr_per_kwh:.2f} INR/kWh) is {direction} "
                    f"than benchmark ({BENCHMARK_PROCUREMENT_COST_INR_PER_KWH:.2f}), adjusting raw tariff by {cost_adjustment:+.2f} INR/kWh."
                )

        # 3. Grid queue & capacity congestion adjustment
        if forecast_demand_mw is not None and available_capacity_mw is not None:
            utilization = forecast_demand_mw / available_capacity_mw
            factors["utilization_ratio"] = round(utilization, 3)
            if utilization > 0.85:
                congestion_adj = previous_day_average_tariff_inr_per_kwh * 0.15
                raw_tariff += congestion_adj
                reasons.append(
                    f"High forecast cluster utilization ({utilization*100:.1f}%), adding congestion adder of +{congestion_adj:.2f} INR/kWh."
                )
            elif utilization < 0.40:
                offpeak_discount = previous_day_average_tariff_inr_per_kwh * 0.10
                raw_tariff -= offpeak_discount
                reasons.append(
                    f"Low forecast cluster utilization ({utilization*100:.1f}%), applying off-peak discount of -{offpeak_discount:.2f} INR/kWh."
                )

        # 4. Solar surplus adjustment
        if forecast_solar_surplus_mw is not None and forecast_solar_surplus_mw > 5.0:
            factors["solar_surplus_mw"] = forecast_solar_surplus_mw
            solar_discount = 1.00
            raw_tariff -= solar_discount
            reasons.append(
                f"Local solar generation surplus ({forecast_solar_surplus_mw:.1f} MW), granting green discount of -{solar_discount:.2f} INR/kWh."
            )

        raw_tariff = round(raw_tariff, 2)
        factors["raw_tariff"] = raw_tariff

        # 5. Regulatory Clipping to [0.80x, 1.20x]
        if raw_tariff > tariff_max:
            final_tariff = tariff_max
            clamped = True
            direction = "UPPER_BOUND"
            reasons.append(
                f"Raw tariff ({raw_tariff:.2f} INR/kWh) exceeded regulatory ceiling (1.20x = {tariff_max:.2f} INR/kWh); clamped to ceiling."
            )
        elif raw_tariff < tariff_min:
            final_tariff = tariff_min
            clamped = True
            direction = "LOWER_BOUND"
            reasons.append(
                f"Raw tariff ({raw_tariff:.2f} INR/kWh) fell below regulatory floor (0.80x = {tariff_min:.2f} INR/kWh); clamped to floor."
            )
        else:
            final_tariff = raw_tariff
            clamped = False
            direction = "NONE"
            reasons.append("Tariff lies within regulatory [0.80x, 1.20x] band; no clamping required.")

        return TariffRecommendation(
            cluster_id=cluster_id,
            service_type=service_type,
            timestamp=timestamp,
            previous_day_average_tariff_inr_per_kwh=previous_day_average_tariff_inr_per_kwh,
            tariff_min_inr_per_kwh=tariff_min,
            tariff_max_inr_per_kwh=tariff_max,
            raw_tariff_inr_per_kwh=raw_tariff,
            final_tariff_inr_per_kwh=final_tariff,
            clamped=clamped,
            clamping_direction=direction,
            pricing_factors=factors,
            adjustment_reasons=reasons,
            provenance="ASSUMED_POLICY",
        )
