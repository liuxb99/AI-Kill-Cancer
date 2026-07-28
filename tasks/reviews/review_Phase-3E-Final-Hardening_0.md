# Review: Phase-3E-Final-Hardening (循環 0)

## 檢查清單

- **是否遵守流程**：YES
  - 未發現步驟跳過或順序錯誤的證據，交付物（Migration 025、測試、CI 配置）已產出。
- **是否可執行**：YES
  - Migration 025 語法正確，SQLite/PostgreSQL 分支邏輯完整；測試導入無缺失；CI 配置語法正確。
- **是否有錯誤**：YES（無錯誤）
  - Migration 025 的 DROP CONSTRAINT / ADD CONSTRAINT / CREATE INDEX 均使用了 IF EXISTS / IF NOT EXISTS 或動態 pg_constraint 查詢，邏輯正確。測試程式碼無語法或邏輯錯誤。
- **是否滿足需求**：NO
  - **關鍵缺失**：CI 的 `migration-gate` Job 中**未執行 `pytest tests/test_migration_gate.py`**（即 Phase-3E-Final-Hardening 新增的 Migration Gate 測試），違反 P0-3「CI 必須完整執行 migration tests」以及 P1-4「新增 CI Tests」。
- **是否有測試**：YES
  - 新增了 4 個測試檔案：`test_migration_025_pg_trace_constraint.py`、`test_migration_025_pg_schema_compare.py`、`test_migration_025_pg_full_cycle.py`、`test_migration_gate.py`，並在 `tests/conftest.py` 提供了 PostgreSQL 整合測試所需的 fixtures。

---

## 細項評分

### 完整性：8/25
- 需求「滿足需求=NO」→ 最高 10 分。
- Migration 025 的 upgrade/downgrade 完整涵蓋了兩張表的約束變更及 FK/Index；SQLite 與 PostgreSQL 雙分支完備。
- 三個 PostgreSQL Integration Test 覆蓋了 Trace Constraint、Schema Compare、Full Cycle 三大情境。
- **扣分原因**：CI 配置缺少 `pytest tests/test_migration_gate.py` 的執行步驟，導致交付清單第 5 項（新增 CI Tests）未真正接入 CI 流程。

### 正確性：22/25
- Migration 025：
  - 對 `domain_treatment_plan_traces` 使用動態 pg_constraint 查詢後 DROP CONSTRAINT，再 ADD UNIQUE(trace_id, step_order)，完全符合 P0-1 要求。
  - 對 `domain_treatment_plans` 同理處理，且 downgrade 正確恢復 024 Schema（plan_id UNIQUE、trace_id UNIQUE、移除兩欄位）。
  - SQLite 分支使用 batch_alter_table 保持相容。
- 測試邏輯正確：Trace Constraint 測試插入同一 trace_id 的三筆 step 全部通過；Full Cycle 測試完整驗證 upgrade→downgrade→re-upgrade→insert→query。
- **扣分原因**：CI 配置的缺失（未執行 migration tests）降低了整體正確性評分。

### 可維護性：22/25
- Migration 025 程式碼結構清晰，PostgreSQL/SQLite 分支明確，使用了 DO $$ 動態區塊與 IF EXISTS 模式。
- 測試檔案命名規範、註解完整（中英雙語說明），fixtures 集中在 `conftest.py`。
- schema compare 測試的 `get_schema_summary()` 函數可復用。
- **扣分原因**：無重大可維護性問題。略低分是因 CI 配置缺少 migration tests 步驟，導致交付物在 CI 層面不完整。

### 測試與驗證：18/25
- 測試檔案覆蓋：
  - `test_migration_025_pg_trace_constraint.py`：同 trace_id 三筆不同 step ✅
  - `test_migration_025_pg_schema_compare.py`：025→024 Schema Equal + 024→025 Schema Equal ✅
  - `test_migration_025_pg_full_cycle.py`：upgrade→downgrade→re-upgrade→insert→query ✅
  - `test_migration_gate.py`：upgrade head、composite unique、FK、downgrade 024、re-upgrade head ✅
- **扣分原因**：
  1. CI `migration-gate` Job 中未執行 `pytest tests/test_migration_gate.py`，該檔案被閒置。
  2. Integration tests（`test_migration_025_pg_*.py`）在 `backend` Job 的「Test with pytest」步驟中透過 `tests/integration/` 路徑間接執行，但使用的是共用資料庫 `cancer_db` 而非隔離的 Migration Gate 資料庫，違反 P0-4 隔離要求。

---

## 總分：8 + 22 + 22 + 18 = 70/100

**不合格**（< 90，且需求未完全滿足）

---

## 逐條審查

### P0-1 PostgreSQL Trace Constraint

| 需求 | 狀態 | 審查說明 |
|------|------|----------|
| 1. 查詢 PostgreSQL 目前真正存在的 UNIQUE Constraint | ✅ | migration 025 第 114-137 行：使用 `pg_catalog.pg_constraint` 動態查詢 |
| 2. 刪除 UNIQUE(trace_id) | ✅ | 同一 DO $$ 區塊：查詢到後 EXECUTE DROP CONSTRAINT |
| 3. 建立 UNIQUE(trace_id, step_order) | ✅ | 第 138-148 行：ADD CONSTRAINT uq_trace_step |
| 4. 不得只 DROP INDEX（Constraint vs Index 區分） | ✅ | 操作的是 CONSTRAINT 而非 INDEX |
| 5. 支援同 trace_id 多 step 全部成功 | ✅ | `test_migration_025_pg_trace_constraint.py` 同 trace_id 3 筆 step 全部 PASS |
| 6. 新增 PostgreSQL Integration Test | ✅ | `tests/integration/test_migration_025_pg_trace_constraint.py` |

