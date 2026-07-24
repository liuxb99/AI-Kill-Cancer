"""
Recommendation Service — orchestrates the full recommendation pipeline.

Responsibilities
----------------
1. Accept request DTO from the API layer
2. Execute the recommendation pipeline (EvidenceCollector → Aggregator →
   DrugRanker → RecommendationEngine → DrugRankingEngine → ExplainableEngine)
3. Persist recommendation record via ``RecommendationRepository``
4. Persist calculation trace records via ``TraceRepository``
5. Generate HTML report via ``ReportGenerator``
6. Manage the transaction boundary (commit on success, rollback on failure)
7. Return a structured response DTO

The API router delegates all business logic here — the router only handles
request validation, authentication, calling the service, and exception mapping.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.clinical.calculation_trace import TraceManager
from src.backend.clinical.collector import EvidenceCollector
from src.backend.clinical.drug_ranking import DrugRankingEngine
from src.backend.clinical.evidence_weight import WeightRegistry
from src.backend.clinical.explainable_recommendation import ExplainableEngine
from src.backend.clinical.models import ClinicalContext
from src.backend.clinical.report_generator import ReportGenerator
from src.backend.clinical.recommendation_engine import (
    DrugRanker,
    EvidenceAggregator,
    RecommendationEngine,
)
from src.backend.domain.enums import RecommendationStatusEnum
from src.backend.domain.recommendation import (
    RecommendationModel,
    RecommendationTraceModel,
    RecommendationTraceStepModel,
)
from src.backend.repositories.recommendation_repo import (
    RecommendationRepository,
    TraceRepository,
)

logger = logging.getLogger(__name__)

_ENGINE_VERSION = "1.0.0"


class RecommendationService:
    """Orchestrates the recommendation pipeline and persists results.

    All business logic lives here; the API router calls this service and
    maps the result to HTTP responses.

    Parameters
    ----------
    db : AsyncSession
        The SQLAlchemy async session to use for all persistence.
        Transaction management (commit / rollback) is handled by this service.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._recommendation_repo = RecommendationRepository(db)
        self._trace_repo = TraceRepository(db)

    # ── Public API ─────────────────────────────────────────────────────────

    async def create_recommendation(
        self,
        request_data: dict[str, Any],
        user_id: str,
    ) -> dict[str, Any]:
        """Run the full recommendation pipeline and persist results.

        Parameters
        ----------
        request_data : dict
            The validated request payload.  Expected keys:
            - ``patient_id`` (str)
            - ``variants`` (list[str])
            - ``patient_context`` (dict, optional)
            - ``top_n`` (int, optional, default 5)
        user_id : str
            The authenticated user's UUID string.

        Returns
        -------
        dict
            A serialised ``RecommendationResponse``-compatible dictionary
            with keys: ``recommendation_id``, ``patient_id``,
            ``recommendations``, ``trace_id``, ``engine_version``,
            ``report_html``, ``created_at``.

        Raises
        ------
        ValueError
            If the pipeline produces no evidence or no rankings.
        RuntimeError
            If the pipeline crashes.
        """
        recommendation_id = uuid.uuid4().hex
        patient_id: str = request_data["patient_id"]
        variants: list[str] = request_data.get("variants", [])
        patient_context: dict[str, Any] | None = request_data.get("patient_context")
        top_n: int = request_data.get("top_n", 5)

        # ── Parse variant strings ──────────────────────────────────────────
        parsed_variants: list[dict[str, str]] = [
            {"gene_symbol": gene, "protein_change": change}
            for gene, change in (self._parse_variant(v) for v in variants)
        ]

        # ── Build ClinicalContext ──────────────────────────────────────────
        ctx = patient_context or {}
        context = ClinicalContext(
            case_id=f"rec-{recommendation_id[:12]}",
            patient_id=patient_id,
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

        # ── Ensure WeightRegistry is loaded ─────────────────────────────────
        _ = WeightRegistry  # force module-level registrations

        # ── Prepare pipeline components ────────────────────────────────────
        collector = EvidenceCollector(self._db)
        aggregator = EvidenceAggregator()
        ranker = DrugRanker()
        ranking_engine = DrugRankingEngine()

        # In-memory TraceManager for step-level tracing during pipeline run
        trace_manager = TraceManager()
        trace = trace_manager.start_trace(patient_id=patient_id)
        trace_id = trace.trace_id

        engine = RecommendationEngine(
            collector=collector,
            aggregator=aggregator,
            ranker=ranker,
            trace_manager=trace_manager,
        )

        # ── Run pipeline ────────────────────────────────────────────────────
        try:
            pipeline_result = await engine.run(patient_context=context)
        except Exception as exc:
            logger.exception("Recommendation pipeline raised an unhandled exception.")
            trace_manager.complete_trace(trace_id, status="failed")
            raise RuntimeError("Recommendation pipeline encountered an internal error") from exc

        pipeline_status: str = pipeline_result.get("pipeline_status", "")
        if pipeline_status.startswith("error"):
            trace_manager.complete_trace(trace_id, status="failed")
            raise RuntimeError(
                "Recommendation pipeline did not complete successfully",
            )

        aggregated_data: dict[str, dict] = pipeline_result.get("aggregated", {})
        if not aggregated_data:
            trace_manager.complete_trace(trace_id, status="failed")
            raise ValueError(
                "No clinical evidence found for the provided variants",
            )

        # ── DrugRankingEngine detailed scoring ──────────────────────────────
        ranking_results = ranking_engine.rank(aggregated_data, top_n=top_n)
        if not ranking_results:
            trace_manager.complete_trace(trace_id, status="failed")
            raise ValueError("No drugs could be ranked based on available evidence.")

        # ── ExplainableEngine ───────────────────────────────────────────────
        explainable = ExplainableEngine(
            ranking_engine=ranking_engine,
            aggregated_data=aggregated_data,
        )
        explanations = explainable.generate_explanations(ranking_results)

        # ── Assemble response data ──────────────────────────────────────────
        recommendations: list[dict[str, Any]] = []
        for result, explanation in zip(ranking_results, explanations):
            recommendations.append(
                {
                    "drug_name": result.drug_name,
                    "rank": result.rank,
                    "overall_score": result.overall_score.raw_score,
                    "evidence_score": result.evidence_score.confidence_score,
                    "sensitivity_score": result.sensitivity.score,
                    "resistance_score": result.resistance.score,
                    "conflict_score": result.conflict_score.score,
                    "explanations": [r.model_dump() for r in explanation.reasons],
                },
            )

        trace_manager.complete_trace(trace_id, status="completed")

        # ── Retrieve trace steps for report ─────────────────────────────────
        trace_steps: list[dict] = []
        pipeline_evidence_count: int = pipeline_result.get("evidence_count", 0)
        pipeline_rules_evaluated: int = pipeline_result.get("rules_evaluated", 0)
        pipeline_rules_fired: int = pipeline_result.get("rules_fired", 0)
        calc_trace = trace_manager.get_trace(trace_id)
        if calc_trace is not None:
            try:
                trace_steps = [s.model_dump() for s in calc_trace.steps]
            except Exception:
                logger.debug("Failed to serialise trace steps.", exc_info=True)

        created_at = datetime.now(UTC).isoformat()

        response: dict[str, Any] = {
            "recommendation_id": recommendation_id,
            "patient_id": patient_id,
            "recommendations": recommendations,
            "trace_id": trace_id,
            "engine_version": _ENGINE_VERSION,
            "report_html": None,
            "created_at": created_at,
        }

        # ── Generate HTML report ────────────────────────────────────────────
        try:
            from src.backend.api.v1.recommendation import RecommendationResponse

            # Build a temporary RecommendationResponse for the ReportGenerator
            resp = RecommendationResponse(**response)
            generator = ReportGenerator()
            report_html = generator.generate(
                resp,
                variants=variants,
                evidence_count=pipeline_evidence_count,
                rules_evaluated=pipeline_rules_evaluated,
                rules_fired=pipeline_rules_fired,
                trace_steps=trace_steps,
            )
            response["report_html"] = report_html
        except Exception:
            logger.exception("Failed to generate HTML report — continuing without it.")

        # ── Persist via repositories (transaction managed here) ──────────────
        try:
            await self._persist_recommendation(
                recommendation_id=recommendation_id,
                patient_id=patient_id,
                trace_id=trace_id,
                request_data=request_data,
                result_data=response,
                user_id=user_id,
                trace_manager=trace_manager,
            )
            await self._db.commit()
        except Exception:
            await self._db.rollback()
            logger.exception(
                "Failed to persist recommendation %s — rolled back.",
                recommendation_id,
            )
            # Return the in-memory result even if persistence fails
            # (the pipeline result is still valid for the caller)

        return response

    async def get_recommendation(
        self,
        recommendation_id: str,
    ) -> Optional[dict[str, Any]]:
        """Retrieve a previously persisted recommendation by its ID.

        Parameters
        ----------
        recommendation_id : str
            The hex-string UUID returned by ``create_recommendation``.

        Returns
        -------
        dict | None
            A serialised ``RecommendationResponse``-compatible dictionary,
            or ``None`` if not found.
        """
        model = await self._recommendation_repo.get_by_id(recommendation_id)
        if model is None:
            return None

        # Deserialise the stored result payload
        result_payload: dict[str, Any] = model.result_payload or {}
        return {
            "recommendation_id": model.recommendation_id,
            "patient_id": str(model.patient_id) if model.patient_id else "",
            "recommendations": result_payload.get("recommendations", []),
            "trace_id": model.trace_id or "",
            "engine_version": model.engine_version,
            "report_html": model.report_html,
            "created_at": (
                model.created_at.isoformat() if model.created_at else ""
            ),
        }

    # ── Internal helpers ───────────────────────────────────────────────────

    @staticmethod
    def _parse_variant(variant_str: str) -> tuple[str, str]:
        """Parse a variant string into ``(gene_symbol, protein_change)``.

        Accepts ``"EGFR L858R"``, ``"KRAS G12C"``, or a bare gene name.
        """
        stripped = variant_str.strip()
        parts = stripped.split(maxsplit=1)
        gene = parts[0]
        protein_change = parts[1] if len(parts) > 1 else ""
        return gene, protein_change

    async def _persist_recommendation(
        self,
        *,
        recommendation_id: str,
        patient_id: str,
        trace_id: str,
        request_data: dict[str, Any],
        result_data: dict[str, Any],
        user_id: str,
        trace_manager: TraceManager,
    ) -> None:
        """Persist the recommendation, trace, and steps in a single session.

        Does **not** commit — the caller is responsible for calling
        ``self._db.commit()`` (and ``self._db.rollback()`` on failure).
        """
        # ── Recommendation record ──────────────────────────────────────────
        rec_model = RecommendationModel(
            recommendation_id=recommendation_id,
            patient_id=uuid.UUID(patient_id) if patient_id else None,
            trace_id=trace_id,
            engine_version=_ENGINE_VERSION,
            status=RecommendationStatusEnum.COMPLETED.value,
            request_payload=request_data,
            result_payload=result_data,
            report_html=result_data.get("report_html"),
            created_by=uuid.UUID(user_id) if user_id else None,
        )
        await self._recommendation_repo.create(rec_model)

        # ── Trace record ───────────────────────────────────────────────────
        calc_trace = trace_manager.get_trace(trace_id)
        if calc_trace is not None:
            # Flush to ensure rec_model.id is assigned
            await self._db.flush()

            trace_model = RecommendationTraceModel(
                trace_id=trace_id,
                recommendation_id=rec_model.id,
            )
            await self._trace_repo.create_trace(trace_model)

            # Flush to ensure trace_model.id is assigned before creating steps
            await self._db.flush()

            # Persist individual steps
            for idx, step in enumerate(calc_trace.steps):
                step_model = RecommendationTraceStepModel(
                    trace_id=trace_model.id,
                    step_order=idx,
                    step_type=step.step_type,
                    input_summary=step.input_data,
                    output_summary=step.output_data,
                    weight=step.input_data.get("weight") if isinstance(step.input_data, dict) else None,
                    status="completed",
                )
                await self._trace_repo.create_step(step_model)
