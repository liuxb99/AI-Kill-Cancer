# Phase 3C Hardening 執行計劃

> **場景**: hardening（架構強化）
> **目標**: Migration PASS + Restart PASS + Frontend PASS + CI PASS + Reviewer >= 95
> **Commit**: `fix(phase3c): harden migration restart and ci`
> **返工上限**: 5 次

---

## 1. 任務依賴圖

```
                    ┌──────────────────────┐
                    │  H-07  AGENTS.md      │ (無依賴)
                    │  Restore             │
                    └──────────────────────┘

┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  H-01  P0-1     │  │  H-03  P0-2     │  │  H-05  P0-3     │
│  Migration 020  │  │  Restart         │  │  Frontend       │
│  Downgrade      │  │  Recovery 強化   │  │  Tests 修復     │
│  (backend-logic)│  │  (backend-logic) │  │  (test-writer)  │
└────────┬────────┘  └────────┬────────┘  └────────┬────────┘
         │                    │                     │
         ▼                    ▼                     │
┌─────────────────┐  ┌─────────────────┐           │
│  H-02  P0-1     │  │  H-04  P0-2     │           │
│  Migration      │  │  Restart        │           │
│  Tests          │  │  Recovery Tests │           │
│  (test-writer)  │  │  (test-writer)  │           │
└────────┬────────┘  └────────┬────────┘           │
         │                    │                     │
         └──────┬─────────────┘                     │
                │                                   │
                ▼                                   ▼
         ┌──────────────────────────────────────────────┐
         │           H-08  P1-1 Consensus Status        │
         │           Default (backend-logic)            │
         │           無依賴，可並行執行                  │
         └──────────────────────┬───────────────────────┘
                                │
                                ▼
         ┌──────────────────────────────────────────────┐
         │    H-06  P0-4 Postgres CI (devops)           │
         │    依賴 H-01~H-05、H-08 全部完成              │
         └──────────────────────┬───────────────────────┘
                                │
                                ▼
         ┌──────────────────────────────────────────────┐
         │    H-09 全面驗證 (test-writer)                 │
         │    依賴 H-01~H-08 全部完成                     │
         └──────────────────────┬───────────────────────┘
                                │
                                ▼
         ┌──────────────────────────────────────────────┐
         │    Step 5  REVIEWER 評分                      │
         └──────────────────────────────────────────────┘
```

---

## 2. Batch 分組

| Batch | 任務 ID | 內容 | 負責角色 | 依賴 | 預估工時 |
|-------|---------|------|----------|------|----------|
| **A** | H-01 | P0-1 Migration 020 Downgrade 修正 | backend-logic | 無 | 30 min |
| **B** | H-02 | P0-1 Migration Tests 補強 | test-writer | H-01 | 20 min |
| **C** | H-03 | P0-2 Restart Recovery 強化 | backend-logic | 無 | 30 min |
| **D** | H-04 | P0-2 Restart Recovery Tests | test-writer | H-03 | 20 min |
| **E** | H-05 | P0-3 Frontend Tests 修復 | test-writer | 無 | 20 min |
| **F** | H-07 | P0-5 AGENTS.md Restore | doc-writer | 無 | 10 min |
| **G** | H-08 | P1-1 Consensus Status Default | backend-logic | 無 | 15 min |
| **H** | H-06 | P0-4 Postgres CI 配置與驗證 | devops | A~G | 30 min |
| **I** | H-09 | 全面驗證（後端+前端） | test-writer | H-01~H-08 | 30 min |

> **注意**: Batch A/B（Migration）、C/D（Restart Recovery）、E（Frontend）、F（AGENTS.md）、G（Consensus Default）五條路徑彼此無依賴，可**完全並行**執行。

---

## 3. 每個 Batch 的負責角色與交付物

### Batch A — P0-1 Migration 020 Downgrade（backend-logic）

**負責角色**: backend-logic

**目標**: 將 `migrations/versions/020_phase3c_tumor_board_consensus.py` 的 `downgrade()` 從「永遠 raise IrreversibleMigrationError」改為「有資料才阻擋，空資料表允許 drop」

