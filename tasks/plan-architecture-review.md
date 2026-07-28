# Architecture Review 執行計劃 (Phase 1 ~ Phase 3E)

> **任務 ID**：architecture-review  
> **場景**：architecture-review（架構審查 + Code Review）  
> **範圍**：Phase1 → Phase2 → Phase3A → Phase3B → Phase3C → Phase3D → Phase3E 全部程式  
> **核心原則**：**禁止新增/修改功能或 API 行為**。只能 Review / Analysis / Report。  
> **最終產出**：`tasks/reviews/architecture_review.md`

---

## 1. Review 執行策略

### 策略選擇：按 Review 項目橫跨所有 Phase

建議採用 **「按 Review 項目，每個項目橫跨所有 Phase」** 的策略，而非按 Phase 逐個分析。理由如下：

| 策略 | 優點 | 缺點 |
|------|------|------|
| **按 Phase 掃** | 符合開發歷程，容易定位每個 Phase 的問題 | 重複造輪子（每輪都要重新熟悉架構），跨 Phase 的一致性問題容易被忽略 |
| **按 Review 項目掃** ✅ | 一次聚焦一個架構關注點，跨 Phase 橫向對比，容易發現不一致和架構侵蝕 | 需要同時理解所有 Phase 的程式碼 |

**核心原因**：Architecture Review 的最大價值在於發現**跨 Phase 的架構漂移** — 例如 Phase3E 的 Engine 是否混入了 DB 依賴、Phase3A 的 Repository 是否出現了 Business Logic。按項目橫掃能最有效地暴露這類問題。

### 執行順序（推薦）

```
Phase 1: 靜態分析工具掃描（Dead Code / Code Smell / Duplicate）
Phase 2: 分層架構審查（Domain → Repository → Service → Engine）
Phase 3: 跨層橫向審查（Migration → API → Digital Thread → Trace → Graph Adapter）
Phase 4: 測試覆蓋率審查
Phase 5: 綜合分析（Refactor Candidate / Architecture Smell）
Phase 6: 報告彙總與評分
```

---

## 2. 依賴關係與並行策略

### 依賴圖

```
                    ┌──────────────────────┐
                    │  Dead Code Analysis   │ ← 無依賴，可最先啟動
                    │  (Item 11)            │
                    └──────────┬───────────┘
                               │
            ┌──────────────────┼──────────────────┐
            ▼                  ▼                  ▼
    ┌───────────────┐  ┌───────────────┐  ┌───────────────┐
    │ Domain Review │  │   Code Smell  │  │  Duplicate    │
    │ (Item 1)      │  │   (Item 12)   │  │  Code (part)  │
    └───────┬───────┘  └───────┬───────┘  └───────┬───────┘
            │                  │                   │
            ▼                  │                   │
    ┌───────────────┐          │                   │
    │ Repository    │◄─────────┼───────────────────┘
    │ Review (2)    │          │
    └───────┬───────┘          │
            ▼                  │
    ┌───────────────┐          │
    │ Service       │          │
    │ Review (3)    │          │
    └───────┬───────┘          │
            ▼                  │
    ┌───────────────┐          │
    │ Engine        │          │
    │ Review (4)    │          │
    └───────┬───────┘          │
            │                  │
            ▼                  ▼
    ┌───────────────────────────────────────────┐
    │  Migration / API / Digital Thread / Trace │  ← 可並行
    │  / Graph Adapter (Items 5-9)              │
    └───────────────────┬───────────────────────┘
                        │
                        ▼
    ┌───────────────────────────────────────────┐
    │  Tests Coverage Review (Item 10)          │
    └───────────────────┬───────────────────────┘
                        │
                        ▼
    ┌───────────────────────────────────────────┐
    │  Refactor Candidate Analysis (Item 13)    │  ← 依賴前面所有發現
    └───────────────────┬───────────────────────┘
                        │
                        ▼
    ┌───────────────────────────────────────────┐
    │  最終報告彙總 & 評分                       │
    └───────────────────────────────────────────┘
```

