# Phase 3D Final Acceptance — 最終修復計劃

> 基於 `tasks/requirements.md`（Phase 3D Final Acceptance 需求）  
> 最新評分報告：`tasks/reviews/review_Phase-3D-Graph-Correctness-Hardening_5.md`（80/100，FAIL）  
> 先前計劃：`tasks/plan-phase3d-hardening.md`、`tasks/plan-phase3d-hardening-rework-1.md`  
> 本輪目標：修正所有剩餘 P0/P1 問題，使 Reviewer 評分 ≥ 95

---

## 當前狀態摘要

| 需求項 | 優先級 | 當前狀態 | 評分報告狀態 |
|--------|--------|---------|-------------|
| P0-1 Cross-language ID Parity | P0 | ⚠️ PARTIAL — 僅 Python 端驗證，無 Go→Python 交叉比對 | #11 PARTIAL |
| P0-2 Cross Repository Digital Thread | P0 | ⚠️ PARTIAL — 僅 schema 層級 + adapter 單元測試，無完整 E2E | #20 PARTIAL |
| P0-3 Store Level Idempotent Replay | P0 | ✅ PASS — Go 端 idempotent 測試通過 | #3 PASS |
| P1-1 Stub Entity | P1 | ❓ 待確認 — 未在評分報告中明確標記但需驗證 | 未明確檢查 |
| P1-2 Relation Provenance | P1 | ⚠️ PARTIAL — Entity 有完整 provenance，Relation 僅 ProvenanceImported | #12 PARTIAL |
| P1-3 Panic | P1 | ⚠️ PARTIAL — 3 項 Python 測試因測試代碼未同步更新而失敗 | 3 FAILED |
| CI 強化 | CI | ⚠️ 需補齊 | 部分存在 |

**總分：80/100，判定期：FAIL ❌**

---

## 一、任務清單

### P0 必須完成

---

#### P0-1 Cross-language ID Parity（真正跨語言）

**問題描述**：
CI 目前僅驗證 Python 端的 ID 確定性和有效性，無直接 Go→Python 交叉比對。  
無法直接證明 `Python ID == Go ID`。

**任務分解**：

| ID | 任務 | 依賴 | 負責角色 | 估算 |
|----|------|------|---------|------|
| P0-1a | **KnowGraphGo 建立 golden test 輸出 `golden_output.json`**：Go 端 `id_factory_test.go` 新增一個測試案例，對所有 10 種 Entity Kind（patient, recommendation, decision, consensus, opinion, specialty, drug, evidence, variant, relation）用預定義輸入計算 UUID，輸出 JSON 檔案 | 無 | **knowgraphgo-dev** | 1h |
| P0-1b | **Python 測試讀取 golden_output.json 逐項 assert**：`tests/test_phase3d_id_parity.py` 中新增 `test_id_parity_with_go_golden()`，從 KnowGraphGo 的 golden_output.json 讀取每筆 case，對應調用 `ClinicalGraphIDFactory` 的方法，assert 結果完全一致 | P0-1a | **test-writer** | 0.5h |
| P0-1c | **CI 整合跨語言 ID Parity 驗證**：在 `.github/workflows/ci.yml` 中，確認 Checkout KnowGraphGo → Build CLI → Run Go golden test（輸出 golden_output.json）→ Python 測試讀取比對的完整流程 | P0-1a, P0-1b | **devops** | 0.5h |

**驗收標準**：
- Golden test 覆蓋所有 10 種 Entity Kind + Relation
- 每個 case 的 Python 計算結果與 Go 計算結果完全一致
- CI 中自動化執行，FAIL 則阻斷 pipeline

---

#### P0-2 Cross Repository Digital Thread

**問題描述**：
CI 中僅運行 adapter 單元測試 + Python ID 校驗，缺少需求 §十七要求的完整端到端流程：
Build CLI → 建立 Temporary SQLite Graph DB → 產生 Event 序列 → CLI apply → 再次 apply → CLI query → 驗證冪等 + Digital Thread 路徑。

**任務分解**：

