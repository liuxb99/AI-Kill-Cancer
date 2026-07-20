"""phase2a_full_file_validation

Revision ID: 005
Revises: 004
Create Date: 2026-07-20

Adds duplicate blob sharing field:
- domain_uploaded_files: duplicate_of_upload_id
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("domain_uploaded_files",
        sa.Column("duplicate_of_upload_id", sa.String(36), nullable=True,
                  comment="Points to original upload if this is a blob duplicate"))


def downgrade() -> None:
    op.drop_column("domain_uploaded_files", "duplicate_of_upload_id")
