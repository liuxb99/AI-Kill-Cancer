# Requirements History

## 2026-07-24 — Vercel / Phase E

Vercel / Phase E 需求歷史詳見 Git 歷史記錄

---

## 2026-07-24 — Phase 3A Drug Recommendation Engine

# AI-Kill-Cancer Phase 3A

Repository：https://github.com/liuxb99/AI-Kill-Cancer

Branch：master

目前狀態：
- Phase 1 ✅ 完成
- Phase 2 ✅ 完成（CI/CD、GitHub Actions、Vercel、Production、Secrets 已驗收）
- Phase 3 開始

---

# 本輪目標

開始真正的 Clinical Intelligence。

不是再做部署、CI、Workflow、Docker、Vercel — 那些全部停止。

---

# 本輪一次完成

建立 Drug Recommendation Engine V1，完整鏈路：

Variant → Evidence → Drug → Evidence Score → Drug Score → Rank → Recommendation

---

# 必做功能

## 1. Recommendation Engine
建立 RecommendationEngine、RecommendationRule、EvidenceAggregator、DrugRanker。不要寫死，全部規則化。

## 2. Evidence Weight / Tier / Confidence / Evidence Level
支援 FDA、NCCN、OncoKB、CIViC、DGIdb、OpenCRAVAT 等來源。全部可擴充。

## 3. Drug Ranking
包含 Overall Score、Evidence Score、Sensitivity、Resistance、Conflict Score。最終排序輸出 Top N。

## 4. Explainable AI
每個 Recommendation 必須產生 Reason、Evidence、Source、Score Detail。例如：為何第一名、為何第二名、為何被扣分、哪些證據支持。全部可追溯。

## 5. Calculation Trace
沿用既有架構：Input → Evidence → Score → Recommendation → Output。所有計算必須 Traceable。

## 6. JSON Schema
建立 RecommendationResult、DrugScore、EvidenceScore、RecommendationReason，全部 Versioned。

## 7. API
POST /recommendation 以及 GET /recommendation/{id}

## 8. Report
HTML Drug Recommendation Report，包含 Patient、Variants、Evidence、Top Drugs、Reason、Warnings、Trace。

## 9. Frontend
不要重新設計，只補 Recommendation Page。

## 10. Test
至少 Unit Tests、Integration Tests、API Tests、Golden Tests，全部通過。

---

# 品質要求

不得有 Placeholder、TODO、Fake Data、Mock Recommendation。正式完成。

---

# 驗證

完成後須執行：go test ./...、Frontend build、Backend build、API Smoke Test、Coverage、Git Diff，全部完成。

---

# Git

全部完成後一次 git add、git commit、git push。不要中途回報。

---

# Reviewer

Reviewer 重新閱讀 tasks/requirements.md，重新確認需求是否全部完成。必須執行 Step 4b Requirement Regression Check。低於 90 分直接返工。

---

# 最後回報

只回報：Commit SHA、修改檔案數、新增 API、新增 Package、新增 Tests、Coverage、Build、Test、Push、Reviewer Score。不要貼程式碼。

---

## 2026-07-24 — Phase 3A Hardening

**狀態**：PARTIAL（82/100，不可驗收，不可進入 Phase 3B）

## 已確認問題

### P0-1 Recommendation 使用記憶體 dict
`_recommendations: dict[str, dict] = {}` 必須改為 Postgres Database 正式儲存。禁止使用 dict、global variable、singleton cache、module-level cache、process memory、temporary file、JSON file、SQLite fallback。

### P0-2 Calculation Trace 沒有資料庫持久化
TraceManager 只存在請求內記憶體，必須讓 Calculation Trace 正式持久化到 Database，伺服器重啟後仍可查詢。

### P0-3 RecommendationPage 是孤立頁面
必須接入 App Router、Route、Navigation、Menu、Link，讓使用者可從前端 UI 真正進入。

### P0-4 Commit 混入無關內容
Phase 3A commit 混入 Phase E/Vercel task artefacts，必須移除（但先確認無其他正式功能引用）。

### P0-5 requirements.md 被覆蓋
本輪必須恢復需求歷史（保留舊有 Vercel/Phase E 需求、保留 Phase 3A 原始需求、新增 Phase 3A Hardening 章節），從此只 append。

### P1 HTTP 500 洩漏 Exception
`f"internal error: {exc}"` 把內部 Exception 傳給 Client，必須改為 logger.exception() + 固定 Error Code + Generic Message。

## 正式實作要求

1. **RecommendationModel**：建立正式 SQLAlchemy Model（id, patient_id, case_id, trace_id, engine_version, status, request_payload, result_payload, report_html, created_by, created_at, updated_at 等）
2. **Calculation Trace Persistence**：建立正式 Trace Persistence（RecommendationTraceModel / RecommendationTraceStepModel），保存完整計算鏈
3. **Migration**：新增正式 Alembic Migration，upgrade/downgrade 安全
4. **RecommendationRepository**：建立正式 Repository（create, get_by_id, get_by_trace_id, list_by_patient_id），不自行 commit
5. **RecommendationService**：建立正式 Service（執行 Pipeline、建立 Record + Trace、生成 HTML Report、同一 Transaction）
6. **API**：保留 POST /api/v1/recommendation 和 GET /api/v1/recommendation/{recommendation_id}，改為全 Database 操作
7. **Restart Recovery**：新增真實 Restart Recovery Integration Test
8. **Frontend Router**：RecommendationPage 正式接入 App.tsx、Route、Navigation、Menu
9. **Frontend API Integration**：確保 RecommendationPage 呼叫正式 API，不 fake data
10. **HTTP Error Security**：所有非預期 500 用 logger.exception()，Client 只收固定 error code + generic message

## 測試要求
- Backend Model Tests（RecommendationModel, JSON round-trip, Index, Trace relation）
- Repository Tests（create, get_by_id, get_by_trace_id, list_by_patient_id, not found, rollback）
- Service Tests（成功建立、同 transaction、Report failure、Pipeline failure rollback）
- API Integration Tests（POST→DB、GET→DB、404、422、500 generic）
- Restart Recovery Test（真實新 App、新 Engine、新 Session）
- Trace Persistence Test（Evidence→Weight→Score→Rank→Explanation 可從 DB 還原）
- Frontend Route Test（Route registered、Navigation clickable、Page renders、API path correct）
- Migration Tests（upgrade→downgrade→upgrade again）

## 清理要求
Hardening Commit 只包含：Recommendation persistence、Trace persistence、Repository、Service、Migration、API hardening、Frontend route、相關 tests、requirements history restoration、Phase 3A 無關 artefacts 清理。

## 禁止事項
dict 代替 DB、mock restart、monkeypatch、只新增 Model 不接 API、只接 Route 不接 Navigation、force push、rebase master。

## 驗收條件
共 22 項檢查清單（見需求回歸檢查章節），只要任一 FAIL/PARTIAL/Pending 則滿足需求=NO，Reviewer 最高 89 分。
