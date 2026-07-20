"""
Pydantic models for the Doctor Workbench.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class GraphNode(BaseModel):
    """A node in the knowledge graph visualization."""
    id: str = ""
    label: str = ""
    node_type: str = ""  # gene, variant, disease, drug, evidence, publication, trial, guideline
    color: str = ""
    size: int = 1
    metadata: dict = {}


class GraphEdge(BaseModel):
    """An edge in the knowledge graph visualization."""
    source_id: str = ""
    target_id: str = ""
    label: str = ""
    edge_type: str = ""


class KnowledgeGraph(BaseModel):
    """A complete knowledge graph for visualization."""
    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []


class TumorBoardReview(BaseModel):
    """A tumor board review entry."""
    id: str = ""
    case_id: str = ""
    reviewer_id: str = ""
    reviewer_name: str = ""
    comment: str = ""
    decision: str = ""  # approve, reject, needs_info
    evidence_override: dict = {}
    override_reason: str = ""
    created_at: str = ""


class WorkbenchNote(BaseModel):
    """A workbench note or comment."""
    id: str = ""
    case_id: str = ""
    user_id: str = ""
    content: str = ""
    note_type: str = "general"  # general, decision, override, flag
    created_at: str = ""


class WorkbenchTimeline(BaseModel):
    """Timeline of events for a case."""
    events: list[dict] = []


class CaseComparisonResult(BaseModel):
    """Result of comparing two or more cases."""
    comparison_type: str = ""
    case_ids: list[str] = []
    shared_variants: list[dict] = []
    unique_variants: dict = {}
    shared_evidence: list[dict] = []
    ranking_differences: list[dict] = []
