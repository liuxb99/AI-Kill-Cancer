"""
Tests for TreatmentPlanService (Phase 3E Batch 2).

Covers:
- Successful full create_plan flow
- Upstream ID consistency validation (5 mismatch scenarios)
- created_by recording
- Transaction rollback on various persistence failures
- Revision versioning
- Status transitions (approval)
- get_plan, list_plans, get_trace, get_versions
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.clinical.treatment_plan_engine import EngineOutput
from src.backend.clinical.treatment_plan_state_machine import (
    IllegalTransitionError,
    PlanStatus,
)
from src.backend.domain.treatment_plan import TreatmentPlanModel
from src.backend.schemas.clinical_graph_event import (
    GraphAggregateType,
    GraphEventType,
)
from src.backend.services.treatment_plan_service import (
    CreatePlanRequest,
    TreatmentPlanResponse,
    TreatmentPlanService,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════


def _make_uuid(seed: str = "00000001") -> uuid.UUID:
    """Deterministic UUID from an 8-char hex seed (first group)."""
    return uuid.UUID(f"{seed}-0000-0000-0000-000000000000")


PATIENT_UUID = _make_uuid("10000001")
REC_UUID = _make_uuid("20000001")
REC_BIZ_ID = "rec-001"
CD_UUID = _make_uuid("30000001")
CD_BIZ_ID = "cd-001"
CONS_UUID = _make_uuid("40000001")
CONS_BIZ_ID = "cons-001"
USER_UUID = _make_uuid("90000001")
WRONG_UUID = _make_uuid("99999999")
WRONG_UUID2 = _make_uuid("88888888")


def _make_recommendation_model(patient_id: uuid.UUID | None = PATIENT_UUID):
    """Create a mock RecommendationModel."""
    model = MagicMock()
    model.id = REC_UUID
    model.patient_id = patient_id
    model.recommendation_id = REC_BIZ_ID
    model.status = "completed"
    model.result_payload = {
        "recommendations": [
            {"drug_name": "Lenvatinib", "rank": 1, "overall_score": 0.95},
            {"drug_name": "Sorafenib", "rank": 2, "overall_score": 0.72},
        ],
    }
    return model


def _make_clinical_decision_model(
    patient_id: uuid.UUID | None = PATIENT_UUID,
    recommendation_fk: uuid.UUID | None = REC_UUID,
):
    """Create a mock ClinicalDecisionModel."""
    model = MagicMock()
    model.id = CD_UUID
    model.patient_id = patient_id
    model.decision_id = CD_BIZ_ID
    model.recommendation_id = recommendation_fk
    model.decision_type = "approved"
    model.reason = "Strong evidence for Lenvatinib"
    model.confidence = "high"
    model.evidence_summary = {"drug": "Lenvatinib", "level": "Level_1"}
    model.alternatives = [
        {"drug_name": "Sorafenib", "rank": 2, "overall_score": 0.72, "rationale": "Alternative"},
    ]
    model.contraindications = []
    return model


def _make_consensus_model(
    patient_id: uuid.UUID | None = PATIENT_UUID,
    recommendation_fk: uuid.UUID | None = REC_UUID,
    clinical_decision_fk: uuid.UUID | None = CD_UUID,
):
    """Create a mock TumorBoardConsensusModel."""
    model = MagicMock()
    model.id = CONS_UUID
    model.patient_id = patient_id
    model.consensus_id = CONS_BIZ_ID
    model.recommendation_id = recommendation_fk
    model.clinical_decision_id = clinical_decision_fk
    model.consensus_status = "unanimous"
    model.consensus_score = 1.0
    model.supporting_rationale = "All specialists agree"
    model.final_recommendation = "Lenvatinib"
    model.dissenting_opinions = []
    model.participating_specialties = ["medical_oncology"]
    return model


def _make_engine_output(overrides: dict | None = None) -> EngineOutput:
    """Create a minimal EngineOutput."""
    defaults: dict[str, Any] = {
        "summary": "Test plan summary",
        "clinical_rationale": "Test rationale",
        "phases": [
            {"phase_type": "preparation", "name": "Preparation", "order": 1, "duration_days": 14},
            {"phase_type": "primary_treatment", "name": "Primary Treatment", "order": 2, "duration_days": 90},
        ],
        "items": [
            {
                "item_type": "medication",
                "name": "Lenvatinib",
                "description": "Primary recommendation: Lenvatinib",
                "priority": 1,
                "rationale": "Top-ranked drug",
                "source_recommendation": "recommendation_engine",
            },
        ],
        "monitoring": [
            {
                "monitoring_type": "laboratory",
                "name": "Complete Blood Count",
                "schedule": "weekly",
                "baseline_required": True,
                "repeat_interval": "7d",
                "phase_type": "primary_treatment",
            },
        ],
        "safety_rules": [
            {
                "rule_type": "review",
                "condition": {"type": "contraindication", "detail": "test"},
                "severity": "medium",
                "recommended_action": "Review",
                "requires_review": True,
                "source": "engine",
            },
        ],
        "alternatives": [
            {"drug_name": "Sorafenib", "rank": 2, "overall_score": 0.72, "rationale": "Alternative", "priority": 50},
        ],
        "trace": [
            {"step_order": 0, "step_type": "load_context", "input_summary": {}, "output_summary": {}},
            {"step_order": 1, "step_type": "validate_links", "input_summary": {}, "output_summary": {}},
        ],
        "review_date": None,
        "plan_status": "draft",
    }
    if overrides:
        defaults.update(overrides)
    return EngineOutput(**defaults)


def _make_plan_model(
    plan_id: str = "plan-001",
    version: int = 1,
    patient_id: uuid.UUID = PATIENT_UUID,
    plan_status: str = "draft",
    **kwargs,
) -> TreatmentPlanModel:
    """Create a minimal TreatmentPlanModel for testing."""
    now = datetime.now(timezone.utc)
    model = TreatmentPlanModel(
        plan_id=plan_id,
        version=version,
        patient_id=patient_id,
        plan_status=plan_status,
        plan_intent="curative",
        treatment_goals=["goal_1"],
        summary="Test summary",
        clinical_rationale="Test rationale",
        is_current=True,
        created_by=USER_UUID,
        created_at=now,
        updated_at=now,
    )
    # Set PK manually since we bypass the session
    model.id = _make_uuid(f"5000000{version}")
    # Set version-specific kwargs
    for k, v in kwargs.items():
        setattr(model, k, v)
    return model


def sample_request() -> CreatePlanRequest:
    """Create a valid sample request."""
    return CreatePlanRequest(
        patient_id=str(PATIENT_UUID),
        recommendation_id=REC_BIZ_ID,
        clinical_decision_id=CD_BIZ_ID,
        consensus_id=CONS_BIZ_ID,
        plan_intent="curative",
        treatment_goals=["tumor_resection", "prevent_recurrence"],
        clinical_context={"cancer_type": "PTC"},
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def mock_db():
    """Create a mock AsyncSession."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def mock_repos(mock_db):
    """Create mock repositories and return a dict of them."""
    return {
        "db": mock_db,
        "plan_repo": AsyncMock(),
        "phase_repo": AsyncMock(),
        "item_repo": AsyncMock(),
        "monitoring_repo": AsyncMock(),
        "safety_repo": AsyncMock(),
        "trace_repo": AsyncMock(),
        "outbox_repo": AsyncMock(),
        "engine": MagicMock(),
    }


