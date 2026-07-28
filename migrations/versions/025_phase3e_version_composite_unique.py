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
    bind = op.get_bind()
    return bind.dialect.name == "sqlite"


def _drop_pg_unique_constraint(table: str, column: str) -> None:
    """Drop a single-column unique constraint on PostgreSQL with dynamic name lookup."""
    op.execute(f"""
        DO $$
        DECLARE
            con_name text;
        BEGIN
            FOR con_name IN
                SELECT con.conname
                FROM pg_constraint con
                JOIN pg_class rel ON rel.oid = con.conrelid
                WHERE rel.relname = '{table}'
                AND con.contype = 'u'
                AND con.conkey = ARRAY(
                    SELECT attnum FROM pg_attribute
                    WHERE attrelid = rel.oid AND attname = '{column}'
                )
            LOOP
                EXECUTE format('ALTER TABLE {table} DROP CONSTRAINT %%I', con_name);
            END LOOP;
        END;
        $$;
    """)


def upgrade() -> None:
    # ─── domain_treatment_plans ─────────────────────────────────────────
    if _is_sqlite():
        with op.batch_alter_table("domain_treatment_plans", recreate="always") as batch_op:
            batch_op.drop_index("ix_domain_treatment_plans_plan_id")
            batch_op.alter_column("plan_id", existing_type=sa.String(64), nullable=False)
            batch_op.drop_constraint("uq_treatment_plan_version", type_="unique")
            batch_op.create_unique_constraint("uq_plan_id_version", ["plan_id", "version"])
            batch_op.add_column(sa.Column("previous_version_id", sa.String(36), nullable=True))
            batch_op.add_column(sa.Column("supersedes_version_id", sa.String(36), nullable=True))
            batch_op.create_index("ix_domain_treatment_plans_prev_ver", ["previous_version_id"])
            batch_op.create_index("ix_domain_treatment_plans_sup_ver", ["supersedes_version_id"])
            batch_op.create_foreign_key(
                "fk_prev_version", "domain_treatment_plans",
                ["previous_version_id"], ["id"], ondelete="SET NULL",
            )
            batch_op.create_foreign_key(
                "fk_supersedes_version", "domain_treatment_plans",
                ["supersedes_version_id"], ["id"], ondelete="SET NULL",
            )
    else:
        # PostgreSQL: drop old single-column unique constraint dynamically
        _drop_pg_unique_constraint("domain_treatment_plans", "plan_id")
        # Also drop the composite constraint from 023 if it exists (renamed version)
        op.execute(
            "ALTER TABLE domain_treatment_plans "
            "DROP CONSTRAINT IF EXISTS uq_treatment_plan_version"
        )
        # Add version link columns
        op.add_column("domain_treatment_plans",
                       sa.Column("previous_version_id", sa.String(36), nullable=True))
        op.add_column("domain_treatment_plans",
                       sa.Column("supersedes_version_id", sa.String(36), nullable=True))
        # Add indexes
        op.create_index("ix_domain_treatment_plans_prev_ver", "domain_treatment_plans",
                        ["previous_version_id"])
        op.create_index("ix_domain_treatment_plans_sup_ver", "domain_treatment_plans",
                        ["supersedes_version_id"])
        # Add composite unique
        op.create_unique_constraint("uq_plan_id_version", "domain_treatment_plans",
                                     ["plan_id", "version"])
        # Add FK constraints
        op.create_foreign_key(
            "fk_prev_version", "domain_treatment_plans", "domain_treatment_plans",
            ["previous_version_id"], ["id"], ondelete="SET NULL",
        )
        op.create_foreign_key(
            "fk_supersedes_version", "domain_treatment_plans", "domain_treatment_plans",
            ["supersedes_version_id"], ["id"], ondelete="SET NULL",
        )

    # ─── domain_treatment_plan_traces ───────────────────────────────────
    if _is_sqlite():
        with op.batch_alter_table("domain_treatment_plan_traces", recreate="always") as batch_op:
            batch_op.drop_index("ix_domain_treatment_plan_traces_trace_id")
            batch_op.alter_column("trace_id", existing_type=sa.String(64), nullable=False)
            batch_op.create_unique_constraint("uq_trace_step", ["trace_id", "step_order"])
    else:
        _drop_pg_unique_constraint("domain_treatment_plan_traces", "trace_id")
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
        op.drop_constraint("fk_supersedes_version", "domain_treatment_plans", type_="foreignkey")
        op.drop_constraint("fk_prev_version", "domain_treatment_plans", type_="foreignkey")
        op.drop_index("ix_domain_treatment_plans_sup_ver", table_name="domain_treatment_plans")
        op.drop_index("ix_domain_treatment_plans_prev_ver", table_name="domain_treatment_plans")
        op.drop_column("domain_treatment_plans", "supersedes_version_id")
        op.drop_column("domain_treatment_plans", "previous_version_id")
        op.drop_constraint("uq_plan_id_version", "domain_treatment_plans", type_="unique")

    # ─── domain_treatment_plan_traces ───────────────────────────────────
    if _is_sqlite():
        with op.batch_alter_table("domain_treatment_plan_traces", recreate="always") as batch_op:
            batch_op.drop_constraint("uq_trace_step", type_="unique")
            batch_op.alter_column("trace_id", existing_type=sa.String(64), nullable=False)
            batch_op.create_index("ix_domain_treatment_plan_traces_trace_id",
                                  ["trace_id"], unique=True)
    else:
        op.drop_constraint("uq_trace_step", "domain_treatment_plan_traces", type_="unique")
