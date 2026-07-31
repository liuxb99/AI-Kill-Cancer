"""Convert the complete PTC graph snapshot into KnowGraphGo GraphData JSON."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.services.ptc_completion_service import PTCCompletionService

PTC_GRAPH_NAMESPACE = uuid.UUID("6a54d11c-23ce-4b10-95aa-b3e0eeb97d4a")


def entity_uuid(business_id: str) -> str:
    return str(uuid.uuid5(PTC_GRAPH_NAMESPACE, f"entity:{business_id}"))


def relation_uuid(relation: str, source: str, target: str) -> str:
    return str(uuid.uuid5(PTC_GRAPH_NAMESPACE, f"relation:{relation}:{source}:{target}"))


class PTCKnowGraphExportService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def export(self, *, case_limit: int = 500) -> dict[str, Any]:
        snapshot = await PTCCompletionService(self.db).full_graph(case_limit=case_limit)
        node_map = {node["id"]: node for node in snapshot["nodes"]}

        # A graph import must never contain dangling relations. Some evidence or
        # interaction records can legally reference knowledge imported later;
        # represent these as explicit stub nodes so replay remains deterministic.
        for edge in snapshot["edges"]:
            for endpoint in (edge["source"], edge["target"]):
                if endpoint not in node_map:
                    kind = "ExternalKnowledgeStub"
                    label = endpoint.split(":", 1)[-1]
                    node_map[endpoint] = {
                        "id": endpoint,
                        "type": kind,
                        "label": label,
                        "properties": {"stub": True, "source_system": "AI-Kill-Cancer"},
                    }

        entities = [
            {
                "id": entity_uuid(node_id),
                "namespace": "ptc",
                "kind": node["type"],
                "name": node["label"] or node_id,
                "properties": {
                    **(node.get("properties") or {}),
                    "business_id": node_id,
                    "source_system": "AI-Kill-Cancer",
                },
                "provenance": "imported",
                "confidence": 1.0,
                "lifecycle": "active",
            }
            for node_id, node in sorted(node_map.items())
        ]
        relations = [
            {
                "id": relation_uuid(edge["relation"], edge["source"], edge["target"]),
                "namespace": "ptc",
                "from": entity_uuid(edge["source"]),
                "to": entity_uuid(edge["target"]),
                "kind": edge["relation"],
                "weight": 1.0,
                "confidence": 1.0,
                "provenance": "imported",
                "properties": {
                    **(edge.get("properties") or {}),
                    "business_relation_id": edge["id"],
                    "source_system": "AI-Kill-Cancer",
                },
            }
            for edge in sorted(snapshot["edges"], key=lambda item: item["id"])
        ]
        return {
            "schema": {
                "version": "1.0",
                "entity_kinds": sorted({item["kind"] for item in entities}),
                "relation_kinds": sorted({item["kind"] for item in relations}),
            },
            "entities": entities,
            "relations": relations,
            "metadata": {
                "domain": "papillary_thyroid_carcinoma",
                "source_system": "AI-Kill-Cancer",
                "generated_at": datetime.utcnow().isoformat(),
                "id_strategy": "uuid5",
                "entity_count": len(entities),
                "relation_count": len(relations),
            },
        }


__all__ = ["PTCKnowGraphExportService", "entity_uuid", "relation_uuid", "PTC_GRAPH_NAMESPACE"]
