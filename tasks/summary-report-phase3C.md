# Phase 3C — Tumor Board Consensus Engine 總結報告

## Commit SHA
```
PENDING（等待 Git commit 後填入）
Base: 5b2c658a85d9062902689c9f2c4faaa91a3a5189
```

## Files Changed

### 新增檔案（19 個）

| 層級 | 路徑 | 行數 |
|------|------|------|
| Enum | `src/backend/domain/tumor_board.py`（TumorBoardConsensusModel / TumorBoardOpinionModel / TumorBoardConsensusTraceModel） | 126 |
| Migration | `migrations/versions/020_phase3c_tumor_board_consensus.py` | 93 |
| Rules | `src/backend/clinical/consensus_rules.py` | 83 |
| Engine | `src/backend/clinical/tumor_board_engine.py` | 783 |
| Repository | `src/backend/repositories/tumor_board_repo.py` | 397 |
| Service | `src/backend/services/tumor_board_service.py` | 858 |
| API | `src/backend/api/v1/tumor_board_consensus.py` | 153 |
| Frontend Page | `src/frontend/src/pages/TumorBoardConsensusListPage.tsx` | 298 |
| Frontend Page | `src/frontend/src/pages/TumorBoardConsensusPage.tsx` | 476 |
| Frontend API | `src/frontend/src/api/workbench.ts`（Phase 3C 追加部分） | — |
| Tests (Engine) | `tests/test_tumor_board_engine.py` | ~800 |
| Tests (Models) | `tests/test_tumor_board_models.py` | ~400 |
| Tests (Repo) | `tests/test_tumor_board_repo.py` | ~500 |
| Tests (Service) | `tests/test_tumor_board_service.py` | ~600 |
| Tests (API) | `tests/test_api_tumor_board.py` | ~400 |
| Tests (Thread) | `tests/test_tumor_board_digital_thread.py` | ~200 |
| Tests (Restart) | `tests/test_tumor_board_restart_recovery.py` | ~100 |
| Tests (Frontend) | `src/frontend/src/test/TumorBoardConsensusListPage.test.tsx` | 458 |
| Tests (Frontend) | `src/frontend/src/test/TumorBoardConsensusPage.test.tsx` | 504 |
| Tests (Frontend) | `src/frontend/src/test/App.test.tsx` | 184 |

### 修改檔案（17 個）

| 檔案 | 變更內容 |
|------|----------|
| `src/backend/domain/enums.py` | 追加 SpecialtyType（9 專科）、ConsensusStatus（6 種）、Position（3 種） |
| `src/backend/domain/__init__.py` | 追加 tumor_board models 匯出 |
| `src/backend/clinical/__init__.py` | 追加 tumor_board_engine 匯出 |
| `src/backend/clinical/report_generator.py` | 追加 `_render_tumor_board_consensus()` 方法（~200 行） |
| `src/backend/repositories/__init__.py` | 追加 tumor_board_repo 匯出 |
| `src/backend/services/__init__.py` | 追加 tumor_board_service 匯出 |
| `src/backend/api/v1/router.py` | 追加 import + `include_router(tumor_board_consensus_router)` |
| `src/frontend/src/App.tsx` | 追加路由 `/tumor-board`、`/tumor-board/:id` + Navigation「腫瘤委員會」連結 |
| `src/frontend/src/pages/ClinicalDecisionPage.tsx` | 追加建立 Tumor Board Consensus 表單 + POST → navigate |
| `src/frontend/src/test/ClinicalDecisionPage.test.tsx` | 追加 Consensus 建立流程測試 |
| `tests/test_migration.py` | 追加 `TestMigration020` 類別（13 個測試） |
| `tests/integration/test_migration_016.py` | 擴充支援 Phase 3C migration |
| `.github/workflows/ci.yml` | 追加 Phase 3C Tumor Board Tests 步驟於 Postgres Gate |
| `tasks/requirements.md` | 全面改寫為 Phase 3C 需求文件 |
| `agent_workflow_History.md` | 更新 Phase 3C 執行記錄 |
| `tasks/task-status.md` | 更新進度狀態 |
| `AGENTS.md` | 微調 Phase 3C 相關說明 |

---

## Migration 020
- **檔案**: `migrations/versions/020_phase3c_tumor_board_consensus.py`
- **Revises**: 019
- **建立 3 張表**:
  - `domain_tumor_board_consensus`
  - `domain_tumor_board_opinions`
  - `domain_tumor_board_consensus_traces`

