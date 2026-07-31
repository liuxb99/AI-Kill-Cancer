"""
REVIEW-PHASE3F0-R3 / P0-01：get_db() 自動 commit 造成雙 transaction owner — 驗證測試

問題背景：
- `src/backend/database/session.py` 的 `get_db()` 在 yield 後自動 `await session.commit()`（L22）
- 但 Service 層（如 VariantIngestionService、EvidenceIngestionService）也自行 commit/rollback
- 同一請求存在兩個 transaction owner

修改要求：get_db 移除 auto commit，所有寫入由 Service 管理。

驗證 3 項：
1. Service 成功只 commit 一次
   - 情境 A：VariantIngestionService.bulk_create_variants() 成功 → commit 恰 1 次、rollback 0 次
   - 情境 B：PatientRepository（僅 flush）後手動 commit → Repository 不 commit、Service 層 commit 一次
   - 情境 C：直接驅動 get_db() 生成器，yield 後正常返回 → session 沒有 commit（spy 計數）
2. Service 後段失敗完整 rollback（模擬後段失敗 → rollback 被調用、fresh session 無殘留）
3. endpoint 在 Service 返回後發生例外時，不會留下部分提交資料（目前 get_db auto-commit 會把
   Service 返回後的 endpoint 後段寫入隱式提交 → 測試 FAIL，紅燈）

預期紅燈（修改前）：
- test_situation_c_get_db_does_not_commit  → FAIL（get_db 在 yield 後自動 commit）
- test_endpoint_exception_after_service_leaves_no_data → FAIL（get_db 把 endpoint 後段寫入隱式提交，
  造成 Service + get_db 雙 commit）
其餘為回歸保護（PASS）。
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.backend.database.models import Base


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════


class CountingSession:
    """Proxy 包裝 AsyncSession，統計 commit / rollback 呼叫次數。

    其他屬性/方法（add/flush/execute/refresh/delete...）全部委派給底層 session，
    因此可作為 Service / get_db 的 session 直接使用。
    """

    def __init__(self, session: AsyncSession):
        self._session = session
        self.commit_count = 0
        self.rollback_count = 0
        self.closed = False

    async def commit(self):
        self.commit_count += 1
        await self._session.commit()

    async def rollback(self):
        self.rollback_count += 1
        await self._session.rollback()

    async def close(self):
        self.closed = True
        await self._session.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()

    def __getattr__(self, name):
        return getattr(self._session, name)


class _Factory:
    """模擬 async_session_factory：每次 __call__ 回傳同一個 (spy 包裝的) session。"""

    def __init__(self, session):
        self.session = session

    def __call__(self):
        return self.session


def make_variant_data(sequencing_test_id: uuid.UUID) -> dict:
    """建構單筆 VariantModel 所需的最小完整資料。"""
    return {
        "sequencing_test_id": str(sequencing_test_id),
        "gene_symbol": "BRAF",
        "chromosome": "7",
        "position": 140453136,
        "reference": "A",
        "alternate": "T",
        "genome_build": "GRCh38",
        "variant_type": "SNV",
        "origin": "somatic",
        "oncogenicity": "not_assessed",
        "driver_status": "unknown",
        "zygosity": "unknown",
        "normalization_status": "pending",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
async def db_engine():
    """獨立 sqlite in-memory engine，建好所有需要的 domain 表。"""
    from src.backend.domain.cancer_case import CancerCaseModel  # noqa: F401
    from src.backend.domain.gene import GeneModel  # noqa: F401
    from src.backend.domain.patient import PatientModel  # noqa: F401
    from src.backend.domain.sequencing import SequencingTestModel  # noqa: F401
    from src.backend.domain.specimen import SpecimenModel  # noqa: F401
    from src.backend.domain.variant import VariantModel  # noqa: F401

    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine):
    """每個測試一個獨立 session（不 commit；由測試/Service 管理交易邊界）。"""
    async_session = async_sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False,
    )
    async with async_session() as session:
        yield session


@pytest.fixture
async def upstream_chain(db_session):
    """建立 Patient → CancerCase → Specimen → SequencingTest 的 FK 資料鏈（flush-only）。

    不 commit，讓 Service 決定交易邊界。
    """
    from src.backend.domain.cancer_case import CancerCaseModel
    from src.backend.domain.enums import (
        AnalysisResultTypeEnum,
        CancerTypeEnum,
        ConsentStatusEnum,
        SexEnum,
        SpecimenTypeEnum,
    )
    from src.backend.domain.patient import PatientModel
    from src.backend.domain.sequencing import SequencingTestModel
    from src.backend.domain.specimen import SpecimenModel

    patient = PatientModel(
        display_name="P0-UPSTREAM-PATIENT",
        sex=SexEnum.UNKNOWN,
        consent_status=ConsentStatusEnum.GRANTED,
    )
    db_session.add(patient)
    await db_session.flush()

    case = CancerCaseModel(patient_id=patient.id, cancer_type=CancerTypeEnum.PTC)
    db_session.add(case)
    await db_session.flush()

    specimen = SpecimenModel(case_id=case.id, specimen_type=SpecimenTypeEnum.FFPE)
    db_session.add(specimen)
    await db_session.flush()

    st = SequencingTestModel(
        specimen_id=specimen.id,
        assay_name="P0-TST2",
        result_type=AnalysisResultTypeEnum.SOMATIC,
    )
    db_session.add(st)
    await db_session.flush()

    return {
        "patient_id": patient.id,
        "case_id": case.id,
        "specimen_id": specimen.id,
        "sequencing_test_id": st.id,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 驗證 1：Service 成功只 commit 一次
# ═══════════════════════════════════════════════════════════════════════════════


class TestServiceCommitsExactlyOnce:
    """驗證「get_db 不再 commit」與「Service commit 一次」。"""

    async def test_situation_a_variant_service_commits_exactly_once(
        self,
        db_engine,
        db_session,
        upstream_chain,
    ) -> None:
        """情境 A（B 類既有 Service）：VariantIngestionService.bulk_create_variants() 成功。

        驗證 commit 恰 1 次、rollback 0 次、fresh session 資料存在。
        """
        from src.backend.repositories.variant_repo import VariantRepository
        from src.backend.services.variant_ingestion_service import (
            VariantIngestionService,
        )

        variant_data = make_variant_data(upstream_chain["sequencing_test_id"])
        counting = CountingSession(db_session)

        # ---- Act：Service 成功路徑 ----
        service = VariantIngestionService(counting)
        variants = await service.bulk_create_variants([variant_data])

        # ---- Assert：commit 恰 1 次、rollback 0 次 ----
        assert len(variants) == 1, "Service 應回傳 1 筆 variant"
        assert counting.commit_count == 1, (
            "RED/GREEN: Service 成功路徑應恰好 commit 1 次"
        )
        assert counting.rollback_count == 0, "Service 成功路徑不應 rollback"

        # ---- Assert：fresh session 資料存在 ----
        async_session = async_sessionmaker(
            db_engine, class_=AsyncSession, expire_on_commit=False,
        )
        async with async_session() as fresh:
            repo = VariantRepository(fresh)
            found = await repo.find_by_gene("BRAF")
            assert len(found) == 1, (
                "Service commit 後 fresh session 應能看到資料"
            )

    async def test_situation_b_repository_flush_only_service_commits(
        self,
        db_engine,
        db_session,
    ) -> None:
        """情境 B：Repository 僅 flush、commit 由 Service（模擬）負責一次。

        對應 A 類新 Service 尚未存在的過渡期：直接測既有 Repository 模式，
        重點是驗證「get_db 不再 commit」與「Service commit 一次」。
        """
        from src.backend.domain.patient import PatientModel
        from src.backend.repositories.patient_repo import PatientRepository

        counting = CountingSession(db_session)

        # ---- Act：Repository 僅 flush（不 commit）----
        repo = PatientRepository(counting)
        patient = await repo.create(display_name="P0-SITB-PATIENT")

        # ---- Assert：Repository 不 commit / 不 rollback ----
        assert counting.commit_count == 0, (
            "Repository.create() 應為 flush-only，不應 commit"
        )
        assert counting.rollback_count == 0

        # ---- Act：Service 層（模擬）手動 commit 一次 ----
        await counting.commit()
        assert counting.commit_count == 1, (
            "Service 層應恰 commit 1 次"
        )

        # ---- Assert：fresh session 資料存在 ----
        async_session = async_sessionmaker(
            db_engine, class_=AsyncSession, expire_on_commit=False,
        )
        async with async_session() as fresh:
            found = await fresh.get(PatientModel, patient.id)
            assert found is not None, "commit 後 fresh session 應能看到資料"

    async def test_situation_c_get_db_does_not_commit(
        self,
        db_engine,
        db_session,
        monkeypatch,
    ) -> None:
        """情境 C：直接驅動 get_db() 生成器，yield 後正常返回 → session 沒有 commit。

        目前 get_db() 會在 yield 後自動 `await session.commit()`，
        因此 spy 的 commit_count == 1 → 此測試在修改前 FAIL（紅燈）。
        """
        from src.backend.database import session as session_module
        from src.backend.domain.patient import PatientModel

        async_session = async_sessionmaker(
            db_engine, class_=AsyncSession, expire_on_commit=False,
        )
        async with async_session() as raw:
            counting = CountingSession(raw)
            monkeypatch.setattr(
                session_module, "async_session_factory", _Factory(counting),
            )

            # 驅動 get_db() 生成器，取得 session（模擬 endpoint 拿到 db 依賴）
            gen = session_module.get_db()
            sess = await gen.__anext__()
            assert sess is counting, "get_db 應 yield 我們注入的 session"

            # endpoint 內：寫入一筆資料並 flush（尚未 commit）
            patient = PatientModel(display_name="P0-GETDB-NOCOMMIT")
            sess.add(patient)
            await sess.flush()
            patient_id = patient.id

            # 模擬 endpoint 正常返回 → get_db 恢復執行 yield 之後的程式碼
            with pytest.raises(StopAsyncIteration):
                await gen.__anext__()

            # ---- Assert：get_db 不應自動 commit ----
            assert counting.commit_count == 0, (
                "RED LIGHT: get_db() 不應在 yield 後自動 commit（移除 auto-commit 後此測試轉綠）"
            )

        # ---- Assert：fresh session 查不到資料（未被隱式提交）----
        async_session = async_sessionmaker(
            db_engine, class_=AsyncSession, expire_on_commit=False,
        )
        async with async_session() as fresh:
            found = await fresh.get(PatientModel, patient_id)
            assert found is None, (
                "get_db() 不應隱式提交未 commit 的資料"
            )


# ═══════════════════════════════════════════════════════════════════════════════
# 驗證 2：Service 後段失敗完整 rollback
# ═══════════════════════════════════════════════════════════════════════════════


class TestServiceFailureRollsBack:
    """驗證 Service 後段失敗時完整 rollback、fresh session 無殘留。"""

    async def test_service_failure_rolls_back(
        self,
        db_engine,
        db_session,
        upstream_chain,
        monkeypatch,
    ) -> None:
        """模擬 Service 後段失敗（如 CaseACLService.grant_owner 拋 Exception 的後段步驟）。

        使用 VariantIngestionService 真實 try/except/commit/rollback 程式碼路徑：
        - 前段：repo 寫入 variant 並 flush（成功）
        - 後段：拋出 RuntimeError（模擬後段失敗）
        - Service except → rollback → 無殘留
        """
        from src.backend.domain.variant import VariantModel
        from src.backend.repositories.variant_repo import VariantRepository
        from src.backend.services.variant_ingestion_service import (
            VariantIngestionService,
        )

        counting = CountingSession(db_session)
        service = VariantIngestionService(counting)

        async def failing_bulk_create(items_data):
            """前段成功寫入，後段失敗。"""
            inst = VariantModel(**items_data[0])
            service.repo.db.add(inst)
            await service.repo.db.flush()  # 前段：flush 成功
            raise RuntimeError(
                "late-stage service failure (e.g. ACL grant_owner failed)"
            )

        monkeypatch.setattr(service.repo, "bulk_create", failing_bulk_create)

        variant_data = make_variant_data(upstream_chain["sequencing_test_id"])

        # ---- Act ----
        with pytest.raises(RuntimeError, match="late-stage"):
            await service.bulk_create_variants([variant_data])

        # ---- Assert：rollback 被調用、commit 未被調用 ----
        assert counting.rollback_count == 1, (
            "Service 後段失敗應 rollback 一次"
        )
        assert counting.commit_count == 0, (
            "Service 後段失敗不應 commit"
        )

        # ---- Assert：fresh session 無殘留資料 ----
        async_session = async_sessionmaker(
            db_engine, class_=AsyncSession, expire_on_commit=False,
        )
        async with async_session() as fresh:
            repo = VariantRepository(fresh)
            found = await repo.find_by_gene("BRAF")
            assert len(found) == 0, (
                "Service 後段失敗 rollback 後，fresh session 不應有殘留 variant"
            )


# ═══════════════════════════════════════════════════════════════════════════════
# 驗證 3：endpoint 在 Service 返回後發生例外時，不留下部分提交資料
# ═══════════════════════════════════════════════════════════════════════════════


class TestEndpointExceptionAfterService:
    """驗證 get_db 不應在 Service 返回後隱式提交 endpoint 後段的寫入。"""

    async def test_endpoint_exception_after_service_leaves_no_data(
        self,
        db_engine,
        monkeypatch,
    ) -> None:
        """endpoint 在 Service 返回後發生例外 → get_db 不應留下部分提交資料。

        場景：
        1. Service 寫入資料 A 並自行 commit（Service-owned transaction，commit 1 次）
        2. endpoint 在 Service 返回後又寫入資料 B 並 flush（尚未 commit）
        3. endpoint 後段拋出例外（模擬 response 構建 / 序列化等階段的錯誤）
        4. get_db teardown 恢復 → 目前會執行 auto-commit，把 B 一併隱式提交

        斷言：
        - commit 總次數 == 1（只有 Service 那次；get_db 不應再 commit）
        - fresh session 看不到資料 B（endpoint 後段寫入不應被 get_db 隱式提交）

        目前 get_db auto-commit 會造成 commit_count == 2 且 B 被持久化 → 紅燈 FAIL。
        """
        from src.backend.database import session as session_module
        from src.backend.domain.patient import PatientModel

        async_session = async_sessionmaker(
            db_engine, class_=AsyncSession, expire_on_commit=False,
        )
        async with async_session() as raw:
            counting = CountingSession(raw)
            monkeypatch.setattr(
                session_module, "async_session_factory", _Factory(counting),
            )

            gen = session_module.get_db()
            sess = await gen.__anext__()

            # ── Step 1：Service 寫入資料 A 並自行 commit ──
            service_a = PatientModel(display_name="P0-SVC-COMMITTED")
            sess.add(service_a)
            await sess.flush()
            await sess.commit()  # Service-owned commit（第 1 次）

            # ── Step 2：endpoint 在 Service 返回後又寫入資料 B（未 commit）──
            endpoint_b = PatientModel(display_name="P0-ENDPOINT-PARTIAL")
            sess.add(endpoint_b)
            await sess.flush()
            endpoint_b_id = endpoint_b.id

            # ── Step 3：endpoint 後段拋出例外（被 endpoint 內部處理後正常返回，
            #            模擬 response 構建階段的可恢復錯誤）──
            try:
                raise RuntimeError("endpoint crashed after service returned")
            except RuntimeError:
                pass  # endpoint 捕獲並記錄（回應仍正常返回）

            # ── Step 4：get_db teardown（目前會 auto-commit B）──
            with pytest.raises(StopAsyncIteration):
                await gen.__anext__()

            # ---- Assert：get_db 不應再次 commit ----
            assert counting.commit_count == 1, (
                "RED LIGHT: get_db() 不應在 Service 之後再次 commit"
                "（endpoint 後段的寫入不應被隱式提交）"
            )
            assert counting.rollback_count == 0

        # ---- Assert：fresh session 看不到資料 B（未被 get_db 隱式提交）----
        async_session = async_sessionmaker(
            db_engine, class_=AsyncSession, expire_on_commit=False,
        )
        async with async_session() as fresh:
            found_b = await fresh.get(PatientModel, endpoint_b_id)
            assert found_b is None, (
                "RED LIGHT: get_db() 隱式提交了 endpoint 後段的寫入，"
                "留下部分提交資料；移除 auto-commit 後此測試轉綠"
            )
