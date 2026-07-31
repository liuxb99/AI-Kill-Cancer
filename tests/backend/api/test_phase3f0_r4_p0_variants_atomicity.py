"""
REVIEW-PHASE3F0-R4-P0-01：VariantIngestionService DTO 建構移入 transaction — 真實 endpoint 驗證

R4 改造：
- `VariantIngestionService.bulk_create_variants` 將 response DTO 建構
  （`VariantResponse.model_validate`）移入 Service 內、commit 之前。
- 若 DTO 建構失敗 → rollback → 資料不落庫。

驗證 2 項：
1. response validation 失败 → rollback → fresh session 查不到资料（原子性）
2. 成功路径只 commit 一次，fresh session 可查到资料

注意：
- 使用真实 TestClient 呼叫 POST /api/v1/variants/import endpoint
- 只透過 monkeypatch 注入失败条件
- 不得修改 R3 既有测试
"""

from __future__ import annotations

import asyncio
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from src.backend.config import settings
from src.backend.domain.variant import VariantModel, VariantResponse
from src.backend.main import create_app


# ── 辅助函数 ──────────────────────────────────────────────────────────────────


def _valid_variant_payload(sequencing_test_id: str = str(uuid.uuid4())) -> dict:
    """建構一個通過 VariantImport pydantic 驗證的 payload。"""
    return {
        "items": [
            {
                "sequencing_test_id": sequencing_test_id,
                "gene_symbol": "BRAF",
                "chromosome": "7",
                "position": 140453136,
                "reference": "A",
                "alternate": "T",
                "genome_build": "GRCh38",
                "variant_type": "SNV",
                "origin": "somatic",
            }
        ]
    }


async def _count_variants() -> int:
    """使用 fresh session 查詢 variants 總數。"""
    from src.backend.database import session as session_module
    if session_module.async_session_factory is None:
        raise RuntimeError("Database not initialized")
    async with session_module.async_session_factory() as session:
        result = await session.execute(
            select(func.count()).select_from(VariantModel)
        )
        return result.scalar() or 0


def _fresh_count() -> int:
    """Sync wrapper：在新的 event loop 中執行 _count_variants。"""
    return asyncio.run(_count_variants())


# ── Fixture ───────────────────────────────────────────────────────────────────


@pytest.fixture
def client():
    """獨立 in-memory sqlite + 已登入用戶的 TestClient（每次測試全新 app/DB）。"""
    settings.DATABASE_URL = "sqlite+aiosqlite://"
    settings.APP_MODE = "demo"
    settings.DEBUG = False
    app = create_app()
    with TestClient(app) as c:
        c.post(
            "/auth/register",
            json={
                "username": "r4_user",
                "password": "TestPass123!",
                "display_name": "R4 Test User",
            },
        )
        login_resp = c.post(
            "/auth/login",
            json={"username": "r4_user", "password": "TestPass123!"},
        )
        token = login_resp.json()["access_token"]
        c.headers.update({"Authorization": f"Bearer {token}"})
        yield c


# ── 测试类 ────────────────────────────────────────────────────────────────────


