"""
Variant API routes.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from src.backend.api.v1.deps import get_variant_repo
from src.backend.domain.variant import VariantImportBatch, VariantResponse
from src.backend.repositories.variant_repo import VariantRepository

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/variants", tags=["variants"])


@router.post("/import", response_model=list[VariantResponse], status_code=201)
async def import_variants(
    body: VariantImportBatch,
    repo: VariantRepository = Depends(get_variant_repo),
):
    try:
        items = [item.model_dump(exclude_none=True) for item in body.items]
        variants = await repo.bulk_create(items)
        return [VariantResponse.model_validate(v) for v in variants]
    except Exception as e:
        logger.exception("Failed to import variants")
        raise HTTPException(status_code=500, detail=str(e))
