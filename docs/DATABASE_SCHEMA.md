# Database Schema — v0.2.1

> Precision Oncology Foundation Phase 1
> Migration: #001 `initial_precision_oncology_foundation`
> 19 domain tables + existing legacy tables

## Conventions

- **UUID PKs**: All tables use UUIDv4 primary keys stored as `String(36)` for cross-database compatibility.
- **Timestamps**: `created_at`, `updated_at` use `DateTime` with `utcnow` defaults.
- **Enums**: Stored as strings for cross-database compatibility (PostgreSQL ENUM emulation).
- **JSON**: Structured data stored in JSON columns; no formal sub-schema in Phase 1.
- **Soft deletes**: Not implemented; records are hard-deleted.
- **Naming**: Domain tables prefixed with `domain_` to avoid conflict with existing `patients`, `diagnoses`, etc.

## Table: domain_patients

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | String(36) | PK | UUID |
| external_id | String(128) | UNIQUE, INDEX | External system ID |
| display_name | String(128) | NULLABLE | Anonymous display code |
| birth_year | Integer | NULLABLE | |
| age_range | String(32) | NULLABLE | e.g. "40-49" |
| sex | String(16) | NULLABLE | M / F / unknown |
| consent_status | String(16) | NOT NULL, DEFAULT 'pending' | granted | revoked | expired | pending |
| created_at | DateTime | NOT NULL | |
| updated_at | DateTime | NOT NULL | |

**Sensitive data:** Avoid storing full names or government IDs.

## Table: domain_cancer_cases

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | String(36) | PK | |
| patient_id | String(36) | FK→domain_patients, CASCADE, INDEX | |
| oncotree_code | String(32) | INDEX | Standardized cancer code |
| cancer_type | String(16) | NOT NULL, INDEX | PTC|FTC|MTC|HCC|PDTC|ATC |
| histology | String(256) | NULLABLE | |
| stage | String(32) | NULLABLE | |
| diagnosis_date | Date | NULLABLE | |
| radioiodine_status | String(64) | NULLABLE | |
| recurrence_status | String(64) | NULLABLE | |
| metastatic_sites | JSON | | Array of site descriptions |
| treatment_history | JSON | | Array of treatment records |
| current_medications | JSON | | Array of medication records |
| clinical_notes | Text | NULLABLE | |
| created_at | DateTime | NOT NULL | |
| updated_at | DateTime | NOT NULL | |

## Table: domain_specimens

| Column | Type | Constraints |
|--------|------|-------------|
| id | String(36) | PK |
| case_id | String(36) | FK→domain_cancer_cases, CASCADE, INDEX |
| specimen_type | String(32) | NOT NULL |
| collection_site | String(256) | NULLABLE |
| collection_date | Date | NULLABLE |
| tumor_purity | Float | NULLABLE (0.0–1.0) |
| matched_normal_available | Boolean | DEFAULT false |
| storage_reference | String(256) | NULLABLE |
| created_at | DateTime | NOT NULL |
| updated_at | DateTime | NOT NULL |

## Table: domain_sequencing_tests

| Column | Type | Constraints |
|--------|------|-------------|
| id | String(36) | PK |
| specimen_id | String(36) | FK→domain_specimens, CASCADE, INDEX |
| laboratory | String(256) | NULLABLE |
| assay_name | String(256) | NOT NULL |
| assay_version | String(64) | NULLABLE |
| panel_name | String(256) | NULLABLE |
| genome_build | String(32) | NULLABLE |
| sequencing_depth | Float | NULLABLE |
| minimum_detectable_vaf | Float | NULLABLE |
| test_date | Date | NULLABLE |
| result_type | String(16) | NOT NULL, DEFAULT 'somatic' |
| limitations | Text | NULLABLE |
| created_at | DateTime | NOT NULL |
| updated_at | DateTime | NOT NULL |

## Table: domain_uploaded_files

