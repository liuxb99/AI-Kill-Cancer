"""
Clinical Decision API — clinical decision endpoint.

Provides:
- POST /api/v1/clinical-decision  — Create a clinical decision
- GET  /api/v1/clinical-decision/{decision_id}  — Retrieve a clinical decision
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.auth.dependencies import require_auth
from src.backend.database.session import get_db
from src.backend.domain.user import UserModel
from src.backend.services.clinical_decision_service import (
    ClinicalDecisionRequest,
    ClinicalDecisionResponse,
    ClinicalDecisionService,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/clinical-decision", tags=["Clinical Decision"])


@router.post("", response_model=ClinicalDecisionResponse, status_code=201)
async def create_clinical_decision(
    request: ClinicalDecisionRequest,
    user: UserModel = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> ClinicalDecisionResponse:
    """
    建立 Clinical Decision。

    輸入 patient_id, recommendation_id, variants，
    回傳 Clinical Decision（含 decision_type, reason, confidence, alternatives, contraindications）。
    """
    service = ClinicalDecisionService(db=db)
    try:
        result = await service.create_decision(
            patient_id=request.patient_id,
            recommendation_id=request.recommendation_id,
            variants=request.variants,
            context=request.context,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except RuntimeError:
        raise HTTPException(status_code=500, detail="Internal server error")
    except Exception:
        logger.exception("Unexpected error in create_clinical_decision")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{decision_id}", response_model=ClinicalDecisionResponse)
async def get_clinical_decision(
    decision_id: str,
    user: UserModel = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> ClinicalDecisionResponse:
    """依 decision_id 查詢 Clinical Decision。"""
    service = ClinicalDecisionService(db=db)
    try:
        result = await service.get_decision(decision_id=decision_id)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except RuntimeError:
        raise HTTPException(status_code=500, detail="Internal server error")
    except Exception:
        logger.exception("Unexpected error in get_clinical_decision")
        raise HTTPException(status_code=500, detail="Internal server error")

    if not result:
        raise HTTPException(status_code=404, detail="Clinical decision not found")
    return result
