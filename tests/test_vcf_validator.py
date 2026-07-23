"""
Tests for VCF validation module.
"""
from __future__ import annotations

from src.backend.vcf.validator import validate_vcf

VALID_VCF = """##fileformat=VCFv4.2
##reference=GRCh38
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO
1	1000	.	A	G	30.5	PASS	.
7	140753336	rs113488022	T	C	99.0	PASS	.
"""

EMPTY_VCF = ""

NO_FORMAT_VCF = """#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO
1	1000	.	A	G	30	PASS	.
"""

BAD_REF_VCF = """##fileformat=VCFv4.2
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO
1	1000	.	B	X	30	PASS	.
"""


class TestValidateVCF:
    def test_valid_vcf(self):
        result = validate_vcf(VALID_VCF)
        assert result.valid is True
        assert len(result.errors) == 0
        assert result.record_count == 2

    def test_empty_vcf(self):
        result = validate_vcf(EMPTY_VCF)
        assert result.valid is False
        assert any(e.code == "EMPTY_FILE" for e in result.errors)

    def test_missing_fileformat(self):
        result = validate_vcf(NO_FORMAT_VCF)
        assert result.valid is False
        assert any(e.code == "NO_FILEFORMAT" for e in result.errors)

    def test_invalid_reference_allele(self):
        result = validate_vcf(BAD_REF_VCF)
        # B and X are invalid bases
        assert result.valid is False
        ref_errors = [e for e in result.errors if "INVALID_REF" in e.code or "INVALID_ALT" in e.code]
        assert len(ref_errors) > 0

    def test_genome_build_detection(self):
        result = validate_vcf(VALID_VCF, expected_build="GRCh38")
        # CHROM "7" vs "chr7" detection
        # With expected build provided, it'll use that if detection fails
        assert result.genome_build is not None

    def test_record_count(self):
        result = validate_vcf(VALID_VCF)
        assert result.record_count == 2

    def test_sample_count(self):
        result = validate_vcf(VALID_VCF)
        assert result.sample_count == 0  # No sample column in test VCF

    def test_too_few_fields(self):
        bad = """##fileformat=VCFv4.2
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO
1	1000	.	A
"""
        result = validate_vcf(bad)
        assert result.valid is False
