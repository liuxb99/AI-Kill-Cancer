"""doctor_workbench

Revision ID: 012
Revises: 011
Create Date: 2026-07-20

Adds workbench tables:
- domain_tumor_board_reviews
- domain_workbench_notes
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "012"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "domain_tumor_board_reviews",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("case_id", sa.String(36), nullable=False, index=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("reviewer_id", sa.String(64), nullable=True),
        sa.Column("reviewer_name", sa.String(128), nullable=True),
        sa.Column("decision", sa.String(32), nullable=True),
        sa.Column("comments", sa.JSON, default=list),
        sa.Column("decision_log", sa.JSON, default=list),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "domain_workbench_notes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("case_id", sa.String(36), nullable=False, index=True),
        sa.Column("user_id", sa.String(64), nullable=True),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("note_type", sa.String(32), nullable=False, server_default="general"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("domain_workbench_notes")
    op.drop_table("domain_tumor_board_reviews")
