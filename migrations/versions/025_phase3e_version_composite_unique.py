"""phase3e_version_composite_unique

Revision ID: 025
Revises: 024
Create Date: 2026-07-28

Changes:
1. domain_treatment_plans: plan_id unique=True → UNIQUE(plan_id, version)
2. domain_treatment_plan_traces: trace_id unique=True → UNIQUE(trace_id, step_order)
3. Add previous_version_id and supersedes_version_id columns (FK self-reference, nullable)
4. Preserve existing data
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "025"
down_revision: Union[str, None] = "024"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _is_sqlite() -> bool:
    """Check if the current database backend is SQLite."""
    bind = op.get_bind()
    return bind.dialect.name == "sqlite"


def upgrade() -> None:
    # ─── domain_treatment_plans ─────────────────────────────────────────
    if _is_sqlite():
        # SQLite: use batch_alter_table with recreate (only way to change constraints)
        with op.batch_alter_table("domain_treatment_plans", recreate="always") as batch_op:
            # Drop the unique index created by unique=True on plan_id in 023
            batch_op.drop_index("ix_domain_treatment_plans_plan_id")
            batch_op.alter_column("plan_id", existing_type=sa.String(64), nullable=False)
            # Drop old composite unique constraint from 023 (avoid duplication)
            batch_op.drop_constraint("uq_treatment_plan_version", type_="unique")
            # Add composite unique
            batch_op.create_unique_constraint("uq_plan_id_version", ["plan_id", "version"])
            # Add version link columns
            batch_op.add_column(sa.Column("previous_version_id", sa.String(36), nullable=True))
            batch_op.add_column(sa.Column("supersedes_version_id", sa.String(36), nullable=True))
            # Add indexes for version link columns
            batch_op.create_index("ix_domain_treatment_plans_prev_ver", ["previous_version_id"])
            batch_op.create_index("ix_domain_treatment_plans_sup_ver", ["supersedes_version_id"])
            # Add FK constraints (self-referencing)
            batch_op.create_foreign_key(
                "fk_prev_version", "domain_treatment_plans",
                ["previous_version_id"], ["id"], ondelete="SET NULL",
            )
            batch_op.create_foreign_key(
                "fk_supersedes_version", "domain_treatment_plans",
                ["supersedes_version_id"], ["id"], ondelete="SET NULL",
            )
    else:
        # PostgreSQL: direct ALTER TABLE (supports DROP CONSTRAINT)
        # 1. Drop the unique constraint created by unique=True on plan_id in 023
        op.drop_constraint("domain_treatment_plans_plan_id_key", "domain_treatment_plans", type_="unique")
        # 2. Add composite unique
        op.create_unique_constraint("uq_plan_id_version", "domain_treatment_plans",
                                     ["plan_id", "version"])
        # 3. Add version link columns
        op.add_column("domain_treatment_plans",
                       sa.Column("previous_version_id", sa.String(36), nullable=True))
        op.add_column("domain_treatment_plans",
                       sa.Column("supersedes_version_id", sa.String(36), nullable=True))
        # 4. Add indexes
        op.create_index("ix_domain_treatment_plans_prev_ver", "domain_treatment_plans",
                        ["previous_version_id"])
        op.create_index("ix_domain_treatment_plans_sup_ver", "domain_treatment_plans",
                        ["supersedes_version_id"])
        # 5. Add FK constraints (need to wait until batch mode sets up the table;
        #    use direct execute because self-referencing FK needs the table to exist)
        op.create_foreign_key(
            "fk_prev_version", "domain_treatment_plans",
            ["previous_version_id"], ["id"], ondelete="SET NULL",
        )
        op.create_foreign_key(
            "fk_supersedes_version", "domain_treatment_plans",
            ["supersedes_version_id"], ["id"], ondelete="SET NULL",
        )
        # 6. Drop old composite unique from 023 (uq_treatment_plan_version) if it exists
        try:
            op.drop_constraint("uq_treatment_plan_version", "domain_treatment_plans",
                               type_="unique")
        except Exception:
            pass  # may not exist on PostgreSQL if 023 created differently

    # ─── domain_treatment_plan_traces ───────────────────────────────────
    if _is_sqlite():
        with op.batch_alter_table("domain_treatment_plan_traces", recreate="always") as batch_op:
            batch_op.drop_index("ix_domain_treatment_plan_traces_trace_id")
            batch_op.alter_column("trace_id", existing_type=sa.String(64), nullable=False)
            batch_op.create_unique_constraint("uq_trace_step", ["trace_id", "step_order"])
    else:
        # PostgreSQL: direct ALTER
        op.drop_constraint("domain_treatment_plan_traces_trace_id_key", "domain_treatment_plan_traces", type_="unique")
        op.create_unique_constraint("uq_trace_step", "domain_treatment_plan_traces",
                                     ["trace_id", "step_order"])


def downgrade() -> None:
    # ─── domain_treatment_plans ─────────────────────────────────────────
    if _is_sqlite():
        with op.batch_alter_table("domain_treatment_plans", recreate="always") as batch_op:
            batch_op.drop_constraint("fk_supersedes_version", type_="foreignkey")
            batch_op.drop_constraint("fk_prev_version", type_="foreignkey")
            batch_op.drop_index("ix_domain_treatment_plans_sup_ver")
            batch_op.drop_index("ix_domain_treatment_plans_prev_ver")
            batch_op.drop_column("supersedes_version_id")
            batch_op.drop_column("previous_version_id")
            batch_op.drop_constraint("uq_plan_id_version", type_="unique")
            batch_op.alter_column("plan_id", existing_type=sa.String(64), nullable=False)
            batch_op.create_index("ix_domain_treatment_plans_plan_id", ["plan_id"], unique=True)
    else:
        # PostgreSQL: reverse order
        op.drop_constraint("fk_supersedes_version", "domain_treatment_plans", type_="foreignkey")
        op.drop_constraint("fk_prev_version", "domain_treatment_plans", type_="foreignkey")
        op.drop_index("ix_domain_treatment_plans_sup_ver")
        op.drop_index("ix_domain_treatment_plans_prev_ver")
        op.drop_column("domain_treatment_plans", "supersedes_version_id")
        op.drop_column("domain_treatment_plans", "previous_version_id")
        op.drop_constraint("uq_plan_id_version", "domain_treatment_plans", type_="unique")
        # Restore single-column unique on plan_id
        op.create_unique_constraint("domain_treatment_plans_plan_id_key",
                                    "domain_treatment_plans", ["plan_id"])

    # ─── domain_treatment_plan_traces ───────────────────────────────────
    if _is_sqlite():
        with op.batch_alter_table("domain_treatment_plan_traces", recreate="always") as batch_op:
            batch_op.drop_constraint("uq_trace_step", type_="unique")
            batch_op.alter_column("trace_id", existing_type=sa.String(64), nullable=False)
            batch_op.create_index("ix_domain_treatment_plan_traces_trace_id",
                                  ["trace_id"], unique=True)
    else:
        op.drop_constraint("uq_trace_step", "domain_treatment_plan_traces", type_="unique")
        op.create_unique_constraint("domain_treatment_plan_traces_trace_id_key",
                                    "domain_treatment_plan_traces", ["trace_id"])
