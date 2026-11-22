"""Scenarios endpoint."""

from fastapi import APIRouter, HTTPException
from backend.app.schemas.scenario import ScenariosResponse
from backend.app.services.config_service import config_service

router = APIRouter(tags=["Scenarios"])


@router.get("/scenarios", response_model=ScenariosResponse)
def get_scenarios() -> ScenariosResponse:
    """Return configured operational disturbance scenario metadata."""
    try:
        return config_service.get_scenarios()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load scenarios: {str(e)}")
