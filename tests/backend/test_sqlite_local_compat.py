from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from src.backend.config import _sqlite_database_url
from src.backend.database import session as db_session
from src.backend.database.models import CancerStageEnum, Diagnosis, GenderEnum, Patient


@pytest.mark.asyncio
async def test_sqlite_file_init_creates_parent_and_persists_across_sessions(tmp_path: Path):
    db_path = tmp_path / "nested" / "ai-kill-cancer.db"
    db_url = _sqlite_database_url(str(db_path))

    await db_session.init_db(db_url)
    try:
        assert db_path.exists()
        assert db_session.engine is not None
        assert db_session.async_session_factory is not None
        assert db_session.engine.dialect.name == "sqlite"

        async with db_session.async_session_factory() as session:
            patient = Patient(name="LOCAL-SQLITE", age=53, gender=GenderEnum.M)
            session.add(patient)
            await session.commit()
            patient_id = patient.id

        async with db_session.async_session_factory() as session:
            loaded = await session.scalar(select(Patient).where(Patient.id == patient_id))
            assert loaded is not None
            assert loaded.name == "LOCAL-SQLITE"
    finally:
        await db_session.close_db()


@pytest.mark.asyncio
async def test_sqlite_foreign_keys_are_enforced(tmp_path: Path):
    db_url = _sqlite_database_url(str(tmp_path / "fk.db"))
    await db_session.init_db(db_url)
    try:
        assert db_session.async_session_factory is not None
        async with db_session.async_session_factory() as session:
            enabled = (await session.execute(text("PRAGMA foreign_keys"))).scalar_one()
            assert enabled == 1

            diagnosis = Diagnosis(
                patient_id=uuid.uuid4(),
                cancer_type="PTC",
                stage=CancerStageEnum.STAGE_1,
            )
            session.add(diagnosis)
            with pytest.raises(IntegrityError):
                await session.commit()
            await session.rollback()
    finally:
        await db_session.close_db()


@pytest.mark.asyncio
async def test_memory_sqlite_schema_survives_multiple_sessions():
    await db_session.init_db("sqlite+aiosqlite:///:memory:")
    try:
        assert db_session.async_session_factory is not None
        async with db_session.async_session_factory() as session:
            patient = Patient(name="MEMORY-SQLITE", age=40, gender=GenderEnum.F)
            session.add(patient)
            await session.commit()
            patient_id = patient.id

        async with db_session.async_session_factory() as session:
            loaded = await session.scalar(select(Patient).where(Patient.id == patient_id))
            assert loaded is not None
            assert loaded.name == "MEMORY-SQLITE"
    finally:
        await db_session.close_db()


def test_sqlite_url_builder_supports_file_and_memory(tmp_path: Path):
    file_url = _sqlite_database_url(str(tmp_path / "local.db"))
    assert file_url.startswith("sqlite+aiosqlite:///")
    assert file_url.endswith("local.db")
    assert _sqlite_database_url(":memory:") == "sqlite+aiosqlite:///:memory:"
