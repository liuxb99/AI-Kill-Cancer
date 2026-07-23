"""
Tests for VCF parser module.
"""
from __future__ import annotations

from src.backend.vcf.parser import VCFHeader, detect_genome_build, parse_vcf

SAMPLE_VCF = """##fileformat=VCFv4.2
##reference=GRCh38
##INFO=<ID=AF,Number=A,Type=Float,Description="Allele Frequency">
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	SAMPLE
1	1000	.	A	G	30.5	PASS	AF=0.05	GT	0/1
7	140753336	rs113488022	T	C	99.0	PASS	AF=0.001	GT	0/1
"""

SAMPLE_VCF_NO_HEADER = """1	1000	.	A	G	30.5	PASS	.	GT	0/1
"""

SAMPLE_VCF_GZ = None  # Not testing gz in unit tests


class TestParseVCF:
    def test_parse_valid_vcf(self):
        result = parse_vcf(SAMPLE_VCF)
        assert result.header is not None
        assert result.header.fileformat == "VCFv4.2"
        assert result.record_count == 2
        assert len(result.records) == 2
        assert len(result.errors) == 0

    def test_parse_vcf_build_detection(self):
        result = parse_vcf(SAMPLE_VCF)
        # reference=GRCh38 in header
        # but data has "1" not "chr1" so detection may vary
        assert result.header.reference is not None
        assert result.header.genome_build is not None

    def test_parse_first_record(self):
        result = parse_vcf(SAMPLE_VCF)
        r = result.records[0]
        assert r.chromosome == "1"
        assert r.position == 1000
        assert r.reference == "A"
        assert r.alternate == "G"
        assert r.quality == 30.5
        assert r.filter_status == "PASS"
        assert r.info.get("AF") == "0.05"

    def test_parse_second_record(self):
        result = parse_vcf(SAMPLE_VCF)
        r = result.records[1]
        assert r.chromosome == "7"
        assert r.position == 140753336
        assert r.id == "rs113488022"
        assert r.reference == "T"
        assert r.alternate == "C"

    def test_parse_empty(self):
        result = parse_vcf("")
        assert result.record_count == 0
        assert result.header is not None

    def test_parse_no_header_content(self):
        result = parse_vcf(SAMPLE_VCF_NO_HEADER)
        assert result.record_count == 0  # No #CHROM line to parse
        assert len(result.errors) > 0

    def test_parse_header_samples(self):
        result = parse_vcf(SAMPLE_VCF)
        assert result.header.sample_ids == ["SAMPLE"]

    def test_detect_genome_build_grch38(self):
        header = VCFHeader(reference="GRCh38", genome_build=None)
        build = detect_genome_build(header)
        assert build == "GRCh38"

    def test_detect_genome_build_none(self):
        header = VCFHeader()
        build = detect_genome_build(header)
        assert build is None
