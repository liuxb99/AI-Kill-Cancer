# API Contract — v0.2.1

> Precision Oncology Foundation Phase 1

## Base URL

```
https://<host>/api/v1
```

## Authentication

Not implemented in Phase 1.

## Common Response Envelope

### Error Response

```json
{
  "detail": {
    "error": "error_code",
    "message": "Human-readable description"
  }
}
```

### Provenance (legacy endpoints)

```json
{
  "provenance": {
    "data_mode": "synthetic|research|production",
    "source": "string",
    "retrieved_at": "ISO8601",
    "disclaimer": "string"
  }
}
```

---

## Patients

### POST /patients — Create Patient

**Request:**
```json
{
  "external_id": "str (optional)",
  "display_name": "str (optional)",
  "birth_year": "int (optional, 1900-2100)",
  "age_range": "str (optional)",
  "sex": "M|F|unknown (optional)",
  "consent_status": "granted|revoked|expired|pending (default: pending)"
}
```

**Response 201:**
```json
{
  "id": "uuid-string",
  "external_id": "str|null",
  "display_name": "str|null",
  "birth_year": "int|null",
  "age_range": "str|null",
  "sex": "str|null",
  "consent_status": "str",
  "created_at": "ISO8601",
  "updated_at": "ISO8601"
}
```

### GET /patients — List Patients

**Query:** `?skip=0&limit=100`

**Response 200:**
```json
{
  "items": [PatientResponse],
  "total": 0,
  "skip": 0,
  "limit": 100
}
```

### GET /patients/{id} — Get Patient

**Response 200:** PatientResponse
**Response 404:** Patient not found
**Response 400:** Invalid UUID

### PATCH /patients/{id} — Update Patient

**Request:** Partial PatientCreate fields.
**Response 200:** PatientResponse
**Response 404:** Patient not found

### DELETE /patients/{id} — Delete Patient

**Response 204:** No content
**Response 404:** Patient not found

---

## Cancer Cases

### POST /cases — Create Cancer Case

**Request:**
```json
{
  "patient_id": "uuid (required)",
  "oncotree_code": "str (optional)",
  "cancer_type": "PTC|FTC|MTC|HCC|PDTC|ATC (required)",
  "histology": "str (optional)",
  "stage": "str (optional)",
  "diagnosis_date": "date (optional)",
  "radioiodine_status": "str (optional)",
  "recurrence_status": "str (optional)",
  "metastatic_sites": ["str", "..."],
  "treatment_history": [{}],
  "current_medications": [{}],
  "clinical_notes": "str (optional)"
}
```

### GET /cases — List Cases

**Query:** `?patient_id=uuid&cancer_type=PTC&skip=0&limit=100`

**Response 200:**
```json
{
  "items": [CancerCaseResponse],
  "total": 0,
  "skip": 0,
  "limit": 100
}
```

### GET /cases/{id} — Get Case

**Response 200:** CancerCaseResponse
**Response 404:** Case not found

---

## Specimens

### POST /specimens — Create Specimen

**Request:**
```json
{
  "case_id": "uuid (required)",
  "specimen_type": "FFPE|fresh_frozen|blood|bone_marrow|FNA|other",
  "collection_site": "str (optional)",
  "collection_date": "date (optional)",
  "tumor_purity": "float 0.0-1.0 (optional)",
  "matched_normal_available": "bool (default: false)",
  "storage_reference": "str (optional)"
}
```

### GET /specimens/{id} — Get Specimen

---

## Sequencing Tests

### POST /sequencing-tests — Create Sequencing Test

**Request:**
```json
{
  "specimen_id": "uuid (required)",
  "laboratory": "str (optional)",
  "assay_name": "str (required)",
  "assay_version": "str (optional)",
  "panel_name": "str (optional)",
  "genome_build": "str (optional)",
  "sequencing_depth": "float (optional)",
  "minimum_detectable_vaf": "float (optional)",
  "test_date": "date (optional)",
  "result_type": "somatic|germline|RNA|protein (default: somatic)",
  "limitations": "str (optional)"
}
```