| ID | 任務 | 依賴 | 負責角色 | 估算 |
|----|------|------|---------|------|
| P0-2a | **建立端到端 E2E Digital Thread CI 腳本**：在 `scripts/cross_repo_e2e_test.sh`（或 `.py`）中實現完整流程：① Build KnowGraphGo CLI；② 建立臨時 SQLite Graph DB；③ 模擬事件序列：patient.created → recommendation.created → clinical_decision.created → tumor_board_consensus.created；④ CLI apply 每個事件；⑤ CLI query 驗證 Patient→Recommendation→Decision→Consensus 完整路徑；⑥ 驗證 Node Count、Relation Count、Thread Properties 正確 | P0-1a（需 Go CLI） | **test-writer** | 2h |
| P0-2b | **E2E 腳本加入 Idempotent Replay 驗證**：重新 apply 相同事件序列，驗證 Entity Count 不增加、Relation Count 不增加、Update Count 正常、No Duplicate | P0-2a | **test-writer** | 1h |
| P0-2c | **CI 整合 E2E Digital Thread 測試**：在 `.github/workflows/ci.yml` 中以獨立步驟運行 `scripts/cross_repo_e2e_test.sh`，使用 KnowGraphGo 的 fixed SHA binary | P0-2a, P0-2b | **devops** | 0.5h |

**驗收標準**：
- E2E 腳本可在 CI 環境中完整運行
- Digital Thread 路徑完整（Patient→Recommendation→Decision→Consensus）
- Node Count、Relation Count 正確
- Idempotent Replay 驗證 No Duplicate
- 不能只跑 unit test，必須真正 CLI apply → CLI query

---

#### P0-3 Store Level Idempotent Replay

**問題描述**：
Go 端的 idempotent 測試已通過（`TestDuplicateReplay_Idempotent` PASS），但需確認 Store 層級（通過 CLI）的 replay 也通過。P0-2b 中的 E2E Idempotent Replay 驗證已涵蓋此需求。

**任務分解**：

| ID | 任務 | 依賴 | 負責角色 | 估算 |
|----|------|------|---------|------|
| P0-3a | **確認 Go 端 Store Level Idempotent Replay 測試完整**：檢查 `adapter/clinical/adapter_test.go` 中的 `TestDuplicateReplay_Idempotent` 和 `TestUpdatedEvent_Upsert` 覆蓋了第一次創建 + 第二次 Entity Count 不增加的需求 | 無 | **knowgraphgo-dev** | 0.3h |
| P0-3b | **E2E Idempotent Replay 驗證**（與 P0-2b 合併）：在 E2E 腳本中確認 apply 兩次後 Entity/Relation Count 不增加 | P0-2a | **test-writer** | 已含在 P0-2b |

**驗收標準**：
- Go 測試 Entity 和 Relation 的 idempotent replay 全部 PASS
- E2E 測試中 apply 兩次後 Count 不變

---

### P1 必須完成

---

#### P1-1 Stub Entity

**問題描述**：
需要驗證：patient.created 有完整資料（name, sex, age, cancer_type）；recommendation.created 建立 stub；Stub 不能覆蓋完整 Entity，Properties 不得遺失。

目前未在評分報告中明確標記為 FAIL，但需求明確要求。

**任務分解**：

| ID | 任務 | 依賴 | 負責角色 | 估算 |
|----|------|------|---------|------|
| P1-1a | **確認 Patient Entity 建立時有完整 Properties**：檢查 Go 端 `adapter.go` 中 `MapPatientEvent` 是否包含 name/sex/age/cancer_type 等完整欄位 | 無 | **knowgraphgo-dev** | 0.3h |
| P1-1b | **確認 Recommendation created 建立 Stub 且不覆蓋 Patient**：檢查 Go 端 adapter 是否在 recommendation.created 事件中對 Patient Entity 進行 Upsert 時，若 Patient 已存在則不覆蓋現有 Properties | 無 | **knowgraphgo-dev** | 0.3h |
| P1-1c | **新增 Stub Entity 測試**：在 `adapter/clinical/adapter_test.go` 或 Python 端測試驗證：先建立 Patient（完整資料）→ 再 apply recommendation.created → Patient Properties 未被覆蓋 | P1-1a, P1-1b | **test-writer** | 1h |

**驗收標準**：
- Patient Entity 建立時包含 name/sex/age/cancer_type
- Recommendation created 不覆蓋 Patient Properties
- 測試自動化驗證

---

#### P1-2 Relation Provenance

**問題描述**：
需求 §七要求「每一條 Relation 必須保留：event_id, event_type, aggregate_type, aggregate_id, correlation_id, causation_id, occurred_at, source_system」。  
但目前 Relation 僅設置 `ProvenanceImported` 枚舉值，未在 Relation.Properties 中保存詳細來源信息。

**任務分解**：

