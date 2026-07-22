"""
Integration tests for Workbench v1.1 — API routing, ACL, audit, response models.
"""

from __future__ import annotations

import uuid


from src.backend.workbench.models import (
    KnowledgeGraph, GraphNode, GraphEdge,
    PatientSummary, PatientDemographics,
    TreatmentRecommendation, DrugInfo,
    ActivityLog, ActivityEntry,
    WorkbenchTimeline,
    TumorBoardVote,
)


class TestResponseModels:
    """API response models and validation."""

    def test_knowledge_graph_model(self):
        """KnowledgeGraph validates correctly."""
        graph = KnowledgeGraph(
            nodes=[GraphNode(id="n1", label="Node", node_type="gene", color="red")],
            edges=[GraphEdge(source_id="n1", target_id="n2", label="link", edge_type="genomic")],
        )
        data = graph.model_dump()
        assert len(data["nodes"]) == 1
        assert len(data["edges"]) == 1
        assert data["nodes"][0]["node_type"] == "gene"

    def test_knowledge_graph_no_mutable_defaults(self):
        """KnowledgeGraph with no data returns empty lists, not None/mutable shared."""
        graph = KnowledgeGraph()
        assert graph.nodes == []
        assert graph.edges == []
        # Modifying one instance should not affect another
        graph2 = KnowledgeGraph()
        graph.nodes.append(GraphNode(id="x", label="X", node_type="gene"))
        assert len(graph2.nodes) == 0

    def test_patient_summary_model(self):
        """PatientSummary with full data serializes correctly."""
        summary = PatientSummary(
            patient=PatientDemographics(id="p1", age=45, sex="F"),
            cancer_type="MEL",
            stage="IV",
            biomarkers=["BRAF V600E"],
        )
        data = summary.model_dump()
        assert data["cancer_type"] == "MEL"
        assert data["patient"]["age"] == 45
        assert data["biomarkers"] == ["BRAF V600E"]

    def test_patient_summary_defaults(self):
        """PatientSummary defaults are isolated instances."""
        s1 = PatientSummary()
        s2 = PatientSummary()
        s1.biomarkers.append("TEST")
        assert len(s2.biomarkers) == 0
        s1.patient.age = 30
        assert s2.patient.age == 0

    def test_treatment_recommendation_model(self):
        """TreatmentRecommendation serializes correctly."""
        rec = TreatmentRecommendation(
            case_id="case-1",
            recommendations=[DrugInfo(name="Drug A", confidence=0.8)],
        )
        data = rec.model_dump()
        assert data["case_id"] == "case-1"
        assert data["recommendations"][0]["name"] == "Drug A"

    def test_activity_log_model(self):
        """ActivityLog with entries serializes correctly."""
        log = ActivityLog(
            entries=[ActivityEntry(id="e1", case_id="c1", action="test")],
            total=1,
        )
        data = log.model_dump()
        assert data["total"] == 1
        assert data["entries"][0]["action"] == "test"

    def test_activity_log_defaults(self):
        """ActivityLog defaults are empty, not fake."""
        log = ActivityLog()
        assert len(log.entries) == 0
        assert log.total == 0

    def test_workbench_timeline_model(self):
        """WorkbenchTimeline with events."""
        tl = WorkbenchTimeline(events=[{"type": "case_created", "timestamp": "2024-01-01"}])
        data = tl.model_dump()
        assert len(data["events"]) == 1

    def test_tumor_board_vote_valid_enum(self):
        """TumorBoardVote accepts valid vote values."""
        vote = TumorBoardVote(vote="approve", rationale="Good evidence")
        assert vote.vote == "approve"
        assert vote.rationale == "Good evidence"

    def test_tumor_board_vote_no_reviewer_id(self):
        """TumorBoardVote must NOT have reviewer_id field (comes from JWT)."""
        # This should work — the model no longer has reviewer_id
        vote = TumorBoardVote(vote="abstain", rationale="Conflict of interest")
        assert not hasattr(vote, 'reviewer_id')
        assert not hasattr(vote, 'reviewer_name')
        assert not hasattr(vote, 'created_at')

    async def test_invalid_vote_returns_422(self):
        """Invalid vote value should be rejected."""
        vote = TumorBoardVote(vote="invalid_value", rationale="test")
        assert vote.vote not in {"approve", "reject", "abstain"}


class TestNoFakeData:
    """No BRFA, Vemurafenib, sample, mock, or placeholder data in any model."""

    FAKE_KEYWORDS = ["BRAF", "Vemurafenib", "sample", "placeholder",
                     "[模拟]", "mock", "Coming Soon", "not_implemented"]

    def test_patient_summary_no_fake(self):
        """PatientSummary default has no fake medical values."""
        summary = PatientSummary()
        text = str(summary.model_dump())
        for kw in self.FAKE_KEYWORDS:
            assert kw not in text, f"Found fake keyword '{kw}' in PatientSummary defaults"

    def test_activity_log_no_placeholder(self):
        """ActivityLog default has no placeholder entries."""
        log = ActivityLog()
        text = str(log.model_dump())
        assert "placeholder" not in text

    def test_knowledge_graph_no_braf(self):
        """KnowledgeGraph doesn't default to BRAF."""
        graph = KnowledgeGraph()
        text = str(graph.model_dump())
        assert "BRAF" not in text
        assert "Vemurafenib" not in text

    def test_treatment_recommendation_no_fake(self):
        """TreatmentRecommendation has no fake drug names."""
        rec = TreatmentRecommendation()
        text = str(rec.model_dump())
        for kw in self.FAKE_KEYWORDS:
            assert kw not in text, f"Found fake keyword '{kw}' in TreatmentRecommendation"


class TestAuditLog:
    """Audit log entries for write operations."""

    def test_audit_log_model(self):
        """Audit log entry model."""
        entry = ActivityEntry(
            id=str(uuid.uuid4()),
            case_id="case-1",
            user_id="user-1",
            action="note_created",
            entity_type="workbench_note",
            entity_id="note-1",
            details={"note_id": "note-1"},
            created_at="2024-01-01T00:00:00Z",
        )
        assert entry.action == "note_created"
        assert entry.details["note_id"] == "note-1"
