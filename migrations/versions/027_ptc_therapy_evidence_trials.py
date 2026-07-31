"""Add PTC therapy, evidence, and clinical-trial knowledge tables.

Revision ID: 027
Revises: 026
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "027"
down_revision: Union[str, None] = "026"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "domain_ptc_therapies",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("therapy_key", sa.String(160), nullable=False),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("generic_name", sa.String(256), nullable=True),
        sa.Column("therapy_type", sa.String(64), nullable=False, server_default="drug"),
        sa.Column("approval_status", sa.String(128), nullable=True),
        sa.Column("indications", sa.JSON(), nullable=False),
        sa.Column("mechanism", sa.Text(), nullable=True),
        sa.Column("dosage_and_administration", sa.Text(), nullable=True),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.Column("source_name", sa.String(64), nullable=False),
        sa.Column("source_record_id", sa.String(256), nullable=False),
        sa.Column("source_url", sa.String(1024), nullable=True),
        sa.Column("source_version", sa.String(64), nullable=True),
        sa.Column("retrieved_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("therapy_key", name="uq_ptc_therapy_key"),
        sa.UniqueConstraint("source_name", "source_record_id", name="uq_ptc_therapy_source"),
    )
    op.create_index("ix_ptc_therapy_name", "domain_ptc_therapies", ["name"])

    op.create_table(
        "domain_ptc_therapy_targets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("therapy_id", sa.String(36), sa.ForeignKey("domain_ptc_therapies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("gene_symbol", sa.String(32), nullable=False),
        sa.Column("variant", sa.String(128), nullable=True),
        sa.Column("target_type", sa.String(64), nullable=True),
        sa.Column("interaction_type", sa.String(128), nullable=True),
        sa.Column("evidence_level", sa.String(64), nullable=True),
        sa.Column("source_record_id", sa.String(256), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("therapy_id", "gene_symbol", "variant", name="uq_ptc_therapy_target"),
    )
    op.create_index("ix_ptc_target_gene", "domain_ptc_therapy_targets", ["gene_symbol"])

    op.create_table(
        "domain_ptc_clinical_trials",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("nct_id", sa.String(32), nullable=False),
        sa.Column("brief_title", sa.String(1024), nullable=False),
        sa.Column("official_title", sa.Text(), nullable=True),
        sa.Column("overall_status", sa.String(64), nullable=True),
        sa.Column("phases", sa.JSON(), nullable=False),
        sa.Column("study_type", sa.String(64), nullable=True),
        sa.Column("conditions", sa.JSON(), nullable=False),
        sa.Column("interventions", sa.JSON(), nullable=False),
        sa.Column("eligibility", sa.Text(), nullable=True),
        sa.Column("enrollment", sa.Integer(), nullable=True),
        sa.Column("locations", sa.JSON(), nullable=False),
        sa.Column("start_date", sa.String(32), nullable=True),
        sa.Column("completion_date", sa.String(32), nullable=True),
        sa.Column("source_url", sa.String(1024), nullable=True),
        sa.Column("source_version", sa.String(64), nullable=True),
        sa.Column("last_update_posted", sa.String(32), nullable=True),
        sa.Column("retrieved_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("nct_id", name="uq_ptc_trial_nct"),
    )
    op.create_index("ix_ptc_trial_status", "domain_ptc_clinical_trials", ["overall_status"])

    op.create_table(
        "domain_ptc_evidence_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("evidence_key", sa.String(256), nullable=False),
        sa.Column("source_name", sa.String(64), nullable=False),
        sa.Column("source_record_id", sa.String(256), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("evidence_type", sa.String(64), nullable=False),
        sa.Column("evidence_level", sa.String(64), nullable=True),
        sa.Column("direction", sa.String(32), nullable=True),
        sa.Column("gene_symbol", sa.String(32), nullable=True),
        sa.Column("variant", sa.String(128), nullable=True),
        sa.Column("disease", sa.String(128), nullable=False, server_default="papillary_thyroid_carcinoma"),
        sa.Column("therapy_id", sa.String(36), sa.ForeignKey("domain_ptc_therapies.id", ondelete="SET NULL"), nullable=True),
        sa.Column("clinical_trial_id", sa.String(36), sa.ForeignKey("domain_ptc_clinical_trials.id", ondelete="SET NULL"), nullable=True),
        sa.Column("publication_id", sa.String(64), nullable=True),
        sa.Column("citation", sa.Text(), nullable=True),
        sa.Column("source_url", sa.String(1024), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("evidence_key", name="uq_ptc_evidence_key"),
        sa.UniqueConstraint("source_name", "source_record_id", name="uq_ptc_evidence_source"),
    )
    op.create_index("ix_ptc_evidence_gene", "domain_ptc_evidence_records", ["gene_symbol"])
    op.create_index("ix_ptc_evidence_level", "domain_ptc_evidence_records", ["evidence_level"])


def downgrade() -> None:
    op.drop_table("domain_ptc_evidence_records")
    op.drop_table("domain_ptc_clinical_trials")
    op.drop_table("domain_ptc_therapy_targets")
    op.drop_table("domain_ptc_therapies")