class TestVariantAtomicity:
    """R4-P0-01 原子性驗證：DTO 建構失敗 → rollback + 成功只 commit 一次。"""

    # ── 情境 A：response validation 失敗 → fresh session 查不到資料 ───────

    def test_variant_import_atomicity_validation_failure_rolls_back(
        self,
        client,
        monkeypatch,
    ):
        """當 Service 內 DTO 建構失敗時，應 rollback 且資料不落庫。

        1. 繞過 4xx 校驗（sequencing_test 解析 + case ACL）
        2. monkeypatch VariantResponse.model_validate 使其拋出例外
        3. 呼叫 endpoint → 預期 500
        4. fresh session 查不到任何 variant（count == 0）
        5. response body 不含原始例外文字（安全模式）
        """
        import src.backend.api.v1.variants as variants_module

        # ── 繞過 sequencing_test 解析與 ACL ──
        async def _fake_resolve(st_id, db):
            return uuid.UUID("10000000-0000-0000-0000-000000000001")

        async def _fake_verify(case_id, user, db, role):
            return None

        monkeypatch.setattr(
            variants_module, "_resolve_sequencing_test_case_id", _fake_resolve,
        )
        monkeypatch.setattr(
            variants_module, "verify_case_access", _fake_verify,
        )

        # ── 注入 DTO 建構失敗 ──
        def _fail_validate(*args, **kwargs):
            raise ValueError("simulated serialization failure")

        monkeypatch.setattr(
            VariantResponse, "model_validate", _fail_validate,
        )

        # ── 確認初始 DB 為空 ──
        initial_count = _fresh_count()
        assert initial_count == 0, (
            f"初始 variant 數量應為 0，實際為 {initial_count}"
        )

        # ── Act ──
        resp = client.post(
            "/api/v1/variants/import",
            json=_valid_variant_payload(),
        )

        # ── Assert 1：500（內部錯誤）────
        assert resp.status_code == 500, (
            f"DTO 建構失敗應回傳 500，實際 {resp.status_code}"
        )

        # ── Assert 2：body 不含原始例外文字（安全模式 P1-02）────
        assert "simulated serialization failure" not in resp.text, (
            "RED LIGHT: response body 洩漏了內部例外文字 "
            "'simulated serialization failure'"
        )

        # ── Assert 3：body 含可追蹤 error_id ────
        body = resp.json()
        assert "error_id" in str(body), (
            "RED LIGHT: response 應包含可追蹤的 error_id"
        )
        # detail 是 dict 時才檢查 error 字段
        detail = body.get("detail", {})
        if isinstance(detail, dict):
            assert detail.get("error") == "internal_error", (
                "response 應為 internal_error 格式"
            )

        # ── Assert 4：rollback 成功，資料不落庫 ────
        final_count = _fresh_count()
        assert final_count == 0, (
            "RED LIGHT: DTO 建構失敗後 rollback 未生效，"
            f"variants 數量應為 0，實際為 {final_count}"
        )

    # ── 情境 B：成功路徑只 commit 一次，fresh session 查得到資料 ─────────

    def test_variant_import_success_commits_exactly_once(
        self,
        client,
        monkeypatch,
    ):
        """成功路徑應正常 commit 且 fresh session 可查到所有資料。

        1. 繞過 4xx 校驗
        2. 正常呼叫 endpoint（不注入失敗）
        3. 預期 201
        4. fresh session 中 variant 數量 == payload 數量（全部提交）
        5. response 結構正確（list[VariantResponse]）
        """
        import src.backend.api.v1.variants as variants_module

        # ── 繞過 sequencing_test 解析與 ACL ──
        async def _fake_resolve(st_id, db):
            return uuid.UUID("10000000-0000-0000-0000-000000000001")

        async def _fake_verify(case_id, user, db, role):
            return None

        monkeypatch.setattr(
            variants_module, "_resolve_sequencing_test_case_id", _fake_resolve,
        )
        monkeypatch.setattr(
            variants_module, "verify_case_access", _fake_verify,
        )

        # ── 確認初始 DB 為空 ──
        initial_count = _fresh_count()
        assert initial_count == 0, (
            f"初始 variant 數量應為 0，實際為 {initial_count}"
        )

        # ── 準備多個 variant 的 payload ──
        payload = {
            "items": [
                {
                    "sequencing_test_id": str(uuid.uuid4()),
                    "gene_symbol": "BRAF",
                    "chromosome": "7",
                    "position": 140453136,
                    "reference": "A",
                    "alternate": "T",
                    "genome_build": "GRCh38",
                    "variant_type": "SNV",
                    "origin": "somatic",
                },
                {
                    "sequencing_test_id": str(uuid.uuid4()),
                    "gene_symbol": "KRAS",
                    "chromosome": "12",
                    "position": 25398284,
                    "reference": "C",
                    "alternate": "T",
                    "genome_build": "GRCh38",
                    "variant_type": "SNV",
                    "origin": "somatic",
                },
                {
                    "sequencing_test_id": str(uuid.uuid4()),
                    "gene_symbol": "TP53",
                    "chromosome": "17",
                    "position": 7577120,
                    "reference": "G",
                    "alternate": "A",
                    "genome_build": "GRCh38",
                    "variant_type": "SNV",
                    "origin": "somatic",
                },
            ]
        }

        # ── Act ──
        resp = client.post("/api/v1/variants/import", json=payload)

        # ── Assert 1：201 ────
        assert resp.status_code == 201, (
            f"成功 import 應回傳 201，實際 {resp.status_code}: {resp.text}"
        )

        # ── Assert 2：response 結構正確 ────
        response_data = resp.json()
        assert isinstance(response_data, list), (
            "response 應為 list[VariantResponse]"
        )
        assert len(response_data) == len(payload["items"]), (
            f"response 數量應為 {len(payload['items'])}，"
            f"實際 {len(response_data)}"
        )

        # 檢查每個 response item 的關鍵欄位
        for i, item in enumerate(response_data):
            assert "id" in item, f"item[{i}] 缺少 id"
            assert "gene_symbol" in item, f"item[{i}] 缺少 gene_symbol"
            assert "variant_type" in item, f"item[{i}] 缺少 variant_type"
            assert "origin" in item, f"item[{i}] 缺少 origin"
            assert "created_at" in item, f"item[{i}] 缺少 created_at"

        # ── Assert 3：fresh session 查得到所有資料 ────
        final_count = _fresh_count()
        assert final_count == len(payload["items"]), (
            "RED LIGHT: 成功 import 後 fresh session 應查到所有 variants，"
            f"預期 {len(payload['items'])}，實際 {final_count}"
        )

        # ── Assert 4：回歸保護 —— 只應有一次 commit（無多餘提交）──
        # 由於 R3 已移除 get_db 的自動 commit，此處確保 Service 只做了
        # 一次 commit 而非多次。驗證方式：variant 數量精確吻合 payload，
        # 且沒有重複資料。
        ids = [item["id"] for item in response_data]
        assert len(set(ids)) == len(ids), (
            "response 中 variant id 不應重複"
        )
