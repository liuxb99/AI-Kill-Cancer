"""
Clinical Reasoning API — evidence-grounded clinical reasoning endpoints.

Provides:
- POST /api/v1/reasoning/case/{case_id}
- GET  /api/v1/reasoning/run/{run_id}
- POST /api/v1/reasoning/run/{run_id}/validate
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.auth.dependencies import require_auth, require_case_access, verify_case_access
from src.backend.database.session import get_db
from src.backend.domain.case_acl import CaseRole
from src.backend.domain.user import UserModel
from src.backend.reasoning.llm import get_llm_adapter
from src.backend.reasoning.models import (
    ClinicalReasoningResult,
    ReasoningRunResponse,
    ReasoningValidationResult,
)
from src.backend.reasoning.repository import ReasoningRunRepository
from src.backend.reasoning.service import ClinicalReasoningService
from src.backend.reasoning.validator import EvidenceCitationValidator

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reasoning", tags=["reasoning"])


@router.post("/case/{case_id}", response_model=ReasoningRunResponse)
async def reason_case(
    case_id: str,
    user: UserModel = Depends(require_case_access(CaseRole.EDITOR)),
    db: AsyncSession = Depends(get_db),
):
    """
    Run clinical reasoning for a case.
    Requires evidence, ranking, and knowledge to be pre-collected.
    """
    llm_adapter = get_llm_adapter()
    service = ClinicalReasoningService(db=db, llm_adapter=llm_adapter)

    # For now, run reasoning with minimal context
    # Full case-based reasoning will be implemented with case-to-evidence resolution
    result = await service.reason(
        case_id=case_id,
        gene_symbol="",
        disease="",
    )

    return result


@router.get("/run/{run_id}", response_model=ReasoningRunResponse)
async def get_reasoning_run(
    run_id: str,
    user: UserModel = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Get a previously computed reasoning run."""
    try:
        rid = uuid.UUID(run_id)
    except ValueError:
        raise HTTPException(status_code=400, detail={"error": "invalid_uuid", "message": "Invalid run ID"})

    repo = ReasoningRunRepository(db)
    run_model = await repo.get(rid)

    if not run_model:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Reasoning run not found"})

    # Resolve case_id from reasoning_run if stored
    if hasattr(run_model, 'case_id') and run_model.case_id:
        try:
            cid = uuid.UUID(str(run_model.case_id))
            await verify_case_access(cid, user, db, CaseRole.VIEWER)
        except ValueError:
            raise HTTPException(status_code=403, detail={"error": "access_denied"})

    reasoning_data = run_model.reasoning_data if isinstance(run_model.reasoning_data, dict) else {}
    validation_data = run_model.validation_result if isinstance(run_model.validation_result, dict) else None

    reasoning_result = ClinicalReasoningResult(**reasoning_data) if reasoning_data else None
    validation_result = ReasoningValidationResult(**validation_data) if validation_data else None

    return ReasoningRunResponse(
        run_id=str(run_model.id),
        status=run_model.status,
        reasoning=reasoning_result,
        validation_result=validation_result,
    )


@router.post("/run/{run_id}/validate", response_model=ReasoningValidationResult)
async def validate_reasoning_run(
    run_id: str,
    user: UserModel = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
):
    """Re-validate a reasoning run's citations."""
    try:
        rid = uuid.UUID(run_id)
    except ValueError:
        raise HTTPException(status_code=400, detail={"error": "invalid_uuid", "message": "Invalid run ID"})

    repo = ReasoningRunRepository(db)
    run_model = await repo.get(rid)

    if not run_model:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Reasoning run not found"})

    # Resolve case_id from reasoning_run if stored
    if hasattr(run_model, 'case_id') and run_model.case_id:
        try:
            cid = uuid.UUID(str(run_model.case_id))
            await verify_case_access(cid, user, db, CaseRole.EDITOR)
        except ValueError:
            raise HTTPException(status_code=403, detail={"error": "access_denied"})

    reasoning_data = run_model.reasoning_data if isinstance(run_model.reasoning_data, dict) else {}
    reasoning_result = ClinicalReasoningResult(**reasoning_data)

    validator = EvidenceCitationValidator()
    return validator.validate(reasoning_result)
