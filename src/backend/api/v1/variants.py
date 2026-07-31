"""
Variant API routes.
"""
from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.api.v1.deps import get_variant_repo
from src.backend.auth.dependencies import require_auth, verify_case_access
from src.backend.database.session import get_db
from src.backend.domain.case_acl import CaseRole
from src.backend.domain.user import UserModel
from src.backend.domain.variant import VariantImportBatch, VariantResponse
from src.backend.repositories.sequencing_test_repo import SequencingTestRepository
from src.backend.repositories.specimen_repo import SpecimenRepository
from src.backend.repositories.variant_repo import VariantRepository
from src.backend.services.variant_ingestion_service import VariantIngestionService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/variants", tags=["variants"])


async def _resolve_sequencing_test_case_id(
    sequencing_test_id: uuid.UUID,
    db: AsyncSession,
) -> uuid.UUID:
    """Resolve case_id from a sequencing_test_id through specimen."""
    st_repo = SequencingTestRepository(db)
    st = await st_repo.get(sequencing_test_id)
    if not st or not st.specimen_id:
        raise HTTPException(status_code=400, detail="Sequencing test not found or missing specimen association")
    spec_repo = SpecimenRepository(db)
    spec = await spec_repo.get(st.specimen_id)
    if not spec or not spec.case_id:
        raise HTTPException(status_code=400, detail="Specimen not found or missing case association")
    return spec.case_id


@router.post("/import", response_model=list[VariantResponse], status_code=201)
async def import_variants(
    body: VariantImportBatch,
    request: Request,
    user: UserModel = Depends(require_auth),
    repo: VariantRepository = Depends(get_variant_repo),
    db: AsyncSession = Depends(get_db),
):
    # Verify EDITOR access for each unique sequencing_test_id
    seen_case_ids = set()
    for item in body.items:
        try:
            st_id = uuid.UUID(item.sequencing_test_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid sequencing_test_id in variant batch")

        if st_id not in seen_case_ids:
            seen_case_ids.add(st_id)
            case_id = await _resolve_sequencing_test_case_id(st_id, db)
            await verify_case_access(case_id, user, db, CaseRole.EDITOR)

    try:
        items_data = [item.model_dump(exclude_none=True) for item in body.items]
        service = VariantIngestionService(db)
        variants = await service.bulk_create_variants(items_data)
        return [VariantResponse.model_validate(v) for v in variants]
    except HTTPException:
        # 合法 4xx 業務錯誤（如 400）透傳，不轉換為 500
        raise
    except Exception:
        # REVIEW-PHASE3F0-R3-P1-02 / REVIEW-RESOLVED
        # 問題：直接把 str(e) 回傳給 API 用戶，可能洩漏 SQL、資料表、constraint、
        # 驅動或內部路徑資訊；同時所有業務錯誤均被壓成無差別 500。
        # 修改：保留並重新拋出既有 HTTPException；其餘例外只記錄完整 server log，
        # 對外回傳固定、安全的錯誤訊息與可追蹤 request/error id，不得暴露原始例外。
        # 驗證：新增測試證明內部 DB 例外文字不會出現在 response body，且合法的
        # 4xx 業務錯誤不會被轉換為 500。
        # RESOLUTION (REVIEW-PHASE3F0-R3-P1-02): except HTTPException 4xx 透傳；其餘例外僅記錄完整
        # server log 並回傳固定訊息 + error_id（request.state.request_id / X-Request-ID / uuid4），
        # 不再洩漏 str(e)；驗證測試 test_phase3f0_r3_p1_variants_errors.py 通過。
        error_id = getattr(request.state, "request_id", None) or request.headers.get(
            "X-Request-ID"
        ) or str(uuid.uuid4())
        logger.exception(
            "Failed to import variants [error_id=%s]", error_id,
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error": "internal_error",
                "error_id": error_id,
                "message": "Internal server error",
            },
        )
