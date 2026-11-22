"""FastAPI routes for Phase 3 Probabilistic Quantile Forecasting."""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from backend.app.schemas.forecast_schemas import (
    ForecastMetricsResponse,
    ForecastResponse,
    ForecastRunRequest,
    ForecastSummaryResponse,
)
from backend.app.services.forecast_service import forecast_service

router = APIRouter(prefix="/forecasts", tags=["Forecasting"])


@router.get("/summary", response_model=ForecastSummaryResponse)
def get_forecast_summary() -> ForecastSummaryResponse:
    """Return forecasting model inventory, supported targets, and date ranges."""
    try:
        return forecast_service.get_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch forecast summary: {str(e)}")


@router.get("/latest", response_model=ForecastResponse)
def get_latest_forecast(
    cluster_id: str = Query("delhi_ncr", description="Cluster ID (delhi_ncr, mumbai_mmr, etc.)"),
    target_name: str = Query("fast_charge_demand_mwh", description="Target variable name"),
) -> ForecastResponse:
    """Fetch the latest rolling 24-hour P10, P50, and P90 forecast for the target and cluster."""
    try:
        return forecast_service.get_latest_forecast(cluster_id=cluster_id, target_name=target_name)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate latest forecast: {str(e)}")


@router.post("/run", response_model=ForecastResponse)
def run_forecast(request: ForecastRunRequest) -> ForecastResponse:
    """Execute rolling 24-hour probabilistic forecast from a validated origin timestamp."""
    try:
        return forecast_service.run_forecast(
            origin_timestamp=request.origin_timestamp,
            cluster_id=request.cluster_id,
            target_name=request.target_name,
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Forecast execution failed: {str(e)}")


@router.get("/metrics", response_model=ForecastMetricsResponse)
def get_forecast_metrics(
    target_name: Optional[str] = Query(None, description="Optional target filter"),
    cluster_id: Optional[str] = Query(None, description="Optional cluster filter"),
) -> ForecastMetricsResponse:
    """Return chronological backtest metrics on untouched 2025 test dataset."""
    try:
        return forecast_service.get_metrics(target_name=target_name, cluster_id=cluster_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch forecast metrics: {str(e)}")
