"""
Evidence Merger — unifies evidence from CIViC, DGIdb into a single evidence layer.

Deduplicates by (source, source_record_id).
Merges evidence with same gene_symbol + drug_name by keeping the highest evidence level.
Preserves provenance for all sources.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from src.backend.pipeline.civic_adapter import CIViCAdapter
from src.backend.pipeline.dgidb_adapter import DGIdbAdapter
from src.backend.adapters.base import AdapterResult

logger = logging.getLogger(__name__)


class EvidenceMerger:
    """Merges evidence from multiple sources into unified results."""

    def __init__(self, civic_adapter: Optional[CIViCAdapter] = None, dgidb_adapter: Optional[DGIdbAdapter] = None):
        self.civic = civic_adapter or CIViCAdapter()
        self.dgidb = dgidb_adapter or DGIdbAdapter()
        self.retrieved_at: str = ""

    async def merge_variant_evidence(self, gene_symbol: str, hgvs: str = "", chromosome: str = "", position: int = 0,
                                      reference: str = "", alternate: str = "", request_id: str = "") -> dict:
        """Gather and merge evidence for a variant from all sources."""
        self.retrieved_at = datetime.now(timezone.utc).isoformat()
        all_items = []
        all_interactions = []
        warnings = []
        errors = []

        # CIViC lookup
        try:
            civic_payload = {"gene": gene_symbol}
            if hgvs:
                civic_payload["hgvs"] = hgvs
            if chromosome:
                civic_payload.update({"chromosome": chromosome, "position": position, "reference": reference, "alternate": alternate})
            civic_result = await self.civic.annotate(civic_payload, request_id=request_id)
            if civic_result.success:
                for r in civic_result.records:
                    r["_source"] = "civic"
                    r["_source_record_id"] = r.get("source_record_id", "")
                all_items.extend(civic_result.records)
            if civic_result.warnings:
                warnings.extend(civic_result.warnings)
        except Exception as e:
            errors.append(f"CIViC query failed: {e}")

        # DGIdb lookup
        try:
            dgidb_result = await self.dgidb.annotate(gene_symbol, request_id=request_id)
            if dgidb_result.success:
                for r in dgidb_result.records:
                    r["_source"] = "dgidb"
                all_interactions.extend(dgidb_result.records)
            if dgidb_result.warnings:
                warnings.extend(dgidb_result.warnings)
        except Exception as e:
            errors.append(f"DGIdb query failed: {e}")

        # Deduplicate evidence by (source, source_record_id)
        seen: set = set()
        deduped_items = []
        for item in all_items:
            key = (item.get("_source", ""), str(item.get("_source_record_id", "")))
            if key not in seen:
                seen.add(key)
                deduped_items.append(item)

        # Deduplicate interactions by (source, drug_name, interaction_type)
        seen_interactions: set = set()
        deduped_interactions = []
        for item in all_interactions:
            key = (item.get("source", ""), item.get("drug_name", ""), item.get("interaction_type", ""))
            if key not in seen_interactions:
                seen_interactions.add(key)
                deduped_interactions.append(item)

        # Determine highest evidence level
        level_order = {"Level_1": 1, "Level_2": 2, "Level_3": 3, "Level_4": 4, "Level_5": 5,
                       "A": 1, "B": 2, "C": 3, "D": 4, "E": 5}
        highest_level = None
        lowest_order = 99
        for item in deduped_items:
            lvl = item.get("evidence_level", "")
            order = level_order.get(lvl, 99)
            if order < lowest_order:
                lowest_order = order
                highest_level = lvl

        return {
            "gene_symbol": gene_symbol,
            "evidence_items": deduped_items,
            "drug_interactions": deduped_interactions,
            "evidence_count": len(deduped_items),
            "drug_count": len(deduped_interactions),
            "highest_evidence_level": highest_level,
            "warnings": warnings,
            "errors": errors,
            "retrieved_at": self.retrieved_at,
        }

    async def merge_gene_evidence(self, gene_symbol: str, request_id: str = "") -> dict:
        """Gather and merge evidence for a gene from all sources."""
        return await self.merge_variant_evidence(gene_symbol=gene_symbol, request_id=request_id)
