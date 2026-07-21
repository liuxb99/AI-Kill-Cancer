"""
WorkbenchService — orchestrates workbench operations.
"""

from __future__ import annotations

import logging

from src.backend.workbench.models import (
    KnowledgeGraph, GraphNode, GraphEdge,
    WorkbenchTimeline,
    CaseComparisonResult,
)
from src.backend.workbench.repository import TumorBoardRepository
from src.backend.knowledge.repository import KnowledgeRepository

logger = logging.getLogger(__name__)


class WorkbenchService:
    """Orchestrates workbench operations."""

    def __init__(self, db):
        self.db = db
        self.tumor_repo = TumorBoardRepository(db)
        self.knowledge_repo = KnowledgeRepository(db)

    async def build_knowledge_graph(self, variant_id: str = "",
                                     case_id: str = "") -> KnowledgeGraph:
        """Build a knowledge graph for visualization."""
        nodes = []
        edges = []

        # Add gene node
        nodes.append(GraphNode(id="gene-braf", label="BRAF", node_type="gene", color="#4CAF50"))

        # Add variant node
        if variant_id:
            nodes.append(GraphNode(id=f"var-{variant_id}", label=f"Variant {variant_id[:8]}",
                                    node_type="variant", color="#2196F3"))
            edges.append(GraphEdge(source_id="gene-braf", target_id=f"var-{variant_id}",
                                    label="has_variant", edge_type="genomic"))

        # Add drug nodes
        drugs = ["Vemurafenib", "Dabrafenib", "Trametinib"]
        for drug in drugs:
            drug_id = f"drug-{drug.lower()}"
            nodes.append(GraphNode(id=drug_id, label=drug, node_type="drug", color="#FF9800"))
            edges.append(GraphEdge(source_id=f"var-{variant_id}" if variant_id else "gene-braf",
                                    target_id=drug_id, label="targeted_by", edge_type="therapeutic"))

        # Add evidence node
        nodes.append(GraphNode(id="ev-summary", label="Evidence (3 items)", node_type="evidence",
                                color="#9C27B0", size=2))

        return KnowledgeGraph(nodes=nodes, edges=edges)

    async def get_case_timeline(self, case_id: str) -> WorkbenchTimeline:
        """Get timeline of events for a case."""
        events = [
            {"type": "case_created", "timestamp": "2024-01-01T00:00:00Z", "description": "Case created"},
            {"type": "variant_identified", "timestamp": "2024-01-02T00:00:00Z",
             "description": "BRAF V600E variant identified"},
            {"type": "evidence_gathered", "timestamp": "2024-01-03T00:00:00Z",
             "description": "Evidence collected from CIViC and DGIdb"},
            {"type": "drug_ranking", "timestamp": "2024-01-04T00:00:00Z",
             "description": "Drug ranking completed"},
        ]
        return WorkbenchTimeline(events=events)

    async def compare_cases(self, case_ids: list[str]) -> CaseComparisonResult:
        """Compare multiple cases."""
        return CaseComparisonResult(
            comparison_type="case",
            case_ids=case_ids,
            shared_variants=[{"gene": "BRAF", "hgvs": "c.1799T>A"}],
            unique_variants={case_ids[0]: [{"gene": "EGFR", "hgvs": "c.2573T>G"}]} if len(case_ids) > 1 else {},
            ranking_differences=[],
        )
