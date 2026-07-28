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
)
from src.backend.domain.treatment_plan import TreatmentPlanModel
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
                "phase_type": "primary_treatment",
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

        # plan_repo.get_current_by_plan_id returns current version
        current_model = _make_plan_model(plan_id="plan-001", version=1, plan_status="approved")
        mock_repos["plan_repo"].get_current_by_plan_id.return_value = current_model

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

    async def test_revise_plan_uses_current_version(self, mock_repos):
        """revise_plan loads the current version via get_current_by_plan_id."""
        svc = _make_service(mock_repos)
        req = sample_request()

        current_model = _make_plan_model(plan_id="plan-001", version=1, plan_status="approved")
        mock_repos["plan_repo"].get_current_by_plan_id.return_value = current_model

        with (
            patch.object(svc, "_load_recommendation", return_value=_make_recommendation_model()),
            patch.object(svc, "_load_clinical_decision", return_value=_make_clinical_decision_model()),
            patch.object(svc, "_load_consensus", return_value=_make_consensus_model()),
            patch.object(svc, "_load_patient_data", return_value={"id": str(PATIENT_UUID)}),
        ):
            result = await svc.revise_plan("plan-001", req, user_id=str(USER_UUID))

        # Verify it used get_current_by_plan_id to load the current version
        mock_repos["plan_repo"].get_current_by_plan_id.assert_awaited_once_with("plan-001")
        assert result.version == 2

    # ── H-03: Version Chain ─────────────────────────────────────────────────

    async def test_version_chain(self, mock_repos):
        """Version chain: create v1 → revise v2 → revise v3 → get_versions returns 3."""
        svc = _make_service(mock_repos)
        req = sample_request()

        # ── Step 1: Create v1 ───────────────────────────────────────────
        with (
            patch.object(svc, "_load_recommendation", return_value=_make_recommendation_model()),
            patch.object(svc, "_load_clinical_decision", return_value=_make_clinical_decision_model()),
            patch.object(svc, "_load_consensus", return_value=_make_consensus_model()),
            patch.object(svc, "_load_patient_data", return_value={"id": str(PATIENT_UUID), "display_name": "Test"}),
        ):
            v1 = await svc.create_plan(req, user_id=str(USER_UUID))

        plan_id = v1.plan_id
        assert v1.version == 1

        # ── Step 2: Revise to v2 ────────────────────────────────────────
        v1_model = _make_plan_model(plan_id=plan_id, version=1, plan_status="approved")
        mock_repos["plan_repo"].get_current_by_plan_id.return_value = v1_model

        with (
            patch.object(svc, "_load_recommendation", return_value=_make_recommendation_model()),
            patch.object(svc, "_load_clinical_decision", return_value=_make_clinical_decision_model()),
            patch.object(svc, "_load_consensus", return_value=_make_consensus_model()),
            patch.object(svc, "_load_patient_data", return_value={"id": str(PATIENT_UUID), "display_name": "Test"}),
        ):
            v2 = await svc.revise_plan(plan_id, req, user_id=str(USER_UUID))

        assert v2.plan_id == plan_id
        assert v2.version == 2

        # ── Step 3: Revise to v3 ────────────────────────────────────────
        v2_model = _make_plan_model(plan_id=plan_id, version=2, plan_status="approved")
        mock_repos["plan_repo"].get_current_by_plan_id.return_value = v2_model

        with (
            patch.object(svc, "_load_recommendation", return_value=_make_recommendation_model()),
            patch.object(svc, "_load_clinical_decision", return_value=_make_clinical_decision_model()),
            patch.object(svc, "_load_consensus", return_value=_make_consensus_model()),
            patch.object(svc, "_load_patient_data", return_value={"id": str(PATIENT_UUID), "display_name": "Test"}),
        ):
            v3 = await svc.revise_plan(plan_id, req, user_id=str(USER_UUID))

        assert v3.plan_id == plan_id
        assert v3.version == 3

        # ── Step 4: get_versions returns all three ──────────────────────
        v1_ver = _make_plan_model(plan_id=plan_id, version=1)
        v2_ver = _make_plan_model(plan_id=plan_id, version=2)
        v3_ver = _make_plan_model(plan_id=plan_id, version=3)
        mock_repos["plan_repo"].list_versions.return_value = [v3_ver, v2_ver, v1_ver]

        results = await svc.get_versions(plan_id)
        assert len(results) == 3
        assert results[0].version == 3
        assert results[1].version == 2
        assert results[2].version == 1
        for r in results:
            assert r.plan_id == plan_id

    # ── H-14: Revision Policy ──────────────────────────────────────────────

    async def test_revision_allowed_for_approved(self, mock_repos):
        """Revision succeeds for approved plans."""
        svc = _make_service(mock_repos)
        req = sample_request()
        plan_model = _make_plan_model(plan_id="plan-rp-001", version=1, plan_status="approved")
        mock_repos["plan_repo"].get_current_by_plan_id.return_value = plan_model

        with (
            patch.object(svc, "_load_recommendation", return_value=_make_recommendation_model()),
            patch.object(svc, "_load_clinical_decision", return_value=_make_clinical_decision_model()),
            patch.object(svc, "_load_consensus", return_value=_make_consensus_model()),
            patch.object(svc, "_load_patient_data", return_value={"id": str(PATIENT_UUID)}),
        ):
            result = await svc.revise_plan("plan-rp-001", req, user_id=str(USER_UUID))

        assert result.version == 2
        mock_repos["db"].commit.assert_awaited_once()

    async def test_revision_allowed_for_active(self, mock_repos):
        """Revision succeeds for active plans."""
        svc = _make_service(mock_repos)
        req = sample_request()
        plan_model = _make_plan_model(plan_id="plan-rp-002", version=1, plan_status="active")
        mock_repos["plan_repo"].get_current_by_plan_id.return_value = plan_model

        with (
            patch.object(svc, "_load_recommendation", return_value=_make_recommendation_model()),
            patch.object(svc, "_load_clinical_decision", return_value=_make_clinical_decision_model()),
            patch.object(svc, "_load_consensus", return_value=_make_consensus_model()),
            patch.object(svc, "_load_patient_data", return_value={"id": str(PATIENT_UUID)}),
        ):
            result = await svc.revise_plan("plan-rp-002", req, user_id=str(USER_UUID))

        assert result.version == 2
        mock_repos["db"].commit.assert_awaited_once()

    async def test_revision_allowed_for_paused(self, mock_repos):
        """Revision succeeds for paused plans."""
        svc = _make_service(mock_repos)
        req = sample_request()
        plan_model = _make_plan_model(plan_id="plan-rp-003", version=1, plan_status="paused")
        mock_repos["plan_repo"].get_current_by_plan_id.return_value = plan_model

        with (
            patch.object(svc, "_load_recommendation", return_value=_make_recommendation_model()),
            patch.object(svc, "_load_clinical_decision", return_value=_make_clinical_decision_model()),
            patch.object(svc, "_load_consensus", return_value=_make_consensus_model()),
            patch.object(svc, "_load_patient_data", return_value={"id": str(PATIENT_UUID)}),
        ):
            result = await svc.revise_plan("plan-rp-003", req, user_id=str(USER_UUID))

        assert result.version == 2
        mock_repos["db"].commit.assert_awaited_once()

    async def test_revision_denied_for_draft(self, mock_repos):
        """Revision denied for draft plans — raises IllegalTransitionError."""
        svc = _make_service(mock_repos)
        req = sample_request()
        plan_model = _make_plan_model(plan_id="plan-rp-004", version=1, plan_status="draft")
        mock_repos["plan_repo"].get_current_by_plan_id.return_value = plan_model

        with (
            patch.object(svc, "_load_recommendation", return_value=_make_recommendation_model()),
            patch.object(svc, "_load_clinical_decision", return_value=_make_clinical_decision_model()),
            patch.object(svc, "_load_consensus", return_value=_make_consensus_model()),
            patch.object(svc, "_load_patient_data", return_value={"id": str(PATIENT_UUID)}),
        ):
            with pytest.raises(IllegalTransitionError):
                await svc.revise_plan("plan-rp-004", req, user_id=str(USER_UUID))

        mock_repos["db"].commit.assert_not_awaited()

    async def test_revision_denied_for_cancelled(self, mock_repos):
        """Revision denied for cancelled plans — raises IllegalTransitionError."""
        svc = _make_service(mock_repos)
        req = sample_request()
        plan_model = _make_plan_model(plan_id="plan-rp-005", version=1, plan_status="cancelled")
        mock_repos["plan_repo"].get_current_by_plan_id.return_value = plan_model

        with (
            patch.object(svc, "_load_recommendation", return_value=_make_recommendation_model()),
            patch.object(svc, "_load_clinical_decision", return_value=_make_clinical_decision_model()),
            patch.object(svc, "_load_consensus", return_value=_make_consensus_model()),
            patch.object(svc, "_load_patient_data", return_value={"id": str(PATIENT_UUID)}),
        ):
            with pytest.raises(IllegalTransitionError):
                await svc.revise_plan("plan-rp-005", req, user_id=str(USER_UUID))

    async def test_revision_denied_for_completed(self, mock_repos):
        """Revision denied for completed plans — raises IllegalTransitionError."""
        svc = _make_service(mock_repos)
        req = sample_request()
        plan_model = _make_plan_model(plan_id="plan-rp-006", version=1, plan_status="completed")
        mock_repos["plan_repo"].get_current_by_plan_id.return_value = plan_model

        with (
            patch.object(svc, "_load_recommendation", return_value=_make_recommendation_model()),
            patch.object(svc, "_load_clinical_decision", return_value=_make_clinical_decision_model()),
            patch.object(svc, "_load_consensus", return_value=_make_consensus_model()),
            patch.object(svc, "_load_patient_data", return_value={"id": str(PATIENT_UUID)}),
        ):
            with pytest.raises(IllegalTransitionError):
                await svc.revise_plan("plan-rp-006", req, user_id=str(USER_UUID))

    async def test_revision_denied_for_superseded(self, mock_repos):
        """Revision denied for superseded plans — raises IllegalTransitionError."""
        svc = _make_service(mock_repos)
        req = sample_request()
        plan_model = _make_plan_model(plan_id="plan-rp-007", version=1, plan_status="superseded")
        mock_repos["plan_repo"].get_current_by_plan_id.return_value = plan_model

        with (
            patch.object(svc, "_load_recommendation", return_value=_make_recommendation_model()),
            patch.object(svc, "_load_clinical_decision", return_value=_make_clinical_decision_model()),
            patch.object(svc, "_load_consensus", return_value=_make_consensus_model()),
            patch.object(svc, "_load_patient_data", return_value={"id": str(PATIENT_UUID)}),
        ):
            with pytest.raises(IllegalTransitionError):
                await svc.revise_plan("plan-rp-007", req, user_id=str(USER_UUID))


