"""Explainable research-only PTC clinical-trial navigation.

The matcher ranks imported ClinicalTrials.gov records by research relevance to
an de-identified public research case. Eligibility is evaluated on a separate
track and never contributes points to the relevance score. The output never
claims enrollment eligibility.
"""
from __future__ import annotations

import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.backend.database.session import get_db
from src.backend.domain.ptc_knowledge import PTCClinicalTrialModel
from src.backend.domain.ptc_research import PTCResearchCaseModel

router = APIRouter(prefix="/ptc-trial-matching", tags=["ptc-trial-matching"])

MATCHING_VERSION = "ptc-trial-research-navigation-v2"
ACTIVE_STATUSES = {
    "RECRUITING",
    "NOT_YET_RECRUITING",
    "ENROLLING_BY_INVITATION",
    "ACTIVE_NOT_RECRUITING",
}
RELEVANCE_WEIGHTS = {
    "disease_relevance": 20.0,
    "gene_relevance": 30.0,
    "protein_variant_relevance": 20.0,
    "recruitment_status": 15.0,
    "site_information": 10.0,
    "source_provenance": 5.0,
}
ELIGIBILITY_FIELDS = (
    "age",
    "pathologic_stage",
    "sex",
    "ecog_performance_status",
    "organ_function",
    "prior_treatment",
    "exclusion_criteria",
)


