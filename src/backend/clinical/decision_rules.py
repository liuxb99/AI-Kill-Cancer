"""
Decision Rule Set — data-driven rules for clinical decision type classification,
confidence calculation, alternative identification, contraindication detection,
and human-readable reason generation.

All rules are drug- and disease-agnostic — no specific drug names, cancer types,
or hardcoded thresholds are used.  Behaviour is driven entirely by the evidence
metadata (tiers, directions, sources) and the recommendation structure.

Provides
--------
- ``DecisionRuleSet`` — configurable rule set that the ``ClinicalDecisionEngine``
  uses to produce a ``ClinicalDecisionResult``.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# ── Tier-to-confidence mapping (data-driven) ──────────────────────────────
# Keys are evidence tier labels as they appear in the data; the list order
# represents descending strength.  Unknown tiers fall through to "insufficient".
_CONFIDENCE_BY_MAX_TIER: dict[str, str] = {
    "Tier_0": "high",
    "Tier_1": "high",
    "Tier_2": "medium",
    "Tier_3": "low",
    "Tier_4": "insufficient",
    "not_assessed": "insufficient",
}

# Decision types are ordered by clinical actionability (descending).
_DECISION_TYPES: list[str] = [
    "approved",
    "off_label",
    "clinical_trial",
    "contraindicated",
    "experimental",
    "not_recommended",
]


def _resolve_max_evidence_tier(evidence: list[dict]) -> str | None:
    """Return the *best* (most significant) evidence tier across *evidence*.

    Tiers are sorted by the order of keys in ``_CONFIDENCE_BY_MAX_TIER``;
    the first matching key is returned.  If no item carries a recognised
    tier, ``None`` is returned.
    """
    recognised = list(_CONFIDENCE_BY_MAX_TIER)
    best: str | None = None
    best_idx = len(recognised)  # worst possible index
    for item in evidence:
        tier = (item.get("evidence_level") or item.get("tier") or
                item.get("highest_tier") or "not_assessed")
        if tier in recognised:
            idx = recognised.index(tier)
            if idx < best_idx:
                best_idx = idx
                best = tier
    return best


def _extract_highest_tier_from_recommendation(recommendation: dict) -> str | None:
    """Walk the recommendation structure to find the best evidence tier."""
    # Check top-level keys first
    for key in ("highest_tier", "max_evidence_tier"):
        val = recommendation.get(key)
        if val and isinstance(val, str) and val in _CONFIDENCE_BY_MAX_TIER:
            return val

    # Drill into recommendations list
    drugs = recommendation.get("recommendations") or recommendation.get("drugs_ranked") or []
    if not drugs:
        drugs = [recommendation]  # maybe it is a single drug entry

    best: str | None = None
    best_idx = len(_CONFIDENCE_BY_MAX_TIER)
    for drug in drugs:
        # Look for evidence_score.evidence_score.highest_tier path
        ev_score = drug.get("evidence_score") or {}
        if isinstance(ev_score, dict):
            ht = ev_score.get("highest_tier")
        else:
            ht = None
        if ht and ht in _CONFIDENCE_BY_MAX_TIER:
            idx = list(_CONFIDENCE_BY_MAX_TIER).index(ht)
            if idx < best_idx:
                best_idx = idx
                best = ht
    return best


def _get_drug_name(entry: dict) -> str:
    """Extract a drug name from a rank/drug entry dict."""
    return entry.get("drug_name") or entry.get("name") or "Unknown drug"


# ═══════════════════════════════════════════════════════════════════════════════
# DecisionRuleSet
# ═══════════════════════════════════════════════════════════════════════════════


class DecisionRuleSet:
    """Configurable rule set for clinical decision classification.

    Each method implements a single aspect of the decision logic, making
    the set composable and testable in isolation.  All rules are
    data-driven — they inspect the evidence and recommendation structures
    rather than hardcoding specific drugs or diseases.

    Parameters
    ----------
    confidence_map : dict[str, str] | None
        Override mapping of evidence tier → confidence label.  Defaults to
        ``_CONFIDENCE_BY_MAX_TIER``.
    decision_type_order : list[str] | None
        Ordered list of recognised decision types (most actionable first).
        Defaults to ``_DECISION_TYPES``.
    """

    def __init__(
        self,
        confidence_map: dict[str, str] | None = None,
        decision_type_order: list[str] | None = None,
    ) -> None:
        self._confidence_map = confidence_map or dict(_CONFIDENCE_BY_MAX_TIER)
        self._decision_types = decision_type_order or list(_DECISION_TYPES)

    # ── Public API ─────────────────────────────────────────────────────────

    def determine_decision_type(
        self,
        recommendation: dict,
        evidence: list[dict],
    ) -> str:
        """Determine the clinical decision type for a recommendation.

        The method inspects evidence tiers, suggestion markers,
        contraindication flags, and drug-status indicators embedded in
        the recommendation and evidence structures.

        Decision types (from most to least actionable):

        - ``approved`` — strong evidence (Tier_0/1), no contraindication
          signals, and drug is marked as approved or is the top ranked.
        - ``off_label`` — evidence exists but drug not formally approved
          for this indication.
        - ``clinical_trial`` — recommendation or evidence explicitly
          references a clinical trial.
        - ``contraindicated`` — resistance or contraindication signals
          detected.
        - ``experimental`` — only weak / preclinical evidence.
        - ``not_recommended`` — insufficient or no evidence.

        Parameters
        ----------
        recommendation : dict
            The recommendation structure (output of
            ``RecommendationEngine.run()`` or a single drug-score dict).
        evidence : list[dict]
            List of evidence items considered for this decision.

        Returns
        -------
        str
            One of the recognised decision types.
        """
        # 1. Check for explicit contraindication / resistance markers
        if self._has_contraindication_signal(recommendation, evidence):
            return "contraindicated"

        # 2. Check for clinical-trial suggestion
        if self._has_clinical_trial_signal(recommendation, evidence):
            return "clinical_trial"

        # 3. Determine best evidence tier
        best_tier = self._resolve_tier(recommendation, evidence)

        # 4. Check drug-status markers
        drug_status = self._extract_drug_status(recommendation)

        # 5. Classify
        if best_tier in ("Tier_0", "Tier_1") and drug_status in ("approved", None):
            # Strong evidence → approved (unless explicitly marked otherwise)
            return "approved"

        if best_tier in ("Tier_0", "Tier_1") and drug_status == "off_label":
            return "off_label"

        if best_tier in ("Tier_2",) and drug_status != "contraindicated":
            return "off_label"

        if best_tier == "Tier_2" and drug_status == "experimental":
            return "clinical_trial"

        if best_tier in ("Tier_3",):
            return "experimental"

        if self._has_resistance_signal(evidence):
            return "contraindicated"

        return "not_recommended"

    def calculate_confidence(
        self,
        evidence: list[dict],
        recommendation: dict,
    ) -> str:
        """Calculate the confidence level for the decision.

        Confidence is derived from the highest (strongest) evidence tier
        found across both the evidence list and the recommendation structure.
        When multiple sources agree and there is no conflicting evidence,
        the confidence is elevated one level (e.g. ``medium`` → ``high``).

        Parameters
        ----------
        evidence : list[dict]
            List of evidence items.
        recommendation : dict
            The recommendation structure.

        Returns
        -------
        str
            One of ``"high"``, ``"medium"``, ``"low"``, ``"insufficient"``.
        """
        best_tier = self._resolve_tier(recommendation, evidence)
        base = self._confidence_map.get(best_tier or "not_assessed", "insufficient")

        # Elevate confidence when there is source consensus and no conflict
        if self._has_source_consensus(evidence) and not self._has_conflict(evidence):
            upgrade_map = {
                "insufficient": "low",
                "low": "medium",
                "medium": "high",
            }
            base = upgrade_map.get(base, base)

        # Downgrade confidence when there is significant conflict
        if self._has_conflict(evidence) and base == "high":
            base = "medium"

        return base

    def identify_alternatives(
        self,
        recommendation: dict,
    ) -> list[dict]:
        """Identify alternative drug options from the recommendation.

        Alternatives are the ranked drugs excluding the top-ranked one.
        Each alternative carries its rank, drug_name, overall_score, and
        an optional rationale placeholder.

        Parameters
        ----------
        recommendation : dict
            The recommendation structure.  Expected to contain either
            ``"recommendations"`` (list of drug-score dicts) or
            ``"drugs_ranked"`` (list of ranked drug dicts).

        Returns
        -------
        list[dict]
            Up to 5 alternative entries, each with keys ``drug_name``,
            ``rank``, ``overall_score``, and ``rationale``.  Empty list
            when there is only one drug or no ranked list.
        """
        drugs = self._extract_ranked_drugs(recommendation)
        if len(drugs) <= 1:
            return []

        # Top-ranked drug is the primary recommendation; everything else
        # is an alternative (up to 5 items).
        alternatives: list[dict] = []
        for entry in drugs[1:6]:  # top 5 alternatives max
            alternatives.append({
                "drug_name": _get_drug_name(entry),
                "rank": entry.get("rank", 0),
                "overall_score": entry.get("overall_score", 0.0),
                "rationale": (
                    f"Alternative #{entry.get('rank', '?')} — "
                    f"evidence score {entry.get('overall_score', 0.0):.4f}"
                ),
            })
        return alternatives

    def detect_contraindications(
        self,
        patient: dict | Any,
        variants: list[dict],
        recommendation: dict,
    ) -> list[dict]:
        """Detect contraindications for the recommended drugs.

        Contraindications can arise from:
        - Variants associated with resistance to a recommended drug.
        - Patient conditions (e.g. allergy, organ impairment) flagged in
          the patient data.
        - Evidence items with direction ``"resistance"`` or
          ``"contraindicated"`` that reference the top drug.

        Parameters
        ----------
        patient : dict | Any
            Patient data (may be a dict or an object with attributes like
            ``allergies``, ``current_medications``).
        variants : list[dict]
            List of variant dictionaries, each carrying at minimum
            ``gene_symbol`` and optionally ``clinical_significance``.
        recommendation : dict
            The recommendation structure.

        Returns
        -------
        list[dict]
            Each item has ``drug``, ``type`` (e.g. ``"variant_resistance"``,
            ``"allergy"``, ``"drug_interaction"``, ``"evidence_contraindication"``),
            ``detail``, and ``severity`` (``"high"`` | ``"medium"`` | ``"low"``).
            Empty list if no contraindications are found.
        """
        contraindications: list[dict] = []
        top_drug = self._get_top_drug_name(recommendation)
        if not top_drug:
            return []

        # 1. Variant-based resistance
        for v in variants:
            gene = v.get("gene_symbol") or v.get("gene") or ""
            sig = v.get("clinical_significance") or ""
            sig_lower = sig.lower()
            if any(word in sig_lower for word in ("resistance", "contraindicated", "poor_response")):
                contraindications.append({
                    "drug": top_drug,
                    "type": "variant_resistance",
                    "detail": (
                        f"Variant in {gene} has clinical significance "
                        f"'{sig}' indicating possible resistance to {top_drug}."
                    ),
                    "severity": "high",
                })

        # 2. Evidence-based contraindication signals
        ev_drugs = recommendation.get("recommendations") or recommendation.get("drugs_ranked") or []
        for ev in evidence:
            ev_drug = ev.get("drug_name") or ""
            direction = (ev.get("evidence_direction") or
                         ev.get("direction") or "")
            if ev_drug == top_drug and direction in ("resistance", "contraindicated"):
                contraindications.append({
                    "drug": top_drug,
                    "type": "evidence_contraindication",
                    "detail": (
                        f"Evidence from {ev.get('source', 'unknown')} indicates "
                        f"{direction} for {top_drug}."
                    ),
                    "severity": "medium",
                })
                break  # one evidence-level entry per drug is enough

        # 3. Patient allergies (if patient data is available)
        allergies: list[str] = []
        if isinstance(patient, dict):
            allergies = patient.get("allergies") or []
        elif hasattr(patient, "allergies"):
            allergies = list(getattr(patient, "allergies") or [])
        for allergy in allergies:
            allergy_lower = allergy.lower()
            if top_drug.lower() in allergy_lower or allergy_lower in top_drug.lower():
                contraindications.append({
                    "drug": top_drug,
                    "type": "allergy",
                    "detail": f"Patient has a documented allergy to '{allergy}' related to {top_drug}.",
                    "severity": "high",
                })

        return contraindications

    def generate_reason(
        self,
        decision_type: str,
        confidence: str,
        recommendation: dict,
        evidence: list[dict],
    ) -> str:
        """Generate a human-readable reason for the clinical decision.

        Parameters
        ----------
        decision_type : str
            The classified decision type.
        confidence : str
            The confidence level.
        recommendation : dict
            The recommendation structure.
        evidence : list[dict]
            The evidence items considered.

        Returns
        -------
        str
            A plain-English, multi-sentence explanation of the decision.
        """
        top_drug = self._get_top_drug_name(recommendation) or "the top-ranked drug"
        best_tier = self._resolve_tier(recommendation, evidence)
        ev_count = len(evidence)

        # Build the reason from parts
        parts: list[str] = []

        # Decision type heading
        type_labels = {
            "approved": f"Recommended: {top_drug} is supported by strong evidence.",
            "off_label": (
                f"Recommended (off-label): {top_drug} shows evidence of "
                f"efficacy, but is not formally approved for this indication."
            ),
            "clinical_trial": (
                f"Clinical Trial: {top_drug} should be considered in the "
                f"context of a clinical trial."
            ),
            "contraindicated": (
                f"Contraindicated: {top_drug} is not recommended due to "
                f"resistance or safety signals."
            ),
            "experimental": (
                f"Experimental: {top_drug} has only preclinical or "
                f"early-stage evidence."
            ),
            "not_recommended": (
                f"Not Recommended: insufficient evidence to support {top_drug}."
            ),
        }
        parts.append(type_labels.get(decision_type, f"Decision: {decision_type}."))

        # Evidence summary
        if best_tier:
            parts.append(
                f"The strongest evidence tier observed is {best_tier} "
                f"across {ev_count} evidence item(s)."
            )
        else:
            parts.append(f"No evidence tier information available ({ev_count} item(s) reviewed).")

        # Confidence statement
        parts.append(f"Overall confidence in this decision is **{confidence}**.")

        # Supporting sources
        source_set: set[str] = set()
        for item in evidence:
            src = item.get("source") or item.get("source_name") or ""
            if src:
                source_set.add(src)
        if source_set:
            sources_str = ", ".join(sorted(source_set))
            parts.append(f"Evidence sources reviewed: {sources_str}.")

        # Resistance / conflict note
        res_count = sum(
            1 for item in evidence
            if (item.get("evidence_direction") or item.get("direction")) in ("resistance", "contraindicated")
        )
        if res_count > 0:
            parts.append(
                f"Note: {res_count} evidence item(s) indicate resistance "
                f"or contraindication."
            )

        return " ".join(parts)

    # ── Internal helpers ───────────────────────────────────────────────────

    def _resolve_tier(self, recommendation: dict, evidence: list[dict]) -> str | None:
        """Resolve the best evidence tier from both sources."""
        tier_from_ev = _resolve_max_evidence_tier(evidence)
        tier_from_rec = _extract_highest_tier_from_recommendation(recommendation)
        recognised = list(self._confidence_map)
        best: str | None = None
        best_idx = len(recognised)
        for t in (tier_from_ev, tier_from_rec):
            if t and t in recognised:
                idx = recognised.index(t)
                if idx < best_idx:
                    best_idx = idx
                    best = t
        return best

    @staticmethod
    def _get_top_drug_name(recommendation: dict) -> str | None:
        """Return the name of the top-ranked drug, if any."""
        drugs = recommendation.get("recommendations") or recommendation.get("drugs_ranked") or []
        if drugs:
            return _get_drug_name(drugs[0])
        # Fallback: single drug entry
        if "drug_name" in recommendation:
            return recommendation["drug_name"]
        return None

    @staticmethod
    def _extract_ranked_drugs(recommendation: dict) -> list[dict]:
        """Extract the ranked drug list from a recommendation structure."""
        return (recommendation.get("recommendations") or
                recommendation.get("drugs_ranked") or
                ([recommendation] if "drug_name" in recommendation else []))

    @staticmethod
    def _extract_drug_status(recommendation: dict) -> str | None:
        """Extract a drug-status marker from the recommendation."""
        drugs = recommendation.get("recommendations") or recommendation.get("drugs_ranked") or []
        if drugs:
            return drugs[0].get("drug_status") or drugs[0].get("status") or None
        return recommendation.get("drug_status") or recommendation.get("status") or None

    @staticmethod
    def _has_contraindication_signal(recommendation: dict, evidence: list[dict]) -> bool:
        """Check for explicit contraindication markers."""
        # Recommendation-level flag
        if recommendation.get("decision_type") == "contraindicated":
            return True
        # Drug-level flag on top drug
        drugs = recommendation.get("recommendations") or recommendation.get("drugs_ranked") or []
        if drugs and drugs[0].get("drug_status") == "contraindicated":
            return True
        # Evidence with contraindicated direction
        for item in evidence:
            direction = (item.get("evidence_direction") or item.get("direction") or "")
            if direction == "contraindicated":
                return True
        return False

    @staticmethod
    def _has_clinical_trial_signal(recommendation: dict, evidence: list[dict]) -> bool:
        """Check for clinical-trial related signals."""
        if recommendation.get("decision_type") == "clinical_trial":
            return True
        drugs = recommendation.get("recommendations") or recommendation.get("drugs_ranked") or []
        if drugs and drugs[0].get("drug_status") == "clinical_trial":
            return True
        for item in evidence:
            source = (item.get("source") or "").lower()
            if "trial" in source or "trial" in (item.get("evidence_level") or "").lower():
                return True
        return False

    @staticmethod
    def _has_resistance_signal(evidence: list[dict]) -> bool:
        """Check if evidence contains resistance signals."""
        for item in evidence:
            direction = (item.get("evidence_direction") or item.get("direction") or "")
            if direction == "resistance":
                return True
        return False

    @staticmethod
    def _has_source_consensus(evidence: list[dict]) -> bool:
        """Check if multiple sources agree on the direction."""
        directions: set[str] = set()
        sources: set[str] = set()
        for item in evidence:
            d = (item.get("evidence_direction") or item.get("direction") or "")
            s = item.get("source") or item.get("source_name") or ""
            if d and s:
                directions.add(d)
                sources.add(s)
        # Consensus: at least 2 sources, all agreeing on the same direction
        return len(sources) >= 2 and len(directions) == 1

    @staticmethod
    def _has_conflict(evidence: list[dict]) -> bool:
        """Check if evidence contains conflicting directions."""
        directions: set[str] = set()
        for item in evidence:
            d = (item.get("evidence_direction") or item.get("direction") or "")
            if d:
                directions.add(d)
        # Conflict exists when both supporting and resistance/contraindicated
        # directions are present
        supportive = {"supporting", "sensitive", "responsive", ""}
        opposing = {"resistance", "contraindicated", "conflicting"}
        return bool(directions & supportive) and bool(directions & opposing)


__all__ = [
    "DecisionRuleSet",
]