def _make_service(mock_repos) -> TreatmentPlanService:
    """Build a TreatmentPlanService with mocked repos."""
    repos = mock_repos
    repos["engine"].generate.return_value = _make_engine_output()
    return TreatmentPlanService(
        db=repos["db"],
        engine=repos["engine"],
        plan_repo=repos["plan_repo"],
        phase_repo=repos["phase_repo"],
        item_repo=repos["item_repo"],
        monitoring_repo=repos["monitoring_repo"],
        safety_repo=repos["safety_repo"],
        trace_repo=repos["trace_repo"],
        outbox_repo=repos["outbox_repo"],
    )


@pytest.fixture
def service(mock_repos):
    """Return a TreatmentPlanService with standard mocks."""
    return _make_service(mock_repos)


# ═══════════════════════════════════════════════════════════════════════════════
# Success Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestCreatePlanSuccess:
    """Happy path: full create_plan pipeline."""

    async def _call_create(self, service, mock_repos, request):
        """Call create_plan with all upstream loaders patched."""
        with (
            patch.object(service, "_load_recommendation", return_value=_make_recommendation_model()),
            patch.object(service, "_load_clinical_decision", return_value=_make_clinical_decision_model()),
            patch.object(service, "_load_consensus", return_value=_make_consensus_model()),
            patch.object(service, "_load_patient_data", return_value={"id": str(PATIENT_UUID), "display_name": "Test"}),
        ):
            return await service.create_plan(request, user_id=str(USER_UUID))

    async def test_full_success_flow(self, mock_repos):
        """Verify complete pipeline returns a valid TreatmentPlanResponse."""
        svc = _make_service(mock_repos)
        req = sample_request()
        result = await self._call_create(svc, mock_repos, req)

        assert isinstance(result, TreatmentPlanResponse)
        assert result.plan_id is not None
        assert result.version == 1
        assert result.plan_status == "draft"
        assert result.patient_id == str(PATIENT_UUID)
        assert result.is_current is True
        assert result.created_by == str(USER_UUID)
        # Engine output fields present
        assert len(result.phases) > 0
        assert len(result.items) > 0

        # Verify all repos called
        mock_repos["plan_repo"].create.assert_awaited_once()
        mock_repos["phase_repo"].create_many.assert_awaited_once()
        mock_repos["item_repo"].create_many.assert_awaited_once()
        mock_repos["monitoring_repo"].create_many.assert_awaited_once()
        mock_repos["safety_repo"].create_many.assert_awaited_once()
        mock_repos["trace_repo"].create_many.assert_awaited_once()
        mock_repos["outbox_repo"].create.assert_awaited_once()
        # Verify commit called
        mock_repos["db"].commit.assert_awaited_once()

    async def test_created_by_recorded(self, mock_repos):
        """Verify created_by is set to user_id."""
        svc = _make_service(mock_repos)
        req = sample_request()
        result = await self._call_create(svc, mock_repos, req)

        assert result.created_by == str(USER_UUID)

        # Verify the model passed to plan_repo.create had created_by set
        call_args = mock_repos["plan_repo"].create.await_args
        assert call_args is not None
        args = call_args.args
        model = args[0] if args else call_args.kwargs.get("model")
        assert model is not None
        assert str(model.created_by) == str(USER_UUID)