### 可並行執行的項目

| 並行組 | 項目 | 說明 |
|--------|------|------|
| **A** (無依賴) | 11. Dead Code | 可純靜態分析，不依賴其他 Review 結果 |
| **B** (層層依賴) | 1→2→3→4 | Domain → Repository → Service → Engine，必須依序 |
| **C** (橫向獨立) | 5, 6, 7, 8, 9 | Migration, API, Digital Thread, Trace, Graph Adapter 彼此獨立，可並行 |
| **D** (依賴 C) | 10. Tests | 需要知道各層的實作才能判斷測試覆蓋率 |
| **E** (依賴全部) | 12, 13 | Architecture Smell 和 Refactor Candidate 需要所有前期發現 |
| **F** (彙總) | 最終報告 | 依賴所有項目完成 |

### 建議調度

```
Week 1: [A] Dead Code + [B-1] Domain
Week 2: [B-2] Repository + [B-3] Service + [C] 並行啟動 Migration/API
Week 3: [B-4] Engine + [C] 完成 Trace/Graph/Digital Thread
Week 4: [D] Tests + [E] Smell + Refactor
Week 5: [F] 最終報告
```

---

## 3. 各項 Review 的負責方式與工具建議

### Item 1: Domain 架構審查

**審查目標**：確保 Entity/Aggregate/ValueObject/State/Version 的一致性，Domain 層無 SQL/API/Session/HTTP 依賴。

| 面向 | 方法 | 工具 |
|------|------|------|
| 模型一致性 | 逐檔檢視 `src/backend/domain/` 所有模型，檢查命名、型別、關係設計 | `grep`, `code_index`, VS Code |
| 外部依賴檢查 | 掃描 `src/backend/domain/` 所有 import，確保無 `sqlalchemy.orm` 外的 DB 依賴、無 `requests`/`httpx`/`fastapi` | `grep -r "^import\|^from" src/backend/domain/` |
| State/Version 檢查 | 審查 `TreatmentPlanModel` 的 version、status 欄位設計，確認狀態機 enum 完整 | 手動檢視 |
| Pydantic vs ORM 分離 | 確認 domain 層清楚區分 Pydantic schema 和 SQLAlchemy Model | 手動檢視 |

**跨越 Phase 的關注點**：
- Phase1 初始 domain 模型 → Phase3E 新增的 TreatmentPlan 模型，是否保持了相同的設計風格？
- 是否所有 Phase 的 domain 模型都放在 `src/backend/domain/`？
- 是否有 domain 模型因為歷史因素殘留在其他目錄？

### Item 2: Repository 層審查

**審查目標**：無 commit/rollback/flush，無 Business Logic。

| 面向 | 方法 | 工具 |
|------|------|------|
| Transaction 邊界 | 確認所有 repository 的 `*Repository` class 中無 `.commit()` / `.rollback()` / `.flush()` 調用 | `grep -r "\.commit\|\.rollback\|\.flush" src/backend/repositories/` |
| Business Logic 檢查 | 確認 repository 僅做 CRUD/Query，無條件判斷、計分、規則引擎調用 | 手動檢視 |
| BaseRepository 一致性 | 檢查是否所有 repository 繼承自 `BaseRepository` | `code_index search -k class` |
| 查詢方法命名 | 確認查詢方法命名一致（`get_by_*` / `list_by_*` / `find_*`） | 手動檢視 |

### Item 3: Service 層審查

**審查目標**：Transaction Boundary 僅在 Service 層，Engine/Repository 不開 transaction。

