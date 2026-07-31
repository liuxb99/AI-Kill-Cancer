"""Integrated PTC research workbench API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.database.session import get_db
from src.backend.domain.ptc_integrated import (
    PTCHerbCompoundModel,
    PTCHerbDrugInteractionModel,
    PTCHerbModel,
)
from src.backend.services.ptc_integrated_service import PTCIntegratedService, dashboard_dict

router = APIRouter(prefix="/ptc-integrated", tags=["ptc-integrated"])


class InteractionCreate(BaseModel):
    herb_key: str
    therapy_key: str
    interaction_type: str
    severity: str = "unknown"
    mechanism: str | None = None
    clinical_effect: str | None = None
    recommendation: str | None = None
    evidence_level: str = "unknown"
    source_name: str
    source_record_id: str | None = None


@router.post("/bootstrap/herbs")
async def bootstrap_herbs(db: AsyncSession = Depends(get_db)) -> dict[str, int]:
    return await PTCIntegratedService(db).bootstrap_herbal_research()


@router.get("/herbs")
async def list_herbs(
    gene: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    rows = list((await db.execute(select(PTCHerbModel).order_by(PTCHerbModel.chinese_name))).scalars())
    if gene:
        wanted = gene.upper()
        rows = [row for row in rows if wanted in {item.upper() for item in (row.investigated_genes or [])}]
    return [
        {
            "herb_key": row.herb_key,
            "chinese_name": row.chinese_name,
            "english_name": row.english_name,
            "latin_name": row.latin_name,
            "medicinal_part": row.medicinal_part,
            "traditional_functions": row.traditional_functions or [],
            "investigated_genes": row.investigated_genes or [],
            "investigated_pathways": row.investigated_pathways or [],
            "evidence_level": row.evidence_level,
            "evidence_summary": row.evidence_summary,
            "source_name": row.source_name,
            "source_record_id": row.source_record_id,
        }
        for row in rows
    ]


@router.get("/herbs/{herb_key}/compounds")
async def list_herb_compounds(herb_key: str, db: AsyncSession = Depends(get_db)) -> list[dict[str, Any]]:
    rows = list(
        (
            await db.execute(
                select(PTCHerbCompoundModel)
                .where(PTCHerbCompoundModel.herb_key == herb_key)
                .order_by(PTCHerbCompoundModel.compound_name)
            )
        ).scalars()
    )
    return [
        {
            "compound_key": row.compound_key,
            "herb_key": row.herb_key,
            "compound_name": row.compound_name,
            "pubchem_cid": row.pubchem_cid,
            "inchikey": row.inchikey,
            "target_genes": row.target_genes or [],
            "pathways": row.pathways or [],
            "source_name": row.source_name,
        }
        for row in rows
    ]


@router.post("/interactions", status_code=status.HTTP_201_CREATED)
async def create_interaction(body: InteractionCreate, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    row = await PTCIntegratedService(db).add_interaction(body.model_dump())
    return {
        "herb_key": row.herb_key,
        "therapy_key": row.therapy_key,
        "interaction_type": row.interaction_type,
        "severity": row.severity,
        "mechanism": row.mechanism,
        "clinical_effect": row.clinical_effect,
        "recommendation": row.recommendation,
        "evidence_level": row.evidence_level,
        "source_name": row.source_name,
    }


@router.get("/interactions")
async def list_interactions(
    herb_key: str | None = Query(default=None),
    therapy_key: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    stmt = select(PTCHerbDrugInteractionModel).order_by(
        PTCHerbDrugInteractionModel.severity,
        PTCHerbDrugInteractionModel.herb_key,
    )
    if herb_key:
        stmt = stmt.where(PTCHerbDrugInteractionModel.herb_key == herb_key)
    if therapy_key:
        stmt = stmt.where(PTCHerbDrugInteractionModel.therapy_key == therapy_key)
    rows = list((await db.execute(stmt)).scalars())
    return [
        {
            "herb_key": row.herb_key,
            "therapy_key": row.therapy_key,
            "interaction_type": row.interaction_type,
            "severity": row.severity,
            "mechanism": row.mechanism,
            "clinical_effect": row.clinical_effect,
            "recommendation": row.recommendation,
            "evidence_level": row.evidence_level,
            "source_name": row.source_name,
        }
        for row in rows
    ]


@router.post("/cases/{case_id}/similarity")
async def calculate_case_similarity(
    case_id: str,
    limit: int = Query(default=10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    try:
        return await PTCIntegratedService(db).calculate_similarities(case_id, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/cases/{case_id}/recommendation")
async def generate_recommendation(case_id: str, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    try:
        return await PTCIntegratedService(db).generate_research_recommendation(case_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/dashboard")
async def get_dashboard(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    return dashboard_dict(await PTCIntegratedService(db).dashboard())


__all__ = ["router"]