# ═══════════════════════════════════════════════════════════════════════════════
# Validation Error Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestValidationErrors:
    """P0 ID consistency validation — all 5 mismatch scenarios."""

    @staticmethod
    async def _call_with_models(service, rec, cd, cons) -> TreatmentPlanResponse:
        """Call create_plan with specific upstream models (mocked loaders)."""
        req = sample_request()
        with (
            patch.object(service, "_load_recommendation", return_value=rec),
            patch.object(service, "_load_clinical_decision", return_value=cd),
            patch.object(service, "_load_consensus", return_value=cons),
            patch.object(service, "_load_patient_data", return_value={"id": str(PATIENT_UUID)}),
        ):
            return await service.create_plan(req, user_id=str(USER_UUID))

    async def test_patient_mismatch_recommendation(self, mock_repos):
        """Recommendation.patient_id != request.patient_id → ValueError."""
        svc = _make_service(mock_repos)
        rec = _make_recommendation_model(patient_id=WRONG_UUID)
        cd = _make_clinical_decision_model()
        cons = _make_consensus_model()
        with pytest.raises(ValueError, match="belongs to patient"):
            await self._call_with_models(svc, rec, cd, cons)

    async def test_patient_mismatch_clinical_decision(self, mock_repos):
        """ClinicalDecision.patient_id != request.patient_id → ValueError."""
        svc = _make_service(mock_repos)
        rec = _make_recommendation_model()
        cd = _make_clinical_decision_model(patient_id=WRONG_UUID)
        cons = _make_consensus_model()
        with pytest.raises(ValueError, match="belongs to patient"):
            await self._call_with_models(svc, rec, cd, cons)

    async def test_patient_mismatch_consensus(self, mock_repos):
        """Consensus.patient_id != request.patient_id → ValueError."""
        svc = _make_service(mock_repos)
        rec = _make_recommendation_model()
        cd = _make_clinical_decision_model()
        cons = _make_consensus_model(patient_id=WRONG_UUID)
        with pytest.raises(ValueError, match="belongs to patient"):
            await self._call_with_models(svc, rec, cd, cons)

    async def test_recommendation_link_mismatch(self, mock_repos):
        """ClinicalDecision.recommendation_id (FK) != Recommendation.id → ValueError."""
        svc = _make_service(mock_repos)
        rec = _make_recommendation_model()
        cd = _make_clinical_decision_model(recommendation_fk=WRONG_UUID2)
        cons = _make_consensus_model()
        with pytest.raises(ValueError, match="link mismatch"):
            await self._call_with_models(svc, rec, cd, cons)

    async def test_clinical_decision_link_mismatch(self, mock_repos):
        """Consensus.clinical_decision_id (FK) != ClinicalDecision.id → ValueError."""
        svc = _make_service(mock_repos)
        rec = _make_recommendation_model()
        cd = _make_clinical_decision_model()
        cons = _make_consensus_model(clinical_decision_fk=WRONG_UUID2)
        with pytest.raises(ValueError, match="link mismatch"):
            await self._call_with_models(svc, rec, cd, cons)


