"""
Tests for normalization pipeline.
"""
from __future__ import annotations

import pytest
from src.backend.pipeline.normalization import normalize_minimal_representation, BcftoolsAdapter
from src.backend.domain.enums import NormalizationStatusEnum


class TestPythonNormalization:
    def test_basic_snv_no_normalization_needed(self):
        """SNV with single base ref/alt — no change expected."""
        variants = [("7", 140753336, "A", "T")]
        result = normalize_minimal_representation(variants)
        assert result.status == NormalizationStatusEnum.COMPLETED
        assert len(result.normalized) == 1
        nv = result.normalized[0]
        assert nv.position == 140753336
        assert nv.reference == "A"
        assert nv.alternate == "T"

    def test_left_alignment_with_common_prefix(self):
        """Variant with common prefix should be left-aligned."""
        variants = [("1", 100, "AG", "AT")]
        result = normalize_minimal_representation(variants)
        assert len(result.normalized) == 1
        nv = result.normalized[0]
        assert nv.position == 101

    def test_left_alignment_with_common_suffix(self):
        """Variant with common suffix should be trimmed."""
        variants = [("1", 100, "TAA", "TGA")]
        result = normalize_minimal_representation(variants)
        assert len(result.normalized) == 1

    def test_multiple_variants(self):
        variants = [
            ("7", 140753336, "A", "T"),
            ("7", 140753337, "G", "C"),
            ("5", 1295228, "G", "A"),
        ]
        result = normalize_minimal_representation(variants)
        assert len(result.normalized) == 3
        assert result.status == NormalizationStatusEnum.COMPLETED

    def test_empty_input(self):
        result = normalize_minimal_representation([])
        assert len(result.normalized) == 0
        assert result.status == NormalizationStatusEnum.COMPLETED


class TestBcftoolsAdapter:
    async def test_health_check(self):
        adapter = BcftoolsAdapter()
        health = await adapter.health_check()
        assert health["status"] in ("ok", "degraded")

    def test_supports_normalize(self):
        adapter = BcftoolsAdapter()
        assert adapter.supports("normalize") is True
        assert adapter.supports("foo") is False

    async def test_annotate_fallback(self):
        """Even without bcftools, Python fallback should work."""
        adapter = BcftoolsAdapter()
        result = await adapter.annotate([
            ("7", 140753336, "A", "T"),
            ("1", 100, "AG", "AT"),
        ])
        # Should succeed (with Python fallback if bcftools not available)
        assert result.success is True
        assert len(result.records) == 2