| Column | Type | Constraints |
|--------|------|-------------|
| id | String(36) | PK |
| sequencing_test_id | String(36) | FK→domain_sequencing_tests, CASCADE, INDEX |
| original_filename | String(512) | NOT NULL |
| storage_path | String(1024) | NULLABLE |
| media_type | String(128) | NULLABLE |
| file_type | String(16) | NULLABLE |
| size_bytes | BigInteger | NULLABLE |
| sha256 | String(64) | NULLABLE |
| upload_status | String(16) | NOT NULL, DEFAULT 'uploading' |
| validation_status | String(16) | NOT NULL, DEFAULT 'pending' |
| uploaded_at | DateTime | NOT NULL |

## Table: domain_genes

| Column | Type | Constraints |
|--------|------|-------------|
| id | String(36) | PK |
| symbol | String(32) | UNIQUE, NOT NULL, INDEX |
| full_name | String(512) | NULLABLE |
| aliases | JSON | |
| chromosome | String(16) | NULLABLE |
| gene_type | String(64) | NULLABLE |
| description | Text | NULLABLE |
| ncbi_gene_id | String(32) | UNIQUE |
| ensembl_gene_id | String(64) | UNIQUE |
| created_at | DateTime | NOT NULL |
| updated_at | DateTime | NOT NULL |

## Table: domain_proteins

| Column | Type | Constraints |
|--------|------|-------------|
| id | String(36) | PK |
| gene_id | String(36) | FK→domain_genes, CASCADE, INDEX |
| uniprot_id | String(64) | UNIQUE |
| name | String(512) | NULLABLE |
| function | Text | NULLABLE |
| created_at | DateTime | NOT NULL |
| updated_at | DateTime | NOT NULL |

## Table: domain_pathways

| Column | Type | Constraints |
|--------|------|-------------|
| id | String(36) | PK |
| name | String(256) | NOT NULL, INDEX |
| source | String(64) | NULLABLE |
| source_id | String(64) | NULLABLE |
| description | Text | NULLABLE |
| genes | JSON | Array of gene symbols |
| created_at | DateTime | NOT NULL |
| updated_at | DateTime | NOT NULL |

## Table: domain_variants

| Column | Type | Constraints |
|--------|------|-------------|
| id | String(36) | PK |
| sequencing_test_id | String(36) | FK→domain_sequencing_tests, CASCADE, INDEX |
| gene_id | String(36) | FK→domain_genes, SET NULL, INDEX |
| gene_symbol | String(32) | NOT NULL, INDEX |
| chromosome | String(16) | NOT NULL |
| position | Integer | NOT NULL |
| reference | String(256) | NOT NULL |
| alternate | String(256) | NOT NULL |
| genome_build | String(32) | NOT NULL |
| variant_type | String(32) | NOT NULL |
| transcript | String(64) | NULLABLE |
| hgvs_g | String(256) | NULLABLE |
| hgvs_c | String(256) | NULLABLE |
| hgvs_p | String(256) | NULLABLE |
| vaf | Float | NULLABLE |
| read_depth | Integer | NULLABLE |
| origin | String(16) | NOT NULL, DEFAULT 'unknown' |
| clinical_significance | String(128) | NULLABLE |
| oncogenicity | String(16) | NOT NULL, DEFAULT 'not_assessed' |
| driver_status | String(16) | NOT NULL, DEFAULT 'unknown' |
| zygosity | String(16) | NOT NULL, DEFAULT 'unknown' |
| source_record_id | String(256) | NULLABLE |
| annotation_version | String(64) | NULLABLE |
| normalization_status | String(16) | NOT NULL, DEFAULT 'pending' |
| created_at | DateTime | NOT NULL |
| updated_at | DateTime | NOT NULL |

**Indexes:** (chromosome, position) composite, gene_symbol, sequencing_test_id

## Table: domain_drugs

