"""
Pydantic models for the Doctor Workbench (v1.1).
"""

from __future__ import annotations


from pydantic import BaseModel


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


class TumorBoardVote(BaseModel):
    """A vote on a tumor board review."""
    reviewer_id: str = ""
    reviewer_name: str = ""
    vote: str = ""  # approve, reject, abstain
    rationale: str = ""
    created_at: str = ""


class TumorBoardDetail(BaseModel):
    """Full tumor board review with votes and comments."""
    id: str = ""
    case_id: str = ""
    status: str = "draft"
    reviews: list[TumorBoardReview] = []
    votes: list[TumorBoardVote] = []
    summary: str = ""
    final_recommendation: str = ""
    created_at: str = ""
    updated_at: str = ""


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


class ActivityEntry(BaseModel):
    """A single activity log entry."""
    id: str = ""
    case_id: str = ""
    user_id: str = ""
    action: str = ""
    entity_type: str = ""
    entity_id: str = ""
    details: dict = {}
    created_at: str = ""


class ActivityLog(BaseModel):
    """Activity log response."""
    entries: list[ActivityEntry] = []
    total: int = 0


class PatientDemographics(BaseModel):
    """Patient demographics summary."""
    id: str = ""
    mrn: str = ""
    age: int = 0
    sex: str = ""
    race: str = ""
    ethnicity: str = ""


class PatientSummary(BaseModel):
    """Consolidated patient summary for the workbench."""
    patient: PatientDemographics = PatientDemographics()
    diagnosis: str = ""
    stage: str = ""
    cancer_type: str = ""
    histology: str = ""
    biomarkers: list[str] = []
    treatment_history: list[dict] = []
    current_medications: list[dict] = []
    case_status: str = ""
    case_priority: str = ""
    case_owner: str = ""
    alerts: list[dict] = []


class DrugInfo(BaseModel):
    """Drug information in a treatment recommendation."""
    name: str = ""
    drugbank_id: str = ""
    mechanism: str = ""
    status: str = ""  # approved, experimental, off_label
    level: str = ""
    match_level: str = ""
    confidence: float = 0.0


class TreatmentRecommendation(BaseModel):
    """Treatment recommendation for a case."""
    case_id: str = ""
    recommendations: list[DrugInfo] = []
    alternatives: list[DrugInfo] = []
    contraindications: list[DrugInfo] = []
    evidence_summary: str = ""
    generated_at: str = ""


class CaseComparisonResult(BaseModel):
    """Result of comparing two or more cases."""
    comparison_type: str = ""
    case_ids: list[str] = []
    shared_variants: list[dict] = []
    unique_variants: dict = {}
    shared_evidence: list[dict] = []
    ranking_differences: list[dict] = []
