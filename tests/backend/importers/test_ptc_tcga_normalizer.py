from src.backend.importers.ptc_tcga.normalizer import (
    deterministic_variant_id,
    normalize_case_record,
)


def test_normalize_case_record_builds_ptc_case_variant_and_outcome():
    record = {
        "submitter_id": "TCGA-ET-0001",
        "project_id": "TCGA-THCA",
        "gender": "female",
        "days_to_birth": -16425,
        "ajcc_pathologic_stage": "Stage I",
        "ajcc_pathologic_t": "T1",
        "ajcc_pathologic_n": "N0",
        "ajcc_pathologic_m": "M0",
        "vital_status": "Alive",
        "days_to_last_follow_up": 1000,
        "variants": [
            {
                "hugo_symbol": "BRAF",
                "chromosome": "7",
                "start_position": 140453136,
                "reference_allele": "A",
                "tumor_seq_allele2": "T",
                "hgvsp_short": "p.V600E",
                "variant_classification": "Missense_Mutation",
            }
        ],
    }

    result = normalize_case_record(record)

    assert result.case_id == "TCGA-ET-0001"
    assert result.source_dataset == "TCGA-THCA"
    assert result.age_range == "40-49"
    assert result.pathologic_stage == "Stage I"
    assert result.variants[0].gene == "BRAF"
    assert result.variants[0].protein_change == "p.V600E"
    assert result.variants[0].variant_id
    assert result.outcomes[0].outcome_type == "vital_status"
    assert result.outcomes[0].outcome_value == "alive"


def test_variant_id_is_deterministic():
    args = ("TCGA-THCA", "CASE-1", "BRAF", "7", 140453136, "A", "T", "p.V600E")
    assert deterministic_variant_id(*args) == deterministic_variant_id(*args)


def test_normalizer_rejects_record_without_case_identifier():
    try:
        normalize_case_record({"gender": "female"})
    except ValueError as exc:
        assert "case_id" in str(exc)
    else:
        raise AssertionError("record without case id must be rejected")
