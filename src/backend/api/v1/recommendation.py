"""
Recommendation API — evidence-based drug recommendation endpoints.

Provides:
- POST /api/v1/recommendation  — Run the full recommendation pipeline
- GET  /api/v1/recommendation/{recommendation_id}  — Retrieve a stored result
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.auth.dependencies import require_auth
from src.backend.database.session import get_db
from src.backend.domain.user import UserModel
from src.backend.services.recommendation_service import RecommendationService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/recommendation", tags=["recommendation"])

_ENGINE_VERSION = "1.0.0"
"""Current version of the recommendation engine."""


# ─── Pydantic models ──────────────────────────────────────────────────────────


class RecommendationRequest(BaseModel):
    """Request body for creating a new recommendation."""

    patient_id: str = Field(
        ..., min_length=1, description="Unique patient identifier."
    )
    variants: list[str] = Field(
        ...,
        min_length=1,
        description=(
            "List of variant strings, each in 'GENE change' format, "
            "e.g. ['EGFR L858R', 'KRAS G12C'].  Bare gene names are "
            "accepted when the protein change is unknown."
        ),
    )
    patient_context: dict[str, Any] | None = Field(
        default=None,
        description=(
            "Optional patient metadata (age, gender, diagnosis, stage, "
            "cancer_type, histology, oncotree_code, etc.) used to build "
            "the clinical context snapshot."
        ),
    )
    top_n: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Number of top-ranked drugs to include in the response.",
    )


class RecommendationDrugItem(BaseModel):
    """A single drug recommendation with sub-scores and explanations."""

    drug_name: str = Field(..., description="Name of the recommended drug.")
    rank: int = Field(..., ge=1, description="1-based rank position.")
    overall_score: float = Field(
        ..., description="Composite overall score (higher is better)."
    )
    evidence_score: float = Field(
        ..., ge=0.0, le=1.0, description="Evidence confidence score."
    )
    sensitivity_score: float = Field(
        ..., ge=0.0, le=1.0, description="Sensitivity score (response likelihood)."
    )
    resistance_score: float = Field(
        ..., ge=0.0, le=1.0, description="Resistance score (higher = more resistant)."
    )
    conflict_score: float = Field(
        ..., ge=0.0, le=1.0, description="Conflict score (higher = more contradictory evidence)."
    )
    explanations: list[dict[str, Any]] = Field(
        default_factory=list,
        description=(
            "Ordered list of explanation fragments.  Each fragment contains "
            "`category`, `detail`, `source`, `score_impact`, and optionally "
            "`trace_id`."
        ),
    )


class RecommendationResponse(BaseModel):
    """Response returned by the recommendation pipeline."""

    recommendation_id: str = Field(
        ..., description="Unique identifier for this recommendation run."
    )
    patient_id: str = Field(
        ..., description="Patient identifier from the request."
    )
    recommendations: list[RecommendationDrugItem] = Field(
        ..., description="Top-N ranked drug recommendations with explanations."
    )
    trace_id: str = Field(
        ..., description="Calculation trace ID for full auditability."
    )
    engine_version: str = Field(
        default=_ENGINE_VERSION,
        description="Version of the recommendation engine.",
    )
    report_html: str | None = Field(
        default=None,
        description="Optional self-contained HTML report document.",
    )
    created_at: str = Field(
        ..., description="ISO-8601 UTC timestamp of creation."
    )


# ─── POST /api/v1/recommendation ──────────────────────────────────────────────


@router.post("", response_model=RecommendationResponse)
async def create_recommendation(
    request: RecommendationRequest,
    user: UserModel = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> RecommendationResponse:
    """Run the full recommendation pipeline and return top-N drug recommendations.

    Orchestration is delegated to ``RecommendationService``, which handles
    all business logic, pipeline execution, and persistence.

    Parameters
    ----------
    request : RecommendationRequest
        The validated request payload.
    user : UserModel
        The authenticated user (injected via ``require_auth``).
    db : AsyncSession
        SQLAlchemy async session (injected via ``get_db``).

    Returns
    -------
    RecommendationResponse
        The computed recommendation with ranked drugs and explanations.

    Raises
    ------
    HTTPException 422
        If no evidence is found for the provided variants, or if no drugs
        could be ranked.
    HTTPException 500
        If the pipeline encounters an unrecoverable error.  The error
        detail is intentionally generic to avoid leaking internals.
    """
    service = RecommendationService(db)

    try:
        result = await service.create_recommendation(
            request_data=request.model_dump(),
            user_id=str(user.id),
        )
    except ValueError as exc:
        # Known business-rule failures: no evidence, no rankings
        logger.warning("Recommendation request failed: %s", exc)
        raise HTTPException(
            status_code=422,
            detail={
                "error": "validation_failed",
                "message": str(exc),
            },
        )
    except Exception:
        logger.exception("Recommendation processing failed")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "INTERNAL_ERROR",
                "message": "Recommendation processing failed.",
            },
        )

    return RecommendationResponse(**result)


# ─── GET /api/v1/recommendation/{recommendation_id} ────────────────────────────


@router.get("/{recommendation_id}", response_model=RecommendationResponse)
async def get_recommendation(
    recommendation_id: str,
    user: UserModel = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> RecommendationResponse:
    """Retrieve a previously computed recommendation by its ID.

    Reads from the database via ``RecommendationService.get_recommendation``.
    No fallback to in-memory storage, recalculation, or mock data.

    Args:
        recommendation_id: The hex-string UUID returned by the POST endpoint.

    Returns:
        The full ``RecommendationResponse`` exactly as originally returned.

    Raises:
        HTTPException 404 if the recommendation ID is not found.
    """
    service = RecommendationService(db)

    try:
        result = await service.get_recommendation(recommendation_id)
    except Exception:
        logger.exception("Failed to retrieve recommendation %s", recommendation_id)
        raise HTTPException(
            status_code=500,
            detail={
                "error": "INTERNAL_ERROR",
                "message": "Recommendation retrieval failed.",
            },
        )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": "not_found",
                "message": (
                    f"Recommendation not found: {recommendation_id}.  "
                    f"Verify the ID or create a new recommendation via "
                    f"POST /api/v1/recommendation."
                ),
            },
        )

    return RecommendationResponse(**result)