| 面向 | 方法 | 工具 |
|------|------|------|
| Transaction 邊界 | 確認 service 方法使用 `async with db.begin()` 或 `db.commit()` 包裹完整操作 | `grep -r "begin\|commit" src/backend/services/` |
| Engine 調用 | 確認 service 調用 engine 時傳遞的是純資料結構而非 session | 手動檢視 |
| Repository 調用 | 確認 service 注入 session 到 repository | 手動檢視 |
| Service 單一職責 | 檢查是否有 god service（單檔 > 1000 行） | `wc -l src/backend/services/*.py` |

### Item 4: Engine 層審查

**審查目標**：Pure Function，無 DB/API/Repository/Session 依賴。

| 面向 | 方法 | 工具 |
|------|------|------|
| 外部依賴檢查 | 掃描 `src/backend/clinical/*engine*.py` 的 import | `grep "^import\|^from" src/backend/clinical/*engine*.py` |
| EngineInput/Output 純資料 | 確認 engine 接受/回傳 dataclass / dict / Pydantic，無 SQLAlchemy Model | 手動檢視 |
| Side-effect 檢查 | 確認 engine 內無 I/O 操作（file write / API call / subprocess） | 手動檢視 |

**涵蓋的 engine**：
- `recommendation_engine.py` (Phase3A)
- `drug_ranking.py` (Phase3A)
- `clinical_decision_engine.py` (Phase3B)
- `tumor_board_engine.py` (Phase3C)
- `treatment_plan_engine.py` (Phase3E)

### Item 5: Migration 審查

**審查目標**：Upgrade/Downgrade/Re-upgrade 一致性，SQLite/Postgres 一致。

| 面向 | 方法 | 工具 |
|------|------|------|
| Upgrade/Downgrade 對稱性 | 對每個 migration 版本檢查 downgrade() 是否能正確反轉 upgrade() | 手動檢視 + `test_migration.py` |
| SQLite/Postgres 分支 | 檢查 migration 中是否有 `batch_op` 和原生 PostgreSQL SQL 的正確分支 | 手動檢視 |
| Re-upgrade 冪等性 | 確認 upgrade head → downgrade N → upgrade head 可重複執行 | 執行測試 |
| 唯一約束/索引 | 檢查 constraint/index 命名的一致性和可預測性 | 手動檢視 |

**所有 migration 檔案**：`migrations/versions/001_*.py` ~ `025_*.py`

### Item 6: API 層審查

**審查目標**：GET/POST/PATCH/DELETE HTTP Status/Error/Validation 一致性。

| 面向 | 方法 | 工具 |
|------|------|------|
| HTTP Status 一致性 | 檢查所有 API route 的 status_code：POST → 201/202, GET → 200, DELETE → 204 | `grep -r "status_code" src/backend/api/` |
| Error Handling | 檢查錯誤回應是否統一使用 `HTTPException` + 標準格式 | 手動檢視 |
| Input Validation | 確認 API 層使用 Pydantic model 做 request validation | 手動檢視 |
| Auth/ACL 覆蓋 | 檢查是否所有 API route 都有 auth dependency | 手動檢視 |
| Route 命名慣例 | 確認 route path 命名一致（複數名詞、kebab-case） | 手動檢視 |

### Item 7: Digital Thread 審查

**審查目標**：Patient → Recommendation → Decision → Consensus → TreatmentPlan 的 Event → Outbox → Projection → KnowGraphGo 一致性。

| 面向 | 方法 | 工具 |
|------|------|------|
| Event Schema 一致性 | 檢查 `ClinicalGraphEvent` schema 在各 stage 的產生和使用 | `src/backend/schemas/clinical_graph_event.py` |
| Outbox 模式 | 確認 event 寫入 outbox 在 service 的同一 transaction 內 | `src/backend/repositories/clinical_graph_outbox_repo.py` |
| 事件順序 | 確認 Digital Thread 的事件順序正確（Patient → Recommendation → Decision → Consensus → TreatmentPlan） | 手動檢視 |
| KnowGraphGo 投影 | 檢查 `ClinicalGraphClient` 如何消費 outbox 事件 | `src/backend/clinical_graph/` |

