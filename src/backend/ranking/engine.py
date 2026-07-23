"""
DrugRankingEngine — orchestrates all scorers into final drug rankings.

All scores are deterministic and evidence-based. No LLM involvement.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from src.backend.ranking.models import (
    DrugRankingResult,
    DrugRankItem,
    ScoreBreakdown,
)
from src.backend.ranking.penalties import ConflictPenalty, UncertaintyPenalty
from src.backend.ranking.scorers import (
    ClinicalTrialScorer,
    EvidenceScorer,
    GuidelineScorer,
    RegulatoryScorer,
    ResistanceScorer,
    SensitivityScorer,
)

logger = logging.getLogger(__name__)


class DrugRankingEngine:
    """
    Orchestrates all scorers/penalties into final drug rankings.

    Usage:
        engine = DrugRankingEngine()
        result = await engine.rank(
            gene_symbol="BRAF",
            evidence_items=[...],
            drug_interactions=[...],
            disease="melanoma",
        )
    """

    def __init__(self):
        self.evidence_scorer = EvidenceScorer()
        self.resistance_scorer = ResistanceScorer()
        self.sensitivity_scorer = SensitivityScorer()
        self.guideline_scorer = GuidelineScorer()
        self.regulatory_scorer = RegulatoryScorer()
        self.clinical_trial_scorer = ClinicalTrialScorer()
        self.conflict_penalty = ConflictPenalty()
        self.uncertainty_penalty = UncertaintyPenalty()
        self.version = "0.5.0"

    async def rank(
        self,
        gene_symbol: str,
        evidence_items: list[dict],
        drug_interactions: list[dict],
        disease: str = "",
        variant_match_level: str = "gene_level_only",
        evidence_snapshot_id: str | None = None,
        source_versions: dict | None = None,
        git_commit: str = "",
    ) -> DrugRankingResult:
        """
        Rank drugs based on evidence.

        Steps:
        1. Collect all unique drug names from evidence + interactions
        2. For each drug, compute individual scores from all scorers
        3. Apply conflict/uncertainty penalties
        4. Compute total scores and sort
        5. Return ranked list
        """
        now = datetime.now(UTC)
        warnings = []
        errors = []

        # Collect unique drug names
        drug_map: dict[str, dict] = {}  # drug_name -> accumulated data

        # From evidence items
        for item in evidence_items:
            drug_name = (item.get("drug_name", "") or "").strip()
            if not drug_name:
                continue
            if drug_name not in drug_map:
                drug_map[drug_name] = {"evidence": [], "interactions": []}
            drug_map[drug_name]["evidence"].append(item)

        # From drug interactions
        for interaction in drug_interactions:
            drug_name = (interaction.get("drug_name", "") or "").strip()
            if not drug_name:
                continue
            if drug_name not in drug_map:
                drug_map[drug_name] = {"evidence": [], "interactions": []}
            drug_map[drug_name]["interactions"].append(interaction)

        if not drug_map:
            return DrugRankingResult(
                id=str(uuid.uuid4()),
                gene_symbol=gene_symbol,
                disease=disease,
                rankings=[],
                ranking_count=0,
                status="completed",
                warnings=["No drugs found for ranking"],
            )

        # Score each drug
        ranked_drugs: list[DrugRankItem] = []

        for drug_name, data in drug_map.items():
            ev_items = data["evidence"]

            # Evidence scoring
            ev_score, source_count, indep_sources, supporting_ids = self.evidence_scorer.score(
                drug_name, ev_items, match_level=variant_match_level,
            )

            # Resistance
            resistance_penalty, resistance_ids = self.resistance_scorer.score(drug_name, ev_items)

            # Sensitivity
            sensitivity_bonus = self.sensitivity_scorer.score(drug_name, ev_items)

            # Guideline
            guideline_bonus, has_guideline = self.guideline_scorer.score(drug_name, disease)

            # Regulatory
            regulatory_bonus, is_approved = self.regulatory_scorer.score(drug_name)

            # Clinical trial
            trial_bonus = self.clinical_trial_scorer.score(drug_name, ev_items)

            # Conflict penalty
            conflict_pen = self.conflict_penalty.apply(ev_items, drug_name)

            # Uncertainty penalty
            uncertainty_pen = self.uncertainty_penalty.apply(ev_items, drug_name)

            # Collect conflicting evidence IDs
            conflicting_ids = []
            for item in ev_items:
                item_drug = (item.get("drug_name", "") or "").strip().lower()
                if item_drug and item_drug != drug_name.lower():
                    continue
                direction = (item.get("evidence_direction", "") or "").lower()
                if direction in ("conflicting", "does not support"):
                    if item.get("id"):
                        conflicting_ids.append(str(item.get("id")))

            # Build score breakdown
            breakdown = ScoreBreakdown(
                evidence_score=round(ev_score, 4),
                sensitivity_score=round(sensitivity_bonus, 4),
                resistance_score=round(resistance_penalty, 4),
                guideline_score=round(guideline_bonus, 4),
                regulatory_score=round(regulatory_bonus, 4),
                clinical_trial_score=round(trial_bonus, 4),
                conflict_penalty=round(conflict_pen, 4),
                uncertainty_penalty=round(uncertainty_pen, 4),
            )

            total = round(breakdown.total(), 4)

            # Confidence
            if total >= 5.0 and source_count >= 2 and indep_sources >= 2:
                confidence = "high"
            elif total >= 2.0:
                confidence = "medium"
            elif total > 0:
                confidence = "low"
            else:
                confidence = "very_low"

            ranked_drugs.append(DrugRankItem(
                drug_name=drug_name,
                rank=0,  # Will be set after sorting
                total_score=total,
                score_breakdown=breakdown,
                supporting_evidence_ids=supporting_ids,
                conflicting_evidence_ids=conflicting_ids,
                resistance_evidence_ids=resistance_ids,
                disease_match="exact" if disease else "unknown",
                variant_match_scope=variant_match_level,
                source_count=source_count,
                independent_source_count=indep_sources,
                guideline_support=has_guideline,
                regulatory_approval=is_approved,
                confidence=confidence,
                limitations=[],
            ))

        # Sort by total_score descending, then by drug_name for stability
        ranked_drugs.sort(key=lambda d: (-d.total_score, d.drug_name))

        # Assign ranks
        for i, drug in enumerate(ranked_drugs):
            drug.rank = i + 1

        result_id = str(uuid.uuid4())

        return DrugRankingResult(
            id=result_id,
            gene_symbol=gene_symbol,
            disease=disease,
            rankings=ranked_drugs,
            ranking_count=len(ranked_drugs),
            ranking_algorithm_version=self.version,
            normalization_rule_version="1.0.0",
            evidence_snapshot_id=evidence_snapshot_id,
            source_versions=source_versions or {},
            git_commit=git_commit,
            status="completed",
            warnings=warnings,
            errors=errors,
            created_at=now.isoformat(),
        )
