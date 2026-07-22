"""
GuidelineAgent — clinical guideline analysis agent.

Analyses clinical guideline recommendations (NCCN, ESMO, ASCO) against a
patient's clinical context.  Matches guideline evidence items by cancer
type, disease stage, and biomarkers, evaluates standard-of-care
recommendations relative to the patient's specific situation (age,
performance status, prior treatments, comorbidities), and returns a
structured ``AgentOpinion``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.backend.agents.base import BaseAgent
from src.backend.agents.models import AgentOpinion
from src.backend.clinical.evidence_models import EvidenceBundle
from src.backend.clinical.models import ClinicalContext

# ── Guideline source identifiers ──────────────────────────────────────────────

_GUIDELINE_SOURCES: tuple[str, ...] = (
    "NCCN",
    "ESMO",
    "ASCO",
)
"""Recognised clinical-guideline knowledge sources."""

# ── Stage-level mapping ───────────────────────────────────────────────────────

_STAGE_ORDER: dict[str, int] = {
    "stage 0": 0,
    "stage i": 1,
    "stage ia": 1,
    "stage ib": 1,
    "stage ii": 2,
    "stage iia": 2,
    "stage iib": 2,
    "stage iii": 3,
    "stage iiia": 3,
    "stage iiib": 3,
    "stage iiic": 3,
    "stage iv": 4,
    "advanced": 4,
    "metastatic": 4,
}
"""Numeric ordering of cancer stages for guideline matching."""


def _stage_rank(stage: str) -> int:
    """Return a numeric rank for a cancer stage (higher = more advanced).

    Parameters
    ----------
    stage : str
        The clinical stage label (e.g. ``"Stage II"``, ``"Stage IV"``).

    Returns
    -------
    int
        Positional rank in ``_STAGE_ORDER``, or ``-1`` for unrecognised
        stages.
    """
    normalized = stage.strip().lower().replace(" ", "")
    for key, rank in _STAGE_ORDER.items():
        if key.replace(" ", "") == normalized:
            return rank
    return -1


def _is_guideline_item(item: Any) -> bool:
    """Return ``True`` if the evidence item originates from a clinical
    guideline source.

    Parameters
    ----------
    item : EvidenceItem
        The evidence item to check.

    Returns
    -------
    bool
        ``True`` if the item's source is a recognised guideline body.
    """
    source = (item.source or "").strip().lower()
    return source in {s.lower() for s in _GUIDELINE_SOURCES}


def _match_cancer_type(
    item_disease: str | None,
    cancer_type: str,
) -> bool:
    """Check whether a guideline item's disease matches the patient's
    cancer type.

    Performs a case-insensitive substring match on the item's ``disease``
    (or ``description``) field against the patient's ``cancer_type``.

    Parameters
    ----------
    item_disease : str | None
        The disease field from the evidence item.
    cancer_type : str
        The patient's cancer type.

    Returns
    -------
    bool
        ``True`` if the guideline item likely applies to this cancer type.
    """
    if not cancer_type:
        return True
    disease = (item_disease or "").strip().lower()
    target = cancer_type.strip().lower()
    if not disease:
        return False
    return target in disease or disease in target


def _match_stage(
    item_disease: str | None,
    item_description: str | None,
    stage: str,
) -> bool:
    """Check whether a guideline item's scope includes the patient's
    disease stage.

    Looks for stage keywords in the item's ``disease`` and ``description``
    fields and compares them to the patient's stage.

    Parameters
    ----------
    item_disease : str | None
        The disease field from the evidence item.
    item_description : str | None
        The description / recommendation text.
    stage : str
        The patient's clinical stage.

    Returns
    -------
    bool
        ``True`` if the guideline item is relevant for this stage.
    """
    if not stage:
        return True  # no stage to match — pass through
    patient_rank = _stage_rank(stage)
    if patient_rank < 0:
        return True  # cannot determine — do not exclude

    # Collect stage-related text from the item
    text_parts: list[str] = []
    if item_disease:
        text_parts.append(item_disease)
    if item_description:
        text_parts.append(item_description)
    combined = " ".join(text_parts).lower()

    # Broad stage categories
    if patient_rank <= 1:  # Stage 0–I (early)
        if any(kw in combined for kw in ("early", "stage i", "stage 0", "localised")):
            return True
    elif patient_rank <= 3:  # Stage II–III (locally advanced)
        if any(kw in combined for kw in ("stage ii", "stage iii", "locally advanced")):
            return True
    else:  # Stage IV / advanced / metastatic
        if any(kw in combined for kw in ("stage iv", "advanced", "metastatic")):
            return True

    # If no stage-specific keywords found, assume the guideline applies broadly
    return True


def _match_biomarker(
    item_gene: str | None,
    item_description: str | None,
    biomarkers: list[dict],
) -> bool:
    """Check whether a guideline item references any of the patient's
    biomarkers.

    Parameters
    ----------
    item_gene : str | None
        The gene_symbol from the evidence item.
    item_description : str | None
        The description / recommendation text.
    biomarkers : list[dict]
        Patient biomarkers, each expected to contain at least a ``name``
        or ``gene`` key.

    Returns
    -------
    bool
        ``True`` if at least one patient biomarker is referenced.
    """
    if not biomarkers:
        return False

    item_gene_lower = (item_gene or "").strip().lower()
    item_desc_lower = (item_description or "").strip().lower()

    for bm in biomarkers:
        bm_name = (bm.get("name") or bm.get("gene") or "").strip().lower()
        if not bm_name:
            continue
        if bm_name == item_gene_lower or bm_name in item_desc_lower:
            return True
    return False


def _evaluate_patient_factors(
    context: ClinicalContext,
) -> list[str]:
    """Evaluate patient-specific factors that may affect guideline
    concordance.

    Checks age, ECOG performance status, prior treatment history,
    and comorbidities documented in clinical notes.

    Parameters
    ----------
    context : ClinicalContext
        The patient's clinical context.

    Returns
    -------
    list[str]
        Human-readable notes about factors that may influence guideline
        applicability.
    """
    notes: list[str] = []

    # Age considerations
    if context.age < 18:
        notes.append(
            f"Patient is {context.age} years old — most standard guidelines "
            f"address adult populations."
        )
    elif context.age > 75:
        notes.append(
            f"Patient is {context.age} years old — guideline regimens may "
            f"require dose adjustment or modified schedules."
        )

    # ECOG performance status
    if context.ecog_score is not None:
        if context.ecog_score > 2:
            notes.append(
                f"ECOG {context.ecog_score} — reduced performance status may "
                f"contraindicate standard intensive regimens recommended by "
                f"guidelines."
            )
        elif context.ecog_score >= 1:
            notes.append(
                f"ECOG {context.ecog_score} — consider modified guideline "
                f"recommendations for patients with mild impairment."
            )

    # Prior treatment history
    if context.treatment_history:
        prior_lines = len(context.treatment_history)
        notes.append(
            f"Patient has received {prior_lines} prior line(s) of therapy — "
            f"guideline recommendations for later-line treatment may differ "
            f"from first-line options."
        )

    # Comorbidity keywords in clinical notes
    if context.clinical_notes:
        notes_lower = context.clinical_notes.lower()
        comorbidity_flags: list[str] = []
        if any(kw in notes_lower for kw in ("liver", "hepatic", "cirrhosis")):
            comorbidity_flags.append("hepatic impairment")
        if any(kw in notes_lower for kw in ("kidney", "renal", "ckd", "dialysis")):
            comorbidity_flags.append("renal impairment")
        if "cardiac" in notes_lower or "heart" in notes_lower:
            comorbidity_flags.append("cardiac comorbidity")
        if "diabetes" in notes_lower:
            comorbidity_flags.append("diabetes")
        if comorbidity_flags:
            notes.append(
                f"Comorbidity noted: {', '.join(comorbidity_flags)} — may "
                f"affect guideline-concordant drug selection."
            )

    return notes


# ── Agent implementation ──────────────────────────────────────────────────────


class GuidelineAgent(BaseAgent):
    """Agent that analyses clinical guideline recommendations against a
    patient's clinical context.

    This agent filters the ``EvidenceBundle`` for items originating from
    recognised clinical guideline bodies (NCCN, ESMO, ASCO), matches them
    against the patient's cancer type, disease stage, and biomarkers,
    evaluates patient-specific factors that may affect guideline
    concordance, and returns a structured ``AgentOpinion`` with the
    assessment.

    Parameters
    ----------
    db : AsyncSession
        SQLAlchemy asynchronous database session.
    """

    agent_type: str = "guideline"
    """Identifier for this agent type."""

    agent_version: str = "1.0.0"
    """Semantic version of the implementation."""

    async def analyze(
        self,
        context: ClinicalContext,
        evidence: EvidenceBundle,
    ) -> AgentOpinion:
        """Analyse clinical guideline recommendations for the given
        clinical context.

        The analysis proceeds in four stages:

        1. **Filter** — extract ``EvidenceItem`` records from the bundle
           that originate from clinical-guideline sources (NCCN, ESMO,
           ASCO).
        2. **Match** — apply cancer-type, stage, and biomarker matching to
           identify relevant guideline recommendations.
        3. **Patient factors** — evaluate age, ECOG score, prior treatment
           history, and comorbidities that may affect guideline concordance.
        4. **Assemble** — build the final ``AgentOpinion`` with a summary,
           pros/cons, confidence rating, and references.

        Parameters
        ----------
        context : ClinicalContext
            Frozen patient / case snapshot including *cancer_type*,
            *stage*, *biomarkers*, *variants*, *treatment_history*,
            *age*, *ecog_score*, and *clinical_notes*.
        evidence : EvidenceBundle
            Aggregated evidence items from all configured knowledge
            sources, including guideline databases.

        Returns
        -------
        AgentOpinion
            The agent's structured opinion containing guideline
            recommendations, concordance assessment, and supporting
            rationale.
        """
        # ── Stage 1: Filter guideline items ──────────────────────────────
        guideline_items = [
            item for item in evidence.items if _is_guideline_item(item)
        ]

        if not guideline_items:
            return AgentOpinion(
                agent_type=self.agent_type,
                agent_version=self.agent_version,
                summary=(
                    "No clinical guideline recommendations were found in "
                    "the evidence bundle.  The available knowledge sources "
                    "did not return NCCN, ESMO, or ASCO guideline items "
                    "matching the patient's profile."
                ),
                confidence="low",
                created_at=datetime.now(timezone.utc).isoformat(),
                context_hash=context.context_hash or None,
            )

        # ── Stage 2: Match against cancer type, stage, biomarkers ────────
        matched_items: list[dict[str, Any]] = []
        for item in guideline_items:
            cancer_match = _match_cancer_type(
                item.disease, context.cancer_type
            )
            stage_match = _match_stage(
                item.disease, item.description, context.stage
            )
            biomarker_match = _match_biomarker(
                item.gene_symbol, item.description, context.biomarkers
            )

            # A guideline item is considered relevant if:
            # - it matches the cancer type, AND
            # - it matches the stage (or stage is not specified), AND
            # - either it matches a biomarker OR no biomarkers are available
            if not cancer_match:
                continue
            if not stage_match:
                continue

            matched_items.append(
                {
                    "item": item,
                    "cancer_match": cancer_match,
                    "stage_match": stage_match,
                    "biomarker_match": biomarker_match,
                    "source": item.source,
                    "drug": item.drug_name or "",
                    "recommendation": item.description or "",
                    "evidence_level": item.evidence_level or "",
                    "citation": item.citation or "",
                    "url": item.url or "",
                }
            )

        # ── Stage 3: Patient-factor evaluation ───────────────────────────
        patient_notes = _evaluate_patient_factors(context)

        # ── Stage 4: Assemble AgentOpinion ───────────────────────────────

        # Summary
        summary_parts: list[str] = [
            f"Evaluated {len(guideline_items)} guideline item(s) from "
            f"{', '.join(_GUIDELINE_SOURCES)} for "
            f"{context.cancer_type or 'unknown cancer type'} "
            f"(stage: {context.stage or 'not specified'})."
        ]

        matched_drugs = sorted(
            {
                m["drug"]
                for m in matched_items
                if m["drug"]
            }
        )
        if matched_items:
            summary_parts.append(
                f"Found {len(matched_items)} relevant guideline "
                f"recommendation(s) covering "
                f"{len(matched_drugs)} drug(s) / regimen(s)."
            )
        else:
            summary_parts.append(
                "No guideline recommendations matched the patient's "
                "specific cancer type, stage, or biomarkers."
            )

        summary = " ".join(summary_parts)

        # Pros — supporting arguments
        pros: list[str] = []
        if matched_items:
            pros.append(
                f"Identified {len(matched_items)} guideline recommendation(s) "
                f"relevant to the patient's clinical profile."
            )
            if matched_drugs:
                pros.append(
                    f"Guideline-concordant options include: "
                    f"{', '.join(matched_drugs)}."
                )
            biomarker_matched = [
                m for m in matched_items if m["biomarker_match"]
            ]
            if biomarker_matched:
                pros.append(
                    f"{len(biomarker_matched)} recommendation(s) reference "
                    f"biomarkers present in the patient's profile — "
                    f"potential for biomarker-driven therapy."
                )
        else:
            pros.append(
                "Guideline sources were searched; no applicable "
                "recommendations were found for the current profile."
            )

        # Cons — opposing / cautionary arguments
        cons: list[str] = []
        if not matched_items:
            cons.append(
                "No guideline recommendations matched the patient's "
                "cancer type and stage combination — the patient may "
                "be a candidate for clinical trials or off-label options."
            )
        else:
            # Check biomarker coverage
            if context.biomarkers and not any(
                m["biomarker_match"] for m in matched_items
            ):
                cons.append(
                    "None of the matched guideline recommendations "
                    "reference the patient's reported biomarkers — "
                    "the evidence base may not cover biomarker-directed "
                    "therapies."
                )

        # Add patient-factor notes as cons (or considerations)
        for note in patient_notes:
            cons.append(note)

        # Stage-specific caution
        stage_rank = _stage_rank(context.stage)
        if stage_rank >= 4:
            cons.append(
                "Advanced / Stage IV disease — guideline recommendations "
                "for this setting may focus on palliative-intent or "
                "systemic therapy options."
            )

        # References
        references: list[dict[str, Any]] = []
        seen_refs: set[tuple[str, str]] = set()
        for m in matched_items:
            item = m["item"]
            dedup_key = (
                m["source"].lower().strip(),
                (m["citation"] or m["recommendation"] or "").lower().strip(),
            )
            if dedup_key in seen_refs:
                continue
            seen_refs.add(dedup_key)

            ref: dict[str, Any] = {
                "source": m["source"],
                "citation": (
                    m["citation"]
                    or m["recommendation"]
                    or f"{m['source']} guideline recommendation"
                ),
            }
            if m["url"]:
                ref["url"] = m["url"]
            if m["drug"]:
                ref["drug"] = m["drug"]
            if m["evidence_level"]:
                ref["evidence_level"] = m["evidence_level"]
            if item.gene_symbol:
                ref["gene"] = item.gene_symbol
            references.append(ref)

        # Confidence
        if not matched_items:
            confidence = "low"
        elif any(
            (m["evidence_level"] or "") in ("A", "B", "Level_1", "1", "I", "II")
            for m in matched_items
        ):
            confidence = "high"
        elif matched_drugs:
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
            import logging as _logging

            _logging.getLogger(__name__).warning(
                "GuidelineAgent produced an opinion with validation "
                "errors: %s",
                "; ".join(validation_errors),
            )

        return opinion


__all__ = [
    "GuidelineAgent",
]
