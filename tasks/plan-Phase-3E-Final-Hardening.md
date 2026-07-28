# Phase 3E Final Hardening — 執行計劃

> 任務 ID：Phase-3E-Final-Hardening  
> 場景：hardening（架構強化）  
> 核心原則：不得修改業務功能、Engine、API 行為、Frontend

---

## 檔案結構參考

| 檔案 | 路徑 |
|------|------|
| Migration 025 原始碼 | `migrations/versions/025_phase3e_version_composite_unique.py` |
| 現有 Migration 測試 | `tests/test_migration.py` (含 `TestMigration025Upgrade`) |
| 現有 Integration Test | `tests/integration/test_migration_016.py` |
| CI Pipeline | `.github/workflows/ci.yml` |
| Alembic env | `migrations/env.py` |
| Trace Model | `src/backend/domain/treatment_plan.py` |

---

## 1. 任務清單（依賴順序）

### Phase A：核心修正（P0）

| ID | 名稱 | 描述 | 負責角色 | 依賴 | 預估工時 |
|----|------|------|---------|------|---------|
| A-01 | **PostgreSQL Trace Constraint 修正** | 修正 Migration 025 upgrade() 中 `domain_treatment_plan_traces` 的 constraint 處理：查詢 pg_constraint 找出真正的 UNIQUE(trace_id) constraint 名稱，用 `ALTER TABLE ... DROP CONSTRAINT` 刪除，再用 `create_unique_constraint` 建立 UNIQUE(trace_id, step_order)。不得使用 DROP INDEX / CREATE INDEX。 | backend-logic | 無 | 2h |
| A-02 | **Migration 025 Downgrade 修正** | 修正 Migration 025 downgrade() 中 PostgreSQL 分支：用 `DROP CONSTRAINT IF EXISTS` 刪除 `uq_trace_step`，用 `create_unique_constraint` 或 `ALTER TABLE ... ADD CONSTRAINT` 恢復 UNIQUE(trace_id) 如 024 Schema。同時恢復 `plan_id UNIQUE`（024 原有），移除 `previous_version_id`、`supersedes_version_id`。 | backend-logic | A-01 | 2h |
| A-03 | **Migration 024 Schema 確認** | 仔細比對 Migration 024 的 upgrade() 最終 schema 狀態，確保 A-02 的 downgrade 目標正確：`plan_id` 為 UNIQUE、`trace_id` 為 UNIQUE、無 `previous_version_id`、無 `supersedes_version_id`。 | backend-logic | A-02 | 0.5h |
| A-04 | **CI Migration Gate 強化** | 在 CI 中新增專屬的 Migration Gate job/step：使用全新 PostgreSQL Database → upgrade head → migration verify → migration tests → downgrade 025→024 → re-upgrade 025→head → verify。**不允許** `continue-on-error`、`skip`、`allow-failure`。與 Integration Test 共用 PostgreSQL service 但使用獨立 database name。 | backend-logic | A-02 | 2h |
| A-05 | **Downgrade Environment 隔離** | CI Migration Gate 使用全新 PostgreSQL Database（如 `cancer_db_migration_gate`），流程：`create db → upgrade head → migration verify → downgrade 024 → upgrade head → verify`。Migration Gate 與 Integration Test 的 database 完全隔離。 | backend-logic | A-04 | 1h |

### Phase B：穩健性強化（P1）

| ID | 名稱 | 描述 | 負責角色 | 依賴 | 預估工時 |
|----|------|------|---------|------|---------|
| B-01 | **PostgreSQL Migration Robustness** | 全面檢視 Migration 025 所有 DROP/ADD CONSTRAINT/INDEX 操作，加上 IF EXISTS / IF NOT EXISTS 或動態查詢 pg_constraint / pg_indexes。涵蓋：`ALTER TABLE DROP CONSTRAINT IF EXISTS`、`CREATE UNIQUE CONSTRAINT` 前的檢查。SQLite 分支保持相容。 | backend-logic | A-02 | 1.5h |
| B-02 | **SQLite 分支相容性驗證** | 確保 B-01 的變更不破壞 SQLite batch_alter_table 分支的正確性。SQLite 使用 Alembic batch 模式，行為不變。 | backend-logic | B-01 | 0.5h |

