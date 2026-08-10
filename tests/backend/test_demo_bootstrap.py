from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import func, select

from src.backend.config import _sqlite_database_url, settings
from src.backend.database import session as db_session
from src.backend.demo import bootstrap_demo_dataset
from src.backend.domain.cancer_case import CancerCaseModel
from src.backend.domain.patient import PatientModel
from src.backend.domain.sequencing import SequencingTestModel
from src.backend.domain.specimen import SpecimenModel
from src.backend.domain.variant import VariantModel


@pytest.mark.asyncio
async def test_demo_csv_bootstrap_is_idempotent_and_linked(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(settings, "DEMO_AUTO_BOOTSTRAP", False)
    db_url = _sqlite_database_url(str(tmp_path / "demo.db"))
    await db_session.init_db(db_url)
    try:
        assert db_session.async_session_factory is not None

        first = await bootstrap_demo_dataset(db_session.async_session_factory, "data/demo")
        second = await bootstrap_demo_dataset(db_session.async_session_factory, "data/demo")

        assert first == {
            "patients": 3,
            "cases": 3,
            "specimens": 3,
            "sequencing_tests": 3,
            "variants": 3,
        }
        assert second == {
            "patients": 0,
            "cases": 0,
            "specimens": 0,
            "sequencing_tests": 0,
            "variants": 0,
        }

        async with db_session.async_session_factory() as session:
            assert await session.scalar(select(func.count()).select_from(PatientModel)) == 3
            assert await session.scalar(select(func.count()).select_from(CancerCaseModel)) == 3
            assert await session.scalar(select(func.count()).select_from(SpecimenModel)) == 3
            assert await session.scalar(select(func.count()).select_from(SequencingTestModel)) == 3
            assert await session.scalar(select(func.count()).select_from(VariantModel)) == 3

            variants = (await session.scalars(select(VariantModel).order_by(VariantModel.gene_symbol))).all()
            assert {variant.gene_symbol for variant in variants} == {"BRAF", "RET", "NTRK1"}
            assert all(variant.sequencing_test_id is not None for variant in variants)
    finally:
        await db_session.close_db()


def test_demo_dataset_contains_required_csv_files():
    root = Path("data/demo")
    required = {
        "patients.csv",
        "cancer_cases.csv",
        "specimens.csv",
        "sequencing_tests.csv",
        "variants.csv",
    }
    assert required <= {path.name for path in root.glob("*.csv")}
