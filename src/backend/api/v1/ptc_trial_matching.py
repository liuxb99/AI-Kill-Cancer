"""Explainable research-only PTC clinical-trial matching.

The matcher evaluates de-identified public research cases against imported
ClinicalTrials.gov records. It is a navigation aid, not a clinical eligibility
determination. Unknown data never counts as a match.
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

ACTIVE_STATUSES = {"RECRUITING", "NOT_YET_RECRUITING", "ENROLLING_BY_INVITATION", "ACTIVE_NOT_RECRUITING"}


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


def _criterion(name: str, status: str, weight: float, detail: str, evidence: Any = None) -> dict[str, Any]:
    awarded = weight if status == "match" else 0.0
    return {"name": name, "status": status, "weight": weight, "awarded": awarded, "detail": detail, "evidence": evidence}


def _match_trial(case: PTCResearchCaseModel, trial: PTCClinicalTrialModel) -> dict[str, Any]:
    case_genes = {item.gene.upper() for item in case.variants if item.gene}
    case_variants = {f"{item.gene.upper()}:{_norm(item.protein_change)}" for item in case.variants if item.gene and item.protein_change}
    trial_genes = {_norm(item) for item in (trial.target_genes or []) if item}
    eligibility = trial.eligibility or ""
    eligibility_upper = _norm(eligibility)
    conditions = [_norm(item) for item in (trial.conditions or []) if item]

    criteria: list[dict[str, Any]] = []
    status = _norm(trial.overall_status)
    criteria.append(_criterion(
        "recruitment_status",
        "match" if status in ACTIVE_STATUSES else "mismatch",
        15.0,
        f"Trial status is {status or 'unknown'}.",
        status,
    ))

    disease_match = any("THYROID" in item or "PAPILLARY" in item for item in conditions)
    criteria.append(_criterion(
        "disease",
        "match" if disease_match else ("unknown" if not conditions else "mismatch"),
        15.0,
        "Trial condition includes thyroid or papillary thyroid carcinoma." if disease_match else "No explicit PTC condition found.",
        conditions,
    ))

    if trial_genes:
        shared_genes = sorted(case_genes & trial_genes)
        gene_status = "match" if shared_genes else "mismatch"
        gene_detail = f"Shared genes: {', '.join(shared_genes)}" if shared_genes else "No shared target gene."
    else:
        shared_genes = []
        gene_status = "unknown"
        gene_detail = "Trial has no structured target gene metadata."
    criteria.append(_criterion("gene", gene_status, 25.0, gene_detail, {"case": sorted(case_genes), "trial": sorted(trial_genes)}))

    mentioned_variants = sorted(item for item in case_variants if item.split(":", 1)[1] and item.split(":", 1)[1] in eligibility_upper)
    variant_status = "match" if mentioned_variants else ("unknown" if not case_variants or not eligibility else "unknown")
    criteria.append(_criterion(
        "protein_variant",
        variant_status,
        15.0,
        f"Eligibility mentions {', '.join(mentioned_variants)}." if mentioned_variants else "No explicit case variant match found in eligibility text.",
        sorted(case_variants),
    ))

    stage = _norm(case.pathologic_stage)
    if stage and stage in eligibility_upper:
        stage_status, stage_detail = "match", f"Eligibility text mentions {case.pathologic_stage}."
    elif not stage:
        stage_status, stage_detail = "unknown", "Case pathologic stage is missing."
    elif "STAGE" not in eligibility_upper:
        stage_status, stage_detail = "unknown", "Trial eligibility has no machine-readable stage restriction."
    else:
        stage_status, stage_detail = "mismatch", f"Case stage {case.pathologic_stage} is not explicitly accepted."
    criteria.append(_criterion("pathologic_stage", stage_status, 10.0, stage_detail, case.pathologic_stage))

    case_min, case_max = _age_bounds(case.age_range)
    trial_min, trial_max = _trial_age_bounds(eligibility)
    if case_min is None:
        age_status, age_detail = "unknown", "Case age range is missing."
    elif trial_min is None and trial_max is None:
        age_status, age_detail = "unknown", "Trial age limits were not parsed."
    else:
        overlap = (trial_max is None or case_min <= trial_max) and (trial_min is None or case_max >= trial_min)
        age_status = "match" if overlap else "mismatch"
        age_detail = f"Case age {case.age_range}; trial range {trial_min or '—'}–{trial_max or '—'}."
    criteria.append(_criterion("age", age_status, 10.0, age_detail, {"case": case.age_range, "trial_min": trial_min, "trial_max": trial_max}))

    sex = _norm(case.sex)
    if not sex:
        sex_status, sex_detail = "unknown", "Case sex is missing."
    elif "FEMALE" in eligibility_upper and "MALE" not in eligibility_upper:
        sex_status = "match" if sex.startswith("F") else "mismatch"
        sex_detail = "Female-only eligibility detected."
    elif "MALE" in eligibility_upper and "FEMALE" not in eligibility_upper:
        sex_status = "match" if sex.startswith("M") else "mismatch"
        sex_detail = "Male-only eligibility detected."
    else:
        sex_status, sex_detail = "unknown", "No exclusive sex restriction parsed."
    criteria.append(_criterion("sex", sex_status, 5.0, sex_detail, case.sex))

    score = round(sum(item["awarded"] for item in criteria), 2)
    mismatches = [item for item in criteria if item["status"] == "mismatch"]
    unknowns = [item for item in criteria if item["status"] == "unknown"]
    if mismatches:
        classification = "unlikely_match"
    elif score >= 70:
        classification = "potential_match"
    else:
        classification = "insufficient_data"

    return {
        "nct_id": trial.nct_id,
        "title": trial.brief_title,
        "official_title": trial.official_title,
        "status": trial.overall_status,
        "phases": trial.phases or [],
        "conditions": trial.conditions or [],
        "interventions": trial.interventions or [],
        "target_genes": trial.target_genes or [],
        "source_url": trial.source_url,
        "score": score,
        "classification": classification,
        "criteria": criteria,
        "blocking_mismatches": [item["name"] for item in mismatches],
        "missing_or_unparsed": [item["name"] for item in unknowns],
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

    case_genes = {item.gene.upper() for item in case.variants if item.gene}
    selected_gene = gene.upper() if gene else None
    if selected_gene and selected_gene not in case_genes:
        raise HTTPException(status_code=404, detail="Requested gene is not present in this case")

    trials = list((await db.execute(select(PTCClinicalTrialModel).order_by(PTCClinicalTrialModel.updated_at.desc()))).scalars())
    matched = [_match_trial(case, trial) for trial in trials]
    if selected_gene:
        matched = [item for item in matched if selected_gene in {_norm(value) for value in item["target_genes"]} or not item["target_genes"]]
    if active_only:
        matched = [item for item in matched if _norm(item["status"]) in ACTIVE_STATUSES]
    matched.sort(key=lambda item: (-item["score"], item["nct_id"]))
    matched = matched[:limit]

    return {
        "case_id": case.case_id,
        "selected_gene": selected_gene,
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
            "potential_match": sum(item["classification"] == "potential_match" for item in matched),
            "insufficient_data": sum(item["classification"] == "insufficient_data" for item in matched),
            "unlikely_match": sum(item["classification"] == "unlikely_match" for item in matched),
        },
        "trace": [
            {"step": 1, "name": "load_deidentified_case", "records": 1},
            {"step": 2, "name": "load_imported_trials", "records": len(trials)},
            {"step": 3, "name": "evaluate_explainable_criteria", "records": len(matched)},
            {"step": 4, "name": "rank_without_clinical_recommendation", "records": len(matched)},
        ],
        "disclaimer": (
            "Research navigation only. This output is not a determination of trial eligibility, "
            "medical advice, enrollment approval, or treatment recommendation. Trial teams must verify all criteria."
        ),
    }


__all__ = ["router", "match_trials", "_match_trial"]
