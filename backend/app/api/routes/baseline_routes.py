"""API routes for baseline policy calibration and simulation audits."""

from fastapi import APIRouter, HTTPException, Query
from backend.app.schemas.baseline_schemas import BaselineCalibrationResponse, BaselineSimulationResponse
from backend.app.services.data_service import data_service

router = APIRouter(prefix="/baseline", tags=["Baseline Policy"])


@router.get("/calibration", response_model=BaselineCalibrationResponse)
def get_baseline_calibration() -> BaselineCalibrationResponse:
    """Return the baseline policy calibration report and residuals against 78% reliability and 10% losses."""
    try:
        return data_service.get_baseline_calibration()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load baseline calibration: {str(e)}")


@router.get("/simulation", response_model=BaselineSimulationResponse)
def get_baseline_simulation(
    sample_hours: int = Query(168, ge=24, le=720, description="Hours per cluster to simulate and reconcile"),
) -> BaselineSimulationResponse:
    """Run baseline policy simulation and return energy reconciliation audit report."""
    try:
        return data_service.get_baseline_simulation(sample_hours=sample_hours)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to run baseline simulation: {str(e)}")