### Item 8: Trace 審查

**審查目標**：trace_id / step_order / step_name / input / output / created_at 一致性。

| 面向 | 方法 | 工具 |
|------|------|------|
| Trace 欄位一致性 | 檢查所有 trace 相關 table 的 schema 是否一致 | `grep -r "TraceModel\|trace" src/backend/domain/` |
| Trace 產生時機 | 確認 trace 在 engine pipeline 的每個步驟產生 | 手動檢視 |
| Trace 持久化 | 確認 trace 與主體在同一個 transaction 中寫入 | 手動檢視 |

**涵蓋範圍**：
- `CalculationTrace` / `TraceManager` (Phase3A)
- `ClinicalDecisionTraceModel` (Phase3B)
- `TreatmentPlanTraceModel` / `TreatmentPlanTraceBuilder` (Phase3E)

### Item 9: Graph Adapter 審查

**審查目標**：Projection / Relation / Stub / Provenance 一致性，無 Duplicate Mapping。

| 面向 | 方法 | 工具 |
|------|------|------|
| 事件到 Graph 映射 | 檢查 `ClinicalGraphEvent` 如何被 KnowGraphGo 消費 | `KnowGraphGo/adapter/clinical/adapter.go` |
| ID 一致性 | 檢查 `id_factory.py` 和 `id_factory.go` 的 ID 生成邏輯一致 | 比對兩個檔案 |
| Provenance | 檢查 provenance 資訊在 graph 中的保存 | `KnowGraphGo/graph/provenance.go` |

### Item 10: Tests 覆蓋率審查

**審查目標**：Engine / Repository / Service / API / Restart / Migration / Postgres / Graph Coverage 完整性。

| 面向 | 方法 | 工具 |
|------|------|------|
| Engine 測試 | 檢查每個 engine 是否有對應的 unit test | `tests/clinical/`, `tests/test_*engine*.py` |
| Repository 測試 | 檢查每個 repository 是否有 integration test | `tests/test_*repo*.py`, `tests/repositories/` |
| Service 測試 | 檢查每個 service 是否有 integration test | `tests/test_*service*.py`, `tests/services/` |
| API 測試 | 檢查每個 API route 是否有 e2e test | `tests/test_api*.py`, `tests/backend/api/` |
| Migration 測試 | 檢查 upgrade/downgrade/re-upgrade 測試 | `tests/test_migration*.py` |
| Restart 測試 | 檢查 restart recovery 測試 | `tests/test_restart*.py` |
| Postgres 測試 | 檢查 PostgreSQL 專用測試 | `tests/integration/test_migration_025_pg*.py` |
| Digital Thread 測試 | 檢查 Graph/Outbox 測試 | `tests/test_phase3d_*.py` |

### Item 11: Dead Code 分析

**審查目標**：Unused / TODO / FIXME / Deprecated / Duplicate / Copy Paste。

| 面向 | 方法 | 工具 |
|------|------|------|
| TODO/FIXME 掃描 | 全專案 grep `TODO|FIXME|HACK|XXX|WORKAROUND` | `grep -rn "TODO\|FIXME\|HACK\|XXX" src/ --include="*.py"` |
| Deprecated 掃描 | 檢查 `@deprecated` 裝飾器和 `# Deprecated` 註解 | `grep -rn "deprecated\|Deprecated" src/` |
| Unused Import/Variable | 使用 `ruff` 或 `pylint` 掃描 | `ruff check src/` |
| Dead Endpoint | 檢查是否有定義但未註冊的 route | 手動檢視 |
| Orphan Files | 檢查是否有未被任何 import 引用的 Python 檔案 | 腳本輔助 |

### Item 12: Architecture Smell 分析

**審查目標**：God Service / Long Function / Circular Dependency / Duplicated Logic / Duplicated SQL / Duplicated Validation。

