from pathlib import Path

import pytest
from sqlalchemy import func, select

from src.backend.config import _sqlite_database_url, settings
from src.backend.database import session as db_session
from src.backend.demo import bootstrap_demo_dataset, rebuild_demo_dataset, reset_demo_dataset
from src.backend.domain.patient import PatientModel
from src.backend.domain.variant import VariantModel


@pytest.mark.asyncio
async def test_reset_only_removes_deterministic_demo_records(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(settings, "DEMO_AUTO_BOOTSTRAP", False)
    await db_session.init_db(_sqlite_database_url(str(tmp_path / "demo-reset.db")))
    try:
        assert db_session.async_session_factory is not None
        inserted = await bootstrap_demo_dataset(db_session.async_session_factory, "data/demo")
        assert inserted["patients"] == 3
        assert inserted["variants"] == 3

        deleted = await reset_demo_dataset(db_session.async_session_factory, "data/demo")
        assert deleted == {
            "variants": 3,
            "sequencing_tests": 3,
            "specimens": 3,
            "cases": 3,
            "patients": 3,
        }

        async with db_session.async_session_factory() as session:
            assert await session.scalar(select(func.count()).select_from(PatientModel)) == 0
            assert await session.scalar(select(func.count()).select_from(VariantModel)) == 0
    finally:
        await db_session.close_db()


@pytest.mark.asyncio
async def test_rebuild_restores_demo_dataset(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(settings, "DEMO_AUTO_BOOTSTRAP", False)
    await db_session.init_db(_sqlite_database_url(str(tmp_path / "demo-rebuild.db")))
    try:
        assert db_session.async_session_factory is not None
        await bootstrap_demo_dataset(db_session.async_session_factory, "data/demo")

        result = await rebuild_demo_dataset(db_session.async_session_factory, "data/demo")

        assert result["deleted"]["patients"] == 3
        assert result["inserted"] == {
            "patients": 3,
            "cases": 3,
            "specimens": 3,
            "sequencing_tests": 3,
            "variants": 3,
        }
        async with db_session.async_session_factory() as session:
            assert await session.scalar(select(func.count()).select_from(PatientModel)) == 3
            assert await session.scalar(select(func.count()).select_from(VariantModel)) == 3
    finally:
        await db_session.close_db()
