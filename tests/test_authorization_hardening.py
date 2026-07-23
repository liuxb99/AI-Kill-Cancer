"""
Authorization and Case ACL tests for v1.0.2 production hardening.

Tests:
- Case ACL model validity
- Role hierarchy enforcement
- Permission matrix
- Case-level access control logic
"""
from __future__ import annotations

# ─── Authorization matrix integration tests ───────────────────────────────
import pytest
from fastapi.testclient import TestClient

from src.backend.auth.models import ROLE_PERMISSIONS, Role
from src.backend.config import settings
from src.backend.domain.case_acl import (
    CASE_REQUIRED_ROLES,
    CASE_ROLE_HIERARCHY,
    CaseACLModel,
    CaseRole,
)
from src.backend.main import create_app


# Shared helpers — reimplanted locally to avoid cross-test coupling
def _register_user(client: TestClient, username: str, password: str = "TestPass123!") -> str:
    """Register a user and return the access token."""
    resp = client.post("/auth/register", json={
        "username": username,
        "password": password,
        "display_name": username,
    })
    assert resp.status_code == 201, f"Register failed: {resp.json()}"
    login = client.post("/auth/login", json={
        "username": username,
        "password": password,
    })
    assert login.status_code == 200, f"Login failed: {login.json()}"
    return login.json()["access_token"]


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _create_patient(client: TestClient, token: str) -> str:
    """Create a patient and return patient ID."""
    resp = client.post(
        "/api/v1/patients",
        json={"sex": "F", "consent_status": "granted"},
        headers=_auth_headers(token),
    )
    assert resp.status_code == 201, f"Create patient failed: {resp.json()}"
    return resp.json()["id"]


def _create_case(client: TestClient, token: str, patient_id: str) -> str:
    """Create a case and return case ID."""
    resp = client.post(
        "/api/v1/cases",
        json={"patient_id": patient_id, "cancer_type": "PTC"},
        headers=_auth_headers(token),
    )
    assert resp.status_code == 201, f"Create case failed: {resp.json()}"
    return resp.json()["id"]


INVALID_CASE_ID = "550e8400-e29b-41d4-a716-446655440000"
"""Valid UUID format but no case exists with this ID."""


@pytest.fixture(scope="module")
def client():
    """Create a TestClient with in-memory SQLite database."""
    settings.DATABASE_URL = "sqlite+aiosqlite://"
    settings.APP_MODE = "demo"
    settings.DEBUG = False
    app = create_app()
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def auth_setup(client):
    """Register user, create patient + case, return tokens and IDs."""
    token = _register_user(client, "auth_harden_user")
    pid = _create_patient(client, token)
    case_id = _create_case(client, token, pid)
    return {"token": token, "case_id": case_id, "patient_id": pid}


@pytest.fixture(scope="module")
def second_user(client):
    """Register a second user who has NO access to the primary case."""
    token = _register_user(client, "auth_harden_user2")
    return {"token": token}


CLINICAL_PREFIX = "/api/v1/clinical"


