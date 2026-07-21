"""
Tests for VEP adapter module.
"""
from __future__ import annotations

from src.backend.pipeline.vep_adapter import VEPAdapter, _build_region_string, _parse_vep_consequence


class TestVEPHelpers:
    def test_build_region_string(self):
        region = _build_region_string("7", 140753336, "A", "T")
        assert region == "7:140753336-140753336:T"

    def test_build_region_string_with_chr(self):
        region = _build_region_string("chr7", 100, "A", "G")
        assert region == "7:100-100:G"

    def test_build_region_indel(self):
        region = _build_region_string("1", 100, "AG", "A")
        assert region == "1:100-101:A"

    def test_parse_vep_consequence(self):
        assert _parse_vep_consequence("missense_variant") == "missense_variant"
        assert _parse_vep_consequence("STOP_GAINED") == "stop_gained"
        assert _parse_vep_consequence("Splice Acceptor") == "splice_acceptor"


class TestVEPAdapter:
    async def test_health_check(self):
        """Health check should not fail — returns degraded if API unavailable."""
        adapter = VEPAdapter()
        health = await adapter.health_check()
        assert health["status"] in ("ok", "degraded")

    def test_supports(self):
        adapter = VEPAdapter()
        assert adapter.supports("annotate") is True
        assert adapter.supports("vep") is True
        assert adapter.supports("other") is False

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

    async def test_validate_input_no_variants(self):
        adapter = VEPAdapter()
        errors = await adapter.validate_input({"variants": []})
        assert len(errors) > 0
