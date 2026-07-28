"""phase3e_treatment_plan_alternatives

Revision ID: 024
Revises: 023
Create Date: 2026-08-01

Adds alternative_options JSON column to domain_treatment_plans
so that engine-generated treatment plan alternatives are persisted.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "024"
down_revision: Union[str, None] = "023"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "domain_treatment_plans",
        sa.Column("alternative_options", sa.JSON, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("domain_treatment_plans", "alternative_options")
