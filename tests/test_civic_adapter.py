"""
Tests for CIViC adapter.
"""
from __future__ import annotations

from src.backend.pipeline.civic_adapter import CIViCAdapter


class TestCIViCAdapter:
    async def test_health_check(self):
        adapter = CIViCAdapter()
        health = await adapter.health_check()
        assert health["status"] in ("ok", "degraded")

    def test_supports(self):
        adapter = CIViCAdapter()
        assert adapter.supports("variant") is True
        assert adapter.supports("gene") is True
        assert adapter.supports("hgvs") is True
        assert adapter.supports("other") is False

    async def test_validate_input(self):
        adapter = CIViCAdapter()
        errors = await adapter.validate_input({"gene": "BRAF"})
        assert len(errors) == 0
        errors = await adapter.validate_input({})
        assert len(errors) > 0

    async def test_annotate_no_params(self):
        adapter = CIViCAdapter()
        result = await adapter.annotate({}, request_id="test")
        assert result.success is False

    async def test_lookup_gene_not_found_unconfigured(self):
        adapter = CIViCAdapter(config={"api_base": "http://localhost:1"})
        result = await adapter.lookup_gene("BRAF", "test")
        assert result.success is False or result.records == []

    def test_normalize_results_data(self):
        adapter = CIViCAdapter()
        mock_data = [{"id": 123, "gene_symbol": "BRAF", "variant_name": "V600E", "evidence_type": "Predictive", "evidence_direction": "Supports", "evidence_level": "A", "disease": {"name": "Melanoma"}, "drug": {"name": "Vemurafenib"}}]
        records = adapter._normalize_results(mock_data, "http://test")
        assert len(records) == 1
        assert records[0]["gene_symbol"] == "BRAF"
        assert records[0]["evidence_level"] == "Level_1"
        assert records[0]["evidence_direction"] == "supporting"