def _norm(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").strip()).upper()


def _age_bounds(age_range: str | None) -> tuple[int | None, int | None]:
    if not age_range:
        return None, None
    numbers = [int(item) for item in re.findall(r"\d+", age_range)]
    if len(numbers) >= 2:
        return min(numbers[0], numbers[1]), max(numbers[0], numbers[1])
    if len(numbers) == 1:
        return numbers[0], numbers[0]
    return None, None


def _trial_age_bounds(eligibility: str | None) -> tuple[int | None, int | None]:
    text = eligibility or ""
    minimum = re.search(r"MINIMUM\s+AGE\s*[:=-]?\s*(\d+)", text, re.I)
    maximum = re.search(r"MAXIMUM\s+AGE\s*[:=-]?\s*(\d+)", text, re.I)
    if not minimum:
        minimum = re.search(r"(?:AGE|AGED)\s*(?:>=|≥|AT LEAST)\s*(\d+)", text, re.I)
    if not maximum:
        maximum = re.search(r"(?:AGE|AGED)\s*(?:<=|≤|UP TO)\s*(\d+)", text, re.I)
    return (int(minimum.group(1)) if minimum else None, int(maximum.group(1)) if maximum else None)


def _criterion(
    name: str,
    track: str,
    status: str,
    detail: str,
    evidence: Any = None,
    weight: float = 0.0,
) -> dict[str, Any]:
    awarded = weight if track == "relevance" and status == "match" else 0.0
    return {
        "name": name,
        "track": track,
        "status": status,
        "weight": weight,
        "awarded": awarded,
        "detail": detail,
        "evidence": evidence,
    }


def _eligibility_criteria(case: PTCResearchCaseModel, trial: PTCClinicalTrialModel) -> list[dict[str, Any]]:
    eligibility = trial.eligibility or ""
    eligibility_upper = _norm(eligibility)
    criteria: list[dict[str, Any]] = []

    stage = _norm(case.pathologic_stage)
    if not stage:
        status, detail = "unknown", "Case pathologic stage is unavailable."
    elif "STAGE" not in eligibility_upper:
        status, detail = "unknown", "No machine-readable stage restriction was parsed."
    elif stage in eligibility_upper:
        status, detail = "match", f"Eligibility text mentions {case.pathologic_stage}."
    else:
        status, detail = "mismatch", f"Case stage {case.pathologic_stage} was not explicitly accepted."
    criteria.append(_criterion("pathologic_stage", "eligibility", status, detail, case.pathologic_stage))

    case_min, case_max = _age_bounds(case.age_range)
    trial_min, trial_max = _trial_age_bounds(eligibility)
    if case_min is None:
        status, detail = "unknown", "Case age range is unavailable."
    elif trial_min is None and trial_max is None:
        status, detail = "unknown", "Trial age limits were not parsed."
    else:
        overlap = (trial_max is None or case_min <= trial_max) and (trial_min is None or case_max >= trial_min)
        status = "match" if overlap else "mismatch"
        detail = f"Case age {case.age_range}; parsed trial range {trial_min or '—'}–{trial_max or '—'}."
    criteria.append(_criterion("age", "eligibility", status, detail, {
        "case": case.age_range,
        "trial_min": trial_min,
        "trial_max": trial_max,
    }))

    sex = _norm(case.sex)
    if not sex:
        status, detail = "unknown", "Case sex is unavailable."
    elif "FEMALE" in eligibility_upper and "MALE" not in eligibility_upper:
        status = "match" if sex.startswith("F") else "mismatch"
        detail = "Female-only eligibility text was detected."
    elif "MALE" in eligibility_upper and "FEMALE" not in eligibility_upper:
        status = "match" if sex.startswith("M") else "mismatch"
        detail = "Male-only eligibility text was detected."
    else:
        status, detail = "unknown", "No exclusive sex restriction was parsed."
    criteria.append(_criterion("sex", "eligibility", status, detail, case.sex))

    structured_checks = (
        ("ecog_performance_status", ("ECOG", "PERFORMANCE STATUS")),
        ("organ_function", ("ORGAN FUNCTION", "HEPATIC", "RENAL", "CREATININE", "BILIRUBIN")),
        ("prior_treatment", ("PRIOR TREATMENT", "PREVIOUS THERAPY", "PRIOR THERAPY")),
        ("exclusion_criteria", ("EXCLUSION CRITERIA", "EXCLUSION")),
    )
    for name, markers in structured_checks:
        detected = any(marker in eligibility_upper for marker in markers)
        detail = (
            "Requirement exists in trial text but the research case lacks the clinical data needed to verify it."
            if detected
            else "Requirement was not available as a verified structured criterion."
        )
        criteria.append(_criterion(name, "eligibility", "unknown", detail, detected))

    return criteria


def _match_trial(case: PTCResearchCaseModel, trial: PTCClinicalTrialModel) -> dict[str, Any]:
    case_genes = {_norm(item.gene) for item in case.variants if item.gene}
    case_variants = {
        f"{_norm(item.gene)}:{_norm(item.protein_change)}"
        for item in case.variants
        if item.gene and item.protein_change
    }
    trial_genes = {_norm(item) for item in (trial.target_genes or []) if item}
    eligibility_upper = _norm(trial.eligibility)
    conditions = [_norm(item) for item in (trial.conditions or []) if item]
    relevance: list[dict[str, Any]] = []

    status = _norm(trial.overall_status)
    relevance.append(_criterion(
        "recruitment_status",
        "relevance",
        "match" if status in ACTIVE_STATUSES else ("unknown" if not status else "mismatch"),
        f"Trial status is {status or 'unknown'}.",
        status,
        RELEVANCE_WEIGHTS["recruitment_status"],
    ))

    disease_match = any("THYROID" in item or "PAPILLARY" in item for item in conditions)
    relevance.append(_criterion(
        "disease_relevance",
        "relevance",
        "match" if disease_match else ("unknown" if not conditions else "mismatch"),
        "Trial condition includes thyroid or papillary thyroid carcinoma." if disease_match else "No explicit PTC condition was found.",
        conditions,
        RELEVANCE_WEIGHTS["disease_relevance"],
    ))

    if trial_genes:
        shared_genes = sorted(case_genes & trial_genes)
        gene_status = "match" if shared_genes else "mismatch"
        gene_detail = f"Shared genes: {', '.join(shared_genes)}" if shared_genes else "No shared structured target gene."
    else:
        shared_genes = []
        gene_status = "unknown"
        gene_detail = "Trial has no structured target-gene metadata."
    relevance.append(_criterion(
        "gene_relevance",
        "relevance",
        gene_status,
        gene_detail,
        {"case": sorted(case_genes), "trial": sorted(trial_genes)},
        RELEVANCE_WEIGHTS["gene_relevance"],
    ))

    mentioned_variants = sorted(
        item for item in case_variants
        if item.split(":", 1)[1] and item.split(":", 1)[1] in eligibility_upper
    )
    variant_status = "match" if mentioned_variants else "unknown"
    relevance.append(_criterion(
        "protein_variant_relevance",
        "relevance",
        variant_status,
        f"Eligibility mentions {', '.join(mentioned_variants)}." if mentioned_variants else "No explicit case-variant match was parsed.",
        sorted(case_variants),
        RELEVANCE_WEIGHTS["protein_variant_relevance"],
    ))

    locations = trial.locations or []
    relevance.append(_criterion(
        "site_information",
        "relevance",
        "match" if locations else "unknown",
        f"{len(locations)} trial site record(s) are available." if locations else "No structured site information is available.",
        locations,
        RELEVANCE_WEIGHTS["site_information"],
    ))

    provenance_complete = bool(trial.nct_id and trial.source_url)
    relevance.append(_criterion(
        "source_provenance",
        "relevance",
        "match" if provenance_complete else "unknown",
        "NCT identifier and source URL are present." if provenance_complete else "NCT provenance is incomplete.",
        {"nct_id": trial.nct_id, "source_url": trial.source_url},
        RELEVANCE_WEIGHTS["source_provenance"],
    ))

    eligibility = _eligibility_criteria(case, trial)
    score = round(sum(item["awarded"] for item in relevance), 2)
    relevance_mismatches = [item for item in relevance if item["status"] == "mismatch"]
    relevance_unknowns = [item for item in relevance if item["status"] == "unknown"]
    eligibility_mismatches = [item for item in eligibility if item["status"] == "mismatch"]
    eligibility_unknowns = [item for item in eligibility if item["status"] == "unknown"]

    if relevance_mismatches or score < 40:
        classification = "low_relevance"
    elif score >= 60:
        classification = "research_candidate"
    else:
        classification = "insufficient_relevance_data"

    if eligibility_mismatches:
        eligibility_status = "conflict_detected"
    elif eligibility_unknowns:
        eligibility_status = "incomplete_review_required"
    else:
        eligibility_status = "criteria_text_aligned_review_required"

    return {
        "nct_id": trial.nct_id,
        "title": trial.brief_title,
        "official_title": trial.official_title,
        "status": trial.overall_status,
        "phases": trial.phases or [],
        "conditions": trial.conditions or [],
        "interventions": trial.interventions or [],
        "target_genes": trial.target_genes or [],
        "locations": locations,
        "source_url": trial.source_url,
        "score": score,
        "score_type": "research_relevance",
        "score_version": MATCHING_VERSION,
        "classification": classification,
        "eligibility_status": eligibility_status,
        "eligibility_determination": False,
        "relevance_criteria": relevance,
        "eligibility_criteria": eligibility,
        "criteria": [*relevance, *eligibility],
        "blocking_relevance_mismatches": [item["name"] for item in relevance_mismatches],
        "eligibility_conflicts": [item["name"] for item in eligibility_mismatches],
        "missing_or_unverified_eligibility": [item["name"] for item in eligibility_unknowns],
        "missing_relevance_metadata": [item["name"] for item in relevance_unknowns],
    }


@router.get("/case/{case_id}")
async def match_trials(
    case_id: str,
    gene: str | None = Query(default=None, max_length=32),
    active_only: bool = Query(default=True),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    case = (await db.execute(
        select(PTCResearchCaseModel)
        .options(selectinload(PTCResearchCaseModel.variants))
        .where(PTCResearchCaseModel.case_id == case_id)
    )).scalar_one_or_none()
    if case is None:
        raise HTTPException(status_code=404, detail="PTC research case not found")

    case_genes = {_norm(item.gene) for item in case.variants if item.gene}
    selected_gene = _norm(gene) if gene else None
    if selected_gene and selected_gene not in case_genes:
        raise HTTPException(status_code=404, detail="Requested gene is not present in this case")

    trials = list((await db.execute(
        select(PTCClinicalTrialModel).order_by(PTCClinicalTrialModel.updated_at.desc())
    )).scalars())
    matched = [_match_trial(case, trial) for trial in trials]
    if selected_gene:
        matched = [
            item for item in matched
            if selected_gene in {_norm(value) for value in item["target_genes"]} or not item["target_genes"]
        ]
    if active_only:
        matched = [item for item in matched if _norm(item["status"]) in ACTIVE_STATUSES]
    matched.sort(key=lambda item: (-item["score"], item["nct_id"]))
    matched = matched[:limit]

    return {
        "case_id": case.case_id,
        "selected_gene": selected_gene,
        "methodology": {
            "matching_version": MATCHING_VERSION,
            "score_type": "research_relevance",
            "maximum_score": sum(RELEVANCE_WEIGHTS.values()),
            "eligibility_separate_from_score": True,
            "eligibility_determination": False,
            "eligibility_fields": list(ELIGIBILITY_FIELDS),
            "required_for_real_eligibility": [
                "exact_age",
                "diagnosis_and_stage_confirmation",
                "ECOG_performance_status",
                "organ_function_laboratory_results",
                "prior_treatment_history",
                "concomitant_medications",
                "full_inclusion_and_exclusion_review",
                "trial_site_confirmation",
                "investigator_review",
            ],
        },
        "weights": RELEVANCE_WEIGHTS,
        "case_facts": {
            "genes": sorted(case_genes),
            "variants": [
                {"gene": item.gene, "protein_change": item.protein_change, "classification": item.classification}
                for item in case.variants
            ],
            "pathologic_stage": case.pathologic_stage,
            "age_range": case.age_range,
            "sex": case.sex,
        },
        "matches": matched,
        "summary": {
            "total": len(matched),
            "research_candidate": sum(item["classification"] == "research_candidate" for item in matched),
            "insufficient_relevance_data": sum(item["classification"] == "insufficient_relevance_data" for item in matched),
            "low_relevance": sum(item["classification"] == "low_relevance" for item in matched),
            "eligibility_conflict_detected": sum(item["eligibility_status"] == "conflict_detected" for item in matched),
            "eligibility_review_required": sum(item["eligibility_status"] != "conflict_detected" for item in matched),
        },
        "trace": [
            {"step": 1, "name": "load_deidentified_case", "records": 1},
            {"step": 2, "name": "load_imported_trials", "records": len(trials)},
            {"step": 3, "name": "score_research_relevance_only", "records": len(matched)},
            {"step": 4, "name": "evaluate_eligibility_separately", "records": len(matched)},
            {"step": 5, "name": "rank_without_eligibility_claim", "records": len(matched)},
        ],
        "disclaimer": (
            "Research navigation only. A research-candidate label is not trial eligibility, enrollment approval, "
            "medical advice, or a treatment recommendation. Complete eligibility must be verified by the trial team."
        ),
    }


__all__ = [
    "router",
    "match_trials",
    "_match_trial",
    "MATCHING_VERSION",
    "RELEVANCE_WEIGHTS",
    "ELIGIBILITY_FIELDS",
]
