from __future__ import annotations

import csv
from pathlib import Path

from fastapi import APIRouter, HTTPException

from src.backend.config import settings

router = APIRouter(prefix="/demo", tags=["demo"])


def _rows(name: str) -> list[dict[str, str]]:
    path = Path(settings.DEMO_DATA_DIR) / name
    if not path.is_file():
        raise HTTPException(status_code=503, detail=f"Demo dataset missing: {name}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


@router.get("/status")
async def demo_status():
    files = [
        "patients.csv",
        "cancer_cases.csv",
        "specimens.csv",
        "sequencing_tests.csv",
        "variants.csv",
        "drugs.csv",
        "publications.csv",
        "clinical_trials.csv",
        "evidence.csv",
    ]
    counts = {name.removesuffix(".csv"): len(_rows(name)) for name in files}
    return {
        "mode": settings.APP_MODE,
        "dataset": "bundled-synthetic-csv",
        "synthetic": True,
        "clinical_use": False,
        "counts": counts,
    }


@router.get("/cases")
async def demo_cases():
    patients = {row["demo_patient_key"]: row for row in _rows("patients.csv")}
    specimens = {row["demo_case_key"]: row for row in _rows("specimens.csv")}
    sequencing = {row["demo_specimen_key"]: row for row in _rows("sequencing_tests.csv")}
    variants = {row["demo_sequencing_key"]: row for row in _rows("variants.csv")}
    drugs = {row["demo_drug_key"]: row for row in _rows("drugs.csv")}
    publications = {row["demo_publication_key"]: row for row in _rows("publications.csv")}
    trials = {row["demo_trial_key"]: row for row in _rows("clinical_trials.csv")}
    evidence_by_variant = {row["demo_variant_key"]: row for row in _rows("evidence.csv")}

    items = []
    for case in _rows("cancer_cases.csv"):
        patient = patients[case["demo_patient_key"]]
        specimen = specimens.get(case["demo_case_key"], {})
        seq = sequencing.get(specimen.get("demo_specimen_key", ""), {})
        variant = variants.get(seq.get("demo_sequencing_key", ""), {})
        evidence = evidence_by_variant.get(variant.get("demo_variant_key", ""), {})
        drug = drugs.get(evidence.get("demo_drug_key", ""), {})
        publication = publications.get(evidence.get("demo_publication_key", ""), {})
        trial = trials.get(evidence.get("demo_trial_key", ""), {})
        items.append({
            "case_key": case["demo_case_key"],
            "display_name": patient.get("display_name"),
            "cancer_type": case.get("cancer_type"),
            "stage": case.get("stage"),
            "radioiodine_status": case.get("radioiodine_status"),
            "variant": {
                "gene": variant.get("gene_symbol"),
                "hgvs_p": variant.get("hgvs_p") or variant.get("protein_change"),
                "variant_type": variant.get("variant_type"),
                "driver_status": variant.get("driver_status"),
            },
            "drug": {
                "name": drug.get("name"),
                "mechanism": drug.get("mechanism_of_action"),
            },
            "evidence": {
                "level": evidence.get("evidence_level"),
                "direction": evidence.get("evidence_direction"),
                "summary": evidence.get("summary"),
                "synthetic": True,
            },
            "publication": {"title": publication.get("title"), "journal": publication.get("journal")},
            "clinical_trial": {"id": trial.get("nct_id"), "title": trial.get("title"), "status": trial.get("status")},
        })
    return {"synthetic": True, "clinical_use": False, "items": items, "total": len(items)}