| Column | Type | Constraints |
|--------|------|-------------|
| id | String(36) | PK |
| name | String(256) | NOT NULL, INDEX |
| generic_name | String(256) | NULLABLE |
| drugbank_id | String(64) | UNIQUE |
| atc_codes | JSON | |
| mechanism_of_action | Text | NULLABLE |
| description | Text | NULLABLE |
| approval_status | String(64) | NULLABLE |
| created_at | DateTime | NOT NULL |
| updated_at | DateTime | NOT NULL |

## Table: domain_drug_targets

| Column | Type | Constraints |
|--------|------|-------------|
| id | String(36) | PK |
| drug_id | String(36) | FK→domain_drugs, CASCADE, INDEX |
| gene_symbol | String(32) | NOT NULL, INDEX |
| target_type | String(64) | NULLABLE |
| interaction_type | String(128) | NULLABLE |
| source | String(64) | NULLABLE |
| source_id | String(128) | NULLABLE |
| created_at | DateTime | NOT NULL |

## Table: domain_evidences

| Column | Type | Constraints |
|--------|------|-------------|
| id | String(36) | PK |
| evidence_type | String(32) | NOT NULL |
| source_name | String(128) | NOT NULL |
| source_record_id | String(256) | INDEX |
| publication_id | String(36) | FK→domain_publications, SET NULL |
| clinical_trial_id | String(36) | FK→domain_clinical_trials, SET NULL |
| gene_symbol | String(32) | INDEX |
| variant_id | String(36) | FK→domain_variants, SET NULL |
| drug_id | String(36) | FK→domain_drugs, SET NULL |
| cancer_type | String(64) | INDEX |
| study_type | String(64) | NULLABLE |
| sample_size | Integer | NULLABLE |
| evidence_direction | String(16) | NOT NULL |
| evidence_level | String(16) | NOT NULL |
| quality | String(32) | NULLABLE |
| summary | Text | NULLABLE |
| limitations | Text | NULLABLE |
| publication_date | Date | NULLABLE |
| retrieved_at | DateTime | NOT NULL |
| source_version | String(64) | NULLABLE |
| license | String(128) | NULLABLE |
| created_at | DateTime | NOT NULL |

## Table: domain_drug_candidates

| Column | Type | Constraints |
|--------|------|-------------|
| id | String(36) | PK |
| analysis_run_id | String(36) | FK→domain_analysis_runs, CASCADE, INDEX |
| drug_id | String(36) | FK→domain_drugs, CASCADE |
| variant_id | String(36) | FK→domain_variants, SET NULL |
| cancer_type | String(64) | NOT NULL, INDEX |
| candidate_category | String(32) | NOT NULL |
| approval_status | String(64) | NULLABLE |
| off_label | String(64) | NULLABLE |
| clinical_trial_available | String(64) | NULLABLE |
| mechanism | Text | NULLABLE |
| molecular_rationale | Text | NULLABLE |
| evidence_level | String(16) | NOT NULL |
| confidence | String(32) | NULLABLE |
| score | Float | NULLABLE |
| supporting_evidence_ids | JSON | |
| conflicting_evidence_ids | JSON | |
| limitations | Text | NULLABLE |
| safety_notes | Text | NULLABLE |
| explanation | Text | NULLABLE |
| created_at | DateTime | NOT NULL |

## Table: domain_publications

| Column | Type | Constraints |
|--------|------|-------------|
| id | String(36) | PK |
| title | String(1024) | NOT NULL, INDEX |
| authors | JSON | |
| journal | String(256) | NULLABLE |
| year | Integer | NULLABLE |
| doi | String(128) | UNIQUE |
| pmid | String(32) | UNIQUE |
| abstract | Text | NULLABLE |
| keywords | JSON | |
| url | String(1024) | NULLABLE |
| citation_count | Integer | NULLABLE |
| created_at | DateTime | NOT NULL |

## Table: domain_clinical_trials

