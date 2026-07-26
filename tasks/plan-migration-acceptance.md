# Phase 3B Final Migration Acceptance — 修復計劃

## 任務 ID 與依賴關係

| ID | 描述 | 依賴 | 角色 | 優先級 |
|----|------|------|------|--------|
| MIG-1 | Migration 019 downgrade 策略實作（策略A） | 無 | backend-logic | P0 |
| MIG-2 | Migration Tests（3 個 Case） | MIG-1 | test-writer | P0 |
| MIG-3 | API Hardening（skip/limit Query 驗證） | 無 | backend-logic | P0 |
| MIG-4 | 全面測試驗證（後端測試 + CI） | MIG-1, MIG-2, MIG-3 | test-writer | P0 |
| MIG-5 | Git Commit & Push | MIG-4 | backend-logic | P0 |

**執行順序**：MIG-1 → MIG-3 (並行) → MIG-2 → MIG-4 → MIG-5

---

## MIG-1：Migration 019 downgrade 策略實作

### 實作步驟
1. **修改 `migrations/versions/019_phase3b_trace_compound_unique.py` 的 `downgrade()`**
   - 在執行任何 index 操作前，先檢查 `domain_clinical_decision_traces` 表中是否有同一 `trace_id` 出現多筆的情況
   - 使用 Alembic `op.get_bind()` 取得 connection，執行 SQL 查詢
   - SQL 查詢：
     ```sql
     SELECT trace_id FROM domain_clinical_decision_traces
     GROUP BY trace_id HAVING COUNT(*) > 1
     LIMIT 1
     ```
   - 若查到結果（存在多 step trace），則 raise `RuntimeError("Cannot downgrade Migration 019. Database already contains multi-step Clinical Decision Trace. Downgrade would destroy persisted data.")`
   - 若無多 step trace（空資料庫或所有 trace 只有單一步驟），則正常執行原本的 downgrade 邏輯

2. **檢查 `upgrade()` 是否需要修改**
   - 不需要 — upgrade 只在空資料庫成功，原有邏輯正確

### 檔案修改清單
- **修改**：`migrations/versions/019_phase3b_trace_compound_unique.py`

### 驗證方式
- 空資料庫執行 downgrade → PASS（現有行為不變）
- 含 5 個 step 的 trace 執行 downgrade → 拋出 RuntimeError → error message 完全匹配

### 返工預案
- 若 Alembic 環境中 `RuntimeError` 未被適當捕獲，改用 `sa.Exc` 或 `sys.exit(1)` 但此專案標準是 raise。確認上層（Alembic CLI）可正確顯示錯誤訊息

---

## MIG-2：Migration Tests（3 個 Case）

### 實作步驟
1. **修改 `tests/test_migration.py`**，在 `TestMigration019` 類別中新增 3 個測試方法（對應 Case1~Case3）

   **Case1：test_downgrade_019_empty_db_success**
   ```
   018 → 019 → Empty Database → 018 → PASS
   ```
   - 升級到 018 → 升級到 019 → 不插入任何資料 → 降級到 018
   - 驗證：`ix_domain_clinical_decision_traces_trace_id` 恢復 UNIQUE

   **Case2：test_downgrade_019_multi_step_fails**
   ```
   018 → 019 → Insert 5 Trace Steps → Downgrade → 明確失敗 → Error Message 正確
   ```
   - 升級到 018 → 升級到 019
   - 插入 5 行（同一 trace_id，step_order 1~5）
   - 執行 downgrade 到 018
   - 驗證：`RuntimeError` 被拋出
   - 驗證：error message 包含 `"Cannot downgrade Migration 019. Database already contains multi-step Clinical Decision Trace. Downgrade would destroy persisted data."`
   - 驗證：降級後資料仍存在（未遺失）

   **Case3：test_reupgrade_019_after_failed_downgrade**
   ```
   018 → 019 → Insert 5 Trace Steps → Downgrade (fail) → Re-upgrade → PASS
   ```
   - 升級到 018 → 升級到 019 → 插入 5 行 → downgrade 預期失敗
   - 再次執行 upgrade 到 019（此時資料庫仍在 019 狀態，但需確認 Alembic 行為）
   - 驗證：compound index `uq_trace_step` 仍存在

