"""Cluster schemas."""

from typing import Optional
from pydantic import BaseModel, Field
from engine.provenance import Provenance


class ClusterInfo(BaseModel):
    """Cluster representation distinguishing observed facts from assumed parameters."""

    cluster_id: str = Field(..., description="Unique slug identifier (e.g., 'delhi_ncr')")
    name: str = Field(..., description="Display cluster name (e.g., 'Delhi NCR')")
    provenance: Provenance = Field(
        Provenance.OBSERVED, description="Provenance of cluster presence (OBSERVED in case study)"
    )
    installed_capacity_share_assumed: float = Field(
        0.20, description="Assumed capacity share fraction (e.g., 0.20 for equal 20% baseline)"
    )
    installed_capacity_mw_assumed: float = Field(
        240.0, description="Assumed allocated capacity in MW (e.g. 240 MW baseline)"
    )
    capacity_provenance: Provenance = Field(
        Provenance.ASSUMED,
        description="Provenance of capacity allocation (ASSUMED, unsupplied in case facts)",
    )
    grid_import_limit_mw_assumed: float = Field(
        240.0, description="Assumed grid import limit in MW"
    )
    status: str = Field("active", description="Operational status")


class ClustersResponse(BaseModel):
    """Response containing the five metro clusters."""

    total_clusters: int = Field(5, description="Total count of clusters")
    clusters: list[ClusterInfo] = Field(..., description="List of configured clusters")
    provenance: Provenance = Field(
        Provenance.OBSERVED, description="Cluster list provenance (OBSERVED)"
    )
    note: str = Field(
        "Cluster names are observed case study facts. Individual city capacity splits and grid limits are ASSUMED and configurable.",
        description="Clarification of provenance boundary",
    )
