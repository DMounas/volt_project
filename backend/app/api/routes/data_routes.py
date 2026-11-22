"""API routes for synthetic dataset manifest, summaries, and time series."""

from fastapi import APIRouter, HTTPException, Query
from backend.app.schemas.data_schemas import DataManifestResponse, DataSummaryResponse, HourlyDataResponse
from backend.app.services.data_service import data_service

router = APIRouter(prefix="/data", tags=["Data Foundation"])


@router.get("/manifest", response_model=DataManifestResponse)
def get_data_manifest() -> DataManifestResponse:
    """Return the master synthetic dataset manifest, checksums, and provenance."""
    try:
        return data_service.get_manifest()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load data manifest: {str(e)}")


@router.get("/summary", response_model=DataSummaryResponse)
def get_data_summary() -> DataSummaryResponse:
    """Return summary aggregated statistics across all five clusters."""
    try:
        return data_service.get_data_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load data summary: {str(e)}")


@router.get("/hourly", response_model=HourlyDataResponse)
def get_hourly_data(
    cluster_id: str = Query(..., description="Cluster slug (e.g., 'delhi_ncr')"),
    limit: int = Query(168, ge=1, le=720, description="Number of hourly records to return"),
    offset: int = Query(0, ge=0, description="Offset index into hourly series"),
) -> HourlyDataResponse:
    """Return paginated hourly observations for a cluster."""
    try:
        return data_service.get_hourly_timeseries(cluster_id=cluster_id, limit=limit, offset=offset)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load hourly data: {str(e)}")
