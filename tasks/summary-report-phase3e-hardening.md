# Phase 3E Hardening 總結報告

## 任務概述
Phase 3E Hardening（架構強化）— 修復 ChatGPT GitHub Review 指出的 P0-P1 問題，共 7 項架構問題（4 項 P0 + 3 項 P1），以及後續返工修復 1 項 FAIL + 3 項 PARTIAL + 2 項 Reviewer 問題。

## 修復項目

### P0-1 Versioning（最高優先）
- [v] 移除 plan_id UNIQUE，新增 UNIQUE(plan_id, version)
- [v] revise_plan 沿用舊 plan_id，version+1
- [v] GET /versions 可同時看到 v1, v2, v3

### P0-2 Treatment Item Persistence
- [v] drug_id, procedure_code, frequency, duration, route, planned_dose_text 全部六個欄位持久化

### P0-3 Monitoring Persistence
- [v] target_range, warning_threshold, critical_threshold, action_if_abnormal, responsible_specialty 全部五個欄位持久化

### P0-4 Trace
- [v] UNIQUE(trace_id, step_order) 修正（移除 trace_id 單獨 UNIQUE）
- [v] 一個 Plan 共用同一 trace_id（所有 step 共用外部傳入 trace_id）

### P1-1 Phase Mapping
- [v] Item 依 phase_type / item_type 分配到正確 phase，而非全部擠在第一個 phase

### P1-2 Revision Policy
- [v] 允許 approved/active/paused 狀態 revision
- [v] 禁止 draft/cancelled/completed/superseded → 回傳 HTTP 409

### P1-3 Migration Gate
- [v] CI head → 022 → 023 → head 完整測試鏈
- [v] 有資料 downgrade 失敗測試（IrreversibleMigrationError）
- [v] 空資料 downgrade 成功測試

### 返工修復（Rework #1：1 FAIL + 3 PARTIAL）
- [v] **FAIL-1（§十四 Alternative Plan）**：TreatmentPlanModel 新增 alternative_options JSON 欄位；Migration 024 新增欄位；_persist_plan() 寫入 alternatives；_model_to_response() 從 DB 讀取
- [v] **PARTIAL-2（§二十五 Frontend Detail）**：TreatmentPlanDetailPage 新增 review_date 顯示
- [v] **PARTIAL-3（§二十六 HTML Report）**：report_generator.py 新增 review_date 渲染
- [v] **PARTIAL-4（§二十八 Postgres CI）**：CI 新增 Migration 023 獨立 empty downgrade + re-upgrade 測試

### 返工修復（Rework #2：Reviewer 評分問題）
- [v] **E-1（HIGH）**：report_generator.py 修復 Python 3.11 f-string 反斜杠語法錯誤
- [v] **E-2（MEDIUM）**：treatment_plan_state_machine.py 補齊 ACTIVE→CANCELLED 轉換

## 測試結果
- treatment_plan 測試：239 passed ✅（Phase 3E 原始測試 219 + Hardening 新增估計 25+）
- 返工後回歸檢查：8/8 PASS（100%）✅
- Reviewer 最終評分：97/100 ✅

## 修改檔案清單

### 核心邏輯修改（4 檔案）
| # | 檔案 | 修改內容 |
|---|------|---------|
| 1 | `src/backend/domain/treatment_plan.py` | 移除 plan_id unique=True，新增 UniqueConstraint(plan_id, version)；移除 trace_id unique=True，新增 UniqueConstraint(trace_id, step_order)；新增 alternative_options JSON 欄位 |
| 2 | `src/backend/services/treatment_plan_service.py` | revise_plan 沿用舊 plan_id（new_plan_id = plan_id）；新增 RevisionPolicy 狀態檢查（allowed_statuses）；Phase Mapping 依 phase_type/item_type 分配；補齊 Item 6 欄位（drug_id, procedure_code, frequency, duration, route, planned_dose_text）；補齊 Monitoring 5 欄位（target_range, warning_threshold, critical_threshold, action_if_abnormal, responsible_specialty）；Trace 共用 trace_id（step_trace_id = trace_id）；alternatives 寫入與讀取 |
| 3 | `src/backend/clinical/treatment_plan_state_machine.py` | ACTIVE 狀態加入 CANCELLED 轉換 |
| 4 | `src/backend/clinical/report_generator.py` | 修復 f-string 反斜杠語法錯誤（Monitoring # 標籤）；新增 review_date 提取與渲染 |

### Migration（2 檔案）
| # | 檔案 | 修改內容 |
|---|------|---------|
| 5 | `migrations/versions/023_phase3e_treatment_plan_tables.py` | 移除 plan_id UNIQUE，新增 UQ(plan_id, version)；移除 trace_id UNIQUE，新增 UQ(trace_id, step_order) |
| 6 | `migrations/versions/024_phase3e_treatment_plan_alternatives.py` | **新增** — ALTER TABLE domain_treatment_plans ADD COLUMN alternative_options JSON |

### CI（1 檔案）
| # | 檔案 | 修改內容 |
|---|------|---------|
| 7 | `.github/workflows/ci.yml` | 新增「Postgres Integration Gate - Migration 023 Downgrade / Re-upgrade」步驟：downgrade 022 → upgrade 023 → upgrade head |

### 測試檔案（6 檔案）
| # | 檔案 | 修改內容 |
|---|------|---------|
| 8 | `tests/test_migration.py` | **新增** TestMigration023 類別（3 測試）：test_upgrade_chain_head_to_022_to_023、test_downgrade_023_with_data_raises_irreversible、test_downgrade_023_empty_db_succeeds |
| 9 | `tests/backend/services/test_treatment_plan_service.py` | 新增 Version Chain 測試（test_version_chain）、Revision Policy 測試（test_revision_allowed_for_approved/active/paused、test_revision_denied_for_draft/cancelled/completed/superseded）、Phase Mapping 測試（test_items_mapped_to_correct_phase、test_items_without_phase_type_fallback_to_first_phase） |
| 10 | `tests/backend/api/test_treatment_plan_api.py` | 新增 Version Chain 測試（test_version_chain）、Revision Policy 測試（test_revise_409_for_draft/cancelled/completed/superseded） |
| 11 | `tests/backend/integration/test_treatment_plan_restart.py` | 新增 Item 逐欄驗證（test_restart_recovery_full_plan 擴充）、Monitoring 逐欄驗證（test_monitoring_persistence_columns）、Trace 正確性測試（test_trace_correctness） |
| 12 | `tests/backend/integration/test_treatment_plan_digital_thread.py` | 新增 Monitoring columns 測試（test_monitoring_columns_persisted）、Trace correctness 測試（test_trace_correctness） |
| 13 | `tests/backend/models/test_treatment_plan_models.py` | 新增 plan_id/version unique 測試（test_plan_id_version_unique） |

### Frontend（2 檔案）
| # | 檔案 | 修改內容 |
|---|------|---------|
| 14 | `src/frontend/src/pages/TreatmentPlanDetailPage.tsx` | Approval Info 區塊新增 review_date 條件式渲染 |
| 15 | `src/frontend/src/api/treatmentPlan.ts` | TreatmentPlan interface 新增 review_date?: string | null |

## REVIEWER 評分
**97/100 ✅（完整性 25/25 + 正確性 25/25 + 可維護性 22/25 + 測試 25/25）**

## 狀態
❌ 不自行宣告 Accepted — 等待 ChatGPT 使用 GitHub Connector 做正式 Review
