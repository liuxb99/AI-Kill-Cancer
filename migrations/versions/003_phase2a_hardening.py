"""phase2a_hardening

Revision ID: 003
Revises: 002
Create Date: 2026-07-20

Adds Phase 2A hardening fields to domain_uploaded_files:
- decompressed_sha256, genome_build, genome_build_confidence
- compression, record_count, validation_warnings, validation_errors
- sequencing_test_id: nullable=True
- sha256: index=True

Updates domain_analysis_runs:
- Add PARTIAL to status enum (SQLAlchemy handles via string)
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── domain_uploaded_files ─────────────────────────────────────────────
    op.add_column("domain_uploaded_files",
        sa.Column("decompressed_sha256", sa.String(64), nullable=True, comment="SHA256 of decompressed content"))
    op.add_column("domain_uploaded_files",
        sa.Column("genome_build", sa.String(32), nullable=True, comment="Detected or specified genome build"))
    op.add_column("domain_uploaded_files",
        sa.Column("genome_build_confidence", sa.String(32), nullable=True, comment="How build was determined"))
    op.add_column("domain_uploaded_files",
        sa.Column("compression", sa.String(16), nullable=True, comment="none, gzip"))
    op.add_column("domain_uploaded_files",
        sa.Column("record_count", sa.Integer, nullable=True, comment="Number of variant records"))
    op.add_column("domain_uploaded_files",
        sa.Column("validation_warnings", sa.JSON, nullable=True))
    op.add_column("domain_uploaded_files",
        sa.Column("validation_errors", sa.JSON, nullable=True))
    op.create_index("ix_domain_uploaded_files_sha256", "domain_uploaded_files", ["sha256"])

    # Make sequencing_test_id nullable
    with op.batch_alter_table("domain_uploaded_files") as batch_op:
        batch_op.alter_column("sequencing_test_id", existing_type=sa.String(36), nullable=True)

    # ── domain_analysis_runs: add data_version column ─────────────────────
    op.add_column("domain_analysis_runs",
        sa.Column("data_version", sa.String(64), nullable=True, comment="Dataset version identifier"))


def downgrade() -> None:
    # ── domain_uploaded_files ─────────────────────────────────────────────
    op.drop_index("ix_domain_uploaded_files_sha256", table_name="domain_uploaded_files")
    op.drop_column("domain_uploaded_files", "validation_errors")
    op.drop_column("domain_uploaded_files", "validation_warnings")
    op.drop_column("domain_uploaded_files", "record_count")
    op.drop_column("domain_uploaded_files", "compression")
    op.drop_column("domain_uploaded_files", "genome_build_confidence")
    op.drop_column("domain_uploaded_files", "genome_build")
    op.drop_column("domain_uploaded_files", "decompressed_sha256")
    with op.batch_alter_table("domain_uploaded_files") as batch_op:
        batch_op.alter_column("sequencing_test_id", existing_type=sa.String(36), nullable=False)

    # ── domain_analysis_runs ──────────────────────────────────────────────
    op.drop_column("domain_analysis_runs", "data_version")
