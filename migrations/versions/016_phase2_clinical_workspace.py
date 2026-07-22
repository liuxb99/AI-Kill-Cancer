"""phase2_clinical_workspace

Revision ID: 016
Revises: 015
Create Date: 2026-07-21

Adds Phase 2 clinical decision workspace tables:
- clinical_decision_nodes
- clinical_agent_opinions
- clinical_consensus_results
- clinical_recommendations
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "016"
down_revision: Union[str, None] = "015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ─── clinical_decision_nodes ────────────────────────────────────────────
    op.create_table(
        "clinical_decision_nodes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("case_id", sa.String(36), sa.ForeignKey("domain_cancer_cases.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("parent_id", sa.String(36), sa.ForeignKey("clinical_decision_nodes.id", ondelete="SET NULL"), nullable=True),
        sa.Column("node_type", sa.String(64), nullable=False),
        sa.Column("input_snapshot", sa.JSON, nullable=True),
        sa.Column("evidence_snapshot", sa.JSON, nullable=True),
        sa.Column("agent_id", sa.String(128), nullable=True),
        sa.Column("agent_type", sa.String(64), nullable=True),
        sa.Column("reasoning", sa.Text, nullable=True),
        sa.Column("confidence", sa.String(32), nullable=True),
        sa.Column("decision_label", sa.String(256), nullable=True),
        sa.Column("timestamp", sa.DateTime, nullable=False),
        sa.Column("context_hash", sa.String(64), nullable=False, index=True),
    )

    # ─── clinical_agent_opinions ────────────────────────────────────────────
    op.create_table(
        "clinical_agent_opinions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("case_id", sa.String(36), sa.ForeignKey("domain_cancer_cases.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("run_id", sa.String(64), nullable=False, index=True),
        sa.Column("agent_type", sa.String(64), nullable=False),
        sa.Column("agent_version", sa.String(32), nullable=True),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("pros", sa.JSON, nullable=True),
        sa.Column("cons", sa.JSON, nullable=True),
        sa.Column("confidence", sa.String(32), nullable=True),
        sa.Column("references", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    # ─── clinical_consensus_results ─────────────────────────────────────────
    op.create_table(
        "clinical_consensus_results",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("case_id", sa.String(36), sa.ForeignKey("domain_cancer_cases.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("run_id", sa.String(64), nullable=False, index=True),
        sa.Column("agreement_level", sa.String(32), nullable=True),
        sa.Column("conflicts", sa.JSON, nullable=True),
        sa.Column("confidence", sa.String(32), nullable=True),
        sa.Column("recommended_option", sa.JSON, nullable=True),
        sa.Column("alternative_options", sa.JSON, nullable=True),
        sa.Column("unresolved_questions", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    # ─── clinical_recommendations ───────────────────────────────────────────
    op.create_table(
        "clinical_recommendations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("case_id", sa.String(36), sa.ForeignKey("domain_cancer_cases.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("run_id", sa.String(64), nullable=False, index=True),
        sa.Column("recommendation_type", sa.String(64), nullable=False),
        sa.Column("first_line", sa.JSON, nullable=True),
        sa.Column("second_line", sa.JSON, nullable=True),
        sa.Column("clinical_trial", sa.JSON, nullable=True),
        sa.Column("supporting_evidence", sa.JSON, nullable=True),
        sa.Column("expected_benefit", sa.JSON, nullable=True),
        sa.Column("potential_risk", sa.JSON, nullable=True),
        sa.Column("monitoring_plan", sa.JSON, nullable=True),
        sa.Column("structured_json", sa.JSON, nullable=True),
        sa.Column("markdown", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("clinical_recommendations")
    op.drop_table("clinical_consensus_results")
    op.drop_table("clinical_agent_opinions")
    op.drop_table("clinical_decision_nodes")
