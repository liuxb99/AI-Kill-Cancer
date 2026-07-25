"""phase3b_clinical_decision_tables

Revision ID: 018
Revises: 017
Create Date: 2026-07-23

Adds Phase 3B Clinical Decision Layer tables:
- domain_clinical_decisions
- domain_clinical_decision_traces
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "018"
down_revision: Union[str, None] = "017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ─── domain_clinical_decisions ──────────────────────────────────────────
    op.create_table(
        "domain_clinical_decisions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("decision_id", sa.String(64), unique=True, nullable=False, index=True),
        sa.Column("patient_id", sa.String(36), sa.ForeignKey("domain_patients.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("recommendation_id", sa.String(36), sa.ForeignKey("domain_recommendations.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("decision_type", sa.String(64), nullable=False),
        sa.Column("reason", sa.Text, nullable=False),
        sa.Column("evidence_summary", sa.JSON, nullable=True),
        sa.Column("confidence", sa.String(32), nullable=False),
        sa.Column("alternatives", sa.JSON, nullable=True),
        sa.Column("contraindications", sa.JSON, nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("domain_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    # ─── domain_clinical_decision_traces ────────────────────────────────────
    op.create_table(
        "domain_clinical_decision_traces",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("trace_id", sa.String(64), unique=True, nullable=False, index=True),
        sa.Column("clinical_decision_id", sa.String(36), sa.ForeignKey("domain_clinical_decisions.id", ondelete="CASCADE"), nullable=True, index=True),
        sa.Column("recommendation_id", sa.String(36), sa.ForeignKey("domain_recommendations.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("step_order", sa.Integer, nullable=False),
        sa.Column("step_type", sa.String(64), nullable=False),
        sa.Column("input_summary", sa.JSON, nullable=True),
        sa.Column("output_summary", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("domain_clinical_decision_traces")
    op.drop_table("domain_clinical_decisions")
