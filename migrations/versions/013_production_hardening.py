"""production_hardening

Revision ID: 013
Revises: 012
Create Date: 2026-07-20

Adds production hardening tables:
- domain_audit_logs
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "013"
down_revision: Union[str, None] = "012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("domain_audit_logs"):
        # Fresh creation with 013 schema
        op.create_table(
            "domain_audit_logs",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("timestamp", sa.DateTime, nullable=False),
            sa.Column("action", sa.String(64), nullable=False, index=True),
            sa.Column("user_id", sa.String(64), nullable=False, index=True),
            sa.Column("resource_type", sa.String(64), nullable=False),
            sa.Column("resource_id", sa.String(36), nullable=True),
            sa.Column("details", sa.JSON, default=dict),
            sa.Column("ip_address", sa.String(45), nullable=True),
            sa.Column("request_id", sa.String(36), nullable=True),
            sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        )
    else:
        # Table exists from migration 001 — add 013 columns if missing
        existing_cols = {c["name"] for c in inspector.get_columns("domain_audit_logs")}
        if "timestamp" not in existing_cols:
            op.add_column("domain_audit_logs", sa.Column("timestamp", sa.DateTime, nullable=True))
        if "user_id" not in existing_cols:
            op.add_column("domain_audit_logs", sa.Column("user_id", sa.String(64), nullable=True))
        if "request_id" not in existing_cols:
            op.add_column("domain_audit_logs", sa.Column("request_id", sa.String(36), nullable=True))

    # Create indices — use if_not_exists to handle SQLite idempotency
    try:
        op.create_index("ix_audit_logs_action_time", "domain_audit_logs", ["action", "timestamp"],
                         if_not_exists=True)
    except Exception:
        # Some SQLite versions don't support if_not_exists
        pass
    try:
        op.create_index("ix_audit_logs_user_time", "domain_audit_logs", ["user_id", "timestamp"],
                         if_not_exists=True)
    except Exception:
        pass


def downgrade() -> None:
    op.drop_table("domain_audit_logs")
