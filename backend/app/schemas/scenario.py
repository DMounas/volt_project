"""Scenario schemas."""

from typing import Optional
from pydantic import BaseModel, Field
from engine.provenance import Provenance


class ScenarioMetadata(BaseModel):
    """Scenario disturbance specification and metadata."""

    scenario_id: str = Field(..., description="Unique scenario identifier (e.g. 'NORMAL')")
    name: str = Field(..., description="Human-readable scenario name")
    description: str = Field(..., description="Operational disturbance narrative")
    demand_multiplier: float = Field(..., description="Fast-charging demand scaling factor")
    renewable_multiplier: float = Field(..., description="Renewable availability scaling factor")
    iex_price_multiplier: float = Field(..., description="IEX market clearing price multiplier")
    swap_demand_multiplier: float = Field(..., description="Battery swap request multiplier")
    initial_pack_ready_fraction: float = Field(..., description="Starting ready pack fraction")
    initial_bess_soc: float = Field(..., description="Starting stationary BESS SOC")
    probability_weight: float = Field(..., description="A priori scenario probability weight")
    seed: int = Field(..., description="Deterministic seed for simulation replication")
    status: str = Field("configured", description="Configuration state")
    provenance: Provenance = Field(
        Provenance.SYNTHETIC, description="Provenance classification for disturbance scenario"
    )


class ScenariosResponse(BaseModel):
    """Response containing configured scenario metadata."""

    total_scenarios: int = Field(..., description="Number of configured scenarios")
    scenarios: list[ScenarioMetadata] = Field(..., description="List of scenario metadata")
    provenance: Provenance = Field(
        Provenance.SYNTHETIC,
        description="Scenario definitions provenance (SYNTHETIC/ASSUMED for stress testing)",
    )
    note: str = Field(
        "Scenario metadata only. No simulation results or performance claims are made at Phase 1.",
        description="Methodological boundary notice",
    )
