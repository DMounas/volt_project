"""API route modules."""

from backend.app.api.routes.adapter_routes import router as iex_router
from backend.app.api.routes.baseline_routes import router as baseline_router
from backend.app.api.routes.case import router as case_router
from backend.app.api.routes.clusters import router as clusters_router
from backend.app.api.routes.customer_routes import (
    customer_router,
    flexibility_router,
    incentive_router,
    tariff_router,
)
from backend.app.api.routes.data_routes import router as data_router
from backend.app.api.routes.forecast_routes import router as forecast_router
from backend.app.api.routes.health import router as health_router
from backend.app.api.routes.optimization_routes import router as optimization_router
from backend.app.api.routes.scenarios import router as scenarios_router

__all__ = [
    "health_router",
    "case_router",
    "clusters_router",
    "scenarios_router",
    "data_router",
    "iex_router",
    "baseline_router",
    "forecast_router",
    "customer_router",
    "flexibility_router",
    "tariff_router",
    "incentive_router",
    "optimization_router",
]
