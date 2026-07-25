"""phase3b_trace_compound_unique

Revision ID: 019
Revises: 018
Create Date: 2026-07-26

Drop trace_id UNIQUE on domain_clinical_decision_traces,
add compound UNIQUE (trace_id, step_order) to support multiple
trace steps sharing the same trace_id.

Background
----------
Migration 018 defined trace_id as unique=True, but the ORM model
(ClinicalDecisionTraceModel) requires multiple rows per trace_id
(i.e. one row per step_order).  This migration drops the single-column
UNIQUE index, recreates it as a plain index, and adds a compound
UNIQUE constraint on (trace_id, step_order).
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "019"
down_revision: Union[str, None] = "018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Drop the UNIQUE index created by SQLAlchemy unique=True
    op.drop_index(
        "ix_domain_clinical_decision_traces_trace_id",
        table_name="domain_clinical_decision_traces",
    )

    # 2. Recreate the same index but without UNIQUE
    op.create_index(
        "ix_domain_clinical_decision_traces_trace_id",
        "domain_clinical_decision_traces",
        ["trace_id"],
    )

    # 3. Add compound UNIQUE index (equivalent to UNIQUE(trace_id, step_order))
    # Using unique index instead of constraint for SQLite compatibility
    op.create_index(
        "uq_trace_step",
        "domain_clinical_decision_traces",
        ["trace_id", "step_order"],
        unique=True,
    )


def downgrade() -> None:
    # 1. Drop the compound unique index
    op.drop_index(
        "uq_trace_step",
        table_name="domain_clinical_decision_traces",
    )

    # 2. Drop the plain index
    op.drop_index(
        "ix_domain_clinical_decision_traces_trace_id",
        table_name="domain_clinical_decision_traces",
    )

    # 3. Restore the UNIQUE index on trace_id
    op.create_index(
        "ix_domain_clinical_decision_traces_trace_id",
        "domain_clinical_decision_traces",
        ["trace_id"],
        unique=True,
    )
