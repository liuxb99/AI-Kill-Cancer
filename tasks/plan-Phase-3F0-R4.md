# Phase-3F0-R4 返工計劃

> 依據 `tasks/requirements.md` §1-2（REVIEW-PHASE3F0-R4 + Master Plan 統一）
> 狀態：已制定，待執行

---

## 0. 目標

| 項 | 內容 |
|----|------|
| R4 P0-01 | VariantIngestionService response DTO 建構移入 commit 前；真實 endpoint 測試證明不落庫 + 成功只 commit 一次 |
| Master Plan | B1/B2 關係統一為「部分重疊 + 啟動 Gate」；External Adapter 數量全文件統一為 10（7 同步 + 3 非同步） |
| 約束 | 不得修改 R3 既有測試放寬原要求；REVIEW 註解保留原文字改 REVIEW-RESOLVED 附 RESOLUTION |

---

## 1. R4 技術方案

### 1.1 問題根因

```python
# 現狀 variant_ingestion_service.py
async def bulk_create_variants(self, variants_data):
    try:
        variants = await self.repo.bulk_create(variants_data)
        await self.db.commit()           # ← commit 在 DTO 建構前
        return variants
    except Exception:
        await self.db.rollback()
        raise

# 現狀 variants.py endpoint
variants = await service.bulk_create_variants(items_data)
return [VariantResponse.model_validate(v) for v in variants]  # ← DTO 建構在 commit 後
```

若 `model_validate` 失敗（validation/序列化錯誤），資料已 commit 無法 rollback → 請求失敗但資料已落庫。

### 1.2 改造方案（REVIEW 建議二）

**將完整 response DTO 建構納入 Service transaction 成功條件**：

```python
# variant_ingestion_service.py（改造後）
from src.backend.domain.variant import VariantResponse  # 新增 import

async def bulk_create_variants(self, variants_data):
    try:
        variants = await self.repo.bulk_create(variants_data)
        # 在 commit 前建構 response DTO；若 validation 失敗 → rollback → 資料不落庫
        response_dtos = [VariantResponse.model_validate(v) for v in variants]
        await self.db.commit()
        return response_dtos
    except Exception:
        await self.db.rollback()
        raise
```

```python
# variants.py endpoint（改造後）
responses = await service.bulk_create_variants(items_data)
return responses  # DTO 已在 Service 內建構並 commit
```

### 1.3 依賴檢查
- `VariantResponse` 定義在 `src/backend/domain/variant.py`，Service 新增 import 無循環依賴
- `bulk_create_variants` 的呼叫者：grep 確認僅 `variants.py` 一處（`api/v1/variants.py` L67）

---

## 2. R4 測試設計（真實 endpoint）

### 2.1 測試檔案
新檔 `tests/backend/api/test_phase3f0_r4_p0_variants_atomicity.py`

### 2.2 情境 A：response validation 失敗 → fresh session 查不到資料

**方法**：真實 TestClient 呼叫 `POST /api/v1/variants/import`，透過 monkeypatch 讓 Service 內的 `VariantResponse.model_validate` 拋 `pydantic.ValidationError`（模擬序列化/validation 失敗）。

```python
# 1. 建立 TestClient app（含真實 auth）
# 2. 準備有效 variants payload（確保通過所有 4xx 校驗一直到 Service 寫入成功）
# 3. 在 Service 的 model_validate 位置注入失敗
#    方式：monkeypatch VariantResponse.model_validate → 拋 ValidationError
#    或用 dependency override 覆寫 variant_repo，讓它回傳無法 validate 的 VariantModel
#    （推薦後者：repo 寫入真實 DB，但回傳的 model 缺 VariantResponse 必填欄位）
# 4. 呼叫 endpoint → 預期 500
# 5. 用 fresh session 查詢：變異記錄 count == 0（證明 rollback，資料不落庫）
```

### 2.3 情境 B：成功路徑只 commit 一次

**方法**：用 spy session 計數 commit 次數 → 真實 endpoint 成功呼叫 → 斷言 commit == 1。

