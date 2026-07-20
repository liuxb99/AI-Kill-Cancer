"""
Clinical Reports API — traceable clinical study reports.

Provides:
- POST /api/v1/reports/case/{case_id}
- GET  /api/v1/reports/{report_id}
- GET  /api/v1/reports/{report_id}/html
- GET  /api/v1/reports/{report_id}/json
- GET  /api/v1/reports/{report_id}/fhir
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.database.session import get_db
from src.backend.reporting.builder import ReportBuilder
from src.backend.reporting.validator import ReportValidator
from src.backend.reporting.renderer import ReportRenderer, FHIRExporter
from src.backend.reporting.repository import ReportRepository
from src.backend.reporting.models import ClinicalReport, ReportCreateResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("/case/{case_id}", response_model=ReportCreateResponse)
async def create_case_report(
    case_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Create a clinical report for a case (placeholder — requires evidence data)."""
    builder = ReportBuilder()
    repo = ReportRepository(db)
    renderer = ReportRenderer()
    fhir_exporter = FHIRExporter()

    # For now, create minimal report
    # Full version will aggregate evidence, ranking, reasoning
    report = builder.build(
        case_metadata={"case_id": case_id},
        limitations=["Case-to-evidence integration pending. Report contains limited data."],
    )

    # Validate
    validator = ReportValidator()
    issues = validator.validate(report)

    # Render formats
    html = renderer.render_html(report)
    fhir = fhir_exporter.export(report)

    # Persist
    model = await repo.create(
        report_data=report.model_dump(),
        html_content=html,
        fhir_data=fhir,
    )

    return ReportCreateResponse(
        report_id=str(model.id),
        version=report.metadata.version,
        status=report.metadata.status,
        message=f"Report created with {len(issues)} validation issues",
    )


@router.get("/{report_id}")
async def get_report(
    report_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a report's metadata."""
    try:
        rid = uuid.UUID(report_id)
    except ValueError:
        raise HTTPException(status_code=400, detail={"error": "invalid_uuid"})

    repo = ReportRepository(db)
    model = await repo.get(rid)
    if not model:
        raise HTTPException(status_code=404, detail={"error": "not_found"})

    return model.report_data


@router.get("/{report_id}/html")
async def get_report_html(
    report_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a report rendered as HTML."""
    try:
        rid = uuid.UUID(report_id)
    except ValueError:
        raise HTTPException(status_code=400, detail={"error": "invalid_uuid"})

    repo = ReportRepository(db)
    model = await repo.get(rid)
    if not model:
        raise HTTPException(status_code=404, detail={"error": "not_found"})

    return HTMLResponse(content=model.html_content or "<html><body><p>HTML not available</p></body></html>")


@router.get("/{report_id}/json")
async def get_report_json(
    report_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a report rendered as JSON."""
    try:
        rid = uuid.UUID(report_id)
    except ValueError:
        raise HTTPException(status_code=400, detail={"error": "invalid_uuid"})

    repo = ReportRepository(db)
    model = await repo.get(rid)
    if not model:
        raise HTTPException(status_code=404, detail={"error": "not_found"})

    return JSONResponse(content=model.report_data)


@router.get("/{report_id}/fhir")
async def get_report_fhir(
    report_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a report exported as FHIR Bundle."""
    try:
        rid = uuid.UUID(report_id)
    except ValueError:
        raise HTTPException(status_code=400, detail={"error": "invalid_uuid"})

    repo = ReportRepository(db)
    model = await repo.get(rid)
    if not model:
        raise HTTPException(status_code=404, detail={"error": "not_found"})

    return JSONResponse(content=model.fhir_data or {"error": "FHIR export not available"})
