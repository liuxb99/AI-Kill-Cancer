"""
Evidence Merger — unifies evidence from CIViC, DGIdb into a single evidence layer.

Matching priority chain:
  1. HGVS notation
  2. Normalized coordinates (chr:pos:ref:alt)
  3. Exact variant name
  4. Molecular profile
  5. Gene symbol fallback

Persists everything to DB via EvidenceItemRepository, DrugInteractionRepository.
Tracks match_level, conflict_status, source-native level vs normalized tier.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.pipeline.civic_adapter import CIViCAdapter
from src.backend.pipeline.dgidb_adapter import DGIdbAdapter
from src.backend.evidence.domain import (
    MATCH_LEVEL_ORDER, KnowledgeSourceModel,
)
# Lazy imports to avoid circular dependency
# KnowledgeSourceRepository, EvidenceItemRepository, DrugInteractionRepository
# are imported lazily in __init__ methods

logger = logging.getLogger(__name__)


class EvidenceMerger:
    """Merges evidence from multiple sources into unified results, persisted to DB."""

    def __init__(
        self,
        db: Optional[AsyncSession] = None,
        civic_adapter: Optional[CIViCAdapter] = None,
        dgidb_adapter: Optional[DGIdbAdapter] = None,
    ):
        self.db = db
        self.civic = civic_adapter or CIViCAdapter()
        self.dgidb = dgidb_adapter or DGIdbAdapter()
        self.retrieved_at: str = ""
        self._source_cache: dict[str, KnowledgeSourceModel] = {}

        # Repositories (lazy init)
        self._ks_repo: Optional[KnowledgeSourceRepository] = None
        self._ei_repo: Optional[EvidenceItemRepository] = None
        self._di_repo: Optional[DrugInteractionRepository] = None

    @property
    def ks_repo(self):
        if self._ks_repo is None and self.db is not None:
            from src.backend.repositories.knowledge_source_repo import KnowledgeSourceRepository
            self._ks_repo = KnowledgeSourceRepository(self.db)
        return self._ks_repo

    @property
    def ei_repo(self):
        if self._ei_repo is None and self.db is not None:
            from src.backend.repositories.evidence_item_repo import EvidenceItemRepository
            self._ei_repo = EvidenceItemRepository(self.db)
        return self._ei_repo

    @property
    def di_repo(self):
        if self._di_repo is None and self.db is not None:
            from src.backend.repositories.drug_interaction_repo import DrugInteractionRepository
            self._di_repo = DrugInteractionRepository(self.db)
        return self._di_repo

    async def _ensure_source(self, source_name: str, version: str = "",
                              license_text: str = "", base_url: str = "") -> Optional[KnowledgeSourceModel]:
        """Ensure a KnowledgeSource record exists, using cache."""
        if source_name in self._source_cache:
            return self._source_cache[source_name]

        if self.db is None or self.ks_repo is None:
            return None

        try:
            source = await self.ks_repo.upsert(
                name=source_name,
                version=version or None,
                license=license_text or None,
                base_url=base_url or None,
                is_configured="configured" if base_url else "not_configured",
            )
            self._source_cache[source_name] = source
            return source
        except Exception as e:
            logger.warning("Failed to ensure source %s: %s", source_name, e)
            return None

    def _determine_match_level(self, query: dict, item: dict) -> str:
        """
        Determine the match level between the query and an evidence item.
        Returns one of: exact_variant, equivalent_hgvs, coordinate_match,
                       molecular_profile_match, gene_level_only, unmatched
        """
        query_hgvs = query.get("hgvs", "").strip()
        item_hgvs = item.get("hgvs_description", "").strip()
        if query_hgvs and item_hgvs:
            # Normalize for comparison
            q_norm = query_hgvs.replace(" ", "").upper()
            i_norm = item_hgvs.replace(" ", "").upper()
            if q_norm == i_norm:
                return "exact_variant"
            if q_norm.rsplit(":", 1)[-1] == i_norm.rsplit(":", 1)[-1]:
                return "equivalent_hgvs"

        query_chrom = query.get("chromosome", "")
        query_pos = query.get("position", 0)
        query_ref = query.get("reference", "")
        query_alt = query.get("alternate", "")
        item_chrom = item.get("chromosome", "")
        item_pos = item.get("position", 0)
        item_ref = item.get("reference", "")
        item_alt = item.get("alternate", "")

        if query_chrom and query_pos and query_ref and query_alt:
            if (str(item_chrom) == str(query_chrom) and
                str(item_pos) == str(query_pos) and
                str(item_ref).upper() == str(query_ref).upper() and
                str(item_alt).upper() == str(query_alt).upper()):
                return "exact_variant"

        # Coordinate overlap check
        if query_chrom and query_pos:
            if str(item_chrom) == str(query_chrom) and str(item_pos) == str(query_pos):
                return "coordinate_match"

        # Variant name match
        query_variant = query.get("variant_name", "").strip()
        item_variant = item.get("variant_name", "").strip()
        if query_variant and item_variant:
            if query_variant.upper() == item_variant.upper():
                return "molecular_profile_match"

        # Gene level
        query_gene = query.get("gene_symbol", "").strip().upper()
        item_gene = item.get("gene_symbol", "").strip().upper()
        if query_gene and item_gene and query_gene == item_gene:
            return "gene_level_only"

        return "unmatched"

    def _determine_conflict_status(self, item: dict) -> str:
        """Determine conflict status from evidence direction."""
        direction = (item.get("evidence_direction", "") or "").lower()
        if direction in ("supports", "supporting", "sensitive", "responsiveness"):
            return "supporting"
        if direction in ("does not support", "conflicting", "resistance", "non-responsive"):
            return "conflicting"
        if direction in ("neutral", "inconclusive", "unknown", ""):
            return "uncertain"
        return "not_evaluable"

    async def refresh_all(self, gene_symbol: str, hgvs: str = "",
                           chromosome: str = "", position: int = 0,
                           reference: str = "", alternate: str = "",
                           variant_name: str = "",
                           request_id: str = "") -> dict:
        """
        Full refresh: query sources, merge, persist to DB, return summary.

        Matching priority:
          1. HGVS
          2. Normalized coordinates (chr:pos:ref:alt)
          3. Exact variant name
          4. Molecular profile
          5. Gene symbol fallback
        """
        self.retrieved_at = datetime.now(timezone.utc).isoformat()
        now = datetime.utcnow()

        all_items = []
        all_interactions = []
        warnings = []
        errors = []

        # Build query context
        query_ctx = {
            "gene_symbol": gene_symbol,
            "hgvs": hgvs,
            "chromosome": chromosome,
            "position": position,
            "reference": reference,
            "alternate": alternate,
            "variant_name": variant_name,
        }

        # Determine best match level achievable from query
        has_hgvs = bool(hgvs)
        has_coords = bool(chromosome and position and reference and alternate)
        bool(variant_name)
        has_gene = bool(gene_symbol)

        # ── Phase 1: HGVS lookup ──
        if has_hgvs:
            try:
                civic_result = await self.civic.lookup_hgvs(hgvs, request_id=request_id)
                if civic_result.success:
                    for r in civic_result.records:
                        r["_source"] = "civic"
                        r["_request_hash"] = civic_result.metadata.get("request_hash", "")
                        r["_response_hash"] = civic_result.metadata.get("response_hash", "")
                        r["_match_level"] = self._determine_match_level(query_ctx, r)
                        r["_conflict_status"] = self._determine_conflict_status(r)
                    all_items.extend(civic_result.records)
                if not civic_result.success and civic_result.errors:
                    errors.extend([f"CIViC HGVS: {e}" for e in civic_result.errors])
                if civic_result.warnings:
                    warnings.extend(civic_result.warnings)
            except Exception as e:
                errors.append(f"CIViC HGVS query failed: {e}")

        # ── Phase 2: Coordinate lookup ──
        if has_coords:
            try:
                civic_result = await self.civic.lookup_coordinates(
                    chromosome, position, reference, alternate,
                    request_id=request_id,
                )
                if civic_result.success:
                    for r in civic_result.records:
                        r["_source"] = "civic"
                        r["_request_hash"] = civic_result.metadata.get("request_hash", "")
                        r["_response_hash"] = civic_result.metadata.get("response_hash", "")
                        r["_match_level"] = self._determine_match_level(query_ctx, r)
                        r["_conflict_status"] = self._determine_conflict_status(r)
                    all_items.extend(civic_result.records)
                if not civic_result.success and civic_result.errors:
                    errors.extend([f"CIViC coordinates: {e}" for e in civic_result.errors])
                if civic_result.warnings:
                    warnings.extend(civic_result.warnings)
            except Exception as e:
                errors.append(f"CIViC coordinate query failed: {e}")

        # ── Phase 3: Gene lookup (also gets variant list) ──
        if has_gene:
            try:
                civic_result = await self.civic.lookup_variant(gene_symbol, variant_name, request_id=request_id)
                if civic_result.success:
                    for r in civic_result.records:
                        r["_source"] = "civic"
                        r["_request_hash"] = civic_result.metadata.get("request_hash", "")
                        r["_response_hash"] = civic_result.metadata.get("response_hash", "")
                        r["_match_level"] = self._determine_match_level(query_ctx, r)
                        r["_conflict_status"] = self._determine_conflict_status(r)
                    all_items.extend(civic_result.records)
                if not civic_result.success and civic_result.errors:
                    errors.extend([f"CIViC gene: {e}" for e in civic_result.errors])
                if civic_result.warnings:
                    warnings.extend(civic_result.warnings)
            except Exception as e:
                errors.append(f"CIViC gene query failed: {e}")

            # DGIdb
            try:
                dgidb_result = await self.dgidb.lookup_gene(gene_symbol, request_id=request_id)
                if dgidb_result.success:
                    for r in dgidb_result.records:
                        r["_source"] = "dgidb"
                        r["_match_level"] = "gene_level_only"
                        r["_conflict_status"] = "not_evaluable"
                    all_interactions.extend(dgidb_result.records)
                if not dgidb_result.success and dgidb_result.errors:
                    errors.extend([f"DGIdb: {e}" for e in dgidb_result.errors])
                if dgidb_result.warnings:
                    warnings.extend(dgidb_result.warnings)
            except Exception as e:
                errors.append(f"DGIdb query failed: {e}")

        # ── Deduplicate evidence ──
        seen_evidence: set = set()
        deduped_items = []
        for item in all_items:
            key = (item.get("_source", ""), str(item.get("source_record_id", "")),
                   item.get("gene_symbol", ""), item.get("drug_name", ""))
            if key not in seen_evidence:
                seen_evidence.add(key)
                deduped_items.append(item)

        # ── Deduplicate interactions ──
        seen_interactions: set = set()
        deduped_interactions = []
        for item in all_interactions:
            key = (item.get("gene_symbol", ""), item.get("drug_name", ""),
                   item.get("interaction_type", ""))
            if key not in seen_interactions:
                seen_interactions.add(key)
                deduped_interactions.append(item)

        # ── Best match level ──
        best_level = "unmatched"
        for item in deduped_items:
            ml = item.get("_match_level", "unmatched")
            if MATCH_LEVEL_ORDER.get(ml, 99) < MATCH_LEVEL_ORDER.get(best_level, 99):
                best_level = ml

        # ── Persist to DB ──
        persist_errors = []
        if self.db is not None:
            try:
                civic_source = await self._ensure_source(
                    "civic", "2.0", "CC-BY-4.0", "https://civicdb.org/api"
                )
                dgidb_source = await self._ensure_source(
                    "dgidb", "v2", "DGIdb terms", "https://dgidb.org/api/v2"
                )

                persisted_evidence = 0
                for item in deduped_items:
                    source_id = civic_source.id if civic_source and item.get("_source") == "civic" else None
                    if source_id:
                        await self.ei_repo.upsert(
                            source_id=source_id,
                            item=item,
                            match_level=item.get("_match_level", "gene_level_only"),
                            conflict_status=item.get("_conflict_status", "not_evaluable"),
                            now=now,
                        )
                        persisted_evidence += 1

                persisted_interactions = 0
                for item in deduped_interactions:
                    source_id = dgidb_source.id if dgidb_source else None
                    if source_id:
                        await self.di_repo.upsert(
                            source_id=source_id,
                            item=item,
                            now=now,
                        )
                        persisted_interactions += 1

                # Withdraw evidence no longer returned
                if civic_source:
                    active_ids = [
                        str(r.get("source_record_id", ""))
                        for r in deduped_items if r.get("_source") == "civic" and r.get("source_record_id")
                    ]
                    if active_ids:
                        withdrawn = await self.ei_repo.withdraw_by_source_record(civic_source.id, active_ids, now)
                        if withdrawn:
                            logger.info("Withdrew %d evidence items no longer in CIViC results", withdrawn)

            except Exception as e:
                persist_errors.append(f"DB persistence failed: {e}")
                logger.error("Evidence persistence error: %s", e)

        # ── Determine highest evidence level ──
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
            "match_level": best_level,
            "warnings": warnings + persist_errors,
            "errors": errors,
            "retrieved_at": self.retrieved_at,
            "source_updated": ["civic", "dgidb"] if self.db else [],
            "total_evidence_persisted": persisted_evidence if self.db else 0,
            "total_interactions_persisted": persisted_interactions if self.db else 0,
        }

    async def merge_variant_evidence(self, gene_symbol: str, hgvs: str = "",
                                      chromosome: str = "", position: int = 0,
                                      reference: str = "", alternate: str = "",
                                      variant_name: str = "",
                                      request_id: str = "") -> dict:
        """Alias for refresh_all for backward compatibility."""
        return await self.refresh_all(
            gene_symbol=gene_symbol, hgvs=hgvs,
            chromosome=chromosome, position=position,
            reference=reference, alternate=alternate,
            variant_name=variant_name, request_id=request_id,
        )

    async def merge_gene_evidence(self, gene_symbol: str, request_id: str = "") -> dict:
        """Gather and merge evidence for a gene from all sources."""
        return await self.refresh_all(gene_symbol=gene_symbol, request_id=request_id)