**詳細步驟**:
1. 開啟 `migrations/versions/020_phase3c_tumor_board_consensus.py`
2. 修改 `downgrade()` 函數：
   - 移除 `raise IrreversibleMigrationError(...)` 固定寫法
   - 加入三表（`domain_tumor_board_consensus`、`domain_tumor_board_opinions`、`domain_tumor_board_consensus_traces`）的 `COUNT(*)` 檢查
   - 任何一表 `>0` → `raise IrreversibleMigrationError("Cannot downgrade...")`
   - 全部空 → `op.drop_table(...)` 依序刪除三表
3. 保留 `IrreversibleMigrationError` 類別定義（已在檔案中）
4. **不可修改**: upgrade()、upgrade 中的任何欄位定義（consensus_status default 在 P1-1 處理）

**交付檢查**:
- [ ] downgrade() 在空表時正常 drop 三表
- [ ] downgrade() 在有資料時 raise "Cannot downgrade..."
- [ ] upgrade() 完全未修改

---

### Batch B — P0-1 Migration Tests（test-writer）

**負責角色**: test-writer

**目標**: 在 `tests/test_migration.py` 的 `TestMigration020` 類別中補足三個測試情境

**詳細步驟**:
1. 開啟 `tests/test_migration.py`，定位 `TestMigration020` 類別
2. **確認以下測試已存在**（如已存在則跳過）：
   - `test_downgrade_020_empty_db_ok`：
     - upgrade → 確認三表存在 → downgrade → 確認三表已刪除
   - `test_downgrade_020_to_019_raises_irreversible`：
     - upgrade → insert 一筆資料 → downgrade → 檢查 raise
   - `test_downgrade_020_to_019_error_message`：
     - upgrade → insert 一筆資料 → downgrade → 檢查 error message 包含 "Cannot downgrade"
3. 如缺少任一測試，補上
4. 執行 `python -m pytest tests/test_migration.py -v -k "020"` 確認 14 個 020 測試全部 PASS

**交付檢查**:
- [ ] 14 個 020 Migration 測試全部 PASS
- [ ] Empty DB downgrade 測試存在且正確
- [ ] Data Exists blocked 測試存在且正確
- [ ] Error message 驗證測試存在且正確

---

### Batch C — P0-2 Restart Recovery 強化（backend-logic）

**負責角色**: backend-logic

**目標**: 確保 Tumor Board Consensus Restart Recovery 測試真正走完整鏈路：App1 → POST Consensus → Shutdown → App2 → GET Consensus → GET Opinions → GET Trace

**詳細步驟**:
1. 開啟 `tests/test_tumor_board_restart_recovery.py`
2. 確認 `_create_prerequisite_data()` 方法存在，且使用 SQLAlchemy ORM（非 SQLite create_all）寫入 patient/recommendation/clinical_decision
3. 確認 `test_end_to_end_restart_recovery()`：
   - Phase 1: App1 建立 consensus → GET 確認
   - App1 context 關閉（模擬 restart）
   - Phase 3: App2 建立 → GET consensus → 驗證 data integrity
   - App2 GET opinions → 確認至少 1 筆
   - App2 GET trace → 確認至少 1 筆
4. 執行 `python -m pytest tests/test_tumor_board_restart_recovery.py -v --tb=short` 確認 PASS
5. 同時確認原始 `tests/test_restart_recovery.py` 仍然 PASS（避免 Regression）

**交付檢查**:
- [ ] test_tumor_board_restart_recovery.py 全部 PASS
- [ ] 測試使用完整的 API → Service → Repository → Database 路徑（非 SQLite create_all 冒充）
- [ ] App2 驗證了 Consensus、Opinions、Trace 三個 endpoint

---

### Batch D — P0-2 Restart Recovery Tests（test-writer）

**負責角色**: test-writer

**目標**: 補強 Restart Recovery 相關測試，確認所有邊界情境

