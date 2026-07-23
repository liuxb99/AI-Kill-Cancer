
"""
Integration test for workbench flows.
"""
from src.backend.workbench.models import (
    CaseComparisonResult,
    GraphEdge,
    GraphNode,
    KnowledgeGraph,
    TumorBoardReview,
)


class TestWorkbenchAPIFlow:
    def test_knowledge_graph_structure(self):
        graph = KnowledgeGraph(
            nodes=[GraphNode(id="g1", label="BRAF", node_type="gene")],
            edges=[GraphEdge(source_id="g1", target_id="v1", label="has_variant")],
        )
        assert len(graph.nodes) == 1
        assert len(graph.edges) == 1

    def test_tumor_board_review_flow(self):
        review = TumorBoardReview(
            id="r1", case_id="c1", reviewer_id="dr-s",
            decision="approve", comment="OK",
        )
        assert review.decision == "approve"

    def test_case_comparison(self):
        result = CaseComparisonResult(
            comparison_type="case",
            case_ids=["c1", "c2"],
            shared_variants=[{"gene": "BRAF"}],
        )
        assert len(result.case_ids) == 2

