"""phase3e_treatment_plan_tables

Revision ID: 023
Revises: 022
Create Date: 2026-07-29

Adds Phase 3E Treatment Plan Engine V1 tables:
- domain_treatment_plans
- domain_treatment_phases
- domain_treatment_items
- domain_treatment_monitoring
- domain_treatment_safety_rules
- domain_treatment_plan_traces
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


class IrreversibleMigrationError(Exception):
    """Raised when a migration cannot be reversed safely.

    This class was removed from alembic.util in Alembic ≥1.9.
    We define it locally to keep the same semantic contract.
    """


revision: str = "023"
down_revision: Union[str, None] = "022"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ─── domain_treatment_plans ─────────────────────────────────────────
    op.create_table(
        "domain_treatment_plans",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("plan_id", sa.String(64), nullable=False, index=True),
        sa.Column("version", sa.Integer, nullable=False, server_default=sa.text("1")),
        sa.Column("patient_id", sa.String(36), sa.ForeignKey("domain_patients.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("recommendation_id", sa.String(36), sa.ForeignKey("domain_recommendations.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("clinical_decision_id", sa.String(36), sa.ForeignKey("domain_clinical_decisions.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("consensus_id", sa.String(36), sa.ForeignKey("domain_tumor_board_consensus.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("plan_status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("plan_intent", sa.String(256), nullable=True),
        sa.Column("treatment_goals", sa.JSON, nullable=True),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("clinical_rationale", sa.Text, nullable=True),
        sa.Column("start_date", sa.DateTime, nullable=True),
        sa.Column("target_end_date", sa.DateTime, nullable=True),
        sa.Column("review_date", sa.DateTime, nullable=True),
        sa.Column("previous_plan_id", sa.String(64), nullable=True, index=True),
        sa.Column("supersedes_plan_id", sa.String(64), nullable=True, index=True),
        sa.Column("is_current", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("revision_reason", sa.Text, nullable=True),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("domain_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("approved_by", sa.String(36), sa.ForeignKey("domain_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("approved_at", sa.DateTime, nullable=True),
        sa.Column("activated_at", sa.DateTime, nullable=True),
        sa.Column("paused_at", sa.DateTime, nullable=True),
        sa.Column("completed_at", sa.DateTime, nullable=True),
        sa.Column("cancelled_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("plan_id", "version", name="uq_plan_id_version"),
    )

    # ─── domain_treatment_phases ────────────────────────────────────────
    op.create_table(
        "domain_treatment_phases",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("phase_id", sa.String(64), unique=True, nullable=False, index=True),
        sa.Column("plan_id", sa.String(36), sa.ForeignKey("domain_treatment_plans.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("phase_order", sa.Integer, nullable=False),
        sa.Column("phase_type", sa.String(32), nullable=False),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("planned_start", sa.DateTime, nullable=True),
        sa.Column("planned_end", sa.DateTime, nullable=True),
        sa.Column("duration_days", sa.Integer, nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="planned"),
        sa.Column("entry_criteria", sa.JSON, nullable=True),
        sa.Column("exit_criteria", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    # ─── domain_treatment_items ─────────────────────────────────────────
    op.create_table(
        "domain_treatment_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("item_id", sa.String(64), unique=True, nullable=False, index=True),
        sa.Column("plan_id", sa.String(36), sa.ForeignKey("domain_treatment_plans.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("phase_id", sa.String(36), sa.ForeignKey("domain_treatment_phases.id", ondelete="CASCADE"), nullable=True, index=True),
        sa.Column("item_order", sa.Integer, nullable=False),
        sa.Column("item_type", sa.String(32), nullable=False),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("drug_id", sa.String(64), nullable=True),
        sa.Column("procedure_code", sa.String(64), nullable=True),
        sa.Column("frequency", sa.String(128), nullable=True),
        sa.Column("duration", sa.String(128), nullable=True),
        sa.Column("route", sa.String(64), nullable=True),
        sa.Column("planned_dose_text", sa.Text, nullable=True),
        sa.Column("priority", sa.Integer, nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="planned"),
        sa.Column("rationale", sa.Text, nullable=True),
        sa.Column("source_recommendation", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    # ─── domain_treatment_monitoring ────────────────────────────────────
    op.create_table(
        "domain_treatment_monitoring",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("monitoring_id", sa.String(64), unique=True, nullable=False, index=True),
        sa.Column("plan_id", sa.String(36), sa.ForeignKey("domain_treatment_plans.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("phase_id", sa.String(36), sa.ForeignKey("domain_treatment_phases.id", ondelete="CASCADE"), nullable=True, index=True),
        sa.Column("item_id", sa.String(36), sa.ForeignKey("domain_treatment_items.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("monitoring_type", sa.String(32), nullable=False),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("schedule", sa.String(256), nullable=True),
        sa.Column("target_range", sa.JSON, nullable=True),
        sa.Column("warning_threshold", sa.JSON, nullable=True),
        sa.Column("critical_threshold", sa.JSON, nullable=True),
        sa.Column("action_if_abnormal", sa.Text, nullable=True),
        sa.Column("baseline_required", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("repeat_interval", sa.String(64), nullable=True),
        sa.Column("responsible_specialty", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    # ─── domain_treatment_safety_rules ──────────────────────────────────
    op.create_table(
        "domain_treatment_safety_rules",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("rule_id", sa.String(64), unique=True, nullable=False, index=True),
        sa.Column("plan_id", sa.String(36), sa.ForeignKey("domain_treatment_plans.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("phase_id", sa.String(36), sa.ForeignKey("domain_treatment_phases.id", ondelete="CASCADE"), nullable=True, index=True),
        sa.Column("item_id", sa.String(36), sa.ForeignKey("domain_treatment_items.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("rule_type", sa.String(32), nullable=False),
        sa.Column("condition", sa.JSON, nullable=True),
        sa.Column("severity", sa.String(32), nullable=False, server_default="medium"),
        sa.Column("recommended_action", sa.Text, nullable=True),
        sa.Column("requires_review", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("source", sa.String(256), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    # ─── domain_treatment_plan_traces ───────────────────────────────────
    op.create_table(
        "domain_treatment_plan_traces",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("trace_id", sa.String(64), nullable=False, index=True),
        sa.Column("plan_id", sa.String(36), sa.ForeignKey("domain_treatment_plans.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("step_order", sa.Integer, nullable=False),
        sa.Column("step_type", sa.String(64), nullable=False),
        sa.Column("input_summary", sa.JSON, nullable=True),
        sa.Column("output_summary", sa.JSON, nullable=True),
        sa.Column("rule_ids", sa.JSON, nullable=True),
        sa.Column("evidence_ids", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("trace_id", "step_order", name="uq_trace_step"),
    )


def downgrade() -> None:
    bind = op.get_bind()

    # Check each table for existing data before dropping
    tables_to_check = [
        "domain_treatment_plan_traces",
        "domain_treatment_safety_rules",
        "domain_treatment_monitoring",
        "domain_treatment_items",
        "domain_treatment_phases",
        "domain_treatment_plans",
    ]
    for table_name in tables_to_check:
        count = bind.execute(sa.text(f"SELECT COUNT(*) FROM {table_name}")).scalar()
        if count > 0:
            raise IrreversibleMigrationError(
                f"Cannot downgrade Migration 023. "
                f"Table '{table_name}' has {count} row(s). "
                "Downgrade would destroy persisted treatment plan data."
            )

    # All tables are empty — safe to drop in reverse dependency order
    op.drop_table("domain_treatment_plan_traces")
    op.drop_table("domain_treatment_safety_rules")
    op.drop_table("domain_treatment_monitoring")
    op.drop_table("domain_treatment_items")
    op.drop_table("domain_treatment_phases")
    op.drop_table("domain_treatment_plans")
