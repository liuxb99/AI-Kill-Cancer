"""
Tests for DGIdb adapter.
"""
from __future__ import annotations

import pytest
from src.backend.pipeline.dgidb_adapter import DGIdbAdapter


class TestDGIdbAdapter:
    async def test_health_check(self):
        adapter = DGIdbAdapter()
        health = await adapter.health_check()
        assert health["status"] in ("ok", "degraded")

    def test_supports(self):
        adapter = DGIdbAdapter()
        assert adapter.supports("gene") is True
        assert adapter.supports("drug") is True
        assert adapter.supports("other") is False

    async def test_validate_input(self):
        adapter = DGIdbAdapter()
        errors = await adapter.validate_input({"gene": "BRAF"})
        assert len(errors) == 0
        errors = await adapter.validate_input({})
        assert len(errors) > 0

    def test_normalize_results(self):
        adapter = DGIdbAdapter()
        mock_data = {
            "matchedTerms": [{
                "geneName": "BRAF",
                "interactions": [{
                    "drugName": "Vemurafenib",
                    "interactionType": "inhibitor",
                    "interactionScore": 10.0,
                    "sourceDbName": "DrugBank",
                    "pmids": ["12345678"],
                }]
            }]
        }
        records = adapter._normalize_results(mock_data)
        assert len(records) == 1
        assert records[0]["drug_name"] == "Vemurafenib"
        assert records[0]["interaction_type"] == "inhibitor"

    async def test_lookup_gene_unconfigured(self):
        adapter = DGIdbAdapter(config={"api_base": "http://localhost:1"})
        result = await adapter.lookup_gene("BRAF", "test")
        assert result.success is False or result.records == []

    async def test_annotate_no_gene(self):
        adapter = DGIdbAdapter()
        result = await adapter.annotate("", request_id="test")
        assert result.success is False
        assert "No gene" in str(result.errors)