### Phase C：測試撰寫（P1）

| ID | 名稱 | 描述 | 負責角色 | 依賴 | 預估工時 |
|----|------|------|---------|------|---------|
| C-01 | **Trace Constraint PostgreSQL Integration Test** | 撰寫 PostgreSQL Integration Test：在真實 PostgreSQL 上執行 migration 025 upgrade → 插入同 trace_id 三筆不同 step_order（1, 2, 3）→ 全部 INSERT 成功 → SELECT 驗證資料正確。 | test-writer | A-01 | 1.5h |
| C-02 | **Downgrade Schema Compare Test** | 撰寫 schema compare 測試：025→024 降級後 schema 應與 024 upgrade 後的 schema 完全相等；025→024→025 重新升級後 schema 應與直接 025 相等。使用 SQLAlchemy inspect 比較 table、columns、constraints、indexes。 | test-writer | A-02, A-03 | 2h |
| C-03 | **PostgreSQL Real Upgrade/Downgrade/Insert/Query Test** | 撰寫完整 PostgreSQL 真實流程測試：upgrade head → downgrade 024 → upgrade head → 插入測試資料 → query 驗證 → 全部 PASS。使用獨立 database 或 schema。 | test-writer | A-05, C-01, C-02 | 2h |
| C-04 | **CI Migration Gate Tests** | 在 CI 中使用 pytest 執行 Migration Gate：upgrade → migration verify → migration tests → downgrade → re-upgrade → verify，每個步驟均斷言成功。產出 PASS 結果。 | test-writer | A-04, C-03 | 1.5h |
| C-05 | **現有 TestMigration025Upgrade 強化** | 在 `tests/test_migration.py` 中擴展現有 `TestMigration025Upgrade`，確保 SQLite 測試也驗證同 trace_id 多 step 共存（已有 test_upgrade_025_trace_step1_step2_step3_success）。新增 PostgreSQL 專屬測試 class。 | test-writer | C-01 | 1h |

### Phase D：驗收與評分

| ID | 名稱 | 描述 | 負責角色 | 依賴 | 預估工時 |
|----|------|------|---------|------|---------|
| D-01 | **Reviewer 評分** | REVIEWER 角色對所有交付物評分，目標 >=95。若 <90 則依返工預案修正。 | reviewer | C-01~C-05 | 1h |
| D-02 | **交付物清單驗收** | 對應 15 項交付物逐一檢查，產出最終驗收報告。 | reviewer | D-01 | 0.5h |

---

## 2. 執行順序

```
Phase A (Core Fixes)
  ├── A-01: PostgreSQL Trace Constraint 修正
  ├── A-02: Migration 025 Downgrade 修正
  ├── A-03: Migration 024 Schema 確認
  ├── A-04: CI Migration Gate 強化
  └── A-05: Downgrade Environment 隔離
       │
       ▼
Phase B (Robustness)
  ├── B-01: PostgreSQL Migration Robustness
  └── B-02: SQLite 分支相容性驗證
       │
       ▼
Phase C (Tests)
  ├── C-01: Trace Constraint PostgreSQL Integration Test
  ├── C-02: Downgrade Schema Compare Test
  ├── C-03: PostgreSQL Real Upgrade/Downgrade/Insert/Query Test
  ├── C-04: CI Migration Gate Tests
  └── C-05: 現有 TestMigration025Upgrade 強化
       │
       ▼
Phase D (Review & Acceptance)
  ├── D-01: Reviewer 評分
  └── D-02: 交付物清單驗收
```

### Batch 分組

| Batch | 任務 | 說明 |
|-------|------|------|
| **Batch 1** | A-01, A-02, A-03 | 核心 Migration 程式碼修正，無外部依賴，可平行或依序執行 |
| **Batch 2** | A-04, A-05, B-01, B-02 | CI 強化 + 穩健性，依賴 Batch 1 |
| **Batch 3** | C-01, C-02, C-03, C-04, C-05 | 所有測試，依賴 Batch 1 & Batch 2 |
| **Batch 4** | D-01, D-02 | 最終驗收，依賴 Batch 3 |