2. **注意事項**
   - `command.downgrade(cfg, "018")` 拋出異常時需用 `pytest.raises(RuntimeError)` 捕獲
   - 需要檢查 Alembic 的 `command.downgrade()` 是否包裝了例外。Alembic 的 `command.downgrade()` 預設會捕獲異常並 `raise`。可能需要用 `pytest.raises(Exception)` 或直接測試 migration 模組的 `downgrade()` 函數
   - 若 `command.downgrade()` 拋出的是 Alembic 包裝後的例外（如 `alembic.util.exc.CommandError`），則需調整捕獲類型
   - 可以先模仿行測試 migration module 的 downgrade 函數行為

### 檔案修改清單
- **修改**：`tests/test_migration.py`（在 `TestMigration019` 類別中新增 3 個測試方法）

### 驗證方式
- `pytest tests/test_migration.py -k "TestMigration019" -v` → 現有測試 + 3 個新測試全部 PASS

### 返工預案
- 若 Alembic CLI 包裝了例外導致無法直接捕獲 RuntimeError，改為測試 migration module 的 `downgrade()` 函數本身（import module 後直接呼叫）
- 若 SQLite 不支援 COUNT 子查詢，改用 `SELECT COUNT(*) FROM (SELECT trace_id FROM domain_clinical_decision_traces GROUP BY trace_id HAVING COUNT(*) > 1)`

---

## MIG-3：API Hardening（skip/limit Query 驗證）

### 實作步驟
1. **修改 `src/backend/api/v1/clinical_decision.py`**
   - 找到 `list_clinical_decisions` 函數中的 `skip: int = 0`
   - 改為 `skip: int = Query(0, ge=0)`
   - 找到 `limit: int = 50`
   - 改為 `limit: int = Query(50, ge=1, le=100)`

2. **檢查是否需補上 `from fastapi import Query`**
   - 檔案已 import `HTTPException`，但確認是否 import `Query`
   - `Query` 是 FastAPI 匯出，不需額外安裝

### 檔案修改清單
- **修改**：`src/backend/api/v1/clinical_decision.py`

### 驗證方式
- `python -c "import ast; ast.parse(open('src/backend/api/v1/clinical_decision.py').read())"` → 語法正確
- 執行現有 API 測試確認不破壞功能

### 返工預案
- 若 FastAPI 版本不支援 `Query` 作為類型註解的預設值（較舊版本），改用 `Query(default=0, ge=0)` 而非 `Query(0, ge=0)`

---

## MIG-4：全面測試驗證

### 實作步驟
1. 執行所有 migration 測試：
   ```bash
   cd D:\AI-Future\AI-Kill-Cancer
   python -m pytest tests/test_migration.py -v
   ```

2. 執行所有 API 測試：
   ```bash
   python -m pytest tests/ -v
   ```

3. 確認無測試失敗

### 驗證方式
- Migration Tests 全部 PASS（3 Cases + 既有測試）
- API Tests（含 hardening）全部 PASS
- 語法檢查通過

### 返工預案
- 若既有測試因本次修改而失敗，定位問題並修正

---

## MIG-5：Git Commit & Push

### 實作步驟
1. Stage 修改的檔案：
   - `migrations/versions/019_phase3b_trace_compound_unique.py`
   - `src/backend/api/v1/clinical_decision.py`
   - `tests/test_migration.py`

2. Commit：
   ```bash
   git add migrations/versions/019_phase3b_trace_compound_unique.py src/backend/api/v1/clinical_decision.py tests/test_migration.py
   git commit -m "fix(migration): make downgrade safe for multi-step traces"
   ```

3. Push：
   ```bash
   git push origin master
   ```

### 驗證方式
- `git log -1` 確認 commit message 正確
- `git status` 確認無未提交檔案

### 返工預案
- Push 失敗時確認遠端權限與網路連線

---

## 總結：檔案修改清單

| 檔案 | 操作 | 說明 |
|------|------|------|
| `migrations/versions/019_phase3b_trace_compound_unique.py` | 修改 | downgrade() 加入多 step trace 檢查 + 拋出 RuntimeError |
| `src/backend/api/v1/clinical_decision.py` | 修改 | list_clinical_decisions 的 skip/limit 改用 Query(ge/le) 驗證 |
| `tests/test_migration.py` | 修改 | 在 TestMigration019 新增 3 個測試方法（Case1~Case3） |
