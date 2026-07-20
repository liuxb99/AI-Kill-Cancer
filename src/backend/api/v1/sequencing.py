"""
Sequencing test API routes.
"""
from __future__ import annotations

import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException

from src.backend.api.v1.deps import get_sequencing_repo
from src.backend.domain.sequencing_test import SequencingTestCreate, SequencingTestResponse
from src.backend.repositories.sequencing_test_repo import SequencingTestRepository

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sequencing-tests", tags=["sequencing-tests"])


@router.post("", response_model=SequencingTestResponse, status_code=201)
async def create_sequencing_test(
    body: SequencingTestCreate,
    repo: SequencingTestRepository = Depends(get_sequencing_repo),
):
    try:
        test = await repo.create(**body.model_dump(exclude_none=True))
        return SequencingTestResponse.model_validate(test)
    except Exception as e:
        logger.exception("Failed to create sequencing test")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{test_id}", response_model=SequencingTestResponse)
async def get_sequencing_test(
    test_id: str,
    repo: SequencingTestRepository = Depends(get_sequencing_repo),
):
    try:
        tid = uuid.UUID(test_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid test ID")

    test = await repo.get(tid)
    if not test:
        raise HTTPException(status_code=404, detail="Sequencing test not found")
    return SequencingTestResponse.model_validate(test)
