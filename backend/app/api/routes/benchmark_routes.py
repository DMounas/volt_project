"""FastAPI endpoints for Phase 7 Benchmarks, Ablations, and Metric Registry.

Provides auditable statistical evaluations, metric definitions, and downloads.
"""

import json
import os
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from engine.metrics.registry import METRIC_REGISTRY, MetricsRegistryService, PolicySemantics
from engine.provenance import Provenance

benchmark_router = APIRouter(prefix="/benchmarks", tags=["benchmarks"])


class MetricDefinitionSchema(BaseModel):
    key: str
    name: str
    unit: str
    formula: str
    numerator: str
    denominator: str
    boundary: str
    target_value: Optional[float]
    interpretation: str


class MetricRegistryResponse(BaseModel):
    metrics: list[MetricDefinitionSchema]
    policies: list[str]
    ebitda_missing_data: list[str]
    provenance: str = Provenance.ASSUMED.value


@benchmark_router.get("/metrics/registry", response_model=MetricRegistryResponse)
def get_metrics_registry() -> MetricRegistryResponse:
    """Return the canonical metric registry and comparison semantics."""
    defs = [
        MetricDefinitionSchema(
            key=m.key,
            name=m.name,
            unit=m.unit,
            formula=m.formula,
            numerator=m.numerator,
            denominator=m.denominator,
            boundary=m.boundary,
            target_value=m.target_value,
            interpretation=m.interpretation,
        )
        for m in METRIC_REGISTRY.values()
    ]
    policies = [p.value for p in PolicySemantics]
    return MetricRegistryResponse(
        metrics=defs,
        policies=policies,
        ebitda_missing_data=MetricsRegistryService.get_ebitda_missing_data_list(),
    )


@benchmark_router.get("/summary")
def get_benchmark_summary() -> dict[str, Any]:
    """Retrieve aggregate benchmark statistics across fixed seeds and scenarios."""
    summary_path = Path("reports/benchmark_results/benchmark_summary.json")
    if not summary_path.exists():
        # Fallback default statistics structure if benchmark hasn't been run
        return {
            "status": "NOT_RUN",
            "message": "Run python scripts/run_final_benchmarks.py to generate full results",
            "provenance": Provenance.SYNTHETIC.value,
        }
    with open(summary_path, "r", encoding="utf-8") as f:
        return json.load(f)


@benchmark_router.get("/ablations")
def get_ablations_and_sensitivities() -> dict[str, Any]:
    """Retrieve ablation study and parameter sensitivity results."""
    abl_path = Path("reports/benchmark_results/ablations.json")
    sens_path = Path("reports/benchmark_results/sensitivities.json")

    abl_data = {}
    sens_data = {}
    if abl_path.exists():
        with open(abl_path, "r", encoding="utf-8") as f:
            abl_data = json.load(f)
    if sens_path.exists():
        with open(sens_path, "r", encoding="utf-8") as f:
            sens_data = json.load(f)

    return {
        "ablations": abl_data,
        "sensitivities": sens_data,
        "ebitda_status": "NOT_EVALUABLE",
        "provenance": Provenance.SYNTHETIC.value,
    }


@benchmark_router.get("/raw")
def get_raw_benchmark_runs() -> list[dict[str, Any]]:
    """Retrieve all raw benchmark run records."""
    raw_path = Path("reports/benchmark_results/raw_runs.json")
    if not raw_path.exists():
        return []
    with open(raw_path, "r", encoding="utf-8") as f:
        return json.load(f)


@benchmark_router.get("/download/csv")
def download_benchmark_csv():
    """Download raw benchmark run dataset as CSV."""
    csv_path = Path("reports/benchmark_results/raw_runs.csv")
    if not csv_path.exists():
        raise HTTPException(status_code=404, detail="Benchmark CSV not found. Run scripts/run_final_benchmarks.py first.")
    return FileResponse(
        path=csv_path,
        media_type="text/csv",
        filename="volt_final_benchmark_results.csv",
    )
