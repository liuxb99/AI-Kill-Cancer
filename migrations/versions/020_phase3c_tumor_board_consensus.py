"""phase3c_tumor_board_consensus

Revision ID: 020
Revises: 019
Create Date: 2026-07-26

Adds Phase 3C Tumor Board Consensus Layer tables:
- domain_tumor_board_consensus
- domain_tumor_board_opinions
- domain_tumor_board_consensus_traces
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


class IrreversibleMigrationError(Exception):
    """Raised when a migration cannot be reversed safely.

    This class was removed from alembic.util in Alembic ≥1.9.
    We define it locally to keep the same semantic contract.
    """

# revision identifiers, used by Alembic.
revision: str = "020"
down_revision: Union[str, None] = "019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ─── domain_tumor_board_consensus ───────────────────────────────────────────
    op.create_table(
        "domain_tumor_board_consensus",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("consensus_id", sa.String(64), unique=True, nullable=False, index=True),
        sa.Column("patient_id", sa.String(36), sa.ForeignKey("domain_patients.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("recommendation_id", sa.String(36), sa.ForeignKey("domain_recommendations.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("clinical_decision_id", sa.String(36), sa.ForeignKey("domain_clinical_decisions.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("consensus_status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("consensus_score", sa.Float, nullable=True),
        sa.Column("final_recommendation", sa.Text, nullable=True),
        sa.Column("supporting_rationale", sa.Text, nullable=True),
        sa.Column("dissenting_opinions", sa.JSON, nullable=True),
        sa.Column("unresolved_questions", sa.JSON, nullable=True),
        sa.Column("required_follow_up", sa.JSON, nullable=True),
        sa.Column("participating_specialties", sa.JSON, nullable=True),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("domain_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    # ─── domain_tumor_board_opinions ────────────────────────────────────────────
    op.create_table(
        "domain_tumor_board_opinions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("consensus_id", sa.String(36), sa.ForeignKey("domain_tumor_board_consensus.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("specialty", sa.String(64), nullable=False),
        sa.Column("participant_id", sa.String(128), nullable=True),
        sa.Column("position", sa.String(32), nullable=False),
        sa.Column("confidence", sa.Float, nullable=False, server_default="0.5"),
        sa.Column("rationale", sa.Text, nullable=True),
        sa.Column("supporting_evidence", sa.JSON, nullable=True),
        sa.Column("contraindications", sa.JSON, nullable=True),
        sa.Column("preferred_option", sa.Text, nullable=True),
        sa.Column("alternative_option", sa.Text, nullable=True),
        sa.Column("requires_more_information", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    # ─── domain_tumor_board_consensus_traces ────────────────────────────────────
    op.create_table(
        "domain_tumor_board_consensus_traces",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("trace_id", sa.String(64), nullable=False, index=True),
        sa.Column("consensus_id", sa.String(36), sa.ForeignKey("domain_tumor_board_consensus.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("step_order", sa.Integer, nullable=False),
        sa.Column("step_type", sa.String(64), nullable=False),
        sa.Column("input_summary", sa.JSON, nullable=True),
        sa.Column("output_summary", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("trace_id", "step_order", name="uq_tbc_trace_step"),
    )


def downgrade() -> None:
    bind = op.get_bind()

    # Check each table for existing data
    for table_name in (
        "domain_tumor_board_consensus_traces",
        "domain_tumor_board_opinions",
        "domain_tumor_board_consensus",
    ):
        count = bind.execute(sa.text(f"SELECT COUNT(*) FROM {table_name}")).scalar()
        if count > 0:
            raise IrreversibleMigrationError(
                f"Cannot downgrade Migration 020. "
                f"Table '{table_name}' has {count} row(s). "
                "Downgrade would destroy persisted consensus records."
            )

    # All tables are empty — safe to drop
    op.drop_table("domain_tumor_board_consensus_traces")
    op.drop_table("domain_tumor_board_opinions")
    op.drop_table("domain_tumor_board_consensus")
