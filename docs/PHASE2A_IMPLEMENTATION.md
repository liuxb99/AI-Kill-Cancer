# Phase 2A Implementation — Variant Intake, Normalization and Annotation

> Version: 0.3.0
> Date: 2026-07-20

## Scope

```
VCF Upload → Validation → Normalization → VEP → OpenCRAVAT → Standard Variant → Analysis Manifest
```

## Files to Create

```
src/backend/vcf/
├── __init__.py
├── parser.py          # VCF line parsing
├── validator.py       # VCF format validation
└── models.py          # VCF-specific Pydantic schemas

src/backend/pipeline/
├── __init__.py
├── normalization.py   # bcftools adapter + Python fallback
├── vep_adapter.py     # Ensembl REST API adapter
├── opencravat_adapter.py  # OpenCRAVAT adapter (not_configured)
└── analysis_job.py    # Analysis pipeline job manager

src/backend/api/v1/upload_vcf.py  # VCF file upload endpoint

migrations/versions/002_variant_annotation_fields.py

tests/
├── test_vcf_parser.py
├── test_vcf_validator.py
├── test_normalization.py
├── test_vep_adapter.py
├── test_opencravat_adapter.py
├── test_analysis_pipeline.py
└── test_vcf_upload.py

docs/
├── PHASE2A_IMPLEMENTATION.md
├── VCF_PIPELINE.md
├── VEP_INTEGRATION.md
├── OPENCRAVAT_INTEGRATION.md
```

## Files to Modify

```
src/backend/domain/variant.py     — add consequence, dbsnp, clinvar, cosmic, af fields
src/backend/domain/__init__.py     — export new types
src/backend/domain/enums.py        — add ConsequenceEnum
src/backend/main.py                — mount new routes
src/backend/domain/analysis_run.py — update if needed
VERSION                            — 0.2.1 → 0.3.0
src/backend/config.py              — APP_VERSION = 0.3.0
docs/API_CONTRACT.md               — add upload-vcf endpoint
docs/DATABASE_SCHEMA.md            — add new variant columns
docs/CURRENT_STATE.md              — update
```

## Design Decisions

1. **VCF Upload**: Real file upload endpoint with SHA256, metadata, validation
2. **VCF Parser**: Python-based using standard library (no PyVCF dependency)
3. **Genome Build**: Detect from VCF header or explicit user input; reject unknown
4. **Normalization**: bcftools norm via subprocess (Python fallback for basic left-alignment)
5. **VEP**: Ensembl REST API (https://rest.ensembl.org/vep/human/region)
6. **OpenCRAVAT**: Adapter stays not_configured (not installable)
7. **Analysis Pipeline**: In-process job with status tracking
