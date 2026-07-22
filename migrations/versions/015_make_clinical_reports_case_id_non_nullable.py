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
    # Make case_id non-nullable — SQLite does not support ALTER COLUMN SET NOT NULL
    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        op.alter_column(
            "domain_clinical_reports",
            "case_id",
            existing_type=sa.String(36),
            nullable=False,
        )
    else:
        # For SQLite, recreate the table with NOT NULL constraint
        op.execute(sa.text(
            "CREATE TABLE domain_clinical_reports_new ("
            "  id VARCHAR(36) NOT NULL PRIMARY KEY,"
            "  case_id VARCHAR(36) NOT NULL,"
            "  version VARCHAR(32) NOT NULL DEFAULT '1.0.0',"
            "  supersedes_report_id VARCHAR(36),"
            "  status VARCHAR(32) NOT NULL DEFAULT 'draft',"
            "  report_data JSON NOT NULL,"
            "  html_content TEXT,"
            "  fhir_data JSON,"
            "  created_at DATETIME NOT NULL,"
            "  updated_at DATETIME NOT NULL"
            ")"
        ))
        op.execute(sa.text(
            "INSERT INTO domain_clinical_reports_new "
            "SELECT * FROM domain_clinical_reports"
        ))
        op.execute(sa.text("DROP TABLE domain_clinical_reports"))
        op.execute(sa.text("ALTER TABLE domain_clinical_reports_new RENAME TO domain_clinical_reports"))


def downgrade() -> None:
    # SQLite does not support ALTER COLUMN — use batch mode for cross-dialect compatibility
    with op.batch_alter_table("domain_clinical_reports") as batch_op:
        batch_op.alter_column(
            "case_id",
            existing_type=sa.String(36),
            nullable=True,
        )
