"""
Clinical Decision Service — orchestrates clinical decision generation.

Responsibilities
----------------
1. Accept request parameters from the API layer
2. Retrieve patient and recommendation data from the database
3. Call ``ClinicalDecisionEngine.evaluate()`` to produce a decision
4. Persist ``ClinicalDecisionModel`` + ``ClinicalDecisionTraceModel``
5. Manage the transaction boundary (commit on success, rollback on failure)
6. Return a structured ``ClinicalDecisionResponse`` DTO

The API router delegates all business logic here — the router only handles
request validation, authentication, calling the service, and exception mapping.
"""

from __future__ import annotations

import logging
import uuid as _uuid
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.clinical.clinical_decision_engine import (
    ClinicalDecisionEngine,
    ClinicalDecisionResult,
)
from src.backend.domain.clinical_decision import (
    ClinicalDecisionModel,
    ClinicalDecisionTraceModel,
)
from src.backend.repositories.clinical_decision_repo import (
    ClinicalDecisionRepository,
    ClinicalDecisionTraceRepository,
)
from src.backend.schemas.clinical_graph_event import (
    GraphAggregateType,
    GraphEventType,
)
from src.backend.services.clinical_graph_event_service import (
    ClinicalGraphEventService,
)

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# Pydantic DTOs
# ═══════════════════════════════════════════════════════════════════════════════


class ClinicalDecisionRequest(BaseModel):
    """Request DTO for creating a clinical decision.

    Attributes
    ----------
    patient_id : str
        UUID string identifying the patient.
    recommendation_id : str
        UUID string identifying the recommendation to base the decision on.
    variants : list[dict]
        List of variant dictionaries, each containing at minimum
        ``gene_symbol`` and optionally ``protein_change`` /
        ``clinical_significance``.
    context : dict | None
        Optional free-form context.  May include ``evidence`` (list of
        evidence dicts), ``patient`` (patient data dict), or any other
        metadata the caller wishes to pass through.
    """

    patient_id: str
    recommendation_id: str
    variants: list[dict] = Field(default_factory=list)
    context: dict | None = None


class ClinicalDecisionResponse(BaseModel):
    """Response DTO for a clinical decision.

    Attributes
    ----------
    decision_id : str
        Business identifier (hex-string UUID) for the decision.
    patient_id : str
        UUID string of the patient.
    recommendation_id : str
        UUID string of the recommendation.
    decision_type : str
        One of ``"approved"``, ``"off_label"``, ``"clinical_trial"``,
        ``"contraindicated"``, ``"experimental"``, ``"not_recommended"``.
    reason : str
        Human-readable explanation of the decision.
    evidence_summary : dict | None
        Structured summary of evidence considered.
    confidence : str
        One of ``"high"``, ``"medium"``, ``"low"``, ``"insufficient"``.
    alternatives : list[dict]
        Alternative drug options (ranked 2nd and below).
    contraindications : list[dict]
        Contraindication signals detected.
    created_at : str
        ISO-8601 formatted creation timestamp.
    trace_id : str | None
        Optional identifier of the calculation trace.
    """

    decision_id: str
    patient_id: str
    recommendation_id: str
    decision_type: str
    reason: str
    evidence_summary: dict | None = None
    confidence: str
    alternatives: list[dict] = Field(default_factory=list)
    contraindications: list[dict] = Field(default_factory=list)
    created_at: str
    trace_id: str | None = None


# ═══════════════════════════════════════════════════════════════════════════════
# ClinicalDecisionService
# ═══════════════════════════════════════════════════════════════════════════════