---

## 3. 返工預案

若 REVIEWER 評分 < 90，根據扣分項目分類修正：

### 3.1 Migration 邏輯錯誤（扣分權重 40%）

| 扣分原因 | 修正方向 |
|---------|---------|
| PostgreSQL CONSTRAINT 仍使用 INDEX 操作 | 確認 `pg_constraint` 動態查詢正確，使用 `ALTER TABLE ... DROP CONSTRAINT` |
| downgrade 未正確恢復 024 Schema | 重新比對 024 upgrade() 最終狀態，逐 column/constraint 驗證 |
| IF EXISTS/NOT EXISTS 遺漏 | 全面掃描所有 DROP/ADD 操作，補上條件判斷 |
| SQLite 分支被破壞 | 在 SQLite 環境完整執行 upgrade → downgrade → upgrade 循環測試 |

### 3.2 測試涵蓋不足（扣分權重 30%）

| 扣分原因 | 修正方向 |
|---------|---------|
| 缺少 PostgreSQL 真實 downgrade 測試 | 新增獨立 PostgreSQL database 的完整升級/降級流程測試 |
| Schema Compare 未涵蓋所有 constraint 類型 | 擴展 compare 邏輯：比較 UNIQUE、INDEX、FOREIGN KEY、CHECK 全部約束 |
| 未測試同 trace_id 多 step 邊界情況 | 加入 step_order 0、負數、大量 step（20+）的測試 |

### 3.3 CI Gate 缺陷（扣分權重 20%）

| 扣分原因 | 修正方向 |
|---------|---------|
| CI 中未正確隔離 Migration Gate database | 確保使用 `createdb` 建立獨立 database，測試後 drop |
| continue-on-error 未被移除 | 檢查 CI YAML 所有 step 的 `continue-on-error` 設定 |
| Migration verify step 遺漏 | 在每個 upgrade/downgrade 後加入 `alembic check` 或 schema 驗證 |

### 3.4 文件與交付（扣分權重 10%）

| 扣分原因 | 修正方向 |
|---------|---------|
| 15 項交付物未完整填寫 | 對照清單逐項補齊 Commit SHA、Run ID、驗證狀態 |
| Reviewer 評分備註未回應 | 逐一處理 reviewer 的改進建議並在備註中標註 "已修正" |

### 修正流程

```
REVIEWER 評分 < 90
  │
  ├─→ 分類扣分項目
  ├─→ 針對性修正（修改程式碼或補測試）
  ├─→ 重新執行 Full CI (含 Migration Gate)
  ├─→ 再次送 REVIEWER 評分
  └─→ 直到 >=95 或 >=90 且無 P0/P1 未解決問題
```

---

## 4. 交付驗收清單

對應 15 項交付物，每項的驗收標準與負責角色：

| # | 交付物 | 驗收標準 | 負責角色 | 驗收方式 |
|---|--------|---------|---------|---------|
| 1 | **Commit SHA** | Git commit hash 存在且對應到本次所有變更 | reviewer | `git rev-parse HEAD` |
| 2 | **Files Changed** | git diff 或 PR 顯示所有修改檔案清單，僅限 Migration 025、CI、測試檔案 | reviewer | `git diff --stat` |
| 3 | **Migration 025 修改內容** | Migration 025 的 PostgreSQL constraint 已修正為正確的 CONSTRAINT 操作，downgrade 正確恢復 024 Schema | backend-logic | 程式碼審查 + PostgreSQL 實際執行 |
| 4 | **新增 PostgreSQL Tests** | 新增的 PostgreSQL Integration Test 檔案存在，測試同 trace_id 多 step 全部成功 | test-writer | `ls tests/integration/test_migration_025_pg*.py` |
| 5 | **新增 CI Tests** | CI Migration Gate tests 檔案存在，測試流程完整 | test-writer | `ls tests/test_migration_gate*.py` |
| 6 | **Run ID** | GitHub Actions Workflow Run ID，對應到所有 CI Job 全部成功 | reviewer | CI Run URL |
| 7 | **Backend 結果 (SUCCESS)** | CI Backend Job 全部步驟 SUCCESS | reviewer | CI Run 頁面 |
| 8 | **Frontend 結果 (SUCCESS)** | CI Frontend Job SUCCESS（如有修改需通過，否則沿用） | reviewer | CI Run 頁面 |
| 9 | **Migration Verification (PASS)** | `alembic check` 或 schema 比對驗證 upgrade 後 schema 正確 | backend-logic | CI step 輸出 |
| 10 | **Migration Tests (PASS)** | 所有 migration 相關 pytest 全部 PASS | test-writer | `pytest tests/test_migration.py -v` |
| 11 | **Downgrade (PASS)** | 025→024 降級成功，schema 恢復正確 | backend-logic | CI Downgrade step 輸出 |
| 12 | **Re-upgrade (PASS)** | 024→025 重新升級成功，schema 正確 | backend-logic | CI Re-upgrade step 輸出 |
| 13 | **Schema Compare (PASS)** | 025→024 降級後 schema = 024 直接 upgrade schema；025→024→025 後 schema = 直接 025 | test-writer | Schema Compare Test 輸出 |
| 14 | **git status** | 工作目錄乾淨，無未提交變更 | reviewer | `git status` |
| 15 | **Reviewer Score (>=95)** | REVIEWER 評分 >=95，若 <90 需返工 | reviewer | 評分報告 |

