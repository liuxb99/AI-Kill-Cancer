"""clinical_reasoning

Revision ID: 010
Revises: 009
Create Date: 2026-07-20

Adds reasoning tables:
- domain_reasoning_runs
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "domain_reasoning_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("case_id", sa.String(36), nullable=True, index=True),
        sa.Column("variant_id", sa.String(36), nullable=True, index=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("provider", sa.String(64), nullable=True),
        sa.Column("model", sa.String(128), nullable=True),
        sa.Column("model_version", sa.String(64), nullable=True),
        sa.Column("prompt_template_version", sa.String(32), nullable=True),
        sa.Column("temperature", sa.Float, nullable=True),
        sa.Column("seed", sa.Integer, nullable=True),
        sa.Column("input_hash", sa.String(64), nullable=True),
        sa.Column("output_hash", sa.String(64), nullable=True),
        sa.Column("context_hash", sa.String(64), nullable=True),
        sa.Column("token_usage", sa.JSON, default=dict),
        sa.Column("latency_ms", sa.Float, nullable=True),
        sa.Column("git_commit", sa.String(64), nullable=True),
        sa.Column("reasoning_data", sa.JSON, nullable=True),
        sa.Column("validation_result", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("domain_reasoning_runs")
