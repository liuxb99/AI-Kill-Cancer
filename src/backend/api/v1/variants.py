"""
Variant API routes.
"""
from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
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
        variants = await repo.bulk_create(items_data)
        return [VariantResponse.model_validate(v) for v in variants]
    except Exception as e:
        logger.exception("Failed to import variants")
        raise HTTPException(status_code=500, detail=str(e))