class ClinicalDecisionService:
    """Orchestrates clinical decision generation and persistence.

    All business logic lives here; the API router calls this service and
    maps the result to HTTP responses.

    Parameters
    ----------
    db : AsyncSession
        The SQLAlchemy async session to use for all persistence.
        Transaction management (commit / rollback) is handled by this service.
    engine : ClinicalDecisionEngine | None
        The decision engine to use.  Defaults to a fresh
        ``ClinicalDecisionEngine()``.
    decision_repo : ClinicalDecisionRepository | None
        Repository for ``ClinicalDecisionModel``.  Defaults to a fresh
        instance bound to ``db``.
    trace_repo : ClinicalDecisionTraceRepository | None
        Repository for ``ClinicalDecisionTraceModel``.  Defaults to a fresh
        instance bound to ``db``.
    """

    def __init__(
        self,
        db: AsyncSession,
        engine: ClinicalDecisionEngine | None = None,
        decision_repo: ClinicalDecisionRepository | None = None,
        trace_repo: ClinicalDecisionTraceRepository | None = None,
        graph_event_service: ClinicalGraphEventService | None = None,
    ) -> None:
        """Inject db session, engine, and repositories."""
        self._db = db
        self._engine = engine or ClinicalDecisionEngine()
        self._decision_repo = decision_repo or ClinicalDecisionRepository(db)
        self._trace_repo = trace_repo or ClinicalDecisionTraceRepository(db)
        self._graph_event_service = graph_event_service

    # ── Public API ─────────────────────────────────────────────────────────

    async def create_decision(
        self,
        patient_id: str | UUID,
        recommendation_id: str | UUID,
        variants: list[dict],
        context: dict | None = None,
        created_by: str | UUID | None = None,
    ) -> ClinicalDecisionResponse:
        """Create a clinical decision based on a recommendation.

        The method:
        1. Retrieves patient and recommendation data from the database.
        2. Calls ``ClinicalDecisionEngine.evaluate()`` to produce a
           ``ClinicalDecisionResult``.
        3. Creates ``ClinicalDecisionModel`` and
           ``ClinicalDecisionTraceModel``.
        4. Persists everything in a single transaction.
        5. Commits on success and returns the response DTO.
        6. Rolls back on failure and raises a ``RuntimeError``.

        Parameters
        ----------
        patient_id : str | UUID
            UUID of the patient.
        recommendation_id : str | UUID
            Business identifier (``recommendation_id``) of the
            recommendation to base the decision on.
        variants : list[dict]
            List of variant dictionaries.
        context : dict | None
            Optional free-form context.  May contain ``evidence``
            (list of evidence dicts) and/or ``patient`` (patient data
            dict).

        Returns
        -------
        ClinicalDecisionResponse
            The structured response DTO.

        Raises
        ------
        ValueError
            If patient or recommendation is not found, or if the engine
            cannot produce a decision.
        RuntimeError
            If persistence fails.
        """
        # Normalise identifiers
        patient_uuid: UUID = (
            UUID(str(patient_id)) if not isinstance(patient_id, UUID) else patient_id
        )
        rec_id_str: str = str(recommendation_id)

        ctx = context or {}
        decision_id = _uuid.uuid4().hex

        # ── Step 1: Retrieve patient & recommendation data ────────────────
        # Always load patient from Database — the single source of truth
        patient_data = await self._load_patient_data(patient_uuid)

        # context.patient is supplemental only — merge non-overlapping fields
        ctx_patient = ctx.get("patient")
        if ctx_patient and isinstance(ctx_patient, dict):
            for key, value in ctx_patient.items():
                # Do NOT override core identity fields from DB
                if key not in ("id", "patient_id", "external_id", "display_name",
                               "birth_year", "age_range", "sex", "consent_status",
                               "created_at"):
                    patient_data[key] = value

        recommendation = await self._load_recommendation_data(rec_id_str)
        if recommendation is None:
            raise ValueError(
                f"Recommendation with id '{rec_id_str}' not found",
            )

        # P0-1: Validate recommendation belongs to the same patient
        rec_patient_id = recommendation.get("patient_id")
        if rec_patient_id and str(rec_patient_id) != str(patient_uuid):
            raise ValueError(
                f"Recommendation '{rec_id_str}' belongs to patient "
                f"'{rec_patient_id}', not patient '{patient_uuid}'"
            )

        # Extract evidence from context or from the recommendation payload
        evidence: list[dict] = ctx.get("evidence", [])
        if not evidence:
            evidence = self._extract_evidence_from_recommendation(recommendation)

        # ── Step 2: Run the engine ────────────────────────────────────────
        try:
            result: ClinicalDecisionResult = await self._engine.evaluate(
                patient=patient_data,
                variants=list(variants),
                evidence=evidence,
                recommendation=recommendation,
            )
        except ValueError:
            raise
        except Exception as exc:
            logger.exception(
                "ClinicalDecisionEngine.evaluate() raised an unhandled "
                "exception for recommendation %s.",
                rec_id_str,
            )
            raise RuntimeError(
                "Clinical decision engine encountered an internal error",
            ) from exc

        # ── Step 3: Build persistence models ──────────────────────────────
        trace_id = _uuid.uuid4().hex
        created_at = datetime.now(timezone.utc)

        rec_uuid = recommendation.get("_uuid") or recommendation.get("id")

        decision_model = ClinicalDecisionModel(
            decision_id=decision_id,
            patient_id=patient_uuid,
            recommendation_id=rec_uuid,
            decision_type=result.decision_type,
            reason=result.reason,
            evidence_summary=result.evidence_summary,
            confidence=result.confidence,
            alternatives=result.alternatives,
            contraindications=result.contraindications,
            status="active",
            created_by=created_by if isinstance(created_by, UUID) else UUID(created_by) if created_by else None,
            created_at=created_at,
            updated_at=created_at,
        )

        # ── Step 4: Persist — flush first to get decision_model.id ────────
        try:
            await self._decision_repo.create(decision_model)
            await self._db.flush()

            # Build 5 trace steps now that we have decision_model.id
            trace_steps = [
                ClinicalDecisionTraceModel(
                    trace_id=trace_id,
                    clinical_decision_id=decision_model.id,
                    recommendation_id=rec_uuid,
                    step_order=0,
                    step_type="load_recommendation",
                    input_summary={"recommendation_id": rec_id_str},
                    output_summary={"status": "loaded", "has_patient": rec_patient_id is not None},
                    created_at=created_at,
                ),
                ClinicalDecisionTraceModel(
                    trace_id=trace_id,
                    clinical_decision_id=decision_model.id,
                    recommendation_id=rec_uuid,
                    step_order=1,
                    step_type="validate_patient",
                    input_summary={
                        "patient_id": str(patient_uuid),
                        "recommendation_patient_id": rec_patient_id,
                    },
                    output_summary={"valid": True},
                    created_at=created_at,
                ),
                ClinicalDecisionTraceModel(
                    trace_id=trace_id,
                    clinical_decision_id=decision_model.id,
                    recommendation_id=rec_uuid,
                    step_order=2,
                    step_type="evaluate",
                    input_summary={
                        "patient_id": str(patient_uuid),
                        "recommendation_id": rec_id_str,
                        "variants": list(variants),
                        "evidence_count": len(evidence),
                    },
                    output_summary=result.to_dict(),
                    created_at=created_at,
                ),
                ClinicalDecisionTraceModel(
                    trace_id=trace_id,
                    clinical_decision_id=decision_model.id,
                    recommendation_id=rec_uuid,
                    step_order=3,
                    step_type="decision",
                    input_summary={
                        "decision_type": result.decision_type,
                        "confidence": result.confidence,
                    },
                    output_summary={
                        "decision_id": decision_id,
                        "reason": result.reason,
                    },
                    created_at=created_at,
                ),
                ClinicalDecisionTraceModel(
                    trace_id=trace_id,
                    clinical_decision_id=decision_model.id,
                    recommendation_id=rec_uuid,
                    step_order=4,
                    step_type="persist",
                    input_summary={"decision_id": decision_id},
                    output_summary={"status": "persisted"},
                    created_at=created_at,
                ),
            ]

            for step in trace_steps:
                await self._trace_repo.create(step)

            # ── Write outbox event (same transaction) ──────────────────
            if self._graph_event_service is not None:
                payload = {
                    "decision_id": decision_id,
                    "patient_id": str(patient_uuid),
                    "recommendation_id": rec_id_str,
                    "decision_type": result.decision_type,
                    "rationale": result.reason,
                    "evidence_references": result.evidence_summary if hasattr(result, 'evidence_summary') else {},
                    "contraindications": getattr(result, 'contraindications', []),
                    "alternatives": getattr(result, 'alternatives', []),
                    "confidence": result.confidence,
                }
                await self._graph_event_service.create_event(
                    aggregate_type=GraphAggregateType.CLINICAL_DECISION,
                    aggregate_id=decision_id,
                    event_type=GraphEventType.CLINICAL_DECISION_CREATED,
                    payload=payload,
                )

            await self._db.commit()
        except Exception as exc:
            await self._db.rollback()
            logger.exception(
                "Failed to persist clinical decision %s — rolled back.",
                decision_id,
            )
            raise RuntimeError("Failed to persist clinical decision") from exc

        # ── Step 5: Build & return response ───────────────────────────────
        return ClinicalDecisionResponse(
            decision_id=decision_id,
            patient_id=str(patient_uuid),
            recommendation_id=rec_id_str,
            decision_type=result.decision_type,
            reason=result.reason,
            evidence_summary=result.evidence_summary,
            confidence=result.confidence,
            alternatives=result.alternatives,
            contraindications=result.contraindications,
            created_at=created_at.isoformat(),
            trace_id=trace_id,
        )

    async def get_decision(
        self,
        decision_id: str,
    ) -> ClinicalDecisionResponse | None:
        """Retrieve a clinical decision by its business identifier.

        Parameters
        ----------
        decision_id : str
            The hex-string UUID returned by ``create_decision``.

        Returns
        -------
        ClinicalDecisionResponse | None
            The response DTO, or ``None`` if not found.
        """
        model = await self._decision_repo.get_by_id(decision_id)
        if model is None:
            return None
        return await self._model_to_response(model)

    async def get_decision_by_uuid(
        self,
        uuid: UUID,
    ) -> ClinicalDecisionResponse | None:
        """Retrieve a clinical decision by its primary key (UUID).

        Parameters
        ----------
        uuid : UUID
            The primary key of the clinical decision record.

        Returns
        -------
        ClinicalDecisionResponse | None
            The response DTO, or ``None`` if not found.
        """
        model = await self._decision_repo.get_by_uuid(uuid)
        if model is None:
            return None
        return await self._model_to_response(model)

    async def list_decisions_by_patient(
        self,
        patient_id: UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> list[ClinicalDecisionResponse]:
        """List clinical decisions for a patient, newest first.

        Parameters
        ----------
        patient_id : UUID
            The patient's UUID.
        skip : int
            Number of records to skip (for pagination).
        limit : int
            Maximum number of records to return (default 50).

        Returns
        -------
        list[ClinicalDecisionResponse]
        """
        models = await self._decision_repo.list_by_patient_id(
            patient_id=patient_id,
            skip=skip,
            limit=limit,
        )
        return [await self._model_to_response(m) for m in models]

    async def count_decisions_by_patient(
        self,
        patient_id: UUID,
    ) -> int:
        """Count clinical decisions for a patient.

        Parameters
        ----------
        patient_id : UUID
            The patient's UUID.

        Returns
        -------
        int
            Number of clinical decisions for the patient.
        """
        return await self._decision_repo.count_by_patient_id(
            patient_id=patient_id,
        )

    # ── Internal helpers ─────────────────────────────────────────────────

    async def _load_patient_data(
        self,
        patient_uuid: UUID,
    ) -> dict[str, Any]:
        """Load patient data from the database and return as a dict."""
        from src.backend.repositories.patient_repo import PatientRepository

        repo = PatientRepository(self._db)
        patient = await repo.get(patient_uuid)
        if patient is None:
            raise ValueError(f"Patient with UUID '{patient_uuid}' not found")

        return {
            "id": str(patient.id) if patient.id else None,
            "external_id": patient.external_id,
            "display_name": patient.display_name,
            "birth_year": patient.birth_year,
            "age_range": patient.age_range,
            "sex": patient.sex.value if patient.sex else None,
            "consent_status": patient.consent_status.value if patient.consent_status else None,
            "created_at": patient.created_at.isoformat() if patient.created_at else None,
        }

    async def _load_recommendation_data(
        self,
        recommendation_id: str,
    ) -> dict[str, Any] | None:
        """Load recommendation data from the database and return as a dict.

        Returns ``None`` if the recommendation is not found.
        """
        from src.backend.repositories.recommendation_repo import (
            RecommendationRepository,
        )

        repo = RecommendationRepository(self._db)
        model = await repo.get_by_id(recommendation_id)
        if model is None:
            return None

        # Preserve the primary key UUID so the service can use it as a
        # foreign-key value for trace records.
        result: dict[str, Any] = {
            "_uuid": model.id,
            "recommendation_id": model.recommendation_id,
            "patient_id": str(model.patient_id) if model.patient_id else None,
            "status": model.status,
            "engine_version": model.engine_version,
            "trace_id": model.trace_id,
            "request_payload": model.request_payload or {},
            "result_payload": model.result_payload or {},
            "created_at": model.created_at.isoformat() if model.created_at else None,
        }
        # Merge result_payload at the top level for engine compatibility
        if model.result_payload:
            result.update(model.result_payload)
        return result

    @staticmethod
    def _extract_evidence_from_recommendation(
        recommendation: dict[str, Any],
    ) -> list[dict]:
        """Extract evidence items from the recommendation payload.

        Walks the ``result_payload`` for keys that look like evidence
        lists.
        """
        payload = recommendation.get("result_payload", {})
        if not payload:
            payload = recommendation

        # Common locations for evidence data
        for key in ("evidence", "evidence_items", "evidence_list"):
            items = payload.get(key, [])
            if items and isinstance(items, list):
                return items

        # If recommendations list exists, try to pull evidence from each
        recs = payload.get("recommendations", [])
        if recs and isinstance(recs, list) and len(recs) > 0:
            # Some pipelines embed evidence inside each recommendation entry
            all_evidence: list[dict] = []
            for rec in recs:
                ev = rec.get("evidence", [])
                if ev and isinstance(ev, list):
                    all_evidence.extend(ev)
            if all_evidence:
                return all_evidence

        return []

    async def _model_to_response(
        self,
        model: ClinicalDecisionModel,
    ) -> ClinicalDecisionResponse:
        """Convert a ``ClinicalDecisionModel`` to a response DTO.

        The ``recommendation_id`` field is populated from the associated
        ``RecommendationModel.recommendation_id`` (the business identifier)
        rather than the FK UUID.  Falls back to the raw FK UUID string if
        the recommendation record is not found.
        """
        # Gather trace_id from the first trace, if any
        trace_id: str | None = None
        if model.traces:
            # Traces are loaded via selectin; use the first one's trace_id
            trace_id = model.traces[0].trace_id

        # Resolve the business recommendation_id from the FK UUID
        biz_rec_id: str = ""
        if model.recommendation_id:
            from src.backend.repositories.recommendation_repo import (
                RecommendationRepository,
            )

            try:
                repo = RecommendationRepository(self._db)
                rec_model = await repo.get(model.recommendation_id)
                if rec_model is not None:
                    biz_rec_id = rec_model.recommendation_id
                else:
                    biz_rec_id = str(model.recommendation_id)
            except Exception:
                biz_rec_id = str(model.recommendation_id)
        else:
            biz_rec_id = ""

        return ClinicalDecisionResponse(
            decision_id=model.decision_id,
            patient_id=str(model.patient_id) if model.patient_id else "",
            recommendation_id=biz_rec_id,
            decision_type=model.decision_type,
            reason=model.reason,
            evidence_summary=model.evidence_summary,
            confidence=model.confidence,
            alternatives=model.alternatives or [],
            contraindications=model.contraindications or [],
            created_at=model.created_at.isoformat() if model.created_at else "",
            trace_id=trace_id,
        )