### P0-2 Migration 025 Downgrade

| 需求 | 狀態 | 審查說明 |
|------|------|----------|
| 1. plan_id UNIQUE | ✅ | downgrade 第 175-185 行：恢復 `domain_treatment_plans_plan_id_key` |
| 2. trace_id UNIQUE | ✅ | downgrade 第 199-208 行：恢復 `domain_treatment_plan_traces_trace_id_key` |
| 3. previous_version_id 移除 | ✅ | downgrade 第 171 行：`drop_column("previous_version_id")` |
| 4. supersedes_version_id 移除 | ✅ | downgrade 第 172 行：`drop_column("supersedes_version_id")` |
| 5. 024→025→024→025 Schema Compare Test | ✅ | `test_migration_025_pg_schema_compare.py`：兩個 test method 分別驗證 downgrade 和 re-upgrade 前後 schema 一致 |

### P0-3 CI Migration Gate

| 需求 | 狀態 | 審查說明 |
|------|------|----------|
| 1. Postgres → upgrade → migration verify → migration tests → downgrade → re-upgrade → verify → PASS | ❌ | **migration-gate Job 缺少 migration tests 步驟**。現有步驟為：create db → upgrade → check → schema validation (inline Python) → downgrade 024 → upgrade head → check → drop db。未執行 `pytest tests/test_migration_gate.py`。 |
| 2. 不得 continue-on-error、skip、allow-failure | ✅ | CI 配置中無這些設定 |

### P0-4 Downgrade Environment

| 需求 | 狀態 | 審查說明 |
|------|------|----------|
| 1. 使用全新 PostgreSQL Database | ✅ | `createdb cancer_db_migration_gate` 建立獨立資料庫 |
| 2. 流程：create db → upgrade → verify → downgrade → upgrade → verify | ✅ | 步驟順序正確 |
| 3. Migration Gate 與 Integration Test 必須隔離 | ⚠️ 部分滿足 | migration-gate Job 使用獨立資料庫 ✅；但 Integration Tests（`test_migration_025_pg_*.py`）在 `backend` Job 中透過 `cancer_db` 運行，**未使用隔離資料庫** ❌ |

### P1 PostgreSQL Migration Robustness

| 需求 | 狀態 | 審查說明 |
|------|------|----------|
| DROP CONSTRAINT / DROP INDEX → IF EXISTS | ✅ | 全部使用 `IF EXISTS` |
| ADD CONSTRAINT / CREATE INDEX → IF NOT EXISTS 或動態 pg_constraint | ✅ | 使用 `IF NOT EXISTS` + DO $$ 區塊 |
| SQLite 仍保持相容 | ✅ | `batch_alter_table` 分支正確處理 |

### P1 Tests

| 需求 | 狀態 | 審查說明 |
|------|------|----------|
| 1. Trace Constraint：同 trace_id 三筆 step 全部 PASS | ✅ | `test_migration_025_pg_trace_constraint.py` |
| 2. Downgrade 驗證：025→024 Schema Equal → 025 Schema Equal | ✅ | `test_migration_025_pg_schema_compare.py` |
| 3. PostgreSQL 真實：upgrade → downgrade → upgrade → insert → query | ✅ | `test_migration_025_pg_full_cycle.py` |
| 4. GitHub Actions Backend 全部 SUCCESS | ⏳ 無法驗證 | 需實際 CI 運行結果。但 CI 配置中無 continue-on-error 等規避設定。 |

### 核心原則遵守

| 原則 | 狀態 | 審查說明 |
|------|------|----------|
| 不得修改業務功能 | ✅ | 僅 Database Schema 變更 |
| 不得修改 Engine | ✅ | Engine 程式碼未變動 |
| 不得修改 API 行為 | ✅ | API 行為未變動 |
| 不得修改 Frontend | ✅ | Frontend 未變動 |

### 完成交付清單

| 項次 | 項目 | 狀態 |
|------|------|------|
| 1 | Commit SHA | ⏳ 無法驗證（需實際 CI） |
| 2 | Files Changed | ✅ 可確認 |
| 3 | Migration 025 修改內容 | ✅ |
| 4 | 新增 PostgreSQL Tests | ✅ |
| 5 | 新增 CI Tests | ❌ `test_migration_gate.py` 未被 CI 執行 |
| 6-14 | Run ID / Backend 結果 / Frontend 結果 / 驗證結果 | ⏳ 需實際 CI 運行 |
| 15 | Reviewer Score (>=95) | ❌ 目前 70 分，不合格 |

---

## 總結

**主要問題**：CI 的 `migration-gate` Job 中**遺漏了 `pytest tests/test_migration_gate.py` 的執行步驟**，違反 P0-3「完整執行 migration tests」及「新增 CI Tests」要求。此外，PostgreSQL Integration Tests 在 `backend` Job 中使用共用資料庫而非隔離資料庫，違反 P0-4 的隔離原則。

**建議修正**：
1. 在 `migration-gate` Job 的「Migration schema validation」步驟之後（或取代該內聯腳本），加入：
   ```yaml
   - name: Migration tests
     env:
       DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/cancer_db_migration_gate
     run: pytest -v --tb=short tests/test_migration_gate.py tests/integration/test_migration_025_pg_*.py
   ```
2. 確保 Integration Tests 使用 Migration Gate 的獨立資料庫，而非 `cancer_db`。

**總分 70/100 → 不合格** ❌
