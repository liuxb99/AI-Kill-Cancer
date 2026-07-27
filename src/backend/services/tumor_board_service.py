"""
Tumor Board Consensus Service — orchestrates multi-disciplinary consensus generation.

Responsibilities
----------------
1. Accept request parameters from the API layer
2. Retrieve patient, recommendation, and clinical decision data from the database
3. Validate data consistency (P0: patient/recommendation/clinical-decision link)
4. Call ``ConsensusEngine.calculate()`` to produce a consensus result
5. Persist ``TumorBoardConsensusModel`` + ``TumorBoardOpinionModel`` +
   ``TumorBoardConsensusTraceModel``
6. Manage the transaction boundary (commit on success, rollback on failure)
7. Return structured DTOs

The API router delegates all business logic here — the router only handles
request validation, authentication, calling the service, and exception mapping.
"""

from __future__ import annotations

import asyncio
import logging
import uuid as _uuid
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.clinical.tumor_board_engine import (
    ConsensusEngine,
    ConsensusResult,
    SpecialistOpinionInput,
    TumorBoardConsensusInput,
)
from src.backend.domain.tumor_board import (
    TumorBoardConsensusModel,
    TumorBoardConsensusTraceModel,
    TumorBoardOpinionModel,
)
from src.backend.repositories.tumor_board_repo import (
    TumorBoardConsensusRepository,
    TumorBoardConsensusTraceRepository,
    TumorBoardOpinionRepository,
)

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# Pydantic DTOs
# ═══════════════════════════════════════════════════════════════════════════════


class SpecialistOpinionDTO(BaseModel):
    """DTO for a single specialist's opinion input.

    Attributes
    ----------
    specialty : str
        The specialty identifier (e.g. ``"medical_oncology"``).
    participant_id : str, optional
        Optional identifier for the individual participant.
    position : str
        One of ``"support"``, ``"oppose"``, ``"abstain"``.
    confidence : float
        Confidence score in ``[0.0, 1.0]``.
    rationale : str, optional
        Free-text justification for the position.
    supporting_evidence : list[str], optional
        References supporting the position (e.g. literature PMIDs).
    contraindications : list[str], optional
        Contraindication signals considered.
    preferred_option : str, optional
        The option the specialist prefers.
    alternative_option : str, optional
        An alternative the specialist would accept.
    requires_more_information : bool
        Whether the specialist needs more data before deciding.
    """

    specialty: str
    participant_id: Optional[str] = None
    position: str
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: Optional[str] = None
    supporting_evidence: Optional[list[str]] = None
    contraindications: Optional[list[str]] = None
    preferred_option: Optional[str] = None
    alternative_option: Optional[str] = None
    requires_more_information: bool = False


class CreateConsensusRequest(BaseModel):
    """Request DTO for creating a new tumor board consensus.

    Attributes
    ----------
    patient_id : str
        UUID string identifying the patient.
    recommendation_id : str
        UUID string identifying the recommendation being reviewed.
    clinical_decision_id : str
        UUID string identifying the associated clinical decision.
    specialist_opinions : list[SpecialistOpinionDTO]
        Collection of specialist opinions to evaluate.
    meeting_context : str, optional
        Free-text description of the tumor board meeting context.
    """

    patient_id: str
    recommendation_id: str
    clinical_decision_id: str
    specialist_opinions: list[SpecialistOpinionDTO]
    meeting_context: Optional[str] = None