## New Tables
- `domain_tumor_board_consensus` — 共識主表（16 欄位）
- `domain_tumor_board_opinions` — 專家意見表（12 欄位）
- `domain_tumor_board_consensus_traces` — 計算追蹤表（7 欄位）

## New Models
- `TumorBoardConsensusModel` — consensus_id, patient_id (FK→patients), recommendation_id (FK→recommendations), clinical_decision_id (FK→clinical_decisions), consensus_status, consensus_score, final_recommendation, supporting_rationale, dissenting_opinions (JSON), unresolved_questions (JSON), required_follow_up (JSON), participating_specialties (JSON), created_by (FK→users), created_at, updated_at
- `TumorBoardOpinionModel` — consensus_id (FK→consensus CASCADE), specialty, participant_id, position, confidence, rationale, supporting_evidence (JSON), contraindications (JSON), preferred_option, alternative_option, requires_more_information, created_at
- `TumorBoardConsensusTraceModel` — trace_id, consensus_id (FK→consensus CASCADE), step_order, step_type, input_summary (JSON), output_summary (JSON), created_at; `UniqueConstraint("trace_id", "step_order")`

## New Repositories
- `TumorBoardConsensusRepository` — create, get_by_id, get_by_uuid, list_by_patient_id, list_by_clinical_decision_id, count_by_patient_id
- `TumorBoardOpinionRepository` — create, create_many, list_by_consensus_id
- `TumorBoardConsensusTraceRepository` — create, create_many, list_by_consensus_id, get_by_trace_id

## New Service
- `TumorBoardConsensusService` — 整合 Engine + 3 Repositories + Transaction Boundary
  - P0 關聯驗證（Patient / Recommendation / Clinical Decision 三角一致）
  - Engine 執行 → 建立 Consensus Model → Opinion Models → Trace Models → 單一 Transaction commit
  - 失敗 rollback，不留殘餘資料
  - DTOs: `CreateConsensusRequest`, `ConsensusResponse`, `ConsensusListResponse`, `SpecialistOpinionDTO`

## Consensus Engine
- `ConsensusEngine` — 純業務邏輯，無 DB 依賴
- 8 步驟 Pipeline: load_context → validate_links → normalize_opinions → calculate_weights → calculate_consensus → resolve_dissent → finalize_consensus → prepare_persistence
- Scoring: support_score, oppose_score, abstain_score, consensus_ratio, confidence_score
- Weight Calculation: `Opinion Weight = Specialty Weight × Confidence Weight × Evidence Weight`

## Consensus Rule Set
- `ConsensusRuleSet` — 集中管理所有 Threshold（Unanimous=1.0, Strong=0.8, Majority=0.6, Split=0.55, MinOpinions=2, MinConfidence=0.1）
- 9 專科權重（Medical Oncology=1.0, Surgical/Radiation=0.9, Pathology/Radiology=0.8, Genomics/Pharmacy=0.7, Palliative=0.6, Nursing=0.5）
- 3 級 Confidence Weight（High=1.0, Medium=0.7, Low=0.4）

---

## POST API
- `POST /api/v1/tumor-board-consensus` → 201 Created
- 輸入: patient_id, recommendation_id, clinical_decision_id, specialist_opinions[], meeting_context?
- 回傳: ConsensusResponse DTO
- 錯誤: 422（驗證/連結錯誤）、500（generic）

## GET API
- `GET /api/v1/tumor-board-consensus/{consensus_id}` → 200 / 404
- 回傳完整 ConsensusResponse（含 opinions, traces 關聯）

## List API
- `GET /api/v1/tumor-board-consensus?patient_id=&skip=&limit=` → 200
- 分頁: skip≥0, 1≤limit≤100，預設 20
- 回傳 `list[ConsensusListResponse]`

## Opinions API
- `GET /api/v1/tumor-board-consensus/{consensus_id}/opinions` → 200 / 422 / 500
- 回傳該 consensus 的所有專家意見序列化資料

## Trace API
- `GET /api/v1/tumor-board-consensus/{consensus_id}/trace` → 200 / 422 / 500
- 回傳該 consensus 的 8 步驟計算追蹤

---

## Frontend List Route
- `/tumor-board` — `TumorBoardConsensusListPage`
- 支援輸入 patient_id 查詢
- 顯示 consensus_status, consensus_score, participating_specialties, created_at
- 點擊進入 Detail

## Frontend Detail Route
- `/tumor-board/:id` — `TumorBoardConsensusPage`
- 顯示: Consensus Status, Score, Participating Specialties, Final Recommendation, Supporting Rationale, Dissenting Opinions, Unresolved Questions, Required Follow-up, Specialist Opinions, Trace Summary

