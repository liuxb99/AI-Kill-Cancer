"""drug_ranking

Revision ID: 008
Revises: 007
Create Date: 2026-07-20

Adds drug ranking tables:
- domain_drug_rankings: persisted ranking results
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "domain_drug_rankings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("variant_id", sa.String(36), nullable=True, index=True),
        sa.Column("case_id", sa.String(36), nullable=True, index=True),
        sa.Column("gene_symbol", sa.String(32), nullable=True, index=True),
        sa.Column("disease", sa.String(256), nullable=True),
        sa.Column("ranking_data", sa.JSON, nullable=False),
        sa.Column("ranking_algorithm_version", sa.String(32), nullable=False),
        sa.Column("evidence_snapshot_id", sa.String(36), nullable=True),
        sa.Column("source_versions", sa.JSON, default=dict),
        sa.Column("git_commit", sa.String(64), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="completed"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("domain_drug_rankings")