| Column | Type | Constraints |
|--------|------|-------------|
| id | String(36) | PK |
| nct_id | String(32) | UNIQUE, INDEX |
| title | String(1024) | NOT NULL |
| phase | String(32) | NULLABLE |
| status | String(64) | NULLABLE |
| conditions | JSON | |
| interventions | JSON | |
| biomarkers | JSON | |
| sponsor | String(256) | NULLABLE |
| locations | JSON | |
| enrollment | Integer | NULLABLE |
| start_date | Date | NULLABLE |
| completion_date | Date | NULLABLE |
| url | String(1024) | NULLABLE |
| summary | Text | NULLABLE |
| created_at | DateTime | NOT NULL |
| updated_at | DateTime | NOT NULL |

## Table: domain_analysis_runs

| Column | Type | Constraints |
|--------|------|-------------|
| id | String(36) | PK |
| case_id | String(36) | FK→domain_cancer_cases, CASCADE, INDEX |
| sequencing_test_id | String(36) | FK→domain_sequencing_tests, SET NULL |
| status | String(32) | NOT NULL, DEFAULT 'pending' |
| pipeline_version | String(64) | NULLABLE |
| dataset_version | String(64) | NULLABLE |
| annotation_version | String(64) | NULLABLE |
| evidence_version | String(64) | NULLABLE |
| schema_version | String(64) | NULLABLE |
| git_commit | String(64) | NULLABLE |
| started_at | DateTime | NULLABLE |
| finished_at | DateTime | NULLABLE |
| duration_ms | BigInteger | NULLABLE |
| warnings | JSON | |
| errors | JSON | |
| input_manifest | JSON | |
| output_manifest | JSON | |
| created_at | DateTime | NOT NULL |

## Table: domain_reports

| Column | Type | Constraints |
|--------|------|-------------|
| id | String(36) | PK |
| analysis_run_id | String(36) | FK→domain_analysis_runs, CASCADE, INDEX |
| report_type | String(64) | NOT NULL |
| title | String(512) | NOT NULL |
| content | JSON | |
| version | String(32) | NULLABLE |
| generated_at | DateTime | NOT NULL |
| created_at | DateTime | NOT NULL |

## Table: domain_consents

| Column | Type | Constraints |
|--------|------|-------------|
| id | String(36) | PK |
| patient_id | String(36) | FK→domain_patients, CASCADE, INDEX |
| consent_type | String(32) | NOT NULL |
| granted_at | DateTime | NULLABLE |
| revoked_at | DateTime | NULLABLE |
| expires_at | DateTime | NULLABLE |
| consent_document | String(1024) | NULLABLE |
| notes | Text | NULLABLE |
| created_at | DateTime | NOT NULL |
| updated_at | DateTime | NOT NULL |

## Table: domain_audit_logs

| Column | Type | Constraints |
|--------|------|-------------|
| id | String(36) | PK |
| patient_id | String(36) | FK→domain_patients, SET NULL, INDEX |
| actor | String(256) | NULLABLE |
| action | String(32) | NOT NULL |
| resource_type | String(64) | NOT NULL |
| resource_id | String(128) | NULLABLE |
| details | JSON | |
| ip_address | String(64) | NULLABLE |
| user_agent | String(512) | NULLABLE |
| created_at | DateTime | NOT NULL, INDEX |

## Relationships Overview

```
Patients ──→ CancerCases ──→ Specimens ──→ SequencingTests ──→ UploadedFiles
    │                                                         │
    │                                                         └──→ Variants ──→ Genes
    │                                                                        │
    └──→ Consents                                                           Proteins
                                                                               │
    AuditLogs                                                              Pathways
                                                                    
    AnalysisRuns ──→ DrugCandidates ──→ Drugs ──→ DrugTargets
                                        │
                                        └──→ Evidences ──→ Publications
                                                          ──→ ClinicalTrials
```
