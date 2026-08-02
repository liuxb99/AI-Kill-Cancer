"""Objective readiness checks for the complete PTC research product.

The gate does not call external services. It inspects persisted data and the
complete graph snapshot so operators can distinguish "code exists" from a
usable demonstration or research dataset.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.services.ptc_completion_service import PTCCompletionService
from src.backend.services.ptc_knowgraph_export import PTCKnowGraphExportService

DEMO_THRESHOLDS = {
    "cases": 1,
    "variants": 1,
    "therapies": 1,
    "evidence": 1,
    "clinical_trials": 1,
}

RESEARCH_THRESHOLDS = {
    "cases": 100,
    "variants": 100,
    "therapies": 5,
    "evidence": 50,
    "clinical_trials": 20,
}


class PTCReadinessService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def evaluate(self) -> dict[str, Any]:
        completion = PTCCompletionService(self.db)
        status = await completion.source_status()
        graph = await completion.full_graph(case_limit=5000)
        graph_data = await PTCKnowGraphExportService(self.db).export(case_limit=5000)

        node_ids = {node["id"] for node in graph["nodes"]}
        dangling_edges = [
            edge["id"]
            for edge in graph["edges"]
            if edge["source"] not in node_ids or edge["target"] not in node_ids
        ]
        graph_integrity = not dangling_edges
        export_counts_match = (
            graph_data["metadata"]["entity_count"] == len(graph_data["entities"])
            and graph_data["metadata"]["relation_count"] == len(graph_data["relations"])
        )
        export_endpoints_valid = all(
            relation["from"] in {entity["id"] for entity in graph_data["entities"]}
            and relation["to"] in {entity["id"] for entity in graph_data["entities"]}
            for relation in graph_data["relations"]
        )

        demo_checks = self._threshold_checks(status, DEMO_THRESHOLDS)
        research_checks = self._threshold_checks(status, RESEARCH_THRESHOLDS)
        structural_checks = {
            "graph_has_nodes": graph["node_count"] > 0,
            "graph_has_relations": graph["edge_count"] > 0,
            "graph_integrity": graph_integrity,
            "knowgraph_export_counts_match": export_counts_match,
            "knowgraph_export_endpoints_valid": export_endpoints_valid,
        }
        demo_ready = all(demo_checks.values()) and all(structural_checks.values())
        research_ready = all(research_checks.values()) and all(structural_checks.values())

        blockers = [name for name, passed in {**demo_checks, **structural_checks}.items() if not passed]
        research_gaps = [name for name, passed in research_checks.items() if not passed]
        return {
            "status": "ready" if demo_ready else "not_ready",
            "demo_ready": demo_ready,
            "research_ready": research_ready,
            "counts": status,
            "graph": {
                "nodes": graph["node_count"],
                "relations": graph["edge_count"],
                "dangling_edge_count": len(dangling_edges),
                "dangling_edges": dangling_edges[:20],
                "knowgraph_entities": graph_data["metadata"]["entity_count"],
                "knowgraph_relations": graph_data["metadata"]["relation_count"],
            },
            "checks": {
                "demo": demo_checks,
                "research": research_checks,
                "structural": structural_checks,
            },
            "blockers": blockers,
            "research_gaps": research_gaps,
            "disclaimer": "Research and decision-support readiness only; not approval for autonomous clinical use.",
        }

    @staticmethod
    def _threshold_checks(status: dict[str, Any], thresholds: dict[str, int]) -> dict[str, bool]:
        return {
            f"{name}_gte_{minimum}": int(status.get(name, 0)) >= minimum
            for name, minimum in thresholds.items()
        }


__all__ = ["PTCReadinessService", "DEMO_THRESHOLDS", "RESEARCH_THRESHOLDS"]
