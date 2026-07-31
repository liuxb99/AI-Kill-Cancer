"""PTC therapy, evidence, and clinical-trial API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.backend.database.session import get_db
from src.backend.domain.ptc_knowledge import (
    PTCClinicalTrialModel,
    PTCEvidenceRecordModel,
    PTCEvidenceResponse,
    PTCTherapyModel,
    PTCTherapyResponse,
    PTCTrialResponse,
)
from src.backend.services.ptc_knowledge_service import PTCKnowledgeService

router = APIRouter(prefix="/ptc-knowledge", tags=["ptc-knowledge"])


class OpenFDASyncRequest(BaseModel):
    drug_names: list[str] = Field(min_length=1, max_length=50)


class EvidenceCreateRequest(BaseModel):
    source_name: str
    source_record_id: str
    evidence_type: str
    title: str | None = None
    summary: str | None = None
    evidence_level: str | None = None
    direction: str | None = None
    gene_symbol: str | None = None
    variant: str | None = None
    therapy_id: str | None = None
    clinical_trial_id: str | None = None
    publication_id: str | None = None
    citation: str | None = None
    source_url: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


@router.post("/sync/clinical-trials")
async def sync_trials(
    page_size: int = Query(default=100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
) -> dict[str, int | str]:
    count = await PTCKnowledgeService(db).sync_clinical_trials(page_size=page_size)
    return {"status": "completed", "records": count}


@router.post("/sync/openfda")
async def sync_openfda(
    body: OpenFDASyncRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, int | str]:
    count = await PTCKnowledgeService(db).sync_openfda_labels(body.drug_names)
    return {"status": "completed", "records": count}


@router.post("/evidence", response_model=PTCEvidenceResponse)
async def create_evidence(
    body: EvidenceCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> PTCEvidenceRecordModel:
    return await PTCKnowledgeService(db).create_evidence(**body.model_dump())


@router.get("/therapies", response_model=list[PTCTherapyResponse])
async def list_therapies(
    gene: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
) -> list[PTCTherapyModel]:
    stmt = select(PTCTherapyModel).options(selectinload(PTCTherapyModel.targets)).order_by(PTCTherapyModel.name).limit(limit)
    therapies = list((await db.execute(stmt)).scalars().unique())
    if gene:
        wanted = gene.upper()
        therapies = [item for item in therapies if any(target.gene_symbol == wanted for target in item.targets)]
    return therapies


@router.get("/trials", response_model=list[PTCTrialResponse])
async def list_trials(
    recruiting_only: bool = Query(default=False),
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
) -> list[PTCClinicalTrialModel]:
    stmt = select(PTCClinicalTrialModel).order_by(PTCClinicalTrialModel.nct_id).limit(limit)
    if recruiting_only:
        stmt = stmt.where(PTCClinicalTrialModel.overall_status.in_(["RECRUITING", "NOT_YET_RECRUITING", "ENROLLING_BY_INVITATION", "ACTIVE_NOT_RECRUITING"]))
    return list((await db.execute(stmt)).scalars())


@router.get("/evidence", response_model=list[PTCEvidenceResponse])
async def list_evidence(
    gene: str | None = Query(default=None),
    evidence_level: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
) -> list[PTCEvidenceRecordModel]:
    stmt = select(PTCEvidenceRecordModel).order_by(PTCEvidenceRecordModel.created_at.desc()).limit(limit)
    if gene:
        stmt = stmt.where(PTCEvidenceRecordModel.gene_symbol == gene.upper())
    if evidence_level:
        stmt = stmt.where(PTCEvidenceRecordModel.evidence_level == evidence_level)
    return list((await db.execute(stmt)).scalars())


@router.get("/gene/{gene_symbol}")
async def gene_knowledge(gene_symbol: str, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    gene = gene_symbol.upper()
    therapies = await list_therapies(gene=gene, limit=500, db=db)
    evidence = await list_evidence(gene=gene, evidence_level=None, limit=500, db=db)
    trials = await list_trials(recruiting_only=False, limit=500, db=db)
    matching_trials = [
        trial for trial in trials
        if gene.lower() in str(trial.interventions).lower() or gene.lower() in trial.brief_title.lower()
    ]
    return {
        "gene": gene,
        "therapies": [PTCTherapyResponse.model_validate(item).model_dump() for item in therapies],
        "evidence": [PTCEvidenceResponse.model_validate(item).model_dump() for item in evidence],
        "trials": [PTCTrialResponse.model_validate(item).model_dump() for item in matching_trials],
    }


__all__ = ["router"]
