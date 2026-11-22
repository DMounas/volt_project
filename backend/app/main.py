"""VOLT - Virtual Orchestration of Load, Tariffs & Energy.

FastAPI Application Entrypoint.
Provides the decision-support digital twin API boundary.
"""

import json
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.routes import (
    baseline_router,
    case_router,
    clusters_router,
    data_router,
    forecast_router,
    health_router,
    iex_router,
    scenarios_router,
)

app_name = os.getenv("APP_NAME", "VOLT — Virtual Orchestration of Load, Tariffs & Energy")
app_version = os.getenv("APP_VERSION", "0.1.0")

app = FastAPI(
    title=app_name,
    version=app_version,
    description=(
        "Decision-support digital twin API for a five-city Indian EV fast-charging and "
        "battery-swapping network. Jointly schedules procurement, storage dispatch, "
        "customer tariffs, and reserves."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
)

# Parse CORS origins
cors_origins_env = os.getenv("CORS_ORIGINS", '["http://localhost:5173", "http://127.0.0.1:5173"]')
try:
    origins = json.loads(cors_origins_env)
    if not isinstance(origins, list):
        origins = ["*"]
except Exception:
    origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API v1 routes
api_v1_prefix = "/api/v1"
app.include_router(health_router, prefix=api_v1_prefix)
app.include_router(case_router, prefix=api_v1_prefix)
app.include_router(clusters_router, prefix=api_v1_prefix)
app.include_router(scenarios_router, prefix=api_v1_prefix)
app.include_router(data_router, prefix=api_v1_prefix)
app.include_router(iex_router, prefix=api_v1_prefix)
app.include_router(baseline_router, prefix=api_v1_prefix)
app.include_router(forecast_router, prefix=api_v1_prefix)


@app.get("/", tags=["Root"])
def root_status():
    """Root endpoint with basic platform metadata."""
    return {
        "platform": "VOLT",
        "description": "Virtual Orchestration of Load, Tariffs & Energy",
        "version": app_version,
        "docs": "/docs",
        "api_v1": api_v1_prefix,
        "type": "decision-support prototype / digital twin",
    }
