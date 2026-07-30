"""
T-03: Patient + CancerCase 跨 Repository 原子性測試 — 綠燈

情境：
1. 建立 Patient（使用 PatientRepository，flush-only）
2. 建立 Cancer Case 時注入例外（第二步失敗）
3. Rollback 清除錯誤狀態
4. 驗證 Patient 不存在（全部 rollback）

預期：綠燈
- PatientRepository.create() 使用 flush() 而非 commit()
- Patient 和 CancerCase 在相同交易中，失敗後全部 rollback
"""

from __future__ import annotations

import os
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.backend.database.models import Base


@pytest.fixture
async def db_session():
    """Create a database session for testing. Supports Postgres via DATABASE_URL env var."""
    url = os.environ.get("DATABASE_URL", "sqlite+aiosqlite://")

    from src.backend.domain.cancer_case import CancerCaseModel  # noqa: F401
    from src.backend.domain.patient import PatientModel  # noqa: F401

    if url.startswith("postgresql"):
        engine = create_async_engine(url, echo=False)
    else:
        engine = create_async_engine(url, echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
    await engine.dispose()


class TestPatientCancerCaseAtomicity:
    """測試 PatientRepository + CancerCaseRepository 跨 Repository 原子性。

    這兩個 Repository 都繼承 BaseRepository，create() 使用 flush-only，
    Service 層可以將兩個操作包在同一個交易中。
    """

    async def test_patient_and_cancer_case_cross_repo_atomicity_broken(
        self,
        db_session,
    ) -> None:
        """GREEN LIGHT: Patient 和 CancerCase 可在同一交易中建立。

        情境：
        1. 建立 Patient → PatientRepository.create() flush 取得 PK
        2. 建立 CancerCase → 故意失敗（缺少必要欄位）
        3. Rollback 清除 PendingRollbackError
        4. 驗證 Patient 不存在（全部 rollback）
        """
        from src.backend.repositories.cancer_case_repo import CancerCaseRepository
        from src.backend.repositories.patient_repo import PatientRepository

        # ---- Arrange ----
        patient_repo = PatientRepository(db_session)
        cancer_case_repo = CancerCaseRepository(db_session)

        # ---- Act ----
        # Step 1: 建立 Patient → flush-only
        patient = await patient_repo.create(
            display_name="Atomicity Test Patient",
            external_id="ATOMICITY-PATIENT-001",
        )
        patient_id: uuid.UUID = patient.id

        # 驗證 flush 後 PK 可用
        assert patient_id is not None, "Flush should populate PK"

        # Step 2: 建立 CancerCase → 故意失敗（缺少必要欄位）
        with pytest.raises(Exception):
            await cancer_case_repo.create(
                patient_id=patient_id,
                # 缺少 cancer_type（NOT NULL），資料庫會拋出例外
            )

        # Step 3: Rollback 清除 PendingRollbackError
        await db_session.rollback()

        # ---- Assert ----
        # 驗證 Patient 不存在（交易已被 rollback）
        found = await patient_repo.get(patient_id)
        assert found is None, (
            "✅ GREEN LIGHT PASSED: Patient was NOT committed because "
            "PatientRepository.create() uses flush-only. The rollback cleared "
            "both Patient and CancerCase."
        )

    async def test_patient_and_cancer_case_cross_repo_dual_session(
        self,
    ) -> None:
        """GREEN LIGHT: 使用雙 session 驗證跨 Repository 原子性。

        第一個 session 建立 Patient（成功）和 CancerCase（失敗），
        第二個 session 驗證 Patient 是否存在。

        Session 1 結束時自動 rollback（flush-only），Patient 不被持久化。
        """
        from src.backend.repositories.cancer_case_repo import CancerCaseRepository
        from src.backend.repositories.patient_repo import PatientRepository

        engine = create_async_engine("sqlite+aiosqlite://", echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async_session = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False,
        )

        patient_id: uuid.UUID | None = None

        # ---- Session 1: 建立 Patient（成功）和 CancerCase（失敗）----
        async with async_session() as session1:
            patient_repo = PatientRepository(session1)
            patient = await patient_repo.create(
                display_name="Dual Session Patient",
                external_id="DUAL-SESSION-001",
            )
            patient_id = patient.id

            cancer_case_repo = CancerCaseRepository(session1)
            with pytest.raises(Exception):
                await cancer_case_repo.create(
                    patient_id=patient_id,
                    # 缺少 cancer_type
                )
            # Session 1 結束時 close() → rollback

        # ---- Session 2: 驗證 Patient 是否存在 ----
        async with async_session() as session2:
            patient_repo2 = PatientRepository(session2)
            found = await patient_repo2.get(patient_id)

            assert found is None, (
                "✅ GREEN LIGHT PASSED: Patient was NOT persisted across sessions "
                "because PatientRepository.create() uses flush-only. Session 1 "
                "closure rolled back the transaction."
            )

        await engine.dispose()

    async def test_service_cannot_wrap_patient_and_cancer_case_in_one_transaction(
        self,
    ) -> None:
        """GREEN LIGHT: Service 可以將 Patient 和 CancerCase 包在單一交易中。

        模擬 Service 層的典型場景：
        1. 建立 Patient（只用 flush 取得 PK，不 commit）
        2. 使用 Patient PK 建立 CancerCase
        3. 全部成功後才 commit
        4. 若中間失敗，全部 rollback

        現在 PatientRepository.create() 使用 flush-only，此模式可以實現。
        """
        from src.backend.domain.enums import CancerTypeEnum
        from src.backend.repositories.cancer_case_repo import CancerCaseRepository
        from src.backend.repositories.patient_repo import PatientRepository

        engine = create_async_engine("sqlite+aiosqlite://", echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async_session = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False,
        )

        async with async_session() as session:
            patient_repo = PatientRepository(session)
            cancer_case_repo = CancerCaseRepository(session)

            # Step 1: 建立 Patient（flush-only）
            patient = await patient_repo.create(
                display_name="Transaction Test Patient",
                external_id="TX-TEST-001",
            )

            # Step 2: 建立 CancerCase（flush-only）
            await cancer_case_repo.create(
                patient_id=patient.id,
                cancer_type=CancerTypeEnum.PTC,
            )

            # Step 3: 模擬 Service 層 rollback
            await session.rollback()

            # ---- Assert ----
            # flush-only 模式：rollback 後兩者都不應存在
            found_patient = await patient_repo.get(patient.id)
            assert found_patient is None, (
                "✅ GREEN LIGHT PASSED: Both Patient and CancerCase were rolled "
                "back together because PatientRepository.create() uses flush-only."
            )

        await engine.dispose()
