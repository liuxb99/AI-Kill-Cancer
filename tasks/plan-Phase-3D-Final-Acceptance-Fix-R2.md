# Phase 3D Final Acceptance Fix Round 2 — 執行計劃

## 任務概述

本輪針對 Phase 3D 最終驗收的修復任務，共 4 個 P0 問題。目標是真正解決問題（而非讓 CI 變綠），所有修復必須有客觀證據支持。

---

## 1. 角色對照

| 角色 | 負責人 | 負責任務 |
|------|--------|---------|
| PLANNER | planner | 制定執行計劃（本文件） |
| devops | devops | P0-1（CI 配置修復）、P0-4（CI 固定 SHA） |
| backend-logic | backend-logic | P0-1.2（Postgres Migration 相容性修復） |
| test-writer | test-writer | P0-2（Stub Preservation 測試強化）、P0-3 測試部分 |
| knowgraphgo-dev | knowgraphgo-dev | P0-3（Relation Query 查詢能力實現/利用） |
| REVIEWER | reviewer | 評分驗證 |

---

## 2. 任務清單

### Phase 0: 前置分析與準備

| ID | 任務 | 負責角色 | 依賴 | 預計工時 |
|----|------|---------|------|---------|
| T0.1 | 分析現有 CI 配置與 Migration 失敗原因 | backend-logic + devops | 無 | 1h |
| T0.2 | 鎖定 KnowGraphGo 目標 SHA 並驗證存在 | devops | T0.1 | 0.5h |

### Phase 1: P0-1 — Postgres Integration Gate

| ID | 任務 | 負責角色 | 依賴 | 預計工時 |
|----|------|---------|------|---------|
| T1.1 | 移除 ci.yml 中三個 continue-on-error | devops | T0.1 | 0.2h |
| T1.2 | 修復 Migration 022 Postgres 相容性（PRAGMA 改用 information_schema） | backend-logic | T0.1 | 1h |
| T1.3 | 修復 Migration 020 downgrade async/sync 不匹配問題 | backend-logic | T0.1 | 1h |
| T1.4 | 修復 Migration 019 compound unique constraint 在 Postgres 的相容性 | backend-logic | T0.1 | 0.5h |
| T1.5 | 修復 Migration downgrade/re-upgrade 中 Postgres 特有的 FK 問題 | backend-logic | T1.2, T1.3 | 1h |
| T1.6 | 本地執行 Alembic upgrade → 測試 → downgrade → re-upgrade 完整驗證 | backend-logic + devops | T1.2-T1.5 | 1h |
| T1.7 | 更新 CI 下 Postgres Gate 腳本，移除臨時 INSERT/DELETE hack | devops | T1.6 | 0.3h |

### Phase 2: P0-2 — Stub Preservation

| ID | 任務 | 負責角色 | 依賴 | 預計工時 |
|----|------|---------|------|---------|
| T2.1 | 修改 cross_repo_e2e_test.py，在每個 entity 建立後都驗證 Patient Properties | test-writer | 無 | 2h |
| T2.2 | 新增 four-times verification 順序：patient→verify→rec→verify→decision→verify→consensus→verify | test-writer | T2.1 | 0.5h |
| T2.3 | 驗證五欄位：display_name, sex, age_range, cancer_type, source_system | test-writer | T2.2 | 0.3h |
| T2.4 | 本地執行 pytest 驗證修改正確 | test-writer | T2.3 | 0.5h |

### Phase 3: P0-3 — Relation Provenance

| ID | 任務 | 負責角色 | 依賴 | 預計工時 |
|----|------|---------|------|---------|
| T3.1 | 分析 KnowGraphGo CLI 現有 edge get 功能如何讀取 relation 完整屬性 | knowgraphgo-dev | 無 | 0.5h |
| T3.2 | 在 cross_repo_e2e_test.py 中新增真正 Relation Query（使用 `edge get` 或 `query prop` 搭配 graph_id） | test-writer + knowgraphgo-dev | T3.1 | 2h |
| T3.3 | 驗證八個 Provenance 欄位：event_id, event_type, aggregate_type, aggregate_id, correlation_id, causation_id, occurred_at, source_system | test-writer | T3.2 | 0.5h |
| T3.4 | 本地執行 go test + pytest 驗證修改正確 | knowgraphgo-dev + test-writer | T3.3 | 0.5h |

