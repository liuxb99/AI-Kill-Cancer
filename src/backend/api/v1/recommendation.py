"""
Recommendation API — evidence-based drug recommendation endpoints.

Provides:
- POST /api/v1/recommendation  — Run the full recommendation pipeline
- GET  /api/v1/recommendation/{recommendation_id}  — Retrieve a stored result
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.auth.dependencies import require_auth
from src.backend.clinical.calculation_trace import TraceManager
from src.backend.clinical.collector import EvidenceCollector
from src.backend.clinical.drug_ranking import DrugRankingEngine, DrugRankingResult
from src.backend.clinical.evidence_weight import WeightRegistry
from src.backend.clinical.explainable_recommendation import ExplainableEngine
from src.backend.clinical.models import ClinicalContext
from src.backend.clinical.report_generator import ReportGenerator
from src.backend.clinical.recommendation_engine import (
    DrugRanker,
    EvidenceAggregator,
    RecommendationEngine,
)
from src.backend.database.session import get_db
from src.backend.domain.user import UserModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/recommendation", tags=["recommendation"])

# In-memory store for recommendation results (can be replaced with DB later).
_recommendations: dict[str, dict[str, Any]] = {}

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


# ─── Helper: parse variant string ─────────────────────────────────────────────


def _parse_variant(variant_str: str) -> tuple[str, str]:
    """Parse a variant string into ``(gene_symbol, protein_change)``.

    Accepts formats like ``"EGFR L858R"``, ``"KRAS G12C"``, or a bare
    gene name such as ``"EGFR"`` (protein_change will be empty).
    """
    stripped = variant_str.strip()
    parts = stripped.split(maxsplit=1)
    gene = parts[0]
    protein_change = parts[1] if len(parts) > 1 else ""
    return gene, protein_change


# ─── POST /api/v1/recommendation ──────────────────────────────────────────────


@router.post("", response_model=RecommendationResponse)
async def create_recommendation(
    request: RecommendationRequest,
    user: UserModel = Depends(require_auth),
    db: AsyncSession = Depends(get_db),
) -> RecommendationResponse:
    """Run the full recommendation pipeline and return top-N drug recommendations.

    Pipeline
    --------
    1. **WeightRegistry** — default source weight mappings are loaded at import.
    2. **ClinicalContext** — built from *patient_id*, *variants*, and optional
       *patient_context* metadata.
    3. **EvidenceCollector** — gathers clinical evidence for each variant from
       CIViC, DGIdb, ClinVar, PubMed, and ClinicalTrials.gov.
    4. **EvidenceAggregator + DrugRanker** — aggregate evidence by drug and
       produce an initial ranking.
    5. **RecommendationEngine.run()** — orchestrates collection, aggregation,
       ranking, and rule evaluation.
    6. **DrugRankingEngine** — computes detailed sub-scores (evidence,
       sensitivity, resistance, conflict) and a composite overall score.
    7. **ExplainableEngine** — generates human-readable, traceable explanation
       fragments for every ranked drug.
    8. **Response assembly** — top-N drugs with scores and explanations.

    Raises
    ------
    HTTPException 422
        If no evidence is found for the provided variants, or if no drugs
        could be ranked.
    HTTPException 500
        If the pipeline encounters an unrecoverable error.
    """
    recommendation_id = uuid.uuid4().hex

    # ── Parse variant strings ──────────────────────────────────────────────
    parsed_variants: list[dict[str, str]] = [
        {"gene_symbol": gene, "protein_change": change}
        for gene, change in (_parse_variant(v) for v in request.variants)
    ]

    # ── Build ClinicalContext ──────────────────────────────────────────────
    ctx = request.patient_context or {}
    context = ClinicalContext(
        case_id=f"rec-{recommendation_id[:12]}",
        patient_id=request.patient_id,
        age=ctx.get("age", 0),
        gender=ctx.get("gender", "unknown"),
        diagnosis=ctx.get("diagnosis", ""),
        stage=ctx.get("stage", ""),
        histology=ctx.get("histology", ""),
        cancer_type=ctx.get("cancer_type", ""),
        oncotree_code=ctx.get("oncotree_code"),
        variants=parsed_variants,
    )
    context.freeze()

    # ── Step 1: WeightRegistry ──────────────────────────────────────────────
    # Default sources (FDA, NCCN, OncoKB, CIViC, DGIdb, OpenCRAVAT) are
    # registered at import time by src.backend.clinical.evidence_weight.
    _ = WeightRegistry  # ensure the module is loaded

    # ── Steps 2–3: Instantiate pipeline components ─────────────────────────
    collector = EvidenceCollector(db)
    aggregator = EvidenceAggregator()
    ranker = DrugRanker()
    ranking_engine = DrugRankingEngine()

    # ── Step 4: TraceManager ───────────────────────────────────────────────
    trace_manager = TraceManager()
    trace = trace_manager.start_trace(patient_id=request.patient_id)
    trace_id = trace.trace_id

    # ── Step 5: RecommendationEngine.run() ─────────────────────────────────
    engine = RecommendationEngine(
        collector=collector,
        aggregator=aggregator,
        ranker=ranker,
        trace_manager=trace_manager,
    )

    pipeline_result: dict[str, Any]
    try:
        pipeline_result = await engine.run(patient_context=context)
    except Exception as exc:
        logger.exception("Recommendation pipeline raised an unhandled exception.")
        trace_manager.complete_trace(trace_id, status="failed")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "pipeline_crash",
                "message": (
                    "The recommendation pipeline encountered an internal "
                    f"error: {exc}"
                ),
            },
        )

    pipeline_status: str = pipeline_result.get("pipeline_status", "")
    if pipeline_status.startswith("error"):
        trace_manager.complete_trace(trace_id, status="failed")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "pipeline_failed",
                "message": (
                    "The recommendation pipeline did not complete "
                    f"successfully: {pipeline_status}"
                ),
            },
        )

    aggregated_data: dict[str, dict] = pipeline_result.get("aggregated", {})
    if not aggregated_data:
        trace_manager.complete_trace(trace_id, status="failed")
        raise HTTPException(
            status_code=422,
            detail={
                "error": "no_evidence",
                "message": (
                    f"No clinical evidence could be found for the provided "
                    f"variants: {request.variants}.  Please verify the "
                    f"variant names and try again."
                ),
            },
        )

    # ── Step 6: DrugRankingEngine detailed scoring ─────────────────────────
    ranking_results: list[DrugRankingResult] = ranking_engine.rank(
        aggregated_data,
        top_n=request.top_n,
    )

    if not ranking_results:
        trace_manager.complete_trace(trace_id, status="failed")
        raise HTTPException(
            status_code=422,
            detail={
                "error": "no_rankings",
                "message": (
                    "No drugs could be ranked based on the available "
                    "evidence.  This may indicate insufficient or "
                    "contradictory evidence for the provided variants."
                ),
            },
        )

    # ── Step 7: ExplainableEngine ──────────────────────────────────────────
    explainable = ExplainableEngine(
        ranking_engine=ranking_engine,
        aggregated_data=aggregated_data,
    )
    explanations = explainable.generate_explanations(ranking_results)

    # ── Assemble response ──────────────────────────────────────────────────
    recommendations: list[RecommendationDrugItem] = []
    for result, explanation in zip(ranking_results, explanations):
        recommendations.append(
            RecommendationDrugItem(
                drug_name=result.drug_name,
                rank=result.rank,
                overall_score=result.overall_score.raw_score,
                evidence_score=result.evidence_score.confidence_score,
                sensitivity_score=result.sensitivity.score,
                resistance_score=result.resistance.score,
                conflict_score=result.conflict_score.score,
                explanations=[r.model_dump() for r in explanation.reasons],
            )
        )

    trace_manager.complete_trace(trace_id, status="completed")

    # ── Retrieve trace steps for report ─────────────────────────────────────
    trace_steps: list[dict] = []
    pipeline_evidence_count: int = pipeline_result.get("evidence_count", 0)
    pipeline_rules_evaluated: int = pipeline_result.get("rules_evaluated", 0)
    pipeline_rules_fired: int = pipeline_result.get("rules_fired", 0)
    calc_trace = trace_manager.get_trace(trace_id)
    if calc_trace is not None:
        try:
            trace_steps = [s.model_dump() for s in calc_trace.steps]
        except Exception:
            logger.debug("Failed to serialise trace steps for report.", exc_info=True)

    response = RecommendationResponse(
        recommendation_id=recommendation_id,
        patient_id=request.patient_id,
        recommendations=recommendations,
        trace_id=trace_id,
        engine_version=_ENGINE_VERSION,
        created_at=datetime.now(UTC).isoformat(),
    )

    # ── Generate HTML report ────────────────────────────────────────────────
    try:
        generator = ReportGenerator()
        report_html = generator.generate(
            response,
            variants=request.variants,
            evidence_count=pipeline_evidence_count,
            rules_evaluated=pipeline_rules_evaluated,
            rules_fired=pipeline_rules_fired,
            trace_steps=trace_steps,
        )
        response.report_html = report_html
    except Exception:
        logger.exception("Failed to generate HTML report — continuing without it.")

    # Persist in memory for GET retrieval.
    _recommendations[recommendation_id] = response.model_dump()

    return response


# ─── GET /api/v1/recommendation/{recommendation_id} ────────────────────────────


@router.get("/{recommendation_id}", response_model=RecommendationResponse)
async def get_recommendation(
    recommendation_id: str,
    user: UserModel = Depends(require_auth),
) -> RecommendationResponse:
    """Retrieve a previously computed recommendation by its ID.

    Args:
        recommendation_id: The hex-string UUID returned by the POST endpoint.

    Returns:
        The full ``RecommendationResponse`` exactly as originally returned.

    Raises:
        HTTPException 404 if the recommendation ID is not found.
    """
    stored = _recommendations.get(recommendation_id)
    if stored is None:
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
    return RecommendationResponse(**stored)
