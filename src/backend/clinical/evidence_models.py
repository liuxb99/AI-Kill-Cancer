"""
EvidenceBundle and EvidenceItem models for clinical evidence aggregation.

Provides a unified data structure that integrates evidence from NCCN, ESMO,
FDA, ClinVar, CIViC, OncoKB, PubMed, and internal sources for the Phase 2
Evidence Collector.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, Field, computed_field

# ─── Evidence Level Utilities ──────────────────────────────────────────────────

LEVEL_PRECEDENCE: list[str] = [
    "A",
    "B",
    "C",
    "D",
    "E",
    "Level_1",
    "Level_2",
    "Level_3",
    "Level_4",
    "Level_5",
    "not_assessed",
]

LEVEL_ORDER: dict[str, int] = {v: i for i, v in enumerate(LEVEL_PRECEDENCE)}


def evidence_level_rank(level: str) -> int:
    """Return a numeric rank for an evidence level (lower is better)."""
    return LEVEL_ORDER.get(level, len(LEVEL_PRECEDENCE))


# ─── SourceStatus Types ────────────────────────────────────────────────────────


class SourceStatusType(str, Enum):
    """Operational status of a clinical evidence knowledge source.

    Indicates whether the source is currently available, unavailable,
    requires authorisation (API key / licence), or encountered an error.
    """

    AVAILABLE = "available"
    """Source is fully accessible and returning data."""

    UNAVAILABLE = "unavailable"
    """Source is temporarily unavailable (network outage, rate-limit, etc.)."""

    AUTHORIZATION_REQUIRED = "authorization_required"
    """Source requires an API key or commercial licence that has not been configured."""

    ERROR = "error"
    """Source encountered an unrecoverable error."""


class SourceStatus(BaseModel):
    """Status snapshot for a single evidence knowledge source.

    Carried inside ``EvidenceBundle.source_statuses`` so downstream
    consumers can inspect whether a source was reachable, authorised,
    or encountered a problem during collection.
    """

    source_name: str
    """Identifier of the knowledge source (e.g. ``"nccn"``, ``"esmo"``, ``"oncokb"``)."""

    status_type: SourceStatusType
    """The operational status of this source at collection time."""

    message: str | None = None
    """Optional human-readable detail describing the status (e.g. ``"requires API key / licence"``)."""

    items_count: int = 0
    """Number of evidence items retrieved from this source during collection."""

    timestamp: str = ""
    """ISO-8601 timestamp when the status was recorded."""


# ─── EvidenceItem Model ────────────────────────────────────────────────────────


class EvidenceItem(BaseModel):
    """A single piece of clinical evidence from any knowledge source.

    Each item carries provenance fields (source, citation) and normalised
    clinical attributes (evidence_type, evidence_level, etc.) so that
    downstream consumers (ranking, reasoning, report) can operate on a
    uniform schema regardless of the originating source.
    """

    source: str
    """Name of the knowledge source (NCCN, ESMO, FDA, ClinVar, CIViC,
    OncoKB, PubMed, Internal)."""

    source_record_id: str | None = None
    """Original record identifier in the source system."""

    gene_symbol: str | None = None
    drug_name: str | None = None
    disease: str | None = None

    evidence_type: str = ""
    """Clinical category — predictive, prognostic, diagnostic, etc."""

    evidence_direction: str = ""
    """Direction relative to a claim — supporting, conflicting, neutral."""

    evidence_level: str = ""
    """Normalised level string — one of A, B, C, D, E or Level_1–5."""

    source_native_level: str | None = None
    """Original evidence-level string from the source (e.g. CIViC A,
    OncoKB 3B)."""

    clinical_significance: str | None = None
    """Sensitivity, resistance, etc."""

    citation: str | None = None
    pmid: str | None = None
    url: str | None = None

    confidence: str | None = None
    """Assessment confidence — high, medium, low."""

    match_level: str | None = None
    """How this evidence matched the query — exact_variant, gene_level_only,
    etc."""

    conflict_status: str | None = None
    """Whether this item agrees or conflicts with the majority — supporting,
    conflicting, uncertain."""

    description: str | None = None


# ─── EvidenceBundle Model ──────────────────────────────────────────────────────


class EvidenceBundle(BaseModel):
    """Aggregated collection of evidence items with grouped views.

    Acts as the primary output of the Evidence Collector: a flat list of
    items plus computed convenience views (by source, by gene, by drug),
    conflict/level summaries, and a per-source status list that records
    whether each knowledge source was reachable, authorised, or errored.
    """

    items: list[EvidenceItem] = Field(default_factory=list)
    """All evidence items in the bundle."""

    source_statuses: list[SourceStatus] = Field(default_factory=list)
    """Per-source operational status recorded during collection.

    Each entry captures whether the knowledge source was available,
    unavailable, required authorisation, or encountered an error.
    """

    retrieved_at: str = ""
    """ISO-8601 timestamp of when the data was retrieved."""

    context_hash: str | None = None
    """SHA256 hash of the associated ClinicalContext, for traceability."""

    def _current_timestamp(self) -> str:
        """Return an ISO-8601 UTC timestamp string."""
        return datetime.now(UTC).isoformat()

    # ── Computed alias fields ─────────────────────────────────────────────

    @computed_field
    @property
    def total_count(self) -> int:
        """Total number of evidence items."""
        return len(self.items)

    @computed_field
    @property
    def by_source(self) -> dict[str, list[EvidenceItem]]:
        """Evidence items grouped by source name."""
        result: dict[str, list[EvidenceItem]] = {}
        for item in self.items:
            result.setdefault(item.source, []).append(item)
        return result

    @computed_field
    @property
    def by_gene(self) -> dict[str, list[EvidenceItem]]:
        """Evidence items grouped by gene symbol."""
        result: dict[str, list[EvidenceItem]] = {}
        for item in self.items:
            key = item.gene_symbol or "__missing__"
            result.setdefault(key, []).append(item)
        return result

    @computed_field
    @property
    def by_drug(self) -> dict[str, list[EvidenceItem]]:
        """Evidence items grouped by drug name."""
        result: dict[str, list[EvidenceItem]] = {}
        for item in self.items:
            key = item.drug_name or "__missing__"
            result.setdefault(key, []).append(item)
        return result

    @computed_field
    @property
    def highest_level(self) -> str | None:
        """Best (highest) evidence level among all items, or None if empty.

        Priority order: A > B > C > D > E > Level_1 > … > Level_5 > not_assessed.
        """
        best: str | None = None
        best_rank = len(LEVEL_PRECEDENCE)
        for item in self.items:
            rank = evidence_level_rank(item.evidence_level)
            if rank < best_rank:
                best_rank = rank
                best = item.evidence_level
        return best

    @computed_field
    @property
    def conflicts_summary(self) -> list[dict]:
        """Summary of conflict-status distribution across items."""
        counts: dict[str, int] = {}
        for item in self.items:
            status = item.conflict_status or "unknown"
            counts[status] = counts.get(status, 0) + 1
        return [
            {"status": status, "count": count}
            for status, count in sorted(counts.items())
        ]

    # ── Filter ────────────────────────────────────────────────────────────

    def filter(
        self,
        gene: str | None = None,
        drug: str | None = None,
        source: str | None = None,
        min_level: str | None = None,
    ) -> EvidenceBundle:
        """Return a new bundle containing only items matching all criteria.

        Parameters
        ----------
        gene : str, optional
            Filter by exact gene symbol.
        drug : str, optional
            Filter by exact drug name.
        source : str, optional
            Filter by source name.
        min_level : str, optional
            Minimum evidence level (inclusive). Items with a level equal
            to or better (higher rank) than this value are kept.
            Example: ``min_level="C"`` keeps A, B, and C.
        """
        filtered = list(self.items)

        if gene is not None:
            filtered = [i for i in filtered if i.gene_symbol == gene]

        if drug is not None:
            filtered = [i for i in filtered if i.drug_name == drug]

        if source is not None:
            filtered = [i for i in filtered if i.source == source]

        if min_level is not None:
            min_rank = evidence_level_rank(min_level)
            filtered = [
                i for i in filtered
                if evidence_level_rank(i.evidence_level) <= min_rank
            ]

        return EvidenceBundle(
            items=filtered,
            retrieved_at=self.retrieved_at,
            context_hash=self.context_hash,
        )


__all__ = [
    "EvidenceBundle",
    "EvidenceItem",
    "SourceStatus",
    "SourceStatusType",
    "evidence_level_rank",
    "LEVEL_PRECEDENCE",
    "LEVEL_ORDER",
]