class ConsensusResponse(BaseModel):
    """Response DTO for a tumor board consensus.

    Attributes
    ----------
    consensus_id : str
        Business identifier (hex-string UUID) for the consensus.
    patient_id : str
        UUID string of the patient.
    recommendation_id : str
        Business identifier of the recommendation.
    clinical_decision_id : str
        Business identifier of the clinical decision.
    consensus_status : str
        One of the ``ConsensusStatus`` enum values.
    consensus_score : float, optional
        Overall consensus score (0.0-1.0).
    final_recommendation : str, optional
        The agreed-upon recommendation, if any.
    supporting_rationale : str, optional
        Human-readable explanation of how the consensus was reached.
    dissenting_opinions : list[dict]
        Serialised dissenting (oppose) opinions.
    unresolved_questions : list[str]
        Questions raised by specialists that remain unresolved.
    required_follow_up : list[str]
        Actions required before a final decision can be made.
    participating_specialties : list[str]
        Distinct specialties that contributed opinions.
    created_by : str, optional
        UUID string of the user who created this consensus.
    created_at : str
        ISO-8601 formatted creation timestamp.
    trace_id : str, optional
        Identifier of the calculation trace.
    """

    consensus_id: str
    patient_id: str
    recommendation_id: str
    clinical_decision_id: str
    consensus_status: str
    consensus_score: Optional[float] = None
    final_recommendation: Optional[str] = None
    supporting_rationale: Optional[str] = None
    dissenting_opinions: list[dict] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)
    required_follow_up: list[str] = Field(default_factory=list)
    participating_specialties: list[str] = Field(default_factory=list)
    created_by: Optional[str] = None
    created_at: str
    trace_id: Optional[str] = None


class ConsensusListResponse(BaseModel):
    """Lightweight response DTO for listing tumor board consensuses.

    Attributes
    ----------
    consensus_id : str
        Business identifier (hex-string UUID) for the consensus.
    patient_id : str
        UUID string of the patient.
    consensus_status : str
        One of the ``ConsensusStatus`` enum values.
    consensus_score : float, optional
        Overall consensus score (0.0-1.0).
    participating_specialties : list[str]
        Distinct specialties that contributed opinions.
    created_at : str
        ISO-8601 formatted creation timestamp.
    """

    consensus_id: str
    patient_id: str
    consensus_status: str
    consensus_score: Optional[float] = None
    participating_specialties: list[str] = Field(default_factory=list)
    created_at: str


# ═══════════════════════════════════════════════════════════════════════════════
# TumorBoardConsensusService
# ═══════════════════════════════════════════════════════════════════════════════