| ID | 任務 | 依賴 | 負責角色 | 估算 |
|----|------|------|---------|------|
| P1-2a | **在 Go Adapter 中為 Relation 添加完整 Provenance Properties**：修改 `adapter/clinical/adapter.go`，在建立每個 Relation 時，將 `event_id, event_type, aggregate_type, aggregate_id, correlation_id, causation_id, occurred_at, source_system` 寫入 `relation.Properties` map | 無 | **knowgraphgo-dev** | 1.5h |
| P1-2b | **更新 Relation Provenance 測試**：修改 `adapter/clinical/adapter_test.go` 中的 `TestProvenanceFields`，驗證每個 Relation 的 Properties 包含全部 8 個 provenance 欄位 | P1-2a | **knowgraphgo-dev** / **test-writer** | 0.5h |
| P1-2c | **確認 Python 端不對 Relation Provenance 造成破壞**：檢查 worker/client 是否在傳遞事件時遺失 provenance 信息 | P1-2a | **backend-logic** | 0.3h |

**驗收標準**：
- 每個 Relation 的 Properties 包含 event_id, event_type, aggregate_type, aggregate_id, correlation_id, causation_id, occurred_at, source_system
- Provenance 測試 PASS
- 可追蹤來源，不僅是 `Imported` 枚舉值

---

#### P1-3 Panic 處理

**問題描述**：
3 項 Python 測試因測試代碼未同步更新到最新的 status 模型和必填字段而失敗。  
評分報告建議 P0 優先級修復。

**任務分解**：

| ID | 任務 | 依賴 | 負責角色 | 估算 |
|----|------|------|---------|------|
| P1-3a | **修復 `test_mark_failed` 測試**：`tests/unit/test_phase3d_outbox_repo.py` 第 155 行，修正斷言邏輯為正確的 `assert evt.status == "failed"`（當前寫法 `assert evt.status == "failed" or evt.status == "dead_letter"` 因 Python 運算符優先級問題行為不正確） | 無 | **test-writer** | 0.2h |
| P1-3b | **修復 `test_worker_with_mock_client` 測試**：`tests/unit/test_phase3d_worker.py` 第 50-57 行 `repo.create()` 調用中添加 `occurred_at` 參數 | 無 | **test-writer** | 0.2h |
| P1-3c | **修復 `test_worker_retry_on_failure` 測試**：`tests/unit/test_phase3d_worker.py` 第 83-91 行 `repo.create()` 調用中添加 `occurred_at` 參數 | 無 | **test-writer** | 0.2h |
| P1-3d | **確認 Go 端 panic → return error**：檢查 KnowGraphGo adapter 中是否還有 `panic()` 調用，確保全部改為 `return error` | 無 | **knowgraphgo-dev** | 0.3h |

**驗收標準**：
- 全部 Python 測試 PASS（`pytest tests/unit/test_phase3d_*.py`）
- Go 端無 `panic()` 殘留
- Worker 在 Validation Error 時正常 mark_failed → retry → dead_letter
- CLI 不 crash

---

### CI 強化

**問題描述**：
需求要求 Cross-language parity、Cross repository E2E、Replay、Stub overwrite、Relation provenance 全部加入 GitHub Actions，不得只存在 local。

**任務分解**：

| ID | 任務 | 依賴 | 負責角色 | 估算 |
|----|------|------|---------|------|
| CI-01 | **Cross-language ID Parity CI**：在 `.github/workflows/ci.yml` 中新增步驟：Build Go CLI → Run Go golden test → Run Python ID parity test（讀取 golden_output.json） | P0-1a, P0-1b, P0-1c | **devops** | 0.5h |
| CI-02 | **Cross repository E2E CI**：在 `.github/workflows/ci.yml` 中新增步驟：運行 `scripts/cross_repo_e2e_test.sh` | P0-2a, P0-2b, P0-2c | **devops** | 0.5h |
| CI-03 | **Replay CI**：確認 CI 中已包含 Idempotent Replay 測試（Go + E2E），CI 步驟需明確標註 | P0-3a, P0-3b | **devops** | 0.3h |
| CI-04 | **Stub overwrite CI**：在 `.github/workflows/ci.yml` 中新增步驟：運行 Stub Entity 測試 | P1-1c | **devops** | 0.3h |
| CI-05 | **Relation provenance CI**：在 `.github/workflows/ci.yml` 中新增步驟：運行 Provenance 測試 | P1-2b | **devops** | 0.3h |

