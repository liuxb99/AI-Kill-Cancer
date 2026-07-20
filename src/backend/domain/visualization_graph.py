"""
Three.js Visualization Graph Contract.

Defines the shared JSON structure between backend and frontend for
interactive 3D graph visualization of variants, genes, proteins,
pathways, drugs, and evidence.

Node types, edge types, and their relationships are defined here
as the single source of truth.
"""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


# ─── Node Types ───────────────────────────────────────────────────────────────

NODE_TYPES = [
    "chromosome",
    "gene",
    "variant",
    "protein",
    "pathway",
    "drug",
    "evidence",
    "publication",
    "clinical_trial",
]

# ─── Edge Types ───────────────────────────────────────────────────────────────

EDGE_TYPES = [
    "located_on",
    "encodes",
    "affects",
    "activates",
    "inhibits",
    "participates_in",
    "targets",
    "supported_by",
    "conflicts_with",
    "studied_in",
    "approved_for",
    "off_label_for",
]

# ─── Node Status / Category values ────────────────────────────────────────────

NODE_STATUS_VALUES = [
    "active",
    "pending",
    "not_available",
    "not_applicable",
]

NODE_CATEGORY_VALUES = [
    "approved",
    "off_label",
    "clinical_trial",
    "preclinical",
    "hypothesis",
    "driver",
    "passenger",
    "vus",
    "oncogenic",
    "benign",
]


# ─── Pydantic Models ──────────────────────────────────────────────────────────


class GraphNode(BaseModel):
    """A node in the visualization graph."""

    id: str = Field(..., description="Unique node identifier")
    type: str = Field(..., description=f"Node type. One of: {NODE_TYPES}")
    label: str = Field(..., description="Display label")
    category: str = Field("unknown", description=f"Category. One of: {NODE_CATEGORY_VALUES}")
    status: str = Field("active", description=f"Status. One of: {NODE_STATUS_VALUES}")
    evidence_level: Optional[str] = Field(None, description="Highest evidence level for this node")
    metadata: dict = Field(default_factory=dict, description="Arbitrary metadata (VAF, coordinates, etc.)")


class GraphEdge(BaseModel):
    """An edge (relationship) in the visualization graph."""

    id: str = Field(..., description="Unique edge identifier")
    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    relation: str = Field(..., description=f"Relation type. One of: {EDGE_TYPES}")
    direction: str = Field("directed", description="Edge direction: 'directed' or 'undirected'")
    weight: float = Field(1.0, description="Edge weight / evidence strength (0.0–1.0)")
    evidence_ids: list[str] = Field(default_factory=list, description="Associated evidence IDs")
    provenance: dict = Field(default_factory=dict, description="Source provenance information")


class VisualizationGraph(BaseModel):
    """Complete graph payload for Three.js / react-force-graph."""

    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict, description="Graph-level metadata")


class GraphAnalysisResponse(BaseModel):
    """Response from the analysis graph endpoint."""

    analysis_id: str
    status: str  # "completed" | "pending" | "not_configured" | "adapter_unavailable"
    graph: VisualizationGraph = Field(default_factory=VisualizationGraph)