# ═══════════════════════════════════════════════════════════════════════════════
# Transaction Rollback Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestTransactionRollback:
    """Verify rollback on persistence failures — each sub-repo failure tested."""

    @staticmethod
    async def _call(service, mock_repos):
        req = sample_request()
        with (
            patch.object(service, "_load_recommendation", return_value=_make_recommendation_model()),
            patch.object(service, "_load_clinical_decision", return_value=_make_clinical_decision_model()),
            patch.object(service, "_load_consensus", return_value=_make_consensus_model()),
            patch.object(service, "_load_patient_data", return_value={"id": str(PATIENT_UUID)}),
        ):
            return await service.create_plan(req, user_id=str(USER_UUID))

    async def test_rollback_on_plan_failure(self, mock_repos):
        """plan_repo.create raises → rollback."""
        mock_repos["plan_repo"].create.side_effect = Exception("DB error")
        svc = _make_service(mock_repos)
        with pytest.raises(RuntimeError, match="Failed to persist treatment plan"):
            await self._call(svc, mock_repos)
        mock_repos["db"].rollback.assert_awaited_once()

    async def test_rollback_on_phase_failure(self, mock_repos):
        """phase_repo.create_many raises → rollback."""
        mock_repos["phase_repo"].create_many.side_effect = Exception("Phase error")
        svc = _make_service(mock_repos)
        with pytest.raises(RuntimeError, match="Failed to persist treatment plan"):
            await self._call(svc, mock_repos)
        mock_repos["db"].rollback.assert_awaited_once()

    async def test_rollback_on_item_failure(self, mock_repos):
        """item_repo.create_many raises → rollback."""
        mock_repos["item_repo"].create_many.side_effect = Exception("Item error")
        svc = _make_service(mock_repos)
        with pytest.raises(RuntimeError, match="Failed to persist treatment plan"):
            await self._call(svc, mock_repos)
        mock_repos["db"].rollback.assert_awaited_once()

    async def test_rollback_on_trace_failure(self, mock_repos):
        """trace_repo.create_many raises → rollback."""
        mock_repos["trace_repo"].create_many.side_effect = Exception("Trace error")
        svc = _make_service(mock_repos)
        with pytest.raises(RuntimeError, match="Failed to persist treatment plan"):
            await self._call(svc, mock_repos)
        mock_repos["db"].rollback.assert_awaited_once()

    async def test_rollback_on_outbox_failure(self, mock_repos):
        """outbox_repo.create raises → rollback."""
        mock_repos["outbox_repo"].create.side_effect = Exception("Outbox error")
        svc = _make_service(mock_repos)
        with pytest.raises(RuntimeError, match="Failed to persist treatment plan"):
            await self._call(svc, mock_repos)
        mock_repos["db"].rollback.assert_awaited_once()


