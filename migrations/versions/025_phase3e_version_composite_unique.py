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


def upgrade() -> None:
    # ═══════════════════════════════════════════════════════════════════
    # domain_treatment_plans
    # ═══════════════════════════════════════════════════════════════════
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
        # PostgreSQL: drop old unique constraints (ignore if not found)
        for con_name in [
            "domain_treatment_plans_plan_id_key",
            "uq_treatment_plan_version",
            "uq_plan_id_version",
        ]:
            op.execute(f"ALTER TABLE domain_treatment_plans DROP CONSTRAINT IF EXISTS {con_name}")

        op.add_column("domain_treatment_plans",
                       sa.Column("previous_version_id", sa.String(36), nullable=True))
        op.add_column("domain_treatment_plans",
                       sa.Column("supersedes_version_id", sa.String(36), nullable=True))
        op.execute("CREATE INDEX IF NOT EXISTS ix_domain_treatment_plans_prev_ver ON domain_treatment_plans (previous_version_id)")
        op.execute("CREATE INDEX IF NOT EXISTS ix_domain_treatment_plans_sup_ver ON domain_treatment_plans (supersedes_version_id)")
        op.execute("""
            DO $$ BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_catalog.pg_constraint
                    WHERE conname = 'uq_plan_id_version'
                      AND conrelid = 'domain_treatment_plans'::regclass
                ) THEN
                    ALTER TABLE domain_treatment_plans ADD CONSTRAINT uq_plan_id_version UNIQUE (plan_id, version);
                END IF;
            END $$;
        """)
        op.execute("""
            DO $$ BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_catalog.pg_constraint
                    WHERE conname = 'fk_prev_version'
                      AND conrelid = 'domain_treatment_plans'::regclass
                ) THEN
                    ALTER TABLE domain_treatment_plans ADD CONSTRAINT fk_prev_version
                        FOREIGN KEY (previous_version_id) REFERENCES domain_treatment_plans (id) ON DELETE SET NULL;
                END IF;
            END $$;
        """)
        op.execute("""
            DO $$ BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_catalog.pg_constraint
                    WHERE conname = 'fk_supersedes_version'
                      AND conrelid = 'domain_treatment_plans'::regclass
                ) THEN
                    ALTER TABLE domain_treatment_plans ADD CONSTRAINT fk_supersedes_version
                        FOREIGN KEY (supersedes_version_id) REFERENCES domain_treatment_plans (id) ON DELETE SET NULL;
                END IF;
            END $$;
        """)

    # ═══════════════════════════════════════════════════════════════════
    # domain_treatment_plan_traces
    # ═══════════════════════════════════════════════════════════════════
    if _is_sqlite():
        with op.batch_alter_table("domain_treatment_plan_traces", recreate="always") as batch_op:
            batch_op.drop_index("ix_domain_treatment_plan_traces_trace_id")
            batch_op.alter_column("trace_id", existing_type=sa.String(64), nullable=False)
            batch_op.create_unique_constraint("uq_trace_step", ["trace_id", "step_order"])
    else:
        # 动态查询 pg_catalog.pg_constraint 找出 UNIQUE(trace_id) 的真正 constraint 名称
        op.execute("""
            DO $$
            DECLARE
                con_name text;
            BEGIN
                SELECT con.conname INTO con_name
                FROM pg_catalog.pg_constraint con
                JOIN pg_catalog.pg_class rel ON rel.oid = con.conrelid
                WHERE rel.relname = 'domain_treatment_plan_traces'
                  AND con.contype = 'u'
                  AND con.conkey = (
                      SELECT array_agg(a.attnum ORDER BY a.attnum)
                      FROM pg_catalog.pg_attribute a
                      WHERE a.attrelid = rel.oid
                        AND a.attname = 'trace_id'
                  );
                IF con_name IS NOT NULL THEN
                    EXECUTE format(
                        'ALTER TABLE domain_treatment_plan_traces DROP CONSTRAINT %I',
                        con_name
                    );
                END IF;
            END $$;
        """)
        op.execute("""
            DO $$ BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_catalog.pg_constraint
                    WHERE conname = 'uq_trace_step'
                      AND conrelid = 'domain_treatment_plan_traces'::regclass
                ) THEN
                    ALTER TABLE domain_treatment_plan_traces ADD CONSTRAINT uq_trace_step UNIQUE (trace_id, step_order);
                END IF;
            END $$;
        """)


def downgrade() -> None:
    # ═══════════════════════════════════════════════════════════════════
    # domain_treatment_plans
    # ═══════════════════════════════════════════════════════════════════
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
        op.execute("ALTER TABLE domain_treatment_plans DROP CONSTRAINT IF EXISTS fk_supersedes_version")
        op.execute("ALTER TABLE domain_treatment_plans DROP CONSTRAINT IF EXISTS fk_prev_version")
        op.execute("DROP INDEX IF EXISTS ix_domain_treatment_plans_sup_ver")
        op.execute("DROP INDEX IF EXISTS ix_domain_treatment_plans_prev_ver")
        op.drop_column("domain_treatment_plans", "supersedes_version_id")
        op.drop_column("domain_treatment_plans", "previous_version_id")
        op.execute("ALTER TABLE domain_treatment_plans DROP CONSTRAINT IF EXISTS uq_plan_id_version")
        # 恢复 024 schema 的 UNIQUE(plan_id)
        op.execute("""
            DO $$ BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_catalog.pg_constraint
                    WHERE conname = 'domain_treatment_plans_plan_id_key'
                      AND conrelid = 'domain_treatment_plans'::regclass
                ) THEN
                    ALTER TABLE domain_treatment_plans ADD CONSTRAINT domain_treatment_plans_plan_id_key UNIQUE (plan_id);
                END IF;
            END $$;
        """)

    # ═══════════════════════════════════════════════════════════════════
    # domain_treatment_plan_traces
    # ═══════════════════════════════════════════════════════════════════
    if _is_sqlite():
        with op.batch_alter_table("domain_treatment_plan_traces", recreate="always") as batch_op:
            batch_op.drop_constraint("uq_trace_step", type_="unique")
            batch_op.alter_column("trace_id", existing_type=sa.String(64), nullable=False)
            batch_op.create_index("ix_domain_treatment_plan_traces_trace_id",
                                  ["trace_id"], unique=True)
    else:
        op.execute("ALTER TABLE domain_treatment_plan_traces DROP CONSTRAINT IF EXISTS uq_trace_step")
        # 恢复 024 schema 的 UNIQUE(trace_id)
        op.execute("""
            DO $$ BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_catalog.pg_constraint
                    WHERE conname = 'domain_treatment_plan_traces_trace_id_key'
                      AND conrelid = 'domain_treatment_plan_traces'::regclass
                ) THEN
                    ALTER TABLE domain_treatment_plan_traces ADD CONSTRAINT domain_treatment_plan_traces_trace_id_key UNIQUE (trace_id);
                END IF;
            END $$;
        """)
