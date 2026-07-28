"""phase3d_graph_correctness_outbox

Revision ID: 022
Revises: 021
Create Date: 2026-07-28

Adds correlation_id, causation_id, occurred_at, claim_token,
processing_started_at, last_failed_at to domain_clinical_graph_outbox.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


class IrreversibleMigrationError(Exception):
    pass


revision: str = "022"
down_revision: Union[str, None] = "021"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    """跨資料庫檢查表中是否已存在某列（支援 SQLite 和 PostgreSQL）。"""
    conn = op.get_bind()
    dialect = conn.dialect.name
    if dialect == "sqlite":
        rows = conn.execute(sa.text(f"PRAGMA table_info({table})")).fetchall()
        return any(row[1] == column for row in rows)
    elif dialect == "postgresql":
        rows = conn.execute(
            sa.text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = :table AND column_name = :column"
            ),
            {"table": table, "column": column},
        ).fetchall()
        return len(rows) > 0
    else:
        return False


def upgrade() -> None:
    # 依序新增 6 個欄位（每個都先檢查是否存在，支援重新執行）
    new_columns = [
        ("correlation_id", sa.String(64), True),
        ("causation_id", sa.String(64), True),
        ("occurred_at", sa.DateTime, True),
        ("claim_token", sa.String(64), True),
        ("processing_started_at", sa.DateTime, True),
        ("last_failed_at", sa.DateTime, True),
    ]
    for col_name, col_type, nullable in new_columns:
        if not _has_column("domain_clinical_graph_outbox", col_name):
            op.add_column(
                "domain_clinical_graph_outbox",
                sa.Column(col_name, col_type, nullable=nullable),
            )

    # 為 correlation_id 建立索引
    conn = op.get_bind()
    is_sqlite = conn.dialect.name == "sqlite"
    try:
        op.create_index(
            "ix_outbox_correlation_id",
            "domain_clinical_graph_outbox",
            ["correlation_id"],
        )
    except Exception:
        # 索引可能已存在
        pass


def downgrade() -> None:
    conn = op.get_bind()
    is_sqlite = conn.dialect.name == "sqlite"

    if is_sqlite:
        # SQLite 不支援 DROP COLUMN，需重建表
        conn.execute(sa.text("PRAGMA foreign_keys=OFF"))

        # 0. 清理残留的备份表（确保幂等性）
        conn.execute(sa.text("DROP TABLE IF EXISTS _domain_clinical_graph_outbox_backup"))

        # 1. 將原始表改名為暫存表
        op.rename_table(
            "domain_clinical_graph_outbox",
            "_domain_clinical_graph_outbox_backup",
        )

        # 2. 建立不含新欄位的新表（不含任何索引）
        op.create_table(
            "domain_clinical_graph_outbox",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("event_id", sa.String(64), unique=True, nullable=False),
            sa.Column("aggregate_type", sa.String(64), nullable=False),
            sa.Column("aggregate_id", sa.String(64), nullable=False),
            sa.Column("event_type", sa.String(64), nullable=False),
            sa.Column("schema_version", sa.Integer, nullable=False, server_default=sa.text("1")),
            sa.Column("payload", sa.JSON, nullable=False),
            sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
            sa.Column("attempt_count", sa.Integer, nullable=False, server_default=sa.text("0")),
            sa.Column("last_error", sa.Text, nullable=True),
            sa.Column("actor_id", sa.String(64), nullable=True),
            sa.Column("available_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
            sa.Column("processed_at", sa.DateTime, nullable=True),
            sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        )

        # 3. 從備份表複製資料（只選取舊欄位）
        conn.execute(sa.text("""
            INSERT INTO domain_clinical_graph_outbox (
                id, event_id, aggregate_type, aggregate_id, event_type,
                schema_version, payload, status, attempt_count, last_error,
                actor_id, available_at, processed_at, created_at, updated_at
            )
            SELECT
                id, event_id, aggregate_type, aggregate_id, event_type,
                schema_version, payload, status, attempt_count, last_error,
                actor_id, available_at, processed_at, created_at, updated_at
            FROM _domain_clinical_graph_outbox_backup
        """))

        # 4. 刪除備份表（連同其所有索引一起刪除）
        op.drop_table("_domain_clinical_graph_outbox_backup")

        # 5. 在新表上建立所有索引（備份表已刪除，不會有索引名衝突）
        op.create_index("ix_domain_clinical_graph_outbox_event_id", "domain_clinical_graph_outbox", ["event_id"], unique=True)
        op.create_index("ix_domain_clinical_graph_outbox_aggregate_type", "domain_clinical_graph_outbox", ["aggregate_type"])
        op.create_index("ix_domain_clinical_graph_outbox_aggregate_id", "domain_clinical_graph_outbox", ["aggregate_id"])
        op.create_index("ix_domain_clinical_graph_outbox_status", "domain_clinical_graph_outbox", ["status"])
        op.create_index("ix_domain_clinical_graph_outbox_actor_id", "domain_clinical_graph_outbox", ["actor_id"])
        # 複合索引
        op.create_index("ix_outbox_aggregate", "domain_clinical_graph_outbox", ["aggregate_type", "aggregate_id"])
        op.create_index("ix_outbox_status_available", "domain_clinical_graph_outbox", ["status", "available_at"])

        conn.execute(sa.text("PRAGMA foreign_keys=ON"))
    else:
        # PostgreSQL / MySQL 可以直接 DROP COLUMN
        op.drop_column("domain_clinical_graph_outbox", "correlation_id")
        op.drop_column("domain_clinical_graph_outbox", "causation_id")
        op.drop_column("domain_clinical_graph_outbox", "occurred_at")
        op.drop_column("domain_clinical_graph_outbox", "claim_token")
        op.drop_column("domain_clinical_graph_outbox", "processing_started_at")
        op.drop_column("domain_clinical_graph_outbox", "last_failed_at")
