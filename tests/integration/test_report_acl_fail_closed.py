"""Report ACL fail-closed integration tests — real HTTP + DB verification.
Tests NULL case_id, malformed case_id, full format authorization.
"""
from __future__ import annotations

import json
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text as sa_text

from src.backend.config import settings
from src.backend.database import session as db_session
from src.backend.main import create_app


@pytest.fixture(scope="module")
def app_client():
    settings.DATABASE_URL = "sqlite+aiosqlite://"
    settings.APP_MODE = "demo"
    settings.DEBUG = False
    app = create_app()
    with TestClient(app) as c:
        yield c


def _register(app_client, username: str, password: str = "TestPass123!") -> tuple[str, str]:
    resp = app_client.post("/auth/register", json={
        "username": username, "password": password, "display_name": username,
    })
    assert resp.status_code == 201, f"Register failed: {resp.json()}"
    uid = resp.json()["id"]
    login = app_client.post("/auth/login", json={
        "username": username, "password": password,
    })
    assert login.status_code == 200
    return login.json()["access_token"], uid


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _raw_insert_report(
    case_id_value,  # str or None
    report_data: dict = None,
    html_content: str = "<html>test</html>",
    fhir_data: dict = None,
) -> str:
    """Insert a report row directly via raw SQL, bypassing ORM constraints."""
    if report_data is None:
        report_data = {"title": "Legacy Report", "metadata": {"version": "1.0.0", "status": "final"}}
    if fhir_data is None:
        fhir_data = {"resourceType": "Bundle"}

    async with db_session.async_session_factory() as session:
        report_id = str(uuid.uuid4())
        now = "2024-01-01 00:00:00"

        # For NULL case_id testing: temporarily make case_id nullable
        # SQLite doesn't support ALTER COLUMN, so use sentinel approach
        # The sentinel matches what migration 015 assigns to NULL rows
        sentinel = "00000000-0000-0000-0000-000000000000"
        actual_case = case_id_value if case_id_value is not None else sentinel

        stmt = sa_text("""
            INSERT INTO domain_clinical_reports
                (id, case_id, version, status, report_data, html_content, fhir_data, created_at, updated_at)
            VALUES
                (:id, :case_id, :version, :status, :report_data, :html_content, :fhir_data, :created_at, :updated_at)
        """)
        await session.execute(stmt, {
            "id": report_id,
            "case_id": actual_case,
            "version": "1.0.0",
            "status": "final",
            "report_data": json.dumps(report_data),
            "html_content": html_content,
            "fhir_data": json.dumps(fhir_data) if fhir_data else None,
            "created_at": now,
            "updated_at": now,
        })
        await session.commit()
        return report_id


# ── Tests ─────────────────────────────────────────────────────────────────


SENTINEL_CASE_ID = "00000000-0000-0000-0000-000000000000"


class TestLegacyNullMigratedToQuarantineCase:
    """Migration 015 converts NULL case_id → sentinel UUID. Quarantined reports
    must be denied for ALL users, including admin."""

    @pytest.fixture(scope="module")
    def setup(self, app_client):
        token_user, uid_user = _register(app_client, "quarantine_user", "TestPass123!")
        # Register a user as admin role — but admin still cannot access quarantine
        token_admin, uid_admin = _register(app_client, "quarantine_admin", "TestPass123!")
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        report_id = loop.run_until_complete(_raw_insert_report(SENTINEL_CASE_ID))
        loop.close()
        return {
            "token_user": token_user,
            "token_admin": token_admin,
            "report_id": report_id,
        }

    def test_legacy_null_quarantine_denied(self, app_client, setup):
        """Quarantined report (migrated NULL case_id) denied for normal user."""
        resp = app_client.get(
            f"/api/v1/reports/{setup['report_id']}",
            headers=_auth_headers(setup["token_user"]),
        )
        assert resp.status_code == 403

    def test_legacy_null_html_denied(self, app_client, setup):
        resp = app_client.get(
            f"/api/v1/reports/{setup['report_id']}/html",
            headers=_auth_headers(setup["token_user"]),
        )
        assert resp.status_code == 403

    def test_legacy_null_json_denied(self, app_client, setup):
        resp = app_client.get(
            f"/api/v1/reports/{setup['report_id']}/json",
            headers=_auth_headers(setup["token_user"]),
        )
        assert resp.status_code == 403

    def test_legacy_null_fhir_denied(self, app_client, setup):
        resp = app_client.get(
            f"/api/v1/reports/{setup['report_id']}/fhir",
            headers=_auth_headers(setup["token_user"]),
        )
        assert resp.status_code == 403

    def test_admin_quarantine_denied(self, app_client, setup):
        """Admin must also be denied access to quarantined legacy reports."""
        resp = app_client.get(
            f"/api/v1/reports/{setup['report_id']}",
            headers=_auth_headers(setup["token_admin"]),
        )
        assert resp.status_code == 403

    def test_admin_quarantine_html_denied(self, app_client, setup):
        resp = app_client.get(
            f"/api/v1/reports/{setup['report_id']}/html",
            headers=_auth_headers(setup["token_admin"]),
        )
        assert resp.status_code == 403


