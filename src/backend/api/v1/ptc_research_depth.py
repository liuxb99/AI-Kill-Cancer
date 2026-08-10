from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.backend.database.session import get_db
from src.backend.domain.evidence import EvidenceModel
from src.backend.domain.ptc_research import PTCResearchCaseModel
from src.backend.research_depth import (
    build_hypotheses,
    cohort_biomarker_stratification,
    evidence_conflict_summary,
    outcome_feedback_summary,
)

router = APIRouter(prefix="/ptc-research-depth", tags=["ptc-research-depth"])


async def _load_cases(db: AsyncSession, limit: int) -> list[PTCResearchCaseModel]:
    result = await db.execute(
        select(PTCResearchCaseModel)
        .options(
            selectinload(PTCResearchCaseModel.variants),
            selectinload(PTCResearchCaseModel.outcomes),
        )
        .order_by(PTCResearchCaseModel.updated_at.desc())
        .limit(limit)
    )
    return list(result.scalars().unique())


async def _load_gene_evidence(db: AsyncSession, gene: str, limit: int = 500) -> list[EvidenceModel]:
    result = await db.execute(
        select(EvidenceModel)
        .where(EvidenceModel.gene_symbol == gene.strip().upper())
        .order_by(EvidenceModel.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars())


@router.get("/outcomes")
async def research_outcome_feedback(
    limit: int = Query(default=1000, ge=1, le=5000),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Post-selection descriptive outcome feedback across de-identified PTC research cases."""
    cases = await _load_cases(db, limit)
    payload = outcome_feedback_summary(cases)
    payload["trace"] = [
        {"step": 1, "name": "load_deidentified_ptc_research_cases", "records": len(cases)},
        {"step": 2, "name": "aggregate_outcomes_after_selection", "records": len(cases)},
        {"step": 3, "name": "preserve_missingness_and_nonbinary_values"},
    ]
    return payload


@router.get("/biomarker/{gene}")
async def biomarker_research_depth(
    gene: str,
    protein_change: str | None = Query(default=None),
    limit: int = Query(default=1000, ge=1, le=5000),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Build a research-only cohort/conflict/hypothesis packet for one biomarker."""
    normalized_gene = gene.strip().upper()
    cases = await _load_cases(db, limit)
    evidence = await _load_gene_evidence(db, normalized_gene)

    stratification = cohort_biomarker_stratification(cases, normalized_gene, protein_change)
    conflict = evidence_conflict_summary(evidence)
    hypotheses = build_hypotheses(stratification, conflict)

    return {
        "biomarker": stratification["biomarker"],
        "cohort_stratification": stratification,
        "evidence_conflict": conflict,
        "hypotheses": hypotheses,
        "trace": [
            {"step": 1, "name": "load_deidentified_cases_outcome_blind", "records": len(cases)},
            {"step": 2, "name": "stratify_by_biomarker_without_outcomes"},
            {"step": 3, "name": "aggregate_outcomes_post_stratification"},
            {"step": 4, "name": "load_gene_evidence", "records": len(evidence)},
            {"step": 5, "name": "resolve_support_and_dissent_without_majority_only_rule"},
            {"step": 6, "name": "generate_falsifiable_research_hypotheses", "records": len(hypotheses)},
        ],
        "research_only": True,
        "clinical_use": False,
        "disclaimer": (
            "Research hypothesis generation only. Cohort associations are descriptive, evidence "
            "consensus retains dissent, and no output is a diagnosis, prognosis, treatment "
            "recommendation, or causal conclusion."
        ),
    }


__all__ = ["router"]