**驗收標準**：
- 全部新測試在 CI 中自動化執行
- GitHub Actions 完整運行通過

---

### Meta（收尾）

| ID | 任務 | 依賴 | 負責角色 | 估算 |
|----|------|------|---------|------|
| META-01 | **執行全部測試驗證**：`pytest tests/` + `go test ./...` 全部 PASS | 所有開發任務完成 | **test-writer** | 0.5h |
| META-02 | **REVIEWER 評分**：觸發 Reviewer 子代理評分，目標 ≥ 95 | META-01 | **reviewer** | 1h |
| META-03 | **總結報告 + Git Commit & Push**：提供 git status, git diff --stat, git log -1, 全部新增測試, CI Run, GitHub Actions URL | META-02 | **doc-writer** | 0.5h |

---

## 二、依賴關係圖

```
                    ┌──────────────────────────────────────────────┐
                    │              Phase KG (KnowGraphGo)           │
                    │                                              │
                    │  P0-1a: Golden Test + golden_output.json     │
                    │       ↓                                     │
                    │  P1-1a: Patient Properties 確認 (無依賴)     │
                    │  P1-1b: Stub 確認 (無依賴)                   │
                    │  P1-2a: Relation Provenance (無依賴)         │
                    │  P1-3d: Panic 確認 (無依賴)                  │
                    │       ↓                                     │
                    │  P1-1c: Stub 測試 (依賴 P1-1a/b)            │
                    │  P1-2b: Provenance 測試 (依賴 P1-2a)        │
                    │       ↓                                     │
                    │  Push KnowGraphGo → 取得新 SHA               │
                    └──────────────────────┬───────────────────────┘
                                           │ SHA pin
                                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│              Phase AKC (AI-Kill-Cancer)                              │
│                                                                      │
│  P0-1b: Python Golden Test 比對 (依賴 P0-1a)                        │
│  P0-2a: E2E Digital Thread 腳本 (依賴 P0-1a)                       │
│  P0-2b: E2E Idempotent Replay (依賴 P0-2a)                         │
│                                                                      │
│  P1-3a: test_mark_failed 修復 (無依賴)                              │
│  P1-3b: test_worker_with_mock_client 修復 (無依賴)                  │
│  P1-3c: test_worker_retry_on_failure 修復 (無依賴)                  │
│  P1-2c: Relation Provenance 確認 (依賴 P1-2a)                      │
│                                                                      │
│  P0-3a: Store Level Replay 確認 (無依賴)                            │
│                                                                      │
└──────────────────────┬───────────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────────┐
│              Phase CI (CI 強化)                                      │
│                                                                      │
│  CI-01: Cross-language Parity CI (依賴 P0-1b, P0-1a)                │
│  CI-02: Cross-repo E2E CI (依賴 P0-2c)                             │
│  CI-03: Replay CI (依賴 P0-3a, P0-2b)                              │
│  CI-04: Stub CI (依賴 P1-1c)                                        │
│  CI-05: Provenance CI (依賴 P1-2b)                                  │
│                                                                      │
└──────────────────────┬───────────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────────┐
│              Phase META (收尾)                                       │
│                                                                      │
│  META-01: 全部測試驗證 (依賴全部開發 + CI 完成)                      │
│       ↓                                                              │
│  META-02: REVIEWER 評分 (依賴 META-01)                               │
│       ↓ (若 < 95 分 → 返工循環)                                      │
│  META-03: 總結報告 + Commit & Push (依賴 META-02)                    │
└──────────────────────────────────────────────────────────────────────┘
```

### 並行策略

| 可並行任務組 | 說明 |
|------------|------|
| P0-1a + P1-1a + P1-1b + P1-2a + P1-3d | 全部在 KnowGraphGo 端，無依賴關係 |
| P1-3a + P1-3b + P1-3c | 三個測試修復互相獨立 |
| P0-1b + P0-2a | Python 端 ID 比對和 E2E 腳本無依賴 |
| CI-01~CI-05 | 各 CI 步驟可並行配置 |
| META-01→META-02→META-03 | 必須順序執行 |

---

## 三、負責角色對應