**詳細步驟**:
1. 執行 `python -m pytest tests/test_restart_recovery.py -v --tb=short` 確認原始 Restart Recovery 測試 PASS
2. 執行 `python -m pytest tests/test_tumor_board_restart_recovery.py -v --tb=short` 確認 Tumor Board 版本 PASS
3. 如有邊界情境（404、Nonexistent ID）測試不足，補上
4. 確認所有測試不依賴 SQLite create_all 或直接 session 模擬

**交付檢查**:
- [ ] 所有 Restart Recovery 測試 PASS
- [ ] 至少覆蓋正常鏈路與 404 情境

---

### Batch E — P0-3 Frontend Tests 修復（test-writer）

**負責角色**: test-writer

**目標**: Frontend Tests 從 168/172 修復到 172/172

**詳細步驟**:
1. 進入 `src/frontend` 目錄
2. 執行 `npm test` 確認當前狀態
3. 如仍有 FAIL，逐個分析失敗原因：
   - `getByText` 匹配到多個元素 → 改 `getAllByText`
   - 元件行為改變導致測試斷言不匹配 → 修正測試斷言匹配新行為
   - 非同步時序問題 → 增加 `waitFor` / `findBy`
4. **禁止**: skip、xfail、刪除測試
5. 全部修復後執行 `npm test` 確認 172/172 PASS

**交付檢查**:
- [ ] `npm test` 172/172 PASS
- [ ] 無任何 skip / xfail 測試
- [ ] 無測試被刪除

---

### Batch F — P0-5 AGENTS.md Restore（doc-writer）

**負責角色**: doc-writer

**目標**: 回復 AGENTS.md 到 Phase 3C 前的狀態（commit `5b2c658` 版本），僅保留與 Phase 3C Hardening 相關的必要流程

**詳細步驟**:
1. 用 `git show 5b2c658:AGENTS.md` 取得原始版本
2. 對照當前版本，回復以下差異：
   - Step 0A：從簡化版恢復為完整版
   - Step 0B：確認標題一致
   - 移除任何 Phase 3C 特有的流程修改
3. 寫入 AGENTS.md
4. 驗證 AGENTS.md 內容與 `5b2c658` 版本一致（除必要的時間戳差異外）

**交付檢查**:
- [ ] AGENTS.md 已回復到 pre-Phase-3C 狀態
- [ ] 無 Phase 3C 專用的流程修改殘留
- [ ] 繁體中文用語保持一致

---

### Batch G — P1-1 Consensus Status Default（backend-logic）

**負責角色**: backend-logic

**目標**: 將 consensus_status 的預設值從 `unanimous` 改為 `pending`

**詳細步驟**:
1. 確認 `migrations/versions/020_phase3c_tumor_board_consensus.py` 中 `upgrade()` 的 `server_default` 已改為 `"pending"`（第 42 行）
2. 確認 `src/backend/domain/tumor_board.py` 中 `TumorBoardConsensusModel.consensus_status` 的 `default` 已改為 `"pending"` 
3. 確認 `src/backend/domain/enums.py` 中 `ConsensusStatus` 已加入 `PENDING = "pending"`
4. 如有遺漏，修正

**交付檢查**:
- [ ] Migration 020 upgrade 中 `server_default="pending"`
- [ ] TumorBoardConsensusModel 中 `default="pending"`
- [ ] ConsensusStatus Enum 包含 PENDING
- [ ] 無其他檔案需要修改

---

### Batch H — P0-4 Postgres CI（devops）

**負責角色**: devops

**目標**: 在 GitHub Actions 上真正執行 Postgres CI，涵蓋 Migration 020、Engine、Service、API、Digital Thread、Restart Recovery

**詳細步驟**:
1. 確認 `.github/workflows/ci.yml` 已包含：
   - Postgres service container（16-alpine）
   - `Postgres Integration Gate - Alembic upgrade on Postgres`
   - `Postgres Integration Gate - Run Tests on Postgres`（含 tumor board tests）
   - `Postgres Integration Gate - Alembic downgrade & re-upgrade`（含資料驗證、空表 downgrade）
   - `Postgres Integration Gate - Migration verification`
