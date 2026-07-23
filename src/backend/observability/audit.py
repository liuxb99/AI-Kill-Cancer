"""
AuditLogger — records all critical actions for audit trail.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

logger = logging.getLogger(__name__)


class AuditLog:
    """A single audit log entry."""
    def __init__(self, action: str, user_id: str, resource_type: str,
                 resource_id: str = "", details: dict | None = None,
                 ip_address: str = "", request_id: str = ""):
        self.id = str(uuid.uuid4())
        self.timestamp = datetime.now(UTC).isoformat()
        self.action = action
        self.user_id = user_id
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.details = details or {}
        self.ip_address = ip_address
        self.request_id = request_id

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "action": self.action,
            "user_id": self.user_id,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "details": self.details,
            "ip_address": self.ip_address,
            "request_id": self.request_id,
        }


class AuditLogger:
    """
    Logs critical actions for audit trail.
    Entries are immutable once created.
    """

    # Actions that must be audited
    CRITICAL_ACTIONS = {
        "login", "logout", "upload", "delete", "analysis",
        "evidence_refresh", "ranking", "reasoning",
        "report_generation", "report_download",
        "manual_override", "permission_change", "configuration_change",
    }

    def __init__(self):
        self._entries: list[AuditLog] = []
        self._max_entries = 10000

    def log(self, action: str, user_id: str, resource_type: str,
            resource_id: str = "", details: dict | None = None,
            ip_address: str = "", request_id: str = "") -> AuditLog:
        """Create and store an audit log entry."""
        entry = AuditLog(
            action=action, user_id=user_id,
            resource_type=resource_type, resource_id=resource_id,
            details=details, ip_address=ip_address, request_id=request_id,
        )
        self._entries.append(entry)

        # Also log to system logger
        logger.info("AUDIT: %s by %s on %s/%s", action, user_id, resource_type, resource_id)

        # Prune if needed
        if len(self._entries) > self._max_entries:
            self._entries = self._entries[-self._max_entries:]

        return entry

    def get_recent(self, limit: int = 100) -> list[dict]:
        """Get recent audit log entries."""
        return [e.to_dict() for e in self._entries[-limit:]]

    def get_by_user(self, user_id: str, limit: int = 100) -> list[dict]:
        """Get audit entries for a specific user."""
        user_entries = [e for e in self._entries if e.user_id == user_id]
        return [e.to_dict() for e in user_entries[-limit:]]

    def get_by_action(self, action: str, limit: int = 100) -> list[dict]:
        """Get audit entries of a specific action type."""
        action_entries = [e for e in self._entries if e.action == action]
        return [e.to_dict() for e in action_entries[-limit:]]


# Global audit logger
_audit_logger: AuditLogger | None = None


def get_audit_logger() -> AuditLogger:
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger
