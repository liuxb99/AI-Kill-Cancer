"""
Drug Ranking System — evidence-based drug ranking with sensitivity, resistance,
conflict scoring, and overall score aggregation.

Provides a complete pipeline for ranking candidate drugs by clinical evidence
strength, incorporating:

- ``EvidenceScore``: weighted evidence strength from ``EvidenceAggregator``
- ``Sensitivity``: likelihood that the tumour responds to the drug
- ``Resistance``: penalises drugs with documented resistance evidence
- ``ConflictScore``: penalises drugs with contradictory evidence
- ``OverallScore``: composite score combining all sub-scores
- ``DrugRankingEngine``: orchestrates scoring and produces ranked results

All scoring uses configurable weight parameters — no hardcoded magic numbers.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

from src.backend.clinical.evidence_models import EvidenceItem

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# Scoring helpers
# ═══════════════════════════════════════════════════════════════════════════════

# Mapping from evidence-direction strings to numeric contribution.
# "supporting" adds positively to sensitivity; "resistance" adds to resistance;
# "conflicting" reduces confidence.
_DIRECTION_WEIGHTS: dict[str, float] = {
    "supporting": 1.0,
    "resistance": -1.0,
    "conflicting": -0.5,
    "neutral": 0.0,
    "unknown": 0.0,
    "": 0.0,
}


def _normalise_direction(direction: str) -> str:
    """Return a known direction key, defaulting to ``"unknown"``."""
    lower = direction.strip().lower()
    if lower in _DIRECTION_WEIGHTS:
        return lower
    # Fuzzy-match common variants
    if lower in ("sensitive", "responder", "responsive"):
        return "supporting"
    if lower in ("resistant", "non-responder", "non_responder"):
        return "resistance"
    if lower in ("conflict", "conflicting", "contradictory", "discrepant"):
        return "conflicting"
    return "unknown"


# ═══════════════════════════════════════════════════════════════════════════════
# EvidenceScore
# ═══════════════════════════════════════════════════════════════════════════════


class EvidenceScore(BaseModel):
    """Evidence-derived score for a single drug.

    Computed from the aggregated evidence data produced by
    ``EvidenceAggregator``.

    Attributes
    ----------
    total_weighted_score : float
        Sum of all weighted evidence scores for this drug (range 0.0–N).
    source_diversity : float
        Ratio of distinct evidence sources to total items (0.0–1.0).
        Higher values indicate evidence from multiple independent sources.
    highest_tier : str
        The best (highest) evidence tier observed (e.g. ``"Tier_0"``).
    confidence_score : float
        Composite confidence in [0.0, 1.0] derived from weight and diversity.
    """

    total_weighted_score: float = Field(default=0.0, ge=0.0)
    source_diversity: float = Field(default=0.0, ge=0.0, le=1.0)
    highest_tier: str = Field(default="Tier_4")
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)


def compute_evidence_score(
    drug_aggregate: dict[str, Any],
    *,
    diversity_weight: float = 0.3,
    weight_cap: float = 10.0,
) -> EvidenceScore:
    """Compute an ``EvidenceScore`` from a single drug's aggregated data.

    Parameters
    ----------
    drug_aggregate : dict
        A single entry from ``EvidenceAggregator.aggregate()`` output.
        Expected keys: ``evidence_scores``, ``total_weight``,
        ``source_count``, ``item_count``, ``highest_weight``, ``sources``.
    diversity_weight : float, optional
        How much source diversity contributes to the confidence score
        (default 0.3). The remainder (1 - diversity_weight) is
        contributed by the normalised total weight.
    weight_cap : float, optional
        Cap for total_weight normalisation (default 10.0). Weights above
        this value are clipped.

    Returns
    -------
    EvidenceScore
        The computed evidence score.
    """
    evidence_scores: list[dict] = drug_aggregate.get("evidence_scores", [])
    total_weight: float = drug_aggregate.get("total_weight", 0.0)
    source_count: int = drug_aggregate.get("source_count", 0)
    item_count: int = drug_aggregate.get("item_count", 0)
    highest_weight: float = drug_aggregate.get("highest_weight", 0.0)

    # Source diversity: ratio of distinct sources to total items
    source_diversity = 0.0
    if item_count > 0:
        source_diversity = min(source_count / item_count, 1.0)

    # Normalise total weight into [0, 1] using a configurable cap
    normalised_weight = min(total_weight / weight_cap, 1.0)

    # Confidence score = weighted combination of normalised weight + diversity
    weight_contribution = 1.0 - diversity_weight
    confidence_score = (
        weight_contribution * normalised_weight
        + diversity_weight * source_diversity
    )
    confidence_score = max(0.0, min(confidence_score, 1.0))

    # Determine highest tier from individual scores
    _TIER_ORDER: list[str] = [
        "Tier_0", "Tier_1", "Tier_2", "Tier_3", "Tier_4",
    ]
    highest_tier = "Tier_4"
    for entry in evidence_scores:
        tier = entry.get("tier", "Tier_4")
        if tier in _TIER_ORDER:
            if _TIER_ORDER.index(tier) < _TIER_ORDER.index(highest_tier):
                highest_tier = tier

    return EvidenceScore(
        total_weighted_score=total_weight,
        source_diversity=round(source_diversity, 4),
        highest_tier=highest_tier,
        confidence_score=round(confidence_score, 4),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Sensitivity
# ═══════════════════════════════════════════════════════════════════════════════


class Sensitivity(BaseModel):
    """Drug sensitivity score.

    Reflects the proportion and strength of evidence indicating that a
    tumour is likely to respond to the drug.

    Attributes
    ----------
    score : float
        Sensitivity score in [0.0, 1.0] (higher = more sensitive).
    supporting_item_count : int
        Number of evidence items with direction ``"supporting"``.
    total_item_count : int
        Total evidence items considered.
    details : str
        Human-readable explanation of the calculation.
    """

    score: float = Field(default=0.0, ge=0.0, le=1.0)
    supporting_item_count: int = Field(default=0, ge=0)
    total_item_count: int = Field(default=0, ge=0)
    details: str = ""


def compute_sensitivity(
    drug_name: str,
    evidence_scores: list[dict],
    *,
    supporting_bonus: float = 1.0,
    neutral_factor: float = 0.3,
) -> Sensitivity:
    """Calculate the sensitivity score for a drug.

    Sensitivity is computed as the weighted average of evidence items,
    where ``"supporting"`` direction items contribute fully, ``"neutral"``
    items contribute a fraction (``neutral_factor``), and conflicting or
    resistance items do not contribute positively.

    Parameters
    ----------
    drug_name : str
        Name of the drug (used for logging / details only).
    evidence_scores : list[dict]
        List of per-item score dicts. Each must contain ``direction``
        and ``weight`` keys.
    supporting_bonus : float, optional
        Weight multiplier for supporting evidence (default 1.0).
    neutral_factor : float, optional
        Fraction of weight assigned to neutral-direction items
        (default 0.3).

    Returns
    -------
    Sensitivity
        Computed sensitivity score.
    """
    if not evidence_scores:
        return Sensitivity(
            score=0.0,
            supporting_item_count=0,
            total_item_count=0,
            details=f"No evidence items found for {drug_name}.",
        )

    total_weight = 0.0
    supporting_weight = 0.0
    supporting_count = 0

    for entry in evidence_scores:
        direction = _normalise_direction(entry.get("direction", ""))
        weight = entry.get("weight", 0.0)

        if direction == "supporting":
            supporting_weight += weight * supporting_bonus
            supporting_count += 1
            total_weight += weight
        elif direction == "neutral":
            supporting_weight += weight * neutral_factor
            total_weight += weight
        elif direction == "unknown":
            # Unknown direction counts partially
            supporting_weight += weight * neutral_factor
            total_weight += weight
        # resistance and conflicting do not contribute positively

    score = 0.0
    if total_weight > 0:
        score = supporting_weight / total_weight
    score = max(0.0, min(score, 1.0))

    return Sensitivity(
        score=round(score, 4),
        supporting_item_count=supporting_count,
        total_item_count=len(evidence_scores),
        details=(
            f"Sensitivity for {drug_name}: {supporting_count}/{len(evidence_scores)} "
            f"items supporting, weighted score = {score:.4f}."
        ),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Resistance
# ═══════════════════════════════════════════════════════════════════════════════


class Resistance(BaseModel):
    """Drug resistance score.

    Reflects the proportion and strength of evidence indicating that a
    tumour is resistant to the drug.

    Attributes
    ----------
    score : float
        Resistance score in [0.0, 1.0] (higher = more resistant).
    resistance_item_count : int
        Number of evidence items with direction ``"resistance"``.
    total_item_count : int
        Total evidence items considered.
    details : str
        Human-readable explanation of the calculation.
    """

    score: float = Field(default=0.0, ge=0.0, le=1.0)
    resistance_item_count: int = Field(default=0, ge=0)
    total_item_count: int = Field(default=0, ge=0)
    details: str = ""


def compute_resistance(
    drug_name: str,
    evidence_scores: list[dict],
    *,
    resistance_penalty: float = 1.0,
) -> Resistance:
    """Calculate the resistance score for a drug.

    Resistance is computed as the proportion of total weight contributed
    by items with direction ``"resistance"``.  Items with
    ``clinical_significance`` containing ``"resistance"`` (or similar) are
    also counted as resistance evidence regardless of their direction field.

    Parameters
    ----------
    drug_name : str
        Name of the drug (used for logging / details only).
    evidence_scores : list[dict]
        List of per-item score dicts. Each may contain ``direction``,
        ``weight``, and ``clinical_significance`` keys.
    resistance_penalty : float, optional
        Weight multiplier for resistance items (default 1.0).

    Returns
    -------
    Resistance
        Computed resistance score.
    """
    if not evidence_scores:
        return Resistance(
            score=0.0,
            resistance_item_count=0,
            total_item_count=0,
            details=f"No evidence items found for {drug_name}.",
        )

    total_weight = 0.0
    resistance_weight = 0.0
    resistance_count = 0

    for entry in evidence_scores:
        direction = _normalise_direction(entry.get("direction", ""))
        weight = entry.get("weight", 0.0)
        clinical_sig = (entry.get("clinical_significance") or "").lower()

        # Also detect resistance from clinical_significance field
        is_resistance = direction == "resistance" or any(
            keyword in clinical_sig
            for keyword in ("resistance", "resistant", "non-response", "nonresponse")
        )

        if is_resistance:
            resistance_weight += weight * resistance_penalty
            resistance_count += 1

        total_weight += weight  # always accumulate total weight

    score = 0.0
    if total_weight > 0:
        score = resistance_weight / total_weight
    score = max(0.0, min(score, 1.0))

    return Resistance(
        score=round(score, 4),
        resistance_item_count=resistance_count,
        total_item_count=len(evidence_scores),
        details=(
            f"Resistance for {drug_name}: {resistance_count}/{len(evidence_scores)} "
            f"items indicating resistance, weighted score = {score:.4f}."
        ),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# ConflictScore
# ═══════════════════════════════════════════════════════════════════════════════


class ConflictScore(BaseModel):
    """Conflict score for a drug.

    Penalises drugs where evidence items contradict each other.

    Attributes
    ----------
    score : float
        Conflict penalty in [0.0, 1.0] (higher = more conflicting).
    conflicting_pairs : int
        Number of direction-conflicting pairs detected.
    total_items : int
        Total items considered.
    details : str
        Human-readable explanation.
    """

    score: float = Field(default=0.0, ge=0.0, le=1.0)
    conflicting_pairs: int = Field(default=0, ge=0)
    total_items: int = Field(default=0, ge=0)
    details: str = ""


def compute_conflict_score(
    evidence_scores: list[dict],
    *,
    conflict_threshold: float = 0.2,
) -> ConflictScore:
    """Calculate the conflict score for a drug's evidence set.

    A conflict is detected when the same drug has evidence items with
    opposing directions (e.g. ``"supporting"`` vs ``"resistance"``).
    The score is the proportion of item pairs that are conflicting,
    scaled by the weight of the conflicting items.

    Parameters
    ----------
    evidence_scores : list[dict]
        List of per-item score dicts. Each must contain ``direction``
        and ``weight`` keys.
    conflict_threshold : float, optional
        Minimum weight for an item to be considered in conflict detection
        (default 0.2). Items with weight below this threshold are ignored.

    Returns
    -------
    ConflictScore
        Computed conflict score.
    """
    if not evidence_scores or len(evidence_scores) < 2:
        return ConflictScore(
            score=0.0,
            conflicting_pairs=0,
            total_items=len(evidence_scores),
            details="Insufficient items for conflict analysis.",
        )

    # Classify items into direction buckets
    supporting: list[dict] = []
    resistance: list[dict] = []
    conflicting: list[dict] = []
    neutral: list[dict] = []

    for entry in evidence_scores:
        direction = _normalise_direction(entry.get("direction", ""))
        weight = entry.get("weight", 0.0)
        if weight < conflict_threshold:
            continue
        if direction == "supporting":
            supporting.append(entry)
        elif direction == "resistance":
            resistance.append(entry)
        elif direction == "conflicting":
            conflicting.append(entry)
        else:
            neutral.append(entry)

    # Count conflicting pairs (supporting ↔ resistance, or any conflicting)
    conflicting_pairs = (
        len(supporting) * len(resistance)
        + len(conflicting) * (len(supporting) + len(resistance) + len(conflicting) - 1)
    )

    total_pairs = len(evidence_scores) * (len(evidence_scores) - 1) / 2
    score = 0.0
    if total_pairs > 0:
        # Scale by the weight ratio of conflicting items
        total_weight_all = sum(e.get("weight", 0.0) for e in evidence_scores) or 1.0
        conflicting_weight = sum(
            e.get("weight", 0.0)
            for e in supporting + resistance + conflicting
        )
        weight_ratio = conflicting_weight / total_weight_all
        score = min(conflicting_pairs / total_pairs * weight_ratio, 1.0)

    return ConflictScore(
        score=round(score, 4),
        conflicting_pairs=conflicting_pairs,
        total_items=len(evidence_scores),
        details=(
            f"Conflict analysis: {conflicting_pairs} conflicting pair(s) "
            f"among {len(evidence_scores)} items, score = {score:.4f}."
        ),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# OverallScore
# ═══════════════════════════════════════════════════════════════════════════════


class OverallScore(BaseModel):
    """Composite overall score for a drug.

    Combines evidence, sensitivity, resistance (inverse), and conflict
    (inverse) into a single ranking score.

    ``overall = evidence_weight * evidence_score
              + sensitivity_weight * sensitivity_score
              - resistance_penalty * resistance_score
              - conflict_penalty * conflict_score``

    Attributes
    ----------
    raw_score : float
        Unclamped composite score.
    evidence_score_value : float
        Confidence score from ``EvidenceScore``.
    sensitivity_value : float
        Sensitivity score.
    resistance_value : float
        Resistance score.
    conflict_value : float
        Conflict score.
    """

    raw_score: float = Field(default=0.0)
    evidence_score_value: float = Field(default=0.0, ge=0.0, le=1.0)
    sensitivity_value: float = Field(default=0.0, ge=0.0, le=1.0)
    resistance_value: float = Field(default=0.0, ge=0.0, le=1.0)
    conflict_value: float = Field(default=0.0, ge=0.0, le=1.0)


def compute_overall_score(
    evidence_score: EvidenceScore,
    sensitivity: Sensitivity,
    resistance: Resistance,
    conflict: ConflictScore,
    *,
    evidence_weight: float = 0.40,
    sensitivity_weight: float = 0.35,
    resistance_penalty: float = 0.15,
    conflict_penalty: float = 0.10,
) -> OverallScore:
    """Compute the composite overall score for a drug.

    Parameters
    ----------
    evidence_score : EvidenceScore
        The evidence-derived score.
    sensitivity : Sensitivity
        The sensitivity score.
    resistance : Resistance
        The resistance score.
    conflict : ConflictScore
        The conflict score.
    evidence_weight : float, optional
        Weight of evidence score in the composite (default 0.40).
    sensitivity_weight : float, optional
        Weight of sensitivity score (default 0.35).
    resistance_penalty : float, optional
        Penalty multiplier for resistance (default 0.15).
    conflict_penalty : float, optional
        Penalty multiplier for conflict (default 0.10).

    Returns
    -------
    OverallScore
        The computed overall score.
    """
    raw_score = (
        evidence_weight * evidence_score.confidence_score
        + sensitivity_weight * sensitivity.score
        - resistance_penalty * resistance.score
        - conflict_penalty * conflict.score
    )

    return OverallScore(
        raw_score=round(raw_score, 4),
        evidence_score_value=round(evidence_score.confidence_score, 4),
        sensitivity_value=round(sensitivity.score, 4),
        resistance_value=round(resistance.score, 4),
        conflict_value=round(conflict.score, 4),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# DrugRankingResult (Pydantic model)
# ═══════════════════════════════════════════════════════════════════════════════


class DrugRankingResult(BaseModel):
    """Complete ranking result for a single drug.

    This is the primary output model for ``DrugRankingEngine``.

    Attributes
    ----------
    drug_name : str
        Name of the drug.
    overall_score : OverallScore
        Composite overall score.
    evidence_score : EvidenceScore
        Evidence-derived score.
    sensitivity : Sensitivity
        Sensitivity score.
    resistance : Resistance
        Resistance score.
    conflict_score : ConflictScore
        Conflict score.
    rank : int
        1-based overall rank.
    details : dict
        Additional detail fields for traceability.
    """

    drug_name: str
    overall_score: OverallScore
    evidence_score: EvidenceScore
    sensitivity: Sensitivity
    resistance: Resistance
    conflict_score: ConflictScore
    rank: int = Field(default=0, ge=0)
    details: dict = Field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════════════════════
# DrugRankingEngine
# ═══════════════════════════════════════════════════════════════════════════════


class DrugRankingEngine:
    """Orchestrates the full drug ranking pipeline.

    Takes aggregated evidence data (from ``EvidenceAggregator``) and optional
    variant information, computes all sub-scores for each drug, and returns
    a ranked list of ``DrugRankingResult`` instances.

    All scoring weights are configurable at construction time via keyword
    arguments, making the engine fully rule-driven.
    """

    def __init__(
        self,
        *,
        evidence_weight: float = 0.40,
        sensitivity_weight: float = 0.35,
        resistance_penalty: float = 0.15,
        conflict_penalty: float = 0.10,
        diversity_weight: float = 0.3,
        weight_cap: float = 10.0,
        supporting_bonus: float = 1.0,
        neutral_factor: float = 0.3,
        conflict_threshold: float = 0.2,
    ) -> None:
        """Initialise the drug ranking engine.

        Parameters
        ----------
        evidence_weight : float, optional
            Weight of evidence score in overall composite (default 0.40).
        sensitivity_weight : float, optional
            Weight of sensitivity in overall composite (default 0.35).
        resistance_penalty : float, optional
            Penalty multiplier for resistance (default 0.15).
        conflict_penalty : float, optional
            Penalty multiplier for conflict (default 0.10).
        diversity_weight : float, optional
            Source diversity contribution to confidence score (default 0.3).
        weight_cap : float, optional
            Cap for total-weight normalisation (default 10.0).
        supporting_bonus : float, optional
            Sensitivity multiplier for supporting evidence (default 1.0).
        neutral_factor : float, optional
            Sensitivity fraction for neutral-direction items (default 0.3).
        conflict_threshold : float, optional
            Minimum item weight for conflict detection (default 0.2).
        """
        self._evidence_weight = evidence_weight
        self._sensitivity_weight = sensitivity_weight
        self._resistance_penalty = resistance_penalty
        self._conflict_penalty = conflict_penalty
        self._diversity_weight = diversity_weight
        self._weight_cap = weight_cap
        self._supporting_bonus = supporting_bonus
        self._neutral_factor = neutral_factor
        self._conflict_threshold = conflict_threshold

    # ── Public API ─────────────────────────────────────────────────────────

    def rank(
        self,
        aggregated_data: dict[str, dict],
        variants: list[dict] | None = None,
        *,
        top_n: int | None = None,
    ) -> list[DrugRankingResult]:
        """Rank all drugs in the aggregated data.

        Parameters
        ----------
        aggregated_data : dict[str, dict]
            Output from ``EvidenceAggregator.aggregate()``.  Mapping of
            ``drug_name → aggregated dict``.
        variants : list[dict], optional
            List of variant dictionaries (reserved for future variant-aware
            scoring).  Each dict should contain at least ``gene_symbol``.
        top_n : int, optional
            If set, return only the top *N* results.

        Returns
        -------
        list[DrugRankingResult]
            Drugs sorted by overall score descending, each with full
            sub-score breakdowns.
        """
        _ = variants  # reserved for future variant-aware scoring
        results: list[DrugRankingResult] = []

        for drug_name, aggregate in aggregated_data.items():
            evidence_scores_list: list[dict] = aggregate.get("evidence_scores", [])

            # ── Compute sub-scores ────────────────────────────────────────
            evidence_score = compute_evidence_score(
                aggregate,
                diversity_weight=self._diversity_weight,
                weight_cap=self._weight_cap,
            )

            sensitivity = compute_sensitivity(
                drug_name,
                evidence_scores_list,
                supporting_bonus=self._supporting_bonus,
                neutral_factor=self._neutral_factor,
            )

            resistance = compute_resistance(
                drug_name,
                evidence_scores_list,
                resistance_penalty=self._resistance_penalty,
            )

            conflict = compute_conflict_score(
                evidence_scores_list,
                conflict_threshold=self._conflict_threshold,
            )

            overall = compute_overall_score(
                evidence_score,
                sensitivity,
                resistance,
                conflict,
                evidence_weight=self._evidence_weight,
                sensitivity_weight=self._sensitivity_weight,
                resistance_penalty=self._resistance_penalty,
                conflict_penalty=self._conflict_penalty,
            )

            results.append(
                DrugRankingResult(
                    drug_name=drug_name,
                    overall_score=overall,
                    evidence_score=evidence_score,
                    sensitivity=sensitivity,
                    resistance=resistance,
                    conflict_score=conflict,
                    details={
                        "item_count": aggregate.get("item_count", 0),
                        "source_count": aggregate.get("source_count", 0),
                        "highest_weight": aggregate.get("highest_weight", 0.0),
                        "sources": sorted(aggregate.get("sources", set())),
                    },
                )
            )

        # Sort by overall raw_score descending, then evidence_score descending
        results.sort(
            key=lambda r: (
                r.overall_score.raw_score,
                r.evidence_score.confidence_score,
            ),
            reverse=True,
        )

        # Assign 1-based ranks
        for idx, result in enumerate(results, 1):
            result.rank = idx

        # Apply top_n filter
        if top_n is not None and top_n > 0:
            results = results[:top_n]

        return results


__all__ = [
    "ConflictScore",
    "DrugRankingEngine",
    "DrugRankingResult",
    "EvidenceScore",
    "OverallScore",
    "Resistance",
    "Sensitivity",
    "compute_conflict_score",
    "compute_evidence_score",
    "compute_overall_score",
    "compute_resistance",
    "compute_sensitivity",
]