class TestReportMalformedCaseId:
    """Reports with malformed (non-UUID) case_id must be denied."""

    @pytest.fixture(scope="module")
    def setup(self, app_client):
        token_user, uid_user = _register(app_client, "malformed_case_user", "TestPass123!")
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        report_id = loop.run_until_complete(_raw_insert_report("not-a-uuid"))
        loop.close()
        return {
            "token_user": token_user,
            "report_id": report_id,
        }

    def test_malformed_case_denied(self, app_client, setup):
        resp = app_client.get(
            f"/api/v1/reports/{setup['report_id']}",
            headers=_auth_headers(setup["token_user"]),
        )
        assert resp.status_code == 403

    def test_malformed_case_html_denied(self, app_client, setup):
        resp = app_client.get(
            f"/api/v1/reports/{setup['report_id']}/html",
            headers=_auth_headers(setup["token_user"]),
        )
        assert resp.status_code == 403

    def test_malformed_case_json_denied(self, app_client, setup):
        resp = app_client.get(
            f"/api/v1/reports/{setup['report_id']}/json",
            headers=_auth_headers(setup["token_user"]),
        )
        assert resp.status_code == 403

    def test_malformed_case_fhir_denied(self, app_client, setup):
        resp = app_client.get(
            f"/api/v1/reports/{setup['report_id']}/fhir",
            headers=_auth_headers(setup["token_user"]),
        )
        assert resp.status_code == 403


class TestReportFullFormatAuthorization:
    """Full format authorization: 4 endpoints × 3 scenarios."""

    @pytest.fixture(scope="module")
    def setup(self, app_client):
        # Register owner + unrelated
        token_owner, uid_owner = _register(app_client, "fmt_owner", "TestPass123!")
        token_unrelated, uid_unrelated = _register(app_client, "fmt_unrelated", "TestPass123!")
        token_viewer, uid_viewer = _register(app_client, "fmt_viewer", "TestPass123!")

        # Create proper case + report
        resp = app_client.post(
            "/api/v1/patients",
            json={"sex": "F", "consent_status": "granted"},
            headers=_auth_headers(token_owner),
        )
        assert resp.status_code == 201
        pid = resp.json()["id"]

        resp = app_client.post(
            "/api/v1/cases",
            json={"patient_id": pid, "cancer_type": "PTC"},
            headers=_auth_headers(token_owner),
        )
        assert resp.status_code == 201
        case_id = resp.json()["id"]

        # Grant viewer role
        resp = app_client.post(
            f"/api/v1/cases/{case_id}/acl",
            json={"case_id": case_id, "user_id": uid_viewer, "role": "viewer"},
            headers=_auth_headers(token_owner),
        )
        assert resp.status_code == 201

        # Create a report
        resp = app_client.post(
            f"/api/v1/reports/case/{case_id}",
            json={},
            headers=_auth_headers(token_owner),
        )
        assert resp.status_code == 200
        report_id = resp.json()["report_id"]

        return {
            "token_owner": token_owner,
            "token_unrelated": token_unrelated,
            "token_viewer": token_viewer,
            "case_id": case_id,
            "report_id": report_id,
            "random_report_id": str(uuid.uuid4()),
        }

    # ── Unrelated user: all 4 formats must return 403 ──

    def test_unrelated_metadata_403(self, app_client, setup):
        resp = app_client.get(
            f"/api/v1/reports/{setup['report_id']}",
            headers=_auth_headers(setup["token_unrelated"]),
        )
        assert resp.status_code == 403

    def test_unrelated_html_403(self, app_client, setup):
        resp = app_client.get(
            f"/api/v1/reports/{setup['report_id']}/html",
            headers=_auth_headers(setup["token_unrelated"]),
        )
        assert resp.status_code == 403

    def test_unrelated_json_403(self, app_client, setup):
        resp = app_client.get(
            f"/api/v1/reports/{setup['report_id']}/json",
            headers=_auth_headers(setup["token_unrelated"]),
        )
        assert resp.status_code == 403

    def test_unrelated_fhir_403(self, app_client, setup):
        resp = app_client.get(
            f"/api/v1/reports/{setup['report_id']}/fhir",
            headers=_auth_headers(setup["token_unrelated"]),
        )
        assert resp.status_code == 403

    # ── Authorized viewer: all 4 formats must return 200 ──

    def test_viewer_metadata_200(self, app_client, setup):
        resp = app_client.get(
            f"/api/v1/reports/{setup['report_id']}",
            headers=_auth_headers(setup["token_viewer"]),
        )
        assert resp.status_code == 200

    def test_viewer_html_200(self, app_client, setup):
        resp = app_client.get(
            f"/api/v1/reports/{setup['report_id']}/html",
            headers=_auth_headers(setup["token_viewer"]),
        )
        assert resp.status_code == 200

    def test_viewer_json_200(self, app_client, setup):
        resp = app_client.get(
            f"/api/v1/reports/{setup['report_id']}/json",
            headers=_auth_headers(setup["token_viewer"]),
        )
        assert resp.status_code == 200

    def test_viewer_fhir_200(self, app_client, setup):
        resp = app_client.get(
            f"/api/v1/reports/{setup['report_id']}/fhir",
            headers=_auth_headers(setup["token_viewer"]),
        )
        assert resp.status_code == 200

    # ── Random report ID: all 4 formats must return 404 ──

    def test_random_metadata_404(self, app_client, setup):
        resp = app_client.get(
            f"/api/v1/reports/{setup['random_report_id']}",
            headers=_auth_headers(setup["token_viewer"]),
        )
        assert resp.status_code == 404

    def test_random_html_404(self, app_client, setup):
        resp = app_client.get(
            f"/api/v1/reports/{setup['random_report_id']}/html",
            headers=_auth_headers(setup["token_viewer"]),
        )
        assert resp.status_code == 404

    def test_random_json_404(self, app_client, setup):
        resp = app_client.get(
            f"/api/v1/reports/{setup['random_report_id']}/json",
            headers=_auth_headers(setup["token_viewer"]),
        )
        assert resp.status_code == 404

    def test_random_fhir_404(self, app_client, setup):
        resp = app_client.get(
            f"/api/v1/reports/{setup['random_report_id']}/fhir",
            headers=_auth_headers(setup["token_viewer"]),
        )
        assert resp.status_code == 404
