import gzip

from src.backend.importers.ptc_tcga.downloader import GDCClient, GDCDownloadResult

MAF = """Hugo_Symbol\tChromosome\tStart_Position\tReference_Allele\tTumor_Seq_Allele2\tVariant_Type\tVariant_Classification\tHGVSp_Short\tTumor_Sample_Barcode
BRAF\t7\t140453136\tA\tT\tSNP\tMissense_Mutation\tp.V600E\tTCGA-AB-1234-01A
RET\t10\t43609912\tG\tA\tSNP\tMissense_Mutation\tp.G691S\tTCGA-AB-1234-01A
"""


class FakeGDCClient(GDCClient):
    def fetch_ptc_cases(self, *, size: int = 100, offset: int = 0) -> GDCDownloadResult:
        return GDCDownloadResult(
            records=[{"case_id": "TCGA-AB-1234", "source_dataset": "TCGA-THCA", "variants": []}],
            total=1,
            source_version="test-release",
        )

    def fetch_somatic_mutation_manifest(self, *, size: int = 1000):
        return [{"file_id": "file-1"}, {"file_id": "file-2"}]

    def download_public_file(self, file_id: str) -> bytes:
        return gzip.compress(MAF.encode("utf-8"))


def test_fetch_cases_with_mutations_merges_and_deduplicates_maf():
    result = FakeGDCClient().fetch_ptc_cases_with_mutations(size=1, mutation_files=2)
    assert result.mutation_files == 2
    assert result.mutation_variants == 2
    assert [item["gene"] for item in result.records[0]["variants"]] == ["BRAF", "RET"]
