"""Case configuration endpoint."""

from fastapi import APIRouter, HTTPException
from backend.app.schemas.case_config import CaseConfigResponse
from backend.app.services.config_service import config_service

router = APIRouter(prefix="/config", tags=["Configuration"])


@router.get("/case", response_model=CaseConfigResponse)
def get_case_configuration() -> CaseConfigResponse:
    """Return the source-provided case configuration with explicit provenance tags."""
    try:
        return config_service.get_case_config()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load case configuration: {str(e)}")
