from pathlib import Path

import pytest

from src.backend.pipeline.opencravat_adapter import (
    OpenCRAVATAdapter,
    _parse_tsv_reports,
    _write_vcf,
)


def test_write_vcf_from_structured_variants(tmp_path: Path):
    target = tmp_path / "input.vcf"
    _write_vcf(
        target,
        [
            {
                "chromosome": "chr7",
                "position": 140753336,
                "reference": "A",
                "alternate": "T",
                "variant_id": "BRAF-demo",
            }
        ],
        "hg38",
    )

    text = target.read_text(encoding="utf-8")
    assert "##fileformat=VCFv4.2" in text
    assert "##reference=hg38" in text
    assert "7\t140753336\tBRAF-demo\tA\tT" in text


def test_parse_tsv_reports_adds_report_provenance(tmp_path: Path):
    report = tmp_path / "job.variant.tsv"
    report.write_text("base__chrom\tbase__pos\tbase__hugo\n7\t140753336\tBRAF\n", encoding="utf-8")

    records = _parse_tsv_reports(tmp_path)

    assert records == [
        {
            "base__chrom": "7",
            "base__pos": "140753336",
            "base__hugo": "BRAF",
            "_opencravat_report": "job.variant",
        }
    ]


@pytest.mark.asyncio
async def test_validate_input_accepts_variants_and_rejects_bad_genome():
    adapter = OpenCRAVATAdapter()
    valid = await adapter.validate_input(
        {
            "genome": "hg38",
            "variants": [
                {
                    "chromosome": "7",
                    "position": 140753336,
                    "reference": "A",
                    "alternate": "T",
                }
            ],
        }
    )
    assert valid == []

    invalid = await adapter.validate_input(
        {
            "genome": "GRCh37",
            "variants": [
                {
                    "chromosome": "7",
                    "position": 140753336,
                    "reference": "A",
                    "alternate": "T",
                }
            ],
        }
    )
    assert any("Unsupported genome" in message for message in invalid)


@pytest.mark.asyncio
async def test_health_check_is_explicit_when_cli_missing(monkeypatch):
    adapter = OpenCRAVATAdapter({"executable": "definitely-not-installed-opencravat"})
    monkeypatch.setattr(adapter, "_resolved_executable", lambda: None)

    health = await adapter.health_check()

    assert health["status"] == "unavailable"
    assert "OpenCRAVAT CLI not found" in health["detail"]


def test_normalize_response_rejects_empty_payload():
    adapter = OpenCRAVATAdapter()
    result = adapter.normalize_response(None)
    assert result.success is False
    assert result.errors