# ═══════════════════════════════════════════════════════════════════════════════
# Revision Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestRevision:
    """Plan versioning on revise_plan."""

    async def test_revision_creates_new_version(self, mock_repos):
        """revise_plan creates version 2 and marks version 1 as superseded."""
        svc = _make_service(mock_repos)
        req = sample_request()

        # plan_repo.get_by_plan_id returns current version
        current_model = _make_plan_model(plan_id="plan-001", version=1)
        mock_repos["plan_repo"].get_by_plan_id.return_value = current_model

        with (
            patch.object(svc, "_load_recommendation", return_value=_make_recommendation_model()),
            patch.object(svc, "_load_clinical_decision", return_value=_make_clinical_decision_model()),
            patch.object(svc, "_load_consensus", return_value=_make_consensus_model()),
            patch.object(svc, "_load_patient_data", return_value={"id": str(PATIENT_UUID)}),
        ):
            result = await svc.revise_plan("plan-001", req, user_id=str(USER_UUID))

        assert result.version == 2
        assert result.previous_plan_id == "plan-001"
        assert result.is_current is True

        # Verify old plan was marked superseded
        mock_repos["plan_repo"].mark_superseded.assert_awaited_once()

        # Verify outbox events: at least 2 (superseded + created)
        assert mock_repos["outbox_repo"].create.await_count >= 2

        # Verify commit called
        mock_repos["db"].commit.assert_awaited_once()


# ═══════════════════════════════════════════════════════════════════════════════
# Status Transition Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestStatusTransitions:
    """Status transitions via state machine."""

    @pytest.fixture(autouse=True)
    def _setup(self, mock_repos):
        self._svc = _make_service(mock_repos)
        self._repos = mock_repos
        # plan_repo.get_by_plan_id returns a draft plan
        self._plan_model = _make_plan_model(plan_id="plan-001", version=1, plan_status="draft")
        mock_repos["plan_repo"].get_by_plan_id.return_value = self._plan_model

    async def _call_transition(self, method_name: str, plan_id: str = "plan-001"):
        method = getattr(self._svc, method_name)
        return await method(plan_id, user_id=str(USER_UUID))

    async def test_submit_plan(self):
        """submit: draft → proposed."""
        result = await self._call_transition("submit_plan")
        assert result.plan_status == "proposed"

    async def test_approve_plan(self):
        """approve: under_review → approved."""
        self._plan_model.plan_status = "under_review"
        result = await self._call_transition("approve_plan")
        assert result.plan_status == "approved"
        assert result.approved_by == str(USER_UUID)

    async def test_activate_plan(self):
        """activate: approved → active."""
        self._plan_model.plan_status = "approved"
        result = await self._call_transition("activate_plan")
        assert result.plan_status == "active"

    async def test_pause_plan(self):
        """pause: active → paused."""
        self._plan_model.plan_status = "active"
        result = await self._call_transition("pause_plan")
        assert result.plan_status == "paused"

    async def test_complete_plan(self):
        """complete: active → completed."""
        self._plan_model.plan_status = "active"
        result = await self._call_transition("complete_plan")
        assert result.plan_status == "completed"

    async def test_cancel_plan(self):
        """cancel: draft → cancelled."""
        result = await self._call_transition("cancel_plan")
        assert result.plan_status == "cancelled"

    async def test_illegal_transition_raises_error(self):
        """active → draft is illegal (submit from active)."""
        self._plan_model.plan_status = "active"
        with pytest.raises(IllegalTransitionError):
            await self._call_transition("submit_plan")


