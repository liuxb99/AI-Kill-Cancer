"""
T-02: BaseRepository Atomicity — Green Light Test (flush-only)

情境：使用真實 BaseRepository.create()
1. 建立 Entity A（成功，flush 取得 PK，不 commit）
2. 建立 Entity B（故意失敗，例如傳入無效資料）
3. Rollback 清除 PendingRollbackError 狀態
4. 驗證 Entity A 不存在（因為整個 transaction 被 rollback）

預期：綠燈
- BaseRepository.create() 使用 flush() 而非 commit()
- Entity A 和 B 在同一個交易中，B 失敗會 rollback A
- 斷言「A 不存在」應通過
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

    # 確保所有依賴的 model 在 create_all 前載入
    from src.backend.domain.patient import PatientModel  # noqa: F401
    from src.backend.domain.cancer_case import CancerCaseModel  # noqa: F401

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


class TestBaseRepositoryAtomicity:
    """測試 BaseRepository flush-only 模式的正確原子性。"""

    async def test_create_auto_commit_breaks_atomicity(self, db_session) -> None:
        """GREEN LIGHT: BaseRepository flush-only 確保原子性。

        情境說明
        ----------
        BaseRepository.create() 現在使用 flush() 而非 commit()：
        1. Entity A 被 flush → 未 commit，仍在交易中
        2. Entity B 建立失敗 → IntegrityError
        3. Rollback 清除 PendingRollbackError 狀態
        4. Entity A 不存在（交易已被 rollback）

        驗證 flush 後 PK 可用（a.id 不是 None）。
        """
        from src.backend.repositories.base import BaseRepository
        from src.backend.domain.patient import PatientModel
        from src.backend.domain.cancer_case import CancerCaseModel

        # ---- Arrange ----
        repo_a = BaseRepository(PatientModel, db_session)

        # ---- Act ----
        # Step 1: 建立 Entity A → flush 取得 PK，不 commit
        a = await repo_a.create(display_name="Entity A")
        a_id: uuid.UUID = a.id

        # 驗證 flush 後 PK 可用
        assert a_id is not None, "Flush should populate PK"

        # Step 2: 建立 Entity B 時故意失敗（缺少必要欄位 cancer_type）
        repo_b = BaseRepository(CancerCaseModel, db_session)
        with pytest.raises(Exception):
            await repo_b.create(
                patient_id=a_id,
                # 缺少 cancer_type（NOT NULL），資料庫會拋出例外
            )

        # Step 3: Rollback 清除 PendingRollbackError 狀態
        await db_session.rollback()

        # ---- Assert ----
        # 驗證 Entity A 不存在（整個交易已被 rollback）
        found = await repo_a.get(a_id)
        assert found is None, (
            "✅ GREEN LIGHT PASSED: Entity A was NOT committed because "
            "BaseRepository.create() uses flush-only. After Entity B failed, "
            "the rollback removed Entity A as well."
        )

    async def test_create_auto_commit_breaks_atomicity_with_two_sessions(
        self,
    ) -> None:
        """GREEN LIGHT: 使用雙 session 驗證原子性。

        在第一個 session 中建立 A（成功）和嘗試建立 B（失敗），
        在第二個乾淨的 session 中驗證 A 是否存在。

        因為 BaseRepository.create() 只 flush 不 commit，A 在步驟 1
        結束後尚未持久化。Session 1 結束時（close）自動 rollback，
        A 和 B 都不存在。
        """
        from src.backend.repositories.base import BaseRepository
        from src.backend.domain.patient import PatientModel
        from src.backend.domain.cancer_case import CancerCaseModel

        # 建立引擎和 sessionmaker
        engine = create_async_engine("sqlite+aiosqlite://", echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async_session = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False,
        )

        a_id: uuid.UUID | None = None

        # ---- Session 1: 建立 A（成功）和 B（失敗）----
        async with async_session() as session:
            repo_a = BaseRepository(PatientModel, session)
            a = await repo_a.create(display_name="Dual-Session Entity A")
            a_id = a.id

            repo_b = BaseRepository(CancerCaseModel, session)
            with pytest.raises(Exception):
                await repo_b.create(
                    patient_id=a_id,
                    # 缺少 cancer_type（NOT NULL）
                )
            # Session 1 結束時 close() → rollback，A 不被持久化

        # ---- Session 2: 驗證 A 是否存在 ----
        async with async_session() as session2:
            repo_a2 = BaseRepository(PatientModel, session2)
            found = await repo_a2.get(a_id)

            assert found is None, (
                "✅ GREEN LIGHT PASSED: Entity A was NOT persisted because "
                "BaseRepository.create() uses flush-only. The session 1 closure "
                "rolled back the entire transaction."
            )

        await engine.dispose()

    async def test_base_repo_cannot_group_two_creates_in_one_transaction(
        self,
    ) -> None:
        """GREEN LIGHT: BaseRepository 可以將兩次 create 包在同一個交易中。

        這個測試模擬 Service 層的真實需求：
        1. 建立 Entity A（flush 取得 PK，不 commit）
        2. 使用 A 的 PK 建立 Entity B（外鍵關聯）
        3. Rollback 模擬 Service 層需要 rollback 的場景
        4. 驗證兩者都不存在（flush-only 行為）
        """
        from src.backend.repositories.base import BaseRepository
        from src.backend.domain.patient import PatientModel
        from src.backend.domain.cancer_case import CancerCaseModel
        from src.backend.domain.enums import CancerTypeEnum

        # ---- Arrange ----
        engine = create_async_engine("sqlite+aiosqlite://", echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async_session = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False,
        )

        async with async_session() as session:
            repo_a = BaseRepository(PatientModel, session)
            repo_b = BaseRepository(CancerCaseModel, session)

            # ---- Act ----
            # 步驟 1: 建立 A → flush 取得 PK
            a = await repo_a.create(display_name="Entity A for Transaction Test")

            # 步驟 2: 建立 B，使用 A 的 PK（flush-only）
            await repo_b.create(
                patient_id=a.id,
                cancer_type=CancerTypeEnum.PTC,
            )

            # 步驟 3: 手動 rollback（模擬 Service 層需要 rollback 的場景）
            await session.rollback()

            # ---- Assert ----
            # 因為 flush-only，rollback 後兩者都應不存在
            found_a = await repo_a.get(a.id)
            assert found_a is None, (
                "✅ GREEN LIGHT PASSED: Entity A was rolled back with Entity B "
                "because BaseRepository.create() uses flush-only."
            )

        await engine.dispose()
