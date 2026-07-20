"""phase2a_final_security

Revision ID: 004
Revises: 003
Create Date: 2026-07-20

Adds Phase 2A final security fields:
- domain_uploaded_files: decompressed_size_bytes, analysis_eligible, quarantine_reason, retention_until
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("domain_uploaded_files",
        sa.Column("decompressed_size_bytes", sa.BigInteger, nullable=True, comment="Size after decompression"))
    op.add_column("domain_uploaded_files",
        sa.Column("analysis_eligible", sa.String(32), nullable=False, server_default="pending_validation", comment="eligible|invalid|rejected|quarantined|pending_validation"))
    op.add_column("domain_uploaded_files",
        sa.Column("quarantine_reason", sa.String(256), nullable=True, comment="Reason for quarantine/rejection"))
    op.add_column("domain_uploaded_files",
        sa.Column("retention_until", sa.DateTime, nullable=True, comment="When upload may be cleaned up"))


def downgrade() -> None:
    op.drop_column("domain_uploaded_files", "retention_until")
    op.drop_column("domain_uploaded_files", "quarantine_reason")
    op.drop_column("domain_uploaded_files", "analysis_eligible")
    op.drop_column("domain_uploaded_files", "decompressed_size_bytes")
