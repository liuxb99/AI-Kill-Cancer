"""
Treatment Plan Service — orchestrates treatment plan generation and lifecycle.

Responsibilities
----------------
1. Accept request DTO from the API layer
2. Validate upstream link consistency (P0 — 4 IDs)
3. Load patient, recommendation, clinical decision, and consensus data
4. Build ``EngineInput`` and call ``TreatmentPlanEngine.generate()``
5. Persist TreatmentPlanModel + Phases + Items + Monitoring + Safety Rules + Trace
6. Create ``GraphEvent`` outbox record in the same transaction
7. Manage versioning (new plan → version=1, revise → version+1)
8. Manage plan lifecycle status transitions via ``TreatmentPlanStateMachine``
9. Commit on success, rollback on failure

The API router delegates all business logic here — the router only handles
request validation, authentication, calling the service, and exception mapping.
"""

from __future__ import annotations

import logging
import uuid as _uuid
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.clinical.treatment_plan_engine import (
    EngineInput,
    EngineOutput,
    TreatmentPlanEngine,
)
from src.backend.clinical.treatment_plan_rules import TreatmentPlanRuleSet
from src.backend.clinical.treatment_plan_state_machine import (
    IllegalTransitionError,
    PlanStatus,
    TreatmentPlanStateMachine,
)
from src.backend.domain.treatment_plan import (
    TreatmentItemModel,
    TreatmentMonitoringModel,
    TreatmentPhaseModel,
    TreatmentPlanModel,
    TreatmentPlanTraceModel,
    TreatmentSafetyRuleModel,
)
from src.backend.repositories.clinical_graph_outbox_repo import (
    ClinicalGraphOutboxRepository,
)
from src.backend.repositories.treatment_plan_repo import (
    TreatmentItemRepository,
    TreatmentMonitoringRepository,
    TreatmentPhaseRepository,
    TreatmentPlanRepository,
    TreatmentPlanTraceRepository,
    TreatmentSafetyRuleRepository,
)
from src.backend.schemas.clinical_graph_event import (
    GraphAggregateType,
    GraphEventType,
)

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# Pydantic DTOs
# ═══════════════════════════════════════════════════════════════════════════════


class CreatePlanRequest(BaseModel):
    """Request DTO for creating a treatment plan.

    Attributes
    ----------
    patient_id : str
        UUID string identifying the patient.
    recommendation_id : str
        Business identifier of the recommendation.
    clinical_decision_id : str
        Business identifier of the clinical decision.
    consensus_id : str
        Business identifier of the tumor board consensus.
    plan_intent : str
        Treatment intent (e.g. ``"curative"``, ``"palliative"``).
    treatment_goals : list[str]
        List of treatment goal descriptions.
    clinical_context : dict
        Free-form clinical context (may include ``cancer_type``, ``stage``,
        ``histology``, etc.).
    monitoring_requirements : list[dict]
        Pre-existing monitoring requirements from upstream.
    """

    patient_id: str
    recommendation_id: str
    clinical_decision_id: str
    consensus_id: str
    plan_intent: str
    treatment_goals: list[str] = Field(default_factory=list)
    clinical_context: dict = Field(default_factory=dict)
    monitoring_requirements: list[dict] = Field(default_factory=list)


class TreatmentPlanResponse(BaseModel):
    """Response DTO for a treatment plan.

    Attributes
    ----------
    plan_id : str
        Business identifier (hex-string UUID) of the plan.
    version : int
        Version number (1-based, incremented on revise).
    patient_id : str
        UUID string of the patient.
    recommendation_id : str
        Business identifier of the recommendation.
    clinical_decision_id : str
        Business identifier of the clinical decision.
    consensus_id : str
        Business identifier of the tumor board consensus.
    plan_status : str
        Current status (e.g. ``"draft"``, ``"active"``).
    plan_intent : str
        Treatment intent.
    treatment_goals : list[str]
        Treatment goal descriptions.
    summary : str
        Human-readable plan summary.
    clinical_rationale : str
        Clinical reasoning behind the plan.
    phases : list[dict]
        Ordered treatment phases.
    items : list[dict]
        Treatment items.
    monitoring : list[dict]
        Monitoring schedules.
    safety_rules : list[dict]
        Safety rules.
    alternatives : list[dict]
        Alternative treatment options.
    trace : list[dict]
        Calculation trace steps.
    is_current : bool
        Whether this is the current active version.
    previous_plan_id : str | None
        Business identifier of the previous version (if revised).
    supersedes_plan_id : str | None
        Business identifier this plan supersedes.
    revision_reason : str | None
        Reason for revision (if applicable).
    created_by : str | None
        UUID string of the user who created the plan.
    approved_by : str | None
        UUID string of the user who approved the plan.
    approved_at : str | None
        ISO-8601 timestamp of approval.
    activated_at : str | None
        ISO-8601 timestamp of activation.
    created_at : str
        ISO-8601 formatted creation timestamp.
    """

    plan_id: str
    version: int
    patient_id: str
    recommendation_id: str
    clinical_decision_id: str
    consensus_id: str
    plan_status: str
    plan_intent: str | None = None
    treatment_goals: list[str] = Field(default_factory=list)
    summary: str | None = None
    clinical_rationale: str | None = None
    phases: list[dict] = Field(default_factory=list)
    items: list[dict] = Field(default_factory=list)
    monitoring: list[dict] = Field(default_factory=list)
    safety_rules: list[dict] = Field(default_factory=list)
    alternatives: list[dict] = Field(default_factory=list)
    trace: list[dict] = Field(default_factory=list)
    is_current: bool = True
    previous_plan_id: str | None = None
    supersedes_plan_id: str | None = None
    revision_reason: str | None = None
    created_by: str | None = None
    approved_by: str | None = None
    approved_at: str | None = None
    activated_at: str | None = None
    review_date: str | None = None
    created_at: str


