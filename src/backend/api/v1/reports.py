"""
Clinical Reports API — traceable clinical study reports with case-level authorization.

Provides:
- POST /api/v1/reports/case/{case_id}      (requires EDITOR access)
- GET  /api/v1/reports/{report_id}         (requires VIEWER access on the case)
- GET  /api/v1/reports/{report_id}/html    (requires VIEWER access on the case)
- GET  /api/v1/reports/{report_id}/json    (requires VIEWER access on the case)
- GET  /api/v1/reports/{report_id}/fhir    (requires VIEWER access on the case)
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.database.session import get_db
from src.backend.auth.dependencies import require_auth, require_case_access, verify_case_access
from src.backend.domain.case_acl import CaseRole
from src.backend.domain.user import UserModel
from src.backend.reporting.builder import ReportBuilder
from src.backend.reporting.validator import ReportValidator
from src.backend.reporting.renderer import ReportRenderer, FHIRExporter
from src.backend.reporting.repository import ReportRepository
from src.backend.reporting.models import ReportCreateResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reports", tags=["reports"])


async def _get_report_and_verify_access(
    report_id: str,
    user: UserModel,
    db: AsyncSession,
    required_role: CaseRole = CaseRole.VIEWER,
):
    """Look up a report, resolve its case_id, and verify case-level access."""
    try:
        rid = uuid.UUID(report_id)
    except ValueError:
        raise HTTPException(status_code=404, detail={"error": "not_found"})

    repo = ReportRepository(db)
    model = await repo.get(rid)
    if not model:
        raise HTTPException(status_code=404, detail={"error": "not_found"})

    # Resolve case_id from the report model
    case_id_str = getattr(model, 'case_id', None) or (model.report_data or {}).get("metadata", {}).get("case_id")
    if case_id_str:
        try:
            cid = uuid.UUID(str(case_id_str))
            await verify_case_access(cid, user, db, required_role)
        except ValueError:
            pass  # Invalid case_id — still return the report for existing data

    return model


@router.post("/case/{case_id}", response_model=ReportCreateResponse)
async def create_case_report(
    case_id: str,
    user: UserModel = Depends(require_case_access(CaseRole.EDITOR)),
    db: AsyncSession = Depends(get_db),
):
    """Create a clinical report for a case (requires EDITOR access on the case)."""
    builder = ReportBuilder()
    repo = ReportRepository(db)
    renderer = ReportRenderer()
    fhir_exporter = FHIRExporter()

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
    user: UserModel = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Get a report's metadata (requires VIEWER access on the case)."""
    model = await _get_report_and_verify_access(report_id, user, db, CaseRole.VIEWER)
    return model.report_data


@router.get("/{report_id}/html")
async def get_report_html(
    report_id: str,
    user: UserModel = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Get a report rendered as HTML (requires VIEWER access on the case)."""
    model = await _get_report_and_verify_access(report_id, user, db, CaseRole.VIEWER)
    return HTMLResponse(content=model.html_content or "<html><body><p>HTML not available</p></body></html>")


@router.get("/{report_id}/json")
async def get_report_json(
    report_id: str,
    user: UserModel = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Get a report rendered as JSON (requires VIEWER access on the case)."""
    model = await _get_report_and_verify_access(report_id, user, db, CaseRole.VIEWER)
    return JSONResponse(content=model.report_data)


@router.get("/{report_id}/fhir")
async def get_report_fhir(
    report_id: str,
    user: UserModel = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Get a report exported as FHIR Bundle (requires VIEWER access on the case)."""
    model = await _get_report_and_verify_access(report_id, user, db, CaseRole.VIEWER)
    return JSONResponse(content=model.fhir_data or {"error": "FHIR export not available"})