# ═══════════════════════════════════════════════════════════════════════════════
# Phase Mapping Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestPhaseMapping:
    """Verify items are mapped to the correct phase (H-12)."""

    async def test_items_mapped_to_correct_phase(self, mock_repos):
        """Each item's phase_id should point to its matching phase, not all to first."""
        svc = _make_service(mock_repos)
        req = sample_request()

        # Override engine output with 3 phases and items that reference different phases
        custom_output = _make_engine_output({
            "phases": [
                {"phase_type": "preparation", "name": "Preparation", "order": 1, "duration_days": 14},
                {"phase_type": "primary_treatment", "name": "Primary Treatment", "order": 2, "duration_days": 90},
                {"phase_type": "maintenance", "name": "Maintenance", "order": 3, "duration_days": 180},
            ],
            "items": [
                {
                    "item_type": "medication",
                    "name": "Drug A",
                    "description": "Preparation drug",
                    "priority": 1,
                    "rationale": "Part of preparation",
                    "source_recommendation": "engine",
                    "phase_type": "preparation",
                },
                {
                    "item_type": "medication",
                    "name": "Drug B",
                    "description": "Primary drug",
                    "priority": 2,
                    "rationale": "Part of primary treatment",
                    "source_recommendation": "engine",
                    "phase_type": "primary_treatment",
                },
                {
                    "item_type": "radiation",
                    "name": "Radiation C",
                    "description": "Maintenance radiation",
                    "priority": 3,
                    "rationale": "Part of maintenance",
                    "source_recommendation": "engine",
                    "phase_type": "maintenance",
                },
            ],
        })
        mock_repos["engine"].generate.return_value = custom_output

        with (
            patch.object(svc, "_load_recommendation", return_value=_make_recommendation_model()),
            patch.object(svc, "_load_clinical_decision", return_value=_make_clinical_decision_model()),
            patch.object(svc, "_load_consensus", return_value=_make_consensus_model()),
            patch.object(svc, "_load_patient_data", return_value={"id": str(PATIENT_UUID), "display_name": "Test"}),
        ):
            await svc.create_plan(req, user_id=str(USER_UUID))

        # Inspect phase models passed to create_many
        phase_call = mock_repos["phase_repo"].create_many.await_args
        assert phase_call is not None
        phase_models = phase_call.args[0] if phase_call.args else phase_call.kwargs.get("models")
        assert phase_models is not None
        assert len(phase_models) == 3
        phase_map = {p.phase_type: p.id for p in phase_models}

        # Inspect item models passed to create_many
        item_call = mock_repos["item_repo"].create_many.await_args
        assert item_call is not None
        item_models = item_call.args[0] if item_call.args else item_call.kwargs.get("models")
        assert item_models is not None
        assert len(item_models) == 3

        # Verify each item's phase_id matches its designated phase
        assert item_models[0].phase_id == phase_map["preparation"]
        assert item_models[1].phase_id == phase_map["primary_treatment"]
        assert item_models[2].phase_id == phase_map["maintenance"]

        # Verify they are NOT all pointing to the same phase
        assert item_models[0].phase_id != item_models[1].phase_id
        assert item_models[0].phase_id != item_models[2].phase_id
        assert item_models[1].phase_id != item_models[2].phase_id

    async def test_persist_item_phase_mapping_success(self, mock_repos):
        """Items with valid phase_type should be correctly mapped to matching phases."""
        svc = _make_service(mock_repos)
        req = sample_request()

        custom_output = _make_engine_output({
            "phases": [
                {"phase_type": "preparation", "name": "Preparation", "order": 1, "duration_days": 14},
                {"phase_type": "primary_treatment", "name": "Primary Treatment", "order": 2, "duration_days": 90},
                {"phase_type": "maintenance", "name": "Maintenance", "order": 3, "duration_days": 180},
            ],
            "items": [
                {
                    "item_type": "medication",
                    "name": "Drug A",
                    "description": "Preparation drug",
                    "priority": 1,
                    "rationale": "Part of preparation",
                    "source_recommendation": "engine",
                    "phase_type": "preparation",
                },
                {
                    "item_type": "medication",
                    "name": "Drug B",
                    "description": "Primary drug",
                    "priority": 2,
                    "rationale": "Part of primary treatment",
                    "source_recommendation": "engine",
                    "phase_type": "primary_treatment",
                },
                {
                    "item_type": "radiation",
                    "name": "Radiation C",
                    "description": "Maintenance radiation",
                    "priority": 3,
                    "rationale": "Part of maintenance",
                    "source_recommendation": "engine",
                    "phase_type": "maintenance",
                },
            ],
        })
        mock_repos["engine"].generate.return_value = custom_output

        with (
            patch.object(svc, "_load_recommendation", return_value=_make_recommendation_model()),
            patch.object(svc, "_load_clinical_decision", return_value=_make_clinical_decision_model()),
            patch.object(svc, "_load_consensus", return_value=_make_consensus_model()),
            patch.object(svc, "_load_patient_data", return_value={"id": str(PATIENT_UUID), "display_name": "Test"}),
        ):
            await svc.create_plan(req, user_id=str(USER_UUID))

        phase_call = mock_repos["phase_repo"].create_many.await_args
        assert phase_call is not None
        phase_models = phase_call.args[0] if phase_call.args else phase_call.kwargs.get("models")
        assert phase_models is not None
        assert len(phase_models) == 3
        phase_map = {p.phase_type: p.id for p in phase_models}

        item_call = mock_repos["item_repo"].create_many.await_args
        assert item_call is not None
        item_models = item_call.args[0] if item_call.args else item_call.kwargs.get("models")
        assert item_models is not None
        assert len(item_models) == 3

        assert item_models[0].phase_id == phase_map["preparation"]
        assert item_models[1].phase_id == phase_map["primary_treatment"]
        assert item_models[2].phase_id == phase_map["maintenance"]

    async def test_persist_item_phase_mapping_not_found_raises_value_error(self, mock_repos):
        """Item with phase_type that doesn't match any defined phase should raise ValueError."""
        svc = _make_service(mock_repos)
        req = sample_request()

        custom_output = _make_engine_output({
            "phases": [
                {"phase_type": "primary_treatment", "name": "Primary Treatment", "order": 1, "duration_days": 90},
            ],
            "items": [
                {
                    "item_type": "medication",
                    "name": "Mystery Drug",
                    "description": "Unknown phase",
                    "priority": 1,
                    "rationale": "Test",
                    "source_recommendation": "engine",
                    "phase_type": "nonexistent_phase",
                },
            ],
        })
        mock_repos["engine"].generate.return_value = custom_output

        with (
            patch.object(svc, "_load_recommendation", return_value=_make_recommendation_model()),
            patch.object(svc, "_load_clinical_decision", return_value=_make_clinical_decision_model()),
            patch.object(svc, "_load_consensus", return_value=_make_consensus_model()),
            patch.object(svc, "_load_patient_data", return_value={"id": str(PATIENT_UUID), "display_name": "Test"}),
            pytest.raises(ValueError, match="does not match any defined phase"),
        ):
            await svc.create_plan(req, user_id=str(USER_UUID))

    async def test_no_fallback_to_first_phase(self, mock_repos):
        """Items missing phase_type should raise ValueError, not fall back to first phase."""
        svc = _make_service(mock_repos)
        req = sample_request()

        # Item without phase_type — should raise, not fallback
        custom_output = _make_engine_output({
            "phases": [
                {"phase_type": "primary_treatment", "name": "Primary Treatment", "order": 1, "duration_days": 90},
            ],
            "items": [
                {
                    "item_type": "medication",
                    "name": "No Phase Drug",
                    "description": "Missing phase_type",
                    "priority": 1,
                    "rationale": "Test",
                    "source_recommendation": "engine",
                    # phase_type intentionally omitted
                },
            ],
        })
        mock_repos["engine"].generate.return_value = custom_output

        with (
            patch.object(svc, "_load_recommendation", return_value=_make_recommendation_model()),
            patch.object(svc, "_load_clinical_decision", return_value=_make_clinical_decision_model()),
            patch.object(svc, "_load_consensus", return_value=_make_consensus_model()),
            patch.object(svc, "_load_patient_data", return_value={"id": str(PATIENT_UUID), "display_name": "Test"}),
            pytest.raises(ValueError, match="missing required 'phase_type'"),
        ):
            await svc.create_plan(req, user_id=str(USER_UUID))


