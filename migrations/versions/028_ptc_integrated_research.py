"""PTC integrated research and scientific herbal medicine.

Revision ID: 028_ptc_integrated_research
Revises: 027_ptc_therapy_evidence_trials
"""

from alembic import op
import sqlalchemy as sa

revision = "028_ptc_integrated_research"
down_revision = "027_ptc_therapy_evidence_trials"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "domain_ptc_herbs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("herb_key", sa.String(160), nullable=False),
        sa.Column("chinese_name", sa.String(128), nullable=False),
        sa.Column("english_name", sa.String(256)),
        sa.Column("latin_name", sa.String(256)),
        sa.Column("medicinal_part", sa.String(128)),
        sa.Column("traditional_functions", sa.JSON(), nullable=False),
        sa.Column("investigated_genes", sa.JSON(), nullable=False),
        sa.Column("investigated_pathways", sa.JSON(), nullable=False),
        sa.Column("evidence_level", sa.String(64), nullable=False),
        sa.Column("evidence_summary", sa.Text()),
        sa.Column("source_name", sa.String(128), nullable=False),
        sa.Column("source_record_id", sa.String(256)),
        sa.Column("license", sa.String(128)),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("herb_key", name="uq_ptc_herb_key"),
    )
    op.create_index("ix_domain_ptc_herbs_herb_key", "domain_ptc_herbs", ["herb_key"])

    op.create_table(
        "domain_ptc_herb_compounds",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("compound_key", sa.String(192), nullable=False),
        sa.Column("herb_key", sa.String(160), nullable=False),
        sa.Column("compound_name", sa.String(256), nullable=False),
        sa.Column("pubchem_cid", sa.String(64)),
        sa.Column("inchikey", sa.String(64)),
        sa.Column("target_genes", sa.JSON(), nullable=False),
        sa.Column("pathways", sa.JSON(), nullable=False),
        sa.Column("source_name", sa.String(128), nullable=False),
        sa.Column("source_record_id", sa.String(256)),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("compound_key", name="uq_ptc_herb_compound_key"),
    )
    op.create_index("ix_domain_ptc_herb_compounds_compound_key", "domain_ptc_herb_compounds", ["compound_key"])
    op.create_index("ix_domain_ptc_herb_compounds_herb_key", "domain_ptc_herb_compounds", ["herb_key"])

    op.create_table(
        "domain_ptc_herb_drug_interactions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("herb_key", sa.String(160), nullable=False),
        sa.Column("therapy_key", sa.String(160), nullable=False),
        sa.Column("interaction_type", sa.String(64), nullable=False),
        sa.Column("severity", sa.String(32), nullable=False),
        sa.Column("mechanism", sa.Text()),
        sa.Column("clinical_effect", sa.Text()),
        sa.Column("recommendation", sa.Text()),
        sa.Column("evidence_level", sa.String(64), nullable=False),
        sa.Column("source_name", sa.String(128), nullable=False),
        sa.Column("source_record_id", sa.String(256)),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("herb_key", "therapy_key", "interaction_type", name="uq_ptc_herb_drug_interaction"),
    )
    op.create_index("ix_domain_ptc_herb_drug_interactions_herb_key", "domain_ptc_herb_drug_interactions", ["herb_key"])
    op.create_index("ix_domain_ptc_herb_drug_interactions_therapy_key", "domain_ptc_herb_drug_interactions", ["therapy_key"])

    op.create_table(
        "domain_ptc_case_similarities",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("case_id", sa.String(128), nullable=False),
        sa.Column("similar_case_id", sa.String(128), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("shared_genes", sa.JSON(), nullable=False),
        sa.Column("shared_stage", sa.String(64)),
        sa.Column("rationale", sa.Text()),
        sa.Column("algorithm_version", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("case_id", "similar_case_id", name="uq_ptc_case_similarity"),
    )
    op.create_index("ix_domain_ptc_case_similarities_case_id", "domain_ptc_case_similarities", ["case_id"])
    op.create_index("ix_domain_ptc_case_similarities_similar_case_id", "domain_ptc_case_similarities", ["similar_case_id"])

    op.create_table(
        "domain_ptc_recommendation_snapshots",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("recommendation_id", sa.String(128), nullable=False),
        sa.Column("case_id", sa.String(128), nullable=False),
        sa.Column("recommendation_type", sa.String(64), nullable=False),
        sa.Column("ranked_therapies", sa.JSON(), nullable=False),
        sa.Column("matching_trials", sa.JSON(), nullable=False),
        sa.Column("supporting_evidence", sa.JSON(), nullable=False),
        sa.Column("herb_research", sa.JSON(), nullable=False),
        sa.Column("interaction_warnings", sa.JSON(), nullable=False),
        sa.Column("similar_cases", sa.JSON(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("engine_version", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("recommendation_id"),
    )
    op.create_index("ix_domain_ptc_recommendation_snapshots_recommendation_id", "domain_ptc_recommendation_snapshots", ["recommendation_id"])
    op.create_index("ix_domain_ptc_recommendation_snapshots_case_id", "domain_ptc_recommendation_snapshots", ["case_id"])


def downgrade() -> None:
    op.drop_table("domain_ptc_recommendation_snapshots")
    op.drop_table("domain_ptc_case_similarities")
    op.drop_table("domain_ptc_herb_drug_interactions")
    op.drop_table("domain_ptc_herb_compounds")
    op.drop_table("domain_ptc_herbs")
