# Phase 3C CI Final Fix — 總結報告

## CI Run

| 項目 | 值 |
|------|------|
| **Final Run ID** | 30235816895 |
| **Commit SHA** | 437581a |
| **Backend Job** | ✅ **success** |
| **Frontend Job** | ✅ **success** |
| **Overall Conclusion** | ✅ **success** |

## 修復摘要

### 1. CI Workflow YAML
- **根因：** Commit `01f431a` 內聯 Python 在 `run: |` block scalar 中未縮排，GitHub Actions 無法解析（jobs = 0）
- **修復：** 修正 Python 縮排 + 新增 `workflow_dispatch` trigger

### 2. Ruff Lint 錯誤（46 個）
- **自動修復（44 個）：** import sorting（I001）、unused imports（F401）、f-string（F541）
- **手動修復（2 個）：**
  - `F821 decision_rules.py:350` — `detect_contraindications` 方法簽名缺少 `evidence` 參數，導致未定義名稱
  - `F841 clinical_decision_engine.py:218` — 未使用變數 `top_drug_entry`

### 3. Frontend Build
- **根因：** `SpecialistOpinion` 介面 `confidence` 型別為 `string` 但實際值為 `number`；缺少 `participant_id` 欄位
- **修復：** 修正 interface 定義 + `confidenceBadge()` 函數支援數值

### 4. Postgres Migration（Alembic upgrade）
- **根因：** Migration 020 使用 `server_default=sa.text("0")` 對 Boolean 欄位，Postgres 不接受整數作為 Boolean 預設值
- **修復：** 改為 `sa.text("false")`

### 5. Postgres Restart Recovery Test
- **根因：** 
  - Service 層 `datetime.now(UTC)` 回傳 timezone-aware datetime，asyncpg 無法與其他 naive datetime 混合編碼
  - 測試使用 sync engine（psycopg2）與 async engine（asyncpg）混用導致 datetime 型別不一致
  - `created_by` FK 需要使用者記錄存在
- **修復：**
  - Service 層 `datetime.now(UTC)` → `datetime.utcnow()`
  - 測試使用 sync engine 並明確 `engine.dispose()`
  - 測試預先建立使用者記錄

### 6. CI Migration Downgrade 測試
- **根因：** Tumor Board 測試執行後遺留資料在 DB 中，導致 downgrade 檢查失敗
- **修復：** Clean up 步驟改為刪除三個 Tumor Board 表全部資料

## 最終狀態

| 項目 | 結果 |
|------|------|
| Ruff Check | ✅ PASS |
| Frontend Build | ✅ PASS |
| Backend Tests | ✅ PASS |
| Frontend Tests | ✅ PASS |
| Postgres Migration | ✅ PASS |
| Tumor Board Postgres Tests | ✅ PASS |
| Restart Recovery | ✅ PASS |
| Migration Downgrade | ✅ PASS |
| Migration Re-upgrade | ✅ PASS |

**Phase 3C Accepted：** ✅ YES
**Ready for Phase 3D：** ✅ YES
