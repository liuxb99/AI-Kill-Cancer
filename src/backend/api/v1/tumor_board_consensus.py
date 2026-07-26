"""
Tumor Board Consensus API — multi-disciplinary consensus endpoints.

Provides:
- POST /api/v1/tumor-board-consensus        — Create a tumor board consensus
- GET  /api/v1/tumor-board-consensus/{consensus_id}       — Retrieve a consensus
- GET  /api/v1/tumor-board-consensus                       — List consensuses by patient
- GET  /api/v1/tumor-board-consensus/{consensus_id}/opinions — Get opinions for a consensus
- GET  /api/v1/tumor-board-consensus/{consensus_id}/trace    — Get calculation trace
"""

from __future__ import annotations

import logging

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.auth.dependencies import require_auth
from src.backend.database.session import get_db
from src.backend.domain.user import UserModel
from src.backend.services.tumor_board_service import (
    ConsensusListResponse,
    ConsensusResponse,
    CreateConsensusRequest,
    TumorBoardConsensusService,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tumor-board-consensus", tags=["Tumor Board Consensus"])


@router.post("", response_model=ConsensusResponse, status_code=201)
async def create_tumor_board_consensus(
    request: CreateConsensusRequest,
    user: UserModel = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> ConsensusResponse:
    """
    建立 Tumor Board Consensus。

    輸入 patient_id, recommendation_id, clinical_decision_id,
    specialist_opinions 等資訊，
    回傳 Consensus（含 consensus_status, consensus_score, 各項意見總結）。
    """
    service = TumorBoardConsensusService(db=db)
    try:
        result = await service.create_consensus(
            request=request,
            created_by=str(user.id),
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except RuntimeError:
        raise HTTPException(status_code=500, detail="Internal server error")
    except Exception:
        logger.exception("Unexpected error in create_tumor_board_consensus")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("", response_model=list[ConsensusListResponse])
async def list_tumor_board_consensuses(
    patient_id: str = Query(..., description="UUID string of the patient"),
    skip: int = Query(ge=0, default=0, description="Number of records to skip"),
    limit: int = Query(
        ge=1, le=100, default=20, description="Max records to return"
    ),
    user: UserModel = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> list[ConsensusListResponse]:
    """依 patient_id 查詢 Tumor Board Consensus 列表。"""
    service = TumorBoardConsensusService(db=db)
    try:
        results = await service.list_consensus(
            patient_id=patient_id,
            skip=skip,
            limit=limit,
        )
        return results
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception:
        logger.exception("Unexpected error in list_tumor_board_consensuses")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{consensus_id}", response_model=ConsensusResponse)
async def get_tumor_board_consensus(
    consensus_id: str,
    user: UserModel = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> ConsensusResponse:
    """依 consensus_id 查詢 Tumor Board Consensus。"""
    service = TumorBoardConsensusService(db=db)
    try:
        result = await service.get_consensus(consensus_id=consensus_id)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except RuntimeError:
        raise HTTPException(status_code=500, detail="Internal server error")
    except Exception:
        logger.exception("Unexpected error in get_tumor_board_consensus")
        raise HTTPException(status_code=500, detail="Internal server error")

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Tumor board consensus not found",
        )
    return result


@router.get("/{consensus_id}/opinions", response_model=list[dict[str, Any]])
async def get_tumor_board_consensus_opinions(
    consensus_id: str,
    user: UserModel = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """依 consensus_id 查詢 Tumor Board Consensus 的專家意見。"""
    service = TumorBoardConsensusService(db=db)
    try:
        opinions = await service.get_opinions(consensus_id=consensus_id)
        return opinions
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception:
        logger.exception(
            "Unexpected error in get_tumor_board_consensus_opinions"
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{consensus_id}/trace", response_model=list[dict[str, Any]])
async def get_tumor_board_consensus_trace(
    consensus_id: str,
    user: UserModel = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """依 consensus_id 查詢 Tumor Board Consensus 的計算追蹤。"""
    service = TumorBoardConsensusService(db=db)
    try:
        trace = await service.get_trace(consensus_id=consensus_id)
        return trace
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception:
        logger.exception(
            "Unexpected error in get_tumor_board_consensus_trace"
        )
        raise HTTPException(status_code=500, detail="Internal server error")