### 2.4 Fixture 依賴
參考 `tests/backend/api/test_phase3f0_r3_p1_variants_errors.py`：
- `create_app()` + `TestClient`
- 需要 auth token（註冊/登入）
- 需要 valid sequencing_test_id + specimen + case（EDITOR 權限）
- 或使用既有 fixture 模式

---

## 3. Master Plan 統一任務

### 3.1 Phase 4 B1/B2 關係統一

| 檔案 | 修改 |
|------|------|
| `tasks/plan-phase4-clinical-ai-productization.md` | §10 總覽表格與 Batch 說明統一為「B2 需 B1 核心完成（Gate）後啟動，與 B1 剩餘部分並行」；移除 :921 的「完全並行」說法 |
| `tasks/phase4-phase5-dependency-map.md` | 修正 :86/:88 與 :96/:128 的矛盾：統一為「B1/B2 部分重疊、B2 Gate=Patient+Evidence 完成」；:114 修正同一句矛盾 |
| `tasks/roadmap-phase4-phase5.md` | 修正 :95「B1 合併後 B2 才啟動」改為「B1 核心完成（Gate）後 B2 啟動」；:265「漸進整合」保留但精確為 Gate 模式 |
| `tasks/research/phase4-phase5-gap-analysis.md` | 修正舊 Batch 引用（「Phase 4 B4 Infrastructure」等 3 處）為 3-Batch 結構（若有） |

### 3.2 External Adapter 數量統一（10 = 7 同步 + 3 非同步）

| 檔案 | 修改 |
|------|------|
| `tasks/plan-phase4-clinical-ai-productization.md` | :51「7 個外部 adapter」→「10 個（7 同步 + 3 非同步）」；:159「8 個」→「10 個」；:1224「7 個外部 adapter」→「10 個（7 同步 + 3 非同步）」；:681「7/10」→ 移除混亂表述 |
| `tasks/roadmap-phase4-phase5.md` | :55 檔案清單移除 OpenCRAVAT（plan-phase4 明示不做），改為 10 個（7 同步 + 3 非同步）並分組列出 |
| `tasks/plan-phase5-medical-ai-platform.md` | :1084「8 個 stub」→「10 個（7 同步 + 3 非同步）」 |
| `tasks/phase4-phase5-dependency-map.md` | 補齊 adapter 清單：DGIdb 歸 B1（非 B3）、DRKG/PharmCAT/EnsemblVEP、非同步 adapter 均補入 |
| 全文件 | 確保 adapter 名稱、數量、分類完全一致（統一用 plan-phase4 8.3 節分類表 :774-785 為準） |

---

## 4. 任務清單與依賴

| 批次 | 任務 | 檔案 | 依賴 |
|------|------|------|------|
| 0 | T0.1 改造 variant_ingestion_service.py | `src/backend/services/variant_ingestion_service.py` | 無 |
| 0 | T0.2 改造 variants.py endpoint | `src/backend/api/v1/variants.py` | T0.1 |
| 1 | T1.1 R4 真實 endpoint 測試（情境 A+B） | `tests/backend/api/test_phase3f0_r4_p0_variants_atomicity.py`（新） | T0.1-T0.2 |
| 1 | T1.2 紅燈確認 → 綠燈驗證 | 執行測試 | T1.1 |
| 2 | T2 Master Plan B1/B2 統一 | plan-phase4/dependency-map/roadmap/gap-analysis | 無（可並行） |
| 2 | T3 Master Plan Adapter 數量統一 | plan-phase4/roadmap/plan-phase5/dependency-map | 無（可並行） |
| 3 | 全量測試 + Step 6 + Step 7 | 全部 | 所有 |

---

## 5. 風險

| # | 風險 | 緩解 |
|---|------|------|
| R1 | 其他 11 個 Service 有相同「commit 前未建構 DTO」模式 | 本輪僅 variants（R4 標註），列為後續；不阻擋本輪 |
| R2 | R4 改造改變 Service 返回類型（VariantModel → VariantResponse），若有其他呼叫者 | grep 確認僅 variants.py 使用 |
| R3 | 測試（情境 A）的 repo override 可能與真實 path 不完全一致 | 用 monkeypatch model_validate 而非覆寫 repo，確保 Service+repo 真實路徑 |