# ═══════════════════════════════════════════════════════════════════════════════
# Query Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestQueries:
    """get_plan, list_plans, get_trace, get_versions."""

    @pytest.fixture(autouse=True)
    def _setup(self, mock_repos):
        self._svc = _make_service(mock_repos)
        self._repos = mock_repos

    async def test_get_plan_found(self):
        """get_plan returns a TreatmentPlanResponse when plan exists."""
        plan_model = _make_plan_model(plan_id="plan-001")
        self._repos["plan_repo"].get_by_plan_id.return_value = plan_model

        result = await self._svc.get_plan("plan-001")
        assert result is not None
        assert result.plan_id == "plan-001"
        assert result.version == 1

    async def test_get_plan_not_found(self):
        """get_plan returns None when plan does not exist."""
        self._repos["plan_repo"].get_by_plan_id.return_value = None
        result = await self._svc.get_plan("nonexistent")
        assert result is None

    async def test_list_plans(self):
        """list_plans returns plan list items."""
        plan_model = _make_plan_model(plan_id="plan-001")
        self._repos["plan_repo"].list_by_patient_id.return_value = [plan_model]

        results = await self._svc.list_plans(str(PATIENT_UUID))
        assert len(results) == 1
        assert results[0].plan_id == "plan-001"

    async def test_get_versions(self):
        """get_versions returns all versions."""
        v1 = _make_plan_model(plan_id="plan-001", version=1)
        v2 = _make_plan_model(plan_id="plan-001", version=2)
        self._repos["plan_repo"].list_versions.return_value = [v2, v1]

        results = await self._svc.get_versions("plan-001")
        assert len(results) == 2
        assert results[0].version == 2
        assert results[1].version == 1

    async def test_get_trace(self):
        """get_trace returns trace steps."""
        plan_model = _make_plan_model(plan_id="plan-001")
        self._repos["plan_repo"].get_by_plan_id.return_value = plan_model

        mock_step = MagicMock()
        mock_step.trace_id = "trace-001"
        mock_step.step_order = 0
        mock_step.step_type = "load_context"
        mock_step.input_summary = {}
        mock_step.output_summary = {"status": "loaded"}
        mock_step.rule_ids = []
        mock_step.evidence_ids = []
        mock_step.created_at = datetime.now(timezone.utc)

        self._repos["trace_repo"].list_by_plan_id.return_value = [mock_step]

        traces = await self._svc.get_trace("plan-001")
        assert len(traces) == 1
        assert traces[0]["step_type"] == "load_context"


# ═══════════════════════════════════════════════════════════════════════════════
# Engine Failure Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestEngineFailures:
    """Verify engine errors propagate correctly."""

    @staticmethod
    async def _call(service):
        req = sample_request()
        with (
            patch.object(service, "_load_recommendation", return_value=_make_recommendation_model()),
            patch.object(service, "_load_clinical_decision", return_value=_make_clinical_decision_model()),
            patch.object(service, "_load_consensus", return_value=_make_consensus_model()),
            patch.object(service, "_load_patient_data", return_value={"id": str(PATIENT_UUID)}),
        ):
            return await service.create_plan(req, user_id=str(USER_UUID))

    async def test_engine_value_error_propagates(self, mock_repos):
        """Engine ValueError propagates directly (not wrapped)."""
        mock_repos["engine"].generate.side_effect = ValueError("Engine validation failed")
        svc = _make_service(mock_repos)
        with pytest.raises(ValueError, match="Engine validation failed"):
            await self._call(svc)

    async def test_engine_runtime_error_wrapped(self, mock_repos):
        """Engine unexpected exception is wrapped in RuntimeError."""
        mock_repos["engine"].generate.side_effect = Exception("Internal engine crash")
        svc = _make_service(mock_repos)
        with pytest.raises(RuntimeError, match="internal error"):
            await self._call(svc)
