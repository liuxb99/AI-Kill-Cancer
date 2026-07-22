"""
ClinicalTrialAgent — matches available clinical trials against a patient's
clinical context and evidence bundle.

The agent filters clinical-trial evidence items from the evidence bundle,
scores their relevance based on cancer type, disease stage, genomic variants,
and biomarkers, and also considers patient eligibility criteria (age,
performance status, metastatic sites) to produce a structured opinion.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, TYPE_CHECKING

from src.backend.agents.base import BaseAgent
from src.backend.agents.models import AgentOpinion
from src.backend.clinical.evidence_models import EvidenceBundle
from src.backend.clinical.models import ClinicalContext

if TYPE_CHECKING:
    from src.backend.clinical.evidence_models import EvidenceItem

logger = logging.getLogger(__name__)

# ── Matching constants ───────────────────────────────────────────────────────

_TRIAL_SOURCES: tuple[str, ...] = (
    "clinicaltrials",
    "clinical_trials",
    "ClinicalTrials.gov",
)
"""Source identifiers that indicate an evidence item originates from a
clinical trial registry."""

_PHASE_PRECEDENCE: list[str] = [
    "Phase 1",
    "Phase 1/Phase 2",
    "Phase 2",
    "Phase 2/Phase 3",
    "Phase 3",
    "Phase 4",
]
"""Ordered list of trial phases from earliest to most mature."""


def _phase_rank(phase: str) -> int:
    """Return a numeric rank for a trial phase (higher = more mature).

    Parameters
    ----------
    phase : str
        The trial phase label (e.g. ``"Phase 2"``, ``"Phase 3"``).

    Returns
    -------
    int
        Positional rank in ``_PHASE_PRECEDENCE``, or ``-1`` for
        unrecognised phases.
    """
    for i, p in enumerate(_PHASE_PRECEDENCE):
        if phase.strip().lower() == p.lower():
            return i
    return -1


def _is_trial_item(item: EvidenceItem) -> bool:
    """Return ``True`` if the evidence item originates from a clinical trial
    registry.

    Checks the ``source`` field against known trial-source identifiers,
    and also inspects the ``evidence_type`` field as a fallback.

    Parameters
    ----------
    item : EvidenceItem
        The evidence item to check.

    Returns
    -------
    bool
        ``True`` if the item is recognised as clinical-trial evidence.
    """
    source = (item.source or "").strip().lower()
    if source in {s.lower() for s in _TRIAL_SOURCES}:
        return True
    etype = (item.evidence_type or "").strip().lower()
    if "trial" in etype or "clinical study" in etype:
        return True
    return False


def _match_cancer_type(
    item: EvidenceItem,
    cancer_type: str,
) -> bool:
    """Check whether an evidence item's disease / condition field matches
    the patient's cancer type.

    Performs a case-insensitive substring match on ``item.disease``.

    Parameters
    ----------
    item : EvidenceItem
        The evidence item to evaluate.
    cancer_type : str
        The patient's cancer type (e.g. ``"Lung Adenocarcinoma"``).

    Returns
    -------
    bool
        ``True`` if the item likely targets the patient's cancer type.
    """
    if not cancer_type:
        return True  # no cancer type to match — pass through
    disease = (item.disease or "").strip().lower()
    target = cancer_type.strip().lower()
    if not disease:
        return False
    # Exact substring match: the trial condition should contain the
    # cancer type or a well-known synonym.
    return target in disease or disease in target


def _match_gene_variant(
    item: EvidenceItem,
    variants: list[dict],
) -> bool:
    """Check whether the evidence item's gene matches any of the patient's
    variants.

    Parameters
    ----------
    item : EvidenceItem
        The evidence item to evaluate.
    variants : list[dict]
        Patient variants, each expected to contain a ``gene_symbol`` key.

    Returns
    -------
    bool
        ``True`` if at least one patient variant matches the item's gene.
    """
    item_gene = (item.gene_symbol or "").strip().lower()
    if not item_gene:
        return False
    return any(
        (v.get("gene_symbol") or "").strip().lower() == item_gene
        for v in variants
    )


def _match_biomarker(
    item: EvidenceItem,
    biomarkers: list[dict],
) -> bool:
    """Check whether the evidence item refers to a relevant biomarker.

    Compares ``item.gene_symbol`` and ``item.description`` against the
    biomarker entries provided in the clinical context.

    Parameters
    ----------
    item : EvidenceItem
        The evidence item to evaluate.
    biomarkers : list[dict]
        Patient biomarkers, each expected to contain at least a ``name``
        or ``gene`` key.

    Returns
    -------
    bool
        ``True`` if a biomarker match is found.
    """
    item_gene = (item.gene_symbol or "").strip().lower()
    item_desc = (item.description or "").strip().lower()
    for bm in biomarkers:
        name = (bm.get("name") or bm.get("gene") or "").strip().lower()
        if name and (name == item_gene or name in item_desc):
            return True
    return False


def _assess_eligibility(
    context: ClinicalContext,
) -> tuple[bool, list[str]]:
    """Evaluate a patient's general eligibility for interventional trials.

    Performs heuristic checks based on the patient's age, ECOG score,
    metastatic status, and recurrence status.  Because
    ``EvidenceItem`` does not carry structured eligibility fields, the
    assessment is broad and flags only the most common exclusion
    criteria.

    Parameters
    ----------
    context : ClinicalContext
        The patient's clinical context.

    Returns
    -------
    tuple[bool, list[str]]
        A two-element tuple where the first value is ``True`` if the
        patient is potentially eligible, and the second is a list of
        human-readable eligibility notes.
    """
    notes: list[str] = []
    potentially_ineligible = False

    # Age check — many trials have upper or lower age limits.
    if context.age < 18:
        notes.append(
            f"Patient is {context.age} years old; many trials require age ≥ 18."
        )
        potentially_ineligible = True
    elif context.age > 75:
        notes.append(
            f"Patient is {context.age} years old; some trials exclude age > 75."
        )

    # ECOG performance status.
    if context.ecog_score is not None and context.ecog_score > 2:
        notes.append(
            f"ECOG score is {context.ecog_score}; many trials require ECOG 0–2."
        )
        potentially_ineligible = True

    # Metastatic status.
    if context.metastatic_sites:
        notes.append(
            "Patient has metastatic disease "
            f"({', '.join(context.metastatic_sites)})."
        )
    else:
        notes.append("No metastatic sites recorded.")

    # Recurrence.
    if context.recurrence_status:
        notes.append(f"Recurrence status: {context.recurrence_status}.")

    # Rough trial-phase suitability based on disease stage.
    stage_lower = (context.stage or "").strip().lower()
    if stage_lower in ("stage iv", "advanced", "metastatic"):
        notes.append(
            "Advanced / Stage IV disease — late-phase (Phase 3/4) trials "
            "may be most appropriate."
        )
    elif stage_lower and "early" not in stage_lower:
        notes.append(
            f"Disease stage is {context.stage} — suitability depends on "
            "each trial's protocol."
        )

    eligible = not potentially_ineligible
    return eligible, notes


def _calculate_match_score(
    item: EvidenceItem,
    context: ClinicalContext,
) -> float:
    """Calculate a normalised relevance score for a trial evidence item.

    The score considers cancer-type match, gene/variant match, biomarker
    match, evidence level, and aggregate trial-phase maturity.

    Parameters
    ----------
    item : EvidenceItem
        The trial evidence item to score.
    context : ClinicalContext
        The patient's clinical context.

    Returns
    -------
    float
        A score between ``0.0`` and ``1.0`` (higher = better match).
    """
    score = 0.0

    # Cancer-type match (weight: 0–40 %).
    if _match_cancer_type(item, context.cancer_type):
        score += 0.4

    # Gene / variant match (weight: 0–25 %).
    if _match_gene_variant(item, context.variants):
        score += 0.25
    elif _match_biomarker(item, context.biomarkers):
        score += 0.15  # weaker biomarker-only match

    # Evidence-level bonus (weight: 0–20 %).
    level = (item.evidence_level or "").strip()
    level_bonus = {"A": 0.20, "B": 0.15, "C": 0.10, "D": 0.05}
    score += level_bonus.get(level, 0.0)

    # Trial-phase maturity (weight: 0–15 %).
    desc = (item.description or "").lower()
    for phase in _PHASE_PRECEDENCE:
        if phase.lower() in desc:
            rank = _phase_rank(phase)
            if rank >= 0:
                score += 0.15 * (rank / max(len(_PHASE_PRECEDENCE) - 1, 1))
            break

    return min(score, 1.0)


class ClinicalTrialAgent(BaseAgent):
    """Agent that matches clinical trials to a patient's clinical context.

    This agent filters the ``EvidenceBundle`` for clinical-trial records,
    scores their relevance against the patient's cancer type, genomic
    variants, and biomarkers, considers broad eligibility criteria, and
    returns a structured ``AgentOpinion`` with matching trials and a
    supporting rationale.

    Parameters
    ----------
    db : AsyncSession
        SQLAlchemy asynchronous database session.
    """

    agent_type: str = "clinical_trial"
    """Identifier for this agent type."""

    agent_version: str = "1.0.0"
    """Semantic version of the implementation."""

    async def analyze(
        self,
        context: ClinicalContext,
        evidence: EvidenceBundle,
    ) -> AgentOpinion:
        """Match clinical trials against the patient's clinical context.

        The analysis proceeds in three stages:

        1. **Filter** — extract ``EvidenceItem`` records from the bundle
           that originate from a clinical-trial registry.
        2. **Score & match** — for each trial item, compute a relevance
           score based on cancer type, stage, variants, biomarkers,
           evidence level, and trial phase.
        3. **Eligibility** — evaluate general patient eligibility based
           on age, ECOG score, metastatic status, and recurrence.
        4. **Assemble** — build the final ``AgentOpinion`` with a summary,
           pros/cons, confidence rating, and references.

        Parameters
        ----------
        context : ClinicalContext
            Frozen patient / case snapshot including diagnosis, biomarkers,
            variants, treatment history, and performance status.
        evidence : EvidenceBundle
            Aggregated evidence items from all configured knowledge sources
            (including clinical-trial registries).

        Returns
        -------
        AgentOpinion
            The agent's structured opinion containing matched clinical
            trials and supporting rationale.
        """
        # ── Stage 1: Filter trial items ─────────────────────────────────┬
        trial_items = [item for item in evidence.items if _is_trial_item(item)]

        if not trial_items:
            return AgentOpinion(
                agent_type=self.agent_type,
                agent_version=self.agent_version,
                summary=(
                    "No clinical-trial records were found in the evidence "
                    "bundle. The available knowledge sources did not return "
                    "any studies matching the patient's profile."
                ),
                confidence="low",
                created_at=datetime.now(timezone.utc).isoformat(),
                context_hash=context.context_hash or None,
            )

        # ── Stage 2: Score and rank ─────────────────────────────────────┬
        scored: list[tuple[float, EvidenceItem]] = []
        for item in trial_items:
            score = _calculate_match_score(item, context)
            scored.append((score, item))

        scored.sort(key=lambda x: x[0], reverse=True)
        top_trials = scored[:10]  # keep top 10

        # ── Stage 3: Eligibility assessment ─────────────────────────────┬
        eligible, _eligibility_notes = _assess_eligibility(context)

        # ── Stage 4: Assemble AgentOpinion ──────────────────────────────┬

        # Summary
        summary_lines: list[str] = [
            f"Evaluated {len(trial_items)} clinical-trial record(s) "
            f"for {context.cancer_type or 'unknown cancer type'} "
            f"(stage: {context.stage or 'not specified'})."
        ]

        if top_trials:
            best_score = top_trials[0][0]
            summary_lines.append(
                f"Top match score: {best_score:.0%}. "
                f"Recommended trials are listed in the references."
            )
        else:
            summary_lines.append(
                "No trial records achieved a meaningful relevance score."
            )

        summary = " ".join(summary_lines)

        # Pros
        pros: list[str] = []
        if top_trials:
            pros.append(
                f"Found {len(top_trials)} potentially relevant trial(s) "
                f"after filtering and scoring."
            )
            if best_score >= 0.7:
                pros.append(
                    "High-scoring match(es) identified — strong alignment "
                    "between patient profile and trial inclusion criteria."
                )
            if any(_match_gene_variant(item, context.variants) for _, item in top_trials):
                pros.append(
                    "At least one trial targets a genomic variant present "
                    "in the patient's tumour."
                )
            if any(_match_biomarker(item, context.biomarkers) for _, item in top_trials):
                pros.append(
                    "Biomarker-matched trial(s) available — may increase "
                    "likelihood of therapeutic benefit."
                )
        else:
            pros.append(
                "The evidence bundle was searched; no clinical-trial "
                "records were retrieved from the available sources."
            )

        # Cons
        cons: list[str] = []
        if not eligible:
            cons.append(
                "The patient may not meet common eligibility criteria "
                "based on age, ECOG score, or disease status."
            )
        if context.stage and context.stage.lower() in ("stage iv", "advanced"):
            cons.append(
                "Advanced-stage disease may limit trial options; many "
                "studies focus on earlier lines of therapy."
            )
        if context.ecog_score is not None and context.ecog_score > 2:
            cons.append(
                "Reduced performance status (ECOG > 2) is an exclusion "
                "criterion for many interventional trials."
            )
        if not top_trials:
            cons.append(
                "No trial records matched after scoring — consider "
                "broadening the search to nearby cancer types or "
                "gene-agnostic basket trials."
            )
        else:
            cons.append(
                f"Only {len(top_trials)} trial(s) passed the relevance "
                f"threshold; the available trial evidence may be limited "
                f"for this specific profile."
            )

        # References
        references: list[dict[str, Any]] = []
        seen_nct: set[str] = set()
        for score, item in top_trials:
            nct = (item.source_record_id or "").strip()
            dedup_key = nct or item.description or ""
            if dedup_key in seen_nct:
                continue
            seen_nct.add(dedup_key)

            ref: dict[str, Any] = {
                "source": item.source or "clinicaltrials",
                "citation": item.description or item.source_record_id or "Unknown trial",
                "url": item.url or "",
            }
            ref["match_score"] = round(score, 4)
            if item.gene_symbol:
                ref["gene"] = item.gene_symbol
            if item.drug_name:
                ref["drug"] = item.drug_name
            if item.evidence_level:
                ref["evidence_level"] = item.evidence_level
            references.append(ref)

        # Confidence
        if not trial_items:
            confidence = "low"
        elif best_score >= 0.7:
            confidence = "high"
        elif best_score >= 0.4:
            confidence = "medium"
        else:
            confidence = "low"

        opinion = AgentOpinion(
            agent_type=self.agent_type,
            agent_version=self.agent_version,
            summary=summary,
            pros=pros,
            cons=cons,
            confidence=confidence,
            references=references,
            context_hash=context.context_hash or None,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        # Validate before returning
        validation_errors = self.validate_opinion(opinion)
        if validation_errors:
            logger.warning(
                "ClinicalTrialAgent produced an opinion with validation "
                "errors: %s",
                "; ".join(validation_errors),
            )

        return opinion


__all__ = [
    "ClinicalTrialAgent",
]
