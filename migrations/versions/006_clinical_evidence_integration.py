"""clinical_evidence_integration

Revision ID: 006
Revises: 005
Create Date: 2026-07-20

Adds evidence tables for Phase 2B:
- domain_knowledge_sources (registered evidence sources)
- domain_evidence_items (unified evidence from CIViC, DGIdb)
- domain_drug_interactions (drug-gene interactions)
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── domain_knowledge_sources ────────────────────────────────────────
    op.create_table(
        "domain_knowledge_sources",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(128), unique=True, nullable=False),
        sa.Column("version", sa.String(64), nullable=True),
        sa.Column("license", sa.String(256), nullable=True),
        sa.Column("base_url", sa.String(512), nullable=True),
        sa.Column("is_configured", sa.String(16), nullable=False, server_default="not_configured"),
        sa.Column("last_health_check", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_knowledge_sources_name", "domain_knowledge_sources", ["name"])

    # ── domain_evidence_items ───────────────────────────────────────────
    op.create_table(
        "domain_evidence_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("source_id", sa.String(36), sa.ForeignKey("domain_knowledge_sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_record_id", sa.String(256), nullable=True),
        sa.Column("variant_id", sa.String(36), sa.ForeignKey("domain_variants.id", ondelete="SET NULL"), nullable=True),
        sa.Column("gene_symbol", sa.String(32), nullable=True),
        sa.Column("disease", sa.String(256), nullable=True),
        sa.Column("drug_name", sa.String(256), nullable=True),
        sa.Column("drug_id", sa.String(36), sa.ForeignKey("domain_drugs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("evidence_type", sa.String(64), nullable=True),
        sa.Column("evidence_direction", sa.String(32), nullable=True),
        sa.Column("evidence_level", sa.String(32), nullable=True),
        sa.Column("clinical_significance", sa.String(64), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("citation", sa.String(512), nullable=True),
        sa.Column("pmid", sa.String(32), nullable=True),
        sa.Column("url", sa.String(512), nullable=True),
        sa.Column("interaction_type", sa.String(128), nullable=True),
        sa.Column("interaction_score", sa.Float, nullable=True),
        sa.Column("confidence", sa.String(32), nullable=True),
        sa.Column("source_version", sa.String(64), nullable=True),
        sa.Column("retrieved_at", sa.DateTime, nullable=False),
        sa.Column("api_request_hash", sa.String(64), nullable=True),
        sa.Column("api_response_hash", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_evidence_items_source_record", "domain_evidence_items", ["source_record_id"])
    op.create_index("ix_evidence_items_variant_id", "domain_evidence_items", ["variant_id"])
    op.create_index("ix_evidence_items_gene_symbol", "domain_evidence_items", ["gene_symbol"])

    # ── domain_drug_interactions ────────────────────────────────────────
    op.create_table(
        "domain_drug_interactions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("source_id", sa.String(36), sa.ForeignKey("domain_knowledge_sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("gene_symbol", sa.String(32), nullable=False),
        sa.Column("drug_name", sa.String(256), nullable=False),
        sa.Column("interaction_type", sa.String(128), nullable=True),
        sa.Column("interaction_score", sa.Float, nullable=True),
        sa.Column("source_db_name", sa.String(64), nullable=True),
        sa.Column("pmids", sa.JSON, nullable=True),
        sa.Column("source_version", sa.String(64), nullable=True),
        sa.Column("retrieved_at", sa.DateTime, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_drug_interactions_gene", "domain_drug_interactions", ["gene_symbol"])


def downgrade() -> None:
    op.drop_table("domain_drug_interactions")
    op.drop_table("domain_evidence_items")
    op.drop_table("domain_knowledge_sources")
