
"""
Integration test for auth/authorization flows.
"""
import pytest
from src.backend.auth.models import (
    User, Role, Permission, ROLE_PERMISSIONS, AuthenticationError
)
from src.backend.auth.service import AuthService

class TestAuthorizationFlow:
    def test_admin_has_all_permissions(self):
        """Admin role must have every permission."""
        admin_perms = ROLE_PERMISSIONS[Role.ADMIN]
        for perm in Permission:
            assert perm in admin_perms, f"Admin missing {perm}"

    def test_viewer_limited(self):
        """Viewer must NOT have write/delete/admin permissions."""
        viewer_perms = ROLE_PERMISSIONS[Role.VIEWER]
        assert Permission.DELETE_PATIENT not in viewer_perms
        assert Permission.MANAGE_USERS not in viewer_perms
        assert Permission.MANAGE_SETTINGS not in viewer_perms

    def test_auth_authenticate_valid(self):
        auth = AuthService()
        user = auth.authenticate("akc-dev-token-change-in-production")
        assert user is not None
        assert user.role == Role.ADMIN

    def test_auth_rejects_invalid(self):
        auth = AuthService()
        with pytest.raises(AuthenticationError):
            auth.authenticate("bad-token")