### 最終驗收條件（ALL MUST PASS）

- [ ] Backend SUCCESS
- [ ] Frontend SUCCESS
- [ ] Migration Verification PASS
- [ ] Migration Tests PASS
- [ ] Upgrade PASS
- [ ] Downgrade PASS
- [ ] Re-upgrade PASS
- [ ] Schema Compare PASS
- [ ] Reviewer Score >= 95

> **否則不得宣告 Accepted 或 Ready for Next Phase。**

---

## 5. Migration 025 具體修改指引（技術實作細節）

### 5.1 upgrade() — PostgreSQL Trace Constraint 修正

現有問題程式碼（第 89-93 行）：
```python
op.execute("DROP INDEX IF EXISTS uq_trace_step")
op.execute("DROP INDEX IF EXISTS ix_domain_treatment_plan_traces_trace_id")
op.create_index("uq_trace_step", "domain_treatment_plan_traces",
                ["trace_id", "step_order"], unique=True)
```

修正後應為：
```python
# 動態查詢 pg_constraint 找出 UNIQUE(trace_id) 的 constraint 名稱
op.execute("""
    DO $$
    DECLARE
        con_name text;
    BEGIN
        SELECT con.conname INTO con_name
        FROM pg_catalog.pg_constraint con
        JOIN pg_catalog.pg_class rel ON rel.oid = con.conrelid
        WHERE rel.relname = 'domain_treatment_plan_traces'
          AND con.contype = 'u'
          AND con.conkey = (
              SELECT array_agg(a.attnum ORDER BY a.attnum)
              FROM pg_catalog.pg_attribute a
              WHERE a.attrelid = rel.oid
                AND a.attname = 'trace_id'
          );
        IF con_name IS NOT NULL THEN
            EXECUTE format(
                'ALTER TABLE domain_treatment_plan_traces DROP CONSTRAINT %I',
                con_name
            );
        END IF;
    END $$;
""")
# 建立複合 UNIQUE constraint
op.create_unique_constraint(
    "uq_trace_step",
    "domain_treatment_plan_traces",
    ["trace_id", "step_order"],
)
```

### 5.2 upgrade() — domain_treatment_plans 既有邏輯確認

現有 PostgreSQL 分支（第 54-79 行）使用 `DROP CONSTRAINT IF EXISTS` 是正確的做法，但應確認所有可能的 constraint 名稱都已涵蓋。建議統一使用動態查詢 `pg_constraint` 的方式，確保無論 constraint 名稱為何都能正確刪除。

### 5.3 downgrade() — PostgreSQL Trace Constraint 修正

現有問題程式碼（第 129-134 行）：
```python
op.execute("DROP INDEX IF EXISTS uq_trace_step")
op.execute(
    "CREATE UNIQUE INDEX ix_domain_treatment_plan_traces_trace_id "
    "ON domain_treatment_plan_traces (trace_id)"
)
```