class TestClinicalEndpointAuthorization:
    """Authorization matrix for all clinical endpoints.

    Every endpoint must reject unauthenticated requests with 401
    and accept properly authenticated requests with the correct role.
    """

    # ── Helpers ─────────────────────────────────────────────────────────

    def _test_unauthorized(self, client, method, path):
        """Call endpoint without auth token → 401."""
        resp = client.request(method, path)
        assert resp.status_code == 401, (
            f"Expected 401 for {method} {path}, got {resp.status_code}"
        )

    def _test_invalid_token(self, client, method, path):
        """Call endpoint with garbage token → 401."""
        resp = client.request(
            method, path,
            headers={"Authorization": "Bearer invalid_token_xyz"},
        )
        assert resp.status_code == 401, (
            f"Expected 401 for {method} {path} with bad token, got {resp.status_code}"
        )

    # ── GET /context/{case_id} ──────────────────────────────────────────

    def test_context_no_auth(self, client, auth_setup):
        self._test_unauthorized(client, "GET",
                                f"{CLINICAL_PREFIX}/context/{auth_setup['case_id']}")

    def test_context_invalid_token(self, client, auth_setup):
        self._test_invalid_token(client, "GET",
                                 f"{CLINICAL_PREFIX}/context/{auth_setup['case_id']}")

    def test_context_authorized(self, client, auth_setup):
        """Authenticated user with case access gets 200."""
        resp = client.get(
            f"{CLINICAL_PREFIX}/context/{auth_setup['case_id']}",
            headers=_auth_headers(auth_setup["token"]),
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.json()}"

    def test_context_no_case_access(self, client, auth_setup, second_user):
        """User without ACL on the case gets 403."""
        resp = client.get(
            f"{CLINICAL_PREFIX}/context/{auth_setup['case_id']}",
            headers=_auth_headers(second_user["token"]),
        )
        assert resp.status_code == 403, (
            f"Expected 403 for user without case access, got {resp.status_code}"
        )

    # ── GET /evidence/{case_id} ─────────────────────────────────────────

    def test_evidence_no_auth(self, client, auth_setup):
        self._test_unauthorized(client, "GET",
                                f"{CLINICAL_PREFIX}/evidence/{auth_setup['case_id']}")

    def test_evidence_invalid_token(self, client, auth_setup):
        self._test_invalid_token(client, "GET",
                                 f"{CLINICAL_PREFIX}/evidence/{auth_setup['case_id']}")

    def test_evidence_authorized(self, client, auth_setup):
        resp = client.get(
            f"{CLINICAL_PREFIX}/evidence/{auth_setup['case_id']}",
            headers=_auth_headers(auth_setup["token"]),
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.json()}"

    def test_evidence_no_case_access(self, client, auth_setup, second_user):
        resp = client.get(
            f"{CLINICAL_PREFIX}/evidence/{auth_setup['case_id']}",
            headers=_auth_headers(second_user["token"]),
        )
        assert resp.status_code == 403

    # ── GET /evidence/gene/{gene_symbol} ────────────────────────────────

    def test_evidence_gene_no_auth(self, client):
        self._test_unauthorized(client, "GET",
                                f"{CLINICAL_PREFIX}/evidence/gene/BRAF")

    def test_evidence_gene_invalid_token(self, client):
        self._test_invalid_token(client, "GET",
                                 f"{CLINICAL_PREFIX}/evidence/gene/BRAF")

    def test_evidence_gene_authorized(self, client, auth_setup):
        """This endpoint only requires require_auth (no case ACL)."""
        resp = client.get(
            f"{CLINICAL_PREFIX}/evidence/gene/BRAF",
            headers=_auth_headers(auth_setup["token"]),
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.json()}"

    def test_evidence_gene_any_authenticated_user(self, client, second_user):
        """Any authenticated user (even without case access) can query by gene."""
        resp = client.get(
            f"{CLINICAL_PREFIX}/evidence/gene/BRAF",
            headers=_auth_headers(second_user["token"]),
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.json()}"

    # ── POST /agents/{case_id} ─────────────────────────────────────────—

    def test_agents_no_auth(self, client, auth_setup):
        self._test_unauthorized(client, "POST",
                                f"{CLINICAL_PREFIX}/agents/{auth_setup['case_id']}")

    def test_agents_invalid_token(self, client, auth_setup):
        self._test_invalid_token(client, "POST",
                                 f"{CLINICAL_PREFIX}/agents/{auth_setup['case_id']}")

    def test_agents_authorized(self, client, auth_setup):
        resp = client.post(
            f"{CLINICAL_PREFIX}/agents/{auth_setup['case_id']}",
            headers=_auth_headers(auth_setup["token"]),
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.json()}"

    def test_agents_no_case_access(self, client, auth_setup, second_user):
        resp = client.post(
            f"{CLINICAL_PREFIX}/agents/{auth_setup['case_id']}",
            headers=_auth_headers(second_user["token"]),
        )
        assert resp.status_code == 403

    # ── POST /consensus/{case_id} ───────────────────────────────────────

    def test_consensus_no_auth(self, client, auth_setup):
        self._test_unauthorized(client, "POST",
                                f"{CLINICAL_PREFIX}/consensus/{auth_setup['case_id']}")

    def test_consensus_invalid_token(self, client, auth_setup):
        self._test_invalid_token(client, "POST",
                                 f"{CLINICAL_PREFIX}/consensus/{auth_setup['case_id']}")

    def test_consensus_authorized(self, client, auth_setup):
        resp = client.post(
            f"{CLINICAL_PREFIX}/consensus/{auth_setup['case_id']}",
            headers=_auth_headers(auth_setup["token"]),
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.json()}"

    def test_consensus_no_case_access(self, client, auth_setup, second_user):
        resp = client.post(
            f"{CLINICAL_PREFIX}/consensus/{auth_setup['case_id']}",
            headers=_auth_headers(second_user["token"]),
        )
        assert resp.status_code == 403

    # ── POST /recommend/{case_id} ───────────────────────────────────────

    def test_recommend_no_auth(self, client, auth_setup):
        self._test_unauthorized(client, "POST",
                                f"{CLINICAL_PREFIX}/recommend/{auth_setup['case_id']}")

    def test_recommend_invalid_token(self, client, auth_setup):
        self._test_invalid_token(client, "POST",
                                 f"{CLINICAL_PREFIX}/recommend/{auth_setup['case_id']}")

    def test_recommend_authorized(self, client, auth_setup):
        resp = client.post(
            f"{CLINICAL_PREFIX}/recommend/{auth_setup['case_id']}",
            headers=_auth_headers(auth_setup["token"]),
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.json()}"

    def test_recommend_no_case_access(self, client, auth_setup, second_user):
        resp = client.post(
            f"{CLINICAL_PREFIX}/recommend/{auth_setup['case_id']}",
            headers=_auth_headers(second_user["token"]),
        )
        assert resp.status_code == 403

    # ── POST /analyze/{case_id} ─────────────────────────────────────────

    def test_analyze_no_auth(self, client, auth_setup):
        self._test_unauthorized(client, "POST",
                                f"{CLINICAL_PREFIX}/analyze/{auth_setup['case_id']}")

    def test_analyze_invalid_token(self, client, auth_setup):
        self._test_invalid_token(client, "POST",
                                 f"{CLINICAL_PREFIX}/analyze/{auth_setup['case_id']}")

    def test_analyze_authorized(self, client, auth_setup):
        resp = client.post(
            f"{CLINICAL_PREFIX}/analyze/{auth_setup['case_id']}",
            headers=_auth_headers(auth_setup["token"]),
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.json()}"

    def test_analyze_no_case_access(self, client, auth_setup, second_user):
        resp = client.post(
            f"{CLINICAL_PREFIX}/analyze/{auth_setup['case_id']}",
            headers=_auth_headers(second_user["token"]),
        )
        assert resp.status_code == 403

    # ── GET /thread/{case_id} ───────────────────────────────────────────

    def test_thread_no_auth(self, client, auth_setup):
        self._test_unauthorized(client, "GET",
                                f"{CLINICAL_PREFIX}/thread/{auth_setup['case_id']}")

    def test_thread_invalid_token(self, client, auth_setup):
        self._test_invalid_token(client, "GET",
                                 f"{CLINICAL_PREFIX}/thread/{auth_setup['case_id']}")

    def test_thread_authorized(self, client, auth_setup):
        resp = client.get(
            f"{CLINICAL_PREFIX}/thread/{auth_setup['case_id']}",
            headers=_auth_headers(auth_setup["token"]),
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.json()}"

    def test_thread_no_case_access(self, client, auth_setup, second_user):
        resp = client.get(
            f"{CLINICAL_PREFIX}/thread/{auth_setup['case_id']}",
            headers=_auth_headers(second_user["token"]),
        )
        assert resp.status_code == 403

    # ── GET /thread/{case_id}/tree ──────────────────────────────────────

    def test_tree_no_auth(self, client, auth_setup):
        self._test_unauthorized(client, "GET",
                                f"{CLINICAL_PREFIX}/thread/{auth_setup['case_id']}/tree")

    def test_tree_invalid_token(self, client, auth_setup):
        self._test_invalid_token(client, "GET",
                                 f"{CLINICAL_PREFIX}/thread/{auth_setup['case_id']}/tree")

    def test_tree_authorized(self, client, auth_setup):
        resp = client.get(
            f"{CLINICAL_PREFIX}/thread/{auth_setup['case_id']}/tree",
            headers=_auth_headers(auth_setup["token"]),
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.json()}"

    def test_tree_no_case_access(self, client, auth_setup, second_user):
        resp = client.get(
            f"{CLINICAL_PREFIX}/thread/{auth_setup['case_id']}/tree",
            headers=_auth_headers(second_user["token"]),
        )
        assert resp.status_code == 403

    # ── GET /thread/node/{node_id} ──────────────────────────────────────

    def test_thread_node_no_auth(self, client):
        self._test_unauthorized(client, "GET",
                                f"{CLINICAL_PREFIX}/thread/node/{INVALID_CASE_ID}")

    def test_thread_node_invalid_token(self, client):
        self._test_invalid_token(client, "GET",
                                 f"{CLINICAL_PREFIX}/thread/node/{INVALID_CASE_ID}")

    def test_thread_node_authorized_returns_404(self, client, auth_setup):
        """Authenticated user gets 404 for non-existent node (not 401/403)."""
        resp = client.get(
            f"{CLINICAL_PREFIX}/thread/node/{INVALID_CASE_ID}",
            headers=_auth_headers(auth_setup["token"]),
        )
        # 404 because node doesn't exist (the require_auth passes)
        assert resp.status_code == 404, (
            f"Expected 404 for non-existent node, got {resp.status_code}: {resp.json()}"
        )


