"""Explainable PTC evidence matrix for de-identified research cases.

The matrix joins imported variants with persisted therapies, evidence records,
clinical trials, open-full-text assets, and same-gene cohort observations. It is
research navigation only and never emits a prescription or clinical eligibility
claim.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.backend.api.v1.ptc_targeting import GENE_TARGET_CATALOG
from src.backend.database.session import get_db
from src.backend.domain.ptc_knowledge import (
    PTCClinicalTrialModel,
    PTCEvidenceRecordModel,
    PTCTherapyModel,
)
from src.backend.domain.ptc_research import PTCResearchCaseModel

router = APIRouter(prefix="/ptc-evidence-matrix", tags=["ptc-evidence-matrix"])

EVIDENCE_LEVEL_SCORES = {
    "A": 30.0,
    "B": 24.0,
    "C": 18.0,
    "D": 12.0,
    "E": 6.0,
}


def _level_score(level: str | None) -> float:
    if not level:
        return 4.0
    normalized = level.strip().upper()
    for key, value in EVIDENCE_LEVEL_SCORES.items():
        if normalized == key or normalized.startswith(f"LEVEL {key}"):
            return value
    return 4.0


def _trial_is_active(status: str | None) -> bool:
    normalized = (status or "").strip().upper()
    return normalized in {
        "RECRUITING",
        "NOT_YET_RECRUITING",
        "ENROLLING_BY_INVITATION",
        "ACTIVE_NOT_RECRUITING",
    }


def _evidence_assets(item: PTCEvidenceRecordModel) -> tuple[int, int]:
    payload = item.payload if isinstance(item.payload, dict) else {}
    return len(payload.get("figures") or []), len(payload.get("tables") or [])


async def _load_case(db: AsyncSession, case_id: str) -> PTCResearchCaseModel:
    case = await db.scalar(
        select(PTCResearchCaseModel)
        .where(PTCResearchCaseModel.case_id == case_id)
        .options(
            selectinload(PTCResearchCaseModel.variants),
            selectinload(PTCResearchCaseModel.outcomes),
        )
    )
    if case is None:
        raise HTTPException(status_code=404, detail="PTC research case not found")
    return case


@router.get("/case/{case_id}")
async def get_case_evidence_matrix(
    case_id: str,
    gene: str | None = Query(default=None, max_length=32),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    case = await _load_case(db, case_id)
    requested_gene = gene.strip().upper() if gene else None
    variants_by_gene: dict[str, list[Any]] = {}
    for variant in case.variants:
        symbol = (variant.gene or "").strip().upper()
        if not symbol or (requested_gene and symbol != requested_gene):
            continue
        variants_by_gene.setdefault(symbol, []).append(variant)

    if requested_gene and requested_gene not in variants_by_gene:
        raise HTTPException(status_code=404, detail="Requested gene is not present in this case")

    therapy_rows = list(
        (
            await db.execute(
                select(PTCTherapyModel)
                .options(selectinload(PTCTherapyModel.targets))
                .order_by(PTCTherapyModel.name)
            )
        )
        .scalars()
        .unique()
    )

    all_cases = list(
        (
            await db.execute(
                select(PTCResearchCaseModel)
                .options(
                    selectinload(PTCResearchCaseModel.variants),
                    selectinload(PTCResearchCaseModel.outcomes),
                )
                .limit(1000)
            )
        )
        .scalars()
        .unique()
    )

    rows: list[dict[str, Any]] = []
    for symbol, variants in sorted(variants_by_gene.items()):
        therapies = [
            item
            for item in therapy_rows
            if any((target.gene_symbol or "").strip().upper() == symbol for target in item.targets)
        ]
        evidence = list(
            (
                await db.execute(
                    select(PTCEvidenceRecordModel)
                    .where(PTCEvidenceRecordModel.gene_symbol == symbol)
                    .order_by(PTCEvidenceRecordModel.created_at.desc())
                    .limit(100)
                )
            ).scalars()
        )
        trials = list(
            (
                await db.execute(
                    select(PTCClinicalTrialModel)
                    .where(
                        or_(
                            PTCClinicalTrialModel.brief_title.ilike(f"%{symbol}%"),
                            PTCClinicalTrialModel.official_title.ilike(f"%{symbol}%"),
                        )
                    )
                    .order_by(PTCClinicalTrialModel.nct_id)
                    .limit(100)
                )
            ).scalars()
        )

        same_gene_cases = []
        for candidate in all_cases:
            if candidate.case_id == case.case_id:
                continue
            candidate_genes = {(item.gene or "").strip().upper() for item in candidate.variants}
            if symbol in candidate_genes:
                same_gene_cases.append(candidate)

        vital_statuses = Counter((item.vital_status or "unknown") for item in same_gene_cases)
        outcome_values = Counter(
            f"{outcome.outcome_type}:{outcome.outcome_value}"
            for item in same_gene_cases
            for outcome in item.outcomes
        )
        figure_count = 0
        table_count = 0
        for item in evidence:
            figures, tables = _evidence_assets(item)
            figure_count += figures
            table_count += tables

        best_evidence = max((_level_score(item.evidence_level) for item in evidence), default=0.0)
        active_trials = sum(1 for item in trials if _trial_is_active(item.overall_status))
        score_components = {
            "variant_present": 20.0,
            "persisted_therapies": min(20.0, len(therapies) * 5.0),
            "best_evidence_level": best_evidence,
            "active_trials": min(15.0, active_trials * 5.0),
            "open_full_text_assets": min(10.0, (figure_count + table_count) * 2.0),
            "same_gene_cohort": min(5.0, len(same_gene_cases) * 0.5),
        }
        total_score = round(sum(score_components.values()), 2)
        gaps = []
        if not therapies:
            gaps.append("No persisted therapy linked to this gene")
        if not evidence:
            gaps.append("No persisted evidence record linked to this gene")
        if not active_trials:
            gaps.append("No active matching clinical trial")
        if figure_count + table_count == 0:
            gaps.append("No extracted open-full-text figure or table")
        if not same_gene_cases:
            gaps.append("No same-gene comparison case in the imported cohort")

        catalog = GENE_TARGET_CATALOG.get(symbol, {})
        rows.append(
            {
                "gene": symbol,
                "variants": [
                    {
                        "variant_id": item.variant_id,
                        "protein_change": item.protein_change,
                        "classification": item.classification,
                    }
                    for item in variants
                ],
                "protein_domain": catalog.get("protein_domain"),
                "pathway": catalog.get("pathway"),
                "score": total_score,
                "score_components": score_components,
                "therapies": [
                    {
                        "therapy_key": item.therapy_key,
                        "name": item.name,
                        "approval_status": item.approval_status,
                        "mechanism": item.mechanism,
                        "source": item.source_name,
                        "url": item.source_url,
                    }
                    for item in therapies
                ],
                "evidence": [
                    {
                        "evidence_key": item.evidence_key,
                        "title": item.title,
                        "source": item.source_name,
                        "level": item.evidence_level,
                        "direction": item.direction,
                        "publication_id": item.publication_id,
                        "url": item.source_url,
                        "figures": _evidence_assets(item)[0],
                        "tables": _evidence_assets(item)[1],
                    }
                    for item in evidence[:20]
                ],
                "trials": [
                    {
                        "nct_id": item.nct_id,
                        "title": item.brief_title,
                        "status": item.overall_status,
                        "phases": item.phases,
                        "active": _trial_is_active(item.overall_status),
                        "url": item.source_url,
                    }
                    for item in trials[:20]
                ],
                "cohort": {
                    "same_gene_cases": len(same_gene_cases),
                    "vital_status_distribution": dict(vital_statuses),
                    "outcome_distribution": dict(outcome_values),
                },
                "assets": {"figures": figure_count, "tables": table_count},
                "gaps": gaps,
                "actions": [
                    {"type": "open_3d", "case_id": case.case_id, "gene": symbol},
                    {"type": "open_literature", "case_id": case.case_id, "gene": symbol},
                    {"type": "open_report", "case_id": case.case_id, "gene": symbol},
                ],
            }
        )

    rows.sort(key=lambda item: (-item["score"], item["gene"]))
    return {
        "case_id": case.case_id,
        "source_dataset": case.source_dataset,
        "pathologic_stage": case.pathologic_stage,
        "rows": rows,
        "summary": {
            "genes": len(rows),
            "therapies": sum(len(item["therapies"]) for item in rows),
            "evidence": sum(len(item["evidence"]) for item in rows),
            "trials": sum(len(item["trials"]) for item in rows),
            "open_full_text_assets": sum(item["assets"]["figures"] + item["assets"]["tables"] for item in rows),
            "unresolved_gaps": sum(len(item["gaps"]) for item in rows),
        },
        "trace": [
            {"step": 1, "name": "resolve_case_variants", "records": sum(len(item) for item in variants_by_gene.values())},
            {"step": 2, "name": "join_therapies_evidence_trials", "records": len(rows)},
            {"step": 3, "name": "aggregate_same_gene_cohort", "records": len(all_cases)},
            {"step": 4, "name": "score_and_rank_matrix", "records": len(rows)},
        ],
        "disclaimer": (
            "Research evidence navigation only. Matrix scores reflect imported data completeness and linkage, "
            "not clinical benefit, prognosis, prescribing priority, or trial eligibility."
        ),
    }


__all__ = ["router", "EVIDENCE_LEVEL_SCORES"]
