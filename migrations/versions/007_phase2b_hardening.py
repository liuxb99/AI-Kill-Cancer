"""phase2b_hardening

Revision ID: 007
Revises: 006
Create Date: 2026-07-20

Adds Phase 2B hardening fields:
- domain_evidence_items: match_level, conflict_status, source_native_level,
  payload_hash, first_seen_at, last_seen_at, withdrawn_at, superseded_by,
  is_superseded
- domain_knowledge_sources: retrieval_count
- domain_drug_interactions: payload_hash, first_seen_at, last_seen_at,
  withdrawn_at, superseded_by, is_superseded
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── domain_knowledge_sources: add retrieval_count ────────────────
    op.add_column(
        "domain_knowledge_sources",
        sa.Column("retrieval_count", sa.Integer, nullable=False, server_default="0"),
    )

    # ── domain_evidence_items: add Phase 2B fields ────────────────────
    op.add_column(
        "domain_evidence_items",
        sa.Column("match_level", sa.String(32), nullable=True,
                   comment="exact_variant, equivalent_hgvs, coordinate_match, molecular_profile_match, gene_level_only, unmatched"),
    )
    op.add_column(
        "domain_evidence_items",
        sa.Column("conflict_status", sa.String(32), nullable=True,
                   comment="supporting, conflicting, uncertain, not_evaluable"),
    )
    op.add_column(
        "domain_evidence_items",
        sa.Column("source_native_level", sa.String(64), nullable=True,
                   comment="Original evidence level from source (e.g. CIViC A, OncoKB 3B)"),
    )
    op.add_column(
        "domain_evidence_items",
        sa.Column("payload_hash", sa.String(64), nullable=True,
                   comment="SHA256 of unique evidence payload for dedup"),
    )
    op.add_column(
        "domain_evidence_items",
        sa.Column("first_seen_at", sa.DateTime, nullable=True,
                   comment="When this evidence was first retrieved"),
    )
    op.add_column(
        "domain_evidence_items",
        sa.Column("last_seen_at", sa.DateTime, nullable=True,
                   comment="When this evidence was last seen in refresh"),
    )
    op.add_column(
        "domain_evidence_items",
        sa.Column("withdrawn_at", sa.DateTime, nullable=True,
                   comment="When the source withdrew this evidence"),
    )
    op.add_column(
        "domain_evidence_items",
        sa.Column("superseded_by", sa.String(36), nullable=True,
                   comment="ID of superseding evidence item"),
    )
    op.add_column(
        "domain_evidence_items",
        sa.Column("is_superseded", sa.Boolean, nullable=True, server_default="0",
                   comment="Whether this item has been superseded"),
    )
    op.create_index("ix_evidence_items_match_level", "domain_evidence_items", ["match_level"])
    op.create_index("ix_evidence_items_payload_hash", "domain_evidence_items", ["payload_hash"])
    op.create_index("ix_evidence_items_conflict_status", "domain_evidence_items", ["conflict_status"])

    # ── domain_drug_interactions: add Phase 2B fields ─────────────────
    op.add_column(
        "domain_drug_interactions",
        sa.Column("payload_hash", sa.String(64), nullable=True,
                   comment="SHA256 for dedup"),
    )
    op.add_column(
        "domain_drug_interactions",
        sa.Column("first_seen_at", sa.DateTime, nullable=True),
    )
    op.add_column(
        "domain_drug_interactions",
        sa.Column("last_seen_at", sa.DateTime, nullable=True),
    )
    op.add_column(
        "domain_drug_interactions",
        sa.Column("withdrawn_at", sa.DateTime, nullable=True),
    )
    op.add_column(
        "domain_drug_interactions",
        sa.Column("superseded_by", sa.String(36), nullable=True),
    )
    op.add_column(
        "domain_drug_interactions",
        sa.Column("is_superseded", sa.Boolean, nullable=True, server_default="0"),
    )


def downgrade() -> None:
    # ── domain_drug_interactions ─────────────────────────────────────
    op.drop_column("domain_drug_interactions", "is_superseded")
    op.drop_column("domain_drug_interactions", "superseded_by")
    op.drop_column("domain_drug_interactions", "withdrawn_at")
    op.drop_column("domain_drug_interactions", "last_seen_at")
    op.drop_column("domain_drug_interactions", "first_seen_at")
    op.drop_column("domain_drug_interactions", "payload_hash")

    # ── domain_evidence_items ────────────────────────────────────────
    op.drop_index("ix_evidence_items_conflict_status", table_name="domain_evidence_items")
    op.drop_index("ix_evidence_items_payload_hash", table_name="domain_evidence_items")
    op.drop_index("ix_evidence_items_match_level", table_name="domain_evidence_items")
    op.drop_column("domain_evidence_items", "is_superseded")
    op.drop_column("domain_evidence_items", "superseded_by")
    op.drop_column("domain_evidence_items", "withdrawn_at")
    op.drop_column("domain_evidence_items", "last_seen_at")
    op.drop_column("domain_evidence_items", "first_seen_at")
    op.drop_column("domain_evidence_items", "payload_hash")
    op.drop_column("domain_evidence_items", "source_native_level")
    op.drop_column("domain_evidence_items", "conflict_status")
    op.drop_column("domain_evidence_items", "match_level")

    # ── domain_knowledge_sources ─────────────────────────────────────
    op.drop_column("domain_knowledge_sources", "retrieval_count")