2. 如有遺漏，補上 CI step
3. **Push 到 GitHub** 觸發 CI
4. 監控 CI 執行結果，擷取：
   - Run ID
   - 所有 Job 的 Success/Failure 狀態
5. 如有 Job 失敗，修正後重新 push

**CI 涵蓋範圍（必須全部 PASS）**:
- `tests/test_tumor_board_engine.py`
- `tests/test_tumor_board_models.py`
- `tests/test_tumor_board_repo.py`
- `tests/test_tumor_board_service.py`
- `tests/test_api_tumor_board.py`
- `tests/test_tumor_board_digital_thread.py`
- `tests/test_tumor_board_restart_recovery.py`
- `tests/test_migration.py`（含 020 測試）
- `tests/test_restart_recovery.py`
- `tests/test_recommendation_transaction.py`
- `tests/test_api_recommendation.py`
- `tests/test_recommendation_service.py`
- `tests/test_trace_persistence.py`
- `tests/test_acceptance_real_trace.py`
- Alembic downgrade → 016 → re-upgrade head 完整循環

**交付檢查**:
- [ ] GitHub Actions 觸發成功
- [ ] 所有 Job Success
- [ ] Run ID 記錄到 summary-report
- [ ] 無 CI 跳過或遺漏測試

---

### Batch I — 全面驗證（test-writer）

**負責角色**: test-writer

**目標**: 確認所有測試全部 PASS，無 Regression

**詳細步驟**:
1. 執行 `python -m pytest tests/test_migration.py -v -k "020"` → 14 PASS
2. 執行 `python -m pytest tests/test_tumor_board_restart_recovery.py -v` → PASS
3. 執行 `python -m pytest tests/test_restart_recovery.py -v` → PASS
4. 執行 `cd src/frontend && npm test` → 172/172 PASS
5. 執行完整的 backend test suite：`python -m pytest tests/unit/ tests/integration/ -v --tb=short`（如時間允許）
6. 產出驗證報告

**交付檢查**:
- [ ] Migration 020 全部 PASS
- [ ] Restart Recovery 全部 PASS
- [ ] Frontend 172/172 PASS
- [ ] 無 Regression

---

## 4. 各 Batch 執行順序

```
時間線
│
├── [Batch A]  H-01 Migration 020 Downgrade  (backend-logic)
│         └── [Batch B]  H-02 Migration Tests       (test-writer)
│
├── [Batch C]  H-03 Restart Recovery 強化     (backend-logic)
│         └── [Batch D]  H-04 Restart Recovery Tests (test-writer)
│
├── [Batch E]  H-05 Frontend Tests 修復       (test-writer)
│
├── [Batch F]  H-07 AGENTS.md Restore         (doc-writer)
│
├── [Batch G]  H-08 Consensus Status Default  (backend-logic)
│
├── [Batch H]  H-06 Postgres CI               (devops) ← 需要 push
│
├── [Batch I]  H-09 全面驗證                   (test-writer)
│
└── Step 5    REVIEWER 評分
```

> **最佳化建議**: Batch A/B/C/D/E/F/G 彼此無依賴，可用 fleet 或並行 task() 同時啟動，節省 ~60% 總時間。

---

## 5. 返工預案

### 5.1 如果 CI 無法執行（GitHub Actions 無法觸發）

若 Reviewer 發現 CI 無法在 GitHub Actions 上真正執行（例如 Push 權限不足、GitHub Actions 未啟用等），則：

1. **評分約束**: Reviewer 必須遵守「沒有 GitHub Actions 則 Reviewer 不得 >89」
2. **判斷標準**:
   - CI 完全不存在 → 最高 89 分，評為不合格
   - CI 存在但部分 Job 失敗 → 依實際失敗數量扣分
   - CI 存在且全部 PASS → 可達 95+
3. **Reviewer 評分指引**:
   - 如果 Push 權限不足無法觸發 CI，但 `.github/workflows/ci.yml` 配置完整正確，視為「可執行=YES」
   - 但因為缺少實際執行結果，測試與驗證項最高 15 分（滿分 25）
   - 總分最高 = 完整性 25 + 正確性 25 + 可維護性 20 + 測試 15 = 85 → 不合格
