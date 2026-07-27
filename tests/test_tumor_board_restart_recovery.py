"""
Restart Recovery Test for Tumor Board Consensus (Phase 3C).

Verifies that tumor board consensus data survives a full application restart
using file-based SQLite and the complete API/App stack (TestClient + create_app()).

Phases:
1. App 1: POST a consensus → GET to confirm
2. Shutdown App 1 (engine disposed via lifespan)
3. App 2: GET the same consensus → confirm data integrity
"""

from __future__ import annotations

import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.backend.auth.dependencies import require_auth
from src.backend.domain.clinical_decision import ClinicalDecisionModel
from src.backend.domain.enums import ConsentStatusEnum, Role, SexEnum
from src.backend.domain.patient import PatientModel
from src.backend.domain.recommendation import RecommendationModel
from src.backend.domain.user import UserModel

# ── Helpers ──────────────────────────────────────────────────────────────

def _make_fake_user() -> UserModel:
    """Create a fake UserModel for dependency override of require_auth."""
    return UserModel(
        id=uuid.uuid4(),
        username="tb-restart-test-user",
        email="tb-restart-test@example.com",
        password_hash="fake-bcrypt-hash",
        role=Role.VIEWER,
        is_active=True,
        display_name="TB Restart Test User",
    )


# ── Fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture
def db_url() -> str:
    """Detect DATABASE_URL env var; if CI + Postgres use it directly, else use temp SQLite.

    Yields the database URL string.
    """
    env_url = os.environ.get("DATABASE_URL", "")
    is_ci = os.environ.get("CI", "").lower() in ("true", "1") or os.environ.get(
        "GITHUB_ACTIONS", ""
    ).lower() == "true"

    if env_url.startswith("postgresql") and is_ci:
        import src.backend.config as _config

        original_url = _config.settings.DATABASE_URL
        _config.settings.DATABASE_URL = env_url
        yield env_url
        _config.settings.DATABASE_URL = original_url
        return

    # Fallback: file-based SQLite
    import src.backend.config as _config

    original_url = _config.settings.DATABASE_URL
    file_path = os.path.join(
        os.path.dirname(__file__),
        f"test_tb_restart_{uuid.uuid4().hex}.db",
    )
    url = f"sqlite+aiosqlite:///{file_path}"
    _config.settings.DATABASE_URL = url
    yield url
    # Restore original URL
    _config.settings.DATABASE_URL = original_url
    # Clean up the temp DB file
    if os.path.exists(file_path):
        os.unlink(file_path)


# ── Tests ────────────────────────────────────────────────────────────────


