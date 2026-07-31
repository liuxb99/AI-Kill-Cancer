"""PTC research data foundation.

Revision ID: 026
Revises: 025
Create Date: 2026-07-31
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "026"
down_revision: Union[str, None] = "025"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "domain_ptc_research_cases",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("case_id", sa.String(128), nullable=False),
        sa.Column("source_dataset", sa.String(64), nullable=False),
        sa.Column("source_project", sa.String(64), nullable=False),
        sa.Column("disease", sa.String(128), nullable=False),
        sa.Column("sex", sa.String(32), nullable=True),
        sa.Column("age_range", sa.String(32), nullable=True),
        sa.Column("pathologic_stage", sa.String(64), nullable=True),
        sa.Column("t_status", sa.String(32), nullable=True),
        sa.Column("n_status", sa.String(32), nullable=True),
        sa.Column("m_status", sa.String(32), nullable=True),
        sa.Column("vital_status", sa.String(32), nullable=True),
        sa.Column("days_to_last_follow_up", sa.Integer(), nullable=True),
        sa.Column("days_to_death", sa.Integer(), nullable=True),
        sa.Column("source_record_id", sa.String(256), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("source_dataset", "case_id", name="uq_ptc_case_source_id"),
    )
    op.create_index("ix_ptc_cases_case_id", "domain_ptc_research_cases", ["case_id"])
    op.create_index("ix_ptc_cases_dataset", "domain_ptc_research_cases", ["source_dataset"])
    op.create_index("ix_ptc_cases_disease", "domain_ptc_research_cases", ["disease"])

    op.create_table(
        "domain_ptc_variants",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("variant_id", sa.String(256), nullable=False),
        sa.Column("research_case_id", sa.String(36), nullable=False),
        sa.Column("case_id", sa.String(128), nullable=False),
        sa.Column("source_dataset", sa.String(64), nullable=False),
        sa.Column("gene", sa.String(64), nullable=False),
        sa.Column("chromosome", sa.String(32), nullable=True),
        sa.Column("position", sa.Integer(), nullable=True),
        sa.Column("reference", sa.Text(), nullable=True),
        sa.Column("alternate", sa.Text(), nullable=True),
        sa.Column("variant_type", sa.String(64), nullable=True),
        sa.Column("classification", sa.String(128), nullable=True),
        sa.Column("protein_change", sa.String(128), nullable=True),
        sa.Column("source_record_id", sa.String(256), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["research_case_id"], ["domain_ptc_research_cases.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint("source_dataset", "variant_id", name="uq_ptc_variant_source_id"),
    )
    op.create_index("ix_ptc_variants_case", "domain_ptc_variants", ["research_case_id"])
    op.create_index("ix_ptc_variants_case_id", "domain_ptc_variants", ["case_id"])
    op.create_index("ix_ptc_variants_gene", "domain_ptc_variants", ["gene"])

    op.create_table(
        "domain_ptc_outcomes",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("outcome_id", sa.String(256), nullable=False),
        sa.Column("research_case_id", sa.String(36), nullable=False),
        sa.Column("case_id", sa.String(128), nullable=False),
        sa.Column("source_dataset", sa.String(64), nullable=False),
        sa.Column("outcome_type", sa.String(64), nullable=False),
        sa.Column("outcome_value", sa.String(256), nullable=True),
        sa.Column("observed_at", sa.DateTime(), nullable=True),
        sa.Column("source_record_id", sa.String(256), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["research_case_id"], ["domain_ptc_research_cases.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint("source_dataset", "outcome_id", name="uq_ptc_outcome_source_id"),
    )
    op.create_index("ix_ptc_outcomes_case", "domain_ptc_outcomes", ["research_case_id"])
    op.create_index("ix_ptc_outcomes_case_id", "domain_ptc_outcomes", ["case_id"])

    op.create_table(
        "domain_ptc_import_batches",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("batch_id", sa.String(64), nullable=False, unique=True),
        sa.Column("source_dataset", sa.String(64), nullable=False),
        sa.Column("source_version", sa.String(128), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("record_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("checksum", sa.String(128), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_ptc_import_batch_id", "domain_ptc_import_batches", ["batch_id"])
    op.create_index("ix_ptc_import_status", "domain_ptc_import_batches", ["status"])


def downgrade() -> None:
    op.drop_index("ix_ptc_import_status", table_name="domain_ptc_import_batches")
    op.drop_index("ix_ptc_import_batch_id", table_name="domain_ptc_import_batches")
    op.drop_table("domain_ptc_import_batches")

    op.drop_index("ix_ptc_outcomes_case_id", table_name="domain_ptc_outcomes")
    op.drop_index("ix_ptc_outcomes_case", table_name="domain_ptc_outcomes")
    op.drop_table("domain_ptc_outcomes")

    op.drop_index("ix_ptc_variants_gene", table_name="domain_ptc_variants")
    op.drop_index("ix_ptc_variants_case_id", table_name="domain_ptc_variants")
    op.drop_index("ix_ptc_variants_case", table_name="domain_ptc_variants")
    op.drop_table("domain_ptc_variants")

    op.drop_index("ix_ptc_cases_disease", table_name="domain_ptc_research_cases")
    op.drop_index("ix_ptc_cases_dataset", table_name="domain_ptc_research_cases")
    op.drop_index("ix_ptc_cases_case_id", table_name="domain_ptc_research_cases")
    op.drop_table("domain_ptc_research_cases")
