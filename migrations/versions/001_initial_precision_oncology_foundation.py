"""initial_precision_oncology_foundation

Revision ID: 001
Revises: 
Create Date: 2026-07-20

Domain models for Precision Oncology Foundation v0.2.0:
- domain_patients, domain_cancer_cases, domain_specimens
- domain_sequencing_tests, domain_uploaded_files
- domain_variants, domain_genes, domain_proteins, domain_pathways
- domain_drugs, domain_drug_targets
- domain_evidences, domain_drug_candidates
- domain_publications, domain_clinical_trials
- domain_analysis_runs, domain_reports
- domain_consents, domain_audit_logs
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _create_enum_if_not_exists(enum_name: str, values: list[str], schema: str = "public"):
    """Create an enum type if it does not exist (PostgreSQL only)."""
    # Check if running against PostgreSQL
    bind = op.get_context().bind
    if bind.dialect.name == "postgresql":
        op.execute(f"DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = '{enum_name}') THEN CREATE TYPE {schema}.{enum_name} AS ENUM ({','.join(f"'{v}'" for v in values)}); END IF; END $$;")


def upgrade() -> None:
    # ─── Enums ─────────────────────────────────────────────────────────────
    # SQLAlchemy will create Enum types automatically; for PostgreSQL
    # compatibility we define them explicitly.

    # ─── domain_patients ────────────────────────────────────────────────────
    op.create_table(
        "domain_patients",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("external_id", sa.String(128), nullable=True, unique=True),
        sa.Column("display_name", sa.String(128), nullable=True),
        sa.Column("birth_year", sa.Integer, nullable=True),
        sa.Column("age_range", sa.String(32), nullable=True),
        sa.Column("sex", sa.String(16), nullable=True),
        sa.Column("consent_status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_domain_patients_external_id", "domain_patients", ["external_id"])
    op.create_index("ix_domain_patients_created_at", "domain_patients", ["created_at"])

    # ─── domain_cancer_cases ────────────────────────────────────────────────
    op.create_table(
        "domain_cancer_cases",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("patient_id", sa.String(36), sa.ForeignKey("domain_patients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("oncotree_code", sa.String(32), nullable=True),
        sa.Column("cancer_type", sa.String(16), nullable=False),
        sa.Column("histology", sa.String(256), nullable=True),
        sa.Column("stage", sa.String(32), nullable=True),
        sa.Column("diagnosis_date", sa.Date, nullable=True),
        sa.Column("radioiodine_status", sa.String(64), nullable=True),
        sa.Column("recurrence_status", sa.String(64), nullable=True),
        sa.Column("metastatic_sites", sa.JSON, nullable=True),
        sa.Column("treatment_history", sa.JSON, nullable=True),
        sa.Column("current_medications", sa.JSON, nullable=True),
        sa.Column("clinical_notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_domain_cancer_cases_patient_id", "domain_cancer_cases", ["patient_id"])
    op.create_index("ix_domain_cancer_cases_cancer_type", "domain_cancer_cases", ["cancer_type"])

    # ─── domain_specimens ──────────────────────────────────────────────────
    op.create_table(
        "domain_specimens",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("case_id", sa.String(36), sa.ForeignKey("domain_cancer_cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("specimen_type", sa.String(32), nullable=False),
        sa.Column("collection_site", sa.String(256), nullable=True),
        sa.Column("collection_date", sa.Date, nullable=True),
        sa.Column("tumor_purity", sa.Float, nullable=True),
        sa.Column("matched_normal_available", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("storage_reference", sa.String(256), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_domain_specimens_case_id", "domain_specimens", ["case_id"])

    # ─── domain_genes ──────────────────────────────────────────────────────
    op.create_table(
        "domain_genes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("symbol", sa.String(32), nullable=False, unique=True),
        sa.Column("full_name", sa.String(512), nullable=True),
        sa.Column("aliases", sa.JSON, nullable=True),
        sa.Column("chromosome", sa.String(16), nullable=True),
        sa.Column("gene_type", sa.String(64), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("ncbi_gene_id", sa.String(32), nullable=True, unique=True),
        sa.Column("ensembl_gene_id", sa.String(64), nullable=True, unique=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_domain_genes_symbol", "domain_genes", ["symbol"])

    # ─── domain_proteins ────────────────────────────────────────────────────
    op.create_table(
        "domain_proteins",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("gene_id", sa.String(36), sa.ForeignKey("domain_genes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("uniprot_id", sa.String(64), nullable=True, unique=True),
        sa.Column("name", sa.String(512), nullable=True),
        sa.Column("function", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_domain_proteins_gene_id", "domain_proteins", ["gene_id"])

    # ─── domain_pathways ────────────────────────────────────────────────────
    op.create_table(
        "domain_pathways",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("source", sa.String(64), nullable=True),
        sa.Column("source_id", sa.String(64), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("genes", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_domain_pathways_name", "domain_pathways", ["name"])

    # ─── domain_sequencing_tests ────────────────────────────────────────────
    op.create_table(
        "domain_sequencing_tests",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("specimen_id", sa.String(36), sa.ForeignKey("domain_specimens.id", ondelete="CASCADE"), nullable=False),
        sa.Column("laboratory", sa.String(256), nullable=True),
        sa.Column("assay_name", sa.String(256), nullable=False),
        sa.Column("assay_version", sa.String(64), nullable=True),
        sa.Column("panel_name", sa.String(256), nullable=True),
        sa.Column("genome_build", sa.String(32), nullable=True),
        sa.Column("sequencing_depth", sa.Float, nullable=True),
        sa.Column("minimum_detectable_vaf", sa.Float, nullable=True),
        sa.Column("test_date", sa.Date, nullable=True),
        sa.Column("result_type", sa.String(16), nullable=False, server_default="somatic"),
        sa.Column("limitations", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_domain_sequencing_tests_specimen_id", "domain_sequencing_tests", ["specimen_id"])

    # ─── domain_uploaded_files ──────────────────────────────────────────────
    op.create_table(
        "domain_uploaded_files",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("sequencing_test_id", sa.String(36), sa.ForeignKey("domain_sequencing_tests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("original_filename", sa.String(512), nullable=False),
        sa.Column("storage_path", sa.String(1024), nullable=True),
        sa.Column("media_type", sa.String(128), nullable=True),
        sa.Column("file_type", sa.String(16), nullable=True),
        sa.Column("size_bytes", sa.BigInteger, nullable=True),
        sa.Column("sha256", sa.String(64), nullable=True),
        sa.Column("upload_status", sa.String(16), nullable=False, server_default="uploading"),
        sa.Column("validation_status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("uploaded_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_domain_uploaded_files_seq_test_id", "domain_uploaded_files", ["sequencing_test_id"])

    # ─── domain_variants ────────────────────────────────────────────────────
    op.create_table(
        "domain_variants",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("sequencing_test_id", sa.String(36), sa.ForeignKey("domain_sequencing_tests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("gene_id", sa.String(36), sa.ForeignKey("domain_genes.id", ondelete="SET NULL"), nullable=True),
        sa.Column("gene_symbol", sa.String(32), nullable=False),
        sa.Column("chromosome", sa.String(16), nullable=False),
        sa.Column("position", sa.Integer, nullable=False),
        sa.Column("reference", sa.String(256), nullable=False),
        sa.Column("alternate", sa.String(256), nullable=False),
        sa.Column("genome_build", sa.String(32), nullable=False),
        sa.Column("variant_type", sa.String(32), nullable=False),
        sa.Column("transcript", sa.String(64), nullable=True),
        sa.Column("hgvs_g", sa.String(256), nullable=True),
        sa.Column("hgvs_c", sa.String(256), nullable=True),
        sa.Column("hgvs_p", sa.String(256), nullable=True),
        sa.Column("vaf", sa.Float, nullable=True),
        sa.Column("read_depth", sa.Integer, nullable=True),
        sa.Column("origin", sa.String(16), nullable=False, server_default="unknown"),
        sa.Column("clinical_significance", sa.String(128), nullable=True),
        sa.Column("oncogenicity", sa.String(16), nullable=False, server_default="not_assessed"),
        sa.Column("driver_status", sa.String(16), nullable=False, server_default="unknown"),
        sa.Column("zygosity", sa.String(16), nullable=False, server_default="unknown"),
        sa.Column("source_record_id", sa.String(256), nullable=True),
        sa.Column("annotation_version", sa.String(64), nullable=True),
        sa.Column("normalization_status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_domain_variants_seq_test_id", "domain_variants", ["sequencing_test_id"])
    op.create_index("ix_domain_variants_gene_symbol", "domain_variants", ["gene_symbol"])
    op.create_index("ix_domain_variants_position", "domain_variants", ["chromosome", "position"])

    # ─── domain_drugs ───────────────────────────────────────────────────────
    op.create_table(
        "domain_drugs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("generic_name", sa.String(256), nullable=True),
        sa.Column("drugbank_id", sa.String(64), nullable=True, unique=True),
        sa.Column("atc_codes", sa.JSON, nullable=True),
        sa.Column("mechanism_of_action", sa.Text, nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("approval_status", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_domain_drugs_name", "domain_drugs", ["name"])

    # ─── domain_drug_targets ────────────────────────────────────────────────
    op.create_table(
        "domain_drug_targets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("drug_id", sa.String(36), sa.ForeignKey("domain_drugs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("gene_symbol", sa.String(32), nullable=False),
        sa.Column("target_type", sa.String(64), nullable=True),
        sa.Column("interaction_type", sa.String(128), nullable=True),
        sa.Column("source", sa.String(64), nullable=True),
        sa.Column("source_id", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_domain_drug_targets_drug_id", "domain_drug_targets", ["drug_id"])
    op.create_index("ix_domain_drug_targets_gene_symbol", "domain_drug_targets", ["gene_symbol"])

    # ─── domain_publications ────────────────────────────────────────────────
    op.create_table(
        "domain_publications",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("title", sa.String(1024), nullable=False),
        sa.Column("authors", sa.JSON, nullable=True),
        sa.Column("journal", sa.String(256), nullable=True),
        sa.Column("year", sa.Integer, nullable=True),
        sa.Column("doi", sa.String(128), nullable=True, unique=True),
        sa.Column("pmid", sa.String(32), nullable=True, unique=True),
        sa.Column("abstract", sa.Text, nullable=True),
        sa.Column("keywords", sa.JSON, nullable=True),
        sa.Column("url", sa.String(1024), nullable=True),
        sa.Column("citation_count", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_domain_publications_title", "domain_publications", ["title"])

    # ─── domain_clinical_trials ─────────────────────────────────────────────
    op.create_table(
        "domain_clinical_trials",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("nct_id", sa.String(32), nullable=True, unique=True),
        sa.Column("title", sa.String(1024), nullable=False),
        sa.Column("phase", sa.String(32), nullable=True),
        sa.Column("status", sa.String(64), nullable=True),
        sa.Column("conditions", sa.JSON, nullable=True),
        sa.Column("interventions", sa.JSON, nullable=True),
        sa.Column("biomarkers", sa.JSON, nullable=True),
        sa.Column("sponsor", sa.String(256), nullable=True),
        sa.Column("locations", sa.JSON, nullable=True),
        sa.Column("enrollment", sa.Integer, nullable=True),
        sa.Column("start_date", sa.Date, nullable=True),
        sa.Column("completion_date", sa.Date, nullable=True),
        sa.Column("url", sa.String(1024), nullable=True),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_domain_clinical_trials_nct_id", "domain_clinical_trials", ["nct_id"])

    # ─── domain_analysis_runs ───────────────────────────────────────────────
    op.create_table(
        "domain_analysis_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("case_id", sa.String(36), sa.ForeignKey("domain_cancer_cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sequencing_test_id", sa.String(36), sa.ForeignKey("domain_sequencing_tests.id", ondelete="CASCADE"), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("pipeline_version", sa.String(64), nullable=True),
        sa.Column("dataset_version", sa.String(64), nullable=True),
        sa.Column("annotation_version", sa.String(64), nullable=True),
        sa.Column("evidence_version", sa.String(64), nullable=True),
        sa.Column("schema_version", sa.String(64), nullable=True),
        sa.Column("git_commit", sa.String(64), nullable=True),
        sa.Column("started_at", sa.DateTime, nullable=True),
        sa.Column("finished_at", sa.DateTime, nullable=True),
        sa.Column("duration_ms", sa.BigInteger, nullable=True),
        sa.Column("warnings", sa.JSON, nullable=True),
        sa.Column("errors", sa.JSON, nullable=True),
        sa.Column("input_manifest", sa.JSON, nullable=True),
        sa.Column("output_manifest", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_domain_analysis_runs_case_id", "domain_analysis_runs", ["case_id"])

    # ─── domain_evidences ────────────────────────────────────────────────────
    op.create_table(
        "domain_evidences",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("evidence_type", sa.String(32), nullable=False),
        sa.Column("source_name", sa.String(128), nullable=False),
        sa.Column("source_record_id", sa.String(256), nullable=True),
        sa.Column("publication_id", sa.String(36), sa.ForeignKey("domain_publications.id", ondelete="SET NULL"), nullable=True),
        sa.Column("clinical_trial_id", sa.String(36), sa.ForeignKey("domain_clinical_trials.id", ondelete="SET NULL"), nullable=True),
        sa.Column("gene_symbol", sa.String(32), nullable=True),
        sa.Column("variant_id", sa.String(36), sa.ForeignKey("domain_variants.id", ondelete="SET NULL"), nullable=True),
        sa.Column("drug_id", sa.String(36), sa.ForeignKey("domain_drugs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("cancer_type", sa.String(64), nullable=True),
        sa.Column("study_type", sa.String(64), nullable=True),
        sa.Column("sample_size", sa.Integer, nullable=True),
        sa.Column("evidence_direction", sa.String(16), nullable=False),
        sa.Column("evidence_level", sa.String(16), nullable=False),
        sa.Column("quality", sa.String(32), nullable=True),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("limitations", sa.Text, nullable=True),
        sa.Column("publication_date", sa.Date, nullable=True),
        sa.Column("retrieved_at", sa.DateTime, nullable=False),
        sa.Column("source_version", sa.String(64), nullable=True),
        sa.Column("license", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_domain_evidences_source_record_id", "domain_evidences", ["source_record_id"])
    op.create_index("ix_domain_evidences_gene_symbol", "domain_evidences", ["gene_symbol"])
    op.create_index("ix_domain_evidences_cancer_type", "domain_evidences", ["cancer_type"])

    # ─── domain_drug_candidates ──────────────────────────────────────────────
    op.create_table(
        "domain_drug_candidates",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("analysis_run_id", sa.String(36), sa.ForeignKey("domain_analysis_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("drug_id", sa.String(36), sa.ForeignKey("domain_drugs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("variant_id", sa.String(36), sa.ForeignKey("domain_variants.id", ondelete="SET NULL"), nullable=True),
        sa.Column("cancer_type", sa.String(64), nullable=False),
        sa.Column("candidate_category", sa.String(32), nullable=False),
        sa.Column("approval_status", sa.String(64), nullable=True),
        sa.Column("off_label", sa.String(64), nullable=True),
        sa.Column("clinical_trial_available", sa.String(64), nullable=True),
        sa.Column("mechanism", sa.Text, nullable=True),
        sa.Column("molecular_rationale", sa.Text, nullable=True),
        sa.Column("evidence_level", sa.String(16), nullable=False),
        sa.Column("confidence", sa.String(32), nullable=True),
        sa.Column("score", sa.Float, nullable=True),
        sa.Column("supporting_evidence_ids", sa.JSON, nullable=True),
        sa.Column("conflicting_evidence_ids", sa.JSON, nullable=True),
        sa.Column("limitations", sa.Text, nullable=True),
        sa.Column("safety_notes", sa.Text, nullable=True),
        sa.Column("explanation", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_domain_drug_candidates_analysis_run_id", "domain_drug_candidates", ["analysis_run_id"])
    op.create_index("ix_domain_drug_candidates_cancer_type", "domain_drug_candidates", ["cancer_type"])

    # ─── domain_reports ──────────────────────────────────────────────────────
    op.create_table(
        "domain_reports",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("analysis_run_id", sa.String(36), sa.ForeignKey("domain_analysis_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("report_type", sa.String(64), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("content", sa.JSON, nullable=True),
        sa.Column("version", sa.String(32), nullable=True),
        sa.Column("generated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_domain_reports_analysis_run_id", "domain_reports", ["analysis_run_id"])

    # ─── domain_consents ─────────────────────────────────────────────────────
    op.create_table(
        "domain_consents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("patient_id", sa.String(36), sa.ForeignKey("domain_patients.id", ondelete="CASCADE"), nullable=False),
        sa.Column("consent_type", sa.String(32), nullable=False),
        sa.Column("granted_at", sa.DateTime, nullable=True),
        sa.Column("revoked_at", sa.DateTime, nullable=True),
        sa.Column("expires_at", sa.DateTime, nullable=True),
        sa.Column("consent_document", sa.String(1024), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_domain_consents_patient_id", "domain_consents", ["patient_id"])

    # ─── domain_audit_logs ────────────────────────────────────────────────────
    op.create_table(
        "domain_audit_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("patient_id", sa.String(36), sa.ForeignKey("domain_patients.id", ondelete="SET NULL"), nullable=True),
        sa.Column("actor", sa.String(256), nullable=True),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("resource_type", sa.String(64), nullable=False),
        sa.Column("resource_id", sa.String(128), nullable=True),
        sa.Column("details", sa.JSON, nullable=True),
        sa.Column("ip_address", sa.String(64), nullable=True),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_domain_audit_logs_patient_id", "domain_audit_logs", ["patient_id"])
    op.create_index("ix_domain_audit_logs_created_at", "domain_audit_logs", ["created_at"])


def downgrade() -> None:
    """Remove all precision oncology domain tables."""
    tables = [
        "domain_audit_logs",
        "domain_consents",
        "domain_reports",
        "domain_drug_candidates",
        "domain_evidences",
        "domain_analysis_runs",
        "domain_clinical_trials",
        "domain_publications",
        "domain_drug_targets",
        "domain_drugs",
        "domain_variants",
        "domain_uploaded_files",
        "domain_sequencing_tests",
        "domain_pathways",
        "domain_proteins",
        "domain_genes",
        "domain_specimens",
        "domain_cancer_cases",
        "domain_patients",
    ]
    for table in tables:
        op.drop_table(table)
