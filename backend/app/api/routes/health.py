"""Health check endpoint."""

from datetime import datetime, timezone
import os
from fastapi import APIRouter
from backend.app.db.session import check_db_connection
from backend.app.schemas.health import HealthResponse

router = APIRouter(tags=["System"])


@router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    """Return service health status, application version, and database connectivity."""
    db_ok = check_db_connection()
    return HealthResponse(
        status="ok",
        app_name=os.getenv("APP_NAME", "VOLT — Virtual Orchestration of Load, Tariffs & Energy"),
        version=os.getenv("APP_VERSION", "0.1.0"),
        timestamp=datetime.now(timezone.utc),
        database="connected" if db_ok else "disconnected",
        environment=os.getenv("APP_ENV", "development"),
    )
