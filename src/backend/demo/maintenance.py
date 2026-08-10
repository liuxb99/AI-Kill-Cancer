from __future__ import annotations

from pathlib import Path

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.backend.demo.bootstrap import _demo_uuid, _read_csv, bootstrap_demo_dataset
from src.backend.demo.validator import validate_demo_dataset
from src.backend.domain.cancer_case import CancerCaseModel
from src.backend.domain.patient import PatientModel
from src.backend.domain.sequencing import SequencingTestModel
from src.backend.domain.specimen import SpecimenModel
from src.backend.domain.variant import VariantModel


async def reset_demo_dataset(
    session_factory: async_sessionmaker[AsyncSession],
    data_dir: str | Path,
) -> dict[str, int]:
    """Remove only deterministic records owned by the supplied demo dataset.

    The reset is intentionally scoped to UUIDv5 identifiers derived from the
    demo CSV keys.  It never truncates tables and therefore cannot delete local
    research records that happen to share the same tables.
    """
    root = Path(data_dir)
    validation = validate_demo_dataset(root)
    if not validation.ok:
        raise ValueError("Demo dataset validation failed: " + "; ".join(validation.errors))

    ids = {
        "variants": [
            _demo_uuid("variant", row["demo_variant_key"].strip())
            for row in _read_csv(root / "variants.csv")
        ],
        "sequencing_tests": [
            _demo_uuid("sequencing", row["demo_sequencing_key"].strip())
            for row in _read_csv(root / "sequencing_tests.csv")
        ],
        "specimens": [
            _demo_uuid("specimen", row["demo_specimen_key"].strip())
            for row in _read_csv(root / "specimens.csv")
        ],
        "cases": [
            _demo_uuid("case", row["demo_case_key"].strip())
            for row in _read_csv(root / "cancer_cases.csv")
        ],
        "patients": [
            _demo_uuid("patient", row["demo_patient_key"].strip())
            for row in _read_csv(root / "patients.csv")
        ],
    }

    deletion_order = (
        ("variants", VariantModel),
        ("sequencing_tests", SequencingTestModel),
        ("specimens", SpecimenModel),
        ("cases", CancerCaseModel),
        ("patients", PatientModel),
    )
    deleted: dict[str, int] = {}
    async with session_factory() as session:
        try:
            for name, model in deletion_order:
                entity_ids = ids[name]
                if not entity_ids:
                    deleted[name] = 0
                    continue
                result = await session.execute(delete(model).where(model.id.in_(entity_ids)))
                deleted[name] = int(result.rowcount or 0)
            await session.commit()
        except Exception:
            await session.rollback()
            raise
    return deleted


async def rebuild_demo_dataset(
    session_factory: async_sessionmaker[AsyncSession],
    data_dir: str | Path,
) -> dict[str, dict[str, int]]:
    """Reset deterministic demo records and bootstrap them again atomically by phase."""
    deleted = await reset_demo_dataset(session_factory, data_dir)
    inserted = await bootstrap_demo_dataset(session_factory, data_dir)
    return {"deleted": deleted, "inserted": inserted}


__all__ = ["reset_demo_dataset", "rebuild_demo_dataset"]
