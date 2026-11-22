"""API route modules."""

from backend.app.api.routes.case import router as case_router
from backend.app.api.routes.clusters import router as clusters_router
from backend.app.api.routes.health import router as health_router
from backend.app.api.routes.scenarios import router as scenarios_router

__all__ = [
    "health_router",
    "case_router",
    "clusters_router",
    "scenarios_router",
]
