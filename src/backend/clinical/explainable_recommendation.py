"""
Explainable Recommendation Engine — produces human-readable, traceable
explanations for each drug ranking produced by ``DrugRankingEngine``.

Each recommendation is decomposed into individual ``ReasonItem`` entries
that cover evidence support, sensitivity, resistance, conflict, and rule
triggers, enabling full auditability of the ranking decision.

Provides
--------
- ``ReasonItem`` — a single atomic explanation fragment.
- ``RecommendationReason`` — the complete explanation for one drug.
- ``ExplainableEngine`` — generates explanations from ranking results.
- ``ExplanationFormatter`` — renders explanations as plain text or HTML.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field

from src.backend.clinical.drug_ranking import DrugRankingResult


# ═══════════════════════════════════════════════════════════════════════════════
# ReasonItem
# ═══════════════════════════════════════════════════════════════════════════════


class ReasonItem(BaseModel):
    """A single atomic explanation fragment for one drug's ranking.

    Attributes
    ----------
    category : str
        The facet this reason belongs to. One of ``"evidence_support"``,
        ``"sensitivity"``, ``"resistance"``, ``"conflict"``, or ``"rule"``.
    detail : str
        Human-readable description of this reason (in English).
    source : str
        The evidence source or rule identifier that produced this reason.
    score_impact : float
        The numeric contribution (positive or negative) of this reason to
        the overall score.
    trace_id : str | None
        Optional UUID or reference that can be followed back to the
        originating evidence item or rule evaluation.
    """

    category: str = Field(
        ...,
        description=(
            "Facet: evidence_support | sensitivity | resistance | conflict | rule"
        ),
    )
    detail: str = Field(
        ...,
        description="Human-readable explanation of this reason.",
    )
    source: str = Field(
        ...,
        description="Evidence source name or rule identifier.",
    )
    score_impact: float = Field(
        ...,
        description="Numeric contribution (positive or negative) to the score.",
    )
    trace_id: Optional[str] = Field(
        default=None,
        description="Optional UUID or reference for traceability.",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# RecommendationReason
# ═══════════════════════════════════════════════════════════════════════════════


class RecommendationReason(BaseModel):
    """Complete explanation for a single drug's ranking.

    Attributes
    ----------
    drug_name : str
        Name of the drug.
    rank : int
        1-based rank position.
    overall_score : float
        The composite overall score (``raw_score``).
    reasons : list[ReasonItem]
        Ordered list of explanation fragments that together justify the
        rank.  The first items are the most impactful (positive or negative).
    """

    drug_name: str = Field(
        ...,
        description="Drug name.",
    )
    rank: int = Field(
        ...,
        ge=0,
        description="1-based rank position.",
    )
    overall_score: float = Field(
        ...,
        description="Composite overall score (raw_score).",
    )
    reasons: list[ReasonItem] = Field(
        default_factory=list,
        description="Ordered list of explanation fragments.",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# ExplainableEngine
# ═══════════════════════════════════════════════════════════════════════════════


class ExplainableEngine:
    """Generates structured, traceable explanations for drug ranking results.

    The engine analyses each ``DrugRankingResult`` and the original
    aggregated evidence data to produce a set of ``ReasonItem`` entries
    that cover:

    - **Evidence support** — which sources contributed and at what weight.
    - **Sensitivity** — how much supporting evidence exists.
    - **Resistance** — evidence of resistance and its penalty.
    - **Conflict** — contradictory evidence among sources.
    - **Rank context** — why this drug is first (or second, etc.) relative
      to adjacent ranks.

    Parameters
    ----------
    ranking_engine : DrugRankingEngine | None
        The ``DrugRankingEngine`` instance used to produce the rankings.
        When provided, its configuration weights (evidence_weight,
        sensitivity_weight, resistance_penalty, conflict_penalty) are
        included in explanations for full traceability.
    aggregated_data : dict[str, dict] | None
        The original output of ``EvidenceAggregator.aggregate()``, keyed
        by drug name.  When provided, per-item evidence details are
        available for richer explanations.
    """

    def __init__(
        self,
        ranking_engine: Any | None = None,
        aggregated_data: dict[str, dict] | None = None,
    ) -> None:
        """Initialise the explainable engine.

        Parameters
        ----------
        ranking_engine : DrugRankingEngine | None, optional
            The ranking engine instance whose configuration weights should
            be reflected in explanations.
        aggregated_data : dict[str, dict] | None, optional
            Raw aggregated evidence data for per-item detail.
        """
        self._ranking_engine = ranking_engine
        self._aggregated_data = aggregated_data or {}

        # Extract configuration weights if a ranking engine is provided
        if ranking_engine is not None:
            self._evidence_weight: float = getattr(
                ranking_engine, "_evidence_weight", 0.40
            )
            self._sensitivity_weight: float = getattr(
                ranking_engine, "_sensitivity_weight", 0.35
            )
            self._resistance_penalty: float = getattr(
                ranking_engine, "_resistance_penalty", 0.15
            )
            self._conflict_penalty: float = getattr(
                ranking_engine, "_conflict_penalty", 0.10
            )
        else:
            self._evidence_weight = 0.40
            self._sensitivity_weight = 0.35
            self._resistance_penalty = 0.15
            self._conflict_penalty = 0.10

    # ── Public API ─────────────────────────────────────────────────────────

    def generate_explanations(
        self,
        ranking_results: list[DrugRankingResult],
    ) -> list[RecommendationReason]:
        """Generate structured explanations for every ranked drug.

        Parameters
        ----------
        ranking_results : list[DrugRankingResult]
            The ranked results produced by ``DrugRankingEngine.rank()``.

        Returns
        -------
        list[RecommendationReason]
            One ``RecommendationReason`` per drug, in the same order as
            *ranking_results*.
        """
        explanations: list[RecommendationReason] = []

        for idx, result in enumerate(ranking_results):
            reasons: list[ReasonItem] = []

            # ── Evidence-support items ─────────────────────────────────────
            reasons.extend(self._build_evidence_support_reasons(result))

            # ── Sensitivity reasons ────────────────────────────────────────
            reasons.extend(self._build_sensitivity_reasons(result))

            # ── Resistance reasons ─────────────────────────────────────────
            reasons.extend(self._build_resistance_reasons(result))

            # ── Conflict reasons ───────────────────────────────────────────
            reasons.extend(self._build_conflict_reasons(result))

            # ── Rank-context reasons ───────────────────────────────────────
            reasons.extend(
                self._build_rank_context_reasons(result, idx, ranking_results)
            )

            # Sort by absolute score_impact descending (most impactful first)
            reasons.sort(key=lambda r: abs(r.score_impact), reverse=True)

            explanations.append(
                RecommendationReason(
                    drug_name=result.drug_name,
                    rank=result.rank,
                    overall_score=result.overall_score.raw_score,
                    reasons=reasons,
                )
            )

        return explanations

    # ── Internal builders ──────────────────────────────────────────────────

    def _build_evidence_support_reasons(
        self,
        result: DrugRankingResult,
    ) -> list[ReasonItem]:
        """Build reasons describing the evidence support for a drug."""
        reasons: list[ReasonItem] = []
        ev = result.evidence_score

        # Summarise the evidence strength
        reasons.append(
            ReasonItem(
                category="evidence_support",
                detail=(
                    f"Evidence confidence score is {ev.confidence_score:.4f} "
                    f"(weighted score {ev.total_weighted_score:.2f}, "
                    f"source diversity {ev.source_diversity:.2f})."
                ),
                source="EvidenceAggregator",
                score_impact=round(
                    self._evidence_weight * ev.confidence_score, 4
                ),
            )
        )

        # Per-source contributions from aggregated_data if available
        details: dict = result.details
        sources: list[str] = details.get("sources", [])
        if sources:
            reasons.append(
                ReasonItem(
                    category="evidence_support",
                    detail=(
                        f"Evidence contributed by {len(sources)} source(s): "
                        f"{', '.join(sources)}."
                    ),
                    source="EvidenceAggregator",
                    score_impact=0.0,
                )
            )

        # If we have per-item detail in aggregated_data, add top items
        drug_agg = self._aggregated_data.get(result.drug_name)
        if drug_agg is not None:
            evidence_scores_list: list[dict] = drug_agg.get("evidence_scores", [])
            # Show top-3 highest-weight items
            sorted_items = sorted(
                evidence_scores_list,
                key=lambda x: x.get("weight", 0.0),
                reverse=True,
            )
            for item in sorted_items[:3]:
                source = item.get("source", "unknown")
                weight = item.get("weight", 0.0)
                tier = item.get("tier", "not_assessed")
                direction = item.get("direction", "unknown")
                clinical_sig = item.get("clinical_significance", "")
                detail_parts = [
                    f"Weight {weight:.4f} from {source} "
                    f"(tier: {tier}, direction: {direction})"
                ]
                if clinical_sig:
                    detail_parts.append(f" — {clinical_sig}")
                reasons.append(
                    ReasonItem(
                        category="evidence_support",
                        detail="".join(detail_parts),
                        source=source,
                        score_impact=round(weight, 4),
                        trace_id=item.get("source_record_id"),
                    )
                )

        return reasons

    def _build_sensitivity_reasons(
        self,
        result: DrugRankingResult,
    ) -> list[ReasonItem]:
        """Build reasons describing the sensitivity of a drug."""
        sens = result.sensitivity
        reasons: list[ReasonItem] = []

        impact = round(self._sensitivity_weight * sens.score, 4)
        reasons.append(
            ReasonItem(
                category="sensitivity",
                detail=(
                    f"Sensitivity score {sens.score:.4f} — "
                    f"{sens.supporting_item_count}/{sens.total_item_count} "
                    f"evidence items indicate sensitivity."
                ),
                source="DrugRankingEngine",
                score_impact=impact,
            )
        )

        if sens.details:
            reasons.append(
                ReasonItem(
                    category="sensitivity",
                    detail=sens.details,
                    source="DrugRankingEngine",
                    score_impact=0.0,
                )
            )

        return reasons

    def _build_resistance_reasons(
        self,
        result: DrugRankingResult,
    ) -> list[ReasonItem]:
        """Build reasons describing resistance evidence for a drug."""
        res = result.resistance
        reasons: list[ReasonItem] = []

        if res.score > 0:
            impact = round(-self._resistance_penalty * res.score, 4)
            reasons.append(
                ReasonItem(
                    category="resistance",
                    detail=(
                        f"Resistance score {res.score:.4f} — "
                        f"{res.resistance_item_count}/{res.total_item_count} "
                        f"evidence items indicate resistance. "
                        f"Penalty applied: {impact:.4f}."
                    ),
                    source="DrugRankingEngine",
                    score_impact=impact,
                )
            )
            if res.details:
                reasons.append(
                    ReasonItem(
                        category="resistance",
                        detail=res.details,
                        source="DrugRankingEngine",
                        score_impact=0.0,
                    )
                )
        else:
            reasons.append(
                ReasonItem(
                    category="resistance",
                    detail="No resistance evidence detected.",
                    source="DrugRankingEngine",
                    score_impact=0.0,
                )
            )

        return reasons

    def _build_conflict_reasons(
        self,
        result: DrugRankingResult,
    ) -> list[ReasonItem]:
        """Build reasons describing conflicting evidence for a drug."""
        conflict = result.conflict_score
        reasons: list[ReasonItem] = []

        if conflict.score > 0:
            impact = round(-self._conflict_penalty * conflict.score, 4)
            reasons.append(
                ReasonItem(
                    category="conflict",
                    detail=(
                        f"Conflict score {conflict.score:.4f} — "
                        f"{conflict.conflicting_pairs} conflicting pair(s) "
                        f"detected among {conflict.total_items} items. "
                        f"Penalty applied: {impact:.4f}."
                    ),
                    source="DrugRankingEngine",
                    score_impact=impact,
                )
            )
            if conflict.details:
                reasons.append(
                    ReasonItem(
                        category="conflict",
                        detail=conflict.details,
                        source="DrugRankingEngine",
                        score_impact=0.0,
                    )
                )
        else:
            reasons.append(
                ReasonItem(
                    category="conflict",
                    detail="No conflicting evidence detected.",
                    source="DrugRankingEngine",
                    score_impact=0.0,
                )
            )

        return reasons

    def _build_rank_context_reasons(
        self,
        result: DrugRankingResult,
        idx: int,
        all_results: list[DrugRankingResult],
    ) -> list[ReasonItem]:
        """Build reasons that contextualise the rank position."""
        reasons: list[ReasonItem] = []

        if result.rank == 1 and len(all_results) > 1:
            # Compare with the second-place drug
            second = all_results[1]
            diff = round(
                result.overall_score.raw_score
                - second.overall_score.raw_score,
                4,
            )
            reasons.append(
                ReasonItem(
                    category="rule",
                    detail=(
                        f"Ranked #1 — leads {second.drug_name} (#2) by "
                        f"{diff:.4f} points in overall score."
                    ),
                    source="DrugRanker",
                    score_impact=diff,
                )
            )
        elif result.rank > 1:
            # Compare with the drug immediately above
            higher = all_results[idx - 1]
            diff = round(
                higher.overall_score.raw_score
                - result.overall_score.raw_score,
                4,
            )
            reasons.append(
                ReasonItem(
                    category="rule",
                    detail=(
                        f"Ranked #{result.rank} — trails "
                        f"{higher.drug_name} (#{higher.rank}) by "
                        f"{diff:.4f} points."
                    ),
                    source="DrugRanker",
                    score_impact=-diff,
                )
            )

        # Sub-score breakdown
        os = result.overall_score
        reasons.append(
            ReasonItem(
                category="rule",
                detail=(
                    f"Score breakdown — evidence: {os.evidence_score_value:.4f} "
                    f"(×{self._evidence_weight}), "
                    f"sensitivity: {os.sensitivity_value:.4f} "
                    f"(×{self._sensitivity_weight}), "
                    f"resistance: {os.resistance_value:.4f} "
                    f"(×-{self._resistance_penalty}), "
                    f"conflict: {os.conflict_value:.4f} "
                    f"(×-{self._conflict_penalty})."
                ),
                source="DrugRankingEngine",
                score_impact=0.0,
            )
        )

        return reasons


# ═══════════════════════════════════════════════════════════════════════════════
# ExplanationFormatter
# ═══════════════════════════════════════════════════════════════════════════════


class ExplanationFormatter:
    """Renders ``RecommendationReason`` instances as text or HTML.

    Usage::

        formatter = ExplanationFormatter()
        text = formatter.format_text(reason)
        html = formatter.format_html(reason)
    """

    @staticmethod
    def format_text(reason: RecommendationReason) -> str:
        """Format a recommendation reason as human-readable plain text.

        Parameters
        ----------
        reason : RecommendationReason
            The structured explanation to format.

        Returns
        -------
        str
            Multi-line plain-text explanation.
        """
        lines: list[str] = [
            f"Drug: {reason.drug_name}",
            f"Rank: #{reason.rank}",
            f"Overall Score: {reason.overall_score:.4f}",
            "",
            "Explanation:",
        ]

        for i, item in enumerate(reason.reasons, 1):
            category_tag = f"[{item.category.upper()}]"
            impact_str = (
                f"{item.score_impact:+.4f}"
                if item.score_impact != 0.0
                else "  0.0000"
            )
            lines.append(
                f"  {i:2d}. {category_tag:22s} {impact_str}  {item.detail}"
            )
            if item.source:
                lines[-1] += f"  (source: {item.source})"
            if item.trace_id:
                lines[-1] += f"  [trace: {item.trace_id}]"

        return "\n".join(lines)

    @staticmethod
    def format_html(reason: RecommendationReason) -> str:
        """Format a recommendation reason as an HTML fragment.

        Parameters
        ----------
        reason : RecommendationReason
            The structured explanation to format.

        Returns
        -------
        str
            HTML ``<div>`` fragment suitable for embedding in a page.
        """
        items_html = ""
        for item in reason.reasons:
            category_class = item.category.replace("_", "-")
            impact_str = (
                f"{item.score_impact:+.4f}"
                if item.score_impact != 0.0
                else "0.0000"
            )
            trace_html = (
                f' <span class="trace-id">[trace: {item.trace_id}]</span>'
                if item.trace_id
                else ""
            )
            items_html += (
                f'<div class="reason-item reason-{category_class}">\n'
                f'  <span class="reason-category">[{item.category}]</span>\n'
                f'  <span class="reason-impact">{impact_str}</span>\n'
                f'  <span class="reason-detail">{item.detail}</span>\n'
                f'  <span class="reason-source">(source: {item.source})</span>'
                f'{trace_html}\n'
                f'</div>\n'
            )

        html = (
            f'<div class="recommendation-reason">\n'
            f'  <h3 class="drug-name">{reason.drug_name}</h3>\n'
            f'  <p class="rank-info">Rank: #{reason.rank} | '
            f'Overall Score: {reason.overall_score:.4f}</p>\n'
            f'  <div class="reasons-list">\n'
            f'{items_html}'
            f'  </div>\n'
            f'</div>\n'
        )
        return html


__all__ = [
    "ExplainableEngine",
    "ExplanationFormatter",
    "ReasonItem",
    "RecommendationReason",
]
