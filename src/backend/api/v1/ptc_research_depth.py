from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.backend.database.session import get_db
from src.backend.domain.evidence import EvidenceModel
from src.backend.domain.ptc_research import PTCResearchCaseModel
from src.backend.domain.research_depth import (
    ResearchEventModel,
    ResearchHypothesisModel,
    ResearchRunModel,
)
from src.backend.research_depth import (
    build_hypotheses,
    cohort_biomarker_stratification,
    evidence_conflict_summary,
    execute_research_loop,
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


def _hypothesis_payload(item: ResearchHypothesisModel) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "hypothesis_key": item.hypothesis_key,
        "gene_symbol": item.gene_symbol,
        "protein_change": item.protein_change,
        "hypothesis_type": item.hypothesis_type,
        "version": item.version,
        "status": item.status,
        "claim": item.claim,
        "rationale": item.rationale,
        "supporting_observations": item.supporting_observations,
        "counter_evidence": item.counter_evidence,
        "uncertainties": item.uncertainties,
        "falsification_criteria": item.falsification_criteria,
        "next_data_needed": item.next_data_needed,
        "input_fingerprint": item.input_fingerprint,
        "clinical_use": False,
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
    }


def _event_payload(item: ResearchEventModel) -> dict[str, Any]:
    return {
        "id": str(item.id),
        "event_key": item.event_key,
        "event_type": item.event_type,
        "gene_symbol": item.gene_symbol,
        "hypothesis_id": str(item.hypothesis_id) if item.hypothesis_id else None,
        "run_id": str(item.run_id) if item.run_id else None,
        "observed_at": item.observed_at.isoformat() if item.observed_at else None,
        "date_semantics": item.date_semantics,
        "source_type": item.source_type,
        "source_id": item.source_id,
        "provenance": item.provenance,
        "payload": item.payload,
    }


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


@router.post("/biomarker/{gene}/run")
async def run_biomarker_research_loop(
    gene: str,
    protein_change: str | None = Query(default=None),
    limit: int = Query(default=1000, ge=1, le=5000),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Execute and persist the controlled research loop for a biomarker."""
    normalized_gene = gene.strip().upper()
    cases = await _load_cases(db, limit)
    evidence = await _load_gene_evidence(db, normalized_gene)
    return await execute_research_loop(
        db,
        gene=normalized_gene,
        protein_change=protein_change,
        cases=cases,
        evidence=evidence,
    )


@router.get("/hypotheses")
async def list_research_hypotheses(
    gene: str | None = Query(default=None, max_length=32),
    limit: int = Query(default=100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    query = select(ResearchHypothesisModel).order_by(ResearchHypothesisModel.created_at.desc()).limit(limit)
    if gene:
        query = query.where(ResearchHypothesisModel.gene_symbol == gene.strip().upper())
    items = list((await db.execute(query)).scalars())
    return {
        "count": len(items),
        "items": [_hypothesis_payload(item) for item in items],
        "research_only": True,
        "clinical_use": False,
    }


@router.get("/events")
async def list_research_events(
    gene: str | None = Query(default=None, max_length=32),
    limit: int = Query(default=250, ge=1, le=2000),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    query = select(ResearchEventModel).order_by(ResearchEventModel.observed_at.desc()).limit(limit)
    if gene:
        query = query.where(ResearchEventModel.gene_symbol == gene.strip().upper())
    items = list((await db.execute(query)).scalars())
    return {
        "count": len(items),
        "events": [_event_payload(item) for item in items],
        "research_only": True,
        "clinical_use": False,
    }


@router.get("/runs")
async def list_research_runs(
    gene: str | None = Query(default=None, max_length=32),
    limit: int = Query(default=100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    query = select(ResearchRunModel).order_by(ResearchRunModel.created_at.desc()).limit(limit)
    if gene:
        query = query.where(ResearchRunModel.gene_symbol == gene.strip().upper())
    items = list((await db.execute(query)).scalars())
    return {
        "count": len(items),
        "items": [
            {
                "id": str(item.id),
                "run_key": item.run_key,
                "gene_symbol": item.gene_symbol,
                "protein_change": item.protein_change,
                "input_fingerprint": item.input_fingerprint,
                "status": item.status,
                "trace": item.trace,
                "result_summary": item.result_summary,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            }
            for item in items
        ],
        "research_only": True,
        "clinical_use": False,
    }


__all__ = ["router"]
