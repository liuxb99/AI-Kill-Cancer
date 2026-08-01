"""Explainable PTC research-case cohort comparison.

This module compares de-identified public research cases only. Similarity is a
transparent research-navigation score, not a prognostic model or clinical risk
score.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.backend.database.session import get_db
from src.backend.domain.ptc_research import PTCResearchCaseModel

router = APIRouter(prefix="/ptc-cohort", tags=["ptc-cohort"])

WEIGHTS = {
    "genes": 40.0,
    "protein_variants": 20.0,
    "pathologic_stage": 15.0,
    "tnm": 10.0,
    "age_range": 5.0,
    "sex": 5.0,
    "vital_status": 5.0,
}


def _case_genes(case: PTCResearchCaseModel) -> set[str]:
    return {item.gene.strip().upper() for item in case.variants if item.gene}


def _protein_variants(case: PTCResearchCaseModel) -> set[str]:
    return {
        f"{item.gene.strip().upper()}:{item.protein_change.strip().upper()}"
        for item in case.variants
        if item.gene and item.protein_change
    }


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left and not right:
        return 0.0
    union = left | right
    return len(left & right) / len(union) if union else 0.0


def _same(left: str | None, right: str | None) -> float:
    if not left or not right:
        return 0.0
    return 1.0 if left.strip().upper() == right.strip().upper() else 0.0


def _tnm_similarity(left: PTCResearchCaseModel, right: PTCResearchCaseModel) -> float:
    pairs = [
        (left.t_status, right.t_status),
        (left.n_status, right.n_status),
        (left.m_status, right.m_status),
    ]
    available = [(a, b) for a, b in pairs if a and b]
    if not available:
        return 0.0
    return sum(_same(a, b) for a, b in available) / len(available)


def compare_cases(anchor: PTCResearchCaseModel, candidate: PTCResearchCaseModel) -> dict[str, Any]:
    anchor_genes = _case_genes(anchor)
    candidate_genes = _case_genes(candidate)
    anchor_variants = _protein_variants(anchor)
    candidate_variants = _protein_variants(candidate)

    components = {
        "genes": _jaccard(anchor_genes, candidate_genes),
        "protein_variants": _jaccard(anchor_variants, candidate_variants),
        "pathologic_stage": _same(anchor.pathologic_stage, candidate.pathologic_stage),
        "tnm": _tnm_similarity(anchor, candidate),
        "age_range": _same(anchor.age_range, candidate.age_range),
        "sex": _same(anchor.sex, candidate.sex),
        "vital_status": _same(anchor.vital_status, candidate.vital_status),
    }
    weighted = {name: round(value * WEIGHTS[name], 3) for name, value in components.items()}
    score = round(sum(weighted.values()), 3)
    shared_genes = sorted(anchor_genes & candidate_genes)
    shared_variants = sorted(anchor_variants & candidate_variants)

    return {
        "case_id": candidate.case_id,
        "source_dataset": candidate.source_dataset,
        "score": score,
        "components": weighted,
        "shared_genes": shared_genes,
        "shared_protein_variants": shared_variants,
        "case_facts": {
            "pathologic_stage": candidate.pathologic_stage,
            "tnm": [candidate.t_status, candidate.n_status, candidate.m_status],
            "age_range": candidate.age_range,
            "sex": candidate.sex,
            "vital_status": candidate.vital_status,
            "days_to_last_follow_up": candidate.days_to_last_follow_up,
            "days_to_death": candidate.days_to_death,
            "genes": sorted(candidate_genes),
            "variants": [
                {
                    "variant_id": item.variant_id,
                    "gene": item.gene,
                    "protein_change": item.protein_change,
                    "classification": item.classification,
                }
                for item in candidate.variants
            ],
            "outcomes": [
                {"type": item.outcome_type, "value": item.outcome_value}
                for item in candidate.outcomes
            ],
        },
    }


def _cohort_summary(matches: list[dict[str, Any]]) -> dict[str, Any]:
    stages = Counter(item["case_facts"].get("pathologic_stage") or "unknown" for item in matches)
    vital = Counter(item["case_facts"].get("vital_status") or "unknown" for item in matches)
    genes = Counter(gene for item in matches for gene in item["case_facts"].get("genes", []))
    outcome_values = Counter(
        f"{entry.get('type')}:{entry.get('value')}"
        for item in matches
        for entry in item["case_facts"].get("outcomes", [])
    )
    follow_up = [
        item["case_facts"].get("days_to_last_follow_up")
        for item in matches
        if item["case_facts"].get("days_to_last_follow_up") is not None
    ]
    return {
        "size": len(matches),
        "stage_distribution": dict(stages),
        "vital_status_distribution": dict(vital),
        "top_genes": [{"gene": gene, "cases": count} for gene, count in genes.most_common(15)],
        "outcome_distribution": dict(outcome_values),
        "mean_follow_up_days": round(sum(follow_up) / len(follow_up), 2) if follow_up else None,
    }


@router.get("/case/{case_id}/similar")
async def similar_cases(
    case_id: str,
    limit: int = Query(default=20, ge=1, le=100),
    min_score: float = Query(default=0.0, ge=0.0, le=100.0),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    rows = list((await db.execute(
        select(PTCResearchCaseModel)
        .options(
            selectinload(PTCResearchCaseModel.variants),
            selectinload(PTCResearchCaseModel.outcomes),
        )
        .order_by(PTCResearchCaseModel.updated_at.desc())
        .limit(1000)
    )).scalars().unique())
    anchor = next((item for item in rows if item.case_id == case_id), None)
    if anchor is None:
        raise HTTPException(status_code=404, detail="PTC research case not found")

    compared = [compare_cases(anchor, item) for item in rows if item.id != anchor.id]
    compared = [item for item in compared if item["score"] >= min_score]
    compared.sort(key=lambda item: (-item["score"], item["case_id"]))
    matches = compared[:limit]

    return {
        "anchor": {
            "case_id": anchor.case_id,
            "source_dataset": anchor.source_dataset,
            "pathologic_stage": anchor.pathologic_stage,
            "tnm": [anchor.t_status, anchor.n_status, anchor.m_status],
            "genes": sorted(_case_genes(anchor)),
            "protein_variants": sorted(_protein_variants(anchor)),
        },
        "weights": WEIGHTS,
        "matches": matches,
        "cohort": _cohort_summary(matches),
        "trace": [
            {"step": 1, "name": "load_deidentified_cases", "records": len(rows)},
            {"step": 2, "name": "compute_explainable_similarity", "records": len(compared)},
            {"step": 3, "name": "rank_and_limit", "records": len(matches)},
            {"step": 4, "name": "aggregate_cohort_outcomes", "records": len(matches)},
        ],
        "disclaimer": (
            "Research cohort navigation only. Similarity is not prognosis, diagnosis, "
            "treatment efficacy, or clinical eligibility."
        ),
    }


__all__ = ["router", "compare_cases", "WEIGHTS"]
