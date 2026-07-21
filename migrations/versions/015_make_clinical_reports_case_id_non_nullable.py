"""make_clinical_reports_case_id_non_nullable

Revision ID: 015
Revises: 014
Create Date: 2026-07-21

Makes ClinicalReportModel.case_id non-nullable (fail-closed security).
Existing NULL entries are assigned a sentinel UUID.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "015"
down_revision: Union[str, None] = "014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SENTINEL_CASE_ID = "00000000-0000-0000-0000-000000000000"


def upgrade() -> None:
    # Update existing NULL case_id rows to sentinel
    op.execute(
        sa.text(
            "UPDATE domain_clinical_reports SET case_id = :sentinel WHERE case_id IS NULL"
        ).bindparams(sentinel=SENTINEL_CASE_ID)
    )
    # Make case_id non-nullable
    op.alter_column(
        "domain_clinical_reports",
        "case_id",
        existing_type=sa.String(36),
        nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "domain_clinical_reports",
        "case_id",
        existing_type=sa.String(36),
        nullable=True,
    )
