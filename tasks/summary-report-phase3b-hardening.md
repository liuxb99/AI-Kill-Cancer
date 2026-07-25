# Phase 3B Hardening 總結報告

## 概述
- 任務ID：Phase-3B-Hardening
- 場景：hardening
- 基線：Phase 3B Clinical Decision Layer（Commit 2896cb0）
- 目標：修正 ChatGPT GitHub Review 架構問題（84/100 → ≥95/100）

## 完成項目

### P0-1：Recommendation 必須屬於同一位 Patient ✅
- engine 執行前加入 patient_id 驗證
- 不匹配 raise ValueError → API 映射為 422
- Transaction 全部 rollback（無 ClinicalDecisionModel、無 Trace 殘留）
- 測試：`test_create_decision_patient_recommendation_mismatch`（Service Unit）
- 測試：`test_create_decision_patient_recommendation_mismatch_api`（API Integration 422）

### P0-2：created_by 完整傳遞 ✅
- API 層：`created_by=str(user.id)` 從 `require_auth` 傳入 Service
- Service 層：`create_decision(..., created_by=created_by)` 簽名接受參數
- Model 層：`ClinicalDecisionModel(created_by=uuid.UUID(created_by))` 寫入 DB
- Audit Trail 完整（可追溯每個 Decision 由哪個 User 建立）
- 測試：`test_create_decision_created_by_set`（created_by UUID 正確寫入 DB）

### P0-3：context.patient 不得覆蓋 Database Patient ✅
- Patient 唯一來源為 Database（`_load_patient_data()`）
- context.patient 只合併補充欄位（跳過 id/patient_id/external_id/display_name/birth_year/age_range/sex/consent_status/created_at 等核心欄位）
- 測試：`test_context_patient_does_not_override_db`（context sex="female" 不覆蓋 DB sex="M"；supplemental 欄位如 allergies 被合併）

### P0-4：Frontend Navigation 移除假資料 ✅
- 移除 `/clinical-decision/sample` 假路由（grep 確認無殘留）
- 新增 `ClinicalDecisionListPage`（列表頁：輸入 patient_id → 顯示決策列表 → 點擊跳轉 Detail）
- Navbar 導向正式路徑 `/clinical-decision`
- Route 註冊：`/clinical-decision` → ListPage；`/clinical-decision/:id` → DetailPage
- 前端測試 24 項全部通過（Route Registration、Rendering、States、API Request、UI Elements、Navigation）

### P1-1：Trace 拆 5 步驟 ✅
- Step 0：`load_recommendation` — 載入 recommendation 資料
- Step 1：`validate_patient` — 驗證 patient 歸屬
- Step 2：`evaluate` — 引擎評估
- Step 3：`decision` — 決策結果
- Step 4：`persist` — 持久化
- 每個 step 有獨立 `input_summary` / `output_summary`，無塞成同一 output_summary
- 測試：`test_trace_has_all_steps`（驗證 5 steps type/order 正確）

### P1-2：DTO Mutable Default 修正 ✅
- `ClinicalDecisionRequest.variants: list[dict] = []` → `Field(default_factory=list)`
- `ClinicalDecisionResponse.alternatives: list[dict] = []` → `Field(default_factory=list)`
- `ClinicalDecisionResponse.contraindications: list[dict] = []` → `Field(default_factory=list)`
- 無 `= []` 殘留於 DTO 定義中

## 架構修復
- `ClinicalDecisionTraceModel.trace_id: unique=True` → `(trace_id, step_order)` 複合唯一（支援多步驟 trace）

## 修改檔案清單

| 檔案 | 變更內容 |
|------|----------|
| `src/backend/services/clinical_decision_service.py` | P0-1 patient_id 驗證、P0-2 created_by 傳遞、P0-3 DB Patient 優先、P1-1 Trace 拆 5 步驟、P1-2 DTO Mutable Default |
| `src/backend/api/v1/clinical_decision.py` | P0-2 傳遞 `created_by=str(user.id)` |
| `src/frontend/src/App.tsx` | P0-4 Navbar 路徑修正 + 新增 Route |
| `src/frontend/src/pages/ClinicalDecisionListPage.tsx` | **新增** — 決策列表頁 |
| `src/frontend/src/test/ClinicalDecisionPage.test.tsx` | P0-4 更新測試期望值 |
| `tests/test_clinical_decision_service.py` | 新增 P0-1/P0-2/P0-3/P1-1 測試 |
| `tests/test_api_clinical_decision.py` | 新增 P0-1 API 端到端測試 |

## Reviewer 評分
- 總分：**98 分** ✅（門檻 95 分）
- 完整性：25/25
- 正確性：25/25
- 可維護性：23/25
- 測試與驗證：25/25
- **判定：合格 PASS**

## 測試結果
| 套件 | 結果 |
|------|------|
| Backend Service Tests | 18/18 passed |
| Backend API Tests | 15/15 passed |
| Frontend Tests | 24/24 passed |
| **合計** | **57 tests all passed** |

## Git Commit
- **Commit 訊息**：`Phase 3B Hardening: P0/P1 fixes — patient validation, created_by audit, DB patient priority, frontend nav, trace steps, DTO defaults`
- **範圍**：後端 3 檔案 + 前端 3 檔案（含 1 新增）+ 測試 2 檔案 + 計劃/報告 2 檔案

## 完成條件確認
- [x] 所有 6 項 HARDEN 任務（4 P0 + 2 P1）實作完成
- [x] 新增測試全部通過（57 tests）
- [x] `pytest` + `npm test` 全部綠色
- [x] Git diff 僅包含允許範圍（無 Phase 3A/Migration/CI/Vercel 修改）
- [x] Reviewer 評分 ≥ 95（98 分）
- [x] 總結報告產出

---

*報告版本：v1.0｜日期：2026-07-25*