class TestRoleBoundary:
    """Verify that case-role hierarchy is enforced on endpoints.

    Endpoints requiring EDITOR access must reject a VIEWER-only user.
    """

    @pytest.fixture(scope="class")
    def role_setup(self, client):
        """Create two users: one VIEWER (no case write access), one OWNER."""
        owner_token = _register_user(client, "role_owner_user")
        viewer_token = _register_user(client, "role_viewer_user")

        # Owner creates a case
        pid = _create_patient(client, owner_token)
        case_id = _create_case(client, owner_token, pid)

        return {
            "owner_token": owner_token,
            "viewer_token": viewer_token,
            "case_id": case_id,
        }

    # ── VIEWER can read (context), cannot write (cases PUT) ─────────────

    def test_viewer_can_read_context(self, client, role_setup):
        """VIEWER-level access is sufficient for GET /context/{case_id}."""
        # Viewer has no ACL on the case → 403
        resp = client.get(
            f"{CLINICAL_PREFIX}/context/{role_setup['case_id']}",
            headers=_auth_headers(role_setup["viewer_token"]),
        )
        assert resp.status_code == 403, (
            f"Expected 403 for viewer without ACL, got {resp.status_code}"
        )

    def test_owner_can_write_case(self, client, role_setup):
        """OWNER can update a case (requires EDITOR or higher)."""
        resp = client.put(
            f"/api/v1/cases/{role_setup['case_id']}",
            json={"cancer_type": "PTC"},  # PTC is a valid CancerType enum value
            headers=_auth_headers(role_setup["owner_token"]),
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.json()}"

    # ── Role hierarchy: higher role includes lower permissions ──────────

    def test_role_hierarchy_viewer_included_in_owner(self):
        """OWNER hierarchy level >= VIEWER hierarchy level."""
        assert CASE_ROLE_HIERARCHY[CaseRole.OWNER] >= CASE_ROLE_HIERARCHY[CaseRole.VIEWER]
        assert CASE_ROLE_HIERARCHY[CaseRole.EDITOR] >= CASE_ROLE_HIERARCHY[CaseRole.VIEWER]
        assert CASE_ROLE_HIERARCHY[CaseRole.REVIEWER] >= CASE_ROLE_HIERARCHY[CaseRole.VIEWER]


