"""
REVIEW-PHASE3F0-R3 / P1-02：variants.py catch-all 洩漏 str(e) — 驗證測試

問題背景：
- `src/backend/api/v1/variants.py` 的 `import_variants` catch-all `except Exception` 時
  `raise HTTPException(status_code=500, detail=str(e))`
- 洩漏內部例外文字（SQL、constraint、驅動、內部路徑），且把業務 4xx 壓成 500

修改要求：保留 HTTPException（4xx 透傳）、其餘 log + 固定訊息 + error_id。

驗證 2 項：
1. 內部 DB 例外文字不會出現在 response body
   - mock VariantIngestionService.bulk_create_variants 拋 IntegrityError
     （含敏感文字 "UNIQUE constraint failed: variants.hgvs_notation"）
   - 斷言 response 500、body 不含敏感文字、body 含 error_id
   - 目前 detail=str(e) 洩漏 → 紅燈 FAIL
2. 合法的 4xx 業務錯誤不會被轉換為 500
   - POST /api/v1/variants/import 帶無效 sequencing_test_id → 400（回歸保護，PASS）
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from src.backend.config import settings
from src.backend.main import create_app

# 敏感內部文字：修改前會被 str(e) 直接洩漏到 response body
LEAK_SENTINEL = "UNIQUE constraint failed: variants.hgvs_notation"


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


@pytest.fixture
def client():
    """獨立 in-memory sqlite + 已登入用戶的 TestClient（每次測試全新 app/DB）。"""
    settings.DATABASE_URL = "sqlite+aiosqlite://"  # In-memory SQLite
    settings.APP_MODE = "demo"
    settings.DEBUG = False
    app = create_app()
    with TestClient(app) as c:
        c.post(
            "/auth/register",
            json={
                "username": "r3_user",
                "password": "TestPass123!",
                "display_name": "R3 Test User",
            },
        )
        login_resp = c.post(
            "/auth/login",
            json={"username": "r3_user", "password": "TestPass123!"},
        )
        token = login_resp.json()["access_token"]
        c.headers.update({"Authorization": f"Bearer {token}"})
        yield c


class TestVariantErrors:
    """P1-02 驗證：內部錯誤不洩漏 + 4xx 不透傳 500。"""

    def test_internal_error_not_leaked(
        self,
        client,
        monkeypatch,
    ) -> None:
        """內部 DB 例外文字不應出現在 response body，且 response 含可追蹤 error_id。

        目前實現 `raise HTTPException(status_code=500, detail=str(e))` 會把
        "UNIQUE constraint failed: variants.hgvs_notation" 洩漏到 body → 紅燈 FAIL。
        """
        from sqlalchemy.exc import IntegrityError

        import src.backend.api.v1.variants as variants_module
        from src.backend.services.variant_ingestion_service import (
            VariantIngestionService,
        )

        # ── mock：跳過 data chain 解析與 ACL 檢查，讓請求走到 Service ──
        async def fake_resolve(st_id, db):
            return uuid.UUID("10000000-0000-0000-0000-000000000001")

        async def fake_verify(case_id, user, db, role):
            return None

        monkeypatch.setattr(
            variants_module, "_resolve_sequencing_test_case_id", fake_resolve,
        )
        monkeypatch.setattr(variants_module, "verify_case_access", fake_verify)

        # ── mock：Service 拋內部 DB 例外（含敏感文字）──
        async def fake_bulk_create(self, variants_data):
            raise IntegrityError(
                None,
                {},
                Exception(LEAK_SENTINEL),
            )

        monkeypatch.setattr(
            VariantIngestionService, "bulk_create_variants", fake_bulk_create,
        )

        # ---- Act ----
        resp = client.post(
            "/api/v1/variants/import",
            json=_valid_variant_payload(),
        )

        # ---- Assert 1：500（內部錯誤）----
        assert resp.status_code == 500, (
            f"內部 DB 例外應回傳 500，實際 {resp.status_code}"
        )

        # ---- Assert 2：body 不含敏感內部文字（紅燈點）----
        assert LEAK_SENTINEL not in resp.text, (
            "RED LIGHT: response body 洩漏了內部例外文字 "
            f"({LEAK_SENTINEL!r}); 修改為固定訊息 + error_id 後此測試轉綠"
        )
        assert "UNIQUE constraint failed" not in resp.text

        # ---- Assert 3：body 含可追蹤 error_id（修改要求）----
        body = resp.json()
        assert "error_id" in str(body), (
            "RED LIGHT: response 應包含可追蹤的 error_id"
        )

    def test_business_4xx_not_converted_to_500(
        self,
        client,
    ) -> None:
        """合法 4xx 業務錯誤不應被 catch-all 轉換為 500。

        帶一個格式有效但資料庫中不存在的 sequencing_test_id →
        _resolve_sequencing_test_case_id 拋 HTTPException 400。
        （此測試作為回歸保護；目前 400 發生在 try 區塊外，預期 PASS）
        """
        resp = client.post(
            "/api/v1/variants/import",
            json=_valid_variant_payload(
                "00000000-0000-0000-0000-000000000000",
            ),
        )

        assert resp.status_code == 400, (
            f"無效 sequencing_test_id 應回傳 400 而非 500，實際 {resp.status_code}"
        )
        assert resp.status_code != 500, (
            "合法的 4xx 業務錯誤不應被 catch-all 壓成 500"
        )