| 角色 | 負責任務 | 說明 |
|------|---------|------|
| **knowgraphgo-dev** | P0-1a, P1-1a, P1-1b, P1-2a, P1-3d | Go 端修改，操作 KnowGraphGo 倉庫 |
| **backend-logic** | P1-2c | Python 端確認，操作 AI-Kill-Cancer 倉庫 |
| **test-writer** | P0-1b, P0-2a, P0-2b, P0-3a, P1-1c, P1-2b, P1-3a, P1-3b, P1-3c, P0-3b | 測試撰寫與修復，可能跨倉庫 |
| **devops** | P0-1c, P0-2c, CI-01~CI-05 | CI 配置 |
| **reviewer** | META-02 | 評分子代理 |
| **doc-writer** | META-03 | 總結報告 |

---

## 四、返工預案

### 觸發條件

REVIEWER 總分 < 95，或任一核心需求 FAIL：
- Cross-language ID Parity（P0-1）
- Cross Repository Digital Thread（P0-2）
- Store Level Idempotent Replay（P0-3）
- Stub Entity（P1-1）
- Relation Provenance（P1-2）
- Panic（P1-3）
- CI 全部加入 GitHub Actions（CI）

### 返工流程

```
循環次數 = 0

do {
  1. PLANNER(resume) 讀取最新評分報告，重新規劃
     輸入：原始需求 `tasks/requirements.md` + 最新評分報告
     輸出：針對剩餘 FAIL 項目的修正計劃

  2. 開發子代理(resume) 按新計劃重新執行
     輸入：修正後的計劃
     輸出：修正後的交付檔案

  3. REVIEWER 重新評分
     循環次數 + 1
     報告命名：review_phase3d_final_<循環次數>.md

} while (總分 < 95 && 循環次數 < 5)
```

### 常見缺失與修正指引

| 缺失類型 | 典型原因 | 修正策略 |
|----------|---------|----------|
| Python/Go ID 不一致 | Canonical key 格式或 normalization 有差異 | 統一使用 `docs/clinical-graph-id-spec.md` 作為 source of truth，golden test 逐項比對 |
| E2E Digital Thread 失敗 | Event apply 順序錯誤或 Relation 缺失 | 確保 Event 序列按 patient→recommendation→decision→consensus 順序 apply，所有 Target Entity 已存在 |
| Idempotent Replay 失敗 | Upsert 邏輯不正確 | 檢查 key-based upsert：Entity ID 相同則 update properties，不 insert 新的 |
| Relation Provenance 缺失 | Relation.Properties 未被賦值 | 在 `adapter.go` 中每個 Relation 建立點添加 provenance Properties |
| Stub 覆蓋完整 Entity | Upsert 邏輯未區分 stub vs 完整 entity | 檢查 Adapter 中 Patient 已存在時不覆蓋其 Properties |
| 測試失敗 | 測試代碼未同步更新 | 檢查所有測試的斷言邏輯和必填字段，與生產代碼同步 |

### 最終結果判定

- 循環次數 < 5 且 ≥ 95 分 → Phase 3D Final Acceptance 完成 ✅
- 循環次數 ≥ 5 且仍 < 95 分 → 標記「阻塞⚠️ → 啟動 DeepSeek MCP 顧問」，DeepSeek 介入後最多再修 2 輪

---

## 五、驗收標準

### 全部必須 PASS

| # | 驗收項 | 對應任務 | 驗證方式 |
|---|--------|---------|----------|
| 1 | **Python ID == Go ID** | P0-1a, P0-1b, P0-1c | Golden test 交叉比對，10 種 Entity + Relation 全部一致 |
| 2 | **Cross Repository Digital Thread** | P0-2a, P0-2b, P0-2c | E2E CLI apply → query，驗證完整路徑、Node/Relation Count、Properties |
| 3 | **Idempotent Replay** | P0-3a, P0-3b | Apply 兩次，Entity/Relation Count 不增加，Update Count 正常 |
| 4 | **Stub Entity** | P1-1a, P1-1b, P1-1c | Patient 完整 Properties，Stub 不覆蓋 |
| 5 | **Relation Provenance** | P1-2a, P1-2b, P1-2c | 每條 Relation 有 event_id/event_type/aggregate_type/aggregate_id/correlation_id/causation_id/occurred_at/source_system |
| 6 | **No Panic** | P1-3a, P1-3b, P1-3c, P1-3d | 全部測試 PASS，Go 端無 panic() |
| 7 | **CI 全部 GitHub Actions** | CI-01~CI-05 | 所有新測試在 CI 中自動執行 |
| 8 | **Reviewer ≥ 95** | META-02 | REVIEWER 評分子代理評分 ≥ 95 |

### 測試命令

