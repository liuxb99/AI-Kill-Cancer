"""
Clinical Decision Engine — rule-based engine that transforms recommendation
pipeline output, evidence, patient data, and variant information into a
structured clinical decision.

The engine applies ``DecisionRuleSet`` rules to:
1. Classify the decision type (approved / off_label / clinical_trial / etc.)
2. Calculate confidence (high / medium / low / insufficient)
3. Identify alternative drug options
4. Detect contraindications (variant resistance, allergies, evidence signals)
5. Generate a human-readable reason and evidence summary
6. Package everything into a ``ClinicalDecisionResult``

All logic is data-driven — no hardcoded drug names, diseases, or thresholds.
"""

from __future__ import annotations

import logging
from typing import Any

from src.backend.clinical.decision_rules import DecisionRuleSet

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# ClinicalDecisionResult
# ═══════════════════════════════════════════════════════════════════════════════


class ClinicalDecisionResult:
    """Structured output of the Clinical Decision Engine.

    Attributes
    ----------
    decision_type : str
        One of ``"approved"``, ``"off_label"``, ``"clinical_trial"``,
        ``"contraindicated"``, ``"experimental"``, ``"not_recommended"``.
    reason : str
        Human-readable multi-sentence explanation of the decision.
    evidence_summary : dict
        Structured summary with ``total_evidence_count``,
        ``best_evidence_tier``, ``sources``, and ``direction_breakdown``.
    confidence : str
        One of ``"high"``, ``"medium"``, ``"low"``, ``"insufficient"``.
    alternatives : list[dict]
        Alternative drug options (ranked 2nd and below). Each entry
        contains ``drug_name``, ``rank``, ``overall_score``, and
        ``rationale``.
    contraindications : list[dict]
        Contraindication signals. Each entry contains ``drug``, ``type``,
        ``detail``, and ``severity``.
    """

    def __init__(
        self,
        decision_type: str,
        reason: str,
        evidence_summary: dict,
        confidence: str,
        alternatives: list[dict] | None = None,
        contraindications: list[dict] | None = None,
    ) -> None:
        """Initialise the clinical decision result.

        Parameters
        ----------
        decision_type : str
            The classified decision type.
        reason : str
            Human-readable explanation.
        evidence_summary : dict
            Structured evidence summary.
        confidence : str
            Confidence level.
        alternatives : list[dict], optional
            Alternative drug options (default ``[]``).
        contraindications : list[dict], optional
            Contraindication signals (default ``[]``).
        """
        self.decision_type = decision_type
        self.reason = reason
        self.evidence_summary = evidence_summary
        self.confidence = confidence
        self.alternatives = alternatives or []
        self.contraindications = contraindications or []

    def to_dict(self) -> dict:
        """Return a dictionary representation of the result.

        Returns
        -------
        dict
            Dictionary with keys matching the attribute names, suitable
            for JSON serialisation.
        """
        return {
            "decision_type": self.decision_type,
            "reason": self.reason,
            "evidence_summary": self.evidence_summary,
            "confidence": self.confidence,
            "alternatives": self.alternatives,
            "contraindications": self.contraindications,
        }

    def __repr__(self) -> str:
        return (
            f"<ClinicalDecisionResult(decision_type={self.decision_type!r}, "
            f"confidence={self.confidence!r}, "
            f"alternatives={len(self.alternatives)}, "
            f"contraindications={len(self.contraindications)})>"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# ClinicalDecisionEngine
# ═══════════════════════════════════════════════════════════════════════════════


class ClinicalDecisionEngine:
    """Rule-based engine that produces a structured clinical decision.

    The engine consumes the output of the recommendation pipeline, along
    with raw evidence, patient data, and variant information, and applies
    ``DecisionRuleSet`` rules to produce a ``ClinicalDecisionResult``.

    The evaluation pipeline follows these steps:

    1. Extract top drug, scores, and evidence from the recommendation.
    2. Use ``DecisionRuleSet.determine_decision_type()`` to classify.
    3. Use ``DecisionRuleSet.calculate_confidence()`` for confidence.
    4. Use ``DecisionRuleSet.identify_alternatives()`` for alternatives.
    5. Use ``DecisionRuleSet.detect_contraindications()`` for safety signals.
    6. Build the evidence summary dictionary.
    7. Use ``DecisionRuleSet.generate_reason()`` for human-readable text.
    8. Package everything into ``ClinicalDecisionResult``.

    Parameters
    ----------
    rule_set : DecisionRuleSet | None
        The rule set to use for classification.  When ``None`` a default
        ``DecisionRuleSet`` is created.
    """

    def __init__(
        self,
        rule_set: DecisionRuleSet | None = None,
    ) -> None:
        """Initialise the clinical decision engine.

        Parameters
        ----------
        rule_set : DecisionRuleSet | None, optional
            Custom rule set instance.  Defaults to a fresh
            ``DecisionRuleSet()``.
        """
        self._rule_set = rule_set or DecisionRuleSet()

    # ── Public API ─────────────────────────────────────────────────────────

    async def evaluate(
        self,
        patient: dict | Any,
        variants: list[dict],
        evidence: list[dict],
        recommendation: dict | Any,
    ) -> ClinicalDecisionResult:
        """Evaluate the full clinical decision for a patient.

        Parameters
        ----------
        patient : dict | Any
            Patient data.  May be a plain dict or any object with
            ``allergies``, ``current_medications``, etc. as attributes.
        variants : list[dict]
            List of variant dictionaries.  Each should contain at minimum
            ``gene_symbol`` and optionally ``clinical_significance``.
        evidence : list[dict]
            List of evidence items considered for this decision.  Each
            should contain ``drug_name``, ``source``, ``evidence_level`` /
            ``tier``, and ``evidence_direction`` / ``direction``.
        recommendation : dict | Any
            The recommendation structure produced by the recommendation
            pipeline.  Expected to contain either ``recommendations`` or
            ``drugs_ranked`` (list of scored drug dicts), or be a single
            drug-score dict itself.

        Returns
        -------
        ClinicalDecisionResult
            The structured clinical decision with all fields populated.

        Raises
        ------
        ValueError
            If *recommendation* is empty or cannot be parsed.
        """
        # ── Step 0: Normalise inputs ─────────────────────────────────────
        if isinstance(recommendation, dict):
            rec_dict = recommendation
        else:
            # Assume it is an object with a ``to_dict()`` or ``model_dump()``
            rec_dict = self._to_dict(recommendation)

        ev_list = list(evidence) if evidence else []
        v_list = list(variants) if variants else []

        # ── Step 1: Extract top drug info ────────────────────────────────
        top_drug_name = self._rule_set._get_top_drug_name(rec_dict)
        if not top_drug_name:
            raise ValueError(
                "Cannot determine the top recommended drug from the "
                "recommendation structure.  Ensure it contains a "
                "'recommendations' or 'drugs_ranked' list with at least "
                "one entry carrying a 'drug_name' key."
            )

        # ── Step 2: Classify decision type ───────────────────────────────
        decision_type = self._rule_set.determine_decision_type(
            recommendation=rec_dict,
            evidence=ev_list,
        )

        # ── Step 3: Calculate confidence ─────────────────────────────────
        confidence = self._rule_set.calculate_confidence(
            evidence=ev_list,
            recommendation=rec_dict,
        )

        # ── Step 4: Identify alternatives ────────────────────────────────
        alternatives = self._rule_set.identify_alternatives(
            recommendation=rec_dict,
        )

        # ── Step 5: Detect contraindications ─────────────────────────────
        contraindications = self._rule_set.detect_contraindications(
            patient=patient,
            variants=v_list,
            recommendation=rec_dict,
            evidence=ev_list,
        )

        # ── Step 6: Build evidence summary ───────────────────────────────
        evidence_summary = self._build_evidence_summary(
            top_drug_name=top_drug_name,
            evidence=ev_list,
            recommendation=rec_dict,
        )

        # ── Step 7: Generate reason ──────────────────────────────────────
        reason = self._rule_set.generate_reason(
            decision_type=decision_type,
            confidence=confidence,
            recommendation=rec_dict,
            evidence=ev_list,
        )

        # ── Step 8: Assemble result ──────────────────────────────────────
        return ClinicalDecisionResult(
            decision_type=decision_type,
            reason=reason,
            evidence_summary=evidence_summary,
            confidence=confidence,
            alternatives=alternatives,
            contraindications=contraindications,
        )

    # ── Internal helpers ─────────────────────────────────────────────────

    @staticmethod
    def _to_dict(obj: Any) -> dict:
        """Convert an arbitrary object to a dict if possible."""
        if isinstance(obj, dict):
            return obj
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        if hasattr(obj, "to_dict"):
            return obj.to_dict()
        if hasattr(obj, "__dict__"):
            return vars(obj)
        return {"_raw": str(obj)}

    @staticmethod
    def _get_top_drug_entry(recommendation: dict) -> dict:
        """Return the top-ranked drug entry from the recommendation."""
        drugs = (recommendation.get("recommendations") or
                 recommendation.get("drugs_ranked") or [])
        if drugs:
            return dict(drugs[0])
        if "drug_name" in recommendation:
            return recommendation
        return {}

    @staticmethod
    def _build_evidence_summary(
        top_drug_name: str,
        evidence: list[dict],
        recommendation: dict,
    ) -> dict:
        """Build the structured evidence summary dictionary.

        The summary includes total count, best evidence tier, distinct
        sources, and a direction breakdown (supporting / resistance /
        conflicting / neutral).

        Parameters
        ----------
        top_drug_name : str
            Name of the top recommended drug.
        evidence : list[dict]
            List of evidence items.
        recommendation : dict
            The recommendation structure.

        Returns
        -------
        dict
            Structured evidence summary.
        """
        # Count evidence items that pertain to the top drug
        drug_evidence = [
            item for item in evidence
            if (item.get("drug_name") or "").lower() == top_drug_name.lower()
        ] or evidence  # fallback: use all evidence if none match by drug name

        total_count = len(drug_evidence)

        # Determine best tier
        recognised = ["Tier_0", "Tier_1", "Tier_2", "Tier_3", "Tier_4", "not_assessed"]
        best_tier: str = "not_assessed"
        best_idx = len(recognised)

        for item in drug_evidence:
            tier = (item.get("evidence_level") or item.get("tier") or
                    item.get("highest_tier") or "not_assessed")
            if tier in recognised:
                idx = recognised.index(tier)
                if idx < best_idx:
                    best_idx = idx
                    best_tier = tier

        # Also check recommendation structure
        rec_tier = None
        ev_score = recommendation.get("evidence_score") or {}
        if isinstance(ev_score, dict):
            rec_tier = ev_score.get("highest_tier")
        if rec_tier and rec_tier in recognised:
            idx = recognised.index(rec_tier)
            if idx < best_idx:
                best_idx = idx
                best_tier = rec_tier

        # Distinct sources
        sources: set[str] = set()
        for item in drug_evidence:
            src = item.get("source") or item.get("source_name") or ""
            if src:
                sources.add(src)

        # Direction breakdown
        direction_counts: dict[str, int] = {
            "supporting": 0,
            "resistance": 0,
            "conflicting": 0,
            "neutral": 0,
        }
        for item in drug_evidence:
            direction = (item.get("evidence_direction") or
                         item.get("direction") or "neutral")
            d_lower = direction.lower()
            if d_lower in ("supporting", "sensitive", "responsive"):
                direction_counts["supporting"] += 1
            elif d_lower in ("resistance", "resistant"):
                direction_counts["resistance"] += 1
            elif d_lower in ("conflicting", "conflict"):
                direction_counts["conflicting"] += 1
            else:
                direction_counts["neutral"] += 1

        return {
            "total_evidence_count": total_count,
            "best_evidence_tier": best_tier,
            "sources": sorted(sources),
            "direction_breakdown": direction_counts,
        }


__all__ = [
    "ClinicalDecisionEngine",
    "ClinicalDecisionResult",
]