修正後應為：
```python
# 用 DROP CONSTRAINT IF EXISTS 刪除複合 UNIQUE
op.execute("ALTER TABLE domain_treatment_plan_traces DROP CONSTRAINT IF EXISTS uq_trace_step")
# 恢復 024 schema 的 UNIQUE(trace_id)
op.create_unique_constraint(
    "ix_domain_treatment_plan_traces_trace_id",
    "domain_treatment_plan_traces",
    ["trace_id"],
)
```

### 5.4 downgrade() — domain_treatment_plans 恢復 024 Schema

確認 downgrade 正確：
1. 刪除 FK: `fk_supersedes_version`, `fk_prev_version` ✅
2. 刪除 Index: `ix_domain_treatment_plans_sup_ver`, `ix_domain_treatment_plans_prev_ver` ✅
3. 刪除 Column: `supersedes_version_id`, `previous_version_id` ✅
4. 刪除複合 UNIQUE: `DROP CONSTRAINT IF EXISTS uq_plan_id_version`（第 118 行）✅
5. **恢復 plan_id UNIQUE**（024 原有）：目前第 118 行後缺少此步驟！需加入：
   ```python
   op.create_unique_constraint("uq_treatment_plan_version", "domain_treatment_plans", ["plan_id"])
   ```

### 5.5 CI Migration Gate YAML 修改

在 `.github/workflows/ci.yml` 中新增或修改：

```yaml
  migration-gate:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: cancer_db
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install dependencies
        run: |
          pip install -r src/backend/requirements-api.txt
          pip install pytest psycopg2-binary
      - name: Create isolated database for Migration Gate
        env:
          PGPASSWORD: postgres
        run: createdb -h localhost -U postgres cancer_db_migration_gate
      - name: Upgrade head
        env:
          DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/cancer_db_migration_gate
          PYTHONPATH: .
        run: alembic -c migrations/alembic.ini upgrade head
      - name: Migration verify
        env:
          DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/cancer_db_migration_gate
          PYTHONPATH: .
        run: alembic -c migrations/alembic.ini check
      - name: Migration tests (PostgreSQL)
        env:
          DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/cancer_db_migration_gate
          PYTHONPATH: .
        run: pytest -v --tb=long tests/test_migration.py -k "pg"
      - name: Downgrade 024
        env:
          DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/cancer_db_migration_gate
          PYTHONPATH: .
        run: alembic -c migrations/alembic.ini downgrade 024
      - name: Re-upgrade head
        env:
          DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/cancer_db_migration_gate
          PYTHONPATH: .
        run: alembic -c migrations/alembic.ini upgrade head
      - name: Final verify
        env:
          DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/cancer_db_migration_gate
          PYTHONPATH: .
        run: alembic -c migrations/alembic.ini check
      - name: Drop migration gate database
        if: always()
        env:
          PGPASSWORD: postgres
        run: dropdb -h localhost -U postgres cancer_db_migration_gate
```

> **注意**：以上 YAML 為指引，實際實作時需根據 CI 的 PostgreSQL service 連線方式調整。

---

## 6. 風險與配套措施

| 風險 | 可能性 | 影響 | 配套措施 |
|------|--------|------|---------|
| PostgreSQL pg_constraint 動態查詢語法錯誤 | 中 | Migration 執行失敗 | 先在本地 PostgreSQL 測試再提交 CI |
| SQLite 與 PostgreSQL 邏輯分歧 | 低 | 跨資料庫相容性問題 | 確保 SQLite 分支完全不變，只在 PostgreSQL 分支修改 |
| CI Migration Gate 耗時過長 | 低 | CI 逾時 | 設定合理 timeout，必要時增加 runner |
| 現有 TestMigration025Upgrade 使用 SQLite 無法測試 PostgreSQL | 中 | PostgreSQL 專屬測試需要真實 DB | 使用 GitHub Actions PostgreSQL service 做真實測試 |
| downgrade 時 `uq_treatment_plan_version` constraint 名稱衝突 | 低 | constraint 名稱已存在 | 使用 `IF NOT EXISTS` 或動態檢查 |

---

*本計劃由 PLANNER 產出，版本 1.0，待 REVIEWER 審查後執行。*