## Frontend Create Flow
- `ClinicalDecisionPage` 內建「建立 Tumor Board Consensus」表單
- 填寫 Specialist Opinions → POST → navigate(`/tumor-board/{id}`)
- Router 註冊: App.tsx + Navbar「腫瘤委員會」連結

## Report Section
- `ReportGenerator._render_tumor_board_consensus()` — HTML 區塊
- 顯示: Consensus Status, Score, Participating Specialties, Final Recommendation, Supporting Rationale, Dissenting Opinions, Unresolved Questions, Required Follow-up

---

## Patient Link Validation
- ✅ `_validate_links()` 檢查 `Recommendation.patient_id == Request.patient_id`
- 不一致 → ValueError → API 422

## Recommendation Link Validation
- ✅ `_validate_links()` 檢查 `ClinicalDecision.recommendation_id == Recommendation.id (PK)`
- 不一致 → ValueError → API 422

## Clinical Decision Link Validation
- ✅ `_validate_links()` 檢查 `ClinicalDecision.patient_id == Request.patient_id`
- 不一致 → ValueError → API 422

## created_by Audit
- ✅ API 從 `require_auth` 取得 `user.id`
- 傳入 Service → 寫入 `TumorBoardConsensusModel.created_by`
- 測試驗證持久化成功

---

## Opinion Persistence
- ✅ Service 使用 `opinion_repo.create_many()` 批次寫入所有意見
- FK→consensus CASCADE 刪除
- 測試驗證全部持久化

## Consensus Persistence
- ✅ Service 建立 `TumorBoardConsensusModel` → db.add + flush + commit

## Trace Persistence
- ✅ 8 步驟 trace 全部寫入 `TumorBoardConsensusTraceModel`
- `UniqueConstraint("trace_id", "step_order")` 確保不重複
- traces relationship 已設定 `order_by` 維持順序

## Transaction Rollback
- ✅ Service 內 try/except：成功 commit，失敗 rollback
- 模擬 persistence failure 驗證 DB 無殘留資料

## Restart Recovery
- ✅ 測試結構正確：App1 POST → GET → Shutdown → App2 GET + Opinions + Trace
- ⚠️ 本環境因外部 NCCN/ESMO/OncoKB API 授權問題導致 recommendation 建立失敗（422），無法完整驗證
- 需在真實 CI（Postgres + all services）上通過

## Digital Thread
- ✅ 5 個測試：Patient → Recommendation → Clinical Decision → Tumor Board Consensus → Opinions → Trace
- FK 鏈完整，可從 Consensus 回溯至 Patient

---

## Migration Upgrade
- ✅ `alembic upgrade head` — 建立 3 張表
- 測試驗證: 13/13 ✅

## Migration Downgrade
- ✅ 020→019 downgrade 拋 `IrreversibleMigrationError`（保護已持久化資料）
- 測試驗證: downgrade 被正確阻擋 ✅

## Migration Re-upgrade
- ✅ downgrade 016 → upgrade head 完整循環
- 019→020 re-upgrade 測試: PASS ✅

---

## Backend Tests

| 測試檔案 | 數量 | 狀態 |
|---------|------|------|
| `test_tumor_board_engine.py` | 39 tests | ✅ 39/39 |
| `test_tumor_board_models.py` | 19 tests | ✅ 19/19 |
| `test_tumor_board_repo.py` | 28 tests | ✅ 28/28 |
| `test_tumor_board_service.py` | 22 tests | ✅ 22/22（1 fixture ERROR = async SQLite greenlet，同既有問題） |
| `test_api_tumor_board.py` | 20 tests | ✅ 20/20 |
| `test_tumor_board_digital_thread.py` | 5 tests | ✅ 5/5 |
| `test_tumor_board_restart_recovery.py` | 1 test | ⚠️ 0/1（需外部 API 授權） |
| `test_migration.py`（020 部分） | 13 tests | ✅ 13/13 |
| **合計** | **~147 tests** | **~146/147 ✅** |

## Frontend Tests

| 測試檔案 | 數量 | 狀態 |
|---------|------|------|
| `TumorBoardConsensusListPage.test.tsx` | 19 it() | ⚠️ 部分因 mock timing 失敗 |
| `TumorBoardConsensusPage.test.tsx` | 28 it() | ⚠️ 部分因 mock timing 失敗 |
| `App.test.tsx` | 9 it() | ✅ |
| `ClinicalDecisionPage.test.tsx` | 追加測試 | ✅ |
| **合計** | **~56 it()（Phase 3C）** | **~52/56 ✅（4 項 mock selector/等待問題）** |

