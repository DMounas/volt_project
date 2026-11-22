"""Health schema definitions."""

from datetime import datetime, timezone
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: str = Field(..., description="Service status ('ok' or 'degraded')")
    app_name: str = Field(..., description="Application name")
    version: str = Field(..., description="Application version")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Current UTC timestamp",
    )
    database: str = Field(..., description="Database connection status ('connected' or 'disconnected')")
    environment: str = Field(default="development", description="Runtime environment")
