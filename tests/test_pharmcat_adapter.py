import json
from pathlib import Path

import pytest

from src.backend.adapters.pharmcat import PharmCATAdapter


@pytest.mark.asyncio
async def test_validate_input_requires_vcf():
    adapter = PharmCATAdapter()
    errors = await adapter.validate_input({})
    assert errors == ["vcf_path is required; PharmCAT requires a prepared GRCh38 VCF"]


@pytest.mark.asyncio
async def test_validate_input_requires_grch38(tmp_path: Path):
    vcf = tmp_path / "sample.vcf"
    vcf.write_text("##fileformat=VCFv4.2\n", encoding="utf-8")
    adapter = PharmCATAdapter()
    errors = await adapter.validate_input({"vcf_path": str(vcf), "genome": "GRCh37"})
    assert errors == ["PharmCAT input must use GRCh38/hg38"]


@pytest.mark.asyncio
async def test_health_check_requires_jar():
    adapter = PharmCATAdapter({"jar": "definitely-missing-pharmcat.jar"})
    health = await adapter.health_check()
    assert health["status"] == "unavailable"
    assert "PHARMCAT_JAR" in health["detail"]


def test_load_json_artifacts(tmp_path: Path):
    (tmp_path / "pharmcat.match.json").write_text(json.dumps({"gene": "CYP2C19"}), encoding="utf-8")
    (tmp_path / "pharmcat.phenotype.json").write_text(json.dumps({"phenotype": "example"}), encoding="utf-8")
    (tmp_path / "pharmcat.report.html").write_text("<html>research report</html>", encoding="utf-8")

    records = PharmCATAdapter._load_json_artifacts(tmp_path, "pharmcat")

    assert {record["artifact"] for record in records} == {"match", "phenotype", "report"}
    assert next(record for record in records if record["artifact"] == "match")["payload"]["gene"] == "CYP2C19"


def test_normalize_empty_response_is_failure():
    result = PharmCATAdapter().normalize_response(None)
    assert result.success is False
    assert result.errors
