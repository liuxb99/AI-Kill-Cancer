from __future__ import annotations

import pytest

from src.backend.api.v1.demo import demo_cases, demo_status


@pytest.mark.asyncio
async def test_demo_status_reports_complete_synthetic_dataset():
    payload = await demo_status()
    assert payload["synthetic"] is True
    assert payload["clinical_use"] is False
    assert payload["dataset"] == "bundled-synthetic-csv"
    assert payload["counts"]["patients"] == 3
    assert payload["counts"]["variants"] == 3
    assert payload["counts"]["drugs"] == 3
    assert payload["counts"]["publications"] == 3
    assert payload["counts"]["clinical_trials"] == 3
    assert payload["counts"]["evidence"] == 3


@pytest.mark.asyncio
async def test_demo_cases_exposes_traceable_variant_evidence_drug_chain():
    payload = await demo_cases()
    assert payload["synthetic"] is True
    assert payload["clinical_use"] is False
    assert payload["total"] == 3

    by_gene = {item["variant"]["gene"]: item for item in payload["items"]}
    assert {"BRAF", "RET", "NTRK1"} <= set(by_gene)
    assert by_gene["BRAF"]["drug"]["name"] == "Dabrafenib"
    assert by_gene["RET"]["drug"]["name"] == "Selpercatinib"
    assert by_gene["NTRK1"]["drug"]["name"] == "Larotrectinib"

    for item in payload["items"]:
        assert item["evidence"]["synthetic"] is True
        assert item["evidence"]["level"] == "Level_2"
        assert item["publication"]["title"]
        assert item["clinical_trial"]["id"].startswith("DEMO-")