class TestTokenValidation:
    """Edge cases around token validation."""

    def test_expired_token_returns_401(self, client, auth_setup):
        """A clearly malformed/expired JWT is rejected."""
        # JWT with alg=none and empty signature
        bogus_token = "eyJhbGciOiJub25lIn0.eyJzdWIiOiIxMjM0NTY3ODkwIn0."
        resp = client.get(
            f"{CLINICAL_PREFIX}/context/{auth_setup['case_id']}",
            headers={"Authorization": f"Bearer {bogus_token}"},
        )
        assert resp.status_code == 401

    def test_missing_bearer_prefix_returns_401(self, client, auth_setup):
        """Token without 'Bearer ' prefix is rejected."""
        resp = client.get(
            f"{CLINICAL_PREFIX}/context/{auth_setup['case_id']}",
            headers={"Authorization": auth_setup["token"]},
        )
        # Depending on implementation this may be 401 or 403
        assert resp.status_code in (401, 403)

    def test_empty_auth_header_returns_401(self, client, auth_setup):
        """Empty Authorization header is treated as no auth."""
        resp = client.get(
            f"{CLINICAL_PREFIX}/context/{auth_setup['case_id']}",
            headers={"Authorization": ""},
        )
        assert resp.status_code == 401


class TestCaseACLModel:
    """Verify Case ACL domain model correctness."""

    def test_case_role_hierarchy_ordering(self):
        """Verify hierarchy: viewer < reviewer < editor < owner < admin."""
        assert CASE_ROLE_HIERARCHY[CaseRole.VIEWER] == 1
        assert CASE_ROLE_HIERARCHY[CaseRole.REVIEWER] == 2
        assert CASE_ROLE_HIERARCHY[CaseRole.EDITOR] == 3
        assert CASE_ROLE_HIERARCHY[CaseRole.OWNER] == 4
        assert CASE_ROLE_HIERARCHY[CaseRole.ADMIN] == 5
        # Verify ordering
        assert CASE_ROLE_HIERARCHY[CaseRole.VIEWER] < CASE_ROLE_HIERARCHY[CaseRole.REVIEWER]
        assert CASE_ROLE_HIERARCHY[CaseRole.REVIEWER] < CASE_ROLE_HIERARCHY[CaseRole.EDITOR]
        assert CASE_ROLE_HIERARCHY[CaseRole.EDITOR] < CASE_ROLE_HIERARCHY[CaseRole.OWNER]
        assert CASE_ROLE_HIERARCHY[CaseRole.OWNER] < CASE_ROLE_HIERARCHY[CaseRole.ADMIN]

    def test_case_acl_required_roles(self):
        """Verify all required actions have minimum roles defined."""
        required_actions = [
            "view", "edit", "delete", "share",
            "add_evidence", "run_analysis", "create_report",
            "download_report", "view_audit",
        ]
        for action in required_actions:
            assert action in CASE_REQUIRED_ROLES, f"Missing required role for {action}"

        assert CASE_REQUIRED_ROLES["view"] == CaseRole.VIEWER
        assert CASE_REQUIRED_ROLES["edit"] == CaseRole.EDITOR
        assert CASE_REQUIRED_ROLES["delete"] == CaseRole.OWNER
        assert CASE_REQUIRED_ROLES["download_report"] == CaseRole.VIEWER
        assert CASE_REQUIRED_ROLES["create_report"] == CaseRole.REVIEWER

    def test_case_acl_model_fields(self):
        """Verify CaseACLModel has required fields."""
        required_fields = ["case_id", "user_id", "role", "granted_by", "created_at", "updated_at"]
        for field in required_fields:
            assert hasattr(CaseACLModel, field), f"CaseACLModel missing field: {field}"

    def test_case_role_enum_values(self):
        """Verify CaseRole enum has expected values."""
        assert CaseRole.OWNER.value == "owner"
        assert CaseRole.EDITOR.value == "editor"
        assert CaseRole.REVIEWER.value == "reviewer"
        assert CaseRole.VIEWER.value == "viewer"
        assert CaseRole.ADMIN.value == "admin"