### Phase 4: P0-4 — KnowGraphGo Checkout

| ID | 任務 | 負責角色 | 依賴 | 預計工時 |
|----|------|---------|------|---------|
| T4.1 | 修改 CI 中 KnowGraphGo checkout 步驟：固定 SHA 6d2b20a68ba6ea25841e142918e186fb4beece0d | devops | T0.2 | 0.5h |
| T4.2 | 改用 `git fetch --depth=1 origin <SHA>` 直接抓取特定 commit | devops | T4.1 | 0.3h |
| T4.3 | 移除 `git fetch origin main` 和 `checkout FETCH_HEAD` | devops | T4.2 | 0.2h |
| T4.4 | 確保 CI 中兩處 Checkout KnowGraphGo（步驟 56 和 193）都更新 | devops | T4.3 | 0.3h |

### Phase 5: 整合驗證

| ID | 任務 | 負責角色 | 依賴 | 預計工時 |
|----|------|---------|------|---------|
| T5.1 | 本地執行 go test ./... | knowgraphgo-dev | T3.4, T4.4 | 0.5h |
| T5.2 | 本地執行 pytest（含 all tests） | test-writer + backend-logic | T1.6, T2.4, T3.4 | 0.5h |
| T5.3 | 提交 PR、觸發完整 GitHub Actions | devops | T5.1, T5.2 | 0.5h |
| T5.4 | 驗證 CI 全部步驟 PASS（無 continue-on-error） | devops + reviewer | T5.3 | 1h |

### Phase 6: 回報

| ID | 任務 | 負責角色 | 依賴 | 預計工時 |
|----|------|---------|------|---------|
| T6.1 | 收集 10 項客觀證據並產出最終報告 | reviewer | T5.4 | 0.5h |

---

## 3. 執行順序與依賴圖

```
T0.1 ──┬── T1.1 → T1.7 ──┐
       ├── T1.2 → T1.5 → T1.6 ──┤
       ├── T1.3 → ───────────┘  │
       ├── T1.4 → ──────────┐   │
       │                     │   │
T0.2 ──┴── T4.1 → T4.2 → T4.3 → T4.4 ──┐
                                        │
T2.1 → T2.2 → T2.3 → T2.4 ─────────────┤
                                        ├── T5.1 → T5.2 → T5.3 → T5.4 → T6.1
T3.1 → T3.2 → T3.3 → T3.4 ─────────────┘
```

**執行順序建議：**
1. T0.1 + T0.2（並行分析）
2. T1.1 → T1.2 + T1.3 + T1.4（並行修復） → T1.5 → T1.6 → T1.7
3. T2.1 → T2.2 → T2.3 → T2.4（可與 Phase 1 並行）
4. T3.1 → T3.2 → T3.3 → T3.4（可與 Phase 1/2 並行）
5. T4.1 → T4.2 → T4.3 → T4.4（可與 Phase 1/2/3 並行）
6. T5.1 → T5.2 → T5.3 → T5.4（需所有 Phase 完成）
7. T6.1（最終回報）

---

## 4. 詳細技術方案

### P0-1: Postgres Integration Gate

#### T1.1 移除 continue-on-error

檔案：`.github/workflows/ci.yml`
- 第 232 行：`continue-on-error: true` → 移除
- 第 239 行：`continue-on-error: true` → 移除
- 第 257 行：`continue-on-error: true` → 移除

#### T1.2 修復 Migration 022 Postgres 相容性

**問題**：`_has_column()` 使用 `PRAGMA table_info()`，這是 SQLite 專用語法，Postgres 上會失敗。

**方案**：改用跨資料庫相容的方式檢查欄位是否存在：
```python
def _has_column(table: str, column: str) -> bool:
    conn = op.get_bind()
    dialect = conn.dialect.name
    if dialect == "sqlite":
        rows = conn.execute(sa.text(f"PRAGMA table_info({table})")).fetchall()
        return any(row[1] == column for row in rows)
    elif dialect == "postgresql":
        rows = conn.execute(sa.text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = :table AND column_name = :column"
        ), {"table": table, "column": column}).fetchall()
        return len(rows) > 0
    else:
        return False  # 其他資料庫走 try/except
```

#### T1.3 修復 Migration 020 downgrade async/sync 不匹配

