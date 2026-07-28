"""
Treatment Plans API — treatment plan CRUD and lifecycle management.

Provides:
- POST   /api/v1/treatment-plans              — Create a treatment plan (A-01)
- GET    /api/v1/treatment-plans/{plan_id}     — Get a single plan (A-02)
- GET    /api/v1/treatment-plans               — List plans by patient (A-03)
- GET    /api/v1/treatment-plans/{plan_id}/versions — Get plan versions (A-04)
- GET    /api/v1/treatment-plans/{plan_id}/trace    — Get plan trace (A-05)
- POST   /api/v1/treatment-plans/{plan_id}/submit   — Draft → Proposed (A-06)
- POST   /api/v1/treatment-plans/{plan_id}/approve  — Under review → Approved (A-07)
- POST   /api/v1/treatment-plans/{plan_id}/activate — Approved → Active (A-08)
- POST   /api/v1/treatment-plans/{plan_id}/pause    — Active → Paused (A-09)
- POST   /api/v1/treatment-plans/{plan_id}/complete — Active → Completed (A-10)
- POST   /api/v1/treatment-plans/{plan_id}/cancel   — Any non-terminal → Cancelled (A-11)
- POST   /api/v1/treatment-plans/{plan_id}/revise   — Approved/Active → Superseded + new version (A-12)
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.auth.dependencies import require_auth
from src.backend.clinical.treatment_plan_state_machine import IllegalTransitionError
from src.backend.database.session import get_db
from src.backend.domain.enums import Role
from src.backend.domain.user import UserModel
from src.backend.services.treatment_plan_service import (
    CreatePlanRequest,
    TreatmentPlanListItem,
    TreatmentPlanResponse,
    TreatmentPlanService,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/treatment-plans", tags=["Treatment Plans"])

# ─── Role helpers ──────────────────────────────────────────────────────────────

_WRITER_ROLES = {Role.RESEARCHER, Role.CLINICIAN, Role.ADMIN}
_APPROVER_ROLES = {Role.ADMIN}  # Approver maps to Admin
_CLINICIAN_APPROVER_ROLES = {Role.CLINICIAN, Role.ADMIN}
_TUMOR_BOARD_ROLES = {Role.REVIEWER, Role.CLINICIAN, Role.ADMIN}
_ALL_ROLES = set(Role)


def _require_roles(allowed_roles: set[Role]):
    """Return a dependency that checks the user's role is in *allowed_roles*.

    Raises 403 if the user does not have one of the required roles.
    """
    async def _checker(user: UserModel = Depends(require_auth)) -> UserModel:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Operation requires one of roles: "
                    f"{[r.value for r in allowed_roles]}"
                ),
            )
        return user
    return _checker


# ─── Helpers ───────────────────────────────────────────────────────────────────


def _get_service(db: AsyncSession) -> TreatmentPlanService:
    return TreatmentPlanService(db=db)


def _handle_service_error(
    exc: Exception,
    logger_msg: str = "Unexpected error",
) -> None:
    """Map service-layer exceptions to HTTP errors.

    - ValueError       → 422
    - IllegalTransitionError → 409
    - RuntimeError     → 500
    - others           → 500 (logged)
    """
    if isinstance(exc, IllegalTransitionError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if isinstance(exc, ValueError):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    if isinstance(exc, RuntimeError):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")
    logger.exception(logger_msg)
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


def _not_found(resource: str = "Treatment plan") -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{resource} not found")


# ═══════════════════════════════════════════════════════════════════════════════
# Query APIs (A-01 ~ A-05)
# ═══════════════════════════════════════════════════════════════════════════════


@router.post("", response_model=TreatmentPlanResponse, status_code=201)
async def create_treatment_plan(
    request: CreatePlanRequest,
    user: UserModel = Depends(_require_roles(_WRITER_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> TreatmentPlanResponse:
    """建立 Treatment Plan（A-01）。

    需要 Researcher / Clinician / Admin 角色。
    回傳包含完整計劃結構的 TreatmentPlanResponse。
    """
    service = _get_service(db)
    try:
        result = await service.create_plan(
            request=request,
            user_id=str(user.id),
        )
        return result
    except Exception as exc:
        _handle_service_error(exc, "Error in create_treatment_plan")


@router.get("/{plan_id}", response_model=TreatmentPlanResponse)
async def get_treatment_plan(
    plan_id: str,
    user: UserModel = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> TreatmentPlanResponse:
    """取得單一 Treatment Plan（A-02）。

    任何已認證的使用者都可讀取。
    """
    service = _get_service(db)
    try:
        result = await service.get_plan(plan_id=plan_id)
    except Exception as exc:
        _handle_service_error(exc, "Error in get_treatment_plan")

    if result is None:
        raise _not_found()
    return result


@router.get("", response_model=list[TreatmentPlanListItem])
async def list_treatment_plans(
    patient_id: str = Query(..., description="UUID string of the patient"),
    skip: int = Query(ge=0, default=0, description="Number of records to skip"),
    limit: int = Query(ge=1, le=100, default=20, description="Max records to return"),
    user: UserModel = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> list[TreatmentPlanListItem]:
    """列出患者的 Treatment Plans（A-03）。

    任何已認證的使用者都可查詢。
    """
    service = _get_service(db)
    try:
        results = await service.list_plans(
            patient_id=patient_id,
            skip=skip,
            limit=limit,
        )
        return results
    except Exception as exc:
        _handle_service_error(exc, "Error in list_treatment_plans")


@router.get("/{plan_id}/versions", response_model=list[TreatmentPlanResponse])
async def get_plan_versions(
    plan_id: str,
    user: UserModel = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> list[TreatmentPlanResponse]:
    """取得 Plan 的所有版本列表（A-04）。

    任何已認證的使用者都可讀取。
    """
    service = _get_service(db)
    try:
        versions = await service.get_versions(plan_id=plan_id)
    except Exception as exc:
        _handle_service_error(exc, "Error in get_plan_versions")
    return versions


@router.get("/{plan_id}/trace", response_model=list[dict[str, Any]])
async def get_plan_trace(
    plan_id: str,
    user: UserModel = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """取得 Plan 的計算追蹤（A-05）。

    任何已認證的使用者都可讀取。
    """
    service = _get_service(db)
    try:
        trace = await service.get_trace(plan_id=plan_id)
    except Exception as exc:
        _handle_service_error(exc, "Error in get_plan_trace")
    return trace


# ═══════════════════════════════════════════════════════════════════════════════
# Status Operation APIs (A-06 ~ A-12)
# ═══════════════════════════════════════════════════════════════════════════════


@router.post("/{plan_id}/submit", response_model=TreatmentPlanResponse)
async def submit_plan(
    plan_id: str,
    user: UserModel = Depends(_require_roles(_WRITER_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> TreatmentPlanResponse:
    """提交 Plan 審閱：draft → proposed（A-06）。

    需要 Researcher / Clinician / Admin 角色。
    """
    service = _get_service(db)
    try:
        result = await service.submit_plan(
            plan_id=plan_id,
            user_id=str(user.id),
        )
        return result
    except Exception as exc:
        _handle_service_error(exc, "Error in submit_plan")


@router.post("/{plan_id}/review", response_model=TreatmentPlanResponse)
async def review_plan(
    plan_id: str,
    user: UserModel = Depends(_require_roles(_TUMOR_BOARD_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> TreatmentPlanResponse:
    """審閱 Plan：proposed → under_review（A-06b）。

    需要 Tumor Board Member（Reviewer / Clinician / Admin）角色。
    """
    service = _get_service(db)
    try:
        result = await service.review_plan(
            plan_id=plan_id,
            user_id=str(user.id),
        )
        return result
    except Exception as exc:
        _handle_service_error(exc, "Error in review_plan")


@router.post("/{plan_id}/approve", response_model=TreatmentPlanResponse)
async def approve_plan(
    plan_id: str,
    user: UserModel = Depends(_require_roles(_APPROVER_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> TreatmentPlanResponse:
    """審核通過 Plan：under_review → approved（A-07）。

    需要 Admin（Approver）角色。
    """
    service = _get_service(db)
    try:
        result = await service.approve_plan(
            plan_id=plan_id,
            user_id=str(user.id),
        )
        return result
    except Exception as exc:
        _handle_service_error(exc, "Error in approve_plan")


@router.post("/{plan_id}/activate", response_model=TreatmentPlanResponse)
async def activate_plan(
    plan_id: str,
    user: UserModel = Depends(_require_roles(_CLINICIAN_APPROVER_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> TreatmentPlanResponse:
    """啟用 Plan：approved → active（A-08）。

    需要 Clinician / Admin 角色。
    """
    service = _get_service(db)
    try:
        result = await service.activate_plan(
            plan_id=plan_id,
            user_id=str(user.id),
        )
        return result
    except Exception as exc:
        _handle_service_error(exc, "Error in activate_plan")


@router.post("/{plan_id}/pause", response_model=TreatmentPlanResponse)
async def pause_plan(
    plan_id: str,
    user: UserModel = Depends(_require_roles(_CLINICIAN_APPROVER_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> TreatmentPlanResponse:
    """暫停 Plan：active → paused（A-09）。

    需要 Clinician / Admin 角色。
    """
    service = _get_service(db)
    try:
        result = await service.pause_plan(
            plan_id=plan_id,
            user_id=str(user.id),
        )
        return result
    except Exception as exc:
        _handle_service_error(exc, "Error in pause_plan")


@router.post("/{plan_id}/complete", response_model=TreatmentPlanResponse)
async def complete_plan(
    plan_id: str,
    user: UserModel = Depends(_require_roles(_CLINICIAN_APPROVER_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> TreatmentPlanResponse:
    """完成 Plan：active → completed（A-10）。

    需要 Clinician / Admin 角色。
    """
    service = _get_service(db)
    try:
        result = await service.complete_plan(
            plan_id=plan_id,
            user_id=str(user.id),
        )
        return result
    except Exception as exc:
        _handle_service_error(exc, "Error in complete_plan")


@router.post("/{plan_id}/cancel", response_model=TreatmentPlanResponse)
async def cancel_plan(
    plan_id: str,
    user: UserModel = Depends(_require_roles(_CLINICIAN_APPROVER_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> TreatmentPlanResponse:
    """取消 Plan：任意非終端狀態 → cancelled（A-11）。

    需要 Clinician / Admin 角色。
    """
    service = _get_service(db)
    try:
        result = await service.cancel_plan(
            plan_id=plan_id,
            user_id=str(user.id),
        )
        return result
    except Exception as exc:
        _handle_service_error(exc, "Error in cancel_plan")


@router.post("/{plan_id}/revise", response_model=TreatmentPlanResponse)
async def revise_plan(
    plan_id: str,
    request: CreatePlanRequest,
    user: UserModel = Depends(_require_roles(_CLINICIAN_APPROVER_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> TreatmentPlanResponse:
    """修訂 Plan：approved/active → superseded + 建立新版本（A-12）。

    需要 Clinician / Admin 角色。
    """
    service = _get_service(db)
    try:
        result = await service.revise_plan(
            plan_id=plan_id,
            request=request,
            user_id=str(user.id),
        )
        return result
    except Exception as exc:
        _handle_service_error(exc, "Error in revise_plan")


__all__ = [
    "router",
]
