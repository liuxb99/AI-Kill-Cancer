"""
Tests for VEP adapter error handling and transcript selection.
"""
from __future__ import annotations

import pytest
from src.backend.pipeline.vep_adapter import VEPAdapter, _build_region_string, _extract_vep_results, _parse_vep_consequence


class TestVEPErrorHandling:
    async def test_health_check_degraded(self):
        """Without network, health check returns degraded (not crash)."""
        adapter = VEPAdapter(config={"rest_url": "http://localhost:1"})
        health = await adapter.health_check()
        assert health["status"] in ("ok", "degraded")

    async def test_validate_input_valid(self):
        adapter = VEPAdapter()
        errors = await adapter.validate_input({"variants": [{"chromosome": "7", "position": 140753336, "reference": "A", "alternate": "T"}]})
        assert len(errors) == 0

    async def test_validate_input_missing_fields(self):
        adapter = VEPAdapter()
        errors = await adapter.validate_input({"variants": [{"chromosome": "7"}]})
        assert len(errors) > 0

    async def test_validate_input_empty(self):
        adapter = VEPAdapter()
        errors = await adapter.validate_input({})
        assert len(errors) > 0

    async def test_annotate_timeout_handled(self):
        """Connection timeout should be handled gracefully."""
        adapter = VEPAdapter(config={"rest_url": "http://localhost:1", "timeout": 1})
        result = await adapter.annotate(
            {"variants": [{"chromosome": "7", "position": 140753336, "reference": "A", "alternate": "T"}]},
            request_id="test-timeout",
        )
        assert result.success is False
        assert len(result.errors) > 0

    async def test_annotate_empty_variants(self):
        adapter = VEPAdapter()
        result = await adapter.annotate({"variants": []}, request_id="test-empty")
        assert result.records == []


class TestVEPTranscriptSelection:
    def test_transcript_selection_mane_first(self):
        """MANE Select transcript should be selected first."""
        mock_response = {
            "most_severe_consequence": "missense_variant",
            "transcript_consequences": [
                {
                    "transcript_id": "ENST00000496384",
                    "gene_symbol": "BRAF",
                    "consequence_terms": ["missense_variant"],
                    "biotype": "protein_coding",
                    "impact": "MODERATE",
                    "canonical": 1,
                    "mane_select": None,
                },
                {
                    "transcript_id": "ENST00000646891",
                    "gene_symbol": "BRAF",
                    "consequence_terms": ["missense_variant"],
                    "biotype": "protein_coding",
                    "impact": "MODERATE",
                    "canonical": None,
                    "mane_select": "NM_004333.6",
                },
            ],
        }
        results = _extract_vep_results(mock_response, "7:140753336:T:C")
        selected = [r for r in results if r.get("is_selected")]
        assert len(selected) > 0
        assert selected[0]["is_mane_select"] is True

    def test_transcript_selection_canonical_fallback(self):
        """Without MANE, canonical should be selected."""
        mock_response = {
            "most_severe_consequence": "missense_variant",
            "transcript_consequences": [
                {
                    "transcript_id": "ENST00000496384",
                    "gene_symbol": "BRAF",
                    "consequence_terms": ["missense_variant"],
                    "biotype": "protein_coding",
                    "impact": "MODERATE",
                    "canonical": 1,
                },
                {
                    "transcript_id": "ENST00000512345",
                    "gene_symbol": "BRAF",
                    "consequence_terms": ["missense_variant"],
                    "biotype": "processed_transcript",
                    "impact": "MODIFIER",
                },
            ],
        }
        results = _extract_vep_results(mock_response, "7:140753336:T:C")
        selected = [r for r in results if r.get("is_selected")]
        assert len(selected) > 0
        # The canonical transcript should be selected over processed_transcript
        selected_tc = [tc for tc in mock_response["transcript_consequences"] if tc.get("canonical") == 1][0]
        assert selected[0]["transcript_id"] == selected_tc["transcript_id"]

    def test_transcript_all_preserved(self):
        """All transcripts should be in results, not just selected."""
        mock_response = {
            "most_severe_consequence": "missense_variant",
            "transcript_consequences": [
                {"transcript_id": "ENST001", "gene_symbol": "GENE", "consequence_terms": ["missense_variant"], "impact": "MODERATE"},
                {"transcript_id": "ENST002", "gene_symbol": "GENE", "consequence_terms": ["synonymous_variant"], "impact": "LOW"},
            ],
        }
        results = _extract_vep_results(mock_response, "1:100:A:G")
        assert len(results) == 2
        transcript_ids = [r["transcript_id"] for r in results]
        assert "ENST001" in transcript_ids
        assert "ENST002" in transcript_ids

    def test_no_transcript_consequences(self):
        """Intergenic variants should have a result entry."""
        mock_response = {
            "most_severe_consequence": "intergenic_variant",
            "transcript_consequences": [],
        }
        results = _extract_vep_results(mock_response, "1:100000:A:G")
        assert len(results) == 1
        assert results[0]["consequence"] == "intergenic_variant"
        assert results[0]["is_selected"] is True

    def test_selection_reason(self):
        """Selected transcript should have a selection reason."""
        mock_response = {
            "most_severe_consequence": "missense_variant",
            "transcript_consequences": [
                {"transcript_id": "ENST001", "gene_symbol": "BRAF",
                 "consequence_terms": ["missense_variant"],
                 "biotype": "protein_coding", "impact": "MODERATE",
                 "mane_select": "NM_004333.6"},
            ],
        }
        results = _extract_vep_results(mock_response, "7:140753336:T:C")
        selected = [r for r in results if r.get("is_selected")][0]
        assert "selection_reason" in selected
        assert "MANE" in selected["selection_reason"]


class TestVEPHelpers:
    def test_build_region(self):
        region = _build_region_string("7", 140753336, "A", "T")
        assert region == "7:140753336-140753336:T"

    def test_parse_consequence(self):
        assert _parse_vep_consequence("missense_variant") == "missense_variant"
        assert _parse_vep_consequence("STOP_GAINED") == "stop_gained"
