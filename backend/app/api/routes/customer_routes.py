"""VOLT Backend - Customer Flexibility, Dynamic Tariff & Incentive API Routes."""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query

from backend.app.schemas.customer_schemas import (
    CustomerRequestsSummaryResponse,
    CustomerSegmentsResponse,
    FlexibilityEnvelopesResponse,
    FlexibilityEvaluateRequest,
    FlexibilityScenariosResponse,
    FlexibilitySummaryResponse,
    IncentivesSummaryResponse,
    TariffRecommendRequest,
)
from backend.app.services.customer_service import customer_service
from engine.customer.models import (
    CustomerSegment,
    ServiceType,
    TariffRecommendation,
)

# 1. Customer endpoints
customer_router = APIRouter(prefix="/customers", tags=["Customer Intelligence"])

# 2. Flexibility endpoints
flexibility_router = APIRouter(prefix="/flexibility", tags=["Demand Flexibility"])

# 3. Tariff endpoints
tariff_router = APIRouter(prefix="/tariffs", tags=["Dynamic Tariffs"])

# 4. Incentive endpoints
incentive_router = APIRouter(prefix="/incentives", tags=["Customer Incentives"])


# ---------------------------------------------------------------------------
# Customer Routes
# ---------------------------------------------------------------------------
@customer_router.get("/segments", response_model=CustomerSegmentsResponse)
def get_customer_segments():
    """Return all customer classification segments with behavioural assumptions and provenance."""
    segments = customer_service.get_customer_segments()
    return CustomerSegmentsResponse(
        total_segments=len(segments),
        segments=segments,
        provenance="ASSUMED",
    )


@customer_router.get("/requests/summary", response_model=CustomerRequestsSummaryResponse)
def get_requests_summary():
    """Return synthetic customer session counts, energy demand, and reconciliation status."""
    try:
        data = customer_service.get_requests_summary()
        return CustomerRequestsSummaryResponse(**data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate requests summary: {str(e)}")


# ---------------------------------------------------------------------------
# Flexibility Routes
# ---------------------------------------------------------------------------
@flexibility_router.get("/summary", response_model=FlexibilitySummaryResponse)
def get_flexibility_summary(cluster_id: Optional[str] = Query(None, description="Optional metro cluster filter")):
    """Return network or cluster demand flexibility summary."""
    try:
        data = customer_service.get_flexibility_summary(cluster_id=cluster_id)
        return FlexibilitySummaryResponse(**data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to evaluate flexibility summary: {str(e)}")


@flexibility_router.get("/envelopes", response_model=FlexibilityEnvelopesResponse)
def get_flexibility_envelopes(
    cluster_id: Optional[str] = Query(None, description="Metro cluster filter"),
    modality: Optional[ServiceType] = Query(None, description="FAST_CHARGE or BATTERY_SWAP"),
    segment: Optional[CustomerSegment] = Query(None, description="Customer classification segment"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=500, description="Pagination limit"),
):
    """Query and paginate individual customer flexibility envelopes with reason codes."""
    try:
        data = customer_service.get_envelopes(
            cluster_id=cluster_id,
            modality=modality,
            segment=segment,
            offset=offset,
            limit=limit,
        )
        return FlexibilityEnvelopesResponse(**data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve envelopes: {str(e)}")


@flexibility_router.post("/evaluate")
def evaluate_flexibility(payload: FlexibilityEvaluateRequest):
    """Evaluate a customer scenario returning flexibility envelopes, demand decomposition, and offers."""
    try:
        res = customer_service.evaluate_flexibility_scenario(
            scenario_id=payload.scenario_id,
            target_cluster=payload.cluster_id,
            seed_override=payload.seed,
        )
        return {
            "scenario_id": res.scenario_id,
            "scenario_name": res.scenario_name,
            "description": res.description,
            "seed": res.seed,
            "total_requests": res.total_requests,
            "total_demand_kwh": res.total_demand_kwh,
            "non_shiftable_demand_kwh": res.non_shiftable_demand_kwh,
            "eligible_flexible_demand_kwh": res.eligible_flexible_demand_kwh,
            "opted_in_demand_kwh": res.opted_in_demand_kwh,
            "expected_accepted_demand_kwh": res.expected_accepted_demand_kwh,
            "realized_accepted_demand_kwh": res.realized_accepted_demand_kwh,
            "deadline_violations": res.deadline_violations,
            "protected_priority_requests": res.protected_priority_requests,
            "protected_priority_demand_kwh": res.protected_priority_demand_kwh,
            "total_retail_revenue_inr": res.total_retail_revenue_inr,
            "total_incentive_cost_inr": res.total_incentive_cost_inr,
            "average_wait_minutes": res.average_wait_minutes,
            "average_effective_tariff_inr_per_kwh": res.average_effective_tariff_inr_per_kwh,
            "cluster_metrics": res.cluster_metrics,
            "modality_metrics": res.modality_metrics,
            "segment_metrics": res.segment_metrics,
            "sample_envelopes": res.sample_envelopes,
            "sample_offers": res.sample_offers,
            "provenance": res.provenance,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to evaluate scenario: {str(e)}")


@flexibility_router.get("/scenarios", response_model=FlexibilityScenariosResponse)
def get_flexibility_scenarios():
    """Return catalog of configured customer flexibility and sensitivity scenarios."""
    catalog = customer_service.get_flexibility_scenarios_catalog()
    return FlexibilityScenariosResponse(
        total_scenarios=len(catalog),
        scenarios=catalog,
        provenance="SYNTHETIC",
    )


# ---------------------------------------------------------------------------
# Tariff Routes
# ---------------------------------------------------------------------------
@tariff_router.post("/recommend", response_model=TariffRecommendation)
def recommend_tariff(payload: TariffRecommendRequest):
    """Evaluate dynamic retail tariff recommendation bounded strictly by [0.80x, 1.20x] previous day average."""
    try:
        rec = customer_service.recommend_tariff(
            cluster_id=payload.cluster_id,
            service_type=payload.service_type,
            timestamp=payload.timestamp,
            previous_day_average_tariff_inr_per_kwh=payload.previous_day_average_tariff_inr_per_kwh,
            forecast_procurement_cost_inr_per_kwh=payload.forecast_procurement_cost_inr_per_kwh,
            forecast_demand_mw=payload.forecast_demand_mw,
            available_capacity_mw=payload.available_capacity_mw,
            forecast_solar_surplus_mw=payload.forecast_solar_surplus_mw,
        )
        return rec
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to compute tariff recommendation: {str(e)}")


# ---------------------------------------------------------------------------
# Incentive Routes
# ---------------------------------------------------------------------------
@incentive_router.get("/summary", response_model=IncentivesSummaryResponse)
def get_incentives_summary():
    """Return overview of voluntary flexibility incentives across scenarios."""
    try:
        summary_items = customer_service.get_incentives_summary()
        return IncentivesSummaryResponse(
            scenarios=summary_items,
            provenance="ASSUMED_SIMULATION",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to compute incentives summary: {str(e)}")
