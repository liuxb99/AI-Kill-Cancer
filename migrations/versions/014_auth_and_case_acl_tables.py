"""auth_and_case_acl_tables

Revision ID: 014
Revises: 013
Create Date: 2026-07-21

Adds production authentication and case-level ACL tables:
- domain_users
- domain_token_blacklist
- domain_case_acl
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "014"
down_revision: Union[str, None] = "013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ─── domain_users ────────────────────────────────────────────────────────
    op.create_table(
        "domain_users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("username", sa.String(64), nullable=False, unique=True, index=True),
        sa.Column("email", sa.String(256), nullable=True),
        sa.Column("password_hash", sa.String(256), nullable=False),
        sa.Column("role", sa.String(16), nullable=False, server_default="viewer"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("display_name", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    # ─── domain_token_blacklist ──────────────────────────────────────────────
    op.create_table(
        "domain_token_blacklist",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("jti", sa.String(256), nullable=False, unique=True, index=True),
        sa.Column("token_type", sa.String(16), nullable=False),
        sa.Column("expires_at", sa.DateTime, nullable=False),
        sa.Column("revoked_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    # ─── domain_case_acl ─────────────────────────────────────────────────────
    op.create_table(
        "domain_case_acl",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("case_id", sa.String(36), sa.ForeignKey("domain_cancer_cases.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("domain_users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("role", sa.String(16), nullable=False, server_default="viewer"),
        sa.Column("granted_by", sa.String(36), sa.ForeignKey("domain_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("case_id", "user_id", name="uq_case_user"),
    )


def downgrade() -> None:
    op.drop_table("domain_case_acl")
    op.drop_table("domain_token_blacklist")
    op.drop_table("domain_users")
