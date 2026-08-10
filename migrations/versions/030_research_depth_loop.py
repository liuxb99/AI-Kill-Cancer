"""Add persistent research-depth hypothesis, run, and event tables.

Revision ID: 030_research_depth_loop
Revises: 029_ptc_evidence_unique
"""

import sqlalchemy as sa
from alembic import op

revision = "030_research_depth_loop"
down_revision = "029_ptc_evidence_unique"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "domain_research_hypotheses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("hypothesis_key", sa.String(length=256), nullable=False),
        sa.Column("gene_symbol", sa.String(length=32), nullable=False),
        sa.Column("protein_change", sa.String(length=128), nullable=True),
        sa.Column("hypothesis_type", sa.String(length=64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="open"),
        sa.Column("claim", sa.Text(), nullable=False),
        sa.Column("rationale", sa.JSON(), nullable=False),
        sa.Column("supporting_observations", sa.JSON(), nullable=False),
        sa.Column("counter_evidence", sa.JSON(), nullable=False),
        sa.Column("uncertainties", sa.JSON(), nullable=False),
        sa.Column("falsification_criteria", sa.Text(), nullable=False),
        sa.Column("next_data_needed", sa.JSON(), nullable=False),
        sa.Column("input_fingerprint", sa.String(length=128), nullable=False),
        sa.Column("clinical_use", sa.String(length=8), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("hypothesis_key", "version", name="uq_research_hypothesis_version"),
    )
    op.create_index("ix_research_hypothesis_key", "domain_research_hypotheses", ["hypothesis_key"])
    op.create_index("ix_research_hypothesis_gene", "domain_research_hypotheses", ["gene_symbol"])
    op.create_index("ix_research_hypothesis_type", "domain_research_hypotheses", ["hypothesis_type"])
    op.create_index("ix_research_hypothesis_status", "domain_research_hypotheses", ["status"])
    op.create_index("ix_research_hypothesis_fingerprint", "domain_research_hypotheses", ["input_fingerprint"])

    op.create_table(
        "domain_research_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("run_key", sa.String(length=128), nullable=False),
        sa.Column("gene_symbol", sa.String(length=32), nullable=False),
        sa.Column("protein_change", sa.String(length=128), nullable=True),
        sa.Column("input_fingerprint", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="completed"),
        sa.Column("trace", sa.JSON(), nullable=False),
        sa.Column("result_summary", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_key"),
    )
    op.create_index("ix_research_run_key", "domain_research_runs", ["run_key"])
    op.create_index("ix_research_run_gene", "domain_research_runs", ["gene_symbol"])
    op.create_index("ix_research_run_fingerprint", "domain_research_runs", ["input_fingerprint"])
    op.create_index("ix_research_run_status", "domain_research_runs", ["status"])

    op.create_table(
        "domain_research_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_key", sa.String(length=256), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("gene_symbol", sa.String(length=32), nullable=True),
        sa.Column("hypothesis_id", sa.Uuid(), nullable=True),
        sa.Column("run_id", sa.Uuid(), nullable=True),
        sa.Column("observed_at", sa.DateTime(), nullable=False),
        sa.Column("date_semantics", sa.String(length=32), nullable=False, server_default="generated_at"),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("source_id", sa.String(length=256), nullable=True),
        sa.Column("provenance", sa.JSON(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["hypothesis_id"], ["domain_research_hypotheses.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["run_id"], ["domain_research_runs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_key"),
    )
    op.create_index("ix_research_event_key", "domain_research_events", ["event_key"])
    op.create_index("ix_research_event_type", "domain_research_events", ["event_type"])
    op.create_index("ix_research_event_gene", "domain_research_events", ["gene_symbol"])
    op.create_index("ix_research_event_hypothesis", "domain_research_events", ["hypothesis_id"])
    op.create_index("ix_research_event_run", "domain_research_events", ["run_id"])
    op.create_index("ix_research_event_observed", "domain_research_events", ["observed_at"])


def downgrade() -> None:
    op.drop_table("domain_research_events")
    op.drop_table("domain_research_runs")
    op.drop_table("domain_research_hypotheses")
