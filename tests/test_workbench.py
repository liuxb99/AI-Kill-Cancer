"""
Tests for Doctor Workbench (v0.9.0).
"""

from __future__ import annotations

import uuid

from src.backend.workbench.models import (
    GraphNode, GraphEdge, KnowledgeGraph,
    TumorBoardReview, WorkbenchNote, WorkbenchTimeline,
    CaseComparisonResult,
)
from src.backend.workbench.service import WorkbenchService
from src.backend.workbench.repository import (
    TumorBoardRepository,
)


class TestWorkbenchModels:
    def test_graph_node(self):
        node = GraphNode(id="gene-braf", label="BRAF", node_type="gene", color="#4CAF50")
        assert node.id == "gene-braf"
        assert node.node_type == "gene"

    def test_graph_edge(self):
        edge = GraphEdge(source_id="gene-braf", target_id="var-1", label="has_variant")
        assert edge.source_id == "gene-braf"

    def test_knowledge_graph(self):
        graph = KnowledgeGraph(
            nodes=[GraphNode(id="n1", label="Node 1", node_type="gene")],
            edges=[GraphEdge(source_id="n1", target_id="n2", label="edge")],
        )
        assert len(graph.nodes) == 1
        assert len(graph.edges) == 1

    def test_tumor_board_review(self):
        review = TumorBoardReview(
            id="r1", case_id="case-1", reviewer_id="dr-smith",
            decision="approve", comment="Approved based on evidence",
        )
        assert review.decision == "approve"
        assert review.reviewer_id == "dr-smith"

    def test_workbench_note(self):
        note = WorkbenchNote(case_id="case-1", content="Test note")
        assert note.note_type == "general"

    def test_workbench_timeline(self):
        timeline = WorkbenchTimeline(events=[{"type": "test", "description": "Test event"}])
        assert len(timeline.events) == 1

    def test_case_comparison_result(self):
        result = CaseComparisonResult(
            comparison_type="case",
            case_ids=["case-1", "case-2"],
        )
        assert len(result.case_ids) == 2


class TestKnowledgeGraph:
    def test_build_variant_graph(self):
        from tests.test_knowledge_layer import FakeKnowledgeDB
        db = FakeKnowledgeDB()
        service = WorkbenchService(db)

        import asyncio
        graph = asyncio.run(service.build_knowledge_graph(variant_id="test-var-1"))

        assert len(graph.nodes) >= 3  # gene + variant + at least 1 drug
        assert len(graph.edges) >= 1
        assert any(n.node_type == "gene" for n in graph.nodes)
        assert any(n.node_type == "variant" for n in graph.nodes)
        assert any(n.node_type == "drug" for n in graph.nodes)

    def test_build_case_graph(self):
        from tests.test_knowledge_layer import FakeKnowledgeDB
        db = FakeKnowledgeDB()
        service = WorkbenchService(db)

        import asyncio
        graph = asyncio.run(service.build_knowledge_graph(case_id="test-case"))

        assert len(graph.nodes) >= 1


class TestTumorBoardRepository:
    """Test Tumor Board repository with mock DB."""

    async def test_create_review(self):
        from tests.test_knowledge_layer import FakeKnowledgeDB
        db = FakeKnowledgeDB()
        repo = TumorBoardRepository(db)

        review = await repo.create_review(case_id="case-1", reviewer_id="dr-smith")
        assert review.case_id == "case-1"
        assert review.status == "draft"

    async def test_update_status(self):
        from tests.test_knowledge_layer import FakeKnowledgeDB
        db = FakeKnowledgeDB()
        repo = TumorBoardRepository(db)

        # Create and immediately try to update (mock won't persist)
        await repo.create_review(case_id="case-1")
        # Since mock doesn't actually persist, update will return None
        result = await repo.update_status(uuid.uuid4(), "approved", "approve")
        assert result is None  # Mock DB doesn't store


class TestWorkbenchService:
    async def test_get_case_timeline(self):
        from tests.test_knowledge_layer import FakeKnowledgeDB
        db = FakeKnowledgeDB()
        service = WorkbenchService(db)

        timeline = await service.get_case_timeline("case-1")
        assert len(timeline.events) >= 1

    async def test_compare_cases(self):
        from tests.test_knowledge_layer import FakeKnowledgeDB
        db = FakeKnowledgeDB()
        service = WorkbenchService(db)

        result = await service.compare_cases(["case-1", "case-2"])
        assert len(result.case_ids) == 2
        assert result.comparison_type == "case"
