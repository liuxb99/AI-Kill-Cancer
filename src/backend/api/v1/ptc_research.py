"""PTC research data API."""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.backend.database.session import get_db
from src.backend.domain.ptc_research import (
    PTCOutcomeInput,
    PTCResearchCaseInput,
    PTCResearchCaseModel,
    PTCVariantInput,
)
from src.backend.importers.ptc_tcga.downloader import GDCClient
from src.backend.importers.ptc_tcga.service import PTCTCGAImportService

router = APIRouter(prefix="/ptc-research", tags=["ptc-research"])


class PTCImportRequest(BaseModel):
    records: list[dict[str, Any] | PTCResearchCaseInput] = Field(min_length=1)
    source_version: str | None = None
    batch_id: str | None = None


class GDCImportRequest(BaseModel):
    size: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)


class PTCImportResponse(BaseModel):
    batch_id: str
    imported_cases: int
    imported_variants: int
    imported_outcomes: int
    outbox_events: int


class GDCImportResponse(PTCImportResponse):
    gdc_total_cases: int
    downloaded_cases: int


class PTCVariantResponse(PTCVariantInput):
    pass


class PTCOutcomeResponse(PTCOutcomeInput):
    pass


class PTCCaseResponse(BaseModel):
    case_id: str
    source_dataset: str
    source_project: str
    disease: str
    sex: str | None
    age_range: str | None
    pathologic_stage: str | None
    t_status: str | None
    n_status: str | None
    m_status: str | None
    vital_status: str | None
    days_to_last_follow_up: int | None
    days_to_death: int | None
    variants: list[PTCVariantResponse]
    outcomes: list[PTCOutcomeResponse]


def _response(model: PTCResearchCaseModel) -> PTCCaseResponse:
    return PTCCaseResponse(
        case_id=model.case_id,
        source_dataset=model.source_dataset,
        source_project=model.source_project,
        disease=model.disease,
        sex=model.sex,
        age_range=model.age_range,
        pathologic_stage=model.pathologic_stage,
        t_status=model.t_status,
        n_status=model.n_status,
        m_status=model.m_status,
        vital_status=model.vital_status,
        days_to_last_follow_up=model.days_to_last_follow_up,
        days_to_death=model.days_to_death,
        variants=[
            PTCVariantResponse(
                variant_id=v.variant_id,
                gene=v.gene,
                chromosome=v.chromosome,
                position=v.position,
                reference=v.reference,
                alternate=v.alternate,
                variant_type=v.variant_type,
                classification=v.classification,
                protein_change=v.protein_change,
                source_record_id=v.source_record_id,
            )
            for v in model.variants
        ],
        outcomes=[
            PTCOutcomeResponse(
                outcome_id=o.outcome_id,
                outcome_type=o.outcome_type,
                outcome_value=o.outcome_value,
                observed_at=o.observed_at,
                source_record_id=o.source_record_id,
            )
            for o in model.outcomes
        ],
    )


@router.post("/imports", response_model=PTCImportResponse, status_code=status.HTTP_201_CREATED)
async def import_ptc_records(
    body: PTCImportRequest,
    db: AsyncSession = Depends(get_db),
) -> PTCImportResponse:
    service = PTCTCGAImportService(db)
    try:
        result = await service.import_records(
            body.records,
            source_version=body.source_version,
            batch_id=body.batch_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return PTCImportResponse(**result.__dict__)


@router.post("/imports/gdc", response_model=GDCImportResponse, status_code=status.HTTP_201_CREATED)
async def import_ptc_from_gdc(
    body: GDCImportRequest,
    db: AsyncSession = Depends(get_db),
) -> GDCImportResponse:
    """Download public TCGA-THCA clinical records and persist them immediately."""
    try:
        download = await asyncio.to_thread(
            GDCClient().fetch_ptc_cases,
            size=body.size,
            offset=body.offset,
        )
        result = await PTCTCGAImportService(db).import_records(
            download.records,
            source_version=download.source_version,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="GDC public data import failed") from exc
    return GDCImportResponse(
        **result.__dict__,
        gdc_total_cases=download.total,
        downloaded_cases=len(download.records),
    )


@router.get("/gdc/mutation-manifest")
async def get_gdc_mutation_manifest(
    size: int = Query(default=100, ge=1, le=1000),
) -> dict[str, Any]:
    try:
        files = await asyncio.to_thread(GDCClient().fetch_somatic_mutation_manifest, size=size)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="GDC mutation manifest query failed") from exc
    return {"project": "TCGA-THCA", "count": len(files), "files": files}


@router.get("/cases", response_model=list[PTCCaseResponse])
async def list_ptc_cases(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    gene: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> list[PTCCaseResponse]:
    stmt = (
        select(PTCResearchCaseModel)
        .options(
            selectinload(PTCResearchCaseModel.variants),
            selectinload(PTCResearchCaseModel.outcomes),
        )
        .order_by(PTCResearchCaseModel.case_id)
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    models = list(result.scalars().unique())
    if gene:
        gene = gene.upper()
        models = [model for model in models if any(v.gene == gene for v in model.variants)]
    return [_response(model) for model in models]


@router.get("/cases/{case_id}", response_model=PTCCaseResponse)
async def get_ptc_case(case_id: str, db: AsyncSession = Depends(get_db)) -> PTCCaseResponse:
    result = await db.execute(
        select(PTCResearchCaseModel)
        .where(PTCResearchCaseModel.case_id == case_id)
        .options(
            selectinload(PTCResearchCaseModel.variants),
            selectinload(PTCResearchCaseModel.outcomes),
        )
    )
    model = result.scalar_one_or_none()
    if model is None:
        raise HTTPException(status_code=404, detail="PTC research case not found")
    return _response(model)


@router.get("/cases/{case_id}/graph-path")
async def get_ptc_case_graph_path(case_id: str, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    case = await get_ptc_case(case_id, db)
    nodes: list[dict[str, Any]] = [
        {"id": f"ptc:case:{case.source_dataset}:{case.case_id}", "type": "PTCResearchCase", "label": case.case_id},
        {"id": "disease:papillary_thyroid_carcinoma", "type": "Disease", "label": "Papillary Thyroid Carcinoma"},
    ]
    edges: list[dict[str, Any]] = [
        {
            "id": f"edge:{case.case_id}:disease",
            "source": nodes[0]["id"],
            "target": nodes[1]["id"],
            "relation": "HAS_DISEASE",
        }
    ]
    seen_genes: set[str] = set()
    for variant in case.variants:
        variant_node = f"ptc:variant:{case.source_dataset}:{variant.variant_id}"
        nodes.append({"id": variant_node, "type": "Variant", "label": variant.protein_change or variant.variant_id})
        edges.append(
            {
                "id": f"edge:{case.case_id}:{variant.variant_id}",
                "source": nodes[0]["id"],
                "target": variant_node,
                "relation": "HAS_VARIANT",
            }
        )
        gene_node = f"gene:{variant.gene}"
        if variant.gene not in seen_genes:
            nodes.append({"id": gene_node, "type": "Gene", "label": variant.gene})
            seen_genes.add(variant.gene)
        edges.append(
            {
                "id": f"edge:{variant.variant_id}:{variant.gene}",
                "source": variant_node,
                "target": gene_node,
                "relation": "AFFECTS_GENE",
            }
        )
    return {"case_id": case.case_id, "nodes": nodes, "edges": edges}


__all__ = ["router"]