```bash
# Python 測試
cd AI-Kill-Cancer
pytest tests/ --tb=short -v

# Go 測試
cd KnowGraphGo
go test ./... -v
go vet ./...
go build ./cmd/knowgraph/

# CI 模擬
# 在 GitHub Actions 中觀察完整 pipeline
```

---

## 六、時間估算

| Phase | 任務 | 估算工時 | 備註 |
|-------|------|---------|------|
| **P0-1** | Cross-language ID Parity | **2h** | |
| P0-1a | KnowGraphGo golden test | 1h | |
| P0-1b | Python golden 比對測試 | 0.5h | |
| P0-1c | CI 整合 | 0.5h | |
| **P0-2** | Cross Repository Digital Thread | **3.5h** | |
| P0-2a | E2E 腳本 | 2h | 最複雜的單一任務 |
| P0-2b | E2E Idempotent Replay | 1h | 合併在 E2E 腳本中 |
| P0-2c | CI 整合 | 0.5h | |
| **P0-3** | Store Level Idempotent Replay | **0.3h** | 確認 + 整合到 E2E |
| **P1-1** | Stub Entity | **1.6h** | |
| P1-1a | Patient Properties 確認 | 0.3h | |
| P1-1b | Stub 確認 | 0.3h | |
| P1-1c | Stub 測試 | 1h | |
| **P1-2** | Relation Provenance | **2.3h** | |
| P1-2a | Adapter 添加 Provenance | 1.5h | |
| P1-2b | Provenance 測試 | 0.5h | |
| P1-2c | Python 端確認 | 0.3h | |
| **P1-3** | Panic 處理 | **0.9h** | |
| P1-3a~c | 3 項測試修復 | 0.6h | |
| P1-3d | Go 端 panic 確認 | 0.3h | |
| **CI** | CI 強化 | **1.9h** | |
| CI-01~CI-05 | CI 步驟配置 | 1.9h | 含除錯 |
| **META** | 收尾 | **2h** | |
| META-01 | 全部測試驗證 | 0.5h | |
| META-02 | Reviewer 評分 | 1h | |
| META-03 | 總結報告 | 0.5h | |
| | **總計** | **~14.5h** | |
| | *返工循環（每輪）* | *+4~8h* | 視缺失範圍 |

---

## 七、檔案變更完整清單

### KnowGraphGo 修改檔案

| # | 路徑 | 修改內容 | 對應任務 |
|---|------|---------|---------|
| 1 | `adapter/clinical/id_factory_test.go` | 新增 golden test → 輸出 `golden_output.json` | P0-1a |
| 2 | `adapter/clinical/adapter.go` | Relation Properties 添加完整 provenance 信息 | P1-2a |
| 3 | `adapter/clinical/adapter_test.go` | Provenance 測試擴展為檢查每個 Relation 的 Properties | P1-2b |
| 4 | `adapter/clinical/adapter_test.go` | 新增 Stub Entity 測試 | P1-1c |
| 5 | `adapter/clinical/*.go` | 確認無 `panic()` 殘留 | P1-3d |

### AI-Kill-Cancer 修改檔案

| # | 路徑 | 修改內容 | 對應任務 |
|---|------|---------|---------|
| 1 | `tests/test_phase3d_id_parity.py` | 新增 `test_id_parity_with_go_golden()` 方法 | P0-1b |
| 2 | `tests/unit/test_phase3d_outbox_repo.py` | 修正 `test_mark_failed` 斷言邏輯 | P1-3a |
| 3 | `tests/unit/test_phase3d_worker.py` | `test_worker_with_mock_client` 和 `test_worker_retry_on_failure` 添加 `occurred_at` | P1-3b, P1-3c |
| 4 | `.github/workflows/ci.yml` | 新增 CI 步驟：Cross-language parity, E2E Digital Thread, Stub, Provenance | CI-01~CI-05 |

### AI-Kill-Cancer 新增檔案

| # | 路徑 | 說明 | 對應任務 |
|---|------|------|---------|
| 1 | `scripts/cross_repo_e2e_test.sh` | 端到端 E2E Digital Thread 測試腳本（含 Idempotent Replay） | P0-2a, P0-2b |

---

> 本計劃僅針對 ChatGPT Review 指出的 P0/P1 問題進行修正。
> 不得新增功能、不得重構、不得修改 API、不得修改資料模型。
> 完成後提供：git status, git diff --stat, git log -1, 全部新增測試, CI Run, GitHub Actions URL。