# ═══════════════════════════════════════════════════════════════════════════════
# Status Transition Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestStatusTransitions:
    """Status transitions via state machine."""

    @pytest.fixture(autouse=True)
    def _setup(self, mock_repos):
        self._svc = _make_service(mock_repos)
        self._repos = mock_repos
        # plan_repo.get_current_by_plan_id returns a draft plan
        self._plan_model = _make_plan_model(plan_id="plan-001", version=1, plan_status="draft")
        mock_repos["plan_repo"].get_current_by_plan_id.return_value = self._plan_model

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

    async def test_status_transition_uses_current_version(self):
        """Status transitions load the current version via get_current_by_plan_id."""
        self._plan_model.plan_status = "active"
        result = await self._call_transition("complete_plan")
        assert result.plan_status == "completed"
        # Verify it loaded the current version
        self._repos["plan_repo"].get_current_by_plan_id.assert_awaited_with("plan-001")


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
        self._repos["plan_repo"].get_current_by_plan_id.return_value = plan_model

        result = await self._svc.get_plan("plan-001")
        assert result is not None
        assert result.plan_id == "plan-001"
        assert result.version == 1

    async def test_get_plan_returns_current_version(self):
        """get_plan always returns the current (latest) version."""
        # Mock returns a version-2 model (current)
        plan_model = _make_plan_model(plan_id="plan-001", version=2, is_current=True)
        self._repos["plan_repo"].get_current_by_plan_id.return_value = plan_model

        result = await self._svc.get_plan("plan-001")
        assert result is not None
        assert result.version == 2
        assert result.is_current is True
        # Verify the mock was called correctly
        self._repos["plan_repo"].get_current_by_plan_id.assert_awaited_once_with("plan-001")

    async def test_get_plan_not_found(self):
        """get_plan returns None when plan does not exist."""
        self._repos["plan_repo"].get_current_by_plan_id.return_value = None
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

    async def test_list_versions_returns_all(self):
        """get_versions returns all versions for a plan_id."""
        v1 = _make_plan_model(plan_id="plan-chain", version=1)
        v2 = _make_plan_model(plan_id="plan-chain", version=2)
        v3 = _make_plan_model(plan_id="plan-chain", version=3)
        self._repos["plan_repo"].list_versions.return_value = [v3, v2, v1]

        results = await self._svc.get_versions("plan-chain")
        assert len(results) == 3
        assert results[0].version == 3
        assert results[1].version == 2
        assert results[2].version == 1
        for r in results:
            assert r.plan_id == "plan-chain"

    async def test_get_trace(self):
        """get_trace returns trace steps."""
        plan_model = _make_plan_model(plan_id="plan-001")
        self._repos["plan_repo"].get_current_by_plan_id.return_value = plan_model

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

    async def test_get_plan_version_found(self):
        """get_plan_version returns a specific version."""
        plan_model = _make_plan_model(plan_id="plan-001", version=3)
        self._repos["plan_repo"].get_plan_version.return_value = plan_model

        result = await self._svc.get_plan_version("plan-001", 3)
        assert result is not None
        assert result.plan_id == "plan-001"
        assert result.version == 3
        self._repos["plan_repo"].get_plan_version.assert_awaited_once_with("plan-001", 3)

    async def test_get_plan_version_not_found(self):
        """get_plan_version returns None when version does not exist."""
        self._repos["plan_repo"].get_plan_version.return_value = None

        result = await self._svc.get_plan_version("plan-001", 99)
        assert result is None


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
