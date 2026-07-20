# Phase 2A Hardening Plan — Reliable VCF Intake and Reproducible Normalization

> Version: 0.3.1
> Date: 2026-07-20
> Base commit: 30029b463a87ccf6b9f718dc39afac9f6f164302

## Issues Found

| ID | Severity | Issue | File |
|----|----------|-------|------|
| H01 | P0 | VCF.GZ: `.vcf.gz` is decoded as UTF-8 directly (broken) | `upload_vcf.py`, `parser.py` |
| H02 | P0 | Upload: raw exception paths leaked to user | `upload_vcf.py` |
| H03 | P0 | Upload: no file size limit, no decompression bomb protection | `upload_vcf.py` |
| H04 | P0 | Upload: no persistent DB record | `upload_vcf.py` |
| H05 | P0 | Normalization: Python fallback called "normalization" not "minimal_representation" | `normalization.py` |
| H06 | P0 | Normalization: empty REF/ALT possible after trimming | `normalization.py` |
| H07 | P1 | Normalization: symbolic alleles not skipped | `normalization.py` |
| H08 | P1 | bcftools: `request_id="unknown"` hardcoded | `normalization.py` |
| H09 | P1 | bcftools: `normalize_response()` returns NotImplemented | `normalization.py` |
| H10 | P1 | Analysis job: in-memory only, no DB persistence | `analysis_job.py` |
| H11 | P1 | VEP: transcript selection policy undefined (takes any first) | `vep_adapter.py` |
| H12 | P1 | Reference genome: no registry | (missing) |
| H13 | P1 | Upload: no path traversal protection | `upload_vcf.py` |
| H14 | P2 | Upload: no atomic rename | `upload_vcf.py` |
| H15 | P2 | Upload: duplicate SHA256 handling undefined | `upload_vcf.py` |
| H16 | P2 | Normalization: provenance incomplete | `normalization.py` |
| H17 | P2 | Analysis job: missing partial/completed distinction | `analysis_job.py` |

## Fix Plan

1. Rewrite VCF parser/upload for proper .vcf.gz support
2. Add upload security (size limits, path safety, atomic write)
3. Create UploadedFile DB persistence + migration #003
4. Fix normalization semantics: minimal vs canonical
5. Fix normalization algorithm (empty REF/ALT, symbolic alleles)
6. Fix bcftools adapter (provenance, request_id, error handling)
7. Create Reference Genome Registry
8. Fix VEP transcript selection policy + error handling
9. Rewrite AnalysisJob with DB persistence
10. Add transaction boundaries
11. Write comprehensive tests
12. Update documentation
13. Run full verification

## Files to Create

- `src/backend/reference/__init__.py` + `registry.py` — Reference genome registry
- `src/backend/pipeline/reference_registry.py` — Reference lookup/config
- `migrations/versions/003_phase2a_hardening.py` — Schema upgrades
- `tests/test_vcfgz.py` — VCF.GZ tests
- `tests/test_upload_security.py` — Security tests
- `tests/test_upload_persistence.py` — DB persistence tests
- `tests/test_normalization_semantics.py` — Normalization correctness
- `tests/test_bcftools_adapter.py` — Bcftools adapter tests
- `tests/test_reference_registry.py` — Reference registry tests
- `tests/test_vep_mapping.py` — VEP transcript selection tests
- `tests/test_vep_errors.py` — VEP error handling tests
- `tests/test_analysis_persistence.py` — Job persistence tests
- `tests/test_pipeline_transactions.py` — Transaction tests

## Files to Modify

- `src/backend/vcf/parser.py` — Proper gz detection, streaming
- `src/backend/vcf/validator.py` — Max size support
- `src/backend/vcf/models.py` — Additional upload response fields
- `src/backend/api/v1/upload_vcf.py` — Rewrite for persistence + security
- `src/backend/pipeline/normalization.py` — Fix algorithm + semantics
- `src/backend/pipeline/vep_adapter.py` — Transcript policy + error handling
- `src/backend/pipeline/analysis_job.py` — DB persistence
- `src/backend/domain/variant.py` — Additional fields if needed
- `src/backend/domain/uploaded_file.py` — Additional fields for migration #003
- `src/backend/domain/analysis_run.py` — Additional status if needed
- `src/backend/domain/enums.py` — New enums if needed
- `VERSION` — 0.3.0→0.3.1
- `src/backend/config.py` — Version update