---

## Uploads

### POST /uploads — Create Upload Record

**Request:**
```json
{
  "sequencing_test_id": "uuid (required)",
  "original_filename": "str (required)",
  "storage_path": "str (optional)",
  "media_type": "str (optional)",
  "file_type": "VCF|VCF.GZ|CSV|TSV|JSON|PDF",
  "size_bytes": "int (optional)",
  "sha256": "str (optional)"
}
```

---

## Variants

### POST /variants/import — Batch Import Variants

**Request:**
```json
{
  "items": [VariantImport]
}
```

**VariantImport:**
```json
{
  "sequencing_test_id": "uuid (required)",
  "gene_symbol": "str (required)",
  "chromosome": "str (required)",
  "position": "int (required)",
  "reference": "str (required)",
  "alternate": "str (required)",
  "genome_build": "str (required)",
  "variant_type": "SNV|indel|copy-number_amplification|copy-number_deletion|fusion|structural_variant|TERT_promoter|MSI_TMB",
  "transcript": "str (optional)",
  "hgvs_g": "str (optional)",
  "hgvs_c": "str (optional)",
  "hgvs_p": "str (optional)",
  "vaf": "float (optional)",
  "read_depth": "int (optional)",
  "origin": "somatic|germline|unknown",
  "oncogenicity": "oncogenic|likely_oncogenic|VUS|likely_benign|benign|not_assessed",
  "driver_status": "driver|likely_driver|passenger|unknown",
  "zygosity": "heterozygous|homozygous|hemizygous|unknown",
  "source_record_id": "str (optional)"
}
```

**Response 201:** list[VariantResponse]

---

## Analyses

### POST /analyses — Create Analysis Run

**Request:**
```json
{
  "case_id": "uuid (required)",
  "sequencing_test_id": "uuid (optional)",
  "pipeline_version": "str (optional)",
  "dataset_version": "str (optional)",
  "annotation_version": "str (optional)",
  "evidence_version": "str (optional)",
  "schema_version": "str (optional)",
  "git_commit": "str (optional)"
}
```

**Response 201:** AnalysisRunResponse (status: "pending")

### GET /analyses/{id} — Get Analysis

**Response 200:** AnalysisRunResponse

### GET /analyses/{id}/graph — Get Visualization Graph

**Response 200:**
```json
{
  "analysis_id": "uuid",
  "status": "completed|pending|not_configured|adapter_unavailable",
  "graph": {
    "nodes": [GraphNode],
    "edges": [GraphEdge],
    "metadata": {}
  }
}
```

**Phase 1 status:** returns `not_configured` with empty graph.

### GET /analyses/{id}/drug-candidates — Get Drug Candidates

**Response 200:**
```json
{
  "items": [DrugCandidateResponse],
  "total": 0
}
```

**Phase 1 status:** returns empty list.

### GET /analyses/{id}/evidence — Get Evidence

**Response 200:**
```json
{
  "status": "found|not_found|not_searched|insufficient_data",
  "items": [EvidenceResponse],
  "total": 0
}
```

**Phase 1 status:** returns `not_searched` with empty list.

---

## Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 204 | Deleted (no content) |
| 400 | Bad request (invalid UUID, validation) |
| 404 | Resource not found |
| 409 | Conflict (duplicate external_id) |
| 422 | Validation error |
| 500 | Internal server error |
| 503 | Service unavailable (model, adapter) |

## Phase 1 Behavior

| Endpoint | Status | Behavior |
|----------|--------|----------|
| POST /variants/import | ✅ CRUD | Stores variants, no annotation |
| GET /analyses/{id}/graph | ⏳ not_configured | Returns empty graph, no 3D data |
| GET /analyses/{id}/drug-candidates | ⏳ not_configured | Returns empty list |
| GET /analyses/{id}/evidence | ⏳ not_searched | Returns empty list with status |
