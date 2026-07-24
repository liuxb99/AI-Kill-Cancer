# Phase 3A Hardening Review (循環 0)

## 評分檢查清單
- 是否可執行：YES
- 是否有錯誤：YES（無錯誤）
- 是否滿足需求條列：YES
- 是否有測試：YES

## 細項評分
- 完整性：22/25
- 正確性：24/25
- 可維護性：22/25
- 測試與驗證：23/25

## 總分：91/100 — 合格 ✅

## 關鍵證據驗證

### 1. Database Persistence：✅
`_recommendations = {}` 不存在於任何後端程式碼中。所有 recommendation 資料透過 SQLAlchemy Model 持久化到 PostgreSQL。

### 2. Restart Recovery：✅
`tests/test_restart_recovery.py` 存在，包含 3 個測試用例：
- `test_restart_recovery_data_intact` — 完整資料鏈在引擎重啟後完好
- `test_restart_recovery_trace_references` — FK 關聯在重啟後保持
- `test_restart_recovery_multiple_records` — 多筆記錄重啟後均可查詢
使用真實新 Engine + Session，無 mock/monkeypatch restart。

### 3. Trace Persistence：✅
`tests/test_trace_persistence.py` 存在，驗證完整計算鏈（Evidence → Weight → Score → Rank → Explanation）可從 DB 還原。

### 4. Frontend Route：✅
`src/frontend/src/App.tsx` 包含 `<Route path="/recommendation" element={<RecommendationPage />} />`。

### 5. Navigation/Menu：✅
- `Home.tsx` 導航欄包含「藥物推薦」連結到 `/recommendation`
- `Dashboard.tsx` 包含 `/recommendation` 連結
- `ResearchPortal.tsx` 包含 `/recommendation` 連結
- `Workbench.tsx` 包含 `recommendation` tab

### 6. requirements.md History：✅
`tasks/requirements.md` 包含三個完整章節：
- `## 2026-07-24 — Vercel / Phase E`
- `## 2026-07-24 — Phase 3A Drug Recommendation Engine`
- `## 2026-07-24 — Phase 3A Hardening`

### 7. HTTP500 Security：✅
- `src/backend/api/v1/recommendation.py` 使用 `logger.exception()` + 固定 `error: "INTERNAL_ERROR"` + generic message
- 無任何 `f"internal error: {exc}"` 模式存在
- 內部 Exception 不會洩漏給 Client

### 8. Migration：✅
`migrations/versions/017_phase3a_recommendation_tables.py` 存在，支援 upgrade/downgrade，新增三個表：
- `domain_recommendations`
- `domain_recommendation_traces`
- `domain_recommendation_trace_steps`

## 需求逐條審查（對照 Phase 3A Hardening 正式实作要求）

### 1. RecommendationModel ✅
`src/backend/domain/recommendation.py`：
- `RecommendationModel`（id, recommendation_id, patient_id, case_id, trace_id, engine_version, status, request_payload, result_payload, report_html, created_by, created_at, updated_at）
- `RecommendationTraceModel`（id, trace_id, recommendation_id, created_at）
- `RecommendationTraceStepModel`（id, trace_id, step_order, step_type, input_summary, output_summary, evidence_references, weight, score, rank, status, created_at）
- 關聯完整：Recommendation → Trace → Steps

### 2. Calculation Trace Persistence ✅
Trace 和 Steps 完整持久化到資料庫，伺服器重啟後可查詢。

### 3. Migration ✅
017 版本支援 upgrade（建立三個新表）和 downgrade（刪除三個新表）。

### 4. RecommendationRepository ✅
`src/backend/repositories/recommendation_repo.py`：
- `RecommendationRepository`：create, get_by_id, get_by_trace_id, list_by_patient_id
- `TraceRepository`：create_trace, get_trace_by_recommendation_id, get_trace_by_trace_id, create_step, get_steps_by_trace_id
- 不自行 commit，由 Service 管理 Transaction

### 5. RecommendationService ✅
`src/backend/services/recommendation_service.py`：
- 執行完整 Pipeline（EvidenceCollector → EvidenceAggregator → DrugRanker → RecommendationEngine → DrugRankingEngine → ExplainableEngine）
- 建立 Record + Trace + Steps 在同一 Transaction
- 生成 HTML Report（失敗不影響主流程）
- 管理 commit/rollback 邊界

### 6. API ✅
`src/backend/api/v1/recommendation.py`：
- `POST /api/v1/recommendation` — 執行完整管線，結果持久化到 DB
- `GET /api/v1/recommendation/{recommendation_id}` — 從 DB 讀取
- 422 處理（ValueError → validation_failed）
- 500 處理（Exception → INTERNAL_ERROR + generic message）

### 7. Restart Recovery ✅
`tests/test_restart_recovery.py` 使用真實檔案型 SQLite，完整驗證 restart 後資料完整性。

### 8. Frontend Router ✅
`src/frontend/src/App.tsx` 已接入 `/recommendation` route。

### 9. Frontend API Integration ✅
`src/frontend/src/pages/RecommendationPage.tsx` 呼叫 `POST /api/v1/recommendation` 正式 API，無 fake data。

### 10. HTTP Error Security ✅
所有非預期 500 使用 `logger.exception()`，Client 只收固定 `error: "INTERNAL_ERROR"` + generic message。

## 測試覆蓋審查

| 測試類別 | 檔案 | 狀態 |
|---------|------|------|
| Backend Model Tests | 內含在 `test_recommendation_service.py` | ✅ |
| Repository Tests | 內含在 `test_recommendation_service.py` | ✅ |
| Service Tests | `tests/test_recommendation_service.py` | ✅ |
| API Integration Tests | `tests/test_api_recommendation.py` | ✅ |
| Restart Recovery Test | `tests/test_restart_recovery.py` | ✅ |
| Trace Persistence Test | `tests/test_trace_persistence.py` | ✅ |
| Frontend Route Test | `src/frontend/src/test/RecommendationPage.test.tsx` | ✅ |
| Migration Tests | `tests/test_migration.py`（含 017 測試） | ✅ |
| Golden Tests | `tests/test_recommendation_golden.py` | ✅ |
| Schema Tests | `tests/test_recommendation_schemas.py` | ✅ |
| Explainable Trace Tests | `tests/test_explainable_trace.py` | ✅ |

## 可維護性備註（扣 3 分的理由）
- `RecommendationService.create_recommendation()` 方法較長（約 200 行），建議可拆分為更小的私有方法
- 缺少全局 FastAPI exception handler，僅在路由層處理 500 錯誤
- 程式碼整體結構清晰、型別提示完整、docstring 詳盡，屬於高可維護性

## 完整性備註（扣 3 分的理由）
- 少量 Phase E/Vercel artefacts 零位元組檔案未完全刪除（`plan-phaseE.md`, `vercel-phaseE-report.md` 等），但已清空內容
- 其餘 10 項正式实作要求全部完成

## 改進建議
1. 考慮新增全局 FastAPI exception handler 作為防禦性措施
2. 建議清理所有零位元組的 Phase E artefacts 檔案
3. `RecommendationService` 的 `create_recommendation` 方法可考慮拆分為多個步驟方法

## 評分記錄
可執行=YES 無錯誤=YES 滿足需求=YES 測試=YES | 完整性22 正確性24 可維護性22 測試驗證23 | 總分91 合格
