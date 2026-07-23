"""
VariantAgent — gene variant analysis for the Phase 2b multi-agent system.

Analyses each variant in a :class:`ClinicalContext` snapshot, cross-references
them against ClinVar / CIViC evidence from the :class:`EvidenceBundle`,
assesses clinical significance, and identifies druggable alterations.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from src.backend.agents.base import BaseAgent
from src.backend.agents.models import AgentOpinion
from src.backend.clinical.evidence_models import EvidenceBundle
from src.backend.clinical.models import ClinicalContext

# ─── Helper constants ──────────────────────────────────────────────────────────

_CLINICAL_SIGNIFICANCE_ORDER: dict[str, int] = {
    "pathogenic": 0,
    "likely_pathogenic": 1,
    "VUS": 2,
    "likely_benign": 3,
    "benign": 4,
}

_KNOWN_VARIANT_SOURCES = {"ClinVar", "CIViC"}


# ─── Agent implementation ──────────────────────────────────────────────────────


class VariantAgent(BaseAgent):
    """Analyse gene variants from a clinical context and associated evidence.

    This agent evaluates each variant listed in *context.variants*,
    correlates it with variant-specific evidence items (especially from
    ClinVar and CIViC), assigns a clinical significance label, and
    determines whether any alteration is druggable based on the presence
    of drug-associated evidence.

    Parameters
    ----------
    db : AsyncSession
        SQLAlchemy asynchronous database session.

    Attributes
    ----------
    agent_type : str
        Unique identifier ``"variant"``.
    agent_version : str
        Semantic version ``"1.0.0"``.
    """

    agent_type: str = "variant"
    agent_version: str = "1.0.0"

    async def analyze(
        self,
        context: ClinicalContext,
        evidence: EvidenceBundle,
    ) -> AgentOpinion:
        """Analyse variants and return a structured opinion.

        For each variant in *context.variants* the agent:

        - Extracts the gene symbol, HGVS notation, protein change, VAF,
          and any pre-recorded clinical significance.
        - Filters the evidence bundle for items matching the same gene
          symbol, then narrows to ClinVar / CIViC records.
        - Derives an aggregate clinical-significance label guided by the
          evidence (pathogenic → likely_pathogenic → VUS → likely_benign
          → benign).
        - Checks whether any drug-associated evidence item exists for the
          gene to flag the variant as potentially druggable.
        - Records source references with citations.

        Parameters
        ----------
        context : ClinicalContext
            Frozen clinical snapshot containing ``variants`` and patient
            metadata.
        evidence : EvidenceBundle
            Aggregated evidence items from all configured knowledge
            sources.

        Returns
        -------
        AgentOpinion
            A structured opinion that includes a per-variant breakdown,
            a summary of druggable alterations, and supporting references.
        """
        if not context.variants:
            return self._build_empty_opinion(context)

        # ── Analyse each variant ──────────────────────────────────────────
        variant_analyses: list[dict[str, Any]] = []
        all_references: list[dict[str, str]] = []
        druggable_genes: list[str] = []
        total_pathogenic = 0

        for variant in context.variants:
            gene_symbol = variant.get("gene_symbol", "") or ""
            analysis = self._analyse_single_variant(
                variant=variant,
                evidence=evidence,
                gene_symbol=gene_symbol,
            )

            variant_analyses.append(analysis)
            all_references.extend(analysis["references"])

            if analysis.get("is_druggable"):
                druggable_genes.append(gene_symbol)

            if analysis.get("aggregate_significance") in (
                "pathogenic",
                "likely_pathogenic",
            ):
                total_pathogenic += 1

        # ── Build summary text ────────────────────────────────────────────
        summary_parts: list[str] = [
            f"Analysed {len(context.variants)} variant(s) in "
            f"{context.cancer_type} ({context.diagnosis})."
        ]

        if total_pathogenic:
            summary_parts.append(
                f"{total_pathogenic} variant(s) classified as pathogenic or "
                f"likely pathogenic."
            )

        if druggable_genes:
            summary_parts.append(
                f"Druggable alteration(s) identified in: "
                f"{', '.join(sorted(set(druggable_genes)))}."
            )
        else:
            summary_parts.append("No druggable alterations identified.")

        summary = " ".join(summary_parts)

        # ── Build pros / cons ─────────────────────────────────────────────
        pros: list[str] = []
        cons: list[str] = []

        if druggable_genes:
            pros.append(
                f"Druggable target(s) in {', '.join(sorted(set(druggable_genes)))} "
                f"— consider targeted therapy options."
            )
        if total_pathogenic:
            pros.append(
                "Clinically significant variant(s) support molecular-driven "
                "treatment decisions."
            )

        if not druggable_genes and not total_pathogenic:
            cons.append(
                "No pathogenic or druggable variants identified; standard-of-care "
                "treatment may be appropriate."
            )

        variant_without_evidence = [
            a["gene_symbol"]
            for a in variant_analyses
            if not a.get("has_civic_clinvar_evidence")
        ]
        if variant_without_evidence:
            cons.append(
                f"Variant(s) in {', '.join(sorted(set(variant_without_evidence)))} "
                f"lack ClinVar or CIViC evidence — consider orthogonal validation."
            )

        # ── Confidence ────────────────────────────────────────────────────
        confidence = self._derive_confidence(variant_analyses, evidence)

        # ── Deduplicate references ────────────────────────────────────────
        seen_refs: set[tuple[str, str]] = set()
        unique_refs: list[dict[str, str]] = []
        for ref in all_references:
            key = (ref.get("source", ""), ref.get("citation", ""))
            if key not in seen_refs:
                seen_refs.add(key)
                unique_refs.append(ref)

        created_at = datetime.now(UTC).isoformat()

        return AgentOpinion(
            agent_type=self.agent_type,
            agent_version=self.agent_version,
            summary=summary,
            pros=pros,
            cons=cons,
            confidence=confidence,
            references=unique_refs,
            context_hash=context.context_hash or None,
            created_at=created_at,
        )

    # ── Private helpers ───────────────────────────────────────────────────

    @staticmethod
    def _analyse_single_variant(
        variant: dict[str, Any],
        evidence: EvidenceBundle,
        gene_symbol: str,
    ) -> dict[str, Any]:
        """Analyse one variant dict and return structured findings.

        Parameters
        ----------
        variant : dict
            A single variant entry from ``ClinicalContext.variants``.
        evidence : EvidenceBundle
            The aggregated evidence bundle.
        gene_symbol : str
            The gene symbol to cross-reference.

        Returns
        -------
        dict
            A dictionary with keys:
            - ``gene_symbol``
            - ``hgvs``
            - ``protein_change``
            - ``vaf``
            - ``recorded_significance``
            - ``aggregate_significance``
            - ``is_druggable``
            - ``has_civic_clinvar_evidence``
            - ``references``
        """
        hgvs = variant.get("hgvs", "") or ""
        protein_change = variant.get("protein_change", "") or ""
        vaf = variant.get("vaf")
        recorded_significance = variant.get("clinical_significance", "") or ""

        # ── Cross-reference evidence by gene ──────────────────────────────
        gene_evidence = evidence.by_gene.get(gene_symbol, [])

        civic_clinvar = [
            item
            for item in gene_evidence
            if item.source in _KNOWN_VARIANT_SOURCES
        ]

        has_civic_clinvar_evidence = bool(civic_clinvar)

        # ── Derive aggregate clinical significance ────────────────────────
        aggregate_significance = VariantAgent._derive_significance(
            recorded_significance=recorded_significance,
            evidence_items=civic_clinvar,
        )

        # ── Check druggability ────────────────────────────────────────────
        drug_evidence = [
            item
            for item in gene_evidence
            if item.drug_name and item.drug_name.strip()
        ]
        is_druggable = bool(drug_evidence)

        # ── Build references ──────────────────────────────────────────────
        references: list[dict[str, str]] = []
        for item in civic_clinvar:
            ref: dict[str, str] = {
                "source": item.source,
                "citation": item.citation or f"{item.source} record",
            }
            if item.url:
                ref["url"] = item.url
            if item.source_record_id:
                ref["source_record_id"] = item.source_record_id
            references.append(ref)

        for item in drug_evidence:
            if item not in civic_clinvar:
                ref = {
                    "source": item.source,
                    "citation": item.citation or f"{item.source} record",
                }
                if item.url:
                    ref["url"] = item.url
                references.append(ref)

        return {
            "gene_symbol": gene_symbol,
            "hgvs": hgvs,
            "protein_change": protein_change,
            "vaf": vaf,
            "recorded_significance": recorded_significance,
            "aggregate_significance": aggregate_significance,
            "is_druggable": is_druggable,
            "has_civic_clinvar_evidence": has_civic_clinvar_evidence,
            "references": references,
        }

    @staticmethod
    def _derive_significance(
        recorded_significance: str,
        evidence_items: list[Any],
    ) -> str:
        """Derive an aggregate clinical-significance label.

        The function first inspects the pre-recorded significance from the
        variant entry.  If that is empty or uninformative, it falls back
        to scanning the ``clinical_significance`` field of matching
        ClinVar / CIViC evidence items.

        The returned value is one of:
        ``"pathogenic"``, ``"likely_pathogenic"``, ``"VUS"``,
        ``"likely_benign"``, ``"benign"``, or ``"not_assessed"``.

        Parameters
        ----------
        recorded_significance : str
            The ``clinical_significance`` field from the variant dict.
        evidence_items : list of EvidenceItem
            ClinVar / CIViC evidence items for the same gene.

        Returns
        -------
        str
            The derived clinical significance label.
        """
        # ── Use recorded value if it is recognised ────────────────────────
        normalised = recorded_significance.lower().replace(" ", "_")
        if normalised in _CLINICAL_SIGNIFICANCE_ORDER:
            return normalised

        # ── Fall back to evidence items ───────────────────────────────────
        best_rank = len(_CLINICAL_SIGNIFICANCE_ORDER)
        best_label = "not_assessed"

        for item in evidence_items:
            if not item.clinical_significance:
                continue
            sig = item.clinical_significance.lower().replace(" ", "_")
            rank = _CLINICAL_SIGNIFICANCE_ORDER.get(sig, best_rank)
            if rank < best_rank:
                best_rank = rank
                best_label = sig

        return best_label

    @staticmethod
    def _derive_confidence(
        variant_analyses: list[dict[str, Any]],
        evidence: EvidenceBundle,
    ) -> str:
        """Derive an overall confidence level for the agent's opinion.

        Returns ``"high"`` when at least one variant has ClinVar / CIViC
        evidence **and** the evidence bundle contains items from multiple
        sources; ``"low"`` when no variant has ClinVar / CIViC evidence
        **and** the bundle is empty or very small; otherwise ``"medium"``.

        Parameters
        ----------
        variant_analyses : list[dict]
            Output of ``_analyse_single_variant`` for each variant.
        evidence : EvidenceBundle
            The full evidence bundle.

        Returns
        -------
        str
            ``"high"``, ``"medium"``, or ``"low"``.
        """
        any_variant_evidence = any(
            a.get("has_civic_clinvar_evidence") for a in variant_analyses
        )

        unique_sources = {
            item.source
            for item in evidence.items
            if item.source in _KNOWN_VARIANT_SOURCES
        }

        if any_variant_evidence and len(unique_sources) >= 2:
            return "high"

        if any_variant_evidence or evidence.total_count > 0:
            return "medium"

        return "low"

    @staticmethod
    def _build_empty_opinion(context: ClinicalContext) -> AgentOpinion:
        """Return a minimal opinion when there are no variants to analyse.

        Parameters
        ----------
        context : ClinicalContext
            The clinical context (used for ``context_hash``).

        Returns
        -------
        AgentOpinion
            An opinion stating that no variants were found.
        """
        created_at = datetime.now(UTC).isoformat()
        return AgentOpinion(
            agent_type="variant",
            agent_version="1.0.0",
            summary="No variants present in the clinical context to analyse.",
            pros=[],
            cons=[
                "No variant data available — consider comprehensive "
                "genomic profiling."
            ],
            confidence="medium",
            references=[],
            context_hash=context.context_hash or None,
            created_at=created_at,
        )


__all__ = [
    "VariantAgent",
]
