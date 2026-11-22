"""Clusters endpoint."""

from fastapi import APIRouter, HTTPException
from backend.app.schemas.cluster import ClustersResponse
from backend.app.services.config_service import config_service

router = APIRouter(tags=["Clusters"])


@router.get("/clusters", response_model=ClustersResponse)
def get_clusters() -> ClustersResponse:
    """Return the five configured metro clusters."""
    try:
        return config_service.get_clusters()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load clusters: {str(e)}")