**問題**：Migration 020 的 `downgrade()` 使用 `op.get_bind()` 後執行 `bind.execute(sa.text(...))`，但因為 `env.py` 使用 `create_async_engine`，回傳的 connection 是 async 的。在同步 alembic migration 中，這可能導致 `RuntimeError: no active sqlalchemy connection` 或 async/sync 不匹配。

**方案**：修改 `env.py` 在執行 downgrade 時使用 sync engine，或修改 `downgrade()` 避免直接使用 `bind.execute()`。建議方案：
1. 在 `env.py` 中為 migration 建立一個 sync engine（使用 `psycopg2` 替代 `asyncpg`）
2. 或修改 Migration 020/021/022 的 downgrade 函數，使用 `op.get_bind()` 回傳的 connection 的 `execute()` 方法（已存在的 connection）

**現狀分析**：`env.py` 使用 `create_async_engine`，但 `run_migrations_online()` 已經在 `connection.run_sync(do_run_migrations)` 中包裝了 sync 上下文，所以在 `do_run_migrations` 內部 `op.get_bind()` 回傳的 connection 是可用的 sync connection。問題可能在於 Migration 020 的 `downgrade()` 中 `bind.execute(sa.text(...))` — 如果這個 `bind` 不是 `op.get_bind()` 而是 `op.get_bind()` 是對的，但返回的是 proxy connection。

**實際修復**：在 `env.py` 的 `run_migrations_online()` 中，確保使用 sync driver（`psycopg2` 而非 `asyncpg`）來執行 alembic migration：
```python
db_url = config.get_main_option("sqlalchemy.url")
# 將 async driver 替換為 sync driver
sync_url = db_url.replace("+asyncpg", "+psycopg2").replace("+aiosqlite", "+pysqlite")
```

#### T1.4 修復 Migration 019 compound unique constraint

**問題**：Migration 019 的 compound unique constraint 可能使用 SQLite 特有語法。

**方案**：檢查 Migration 019 中的 `UniqueConstraint` 定義，確保使用跨資料庫相容的語法。如果使用了 `sqlite_autoincrement` 或其他 SQLite 特有功能，需改為標準 SQL。

#### T1.5 修復 downgrade/re-upgrade 流程

**問題**：CI 中的 downgrade 測試在 Postgres 上插入資料後進行 downgrade 測試，但可能因為 FK 關聯導致失敗。

**方案**：
1. 修正資料插入的順序（先 parent 再 child）
2. 確保 DELETE 順序正確（先 child 再 parent）
3. 針對每個 Migration 的 downgrade，確保反向相容性

#### T1.7 更新 CI 腳本

**問題**：CI 中 Postgres 測試腳本包含大量手動 INSERT/DELETE hack。

**方案**：簡化測試流程，讓 alembic 自動處理 downgrade/re-upgrade，移除不必要的資料操作 hack（只要 migration 本身正確，不需要手動插入測試資料來驗證 downgrade 被阻止）。

### P0-2: Stub Preservation

#### T2.1-T2.3 修改 E2E 測試

在 `scripts/cross_repo_e2e_test.py` 中：

1. **創建 patient.created** → 立即驗證五欄位
2. **創建 recommendation.created** → 再次驗證 Patient 五欄位不變
3. **創建 clinical_decision.created** → 再次驗證 Patient 五欄位不變
4. **創建 tumor_board_consensus.created** → 再次驗證 Patient 五欄位不變

驗證欄位：
```python
STUB_FIELDS = ["display_name", "sex", "age_range", "cancer_type", "source_system"]
expected_values = {
    "display_name": "ANON",
    "sex": "F",
    "age_range": "40-50",
    "cancer_type": "BRCA",
    "source_system": "EHR",
}
```

每次驗證需從 graph DB 重新讀取 Patient entity 的 properties，確保每次讀取都是最新狀態。

### P0-3: Relation Provenance

#### T3.1-T3.3 實現真正 Relation Query

**現狀**：`get_relation_properties()` 僅回傳 `None`（兩個分支都無效）。

**方案**：使用 KnowGraphGo CLI 的 `edge get <id>` 命令來查詢 relation 的完整屬性。

具體實現：
1. 透過 `clinical id relation FOR_PATIENT <rec_id> <patient_id>` 取得 relation graph_id
2. 使用 `edge get <relation_gid>` 取得完整 Relation 物件（含 Properties）
3. 從 Properties 中提取 8 個 Provenance 欄位並逐一 assert

