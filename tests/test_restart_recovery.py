"""
Restart Recovery Test — End-to-End (Batch E, P0-2).

Verifies that recommendation data survives a full application restart using
file-based SQLite and the complete API/App stack (TestClient + create_app()).

Phases:
1. App 1: POST a patient → POST a recommendation → GET to confirm
2. Shutdown App 1 (engine disposed via lifespan)
3. App 2: GET the same recommendation → confirm data integrity

Constraints (enforced by code review):
- Uses TestClient + create_app() for the full API path
- No direct session.add / Repository.get calls
- File-based SQLite so data survives across app instances
"""

from __future__ import annotations

import os
import uuid

import pytest
from fastapi.testclient import TestClient

from src.backend.auth.dependencies import require_auth
from src.backend.domain.enums import Role
from src.backend.domain.user import UserModel

# ── Helpers ──────────────────────────────────────────────────────────────

def _make_fake_user() -> UserModel:
    """Create a fake UserModel for dependency override of require_auth.

    Must be a callable (fresh instance) because SQLAlchemy models are
    scoped to a session.  Each test phase gets its own user object.
    """
    return UserModel(
        id=uuid.uuid4(),
        username="restart-test-user",
        email="restart-test@example.com",
        password_hash="fake-bcrypt-hash",
        role=Role.VIEWER,
        is_active=True,
        display_name="Restart Test User",
    )


# ── Fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture
def db_url() -> str:
    """Detect DATABASE_URL env var; if CI + Postgres use it directly, else use temp SQLite.

    Yields the database URL string.
    """
    env_url = os.environ.get("DATABASE_URL", "")
    is_ci = os.environ.get("CI", "").lower() in ("true", "1") or os.environ.get("GITHUB_ACTIONS", "").lower() == "true"

    if env_url.startswith("postgresql") and is_ci:
        # CI environment with Postgres available — use it directly
        yield env_url
        return

    # Fallback: file-based SQLite
    import src.backend.config as _config

    original_url = _config.settings.DATABASE_URL
    file_path = os.path.join(
        os.path.dirname(__file__),
        f"test_restart_{uuid.uuid4().hex}.db",
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


class TestRestartRecovery:
    """E2E restart recovery via the full API stack."""

    def test_end_to_end_restart_recovery(self, db_url: str) -> None:
        """
        Full restart-recovery scenario:

        Phase 1 — App 1
            POST /api/v1/patients          → get patient UUID
            POST /api/v1/recommendation     → get recommendation_id
            GET  /api/v1/recommendation/{id} → verify data

        (shutdown and dispose engine)

        Phase 2 — App 2 (separate process simulation, same DB file)
            GET  /api/v1/recommendation/{id} → verify same data is returned
        """
        # pylint: disable=import-outside-toplevel
        from src.backend.main import create_app

        # ═══════════════════════════════════════════════════════════════
        # Phase 1: App 1 — create data
        # ═══════════════════════════════════════════════════════════════
        app1 = create_app()
        app1.dependency_overrides[require_auth] = lambda: _make_fake_user()

        with TestClient(app1) as client1:
            # ── Create a patient (needed for FK constraint) ────────────────
            patient_resp = client1.post(
                "/api/v1/patients",
                json={"display_name": "Restart Recovery Patient"},
            )
            assert patient_resp.status_code == 201, (
                f"POST /api/v1/patients failed: {patient_resp.text}"
            )
            patient_id: str = patient_resp.json()["id"]
            assert patient_id, "Patient ID must not be empty"

            # ── Create a recommendation with mocked pipeline ────────────────
            # pylint: disable=import-outside-toplevel
            from unittest.mock import AsyncMock, patch

            from src.backend.clinical.drug_ranking import (
                ConflictScore,
                DrugRankingEngine,
                DrugRankingResult,
                EvidenceScore,
                OverallScore,
                Resistance,
                Sensitivity,
            )
            from src.backend.clinical.explainable_recommendation import (
                ExplainableEngine,
                ReasonItem,
                RecommendationReason,
            )
            from src.backend.clinical.recommendation_engine import (
                RecommendationEngine,
            )

            # Build mock aggregated data (simulating EvidenceAggregator output)
            mock_aggregated = {
                "Osimertinib": {
                    "variant": "EGFR L858R",
                    "gene": "EGFR",
                    "evidence_scores": [
                        {
                            "source": "TestDB",
                            "evidence_level": "A",
                            "description": (
                                "EGFR L858R is sensitive to osimertinib"
                            ),
                            "direction": "supporting",
                            "weight": 10.0,
                            "tier": "Tier_1",
                            "clinical_significance": "sensitive",
                            "source_record_id": "test-001",
                        }
                    ],
                    "total_weight": 10.0,
                    "source_count": 1,
                    "item_count": 1,
                    "highest_weight": 10.0,
                    "sources": {"TestDB"},
                }
            }

            # Build a real DrugRankingResult for DrugRankingEngine.rank
            ranking_result = DrugRankingResult(
                drug_name="Osimertinib",
                rank=1,
                overall_score=OverallScore(
                    raw_score=85.0,
                    evidence_score_value=0.9,
                    sensitivity_value=0.85,
                    resistance_value=0.1,
                    conflict_value=0.05,
                ),
                evidence_score=EvidenceScore(
                    total_weighted_score=10.0,
                    source_diversity=1.0,
                    highest_tier="Tier_1",
                    confidence_score=0.9,
                ),
                sensitivity=Sensitivity(
                    score=0.85,
                    supporting_item_count=1,
                    total_item_count=1,
                    details=(
                        "Sensitivity for Osimertinib: 1/1 items supporting, "
                        "weighted score = 0.8500."
                    ),
                ),
                resistance=Resistance(
                    score=0.1,
                    resistance_item_count=0,
                    total_item_count=1,
                    details="No resistance evidence detected.",
                ),
                conflict_score=ConflictScore(
                    score=0.05,
                    conflicting_pairs=0,
                    total_items=1,
                    details="Insufficient items for conflict analysis.",
                ),
                details={
                    "item_count": 1,
                    "source_count": 1,
                    "highest_weight": 10.0,
                    "sources": ["TestDB"],
                },
            )

            # Build a real RecommendationReason for ExplainableEngine
            explanation = RecommendationReason(
                drug_name="Osimertinib",
                rank=1,
                overall_score=85.0,
                reasons=[
                    ReasonItem(
                        category="evidence_support",
                        detail=(
                            "Evidence confidence score is 0.9000 "
                            "(weighted score 10.00, source diversity 1.00)."
                        ),
                        source="EvidenceAggregator",
                        score_impact=0.36,
                    ),
                    ReasonItem(
                        category="sensitivity",
                        detail=(
                            "Sensitivity score 0.8500 — 1/1 evidence items "
                            "indicate sensitivity."
                        ),
                        source="DrugRankingEngine",
                        score_impact=0.2975,
                    ),
                    ReasonItem(
                        category="resistance",
                        detail="No resistance evidence detected.",
                        source="DrugRankingEngine",
                        score_impact=0.0,
                    ),
                    ReasonItem(
                        category="conflict",
                        detail="No conflicting evidence detected.",
                        source="DrugRankingEngine",
                        score_impact=0.0,
                    ),
                ],
            )

            with patch.object(
                RecommendationEngine,
                "run",
                new_callable=AsyncMock,
            ) as mock_run, patch.object(
                DrugRankingEngine,
                "rank",
                return_value=[ranking_result],
            ), patch.object(
                ExplainableEngine,
                "generate_explanations",
                return_value=[explanation],
            ):

                mock_run.return_value = {
                    "pipeline_status": "completed",
                    "aggregated": mock_aggregated,
                    "drugs_ranked": [
                        {
                            "drug_name": "Osimertinib",
                            "rank": 1,
                            "total_weight": 10.0,
                        }
                    ],
                    "evidence_count": 1,
                    "rules_evaluated": 10,
                    "rules_fired": 5,
                    "rule_results": [],
                }

                rec_resp = client1.post(
                    "/api/v1/recommendation",
                    json={
                        "patient_id": patient_id,
                        "variants": ["EGFR L858R"],
                        "patient_context": {
                            "cancer_type": "Lung Adenocarcinoma",
                            "age": 62,
                            "gender": "F",
                        },
                    },
                )

            assert rec_resp.status_code == 200, (
                f"POST /api/v1/recommendation failed: {rec_resp.text}"
            )
            rec_data1 = rec_resp.json()
            rec_id: str = rec_data1["recommendation_id"]

            # Validate POST response structure
            assert rec_data1["patient_id"] == patient_id
            assert "recommendations" in rec_data1
            assert len(rec_data1["recommendations"]) > 0
            assert rec_data1["engine_version"] == "1.0.0"
            assert "trace_id" in rec_data1
            assert "created_at" in rec_data1

            # ── Verify read-back in the same app instance ──────────────────
            get_resp1 = client1.get(f"/api/v1/recommendation/{rec_id}")
            assert get_resp1.status_code == 200, (
                f"GET /api/v1/recommendation/{rec_id} in App 1 failed: "
                f"{get_resp1.text}"
            )
            get_data1 = get_resp1.json()
            assert get_data1["recommendation_id"] == rec_id
            assert get_data1["patient_id"] == patient_id
            assert len(get_data1["recommendations"]) == len(
                rec_data1["recommendations"]
            )

        # ── App 1 context exited → lifespan shutdown → engine disposed ─────

        # ── Capture engine & sessionmaker references for Postgres check ────
        # pylint: disable=import-outside-toplevel
        from src.backend.database import session as _db_session

        engine1 = _db_session.engine
        sessionmaker1 = _db_session.async_session_factory

        # ═══════════════════════════════════════════════════════════════
        # Phase 2: App 2 — read back the same data from the DB file
        # ═══════════════════════════════════════════════════════════════
        app2 = create_app()
        app2.dependency_overrides[require_auth] = lambda: _make_fake_user()
        assert app1 is not app2, "App 2 must be a different instance from App 1"

        with TestClient(app2) as client2:
            # ── GET the recommendation created in Phase 1 ──────────────────
            get_resp2 = client2.get(f"/api/v1/recommendation/{rec_id}")
            assert get_resp2.status_code == 200, (
                f"GET /api/v1/recommendation/{rec_id} in App 2 (after restart) "
                f"failed: {get_resp2.text}"
            )
            rec_data2 = get_resp2.json()

            # ── Verify data integrity across restart ───────────────────────
            assert rec_data2["recommendation_id"] == rec_id, (
                "recommendation_id must match after restart"
            )
            assert rec_data2["patient_id"] == patient_id, (
                "patient_id must match after restart"
            )
            assert rec_data2["engine_version"] == "1.0.0", (
                "engine_version must match after restart"
            )
            assert rec_data2["trace_id"] == rec_data1["trace_id"], (
                "trace_id must match after restart"
            )

            # Verify the full recommendation list
            orig_recs = rec_data1["recommendations"]
            restart_recs = rec_data2["recommendations"]
            assert len(restart_recs) == len(orig_recs), (
                f"Number of recommendations changed after restart: "
                f"{len(orig_recs)} → {len(restart_recs)}"
            )
            for orig, rest in zip(orig_recs, restart_recs):
                assert orig["drug_name"] == rest["drug_name"]
                assert orig["rank"] == rest["rank"]
                assert orig["overall_score"] == rest["overall_score"]

            # Optional: verify the patient also survived
            patient_resp2 = client2.get(f"/api/v1/patients/{patient_id}")
            assert patient_resp2.status_code == 200, (
                f"Patient {patient_id} not found after restart"
            )
            assert (
                patient_resp2.json()["display_name"]
                == "Restart Recovery Patient"
            )

        # ── App 2 context exited → lifespan shutdown → cleanup ─────────────

        # ── Postgres-specific check: engine & sessionmaker must differ ─────
        if db_url.startswith("postgresql"):
            engine2 = _db_session.engine
            sessionmaker2 = _db_session.async_session_factory
            assert engine1 is not engine2, (
                "Engine must be a new instance after restart (Postgres)"
            )
            assert sessionmaker1 is not sessionmaker2, (
                "Sessionmaker must be a new instance after restart (Postgres)"
            )

    def test_restart_recovery_nonexistent_returns_404(self, db_url: str) -> None:
        """After restart, a non-existent recommendation returns 404."""
        from src.backend.main import create_app

        app = create_app()
        app.dependency_overrides[require_auth] = lambda: _make_fake_user()

        with TestClient(app) as client:
            resp = client.get(
                f"/api/v1/recommendation/{uuid.uuid4().hex}"
            )
            assert resp.status_code == 404, (
                f"Expected 404 for non-existent recommendation, "
                f"got {resp.status_code}: {resp.text}"
            )


class TestPostgresRestart:
    """Optional Postgres-specific restart checks (only active with real Postgres)."""

    def test_restart_recovery_postgres_engine_check(self, db_url: str) -> None:
        """Verify engine/sessionmaker instances differ across restarts.

        Only performs assertions when DATABASE_URL points to a real Postgres;
        otherwise passes silently (SQLite fallback).
        """
        if not db_url.startswith("postgresql"):
            return  # Not a Postgres environment — nothing to check

        # pylint: disable=import-outside-toplevel
        from src.backend.database import session as _db_session
        from src.backend.main import create_app

        app1 = create_app()
        app1.dependency_overrides[require_auth] = lambda: _make_fake_user()

        with TestClient(app1):
            pass  # trigger lifespan (init_db)

        engine1 = _db_session.engine
        sessionmaker1 = _db_session.async_session_factory

        app2 = create_app()
        app2.dependency_overrides[require_auth] = lambda: _make_fake_user()

        with TestClient(app2):
            pass  # trigger lifespan (init_db again)

        engine2 = _db_session.engine
        sessionmaker2 = _db_session.async_session_factory

        assert engine1 is not engine2, (
            "Engine must be a new instance after restart (Postgres)"
        )
        assert sessionmaker1 is not sessionmaker2, (
            "Sessionmaker must be a new instance after restart (Postgres)"
        )