class TestTumorBoardRestartRecovery:
    """E2E restart recovery for tumor board consensus via the full API stack."""

    BASE = "/api/v1/tumor-board-consensus"

    def _create_app_with_auth_override(self):
        """Create a test app with require_auth overridden to bypass real auth."""
        from src.backend.main import create_app

        app = create_app()
        # Override require_auth to return a fake user
        app.dependency_overrides[require_auth] = _make_fake_user
        return app

    def _create_patient(self, client: TestClient) -> str:
        """Create a patient via API and return its UUID string."""
        from datetime import datetime

        resp = client.post(
            "/api/v1/patients",
            json={
                "display_name": "TB-Restart-Patient",
                "sex": "F",
                "consent_status": "granted",
                "date_of_birth": "1980-01-01",
                "created_at": datetime.utcnow().isoformat(),
            },
        )
        assert resp.status_code in (200, 201), f"Patient creation failed: {resp.text}"
        return resp.json()["id"]

    def _create_recommendation(self, client: TestClient, patient_id: str) -> str:
        """Create a recommendation via API and return its recommendation_id."""
        resp = client.post(
            "/api/v1/recommendation",
            json={
                "patient_id": patient_id,
                "variants": ["EGFR L858R"],
            },
        )
        assert resp.status_code in (
            200, 201,
        ), f"Recommendation creation failed: {resp.text}"
        data = resp.json()
        # Return recommendation_id (business key)
        return data.get("recommendation_id") or data.get("id", "")

    def _create_clinical_decision(
        self, client: TestClient, patient_id: str, recommendation_id: str,
    ) -> str:
        """Create a clinical decision via API and return its decision_id."""
        resp = client.post(
            "/api/v1/clinical-decision",
            json={
                "patient_id": patient_id,
                "recommendation_id": recommendation_id,
                "variants": ["EGFR L858R"],
            },
        )
        assert resp.status_code in (
            200, 201,
        ), f"Clinical decision creation failed: {resp.text}"
        return resp.json()["decision_id"]

    def _create_consensus(
        self,
        client: TestClient,
        patient_id: str,
        recommendation_id: str,
        clinical_decision_id: str,
    ) -> str:
        """Create a tumor board consensus via API and return its consensus_id."""
        resp = client.post(
            self.BASE,
            json={
                "patient_id": patient_id,
                "recommendation_id": recommendation_id,
                "clinical_decision_id": clinical_decision_id,
                "specialist_opinions": [
                    {
                        "specialty": "medical_oncology",
                        "position": "support",
                        "confidence": 0.95,
                    },
                    {
                        "specialty": "surgical_oncology",
                        "position": "support",
                        "confidence": 0.90,
                    },
                ],
            },
        )
        assert resp.status_code in (
            200, 201,
        ), f"Consensus creation failed: {resp.text}"
        return resp.json()["consensus_id"]

    def _create_prerequisite_data(self, db_url: str) -> dict[str, str]:
        """Write patient, recommendation, and clinical_decision directly to DB.

        Uses a synchronous SQLAlchemy connection for both SQLite and Postgres,
        bypassing the Engine (which requires external evidence API keys).

        Manual engine disposal ensures connections are released before
        the async engine takes over.

        Returns dict with ``patient_id``, ``recommendation_id``,
        ``clinical_decision_id`` (business identifiers).
        """
        import uuid
        from datetime import datetime

        # Convert async URL to sync URL
        sync_url = (
            db_url
            .replace("sqlite+aiosqlite:///", "sqlite:///")
            .replace("postgresql+asyncpg://", "postgresql+psycopg2://")
        )
        engine = create_engine(sync_url)

        with Session(engine) as session:
            patient_id = uuid.uuid4()
            patient = PatientModel(
                id=patient_id,
                display_name="TB-Restart-Patient",
                sex=SexEnum.F,
                consent_status=ConsentStatusEnum.GRANTED,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            session.add(patient)

            rec_biz_id = uuid.uuid4().hex
            recommendation = RecommendationModel(
                id=uuid.uuid4(),
                recommendation_id=rec_biz_id,
                patient_id=patient_id,
                engine_version="1.0.0",
                status="completed",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            session.add(recommendation)
            session.flush()  # ensure recommendation.id is populated

            cd_biz_id = uuid.uuid4().hex
            clinical_decision = ClinicalDecisionModel(
                id=uuid.uuid4(),
                decision_id=cd_biz_id,
                patient_id=patient_id,
                recommendation_id=recommendation.id,
                decision_type="treatment",
                reason="Test reason for restart recovery test",
                confidence="high",
                status="active",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            session.add(clinical_decision)

            session.commit()
        engine.dispose()

        return {
            "patient_id": str(patient_id),
            "recommendation_id": rec_biz_id,
            "clinical_decision_id": cd_biz_id,
        }

    def test_end_to_end_restart_recovery(self, db_url: str) -> None:
        """
        Full restart-recovery scenario:

        Phase 1 — App 1
            (DB direct write: patient → recommendation → clinical decision)
            → POST tumor board consensus → GET to confirm
        Phase 2 — Shutdown (session scope closes)
        Phase 3 — App 2 (new TestClient, new app instance)
            GET the same consensus → verify data integrity
            GET opinions → verify opinions exist
            GET trace → verify trace exists
        """
        # ═════════════════════════════════════════════════════════════════
        # Phase 1 — App 1: Create data
        # ═════════════════════════════════════════════════════════════════
        app1 = self._create_app_with_auth_override()
        with TestClient(app1) as client1:
            # ── Write prerequisite data directly to DB (bypass Engine) ──
            prereq = self._create_prerequisite_data(db_url)
            patient_id = prereq["patient_id"]
            rec_id = prereq["recommendation_id"]
            cd_id = prereq["clinical_decision_id"]

            # Create the tumor board consensus
            consensus_id = self._create_consensus(
                client1, patient_id, rec_id, cd_id,
            )
            assert consensus_id, "consensus_id should not be empty"

            # GET the consensus to verify it was created
            get_resp = client1.get(
                f"{self.BASE}/{consensus_id}",
            )
            assert get_resp.status_code == 200, (
                f"App 1 GET failed: {get_resp.status_code} {get_resp.text}"
            )
            response_data = get_resp.json()
            assert response_data["consensus_id"] == consensus_id
            assert response_data["consensus_status"] is not None
            assert response_data["patient_id"] == patient_id

        # App 1 closes here — session, engine disposed

        # ═════════════════════════════════════════════════════════════════
        # Phase 2 — Shutdown (automatic via context manager exit)
        # ═════════════════════════════════════════════════════════════════

        # ═════════════════════════════════════════════════════════════════
        # Phase 3 — App 2: Verify data survives
        # ═════════════════════════════════════════════════════════════════
        app2 = self._create_app_with_auth_override()
        with TestClient(app2) as client2:
            # GET the same consensus
            get_resp2 = client2.get(
                f"{self.BASE}/{consensus_id}",
            )
            assert get_resp2.status_code == 200, (
                f"App 2 GET failed: {get_resp2.status_code} {get_resp2.text}"
            )
            data2 = get_resp2.json()
            assert data2["consensus_id"] == consensus_id
            assert data2["consensus_status"] in (
                "unanimous", "strong_consensus", "majority_consensus",
                "split_decision", "insufficient_information", "deferred",
            ), f"Unexpected consensus_status: {data2['consensus_status']}"
            assert data2["patient_id"] == patient_id
            # Verify recommendation_id and clinical_decision_id are non-empty
            assert data2["recommendation_id"], "recommendation_id should be present"
            assert data2["clinical_decision_id"], "clinical_decision_id should be present"

            # GET opinions
            opinions_resp = client2.get(
                f"{self.BASE}/{consensus_id}/opinions",
            )
            assert opinions_resp.status_code == 200
            opinions = opinions_resp.json()
            assert len(opinions) >= 1, "Should have at least one opinion"
            # Verify the opinions have expected structure
            for opinion in opinions:
                assert "specialty" in opinion
                assert "position" in opinion
                assert "confidence" in opinion

            # GET trace
            trace_resp = client2.get(
                f"{self.BASE}/{consensus_id}/trace",
            )
            assert trace_resp.status_code == 200
            trace = trace_resp.json()
            assert len(trace) >= 1, "Should have at least one trace step"
            # Verify trace has expected structure
            for step in trace:
                assert "step_type" in step
                assert "step_order" in step
