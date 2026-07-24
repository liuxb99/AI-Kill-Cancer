"""phase3a_recommendation_tables

Revision ID: 017
Revises: 016
Create Date: 2026-07-22

Adds Phase 3A recommendation engine tables:
- domain_recommendations
- domain_recommendation_traces
- domain_recommendation_trace_steps
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "017"
down_revision: Union[str, None] = "016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ─── domain_recommendations ─────────────────────────────────────────────
    op.create_table(
        "domain_recommendations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("recommendation_id", sa.String(64), unique=True, nullable=False, index=True),
        sa.Column("patient_id", sa.String(36), sa.ForeignKey("domain_patients.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("case_id", sa.String(36), sa.ForeignKey("domain_cancer_cases.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("trace_id", sa.String(64), nullable=True, index=True),
        sa.Column("engine_version", sa.String(32), nullable=False, server_default="1.0.0"),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("request_payload", sa.JSON, nullable=True),
        sa.Column("result_payload", sa.JSON, nullable=True),
        sa.Column("report_html", sa.Text, nullable=True),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("domain_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    # ─── domain_recommendation_traces ───────────────────────────────────────
    op.create_table(
        "domain_recommendation_traces",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("trace_id", sa.String(64), unique=True, nullable=False, index=True),
        sa.Column("recommendation_id", sa.String(36), sa.ForeignKey("domain_recommendations.id", ondelete="CASCADE"), nullable=True, index=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    # ─── domain_recommendation_trace_steps ──────────────────────────────────
    op.create_table(
        "domain_recommendation_trace_steps",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("trace_id", sa.String(36), sa.ForeignKey("domain_recommendation_traces.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("step_order", sa.Integer, nullable=False),
        sa.Column("step_type", sa.String(64), nullable=False),
        sa.Column("input_summary", sa.JSON, nullable=True),
        sa.Column("output_summary", sa.JSON, nullable=True),
        sa.Column("evidence_references", sa.JSON, nullable=True),
        sa.Column("weight", sa.Float, nullable=True),
        sa.Column("score", sa.Float, nullable=True),
        sa.Column("rank", sa.Integer, nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("domain_recommendation_trace_steps")
    op.drop_table("domain_recommendation_traces")
    op.drop_table("domain_recommendations")
