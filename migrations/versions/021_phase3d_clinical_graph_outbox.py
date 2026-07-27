"""phase3d_clinical_graph_outbox

Revision ID: 021
Revises: 020
Create Date: 2026-07-27

Adds Transactional Outbox table for Clinical Knowledge Graph projection.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


class IrreversibleMigrationError(Exception):
    pass

revision: str = "021"
down_revision: Union[str, None] = "020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "domain_clinical_graph_outbox",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("event_id", sa.String(64), unique=True, nullable=False, index=True),
        sa.Column("aggregate_type", sa.String(64), nullable=False, index=True),
        sa.Column("aggregate_id", sa.String(64), nullable=False, index=True),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("schema_version", sa.Integer, nullable=False, server_default=sa.text("1")),
        sa.Column("payload", sa.JSON, nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending", index=True),
        sa.Column("attempt_count", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("last_error", sa.Text, nullable=True),
        sa.Column("actor_id", sa.String(64), nullable=True, index=True),
        sa.Column("available_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("processed_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    # 复合索引
    op.create_index("ix_outbox_aggregate", "domain_clinical_graph_outbox", ["aggregate_type", "aggregate_id"])
    op.create_index("ix_outbox_status_available", "domain_clinical_graph_outbox", ["status", "available_at"])


def downgrade() -> None:
    # 如果表中有数据，拒绝 downgrade
    conn = op.get_bind()
    result = conn.execute(sa.text("SELECT COUNT(*) FROM domain_clinical_graph_outbox"))
    count = result.scalar()
    if count > 0:
        raise IrreversibleMigrationError(
            f"Cannot downgrade: domain_clinical_graph_outbox has {count} pending events. "
            "Process or delete all events before downgrading."
        )
    op.drop_index("ix_outbox_status_available", table_name="domain_clinical_graph_outbox")
    op.drop_index("ix_outbox_aggregate", table_name="domain_clinical_graph_outbox")
    op.drop_table("domain_clinical_graph_outbox")
