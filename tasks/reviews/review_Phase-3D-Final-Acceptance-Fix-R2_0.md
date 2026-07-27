# 評分報告：Phase 3D Final Acceptance Fix Round 2

## 評分檢查清單

| 項目 | 結果 |
|------|------|
| 是否可執行 | **YES** — CI 語法正確，所有步驟使用有效命令，無不可解析的配置 |
| 是否有錯誤 | **YES（無錯誤）** — 程式碼邏輯正確，無語法或邏輯錯誤 |
| 是否滿足需求條列 | **YES** — 全部 4 個 P0 需求已滿足 |
| 是否有測試 | **YES** — E2E 測試強化、Go adapter 測試、CI 整合測試 |

## 細項評分

| 項目 | 評分 | 說明 |
|------|------|------|
| **完整性** | **25/25** | 所有 4 個 P0 需求完整實現，無缺漏 |
| **正確性** | **25/25** | 邏輯正確：Migration 相容性修復、Stub 驗證時機、Relation 查詢路徑、SHA 固定方式均正確 |
| **可維護性** | **22/25** | 程式碼整體清晰，CI 中 Postgres Test 步驟使用 `EXIT` 變數模式稍複雜但可理解；Migration 022 跨資料庫相容性實作良好 |
| **測試與驗證** | **25/25** | E2E 測試涵蓋四次 Stub 驗證 + 八欄位 Provenance 驗證 + 數位線程路徑驗證；Go adapter 測試完整；CI 整合測試涵蓋多資料庫 |

## 總分

**97/100 — 合格** ✅

---

## 逐項評語

### P0-1: Postgres Integration Gate ✅

**實現摘要：**
- `.github/workflows/ci.yml`：已移除所有 `continue-on-error: true`（grep 無匹配），Postgres Gate 三步驟（Alembic upgrade、Run Tests、Downgrade/Re-upgrade）均使用嚴格錯誤處理
- `migrations/env.py`：使用 `re.sub(r"\+asyncpg|\+aiosqlite|\+aiomysql|\+aioodbc|\+asyncmy", "", url)` 將 async driver URL 轉換為 sync variant，解決 async/sync 不匹配問題
- `migrations/versions/022_phase3d_graph_correctness_outbox.py`：`_has_column()` 函數支援 PostgreSQL（使用 `information_schema.columns`）和 SQLite（使用 `PRAGMA table_info`），跨資料庫相容

**評語：** 修復完整。需注意 CI 中 Postgres Test 步驟使用 `bash scripts/emit_annotations.sh 2>&1 || true` 僅為 annotation 輔助，不影響測試結果傳遞（透過 `EXIT` 變數最終 `exit $EXIT`）。Downgrade/Re-upgrade 步驟包含必要的資料插入/刪除以驗證 downgrade 阻擋邏輯，非 continue-on-error。

---

### P0-2: Stub Preservation ✅

**實現摘要：** `scripts/cross_repo_e2e_test.py` 實現了四次驗證：
1. `patient.created` → 立即 `verify_patient_properties`（line 301-305）
2. `recommendation.created` → 再次驗證（line 331-335）
3. `clinical_decision.created` → 再次驗證（line 359-363）
4. `tumor_board_consensus.created` → 再次驗證（line 392-396）

每次驗證五欄位：`display_name`、`sex`、`age_range`、`cancer_type`、`source_system`，從資料庫重新讀取確保最新狀態。

**評語：** 嚴格遵循需求：驗證在每個 entity 建立之後（非之前），四次驗證完整，五欄位全部 assert。無提前驗證、無只驗第一次。

---

### P0-3: Relation Provenance ✅

**實現摘要：** `scripts/cross_repo_e2e_test.py`（line 700-766）：
1. 透過 `clinical id relation FOR_PATIENT <rec_id> <patient_id>` 取得 relation graph_id
2. 使用 `edge get <relation_gid> --json` 獲取完整 Relation 資料（含 Properties）
3. 驗證 8 個 Provenance 欄位：
   - `event_id`（前綴 `evt-` 檢查）
   - `event_type`（`recommendation.created`）
   - `aggregate_type`（`recommendation`）
   - `aggregate_id`（`REC-001`）
   - `correlation_id`（`corr-P001`）
   - `causation_id`（`None`，起始事件無 causation）
   - `occurred_at`（`2026-07-27T00:00:00Z`）
   - `source_system`（`EHR`）

**評語：** 使用 KnowGraphGo CLI 的 `edge get`（於 `edge_cmd.go` 實作，`--json` 模式下 `json.Encode(relation)` 輸出完整 Relation 含 Properties）進行真正 Relation Query。八欄位全部 assert，不只驗證 graph_id。注意 `causation_id` 對於起始事件（recommendation.created）不存在，測試中驗證為 `None` 合理。

---

### P0-4: KnowGraphGo Checkout ✅

**實現摘要：** CI 中兩處 checkout（line 56-65 與 line 193-202）均使用固定 SHA：
```yaml
git init KnowGraphGo
git remote add origin https://x-access-token:${{ secrets.PAT }}@github.com/liuxb99/KnowGraphGo.git
git fetch --depth=1 origin 6d2b20a68ba6ea25841e142918e186fb4beece0d
git checkout 6d2b20a68ba6ea25841e142918e186fb4beece0d
```

**評語：** 無 `git fetch origin main`、無 `checkout FETCH_HEAD`、無 checkout main。兩處 checkout 均使用固定 SHA `6d2b20a68ba6ea25841e142918e186fb4beece0d`。

---

## 其他觀察

1. **Go 版本 1.25**：CI 中使用 `go-version: "1.25"`，但 Go 目前最新穩定版本為 1.22.x。若 GitHub Actions runner 尚未支援，可能導致失敗。建議確認或調整為實際可用的版本。

2. **Migration 022 downgrade SQLite**：使用重建表（rename→create→insert→drop backup）模式，已正確處理 FK 約束（`PRAGMA foreign_keys=OFF/ON`）。

3. **KnowGraphGo `edge get --json` 輸出**：`edgeGet` 函數使用 `json.Encode(relation)` 輸出，包含完整的 `graph.Relation` 結構體（含 `Properties`、`Provenance`、`Evidence` 等），確保 Python E2E 測試可正確解析。

4. **E2E 測試覆蓋**：除 Stub Preservation 與 Relation Provenance 外，還包含數位線程路徑驗證（FOR_PATIENT、BASED_ON、DERIVED_FROM、RECOMMENDS、SUPPORTED_BY、HAS_OPINION、PROVIDED_BY_SPECIALTY）及 Drug/Evidence/Opinion/Specialty 實體存在驗證。

---

## 最終結論

**總分：97/100 — 合格** 🟢

所有 4 個 P0 需求均已完整實現，程式碼邏輯正確，測試覆蓋全面。建議在實際 CI 運行前確認 Go 1.25 版本的可用性。
