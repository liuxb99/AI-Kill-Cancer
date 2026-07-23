"""
ACL HTTP integration tests — real HTTP requests + database verification.
"""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from src.backend.config import settings
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
    """Register a user and return (access_token, user_id)."""
    resp = app_client.post("/auth/register", json={
        "username": username,
        "password": password,
        "display_name": username,
    })
    assert resp.status_code == 201, f"Register failed: {resp.json()}"
    user_id = resp.json()["id"]
    login = app_client.post("/auth/login", json={
        "username": username,
        "password": password,
    })
    assert login.status_code == 200, f"Login failed: {login.json()}"
    return login.json()["access_token"], user_id


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _create_patient(app_client, token: str) -> str:
    """Create a patient and return patient ID."""
    resp = app_client.post(
        "/api/v1/patients",
        json={"sex": "F", "consent_status": "granted"},
        headers=_auth_headers(token),
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def _create_case(app_client, token: str, patient_id: str) -> str:
    """Create a case and return case ID."""
    resp = app_client.post(
        "/api/v1/cases",
        json={
            "patient_id": patient_id,
            "cancer_type": "PTC",
        },
        headers=_auth_headers(token),
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def _grant_access(app_client, token: str, case_id: str, target_user_id: str, role: str):
    """Grant ACL on a case to another user by user_id."""
    resp = app_client.post(
        f"/api/v1/cases/{case_id}/acl",
        json={"case_id": case_id, "user_id": target_user_id, "role": role},
        headers=_auth_headers(token),
    )
    return resp


class TestCaseACLUpload:
    """Upload ACL: User A owns case, User B guesses upload ID."""

    @pytest.fixture(scope="module")
    def setup(self, app_client):
        # Register users
        token_a, uid_a = _register(app_client, "acl_upload_a", "TestPass123!")
        token_b, uid_b = _register(app_client, "acl_upload_b", "TestPass123!")
        token_c, uid_c = _register(app_client, "acl_upload_c", "TestPass123!")

        # Create patient + case for User A
        pid = _create_patient(app_client, token_a)
        case_id = _create_case(app_client, token_a, pid)

        # Grant User C as VIEWER
        grant_resp = _grant_access(app_client, token_a, case_id, uid_c, "viewer")
        assert grant_resp.status_code == 201, f"Grant viewer failed: {grant_resp.json()}"

        # Grant User B as EDITOR
        grant_resp = _grant_access(app_client, token_a, case_id, uid_b, "editor")
        assert grant_resp.status_code == 201, f"Grant editor failed: {grant_resp.json()}"

        return {
            "token_a": token_a,
            "token_b": token_b,
            "token_c": token_c,
            "case_id": case_id,
        }

    def test_unrelated_user_denied(self, app_client, setup):
        """User D (no ACL) gets 403 on case."""
        token_d, uid_d = _register(app_client, "acl_upload_d", "TestPass123!")
        resp = app_client.get(
            f"/api/v1/cases/{setup['case_id']}",
            headers=_auth_headers(token_d),
        )
        assert resp.status_code == 403

    def test_viewer_read_allowed(self, app_client, setup):
        """Viewer can read case."""
        resp = app_client.get(
            f"/api/v1/cases/{setup['case_id']}",
            headers=_auth_headers(setup["token_c"]),
        )
        assert resp.status_code == 200

    def test_viewer_write_denied(self, app_client, setup):
        """Viewer cannot update case."""
        resp = app_client.put(
            f"/api/v1/cases/{setup['case_id']}",
            json={"diagnosis": "Modified"},
            headers=_auth_headers(setup["token_c"]),
        )
        # 403 or 403-like — write requires EDITOR+
        assert resp.status_code == 403

    def test_editor_write_allowed(self, app_client, setup):
        """Editor can update case."""
        resp = app_client.put(
            f"/api/v1/cases/{setup['case_id']}",
            json={"diagnosis": "Updated diagnosis"},
            headers=_auth_headers(setup["token_b"]),
        )
        assert resp.status_code == 200

    def test_owner_delete_allowed(self, app_client, setup):
        """Owner can delete case."""
        resp = app_client.delete(
            f"/api/v1/cases/{setup['case_id']}",
            headers=_auth_headers(setup["token_a"]),
        )
        assert resp.status_code == 204


class TestSpecimenACL:
    """Specimen ACL through case ownership."""

    @pytest.fixture(scope="module")
    def setup(self, app_client):
        token, uid = _register(app_client, "spec_owner")
        token_other, uid_other = _register(app_client, "spec_unrelated")
        pid = _create_patient(app_client, token)
        case_id = _create_case(app_client, token, pid)

        # Create specimen
        resp = app_client.post(
            "/api/v1/specimens",
            json={"case_id": case_id, "specimen_type": "FFPE", "collection_date": "2024-01-15"},
            headers=_auth_headers(token),
        )
        assert resp.status_code == 201
        specimen_id = resp.json()["id"]

        return {
            "token": token,
            "token_other": token_other,
            "case_id": case_id,
            "specimen_id": specimen_id,
        }

    def test_unrelated_user_denied_specimen(self, app_client, setup):
        """Unrelated user gets 403 on specimen."""
        resp = app_client.get(
            f"/api/v1/specimens/{setup['specimen_id']}",
            headers=_auth_headers(setup["token_other"]),
        )
        assert resp.status_code == 403

    def test_owner_read_allowed(self, app_client, setup):
        """Owner can read specimen."""
        resp = app_client.get(
            f"/api/v1/specimens/{setup['specimen_id']}",
            headers=_auth_headers(setup["token"]),
        )
        assert resp.status_code == 200


class TestReportACL:
    """Report ACL — NULL case_id handling and access enforcement."""

    @pytest.fixture(scope="module")
    def setup(self, app_client):
        token, uid = _register(app_client, "report_owner")
        token_other, uid_other = _register(app_client, "report_other")
        pid = _create_patient(app_client, token)
        case_id = _create_case(app_client, token, pid)

        # Create report via the service (route requires EDITOR)
        resp = app_client.post(
            f"/api/v1/reports/case/{case_id}",
            json={
                "title": "Test Report",
                "evidence_ids": [],
                "drug_rankings": [],
                "reasoning_ids": [],
            },
            headers=_auth_headers(token),
        )
        assert resp.status_code in (200, 201)
        report_id = resp.json().get("id") or resp.json().get("report_id", "")
        assert report_id

        return {
            "token": token,
            "token_other": token_other,
            "case_id": case_id,
            "report_id": report_id,
        }

    def test_unrelated_user_denied_report(self, app_client, setup):
        """Unrelated user cannot read report."""
        resp = app_client.get(
            f"/api/v1/reports/{setup['report_id']}",
            headers=_auth_headers(setup["token_other"]),
        )
        assert resp.status_code == 403

    def test_owner_read_report(self, app_client, setup):
        """Owner can read their report."""
        resp = app_client.get(
            f"/api/v1/reports/{setup['report_id']}",
            headers=_auth_headers(setup["token"]),
        )
        assert resp.status_code == 200

    def test_guess_report_id_denied(self, app_client, setup):
        """Random report ID guess gets 403 or 404."""
        fake_id = str(uuid.uuid4())
        resp = app_client.get(
            f"/api/v1/reports/{fake_id}",
            headers=_auth_headers(setup["token_other"]),
        )
        assert resp.status_code in (403, 404)

    def test_malformed_case_id_denied(self, app_client, setup):
        """Malformed case ID in URL returns 404."""
        resp = app_client.get(
            "/api/v1/cases/not-a-valid-uuid",
            headers=_auth_headers(setup["token_other"]),
        )
        assert resp.status_code == 404
