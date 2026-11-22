"""API routes for IEX market data adapter diagnostics."""

from fastapi import APIRouter, HTTPException, Query
from backend.app.schemas.baseline_schemas import IEXDiagnosticsResponse
from backend.app.services.data_service import data_service

router = APIRouter(prefix="/data/iex", tags=["IEX Adapter"])


@router.get("/diagnostics", response_model=IEXDiagnosticsResponse)
def get_iex_adapter_diagnostics(
    sample_records: int = Query(4000, ge=100, le=20000, description="15-minute sample records to audit"),
) -> IEXDiagnosticsResponse:
    """Audit 15-minute IEX DAM blocks and return hourly aggregation diagnostics."""
    try:
        return data_service.get_iex_diagnostics(sample_records=sample_records)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to run IEX diagnostics: {str(e)}")
