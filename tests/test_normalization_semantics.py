"""
Tests for normalization semantics and bcftools adapter.
"""
from __future__ import annotations

from src.backend.domain.enums import NormalizationMethodEnum, NormalizationSemanticsEnum, NormalizationStatusEnum
from src.backend.pipeline.normalization import (
    BcftoolsAdapter,
    _is_breakend,
    _is_star,
    _is_symbolic,
    _minimal_representation,
    normalize_minimal_representation,
)


class TestMinimalRepresentation:
    def test_snv_no_change(self):
        ref, alt, shift = _minimal_representation("A", "T")
        assert ref == "A"
        assert alt == "T"
        assert shift == 0

    def test_deletion_common_prefix(self):
        ref, alt, shift = _minimal_representation("AG", "A")
        assert ref == "G"
        assert alt == "N"
        assert shift == 1

    def test_insertion_common_prefix(self):
        ref, alt, shift = _minimal_representation("A", "AG")
        assert ref == "N"
        assert alt == "G"
        assert shift == 1

    def test_mnv_common_prefix_suffix(self):
        ref, alt, shift = _minimal_representation("TAA", "TGA")
        assert shift == 1

    def test_no_empty_ref(self):
        ref, alt, shift = _minimal_representation("A", "")
        assert ref != ""
        assert alt != ""

    def test_no_empty_alt(self):
        ref, alt, shift = _minimal_representation("", "A")
        assert ref != ""
        assert alt != ""

    def test_symbolic_alt_unchanged(self):
        ref, alt, shift = _minimal_representation("N", "<DEL>")
        assert alt == "<DEL>"
        assert shift == 0

    def test_symbolic_dup_unchanged(self):
        ref, alt, shift = _minimal_representation("N", "<DUP>")
        assert alt == "<DUP>"

    def test_star_allele_unchanged(self):
        ref, alt, shift = _minimal_representation("A", "*")
        assert alt == "*"

    def test_breakend_unchanged(self):
        ref, alt, shift = _minimal_representation("A", "G[17:198982[")
        assert "[" in alt

    def test_multi_allelic_skipped(self):
        ref, alt, shift = _minimal_representation("A", "T,G")
        # Multi-allelic is handled at normalize_minimal_representation level
        assert "," in alt

    def test_complex_indel(self):
        ref, alt, shift = _minimal_representation("AGCT", "A")
        assert alt != ""
        assert ref != ""


class TestNormalizeMinimalRepresentation:
    def test_basic_snv(self):
        result = normalize_minimal_representation([("7", 140753336, "A", "T")])
        assert result.status == NormalizationStatusEnum.COMPLETED
        assert result.method == NormalizationMethodEnum.MINIMAL_REPRESENTATION
        assert result.semantics == NormalizationSemanticsEnum.MINIMAL_REPRESENTATION_ONLY
        assert len(result.normalized) == 1

    def test_symbolic_skipped(self):
        result = normalize_minimal_representation([("1", 100, "N", "<DEL>")])
        assert len(result.normalized) == 1
        nv = result.normalized[0]
        assert nv.alternate == "<DEL>"
        assert nv.normalization_method == "not_applicable"

    def test_empty_input(self):
        result = normalize_minimal_representation([])
        assert len(result.normalized) == 0

    def test_multi_allelic_split(self):
        result = normalize_minimal_representation([("1", 100, "A", "T,G")])
        assert len(result.normalized) == 2

    def test_provenance_has_method(self):
        result = normalize_minimal_representation([("7", 140753336, "A", "T")])
        assert result.provenance.get("method") == "minimal_representation"
        assert result.provenance.get("reference_required") is False

    def test_normalization_not_called_canonical(self):
        result = normalize_minimal_representation([("1", 100, "A", "T")])
        assert "canonical" not in result.semantics.value.lower()


class TestSymbolicDetection:
    def test_symbolic_del(self):
        assert _is_symbolic("<DEL>") is True

    def test_symbolic_dup(self):
        assert _is_symbolic("<DUP>") is True

    def test_regular_alt(self):
        assert _is_symbolic("A") is False
        assert _is_symbolic("T") is False

    def test_breakend_detection(self):
        assert _is_breakend("G[17:198982[") is True
        assert _is_breakend("A") is False

    def test_star_detection(self):
        assert _is_star("*") is True
        assert _is_star("A") is False


class TestBcftoolsAdapter:
    async def test_health_check(self):
        adapter = BcftoolsAdapter()
        health = await adapter.health_check()
        assert "status" in health
        assert "canonical_normalization" in health

    def test_supports(self):
        adapter = BcftoolsAdapter()
        assert adapter.supports("normalize") is True
        assert adapter.supports("canonical") is True
        assert adapter.supports("foo") is False

    async def test_annotate_with_fallback(self):
        """Without bcftools or ref, should produce minimal representation."""
        adapter = BcftoolsAdapter()
        result = await adapter.annotate(
            [("7", 140753336, "A", "T")],
            request_id="test-001",
            genome_build="",
        )
        assert result.success is True
        assert len(result.records) >= 1
        # Fallback should NOT claim canonical
        assert "bcftools_python_fallback" in result.source

    async def test_annotate_request_id_propagated(self):
        adapter = BcftoolsAdapter()
        result = await adapter.annotate([("7", 100, "A", "T")], request_id="my-req-123")
        assert result.request_id == "my-req-123"

    def test_normalize_response(self):
        adapter = BcftoolsAdapter()
        from src.backend.adapters.base import AdapterResult
        result = adapter.normalize_response(AdapterResult(
            source="test", source_version="1.0", retrieved_at="now",
            request_id="test", success=True,
        ))
        assert result is not None

    async def test_validate_input(self):
        adapter = BcftoolsAdapter()
        errors = await adapter.validate_input([("1", 100, "A", "T")])
        assert len(errors) == 0
        errors2 = await adapter.validate_input("not a list")
        assert len(errors2) > 0