| 面向 | 方法 | 工具 |
|------|------|------|
| God Service | 找出 > 500 行的 service 檔案 | `wc -l src/backend/services/*.py` |
| Long Function | 找出 > 100 行的函數 | `pylint --max-line-length=100` 或手動 |
| Circular Dependency | 檢查 Python import 循環 | `pip install import-linter` 或手動 |
| Duplicated SQL | 掃描相似 SQL 查詢模式 | `grep -rn "SELECT\|INSERT\|UPDATE\|DELETE" src/` |
| Duplicated Validation | 檢查重複的欄位驗證邏輯 | 手動檢視 |

### Item 13: Refactor Candidate 分析

**審查目標**：從前面的發現中提煉出 High / Medium / Low 三個等級的重構候選。

| 等級 | 定義 | 舉例 |
|------|------|------|
| **High** | 影響正確性或明顯違反架構原則 | Engine 混入 session、Repository 有 business logic、Service 無 transaction |
| **Medium** | 影響可維護性但功能正確 | God Service、重複邏輯、命名不一致 |
| **Low** | 程式碼風格或輕微重複 | Missing docstring、變數命名不統一等 |

---

## 4. 預計產出格式

### 最終報告結構 (`tasks/reviews/architecture_review.md`)

```
# Architecture Review 報告

## 摘要
- Architecture Score: X.X/10
- Maintainability Score: X.X/10
- 技術債估算: XX 人天

## 各項 Review 結果
### 1. Domain 層 (Score: X.X/10)
#### 發現
- [P0] 問題描述
- [P1] 問題描述
#### 建議
...

### 2. Repository 層 (Score: X.X/10)
...

### 3-13. 其餘項目 (同上格式)

## 綜合分析
### 跨 Phase 趨勢
- Phase1→Phase3E 架構漂移分析
### 正面模式
- 值得保留的設計決策

## Refactor List
### High Priority
- 項目 | 檔案 | 預估工時
### Medium Priority
- ...
### Low Priority
- ...

## Risk List
- 風險描述 | 影響範圍 | 可能性 | 影響程度

## Code Smell 統計
- God Service: N 個
- Long Function: N 個
- Circular Dependency: N 處
- Duplicated Code: N 處
- 其他: ...

## Duplicate Code 報告
- 重複區塊 | 檔案 | 行數

## Phase 3F 建議
- 基於 Architecture Review 發現，建議 Phase 3F 應處理的重點

## P0 / P1 / P2 改善清單
### P0 (Critical - 需立即修正)
### P1 (High - 下個 Phase 處理)
### P2 (Medium - 可排入 Backlog)
```

### 評分量表

| 維度 | 權重 | 評分項目 |
|------|------|----------|
| 架構正確性 | 40% | 分層依賴方向、Transaction 邊界、Engine 純淨度 |
| 一致性 | 20% | 跨 Phase 設計風格一致、命名慣例 |
| 可維護性 | 20% | Code Smell、重複程式碼、函數長度 |
| 測試覆蓋率 | 20% | 各層測試覆蓋率、邊界案例 |

### 中間產物

每項 Review 產生一個獨立中間報告，存放於 `tasks/reviews/review_<item-name>.md`，最終彙總到 `architecture_review.md`。

```
tasks/reviews/
├── review_domain.md
├── review_repository.md
├── review_service.md
├── review_engine.md
├── review_migration.md
├── review_api.md
├── review_digital_thread.md
├── review_trace.md
├── review_graph_adapter.md
├── review_tests.md
├── review_dead_code.md
├── review_architecture_smell.md
├── review_refactor_candidate.md
└── architecture_review.md          ← 最終彙總報告
```

---

## 5. 返工預案

### 5.1 發現重大問題時的處理流程

```
發現問題 → 記錄到對應 Review 項目
         → 評估嚴重等級 (P0/P1/P2)
         → P0: 立即暫停 Review，通知決策者
         → P1: 記錄到 Risk List，繼續 Review
         → P2: 記錄到改善清單
```