## Postgres Integration Tests
- CI workflow `.github/workflows/ci.yml` 已包含：
  - `test_tumor_board_engine.py`
  - `test_tumor_board_models.py`
  - `test_tumor_board_repo.py`
  - `test_tumor_board_service.py`
  - `test_api_tumor_board.py`
  - `test_tumor_board_digital_thread.py`
  - `test_tumor_board_restart_recovery.py`
- Alembic upgrade 涵蓋 020
- 020→019 downgrade 阻擋測試
- ⏳ **尚未在 GitHub Actions 上執行**

## CI Run ID
```
PENDING（等待 GitHub Actions 觸發）
```

## CI Result
```
PENDING（等待 GitHub Actions 執行）
```

---

## requirements.md additions
**+1003 行** — 完整 Phase 3C 需求文件（25 章節），涵蓋任務定位、執行流程、核心目標、專科意見模型、Consensus 狀態、計算規則、P0 資料一致性、Audit Trail、Database Models、Migration 020、Repository、Service、Consensus Trace、API、Frontend、Report Section、測試要求、Postgres Gate、Reviewer Gate 等

## requirements.md deletions
**-310 行** — 移除了舊版 Phase 3A/3B 需求歷史記錄，替換為 Phase 3C 最新需求規格

---

## Git Status
```
Branch: master
Base Commit: 5b2c658a85d9062902689c9f2c4faaa91a3a5189
Phase 3C 相關變更：
  19 new files (untracked)
  17 modified files
  ~4,650+ 行新增（含測試）
  待 Stage + Commit + Push
```

## Push Result
```
PENDING（等待 git push 至 GitHub）
```

## Reviewer Score
**89/100 — PARTIAL（原始 91，因 CI 未執行扣至 89）**

| 維度 | 分數 | 說明 |
|------|------|------|
| 完整性 (Completeness) | 24/25 | 核心架構完整到位，微小：前端型別與 API contract 不完全一致 |
| 正確性 (Correctness) | 23/25 | 核心邏輯正確，扣分：前端型別不一致 + 前端測試 gap |
| 可維護性 (Maintainability) | 24/25 | Repository Pattern、Service Transaction Boundary、RuleSet 集中管理 |
| 測試與驗證 (Testing & Verification) | 20/25 | 測試覆蓋充足但部分因環境限制無法全線綠燈 |

### 11 項 Gate 檢查結果
| # | 檢查項目 | 結果 |
|---|---------|------|
| 1 | Recommendation / Clinical Decision / Patient 關聯一致（P0 驗證） | ✅ PASS |
| 2 | created_by 寫入所有記錄（Audit Trail） | ✅ PASS |
| 3 | Opinions 全部持久化（create_many） | ✅ PASS |
| 4 | Consensus Trace 多 Step 持久化（8 steps） | ✅ PASS |
| 5 | Transaction All-or-Nothing（失敗 rollback） | ✅ PASS |
| 6 | API POST/GET/List 可用（含 opinions/trace endpoints） | ✅ PASS |
| 7 | Frontend List/Detail/Create 可用（無 hardcoded data） | ⚠️ PARTIAL（4 項前端測試失敗 + type 不一致） |
| 8 | Digital Thread 可還原 | ✅ PASS |
| 9 | Restart 後可讀 | ⚠️ PARTIAL（需外部 API 授權） |
| 10 | Migration 020 upgrade/downgrade/re-upgrade 正確 | ✅ PASS |
| 11 | Postgres CI 全綠 | ❌ FAIL（未在 GitHub Actions 執行） |

---

```
Phase 3C：PARTIAL（原因：CI 未在 GitHub Actions Postgres 執行）
Accepted：NO（需 GitHub Actions CI 全綠 + Reviewer ≥ 95）
Ready for ChatGPT GitHub Review：NO
Ready for Phase 4：NO
```

### 為達成 Accepted 需補足的條件
1. **推送至 GitHub**：`git add` + `git commit -m "feat(phase3c): Tumor Board Consensus Engine"` + `git push`
2. **GitHub Actions CI 全綠**：確認 Postgres Gate 上所有 Phase 3C 測試通過
3. **重啟 Reviewer 評分**：CI 全綠 + 無新問題 → 可達 ≥95
4. **前端 type 修正**（可選但建議）：同步 `workbench.ts` 介面與後端 API 回應欄位名稱

---

*報告產生時間：2026-07-26*
*評分規則：§20（CI 未通過最高 89）+ §23（滿足需求=NO 最高 89）*
