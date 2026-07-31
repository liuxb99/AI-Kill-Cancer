import gzip

from src.backend.importers.ptc_tcga.maf_parser import (
    merge_variants_into_cases,
    parse_maf_bytes,
    tcga_case_id,
)


MAF = """#version 2.4
Hugo_Symbol\tChromosome\tStart_Position\tReference_Allele\tTumor_Seq_Allele2\tVariant_Classification\tVariant_Type\tTumor_Sample_Barcode\tHGVSp_Short\tdbSNP_RS
BRAF\t7\t140453136\tA\tT\tMissense_Mutation\tSNP\tTCGA-ET-0001-01A\tp.V600E\trs113488022
NRAS\t1\t115256529\tT\tC\tMissense_Mutation\tSNP\tTCGA-ET-0002-01A\tp.Q61R\trs121913254
"""


def test_tcga_case_id_uses_participant_barcode():
    assert tcga_case_id("TCGA-ET-0001-01A-11D") == "TCGA-ET-0001"


def test_parse_plain_and_gzip_maf():
    plain = parse_maf_bytes(MAF.encode())
    compressed = parse_maf_bytes(gzip.compress(MAF.encode()))

    assert plain == compressed
    assert plain["TCGA-ET-0001"][0]["gene"] == "BRAF"
    assert plain["TCGA-ET-0001"][0]["protein_change"] == "p.V600E"
    assert plain["TCGA-ET-0002"][0]["position"] == "115256529"


def test_merge_variants_into_downloaded_cases():
    variants = parse_maf_bytes(MAF.encode())
    cases = [{"case_id": "TCGA-ET-0001"}, {"case_id": "TCGA-ET-9999"}]

    merged = merge_variants_into_cases(cases, variants)

    assert len(merged[0]["variants"]) == 1
    assert merged[1]["variants"] == []