class TumorBoardConsensusService:
    """Orchestrates tumor board consensus generation and persistence.

    All business logic lives here; the API router calls this service and
    maps the result to HTTP responses.

    Parameters
    ----------
    db : AsyncSession
        The SQLAlchemy async session to use for all persistence.
        Transaction management (commit / rollback) is handled by this service.
    engine : ConsensusEngine | None
        The consensus engine to use.  Defaults to a fresh ``ConsensusEngine()``.
    consensus_repo : TumorBoardConsensusRepository | None
        Repository for ``TumorBoardConsensusModel``.  Defaults to a fresh
        instance bound to ``db``.
    opinion_repo : TumorBoardOpinionRepository | None
        Repository for ``TumorBoardOpinionModel``.  Defaults to a fresh
        instance bound to ``db``.
    trace_repo : TumorBoardConsensusTraceRepository | None
        Repository for ``TumorBoardConsensusTraceModel``.  Defaults to a fresh
        instance bound to ``db``.
    """

    def __init__(
        self,
        db: AsyncSession,
        engine: ConsensusEngine | None = None,
        consensus_repo: TumorBoardConsensusRepository | None = None,
        opinion_repo: TumorBoardOpinionRepository | None = None,
        trace_repo: TumorBoardConsensusTraceRepository | None = None,
    ) -> None:
        """Inject db session, engine, and repositories."""
        self._db = db
        self._engine = engine or ConsensusEngine()
        self._consensus_repo = consensus_repo or TumorBoardConsensusRepository(db)
        self._opinion_repo = opinion_repo or TumorBoardOpinionRepository(db)
        self._trace_repo = trace_repo or TumorBoardConsensusTraceRepository(db)

    # ── Public API ─────────────────────────────────────────────────────────

    async def create_consensus(
        self,
        request: CreateConsensusRequest,
        created_by: Optional[str] = None,
    ) -> ConsensusResponse:
        """Create a tumor board consensus from specialist opinions.

        The method:
        1. Loads and validates consistency of recommendation and clinical
           decision records (P0 data validation).
        2. Calls ``ConsensusEngine.calculate()`` to produce a
           ``ConsensusResult``.
        3. Creates ``TumorBoardConsensusModel``,
           ``TumorBoardOpinionModel``, and
           ``TumorBoardConsensusTraceModel`` instances.
        4. Persists everything in a single transaction.
        5. Commits on success and returns the response DTO.
        6. Rolls back on failure and raises a ``RuntimeError``.

        Parameters
        ----------
        request : CreateConsensusRequest
            The validated request payload containing patient, recommendation,
            clinical decision, and specialist opinions.
        created_by : str, optional
            UUID string of the user creating this consensus.

        Returns
        -------
        ConsensusResponse
            The structured response DTO.

        Raises
        ------
        ValueError
            If the patient/recommendation/clinical-decision link is
            inconsistent, or if a referenced record is not found.
        RuntimeError
            If persistence fails.
        """
        consensus_id = _uuid.uuid4().hex
        trace_id = _uuid.uuid4().hex
        created_at = datetime.utcnow()

        # ── Step 1: P0 — Load & validate data consistency ──────────────
        recommendation = await self._load_recommendation(request.recommendation_id)
        clinical_decision = await self._load_clinical_decision(
            request.clinical_decision_id,
        )

        self._validate_links(
            recommendation=recommendation,
            clinical_decision=clinical_decision,
            request=request,
        )

        # ── Step 2: Run the engine ─────────────────────────────────────
        try:
            engine_input = self._build_engine_input(request, consensus_id)
            # Engine is synchronous — run in executor to avoid blocking
            result: ConsensusResult = await asyncio.get_event_loop().run_in_executor(
                None,
                self._engine.calculate,
                engine_input,
            )
        except ValueError:
            raise
        except Exception as exc:
            logger.exception(
                "ConsensusEngine.calculate() raised an unhandled exception "
                "for recommendation %s.",
                request.recommendation_id,
            )
            raise RuntimeError(
                "Consensus engine encountered an internal error",
            ) from exc

        # ── Step 3: Build persistence models ────────────────────────────
        rec_uuid: UUID | None = recommendation.id
        cd_uuid: UUID | None = clinical_decision.id
        patient_uuid: UUID | None = recommendation.patient_id

        consensus_model = TumorBoardConsensusModel(
            consensus_id=consensus_id,
            patient_id=patient_uuid,
            recommendation_id=rec_uuid,
            clinical_decision_id=cd_uuid,
            consensus_status=result.consensus_status.value,
            consensus_score=result.consensus_score,
            final_recommendation=result.final_recommendation,
            supporting_rationale=result.supporting_rationale,
            dissenting_opinions=result.dissenting_opinions,
            unresolved_questions=result.unresolved_questions,
            required_follow_up=result.required_follow_up,
            participating_specialties=result.participating_specialties,
            created_by=UUID(created_by) if created_by else None,
            created_at=created_at,
            updated_at=created_at,
        )

        # Build opinion models (consensus_id FK will be set after flush)
        opinion_models = [
            TumorBoardOpinionModel(
                specialty=opinion.specialty,
                participant_id=opinion.participant_id,
                position=opinion.position,
                confidence=opinion.confidence,
                rationale=opinion.rationale,
                supporting_evidence=opinion.supporting_evidence,
                contraindications=opinion.contraindications,
                preferred_option=opinion.preferred_option,
                alternative_option=opinion.alternative_option,
                requires_more_information=opinion.requires_more_information,
                created_at=created_at,
            )
            for opinion in request.specialist_opinions
        ]

        # Build trace models (consensus_id FK will be set after flush)
        trace_models = [
            TumorBoardConsensusTraceModel(
                trace_id=trace_id,
                step_order=idx,
                step_type=step.get("step_type", ""),
                input_summary=step.get("input_summary"),
                output_summary=step.get("output_summary"),
                created_at=created_at,
            )
            for idx, step in enumerate(result.trace_steps)
        ]

        # ── Step 4: Persist — single transaction ───────────────────────
        try:
            await self._consensus_repo.create(consensus_model)
            await self._db.flush()

            # Link opinions and traces to the consensus PK now that it's set
            for opinion_model in opinion_models:
                opinion_model.consensus_id = consensus_model.id
            await self._opinion_repo.create_many(opinion_models)

            for trace_model in trace_models:
                trace_model.consensus_id = consensus_model.id
            await self._trace_repo.create_many(trace_models)

            await self._db.commit()
        except Exception as exc:
            await self._db.rollback()
            logger.exception(
                "Failed to persist tumor board consensus %s — rolled back.",
                consensus_id,
            )
            raise RuntimeError(
                "Failed to persist tumor board consensus",
            ) from exc

        # ── Step 5: Build & return response ────────────────────────────
        return ConsensusResponse(
            consensus_id=consensus_id,
            patient_id=str(patient_uuid) if patient_uuid else "",
            recommendation_id=request.recommendation_id,
            clinical_decision_id=request.clinical_decision_id,
            consensus_status=result.consensus_status.value,
            consensus_score=result.consensus_score,
            final_recommendation=result.final_recommendation,
            supporting_rationale=result.supporting_rationale,
            dissenting_opinions=result.dissenting_opinions,
            unresolved_questions=result.unresolved_questions,
            required_follow_up=result.required_follow_up,
            participating_specialties=result.participating_specialties,
            created_by=created_by,
            created_at=created_at.isoformat(),
            trace_id=trace_id,
        )

    async def get_consensus(
        self,
        consensus_id: str,
    ) -> ConsensusResponse | None:
        """Retrieve a tumor board consensus by its business identifier.

        Parameters
        ----------
        consensus_id : str
            The hex-string UUID returned by ``create_consensus``
            (``TumorBoardConsensusModel.consensus_id``).

        Returns
        -------
        ConsensusResponse | None
            The response DTO, or ``None`` if not found.
        """
        model = await self._consensus_repo.get_by_uuid(consensus_id)
        if model is None:
            return None
        return await self._model_to_response(model)

    async def list_consensus(
        self,
        patient_id: str,
        skip: int = 0,
        limit: int = 20,
    ) -> list[ConsensusListResponse]:
        """List tumor board consensuses for a patient, newest first.

        Parameters
        ----------
        patient_id : str
            UUID string of the patient.
        skip : int
            Number of records to skip (for pagination).
        limit : int
            Maximum number of records to return (default 20).

        Returns
        -------
        list[ConsensusListResponse]
        """
        patient_uuid = UUID(patient_id)
        models = await self._consensus_repo.list_by_patient_id(
            patient_id=patient_uuid,
            skip=skip,
            limit=limit,
        )
        return [
            ConsensusListResponse(
                consensus_id=m.consensus_id,
                patient_id=str(m.patient_id) if m.patient_id else "",
                consensus_status=m.consensus_status,
                consensus_score=m.consensus_score,
                participating_specialties=m.participating_specialties or [],
                created_at=m.created_at.isoformat() if m.created_at else "",
            )
            for m in models
        ]

    async def get_opinions(
        self,
        consensus_id: str,
    ) -> list[dict[str, Any]]:
        """Retrieve all opinions for a given consensus.

        Parameters
        ----------
        consensus_id : str
            The consensus business identifier.

        Returns
        -------
        list[dict]
            Serialised opinion records.  Returns an empty list if the
            consensus is not found.
        """
        model = await self._consensus_repo.get_by_uuid(consensus_id)
        if model is None:
            return []
        opinions = await self._opinion_repo.list_by_consensus_id(model.id)
        return [
            {
                "id": str(o.id),
                "specialty": o.specialty,
                "participant_id": o.participant_id,
                "position": o.position,
                "confidence": o.confidence,
                "rationale": o.rationale,
                "supporting_evidence": o.supporting_evidence,
                "contraindications": o.contraindications,
                "preferred_option": o.preferred_option,
                "alternative_option": o.alternative_option,
                "requires_more_information": o.requires_more_information,
                "created_at": o.created_at.isoformat() if o.created_at else None,
            }
            for o in opinions
        ]

    async def get_trace(
        self,
        consensus_id: str,
    ) -> list[dict[str, Any]]:
        """Retrieve the calculation trace for a given consensus.

        Parameters
        ----------
        consensus_id : str
            The consensus business identifier.

        Returns
        -------
        list[dict]
            Serialised trace steps.  Returns an empty list if the consensus
            is not found.
        """
        model = await self._consensus_repo.get_by_uuid(consensus_id)
        if model is None:
            return []
        traces = await self._trace_repo.list_by_consensus_id(model.id)
        return [
            {
                "trace_id": t.trace_id,
                "step_order": t.step_order,
                "step_type": t.step_type,
                "input_summary": t.input_summary,
                "output_summary": t.output_summary,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in traces
        ]

    async def count_by_patient(
        self,
        patient_id: str,
    ) -> int:
        """Count consensus records for a patient.

        Parameters
        ----------
        patient_id : str
            UUID string of the patient.

        Returns
        -------
        int
            Number of consensus records for the patient.
        """
        patient_uuid = UUID(patient_id)
        return await self._consensus_repo.count_by_patient_id(
            patient_id=patient_uuid,
        )

    # ── Internal helpers ─────────────────────────────────────────────────

    async def _load_recommendation(self, recommendation_id: str):
        """Load a recommendation by its business identifier.

        Parameters
        ----------
        recommendation_id : str
            The recommendation's business identifier
            (``RecommendationModel.recommendation_id``).

        Returns
        -------
        RecommendationModel

        Raises
        ------
        ValueError
            If the recommendation is not found.
        """
        from src.backend.repositories.recommendation_repo import (
            RecommendationRepository,
        )

        repo = RecommendationRepository(self._db)
        model = await repo.get_by_id(recommendation_id)
        if model is None:
            raise ValueError(
                f"Recommendation with id '{recommendation_id}' not found",
            )
        return model

    async def _load_clinical_decision(self, clinical_decision_id: str):
        """Load a clinical decision by its business identifier.

        Parameters
        ----------
        clinical_decision_id : str
            The clinical decision's business identifier
            (``ClinicalDecisionModel.decision_id``).

        Returns
        -------
        ClinicalDecisionModel

        Raises
        ------
        ValueError
            If the clinical decision is not found.
        """
        from src.backend.repositories.clinical_decision_repo import (
            ClinicalDecisionRepository,
        )

        repo = ClinicalDecisionRepository(self._db)
        model = await repo.get_by_id(clinical_decision_id)
        if model is None:
            raise ValueError(
                f"Clinical decision with id '{clinical_decision_id}' not found",
            )
        return model

    @staticmethod
    def _validate_links(
        recommendation,
        clinical_decision,
        request: CreateConsensusRequest,
    ) -> None:
        """P0 validation: ensure patient/recommendation/decision links match.

        Checks:
        - recommendation.patient_id == request.patient_id
        - clinical_decision.patient_id == request.patient_id
        - clinical_decision.recommendation_id (FK) == recommendation.id (PK)

        Parameters
        ----------
        recommendation : RecommendationModel
            The loaded recommendation model.
        clinical_decision : ClinicalDecisionModel
            The loaded clinical decision model.
        request : CreateConsensusRequest
            The original request payload.

        Raises
        ------
        ValueError
            If any link is inconsistent (API layer will convert to 422).
        """
        rec_patient_id = (
            str(recommendation.patient_id) if recommendation.patient_id else None
        )
        cd_patient_id = (
            str(clinical_decision.patient_id)
            if clinical_decision.patient_id
            else None
        )

        if rec_patient_id != request.patient_id:
            raise ValueError(
                f"Recommendation '{request.recommendation_id}' belongs to "
                f"patient '{rec_patient_id}', not patient '{request.patient_id}'",
            )
        if cd_patient_id != request.patient_id:
            raise ValueError(
                f"Clinical decision '{request.clinical_decision_id}' belongs to "
                f"patient '{cd_patient_id}', not patient '{request.patient_id}'",
            )

        # Verify the clinical decision's recommendation FK matches the
        # recommendation's primary key
        cd_rec_fk = (
            str(clinical_decision.recommendation_id)
            if clinical_decision.recommendation_id
            else None
        )
        rec_pk = str(recommendation.id) if recommendation.id else None
        if cd_rec_fk != rec_pk:
            raise ValueError(
                f"Clinical decision '{request.clinical_decision_id}' references "
                f"recommendation '{cd_rec_fk}', but request specifies "
                f"recommendation '{request.recommendation_id}' "
                f"(PK: '{rec_pk}') — Patient/Recommendation/Clinical Decision "
                f"link mismatch",
            )

    @staticmethod
    def _build_engine_input(
        request: CreateConsensusRequest,
        consensus_id: str,
    ) -> TumorBoardConsensusInput:
        """Build the engine input from the request DTO.

        Parameters
        ----------
        request : CreateConsensusRequest
            The validated request payload.
        consensus_id : str
            The generated consensus identifier.

        Returns
        -------
        TumorBoardConsensusInput
        """
        specialist_inputs = [
            SpecialistOpinionInput(
                specialty=opinion.specialty,
                participant_id=opinion.participant_id,
                position=opinion.position,
                confidence=opinion.confidence,
                rationale=opinion.rationale,
                supporting_evidence=opinion.supporting_evidence,
                contraindications=opinion.contraindications,
                preferred_option=opinion.preferred_option,
                alternative_option=opinion.alternative_option,
                requires_more_information=opinion.requires_more_information,
            )
            for opinion in request.specialist_opinions
        ]

        return TumorBoardConsensusInput(
            patient_id=request.patient_id,
            recommendation_id=request.recommendation_id,
            clinical_decision_id=request.clinical_decision_id,
            specialist_opinions=specialist_inputs,
            meeting_context=request.meeting_context,
        )

    async def _model_to_response(
        self,
        model: TumorBoardConsensusModel,
    ) -> ConsensusResponse:
        """Convert a ``TumorBoardConsensusModel`` to a response DTO.

        Resolves the business identifiers for recommendation and clinical
        decision from their FK UUIDs.  Falls back to the raw FK UUID string
        if the related record cannot be loaded.

        Parameters
        ----------
        model : TumorBoardConsensusModel
            The loaded consensus model (opinions and traces are loaded via
            selectin relationships).

        Returns
        -------
        ConsensusResponse
        """
        # Resolve business IDs from FK references
        rec_biz_id: str = ""
        if model.recommendation_id:
            try:
                rec_model = await self._load_recommendation_by_pk(
                    model.recommendation_id,
                )
                rec_biz_id = (
                    rec_model.recommendation_id
                    if rec_model
                    else str(model.recommendation_id)
                )
            except Exception:
                rec_biz_id = str(model.recommendation_id)

        cd_biz_id: str = ""
        if model.clinical_decision_id:
            try:
                cd_model = await self._load_clinical_decision_by_pk(
                    model.clinical_decision_id,
                )
                cd_biz_id = (
                    cd_model.decision_id
                    if cd_model
                    else str(model.clinical_decision_id)
                )
            except Exception:
                cd_biz_id = str(model.clinical_decision_id)

        trace_id: str | None = None
        if model.traces:
            trace_id = model.traces[0].trace_id

        return ConsensusResponse(
            consensus_id=model.consensus_id,
            patient_id=str(model.patient_id) if model.patient_id else "",
            recommendation_id=rec_biz_id,
            clinical_decision_id=cd_biz_id,
            consensus_status=model.consensus_status,
            consensus_score=model.consensus_score,
            final_recommendation=model.final_recommendation,
            supporting_rationale=model.supporting_rationale,
            dissenting_opinions=model.dissenting_opinions or [],
            unresolved_questions=model.unresolved_questions or [],
            required_follow_up=model.required_follow_up or [],
            participating_specialties=model.participating_specialties or [],
            created_by=str(model.created_by) if model.created_by else None,
            created_at=model.created_at.isoformat() if model.created_at else "",
            trace_id=trace_id,
        )

    async def _load_recommendation_by_pk(self, pk: UUID):
        """Load a recommendation by its primary key (UUID).

        Parameters
        ----------
        pk : UUID
            The primary key UUID of the recommendation.

        Returns
        -------
        RecommendationModel | None
        """
        from src.backend.repositories.recommendation_repo import (
            RecommendationRepository,
        )

        repo = RecommendationRepository(self._db)
        return await repo.get(pk)

    async def _load_clinical_decision_by_pk(self, pk: UUID):
        """Load a clinical decision by its primary key (UUID).

        Parameters
        ----------
        pk : UUID
            The primary key UUID of the clinical decision.

        Returns
        -------
        ClinicalDecisionModel | None
        """
        from src.backend.repositories.clinical_decision_repo import (
            ClinicalDecisionRepository,
        )

        repo = ClinicalDecisionRepository(self._db)
        return await repo.get(pk)


__all__ = [
    "SpecialistOpinionDTO",
    "CreateConsensusRequest",
    "ConsensusResponse",
    "ConsensusListResponse",
    "TumorBoardConsensusService",
]