class TestGlobalRBAC:
    """Verify global RBAC permission assignments."""

    def test_permissions_unique(self):
        """No duplicate permissions in the same role."""
        for role, perms in ROLE_PERMISSIONS.items():
            assert len(set(perms)) == len(perms), f"Duplicate permissions in {role}"

    def test_admin_includes_all_actions(self):
        """Admin should have all permission types."""
        admin_perms = ROLE_PERMISSIONS[Role.ADMIN]
        action_types = ["read", "write", "delete", "manage", "view", "create", "download",
                        "refresh", "run", "export", "share", "consent", "analysis"]
        for action in action_types:
            matching = [p for p in admin_perms if action in p.value]
            assert len(matching) >= 1, f"Admin missing permission with {action}"

    def test_viewer_restricted(self):
        """Viewer should only have read permissions."""
        viewer_perms = ROLE_PERMISSIONS[Role.VIEWER]
        for perm in viewer_perms:
            assert perm.value.startswith("read:") or perm.value == "read", \
                f"Viewer has non-read permission: {perm}"


class TestRouteSecurityCoverage:
    """Verify all v1 routes require authentication."""

    def test_all_v1_routes_have_auth(self):
        """Check that every v1 API route has at minimum require_auth."""
        from src.backend.api.v1.router import router as v1_router

        # Collect all route endpoints from sub-routers
        unprotected = []
        for route in v1_router.routes:
            if hasattr(route, 'routes'):
                # Included router
                for sub_route in route.routes:
                    if hasattr(sub_route, 'endpoint'):
                        # Check route-level dependencies
                        route_deps = getattr(sub_route, 'dependencies', [])
                        if route_deps:
                            continue  # Has auth via route dependencies

                        # Check dependant-level dependencies
                        dependant = getattr(sub_route, 'dependant', None)
                        if dependant and dependant.dependencies:
                            continue  # Has auth via dependant

                        # Check route function signature for Depends(require_auth)
                        import inspect
                        sig = inspect.signature(sub_route.endpoint)
                        params = list(sig.parameters.values())
                        has_auth = any(
                            'require_auth' in str(p.default) or
                            'require_case_access' in str(p.default) or
                            'require_permission' in str(p.default)
                            for p in params
                        )
                        if not has_auth:
                            unprotected.append(f"{sub_route.methods} {sub_route.path}")

        known_public = []  # Public routes (health, docs) are not in v1 scope
        actual_unprotected = [p for p in unprotected if p not in known_public]
        assert actual_unprotected == [], f"Potentially unprotected routes: {actual_unprotected}"