class TreatmentPlanListItem(BaseModel):
    """Lightweight response DTO for listing treatment plans."""

    plan_id: str
    version: int
    patient_id: str
    plan_status: str
    plan_intent: str | None = None
    is_current: bool = True
    created_at: str


# ═══════════════════════════════════════════════════════════════════════════════
# TreatmentPlanService
# ═══════════════════════════════════════════════════════════════════════════════


class TreatmentPlanService:
    """Orchestrates treatment plan generation, persistence, and lifecycle.

    All business logic lives here; the API router calls this service and
    maps the result to HTTP responses.

    Parameters
    ----------
    db : AsyncSession
        The SQLAlchemy async session to use for all persistence.
        Transaction management (commit / rollback) is handled by this service.
    """

    def __init__(
        self,
        db: AsyncSession,
        engine: TreatmentPlanEngine | None = None,
        plan_repo: TreatmentPlanRepository | None = None,
        phase_repo: TreatmentPhaseRepository | None = None,
        item_repo: TreatmentItemRepository | None = None,
        monitoring_repo: TreatmentMonitoringRepository | None = None,
        safety_repo: TreatmentSafetyRuleRepository | None = None,
        trace_repo: TreatmentPlanTraceRepository | None = None,
        outbox_repo: ClinicalGraphOutboxRepository | None = None,
    ) -> None:
        """Inject db session, engine, and repositories."""
        self._db = db
        rule_set = TreatmentPlanRuleSet()
        state_machine = TreatmentPlanStateMachine()
        self._engine = engine or TreatmentPlanEngine(rule_set=rule_set)
        self._state_machine = state_machine
        self._plan_repo = plan_repo or TreatmentPlanRepository(db)
        self._phase_repo = phase_repo or TreatmentPhaseRepository(db)
        self._item_repo = item_repo or TreatmentItemRepository(db)
        self._monitoring_repo = monitoring_repo or TreatmentMonitoringRepository(db)
        self._safety_repo = safety_repo or TreatmentSafetyRuleRepository(db)
        self._trace_repo = trace_repo or TreatmentPlanTraceRepository(db)
        self._outbox_repo = outbox_repo or ClinicalGraphOutboxRepository(db)

    # ── Public API: Plan Creation ──────────────────────────────────────────

    async def create_plan(
        self,
        request: CreatePlanRequest,
        user_id: str,
    ) -> TreatmentPlanResponse:
        """Create a new treatment plan (version 1).

        The method:
        1. Loads all upstream data (recommendation, clinical decision, consensus).
        2. Validates ID consistency across the entire chain (P0).
        3. Loads patient data.
        4. Builds ``EngineInput`` from loaded data.
        5. Calls ``TreatmentPlanEngine.generate()``.
        6. Persists the plan model, phases, items, monitoring, safety rules, and trace.
        7. Creates a ``treatment_plan.created`` outbox event.
        8. Commits the transaction on success, rolls back on failure.
        9. Returns the response DTO.

        Parameters
        ----------
        request : CreatePlanRequest
            The validated request payload.
        user_id : str
            The authenticated user's UUID string.

        Returns
        -------
        TreatmentPlanResponse
            The structured response DTO.

        Raises
        ------
        ValueError
            If upstream link validation fails (API layer converts to 422).
        RuntimeError
            If persistence fails.
        """
        plan_id = _uuid.uuid4().hex
        trace_id = _uuid.uuid4().hex
        created_at = datetime.now(timezone.utc)

        # ── Step 1: Load upstream data ──────────────────────────────────
        recommendation = await self._load_recommendation(
            request.recommendation_id,
        )
        clinical_decision = await self._load_clinical_decision(
            request.clinical_decision_id,
        )
        consensus = await self._load_consensus(
            request.consensus_id,
        )

        # ── Step 2: Validate ID consistency (P0) ───────────────────────
        self._validate_links(
            recommendation=recommendation,
            clinical_decision=clinical_decision,
            consensus=consensus,
            request=request,
        )

        # ── Step 3: Load patient data ──────────────────────────────────
        patient_data = await self._load_patient_data(recommendation.patient_id)

        # ── Step 4: Build EngineInput ──────────────────────────────────
        engine_input = self._build_engine_input(
            request=request,
            recommendation=recommendation,
            clinical_decision=clinical_decision,
            consensus=consensus,
            patient_data=patient_data,
        )

        # ── Step 5: Call engine ────────────────────────────────────────
        try:
            engine_output: EngineOutput = self._engine.generate(engine_input)
        except ValueError:
            raise
        except Exception as exc:
            logger.exception(
                "TreatmentPlanEngine.generate() raised an unhandled exception "
                "for recommendation %s.",
                request.recommendation_id,
            )
            raise RuntimeError(
                "Treatment plan engine encountered an internal error",
            ) from exc

        # ── Step 6: Persist (transaction boundary) ─────────────────────
        try:
            plan_model = await self._persist_plan(
                plan_id=plan_id,
                version=1,
                recommendation=recommendation,
                clinical_decision=clinical_decision,
                consensus=consensus,
                request=request,
                engine_output=engine_output,
                trace_id=trace_id,
                user_id=user_id,
                created_at=created_at,
            )

            # ── Step 7: Create outbox event (same transaction) ──────────
            await self._create_outbox_event(
                event_type=GraphEventType.TREATMENT_PLAN_CREATED,
                plan_model=plan_model,
                engine_output=engine_output,
                request=request,
                actor_id=user_id,
            )

            await self._db.commit()
        except Exception as exc:
            await self._db.rollback()
            logger.exception(
                "Failed to persist treatment plan %s — rolled back.",
                plan_id,
            )
            raise RuntimeError("Failed to persist treatment plan") from exc

        # ── Step 9: Build response ─────────────────────────────────────
        return await self._model_to_response(plan_model, engine_output)

    async def get_plan(self, plan_id: str) -> TreatmentPlanResponse | None:
        """Retrieve a treatment plan by its business identifier.

        Parameters
        ----------
        plan_id : str
            The hex-string UUID returned by ``create_plan``.

        Returns
        -------
        TreatmentPlanResponse | None
            The response DTO, or ``None`` if not found.
        """
        model = await self._plan_repo.get_by_plan_id(plan_id)
        if model is None:
            return None
        return await self._model_to_response(model)

    async def list_plans(
        self,
        patient_id: str,
        skip: int = 0,
        limit: int = 20,
    ) -> list[TreatmentPlanListItem]:
        """List treatment plans for a patient, newest first.

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
        list[TreatmentPlanListItem]
        """
        patient_uuid = UUID(patient_id)
        models = await self._plan_repo.list_by_patient_id(
            patient_id=patient_uuid,
            skip=skip,
            limit=limit,
        )
        return [
            TreatmentPlanListItem(
                plan_id=m.plan_id,
                version=m.version,
                patient_id=str(m.patient_id) if m.patient_id else "",
                plan_status=m.plan_status,
                plan_intent=m.plan_intent,
                is_current=m.is_current,
                created_at=m.created_at.isoformat() if m.created_at else "",
            )
            for m in models
        ]

    async def get_versions(self, plan_id: str) -> list[TreatmentPlanResponse]:
        """List all versions of a treatment plan.

        Parameters
        ----------
        plan_id : str
            The business identifier shared across versions.

        Returns
        -------
        list[TreatmentPlanResponse]
        """
        models = await self._plan_repo.list_versions(plan_id)
        return [await self._model_to_response(m) for m in models]

    async def get_trace(self, plan_id: str) -> list[dict]:
        """Retrieve the calculation trace for a given plan.

        Parameters
        ----------
        plan_id : str
            The business identifier of the plan.

        Returns
        -------
        list[dict]
            Serialised trace steps.  Returns an empty list if the plan
            is not found.
        """
        model = await self._plan_repo.get_by_plan_id(plan_id)
        if model is None:
            return []
        traces = await self._trace_repo.list_by_plan_id(model.id)
        return [
            {
                "trace_id": t.trace_id,
                "step_order": t.step_order,
                "step_type": t.step_type,
                "input_summary": t.input_summary,
                "output_summary": t.output_summary,
                "rule_ids": t.rule_ids,
                "evidence_ids": t.evidence_ids,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in traces
        ]

    # ── Public API: Status Transitions ─────────────────────────────────────

    async def _transition_status(
        self,
        plan_id: str,
        target_status: PlanStatus,
        user_id: str,
        event_type: GraphEventType,
    ) -> TreatmentPlanResponse:
        """Apply a status transition and persist the change.

        Parameters
        ----------
        plan_id : str
            The business identifier of the plan.
        target_status : PlanStatus
            The desired target status.
        user_id : str
            The authenticated user's UUID string.
        event_type : GraphEventType
            The outbox event type for this transition.

        Returns
        -------
        TreatmentPlanResponse

        Raises
        ------
        ValueError
            If the plan is not found.
        IllegalTransitionError
            If the transition is not allowed.
        RuntimeError
            If persistence fails.
        """
        model = await self._plan_repo.get_by_plan_id(plan_id)
        if model is None:
            raise ValueError(f"Treatment plan with id '{plan_id}' not found")

        current_status = PlanStatus(model.plan_status)
        self._state_machine.transition(current_status, target_status)

        now = datetime.now(timezone.utc)

        # Update status and timestamp fields based on target
        model.plan_status = target_status.value
        model.updated_at = now

        if target_status == PlanStatus.APPROVED:
            model.approved_by = UUID(user_id) if user_id else None
            model.approved_at = now
        elif target_status == PlanStatus.ACTIVE:
            model.activated_at = now
        elif target_status == PlanStatus.PAUSED:
            model.paused_at = now
        elif target_status == PlanStatus.COMPLETED:
            model.completed_at = now
        elif target_status == PlanStatus.CANCELLED:
            model.cancelled_at = now

        # Outbox event
        try:
            await self._db.flush()

            await self._create_outbox_event(
                event_type=event_type,
                plan_model=model,
                engine_output=None,
                request=None,
                actor_id=user_id,
            )
            await self._db.commit()
        except Exception as exc:
            await self._db.rollback()
            logger.exception(
                "Failed to persist status transition for plan %s — rolled back.",
                plan_id,
            )
            raise RuntimeError("Failed to persist status transition") from exc

        return await self._model_to_response(model)

    async def submit_plan(self, plan_id: str, user_id: str) -> TreatmentPlanResponse:
        """Submit plan for review: draft → proposed."""
        return await self._transition_status(
            plan_id=plan_id,
            target_status=PlanStatus.PROPOSED,
            user_id=user_id,
            event_type=GraphEventType.TREATMENT_PLAN_UPDATED,
        )

    async def review_plan(self, plan_id: str, user_id: str) -> TreatmentPlanResponse:
        """Review plan: proposed → under_review."""
        return await self._transition_status(
            plan_id=plan_id,
            target_status=PlanStatus.UNDER_REVIEW,
            user_id=user_id,
            event_type=GraphEventType.TREATMENT_PLAN_UPDATED,
        )

    async def approve_plan(self, plan_id: str, user_id: str) -> TreatmentPlanResponse:
        """Approve plan: under_review → approved."""
        return await self._transition_status(
            plan_id=plan_id,
            target_status=PlanStatus.APPROVED,
            user_id=user_id,
            event_type=GraphEventType.TREATMENT_PLAN_APPROVED,
        )

    async def activate_plan(self, plan_id: str, user_id: str) -> TreatmentPlanResponse:
        """Activate plan: approved → active."""
        return await self._transition_status(
            plan_id=plan_id,
            target_status=PlanStatus.ACTIVE,
            user_id=user_id,
            event_type=GraphEventType.TREATMENT_PLAN_ACTIVATED,
        )

    async def pause_plan(self, plan_id: str, user_id: str) -> TreatmentPlanResponse:
        """Pause plan: active → paused."""
        return await self._transition_status(
            plan_id=plan_id,
            target_status=PlanStatus.PAUSED,
            user_id=user_id,
            event_type=GraphEventType.TREATMENT_PLAN_PAUSED,
        )

    async def complete_plan(self, plan_id: str, user_id: str) -> TreatmentPlanResponse:
        """Complete plan: active → completed."""
        return await self._transition_status(
            plan_id=plan_id,
            target_status=PlanStatus.COMPLETED,
            user_id=user_id,
            event_type=GraphEventType.TREATMENT_PLAN_COMPLETED,
        )

    async def cancel_plan(self, plan_id: str, user_id: str) -> TreatmentPlanResponse:
        """Cancel plan: any non-terminal → cancelled."""
        return await self._transition_status(
            plan_id=plan_id,
            target_status=PlanStatus.CANCELLED,
            user_id=user_id,
            event_type=GraphEventType.TREATMENT_PLAN_CANCELLED,
        )

    async def revise_plan(
        self,
        plan_id: str,
        request: CreatePlanRequest,
        user_id: str,
    ) -> TreatmentPlanResponse:
        """Create a new version of an existing plan.

        The previous current version is marked as superseded (is_current=False)
        and a new version (version+1) is created with the updated data.

        Parameters
        ----------
        plan_id : str
            The business identifier of the plan to revise.
        request : CreatePlanRequest
            The updated request payload.
        user_id : str
            The authenticated user's UUID string.

        Returns
        -------
        TreatmentPlanResponse
            The new version's response DTO.
        """
        # Load the current version
        current_model = await self._plan_repo.get_by_plan_id(plan_id)
        if current_model is None:
            raise ValueError(f"Treatment plan with id '{plan_id}' not found")

        # RevisionPolicy: only allow revision for approved / active / paused plans
        allowed_statuses = {
            PlanStatus.APPROVED,
            PlanStatus.ACTIVE,
            PlanStatus.PAUSED,
        }
        if current_model.plan_status not in allowed_statuses:
            raise IllegalTransitionError(
                current=current_model.plan_status,
                target="revise",
            )

        # Create the new version
        new_plan_id = plan_id
        new_version = current_model.version + 1
        trace_id = _uuid.uuid4().hex
        created_at = datetime.now(timezone.utc)

        # Load upstream data for the new version
        recommendation = await self._load_recommendation(
            request.recommendation_id,
        )
        clinical_decision = await self._load_clinical_decision(
            request.clinical_decision_id,
        )
        consensus = await self._load_consensus(
            request.consensus_id,
        )

        self._validate_links(
            recommendation=recommendation,
            clinical_decision=clinical_decision,
            consensus=consensus,
            request=request,
        )

        patient_data = await self._load_patient_data(recommendation.patient_id)

        engine_input = self._build_engine_input(
            request=request,
            recommendation=recommendation,
            clinical_decision=clinical_decision,
            consensus=consensus,
            patient_data=patient_data,
        )

        try:
            engine_output: EngineOutput = self._engine.generate(engine_input)
        except ValueError:
            raise
        except Exception as exc:
            logger.exception(
                "TreatmentPlanEngine.generate() raised an unhandled exception "
                "during revision for plan %s.",
                plan_id,
            )
            raise RuntimeError(
                "Treatment plan engine encountered an internal error",
            ) from exc

        # Transaction: mark old as superseded, persist new version
        try:
            # Mark previous version as superseded
            await self._plan_repo.mark_superseded(
                plan_id=plan_id,
                superseded_by_plan_id=new_plan_id,
                revision_reason=request.clinical_context.get("revision_reason", ""),
            )

            # Persist new version
            new_plan_model = await self._persist_plan(
                plan_id=new_plan_id,
                version=new_version,
                recommendation=recommendation,
                clinical_decision=clinical_decision,
                consensus=consensus,
                request=request,
                engine_output=engine_output,
                trace_id=trace_id,
                user_id=user_id,
                created_at=created_at,
                previous_plan_id=plan_id,
            )

            # Outbox: superseded + created
            await self._create_outbox_event(
                event_type=GraphEventType.TREATMENT_PLAN_SUPERSEDED,
                plan_model=current_model,
                engine_output=None,
                request=None,
                actor_id=user_id,
            )
            await self._create_outbox_event(
                event_type=GraphEventType.TREATMENT_PLAN_CREATED,
                plan_model=new_plan_model,
                engine_output=engine_output,
                request=request,
                actor_id=user_id,
            )

            await self._db.commit()
        except Exception as exc:
            await self._db.rollback()
            logger.exception(
                "Failed to persist revised plan %s — rolled back.",
                new_plan_id,
            )
            raise RuntimeError("Failed to persist revised treatment plan") from exc

        return await self._model_to_response(new_plan_model, engine_output)

    # ── Internal: Persistence ──────────────────────────────────────────────

    async def _persist_plan(
        self,
        *,
        plan_id: str,
        version: int,
        recommendation,
        clinical_decision,
        consensus,
        request: CreatePlanRequest,
        engine_output: EngineOutput,
        trace_id: str,
        user_id: str,
        created_at: datetime,
        previous_plan_id: str | None = None,
    ) -> TreatmentPlanModel:
        """Persist the plan model and all related sub-models.

        Does **not** commit — the caller is responsible for calling
        ``self._db.commit()`` (and ``self._db.rollback()`` on failure).
        """
        # ── Plan model ──────────────────────────────────────────────────
        plan_model = TreatmentPlanModel(
            plan_id=plan_id,
            version=version,
            patient_id=recommendation.patient_id,
            recommendation_id=recommendation.id,
            clinical_decision_id=clinical_decision.id,
            consensus_id=consensus.id,
            plan_status=engine_output.plan_status,
            plan_intent=request.plan_intent,
            treatment_goals=request.treatment_goals,
            summary=engine_output.summary,
            clinical_rationale=engine_output.clinical_rationale,
            is_current=True,
            previous_plan_id=previous_plan_id,
            created_by=UUID(user_id) if user_id else None,
            created_at=created_at,
            updated_at=created_at,
            alternative_options=engine_output.alternatives,
        )
        await self._plan_repo.create(plan_model)
        # plan_model.id now populated by flush

        # ── Phases ──────────────────────────────────────────────────────
        phase_models: list[TreatmentPhaseModel] = []
        phase_dicts: dict[str, TreatmentPhaseModel] = {}  # phase_type -> model
        for phase_data in engine_output.phases:
            phase_id = _uuid.uuid4().hex
            phase_model = TreatmentPhaseModel(
                id=_uuid.uuid4(),  # 显式设置 PK，确保即使在 mock 测试中也有值
                phase_id=phase_id,
                plan_id=plan_model.id,
                phase_order=phase_data.get("order", 0),
                phase_type=phase_data.get("phase_type", "unknown"),
                name=phase_data.get("name", ""),
                description=phase_data.get("description"),
                duration_days=phase_data.get("duration_days"),
                status="planned",
                created_at=created_at,
                updated_at=created_at,
            )
            phase_models.append(phase_model)
            phase_dicts[phase_model.phase_type] = phase_model

        await self._phase_repo.create_many(phase_models)
        # phase_models now have their id populated

        # ── Treatment Items ─────────────────────────────────────────────
        item_models: list[TreatmentItemModel] = []
        for idx, item_data in enumerate(engine_output.items):
            # Determine phase assignment based on item type or first phase
            phase_id = None
            # Use phase_type from item if available, otherwise item_type
            item_phase_type = item_data.get("phase_type") or item_data.get("item_type", "")
            matched_phase = phase_dicts.get(item_phase_type)
            if matched_phase is not None:
                phase_id = matched_phase.id
            else:
                # Fallback to first phase if no matching phase found
                first_phase = next(iter(phase_models), None)
                if first_phase is not None:
                    phase_id = first_phase.id

            item_id = _uuid.uuid4().hex
            item_model = TreatmentItemModel(
                item_id=item_id,
                plan_id=plan_model.id,
                phase_id=phase_id,
                item_order=idx,
                item_type=item_data.get("item_type", "medication"),
                name=item_data.get("name", item_data.get("drug_name", "Unknown")),
                description=item_data.get("description"),
                priority=item_data.get("priority"),
                rationale=item_data.get("rationale"),
                source_recommendation=item_data.get("source_recommendation"),
                drug_id=item_data.get("drug_id"),
                procedure_code=item_data.get("procedure_code"),
                frequency=item_data.get("frequency"),
                duration=item_data.get("duration"),
                route=item_data.get("route"),
                planned_dose_text=item_data.get("planned_dose_text"),
                status="planned",
                created_at=created_at,
                updated_at=created_at,
            )
            item_models.append(item_model)

        await self._item_repo.create_many(item_models)

        # ── Monitoring ──────────────────────────────────────────────────
        monitoring_models: list[TreatmentMonitoringModel] = []
        for m_data in engine_output.monitoring:
            monitoring_id = _uuid.uuid4().hex
            phase_type = m_data.get("phase_type")
            phase_ref = phase_dicts.get(phase_type) if phase_type else None

            monitoring_model = TreatmentMonitoringModel(
                monitoring_id=monitoring_id,
                plan_id=plan_model.id,
                phase_id=phase_ref.id if phase_ref else None,
                monitoring_type=m_data.get("monitoring_type", "clinical_assessment"),
                name=m_data.get("name", "Monitoring"),
                schedule=m_data.get("schedule"),
                baseline_required=m_data.get("baseline_required", False),
                repeat_interval=m_data.get("repeat_interval"),
                target_range=m_data.get("target_range"),
                warning_threshold=m_data.get("warning_threshold"),
                critical_threshold=m_data.get("critical_threshold"),
                action_if_abnormal=m_data.get("action_if_abnormal"),
                responsible_specialty=m_data.get("responsible_specialty"),
                created_at=created_at,
                updated_at=created_at,
            )
            monitoring_models.append(monitoring_model)

        await self._monitoring_repo.create_many(monitoring_models)

        # ── Safety Rules ────────────────────────────────────────────────
        safety_models: list[TreatmentSafetyRuleModel] = []
        for idx, s_data in enumerate(engine_output.safety_rules):
            rule_id = _uuid.uuid4().hex
            safety_model = TreatmentSafetyRuleModel(
                rule_id=rule_id,
                plan_id=plan_model.id,
                rule_type=s_data.get("rule_type", "review"),
                condition=s_data.get("condition"),
                severity=s_data.get("severity", "medium"),
                recommended_action=s_data.get("recommended_action"),
                requires_review=s_data.get("requires_review", True),
                source=s_data.get("source", "engine"),
                created_at=created_at,
            )
            safety_models.append(safety_model)

        await self._safety_repo.create_many(safety_models)

        # ── Trace ───────────────────────────────────────────────────────
        trace_models: list[TreatmentPlanTraceModel] = []
        for step_data in engine_output.trace:
            step_trace_id = trace_id
            trace_model = TreatmentPlanTraceModel(
                trace_id=step_trace_id,
                plan_id=plan_model.id,
                step_order=step_data.get("step_order", 0),
                step_type=step_data.get("step_type", "unknown"),
                input_summary=step_data.get("input_summary"),
                output_summary=step_data.get("output_summary"),
                rule_ids=step_data.get("rule_ids"),
                evidence_ids=step_data.get("evidence_ids"),
                created_at=created_at,
            )
            trace_models.append(trace_model)

        await self._trace_repo.create_many(trace_models)

        return plan_model

    # ── Internal: Outbox Event ────────────────────────────────────────────

    async def _create_outbox_event(
        self,
        event_type: GraphEventType,
        plan_model: TreatmentPlanModel,
        engine_output: EngineOutput | None,
        request: CreatePlanRequest | None,
        actor_id: str | None = None,
    ) -> None:
        """Create an outbox event for the treatment plan aggregate.

        The event is created in the same transaction as the plan data.
        The caller (service method) controls commit/rollback.
        """
        payload: dict[str, Any] = {
            "plan_id": plan_model.plan_id,
            "version": plan_model.version,
            "patient_id": str(plan_model.patient_id) if plan_model.patient_id else "",
            "status": plan_model.plan_status,
        }

        if plan_model.recommendation_id:
            payload["recommendation_id"] = str(plan_model.recommendation_id)
        if plan_model.clinical_decision_id:
            payload["clinical_decision_id"] = str(plan_model.clinical_decision_id)
        if plan_model.consensus_id:
            payload["consensus_id"] = str(plan_model.consensus_id)

        if plan_model.treatment_goals:
            payload["goals"] = plan_model.treatment_goals

        if engine_output is not None:
            payload["phases"] = engine_output.phases
            payload["items"] = engine_output.items
            payload["monitoring"] = engine_output.monitoring
            payload["safety_rules"] = engine_output.safety_rules
            payload["alternatives"] = engine_output.alternatives

        if plan_model.approved_by:
            payload["approved_by"] = str(plan_model.approved_by)
        if plan_model.approved_at:
            payload["approved_at"] = plan_model.approved_at.isoformat()

        await self._outbox_repo.create(
            aggregate_type=GraphAggregateType.TREATMENT_PLAN.value,
            aggregate_id=plan_model.plan_id,
            event_type=event_type.value,
            schema_version=1,
            payload=payload,
            actor_id=actor_id,
            occurred_at=datetime.now(timezone.utc),
        )

    # ── Internal: Upstream Data Loading ───────────────────────────────────

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

    async def _load_consensus(self, consensus_id: str):
        """Load a tumor board consensus by its business identifier.

        Parameters
        ----------
        consensus_id : str
            The consensus's business identifier
            (``TumorBoardConsensusModel.consensus_id``).

        Returns
        -------
        TumorBoardConsensusModel

        Raises
        ------
        ValueError
            If the consensus is not found.
        """
        from src.backend.repositories.tumor_board_repo import (
            TumorBoardConsensusRepository,
        )

        repo = TumorBoardConsensusRepository(self._db)
        model = await repo.get_by_uuid(consensus_id)
        if model is None:
            raise ValueError(
                f"Consensus with id '{consensus_id}' not found",
            )
        return model

    async def _load_patient_data(self, patient_uuid: UUID) -> dict[str, Any]:
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

    # ── Internal: Validation ──────────────────────────────────────────────

    @staticmethod
    def _validate_links(
        recommendation,
        clinical_decision,
        consensus,
        request: CreatePlanRequest,
    ) -> None:
        """P0 validation: ensure patient/recommendation/decision/consensus links match.

        Checks:
        - recommendation.patient_id == request.patient_id
        - clinical_decision.patient_id == request.patient_id
        - consensus.patient_id == request.patient_id
        - clinical_decision.recommendation_id (FK) == recommendation.id (PK)
        - consensus.clinical_decision_id (FK) == clinical_decision.id (PK)
        - consensus.recommendation_id (FK) == recommendation.id (PK)

        Parameters
        ----------
        recommendation : RecommendationModel
            The loaded recommendation model.
        clinical_decision : ClinicalDecisionModel
            The loaded clinical decision model.
        consensus : TumorBoardConsensusModel
            The loaded consensus model.
        request : CreatePlanRequest
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
        cons_patient_id = (
            str(consensus.patient_id) if consensus.patient_id else None
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
        if cons_patient_id != request.patient_id:
            raise ValueError(
                f"Consensus '{request.consensus_id}' belongs to "
                f"patient '{cons_patient_id}', not patient '{request.patient_id}'",
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

        # Verify the consensus's clinical_decision FK matches the CD's PK
        cons_cd_fk = (
            str(consensus.clinical_decision_id)
            if consensus.clinical_decision_id
            else None
        )
        cd_pk = str(clinical_decision.id) if clinical_decision.id else None
        if cons_cd_fk != cd_pk:
            raise ValueError(
                f"Consensus '{request.consensus_id}' references "
                f"clinical decision '{cons_cd_fk}', but request specifies "
                f"clinical decision '{request.clinical_decision_id}' "
                f"(PK: '{cd_pk}') — link mismatch",
            )

        # Verify the consensus's recommendation FK matches the recommendation's PK
        cons_rec_fk = (
            str(consensus.recommendation_id)
            if consensus.recommendation_id
            else None
        )
        if cons_rec_fk != rec_pk:
            raise ValueError(
                f"Consensus '{request.consensus_id}' references "
                f"recommendation '{cons_rec_fk}', but request specifies "
                f"recommendation '{request.recommendation_id}' "
                f"(PK: '{rec_pk}') — link mismatch",
            )

    # ── Internal: Engine Input Construction ───────────────────────────────

    @staticmethod
    def _build_engine_input(
        request: CreatePlanRequest,
        recommendation,
        clinical_decision,
        consensus,
        patient_data: dict[str, Any],
    ) -> EngineInput:
        """Build the engine input from upstream data.

        Parameters
        ----------
        request : CreatePlanRequest
            The validated request payload.
        recommendation : RecommendationModel
            The loaded recommendation model.
        clinical_decision : ClinicalDecisionModel
            The loaded clinical decision model.
        consensus : TumorBoardConsensusModel
            The loaded consensus model.
        patient_data : dict
            Patient data dictionary.

        Returns
        -------
        EngineInput
        """
        # Build recommendation dict
        rec_dict: dict[str, Any] = {
            "id": str(recommendation.id) if recommendation.id else None,
            "recommendation_id": recommendation.recommendation_id,
            "patient_id": str(recommendation.patient_id) if recommendation.patient_id else None,
            "status": recommendation.status,
        }
        if recommendation.result_payload:
            rec_dict.update(recommendation.result_payload)

        # Build clinical decision dict
        cd_dict: dict[str, Any] = {
            "id": str(clinical_decision.id) if clinical_decision.id else None,
            "decision_id": clinical_decision.decision_id,
            "patient_id": str(clinical_decision.patient_id) if clinical_decision.patient_id else None,
            "decision_type": clinical_decision.decision_type,
            "reason": clinical_decision.reason,
            "confidence": clinical_decision.confidence,
            "alternatives": clinical_decision.alternatives or [],
            "contraindications": clinical_decision.contraindications or [],
        }

        # Build consensus dict
        cons_dict: dict[str, Any] = {
            "id": str(consensus.id) if consensus.id else None,
            "consensus_id": consensus.consensus_id,
            "patient_id": str(consensus.patient_id) if consensus.patient_id else None,
            "consensus_status": consensus.consensus_status,
            "consensus_score": consensus.consensus_score,
            "supporting_rationale": consensus.supporting_rationale,
            "final_recommendation": consensus.final_recommendation,
            "dissenting_opinions": consensus.dissenting_opinions or [],
            "participating_specialties": consensus.participating_specialties or [],
        }

        # Extract evidence summary and contraindications from CD
        evidence_summary: list[dict] = []
        if clinical_decision.evidence_summary:
            evidence_summary = [clinical_decision.evidence_summary]

        contraindications: list[dict] = clinical_decision.contraindications or []

        return EngineInput(
            patient_id=request.patient_id,
            recommendation_id=request.recommendation_id,
            clinical_decision_id=request.clinical_decision_id,
            consensus_id=request.consensus_id,
            plan_intent=request.plan_intent,
            treatment_goals=list(request.treatment_goals),
            clinical_context=dict(request.clinical_context),
            patient=patient_data,
            recommendation=rec_dict,
            clinical_decision=cd_dict,
            consensus=cons_dict,
            evidence_summary=evidence_summary,
            contraindications=contraindications,
            monitoring_requirements=list(request.monitoring_requirements),
        )

    # ── Internal: Response Conversion ─────────────────────────────────────

    async def _model_to_response(
        self,
        model: TreatmentPlanModel,
        engine_output: EngineOutput | None = None,
    ) -> TreatmentPlanResponse:
        """Convert a ``TreatmentPlanModel`` to a response DTO.

        Parameters
        ----------
        model : TreatmentPlanModel
            The loaded model (phases, items, monitoring, safety_rules, traces
            loaded via selectin relationships).
        engine_output : EngineOutput, optional
            If provided, use engine output data for structured fields.
            Otherwise, load from related models.

        Returns
        -------
        TreatmentPlanResponse
        """
        if engine_output is not None:
            phases = list(engine_output.phases)
            items = list(engine_output.items)
            monitoring = list(engine_output.monitoring)
            safety_rules = list(engine_output.safety_rules)
            alternatives = list(engine_output.alternatives)
            trace = list(engine_output.trace)
        else:
            # Load from related models
            phases = [
                {
                    "phase_id": p.phase_id,
                    "phase_order": p.phase_order,
                    "phase_type": p.phase_type,
                    "name": p.name,
                    "description": p.description,
                    "duration_days": p.duration_days,
                    "status": p.status,
                }
                for p in (model.phases or [])
            ]
            items = [
                {
                    "item_id": i.item_id,
                    "item_order": i.item_order,
                    "item_type": i.item_type,
                    "name": i.name,
                    "description": i.description,
                    "priority": i.priority,
                    "status": i.status,
                    "rationale": i.rationale,
                }
                for i in (model.items or [])
            ]
            monitoring = [
                {
                    "monitoring_id": m.monitoring_id,
                    "monitoring_type": m.monitoring_type,
                    "name": m.name,
                    "schedule": m.schedule,
                    "baseline_required": m.baseline_required,
                    "repeat_interval": m.repeat_interval,
                }
                for m in (model.monitoring or [])
            ]
            safety_rules = [
                {
                    "rule_id": r.rule_id,
                    "rule_type": r.rule_type,
                    "condition": r.condition,
                    "severity": r.severity,
                    "recommended_action": r.recommended_action,
                    "requires_review": r.requires_review,
                }
                for r in (model.safety_rules or [])
            ]
            alternatives = model.alternative_options or []
            trace = [
                {
                    "trace_id": t.trace_id,
                    "step_order": t.step_order,
                    "step_type": t.step_type,
                    "input_summary": t.input_summary,
                    "output_summary": t.output_summary,
                }
                for t in (model.traces or [])
            ]

        return TreatmentPlanResponse(
            plan_id=model.plan_id,
            version=model.version,
            patient_id=str(model.patient_id) if model.patient_id else "",
            recommendation_id=(
                str(model.recommendation_id) if model.recommendation_id else ""
            ),
            clinical_decision_id=(
                str(model.clinical_decision_id)
                if model.clinical_decision_id
                else ""
            ),
            consensus_id=str(model.consensus_id) if model.consensus_id else "",
            plan_status=model.plan_status,
            plan_intent=model.plan_intent,
            treatment_goals=model.treatment_goals or [],
            summary=model.summary,
            clinical_rationale=model.clinical_rationale,
            phases=phases,
            items=items,
            monitoring=monitoring,
            safety_rules=safety_rules,
            alternatives=alternatives,
            trace=trace,
            is_current=model.is_current,
            previous_plan_id=model.previous_plan_id,
            supersedes_plan_id=model.supersedes_plan_id,
            revision_reason=model.revision_reason,
            created_by=str(model.created_by) if model.created_by else None,
            approved_by=str(model.approved_by) if model.approved_by else None,
            approved_at=model.approved_at.isoformat() if model.approved_at else None,
            activated_at=model.activated_at.isoformat() if model.activated_at else None,
            review_date=model.review_date.isoformat() if model.review_date else None,
            created_at=model.created_at.isoformat() if model.created_at else "",
        )


__all__ = [
    "CreatePlanRequest",
    "TreatmentPlanResponse",
    "TreatmentPlanListItem",
    "TreatmentPlanService",
]
