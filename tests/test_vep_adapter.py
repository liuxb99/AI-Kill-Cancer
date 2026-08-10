"""Tests for VEP adapter module."""
from __future__ import annotations

from src.backend.pipeline.vep_adapter import VEPAdapter, _build_region_string, _parse_vep_consequence


class TestVEPHelpers:
    def test_build_region_string(self):
        assert _build_region_string("7", 140753336, "A", "T") == "7:140753336-140753336:T"

    def test_build_region_string_with_chr(self):
        assert _build_region_string("chr7", 100, "A", "G") == "7:100-100:G"

    def test_build_region_indel(self):
        assert _build_region_string("1", 100, "AG", "A") == "1:100-101:A"

    def test_parse_vep_consequence(self):
        assert _parse_vep_consequence("missense_variant") == "missense_variant"
        assert _parse_vep_consequence("STOP_GAINED") == "stop_gained"
        assert _parse_vep_consequence("Splice Acceptor") == "splice_acceptor"


class TestVEPAdapter:
    def test_supports(self):
        adapter = VEPAdapter()
        assert adapter.supports("annotate") is True
        assert adapter.supports("vep") is True
        assert adapter.supports("other") is False

    async def test_validate_input_valid(self):
        adapter = VEPAdapter()
        errors = await adapter.validate_input(
            {"variants": [{"chromosome": "7", "position": 140753336, "reference": "A", "alternate": "T"}]}
        )
        assert errors == []

    async def test_validate_input_missing_fields(self):
        adapter = VEPAdapter()
        errors = await adapter.validate_input({"variants": [{"chromosome": "7"}]})
        assert errors == ["Variant 0: missing required fields"]

    async def test_validate_input_empty(self):
        adapter = VEPAdapter()
        assert await adapter.validate_input({}) == ["No variants provided"]

    def test_normalize_raw_vep_response_selects_transcript(self):
        adapter = VEPAdapter()
        result = adapter.normalize_response(
            [
                {
                    "seq_region_name": "7",
                    "start": 140753336,
                    "allele_string": "A/T",
                    "most_severe_consequence": "missense_variant",
                    "transcript_consequences": [
                        {
                            "gene_symbol": "BRAF",
                            "gene_id": "ENSG00000157764",
                            "transcript_id": "ENST00000288602",
                            "consequence_terms": ["missense_variant"],
                            "impact": "MODERATE",
                            "biotype": "protein_coding",
                            "canonical": 1,
                            "mane_select": "NM_004333.6",
                            "hgvsc": "ENST00000288602.11:c.1799T>A",
                            "hgvsp": "ENSP00000288602.6:p.Val600Glu",
                        }
                    ],
                }
            ]
        )
        assert result.success is True
        assert len(result.records) == 1
        assert result.records[0]["gene_symbol"] == "BRAF"
        assert result.records[0]["is_selected"] is True
        assert result.records[0]["is_mane_select"] is True
        assert "Val600Glu" in result.records[0]["hgvs_p"]

    def test_normalize_already_normalized_records(self):
        adapter = VEPAdapter()
        result = adapter.normalize_response({"records": [{"gene_symbol": "RET"}]})
        assert result.success is True
        assert result.records == [{"gene_symbol": "RET"}]

    def test_normalize_empty_response_is_failure(self):
        adapter = VEPAdapter()
        result = adapter.normalize_response(None)
        assert result.success is False
        assert result.errors