或者，也可以使用 store 的 `GetEdge` API，但由於 Python E2E 測試是通過 CLI 調用的，無法直接使用 Go API。所以使用 CLI `--json edge get <id>`。

如果 `edge get` 命令在 `--json` 模式下回傳完整的 Relation（含 Properties），則可直接解析。

驗證八欄位：
```python
provenance_fields = {
    "event_id": ...,
    "event_type": ...,
    "aggregate_type": ...,
    "aggregate_id": ...,
    "correlation_id": ...,
    "causation_id": ...,
    "occurred_at": ...,
    "source_system": "AI-Kill-Cancer",
}
```

注意：需要確保 `edge get` 命令的 JSON 輸出包含 `properties` 欄位。如果當前實現不包含，可能需要修改 `output.go` 中的 `printRelation` 函數或 edge_cmd.go 中的輸出邏輯。

### P0-4: KnowGraphGo Checkout

#### T4.1-T4.4 修改 CI Checkout 邏輯

**當前 CI 有兩處 checkout KnowGraphGo**：
1. 第 56-65 行（KnowGraphGo Integration 步驟）
2. 第 193-202 行（CI-01 Checkout KnowGraphGo 步驟）

**兩處都需要修改**。

**修改為**：
```yaml
- name: Checkout KnowGraphGo (fixed SHA)
  env:
    GH_TOKEN: ${{ secrets.PAT }}
  run: |
    rm -rf KnowGraphGo
    git init KnowGraphGo
    cd KnowGraphGo
    git remote add origin https://x-access-token:${{ secrets.PAT }}@github.com/liuxb99/KnowGraphGo.git
    git fetch --depth=1 origin 6d2b20a68ba6ea25841e142918e186fb4beece0d
    git checkout 6d2b20a68ba6ea25841e142918e186fb4beece0d
```

**關鍵變更**：
- `git fetch origin main --depth=1` → `git fetch --depth=1 origin 6d2b20a68...`
- `git checkout FETCH_HEAD` → `git checkout 6d2b20a68...`
- 不得有 `git fetch origin main`
- 不得有 `checkout FETCH_HEAD`

---

## 5. 返工預案

### 常見失敗與對策

| 失敗場景 | 可能原因 | 返工方案 |
|---------|---------|---------|
| Migration 020/021 downgrade 因 data check 失敗 | Postgres 上的 COUNT query 使用 sync connection 失敗 | 改用 `op.get_bind().execute()` 確保使用當前 migration connection |
| Migration 022 PRAGMA 替代方案在 Postgres 上仍失敗 | information_schema 查詢需要 schema 名稱 | 加入 `table_schema = 'public'` 過濾條件 |
| P0-2 測試在 `get_entity_properties` 時找不到 Patient | recommendation stub 覆蓋了 Patient entity ID | 使用固定的 business key（patient_id）查詢，確保能正確找到 entity |
| P0-3 `edge get` 不輸出 properties | CLI 輸出格式缺少 properties | 修改 `edge_cmd.go` 中的 JSON 輸出，確保包含 `properties` 欄位 |
| P0-4 SHA checkout 失敗 | SHA 不在遠端默認分支 | 確保 SHA 已 push 到遠端，或者改用 `fetch origin <SHA>:refs/remotes/origin/target` |
| go test ./... 失敗 | Go 版本或依賴問題 | 確認 `go.sum` 與目標 SHA 一致，必要時 `go mod tidy` |
| pytest 在 Postgres 上失敗 | 非同步引擎問題 | 確保 `DATABASE_URL` 使用正確的 async driver（asyncpg） |

### 如果 CI 仍然失敗

1. **先看具體錯誤訊息**，不要直接加 continue-on-error
2. 如果 Migration 失敗，檢查 alembic 日誌中的具體 SQL
3. 如果測試失敗，檢查 pytest 輸出的 assert 失敗位置
4. 如果是 Go 測試失敗，檢查 `go test -v` 的詳細輸出
5. 只有當問題是環境問題（如 service 未就緒）而非代碼問題時，才考慮環境修復而非代碼修復

---

## 6. 驗收標準

### 每個任務的通過條件

