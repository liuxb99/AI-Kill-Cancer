"""extended_knowledge_layer

Revision ID: 009
Revises: 008
Create Date: 2026-07-20

Adds knowledge layer tables:
- domain_knowledge_entities (unified knowledge entities)
- domain_knowledge_relations (typed relations between entities)
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "domain_knowledge_entities",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("entity_type", sa.String(32), nullable=False, index=True),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("source_id", sa.String(256), nullable=False, index=True),
        sa.Column("name", sa.String(512), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("aliases", sa.JSON, default=list),
        sa.Column("identifiers", sa.JSON, default=dict),
        sa.Column("metadata", sa.JSON, default=dict),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_knowledge_entities_type_source", "domain_knowledge_entities",
                     ["entity_type", "source"])

    op.create_table(
        "domain_knowledge_relations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("source_entity_id", sa.String(36),
                   sa.ForeignKey("domain_knowledge_entities.id", ondelete="CASCADE"),
                   nullable=False, index=True),
        sa.Column("target_entity_id", sa.String(36),
                   sa.ForeignKey("domain_knowledge_entities.id", ondelete="CASCADE"),
                   nullable=False, index=True),
        sa.Column("relation_type", sa.String(64), nullable=False, index=True),
        sa.Column("evidence", sa.Text, nullable=True),
        sa.Column("source", sa.String(64), nullable=True),
        sa.Column("confidence", sa.String(32), default="unknown"),
        sa.Column("metadata", sa.JSON, default=dict),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("domain_knowledge_relations")
    op.drop_table("domain_knowledge_entities")
