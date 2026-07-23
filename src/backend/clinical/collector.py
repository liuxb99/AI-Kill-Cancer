"""
EvidenceCollector — aggregates clinical evidence from multiple knowledge sources.

Collects evidence from CIViC, DGIdb, ClinVar, PubMed, ClinicalTrials.gov and
assembles the results into a unified ``EvidenceBundle``.  Authorisation-required
sources (NCCN, ESMO, OncoKB) are logged as warnings and return empty results.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.clinical.evidence_models import (
    EvidenceBundle,
    EvidenceItem,
    SourceStatus,
    SourceStatusType,
)
from src.backend.clinical.models import ClinicalContext
from src.backend.evidence.cache import gene_cache, variant_cache
from src.backend.evidence.merger import EvidenceMerger
from src.backend.knowledge.adapters.clinicaltrials import ClinicalTrialsAdapter
from src.backend.knowledge.adapters.clinvar import ClinVarAdapter
from src.backend.knowledge.adapters.pubmed import PubMedAdapter
from src.backend.reasoning.conflicts import ConflictAnalyzer

logger = logging.getLogger(__name__)

# ─── External sources that require authorisation — placeholder only ────────────

_AUTH_SOURCES: tuple[str, ...] = ("nccn", "esmo", "oncokb")
"""Knowledge sources that need API keys / licences — reserved for future use."""


class EvidenceCollector:
    """Aggregate clinical evidence for a given clinical context.

    Collects data from multiple knowledge sources (CIViC, DGIdb, ClinVar,
    PubMed, ClinicalTrials.gov), runs conflict analysis, and packages
    everything into an ``EvidenceBundle``.

    External API failures are logged and result in partial results rather
    than aborting the entire collection process.
    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialise the collector with a database session.

        Args:
            db: An active async SQLAlchemy session used by the
                ``EvidenceMerger`` and available for future repository
                access.
        """
        self.db = db
        self._merger = EvidenceMerger(db=db)
        self._conflict_analyzer = ConflictAnalyzer()

        # Adapters — lazy initialisation so they can be overridden in tests
        self._clinvar: ClinVarAdapter | None = None
        self._pubmed: PubMedAdapter | None = None
        self._clinicaltrials: ClinicalTrialsAdapter | None = None

    # ── Public API ─────────────────────────────────────────────────────────

    async def collect(self, context: ClinicalContext) -> EvidenceBundle:
        """Collect and aggregate evidence for the given clinical context.

        Iterates over all unique ``gene_symbol`` values found in
        ``context.variants`` and gathers evidence from every available
        knowledge source.  Results are deduplicated at the gene level
        via in-memory TTL caches (``gene_cache``, ``variant_cache``).

        Args:
            context: A frozen ``ClinicalContext`` snapshot containing
                patient, case and variant information.

        Returns:
            An ``EvidenceBundle`` with all collected evidence items,
            grouped views (by source, gene, drug) and conflict
            summaries pre-computed.
        """
        all_items: list[EvidenceItem] = []
        source_statuses: list[SourceStatus] = []
        seen_genes: set[str] = set()

        for variant in context.variants:
            gene = (variant.get("gene_symbol") or "").strip()
            if not gene or gene in seen_genes:
                continue
            seen_genes.add(gene)

            gene_items, gene_statuses = await self._collect_for_gene(gene, context)
            all_items.extend(gene_items)
            source_statuses.extend(gene_statuses)

        # ── Authorisation-required sources ──────────────────────────────
        now_ts = datetime.now(UTC).isoformat()
        source_statuses.extend(self._report_auth_sources())

        bundle = EvidenceBundle(
            items=all_items,
            source_statuses=source_statuses,
            retrieved_at=now_ts,
            context_hash=context.context_hash or "",
        )
        return bundle

    async def collect_by_variant(self, gene: str, hgvs: str) -> EvidenceBundle:
        """Collect evidence scoped to a single variant.

        Args:
            gene: The gene symbol (e.g. *EGFR*).
            hgvs: The HGVS notation of the variant (e.g.
                ``NM_005228.5:c.2573T>G``).

        Returns:
            An ``EvidenceBundle`` containing evidence specific to the
            given variant, plus gene-level evidence from sources that
            do not support variant-level queries.
        """
        items: list[EvidenceItem] = []
        source_statuses: list[SourceStatus] = []
        now_ts = datetime.now(UTC).isoformat()

        # ── Variant-level cache ──────────────────────────────────────────
        cache_key = f"variant:{gene}:{hgvs}"
        cached = variant_cache.get(cache_key)
        if cached is not None:
            return EvidenceBundle(
                items=list(cached),
                source_statuses=source_statuses,
                retrieved_at=now_ts,
            )

        def _record(source_name: str, ok: bool, exc: Exception | None = None,
                    count: int = 0) -> None:
            """Append a SourceStatus entry for *source_name*."""
            if ok:
                source_statuses.append(
                    SourceStatus(
                        source_name=source_name,
                        status_type=SourceStatusType.AVAILABLE,
                        message="success",
                        timestamp=now_ts,
                        items_count=count,
                    )
                )
            else:
                source_statuses.append(
                    SourceStatus(
                        source_name=source_name,
                        status_type=SourceStatusType.ERROR,
                        message=str(exc) if exc else "unknown error",
                        timestamp=now_ts,
                        items_count=0,
                    )
                )

        # ── CIViC via merger (variant-level) ─────────────────────────────
        try:
            merger_result = await self._merger.merge_variant_evidence(
                gene_symbol=gene, hgvs=hgvs,
            )
            for raw in merger_result.get("evidence_items", []):
                items.append(self._raw_to_evidence_item(raw))
            _record("civic", ok=True, count=len(items))
        except Exception as e:
            _record("civic", ok=False, exc=e)
            logger.warning(
                "Failed to merge variant evidence for %s %s",
                gene, hgvs, exc_info=True,
            )

        # ── ClinVar ──────────────────────────────────────────────────────
        clinvar_before = len(items)
        try:
            clinvar = self._get_clinvar()
            results = await clinvar.search_variant(hgvs)
            for raw in results:
                items.append(self._raw_to_evidence_item(raw))
            _record("clinvar", ok=True, count=len(items) - clinvar_before)
        except Exception as e:
            _record("clinvar", ok=False, exc=e)
            logger.warning(
                "ClinVar query failed for %s %s", gene, hgvs, exc_info=True,
            )

        # ── PubMed ───────────────────────────────────────────────────────
        pubmed_before = len(items)
        try:
            pubmed = self._get_pubmed()
            results = await pubmed.search(hgvs)
            for raw in results:
                items.append(self._raw_to_evidence_item(raw))
            _record("pubmed", ok=True, count=len(items) - pubmed_before)
        except Exception as e:
            _record("pubmed", ok=False, exc=e)
            logger.warning(
                "PubMed query failed for %s %s", gene, hgvs, exc_info=True,
            )

        # ── ClinicalTrials ───────────────────────────────────────────────
        ct_before = len(items)
        try:
            ct = self._get_clinicaltrials()
            results = await ct.search(hgvs)
            for raw in results:
                items.append(self._raw_to_evidence_item(raw))
            _record("clinicaltrials", ok=True, count=len(items) - ct_before)
        except Exception as e:
            _record("clinicaltrials", ok=False, exc=e)
            logger.warning(
                "ClinicalTrials query failed for %s %s",
                gene, hgvs, exc_info=True,
            )

        # ── Authorisation-required sources placeholder ───────────────────
        source_statuses.extend(
            self._report_auth_sources(gene=gene, hgvs=hgvs)
        )

        # ── Conflict analysis ────────────────────────────────────────────
        try:
            self._annotate_conflicts(items)
        except Exception:
            logger.warning("Conflict analysis failed", exc_info=True)

        # ── Cache and return ─────────────────────────────────────────────
        variant_cache.set(cache_key, items)
        return EvidenceBundle(
            items=items,
            source_statuses=source_statuses,
            retrieved_at=datetime.now(UTC).isoformat(),
        )

    # ── Internal: per-gene collection ─────────────────────────────────────

    async def _collect_for_gene(
        self, gene: str, context: ClinicalContext,
    ) -> tuple[list[EvidenceItem], list[SourceStatus]]:
        """Collect evidence for a single gene from all available sources.

        Uses the in-memory ``gene_cache`` to avoid redundant API calls
        for the same gene within the TTL window.

        Args:
            gene: The gene symbol to collect evidence for.
            context: The parent clinical context (used for context_hash
                traceability).

        Returns:
            A tuple ``(items, source_statuses)`` where *items* is a list
            of ``EvidenceItem`` instances gathered from all sources for
            this gene, and *source_statuses* is a list of per-source
            operational status records.
        """
        cache_key = f"gene:{gene}"
        cached = gene_cache.get(cache_key)
        if cached is not None:
            return list(cached), []

        items: list[EvidenceItem] = []
        source_statuses: list[SourceStatus] = []
        now_ts = datetime.now(UTC).isoformat()

        def _record(source_name: str, ok: bool, exc: Exception | None = None,
                    count: int = 0) -> None:
            """Append a SourceStatus entry for *source_name*."""
            if ok:
                source_statuses.append(
                    SourceStatus(
                        source_name=source_name,
                        status_type=SourceStatusType.AVAILABLE,
                        message="success",
                        timestamp=now_ts,
                        items_count=count,
                    )
                )
            else:
                source_statuses.append(
                    SourceStatus(
                        source_name=source_name,
                        status_type=SourceStatusType.ERROR,
                        message=str(exc) if exc else "unknown error",
                        timestamp=now_ts,
                        items_count=0,
                    )
                )

        # ── 1. CIViC / DGIdb via EvidenceMerger ──────────────────────────
        try:
            merger_result = await self._merger.merge_gene_evidence(
                gene_symbol=gene,
            )
            for raw in merger_result.get("evidence_items", []):
                items.append(self._raw_to_evidence_item(raw))
            for raw in merger_result.get("drug_interactions", []):
                items.append(self._raw_to_evidence_item(raw))
            _record("civic", ok=True, count=len(items))
        except Exception as e:
            _record("civic", ok=False, exc=e)
            logger.warning(
                "EvidenceMerger failed for gene %s", gene, exc_info=True,
            )

        # ── 2. ClinVar ────────────────────────────────────────────────────
        clinvar_items_before = len(items)
        try:
            clinvar = self._get_clinvar()
            results = await clinvar.search_variant(gene)
            for raw in results:
                items.append(self._raw_to_evidence_item(raw))
            _record("clinvar", ok=True, count=len(items) - clinvar_items_before)
        except Exception as e:
            _record("clinvar", ok=False, exc=e)
            logger.warning(
                "ClinVar query failed for gene %s", gene, exc_info=True,
            )

        # ── 3. PubMed ─────────────────────────────────────────────────────
        pubmed_items_before = len(items)
        try:
            pubmed = self._get_pubmed()
            results = await pubmed.search(gene)
            for raw in results:
                items.append(self._raw_to_evidence_item(raw))
            _record("pubmed", ok=True, count=len(items) - pubmed_items_before)
        except Exception as e:
            _record("pubmed", ok=False, exc=e)
            logger.warning(
                "PubMed query failed for gene %s", gene, exc_info=True,
            )

        # ── 4. ClinicalTrials.gov ─────────────────────────────────────────
        ct_items_before = len(items)
        try:
            ct = self._get_clinicaltrials()
            results = await ct.search(gene)
            for raw in results:
                items.append(self._raw_to_evidence_item(raw))
            _record("clinicaltrials", ok=True, count=len(items) - ct_items_before)
        except Exception as e:
            _record("clinicaltrials", ok=False, exc=e)
            logger.warning(
                "ClinicalTrials query failed for gene %s",
                gene, exc_info=True,
            )

        # ── 5. Conflict analysis ──────────────────────────────────────────
        try:
            self._annotate_conflicts(items)
        except Exception:
            logger.warning(
                "Conflict analysis failed for gene %s", gene, exc_info=True,
            )

        # ── Cache the gene-level results ──────────────────────────────────
        gene_cache.set(cache_key, items)
        return items, source_statuses

    # ── Internal helpers ─────────────────────────────────────────────────

    @staticmethod
    def _report_auth_sources(
        gene: str = "",
        hgvs: str = "",
    ) -> list[SourceStatus]:
        """Return SourceStatus entries for all authorisation-required sources.

        Logs a warning for each source and produces an
        ``AUTHORIZATION_REQUIRED`` status entry.  When *gene* and/or
        *hgvs* are supplied the warning message includes them.

        Args:
            gene: Optional gene symbol for context in the log message.
            hgvs: Optional HGVS notation for context in the log message.

        Returns:
            A list of ``SourceStatus`` instances — one per auth-required
            source, each with status ``AUTHORIZATION_REQUIRED``.
        """
        now_ts = datetime.now(UTC).isoformat()
        suffix = f" for variant {gene} {hgvs}" if gene and hgvs else ""

        statuses: list[SourceStatus] = []
        for src in _AUTH_SOURCES:
            logger.warning(
                "Knowledge source '%s' requires authorisation — "
                "returning empty results%s.",
                src, suffix,
            )
            statuses.append(
                SourceStatus(
                    source_name=src,
                    status_type=SourceStatusType.AUTHORIZATION_REQUIRED,
                    message="requires API key / licence",
                    timestamp=now_ts,
                )
            )
        return statuses

    @staticmethod
    def _raw_to_evidence_item(raw: dict[str, Any]) -> EvidenceItem:
        """Convert a raw dictionary from any source to an ``EvidenceItem``.

        Handles field-name normalisation for every supported knowledge
        source (CIViC, DGIdb, ClinVar, PubMed, ClinicalTrials.gov).

        Args:
            raw: A flat dictionary as returned by the various adapters
                or the ``EvidenceMerger``.

        Returns:
            A populated ``EvidenceItem`` instance.
        """
        source = raw.get("_source") or raw.get("source") or ""
        source_record_id = raw.get("source_record_id") or ""
        gene_symbol = raw.get("gene_symbol") or ""
        drug_name = raw.get("drug_name") or ""
        disease = raw.get("disease") or ""
        evidence_type = raw.get("evidence_type") or ""
        evidence_direction = raw.get("evidence_direction") or ""
        evidence_level = raw.get("evidence_level") or ""
        source_native_level = raw.get("source_native_level")
        clinical_significance = raw.get("clinical_significance") or ""
        description = raw.get("description") or raw.get("title") or raw.get("variant_name") or ""
        citation = raw.get("citation") or raw.get("journal") or ""
        pmid = raw.get("pmid") or ""
        url = raw.get("url") or ""
        confidence = raw.get("confidence") or raw.get("review_status") or ""
        match_level = raw.get("_match_level") or raw.get("match_level") or ""
        conflict_status = raw.get("_conflict_status") or raw.get("conflict_status") or ""

        return EvidenceItem(
            source=source,
            source_record_id=source_record_id,
            gene_symbol=gene_symbol,
            drug_name=drug_name,
            disease=disease,
            evidence_type=evidence_type,
            evidence_direction=evidence_direction,
            evidence_level=evidence_level,
            source_native_level=source_native_level,
            clinical_significance=clinical_significance,
            description=description,
            citation=citation,
            pmid=pmid,
            url=url,
            confidence=confidence,
            match_level=match_level,
            conflict_status=conflict_status,
        )

    @staticmethod
    def _annotate_conflicts(items: list[EvidenceItem]) -> None:
        """Run conflict analysis on a list of items and update their statuses.

        Uses ``ConflictAnalyzer`` to detect drug-level conflicts and
        sets the ``conflict_status`` field on each ``EvidenceItem``
        based on the analysis result.

        Args:
            items: The list of evidence items to analyse (mutated in
                place).
        """
        if not items:
            return

        analyzer = ConflictAnalyzer()
        item_dicts = [item.model_dump() for item in items]
        conflicts = analyzer.analyze(item_dicts)

        # Build a lookup: drug_name → conflict_status
        conflict_map: dict[str, str] = {}
        for report in conflicts:
            drug = report.get("drug_name", "")
            if report.get("conflicting_count", 0) > 0:
                conflict_map[drug] = "conflicting"
            elif report.get("supporting_count", 0) > 0:
                conflict_map[drug] = "supporting"

        # Apply conflict status to each item based on its drug
        for item in items:
            if item.drug_name and item.drug_name in conflict_map:
                item.conflict_status = conflict_map[item.drug_name]
            elif item.conflict_status is None or item.conflict_status == "":
                item.conflict_status = "not_evaluable"

    def _get_clinvar(self) -> ClinVarAdapter:
        """Return (and lazily create) the ClinVar adapter."""
        if self._clinvar is None:
            self._clinvar = ClinVarAdapter()
        return self._clinvar

    def _get_pubmed(self) -> PubMedAdapter:
        """Return (and lazily create) the PubMed adapter."""
        if self._pubmed is None:
            self._pubmed = PubMedAdapter()
        return self._pubmed

    def _get_clinicaltrials(self) -> ClinicalTrialsAdapter:
        """Return (and lazily create) the ClinicalTrials.gov adapter."""
        if self._clinicaltrials is None:
            self._clinicaltrials = ClinicalTrialsAdapter()
        return self._clinicaltrials


__all__ = [
    "EvidenceCollector",
]
