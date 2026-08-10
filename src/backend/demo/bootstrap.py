from __future__ import annotations

import csv
import json
import uuid
from datetime import date
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.backend.domain.cancer_case import CancerCaseModel
from src.backend.domain.enums import (
    AnalysisResultTypeEnum,
    CancerTypeEnum,
    ConsentStatusEnum,
    ConsequenceEnum,
    DriverStatusEnum,
    NormalizationStatusEnum,
    OncogenicityEnum,
    SexEnum,
    SpecimenTypeEnum,
    VariantOriginEnum,
    VariantTypeEnum,
    ZygosityEnum,
)
from src.backend.domain.patient import PatientModel
from src.backend.domain.sequencing import SequencingTestModel
from src.backend.domain.specimen import SpecimenModel
from src.backend.domain.variant import VariantModel

_DEMO_NAMESPACE = uuid.UUID("6f223f16-5f06-4ce4-aedc-fd30cfda4ed3")


def _demo_uuid(kind: str, key: str) -> uuid.UUID:
    return uuid.uuid5(_DEMO_NAMESPACE, f"{kind}:{key}")


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _optional(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def _optional_int(value: str | None) -> int | None:
    value = _optional(value)
    return int(value) if value is not None else None


def _optional_float(value: str | None) -> float | None:
    value = _optional(value)
    return float(value) if value is not None else None


def _optional_date(value: str | None) -> date | None:
    value = _optional(value)
    return date.fromisoformat(value) if value is not None else None


def _json_list(value: str | None) -> list:
    value = _optional(value)
    if value is None:
        return []
    parsed = json.loads(value)
    if not isinstance(parsed, list):
        raise ValueError(f"Expected JSON list, got {type(parsed).__name__}")
    return parsed


async def _exists(session: AsyncSession, model, model_id: uuid.UUID) -> bool:
    return (await session.execute(select(model.id).where(model.id == model_id))).scalar_one_or_none() is not None


_IMPORT_ENTITIES = (
    ("patients", "patients.csv", "demo_patient_key", "patient", PatientModel),
    ("cancer_cases", "cancer_cases.csv", "demo_case_key", "case", CancerCaseModel),
    ("specimens", "specimens.csv", "demo_specimen_key", "specimen", SpecimenModel),
    ("sequencing_tests", "sequencing_tests.csv", "demo_sequencing_key", "sequencing", SequencingTestModel),
    ("variants", "variants.csv", "demo_variant_key", "variant", VariantModel),
)


async def preview_demo_dataset_duplicates(
    session_factory: async_sessionmaker[AsyncSession],
    data_dir: str | Path,
) -> dict[str, dict[str, object]]:
    """Return deterministic create/skip counts before an idempotent CSV import."""
    root = Path(data_dir)
    preview: dict[str, dict[str, object]] = {}
    async with session_factory() as session:
        for entity, filename, key_column, kind, model in _IMPORT_ENTITIES:
            rows = _read_csv(root / filename)
            existing_keys: list[str] = []
            new_keys: list[str] = []
            for row in rows:
                key = row[key_column].strip()
                model_id = _demo_uuid(kind, key)
                if await _exists(session, model, model_id):
                    existing_keys.append(key)
                else:
                    new_keys.append(key)
            preview[entity] = {
                "total": len(rows),
                "existing": len(existing_keys),
                "new": len(new_keys),
                "existing_keys": existing_keys,
                "new_keys": new_keys,
            }
    return preview


async def bootstrap_demo_dataset(
    session_factory: async_sessionmaker[AsyncSession],
    data_dir: str | Path,
) -> dict[str, int]:
    """Idempotently project the bundled synthetic CSV dataset into the database.

    Stable UUIDv5 identifiers make the same demo dataset reproducible across
    Vercel cold starts, local demo resets, and CI. Existing rows are preserved.
    """
    root = Path(data_dir)
    required = [
        "patients.csv",
        "cancer_cases.csv",
        "specimens.csv",
        "sequencing_tests.csv",
        "variants.csv",
    ]
    missing = [name for name in required if not (root / name).is_file()]
    if missing:
        raise FileNotFoundError(f"Demo dataset is incomplete; missing: {', '.join(missing)}")

    counts = {"patients": 0, "cases": 0, "specimens": 0, "sequencing_tests": 0, "variants": 0}

    async with session_factory() as session:
        try:
            for row in _read_csv(root / "patients.csv"):
                patient_id = _demo_uuid("patient", row["demo_patient_key"])
                if await _exists(session, PatientModel, patient_id):
                    continue
                session.add(
                    PatientModel(
                        id=patient_id,
                        external_id=_optional(row.get("external_id")),
                        display_name=_optional(row.get("display_name")),
                        birth_year=_optional_int(row.get("birth_year")),
                        age_range=_optional(row.get("age_range")),
                        sex=SexEnum(row["sex"]),
                        consent_status=ConsentStatusEnum(row["consent_status"]),
                    )
                )
                counts["patients"] += 1
            await session.flush()

            for row in _read_csv(root / "cancer_cases.csv"):
                case_id = _demo_uuid("case", row["demo_case_key"])
                if await _exists(session, CancerCaseModel, case_id):
                    continue
                session.add(
                    CancerCaseModel(
                        id=case_id,
                        patient_id=_demo_uuid("patient", row["demo_patient_key"]),
                        oncotree_code=_optional(row.get("oncotree_code")),
                        cancer_type=CancerTypeEnum(row["cancer_type"]),
                        histology=_optional(row.get("histology")),
                        stage=_optional(row.get("stage")),
                        diagnosis_date=_optional_date(row.get("diagnosis_date")),
                        radioiodine_status=_optional(row.get("radioiodine_status")),
                        recurrence_status=_optional(row.get("recurrence_status")),
                        metastatic_sites=_json_list(row.get("metastatic_sites")),
                        treatment_history=_json_list(row.get("treatment_history")),
                        current_medications=_json_list(row.get("current_medications")),
                        clinical_notes=_optional(row.get("clinical_notes")),
                    )
                )
                counts["cases"] += 1
            await session.flush()

            for row in _read_csv(root / "specimens.csv"):
                specimen_id = _demo_uuid("specimen", row["demo_specimen_key"])
                if await _exists(session, SpecimenModel, specimen_id):
                    continue
                session.add(
                    SpecimenModel(
                        id=specimen_id,
                        case_id=_demo_uuid("case", row["demo_case_key"]),
                        specimen_type=SpecimenTypeEnum(row["specimen_type"]),
                        collection_site=_optional(row.get("collection_site")),
                        collection_date=_optional_date(row.get("collection_date")),
                        tumor_purity=_optional_float(row.get("tumor_purity")),
                        matched_normal_available=row.get("matched_normal_available", "false").strip().lower() == "true",
                        storage_reference=_optional(row.get("storage_reference")),
                    )
                )
                counts["specimens"] += 1
            await session.flush()

            for row in _read_csv(root / "sequencing_tests.csv"):
                sequencing_id = _demo_uuid("sequencing", row["demo_sequencing_key"])
                if await _exists(session, SequencingTestModel, sequencing_id):
                    continue
                session.add(
                    SequencingTestModel(
                        id=sequencing_id,
                        specimen_id=_demo_uuid("specimen", row["demo_specimen_key"]),
                        laboratory=_optional(row.get("laboratory")),
                        assay_name=row["assay_name"].strip(),
                        assay_version=_optional(row.get("assay_version")),
                        panel_name=_optional(row.get("panel_name")),
                        genome_build=_optional(row.get("genome_build")),
                        sequencing_depth=_optional_float(row.get("sequencing_depth")),
                        minimum_detectable_vaf=_optional_float(row.get("minimum_detectable_vaf")),
                        test_date=_optional_date(row.get("test_date")),
                        result_type=AnalysisResultTypeEnum(row["result_type"]),
                        limitations=_optional(row.get("limitations")),
                    )
                )
                counts["sequencing_tests"] += 1
            await session.flush()

            for row in _read_csv(root / "variants.csv"):
                variant_id = _demo_uuid("variant", row["demo_variant_key"])
                if await _exists(session, VariantModel, variant_id):
                    continue
                consequence = _optional(row.get("consequence"))
                session.add(
                    VariantModel(
                        id=variant_id,
                        sequencing_test_id=_demo_uuid("sequencing", row["demo_sequencing_key"]),
                        gene_symbol=row["gene_symbol"].strip(),
                        chromosome=row["chromosome"].strip(),
                        position=int(row["position"]),
                        reference=row["reference"].strip(),
                        alternate=row["alternate"].strip(),
                        genome_build=row["genome_build"].strip(),
                        variant_type=VariantTypeEnum(row["variant_type"]),
                        transcript=_optional(row.get("transcript")),
                        hgvs_g=_optional(row.get("hgvs_g")),
                        hgvs_c=_optional(row.get("hgvs_c")),
                        hgvs_p=_optional(row.get("hgvs_p")),
                        protein_change=_optional(row.get("protein_change")),
                        consequence=ConsequenceEnum(consequence) if consequence else None,
                        vaf=_optional_float(row.get("vaf")),
                        read_depth=_optional_int(row.get("read_depth")),
                        origin=VariantOriginEnum(row["origin"]),
                        clinical_significance=_optional(row.get("clinical_significance")),
                        oncogenicity=OncogenicityEnum(row["oncogenicity"]),
                        driver_status=DriverStatusEnum(row["driver_status"]),
                        zygosity=ZygosityEnum(row["zygosity"]),
                        normalization_status=NormalizationStatusEnum(row["normalization_status"]),
                        annotation_source=_optional(row.get("annotation_source")),
                        source_record_id=row["demo_variant_key"],
                    )
                )
                counts["variants"] += 1

            await session.commit()
        except Exception:
            await session.rollback()
            raise

    return counts