"""
Integration test for auth/authorization flows.
"""
from src.backend.auth.models import (
    Role, Permission, ROLE_PERMISSIONS
)


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

    def test_role_hierarchy_complete(self):
        """All roles defined in ROLE_PERMISSIONS."""
        assert len(ROLE_PERMISSIONS) == 6
        assert Role.ADMIN in ROLE_PERMISSIONS
        assert Role.VIEWER in ROLE_PERMISSIONS
        assert Role.SERVICE in ROLE_PERMISSIONS