### 5.2 返工判斷標準

| 嚴重等級 | 定義 | 行動 |
|---------|------|------|
| **P0 (Critical)** | 可能導致資料遺失、安全性漏洞、核心功能失效 | 立即暫停 Review，通知決策者 |
| **P1 (High)** | 明顯違反架構原則、可能影響正確性 | 記錄到 Risk List，Review 繼續 |
| **P2 (Medium)** | 可維護性問題、程式碼重複、命名不一致 | 記錄到改善清單 |

### 5.3 返工後復查流程

1. 修正完成後，標記對應 Review 項目為 **pending-recheck**
2. 針對修正的部分重新執行該項目的檢查要點
3. 更新最終報告中的評分和發現

### 5.4 無法判定的情況

若某個 Review 項目因以下原因無法判定：
- 資訊不足：需要在代碼中尋找更多上下文
- 設計意圖不明：需要查看 Phase 需求文檔或討論記錄

應在報告中標記為 **INCONCLUSIVE** 並說明原因，而不是主觀猜測。

### 5.5 衝突處理

若不同 Review 項目對同一程式碼給出矛盾的發現（例如：某段邏輯在 Domain Review 中被認為應屬於 Service），則：
1. 記錄兩個觀點到各自的 Review 項目
2. 在最終報告的「綜合分析」章節中進行比較
3. 以架構原則為最終判斷依據

---

## 附錄 A：檔案範圍對照表

| Review 項目 | 主要檔案路徑 |
|------------|-------------|
| 1. Domain | `src/backend/domain/` (所有檔案) |
| 2. Repository | `src/backend/repositories/` (所有檔案) |
| 3. Service | `src/backend/services/` (所有檔案) |
| 4. Engine | `src/backend/clinical/recommendation_engine.py`, `drug_ranking.py`, `clinical_decision_engine.py`, `tumor_board_engine.py`, `treatment_plan_engine.py` |
| 5. Migration | `migrations/versions/001_*.py` ~ `025_*.py`, `migrations/env.py` |
| 6. API | `src/backend/api/v1/` (所有檔案), `src/backend/api/routes.py` |
| 7. Digital Thread | `src/backend/schemas/clinical_graph_event.py`, `src/backend/clinical_graph/`, `src/backend/services/clinical_graph_event_service.py` |
| 8. Trace | `src/backend/clinical/calculation_trace.py`, `treatment_plan_trace.py`, `decision_thread.py` |
| 9. Graph Adapter | `KnowGraphGo/adapter/clinical/`, `KnowGraphGo/graph/`, `KnowGraphGo/service/` |
| 10. Tests | `tests/` (全部), `tests/backend/` (全部), `tests/integration/` (全部) |
| 11. Dead Code | 全專案 `src/`, `KnowGraphGo/` |
| 12. Architecture Smell | 全專案 `src/`, `KnowGraphGo/` |
| 13. Refactor Candidate | 基於所有前期發現彙總 |

## 附錄 B：快速檢查腳本建議

```bash
# Dead Code / TODO / FIXME
grep -rn "TODO\|FIXME\|HACK\|XXX\|WORKAROUND" src/ --include="*.py" --include="*.go"

# Repository 中不該有的操作
grep -rn "\.commit\(\)\|\.rollback\(\)\|\.flush\(\)" src/backend/repositories/

# Engine 中的外部依賴
grep -rn "^import\|^from" src/backend/clinical/ | grep -v "from src.backend.domain\|from src.backend.clinical\|import logging\|import dataclasses"

# Service 行數
wc -l src/backend/services/*.py

# 未使用的 import (需要 ruff)
ruff check src/ --select F401

# Migration upgrade/downgrade 檢查
grep -l "def downgrade" migrations/versions/*.py | wc -l
```
