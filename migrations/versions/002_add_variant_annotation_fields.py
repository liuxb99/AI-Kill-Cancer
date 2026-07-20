"""add_variant_annotation_fields

Revision ID: 002
Revises: 001
Create Date: 2026-07-20

Adds Phase 2A fields to domain_variants:
- consequence, protein_change
- dbsnp_id, clinvar_id, cosmic_id
- af, gnomad_af
- annotation_source
- original_vcf_line, original_vcf_position, original_vcf_reference, original_vcf_alternate
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add columns to domain_variants
    op.add_column("domain_variants", sa.Column("consequence", sa.String(64), nullable=True, comment="Most severe SO consequence"))
    op.add_column("domain_variants", sa.Column("protein_change", sa.String(128), nullable=True, comment="Protein change e.g. p.Val600Glu"))
    op.add_column("domain_variants", sa.Column("dbsnp_id", sa.String(32), nullable=True, comment="dbSNP rs ID"))
    op.add_column("domain_variants", sa.Column("clinvar_id", sa.String(32), nullable=True, comment="ClinVar variation ID"))
    op.add_column("domain_variants", sa.Column("cosmic_id", sa.String(32), nullable=True, comment="COSMIC mutation ID"))
    op.add_column("domain_variants", sa.Column("af", sa.Float, nullable=True, comment="Allele frequency from 1KG"))
    op.add_column("domain_variants", sa.Column("gnomad_af", sa.Float, nullable=True, comment="gnomAD allele frequency"))
    op.add_column("domain_variants", sa.Column("annotation_source", sa.String(64), nullable=True, comment="Source of annotation e.g. VEP, OpenCRAVAT"))
    op.add_column("domain_variants", sa.Column("original_vcf_line", sa.String(1024), nullable=True, comment="Original VCF line before normalization"))
    op.add_column("domain_variants", sa.Column("original_vcf_position", sa.Integer, nullable=True, comment="Original position before normalization"))
    op.add_column("domain_variants", sa.Column("original_vcf_reference", sa.String(256), nullable=True, comment="Original ref before normalization"))
    op.add_column("domain_variants", sa.Column("original_vcf_alternate", sa.String(256), nullable=True, comment="Original alt before normalization"))


def downgrade() -> None:
    op.drop_column("domain_variants", "original_vcf_alternate")
    op.drop_column("domain_variants", "original_vcf_reference")
    op.drop_column("domain_variants", "original_vcf_position")
    op.drop_column("domain_variants", "original_vcf_line")
    op.drop_column("domain_variants", "annotation_source")
    op.drop_column("domain_variants", "gnomad_af")
    op.drop_column("domain_variants", "af")
    op.drop_column("domain_variants", "cosmic_id")
    op.drop_column("domain_variants", "clinvar_id")
    op.drop_column("domain_variants", "dbsnp_id")
    op.drop_column("domain_variants", "protein_change")
    op.drop_column("domain_variants", "consequence")