4. **補救方案**:
   - 請求有 Push 權限的成員觸發 CI
   - 或者提供本地執行 `pytest` 的完整 log 作為替代證據
   - 使用 `act` 工具（GitHub Actions 本地模擬器）執行 CI 並產出 log

### 5.2 如果 CI 部分 Job 失敗

1. 讀取 GitHub Actions 失敗 Job 的 log
2. 判斷失敗原因：
   - 測試程式碼錯誤 → log 修正回 Batch A~E
   - CI 配置錯誤 → 修正 ci.yml 重新 push
   - 環境問題（Postgres connection, dependency）→ 修正 ci.yml 或 requirements
3. 修正後重新 push，確認所有 Job 綠燈

### 5.3 如果 Frontend Tests 仍有失敗（未達 172/172）

1. 逐個分析失敗測試的錯誤訊息
2. 常見原因：
   - `getByText` 匹配到多個元素 → 改為 `getAllByText`
   - 元件渲染行為改變 → 調整斷言
   - 非同步競態條件 → 增加 `waitFor`
3. **禁止**: skip、xfail、刪除測試
4. 修復後重新執行直到 172/172

### 5.4 如果 Reviewer 總分 < 90

啟動完整返工循環（上限 5 次）：

```
do {
  1. PLANNER(resume) → 讀取評分報告，重新規劃
  2. 開發子代理(resume) → 按新計劃執行
  3. REVIEWER → 重新評分
  4. 循環次數 + 1
} while (總分 < 90 && 循環次數 < 5)
```

若 5 次後仍 < 90 → 啟動 DeepSeek MCP 顧問介入（最多再修 2 輪）→ 仍 < 90 則標記需真人決策。

---

## 6. 當前狀態快照（參考用）

下列任務在計劃制定時已確認在 commit `01f431a` 中完成或部分完成，執行時請驗證後跳過：

| 任務 | 狀態 | 備註 |
|------|------|------|
| H-01 Migration 020 Downgrade | **已完成** | downgrade() 已改為有資料阻擋、空表 drop；測試 14/14 PASS |
| H-02 Migration Tests | **已完成** | Empty DB + Data Exists + Error Message 三情境皆覆蓋 |
| H-03 Restart Recovery 強化 | **已完成** | 已改用 `_create_prerequisite_data` 直接寫 DB（bypass Engine） |
| H-04 Restart Recovery Tests | **已完成** | 1 test PASS，覆蓋 Consensus/Opinions/Trace 三鏈路 |
| H-05 Frontend Tests 修復 | **已完成** | 172/172 PASS |
| H-07 AGENTS.md Restore | **待執行** | 當前版本為簡化版，需回復到 pre-Phase-3C 版本 |
| H-08 Consensus Status Default | **已完成** | migration server_default + model default + Enum 皆已改為 "pending" |
| H-06 Postgres CI | **待執行** | ci.yml 已更新但需 push 到 GitHub 觸發執行 |
| H-09 全面驗證 | **待執行** | 需驗證所有測試無 Regression |

---

## 7. 完成條件檢查清單

- [ ] Migration 020 downgrade PASS（空表可降、有資料阻擋）
- [ ] Migration Tests 全部 PASS（14/14）
- [ ] Restart Recovery 完整鏈路 PASS（POST → Shutdown → GET Consensus → GET Opinions → GET Trace）
- [ ] Frontend Tests 172/172 PASS
- [ ] Postgres CI 在 GitHub Actions 上全部 Job Success
- [ ] AGENTS.md 已回復到 pre-Phase-3C 狀態
- [ ] Consensus Status default = "pending"
- [ ] Reviewer >= 95
- [ ] 一個 commit `fix(phase3c): harden migration restart and ci`
- [ ] Git Push 成功
- [ ] Phase 3C Accepted: YES
- [ ] Ready for Phase 3D: YES