| 任務 ID | 通過條件 |
|---------|---------|
| T1.1 | ci.yml 中三處 `continue-on-error: true` 全部移除；git diff 確認 |
| T1.2 | Migration 022 `_has_column()` 支援 Postgres（information_schema）；本地 Postgres 執行 `alembic upgrade head` PASS |
| T1.3 | Migration 020 downgrade 在 Postgres 上正常執行；無 async/sync 相關 RuntimeError |
| T1.4 | Migration 019 compound unique constraint 在 Postgres 上正常 |
| T1.5 | `alembic upgrade head` → `alembic downgrade 016` → `alembic upgrade head` 完整流程在 Postgres 上 PASS |
| T1.6 | 本地完整驗證三步驟 PASS |
| T1.7 | CI 中 Postgres Gate 腳本不再有臨時 INSERT/DELETE hack（或必要的最小化） |
| T2.1 | cross_repo_e2e_test.py 在每個 entity 建立後都驗證 Patient Properties |
| T2.2 | 驗證順序嚴格為：patient→verify→rec→verify→decision→verify→consensus→verify |
| T2.3 | 五欄位（display_name, sex, age_range, cancer_type, source_system）全部 assert |
| T2.4 | `pytest -v scripts/cross_repo_e2e_test.py` PASS（或等價測試命令） |
| T3.1 | 確定 CLI `edge get` 能回傳含 properties 的完整 Relation JSON |
| T3.2 | cross_repo_e2e_test.py 新增真正 Relation Query（使用 CLI 獲取完整的 Relation 物件） |
| T3.3 | 八欄位（event_id, event_type, aggregate_type, aggregate_id, correlation_id, causation_id, occurred_at, source_system）全部 assert |
| T3.4 | `go test ./adapter/... -v` + `pytest` PASS |
| T4.1 | CI 中 KnowGraphGo checkout 使用固定 SHA 6d2b20a68ba6ea25841e142918e186fb4beece0d |
| T4.2 | 使用 `git fetch --depth=1 origin <SHA>` 而非 `fetch origin main` |
| T4.3 | 無 `git fetch origin main` 和 `checkout FETCH_HEAD` 出現 |
| T4.4 | CI 中兩處 checkout 都更新完成 |
| T5.1 | `go test ./...` 全部 PASS（exit code 0） |
| T5.2 | `pytest` 全部 PASS（exit code 0） |
| T5.3 | GitHub Actions 觸發成功，無 workflow 解析錯誤 |
| T5.4 | GitHub Actions 全部步驟 PASS，無 continue-on-error 步驟 |
| T6.1 | 最終報告包含 10 項客觀證據 |

### 最終 10 項客觀證據

1. **KnowGraphGo Commit**: `git rev-parse HEAD` 輸出固定 SHA
2. **AI-Kill-Cancer Commit**: `git rev-parse HEAD` 輸出現有 commit
3. **GitHub Actions Run ID**: Actions run URL
4. **Backend 每一步 PASS**: CI 中 backend job 所有步驟的綠色勾選截圖/log
5. **Frontend PASS**: CI 中 frontend job PASS
6. **Postgres Gate PASS（不得 continue-on-error）**: 三步驟（Alembic upgrade, Run Tests, Downgrade/Re-upgrade）皆 PASS，無 continue-on-error 標記
7. **Stub Preservation 四次驗證結果**: E2E 測試輸出中四次 Patient Properties 驗證全部 ✓
8. **Relation Provenance 八欄位驗證結果**: E2E 測試輸出中八欄位 assert 全部 ✓
9. **固定 SHA Checkout 證據**: CI log 中顯示 checkout 的 commit SHA 為 6d2b20a68ba6ea25841e142918e186fb4beece0d
10. **REVIEWER 評分**: reviewer 最終評分（PASS/FAIL）

---

## 7. 注意事項

1. **所有修改必須同時更新 local 測試和 CI 配置**，確保本地可重現
2. **P0-2 的修改必須禁止「提前驗證」**：驗證必須在 entity 建立之後，不能提前到 entity 建立之前
3. **P0-3 的修改必須禁止「只驗 graph_id」**：必須讀出真正的 Relation Properties 並 assert 八個欄位
4. **P0-4 的修改必須禁止「checkout main」**：兩處 checkout 都必須使用固定 SHA
5. **最終回報必須有 10 項證據**，沒有客觀證據不要回報 PASS
6. **失敗時優先修復代碼問題**，而不是修改測試或 CI 配置來繞過
