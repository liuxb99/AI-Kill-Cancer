# Code Quality Review Report

**日期：** 2025-01-XX
**審查範圍：** 全專案（KnowGraphGo + src/backend）
**審查人員：** AI Code Review Agent

---

## 9. Graph Adapter Review

**分數：7/10**

### 發現的問題

#### 9.1 Python ID Factory 缺少 Treatment Plan 相關方法（嚴重）

**嚴重性：** HIGH
**影響：** 跨語言 ID 不一致，Graph Projection Worker 無法爲治療計劃相關實體生成確定性 ID

**檔案：** `src/backend/clinical_graph/id_factory.py`

Go 版 `ClinicalIDFactory`（`KnowGraphGo/adapter/clinical/id_factory.go`）定義了以下方法但 Python 版缺少對應實作：

| Go 方法 | Python 方法 | 狀態 |
|---------|------------|------|
| `TreatmentPlanID()` | `treatment_plan_id()` | ❌ 缺少 |
| `TreatmentPhaseID()` | `treatment_phase_id()` | ❌ 缺少 |
| `TreatmentItemID()` | `treatment_item_id()` | ❌ 缺少 |
| `MonitoringID()` | `monitoring_id()` | ❌ 缺少 |
| `SafetyRuleID()` | `safety_rule_id()` | ❌ 缺少 |

**證據：**
- Go 版第 76-98 行：`TreatmentPlanID`, `TreatmentPhaseID`, `TreatmentItemID`, `MonitoringID`, `SafetyRuleID`
- Python 版僅有 `patient_id` 到 `variant_id`（第 24-67 行），無上述方法
- ID Parity 測試（`tests/test_phase3d_id_parity.py`）的 `entity_factories` 映射（第 99-109 行）也未包含這些類型

#### 9.2 buildProvenance 總是返回 ProvenanceImported

**檔案：** `KnowGraphGo/adapter/clinical/adapter.go:110-112`

```go
func buildProvenance(event GraphEvent) graph.Provenance {
    return graph.ProvenanceImported
}
```

該函數忽略事件類型，始終返回「Imported」。對於內部生成的事件（如 `treatment_plan.approved`），應該使用不同的 Provenance 值（如 `ProvenanceDerived` 或 `ProvenanceGenerated`）。這會導致圖譜無法區分外部匯入和內部派生的事實。

#### 9.3 Adapter 未處理 Variant/Guideline/Contraindication Event

**檔案：** `KnowGraphGo/adapter/clinical/adapter.go:66-89`

`ApplyEvent` 的 `switch` 分支未包含以下事件類型的映射：
- `variant.created` / `variant.updated` — ontology 定義了 `EntityKindVariant`、`EntityKindGene` 及 `HAS_VARIANT`、`LOCATED_IN_GENE` 關係
- `guideline.*` — ontology 定義了 `EntityKindGuideline`
- `drug.*` — ontology 定義了 `EntityKindDrug`、`HAS_CONTRAINDICATION`、`ALTERNATIVE_TO` 關係

#### 9.4 Patient / Drug / Evidence Stub 實體在多個 Mapper 中重複創建

**檔案：** `KnowGraphGo/adapter/clinical/adapter.go`

| Stub Entity Kind | 出現位置（行號） |
|-----------------|----------------|
| `EntityKindPatient` | 191, 283, 441, 596, 834 |
| `EntityKindDrug` | 323, 979 |
| `EntityKindEvidence` | 364, 509, 723, 1011 |

雖然 Event Sourcing 模式下這是預期行爲（不同 Event 可能引用同一實體），但同一實體在多處以不同屬性集創建，若同一 `aggregate_id` 在不同 mapper 中提供不同 `properties`，會導致資料不一致。建議建立統一的 Stub Factory 方法。

#### 9.5 缺少 Schema Version 沖突處理

沒有邏輯處理同一實體以較低 `schema_version` 覆蓋較高版本的場景。`entityProps()` 在第 136-160 行雖然記錄了 `schema_version`，但未做版本比較。

#### 9.6 Worker Phase 2 外部工作期間無防護

**檔案：** `src/backend/clinical_graph/worker.py:60-84`

Phase 2（External Work）在提交 Claim Transaction 後、Result Transaction 前，如果 Worker 進程崩潰，事件會卡在 `processing` 狀態。缺少 `heartbeat` 或 `timeout` 機制來恢復卡住的事件。

### 良好實踐

- **確定性 ID 生成**：Go 和 Python 使用相同的 UUIDv5 Namespace (`a7b4e5c2-8d9f-4a3b-8c1d-6e9f2a7b3c5d`) 和 Canonical Key 格式，確保跨語言 ID 一致（除了 9.1 的缺失部分）
- **Provenance 欄位完整**：`relationProps()` 和 `entityProps()` 均包含任務要求的 8 個 Provenance 欄位
- **重試策略明確**：`retry_policy.py` 使用指數退避（1min→5min→15min→1h→6h），死信機制清晰
- **三段式 Worker 事務**：Claim → External Work → Result 的事務劃分合理

### 建議

1. **立即修復 9.1**：在 `src/backend/clinical_graph/id_factory.py` 中補上缺少的 5 個方法
2. **改進 `buildProvenance`**：根據事件類型返回不同的 Provenance 值
3. **考慮添加 Variant/Drug Event Mapper**：至少提供 Stub 實體映射
4. **Worker 添加 Heartbeat**：防止 Phase 2 崩潰導致事件卡死

---

## 10. Tests Coverage Review

**分數：8/10**

### 測試檔案清單

#### KnowGraphGo (Go) 測試
- `KnowGraphGo/adapter/clinical/clinical_test.go` — 40KB，Adapter mapping 測試
- `KnowGraphGo/cmd/knowgraph/main_test.go` — 40KB，CLI 整合測試
- `KnowGraphGo/store/sqlite/store_test.go` — 41KB，SQLite 儲存測試
- 其他單元測試：`graph/*_test.go`、`inference/*_test.go`、`pattern/*_test.go` 等

#### Python 測試（tests/ 目錄）
- 引擎測試：`test_recommendation_engine.py`、`test_tumor_board_engine.py`、`test_drug_ranking.py`、`tests/backend/clinical/test_treatment_plan_engine.py`
- 服務測試：`test_recommendation_service.py`、`test_clinical_decision_service.py`、`test_tumor_board_service.py`（透過 test_tumor_board_repo.py?）、`tests/backend/services/test_treatment_plan_service.py`
- API 測試：`test_api.py`、`test_api_v1.py`、`test_api_recommendation.py`、`test_api_clinical_decision.py`、`test_api_tumor_board.py`、`tests/backend/api/test_treatment_plan_api.py`
- 儲存庫測試：`test_repositories.py`、`test_clinical_decision_repo.py`、`test_tumor_board_repo.py`、`tests/backend/repositories/test_treatment_plan_repos.py`
- 遷移測試：`test_migration.py`、`test_migration_gate.py`、`tests/integration/test_migration_*.py`
- 重啟恢復測試：`test_restart_recovery.py`、`test_tumor_board_restart_recovery.py`、`tests/backend/integration/test_treatment_plan_restart.py`
- Graph 整合測試：`tests/test_phase3d_*.py`（6個檔案）
- 其他：`test_evidence.py`、`test_vcf_parser.py`、`test_workbench.py` 等

### 發現的問題

#### 10.1 Engine 測試覆蓋

**現狀：**
- `test_recommendation_engine.py`：覆蓋 `WeightRegistry`、`EvidenceAggregator`、`DrugRanker`、`RecommendationRule`、`DrugRankingEngine` — ✅ 完整
- `test_tumor_board_engine.py`：覆蓋 `ConsensusEngine` 的全部分類、權重、異議處理 — ✅ 完整
- `test_drug_ranking.py`：覆蓋 scoring functions — ✅ 完整
- `tests/backend/clinical/test_treatment_plan_engine.py`：治療計劃引擎 — ✅ 存在

**遺漏：**
- ❌ `TreatmentPlanStateMachine`（`treatment_plan_state_machine.py`，4KB）缺乏獨立單元測試
- ❌ `TreatmentPlanTrace`（`treatment_plan_trace.py`，6.8KB）缺乏獨立單元測試
- ❌ `ClinicalDecisionEngine` 的邊界案例（空證據列表、極端權重值）

#### 10.2 Repository 測試覆蓋

**現狀：**
- `test_repositories.py`：通用 CRUD 測試 — ✅
- `test_clinical_decision_repo.py`：Clinical Decision CRUD — ✅
- `test_tumor_board_repo.py`：Tumor Board CRUD — ✅
- `tests/backend/repositories/test_treatment_plan_repos.py`：治療計劃完整 CRUD + 邊界案例 — ✅ 非常完整

**遺漏：**
- ❌ `ClinicalGraphOutboxRepository` 的邊界案例測試（死信場景、Claim 競爭條件）
- ❌ `EvidenceItemRepository`、`DrugInteractionRepository` 無獨立測試（僅在整合測試中覆蓋）

#### 10.3 Service 測試覆蓋

**現狀：**
- `test_clinical_decision_service.py`：Transactional rollback 測試 — ✅
- `test_recommendation_service.py`：服務層邏輯 — ✅
- `tests/backend/services/test_treatment_plan_service.py`：治療計劃服務測試 — ✅ 覆蓋 create/revision/rollback

**遺漏：**
- ❌ `TumorBoardConsensusService` 無獨立服務層測試（缺少 Transaction rollback 測試）
- ❌ `ClinicalGraphEventService` 無測試（`clinical_graph_event_service.py` 僅 2KB）

#### 10.4 API 測試覆蓋

**現狀：**
- `test_api.py`、`test_api_v1.py`：基本路由/狀態碼測試 — ✅
- `test_api_recommendation.py`、`test_api_clinical_decision.py`、`test_api_tumor_board.py`：各 API 端點 — ✅
- `tests/backend/api/test_treatment_plan_api.py`：治療計劃 API — ✅

**遺漏：**
- ❌ API Validation Error 測試不完整（請求體缺少必填字段的 422 測試）
- ❌ API Authentication/Authorization 測試在部分端點缺失

#### 10.5 Restart Recovery 測試

**現狀：**
- `test_restart_recovery.py` — ✅ 存在
- `test_tumor_board_restart_recovery.py` — ✅ 存在
- `tests/backend/integration/test_treatment_plan_restart.py` — ✅ 存在

**遺漏：**
- ❌ 跨多個 Aggregate 的 Restart Recovery 整合測試

#### 10.6 Migration 測試

**現狀：**
- `test_migration.py`、`test_migration_gate.py` — ✅ 基本遷移測試
- `tests/integration/test_migration_016.py` — ✅ 版本 016 專項測試
- `tests/integration/test_migration_025_pg_full_cycle.py` — ✅ Postgres 完整週期
- `tests/integration/test_migration_025_pg_schema_compare.py` — ✅ Schema 比較
- `tests/integration/test_migration_025_pg_trace_constraint.py` — ✅ Trace 約束測試

**遺漏：**
- ❌ Upgrade + Downgrade + Re-upgrade 完整循環測試（僅針對部分版本）
- ❌ 未涵蓋所有 Migration 版本的獨立測試

#### 10.7 Graph Integration 測試

**現狀：**
- `tests/test_phase3d_id_parity.py` — ✅ 跨語言 ID 一致性測試
- `tests/test_phase3d_rebuild_idempotent.py` — ✅ 重播冪等性測試
- `tests/unit/test_phase3d_worker.py` — ✅ Worker 測試
- `tests/unit/test_phase3d_outbox_repo.py` — ✅ Outbox Repository 測試
- `tests/unit/test_phase3d_outbox_service.py` — ✅ Outbox Service 測試
- `tests/unit/test_phase3d_event_schema.py` — ✅ Event Schema 測試

**遺漏：**
- ❌ **沒有真正的 KnowGraphGo CLI 端到端整合測試**（所有測試使用 Mock Client，不真正呼叫 `knowgraph` binary）
- ❌ 缺少 Event → Adapter → Store 的完整 Graph Projection 整合測試

### 建議

1. 補上 `TreatmentPlanStateMachine` 和 `TreatmentPlanTrace` 的獨立單元測試
2. 爲 `TumorBoardConsensusService` 添加 Transaction rollback 測試
3. 爲所有 API 端點補充 Validation Error（422）測試
4. **建立 KnowGraphGo CLI 端到端 Graph Projection 整合測試**（Priority High）
5. 補上 Upgrade + Downgrade + Re-upgrade 完整循環測試

---

## 11. Dead Code Analysis

**分數：9.5/10**

### 發現的問題

#### 11.1 TODO / FIXME / HACK / XXX 註解

**結果：無**

在全部 Go 和 Python 生產代碼中未發現任何 `TODO`、`FIXME`、`HACK`、`XXX` 註解殘留。這是極好的實踐。

#### 11.2 Deprecated 標記

**結果：無**

未發現 `@deprecated` 或 `// Deprecated:` 標記。

#### 11.3 Unused Imports / Functions / Variables

**潛在問題：**

- **`KnowGraphGo/adapter/clinical/adapter.go:9`**：`"context"` import 在 `ApplyEvent` 中使用了 ctx 參數但未實際傳遞給下游。所有 mapper 的 `context.Context` 參數目前未使用（僅保留 interface signature）。
- **`src/backend/clinical/__init__.py`**：從子模組大量 re-export，部分符號可能未在 module 外部使用。

#### 11.4 Duplicate Code / Copy-Paste 痕跡

- **`adapter.go` 中的 Patient Stub 創建**：第 280-291 行、第 438-448 行、第 593-603 行、第 831-841 行——高度重複的 patient stub 創建代碼塊（僅 From entity 不同）
- **Evidence Stub 創建**：第 360-371 行、第 505-516 行、第 719-730 行、第 1008-1019 行——4 次重複的 evidence stub 創建
- **Relation Provenance 設置**：所有 Relation 的 Properties 設置完全相同（`relationProps(event)`），可提取統一 builder

### 良好實踐

- 生產代碼無 TODO/FIXME 殘留，說明團隊注重代碼質量
- 無明顯未使用的導入或死函數

### 建議

1. 提取 Patient/Drug/Evidence Stub Factory 方法，消除重複代碼
2. 雖然目前無 TODO 殘留，建議建立 Pre-commit Hook 防止 TODO 進入主分支

---

## 12. Architecture Smell

**分數：6.5/10**

### 發現的問題

#### 12.1 God Class / 超大類別（>500 行）

以下檔案規模過大，違反單一職責原則：

| 檔案 | 大小（bytes） | 估算行數 | 類別/功能 |
|------|-------------|---------|----------|
| `src/backend/clinical/report_generator.py` | 64,451 | ~1,600+ | `ReportGenerator` |
| `src/backend/services/treatment_plan_service.py` | 57,242 | ~1,400+ | `TreatmentPlanService` |
| `src/backend/services/tumor_board_service.py` | 34,102 | ~850+ | `TumorBoardConsensusService` |
| `src/backend/clinical/recommendation_engine.py` | 31,224 | ~780+ | `RecommendationEngine` + `DrugRanker` + `EvidenceAggregator` |
| `src/backend/clinical/drug_ranking.py` | 29,274 | ~730+ | `DrugRankingEngine` |
| `src/backend/clinical/tumor_board_engine.py` | 29,670 | ~740+ | `ConsensusEngine` |
| `src/backend/clinical/recommendation.py` | 30,455 | ~760+ | 推薦相關功能 |
| `src/backend/services/clinical_decision_service.py` | 25,548 | ~640+ | `ClinicalDecisionService` |
| `KnowGraphGo/adapter/clinical/adapter.go` | 39,905 | ~1,214 | `ClinicalAdapter` |
| `KnowGraphGo/store/memory/store.go` | 29,045 | ~750+ | In-memory store |

**`TreatmentPlanService`（57KB）是最嚴重的問題**：它同時負責 orchestrating、validation、persistence、outbox 事件創建、版本管理。應拆分爲多個職責清晰的類別。

#### 12.2 Long Function（>100 行）

- **`KnowGraphGo/adapter/clinical/adapter.go`**：
  - `mapTreatmentPlanEvent()` — 第 783-1103 行，約 320 行
  - `mapRecommendationEvent()` — 第 233-392 行，約 159 行
  - `mapClinicalDecisionEvent()` — 第 394-537 行，約 143 行
  - `mapConsensusEvent()` — 第 539-751 行，約 212 行

- **`src/backend/services/treatment_plan_service.py`**：
  - `create_plan()` — 第 253-376 行，約 120 行不含註釋
  - `_persist_plan()` — 第 818-976 行，約 158 行
  - `_build_engine_input()` — 第 1270-1340 行，約 70 行

#### 12.3 Circular Dependency

**結果：未發現明顯的循環依賴**

檢查了 `src/backend/services/` → `src/backend/repositories/` → `src/backend/domain/` 的導入鏈，未發現循環導入。

#### 12.4 Duplicated Logic

1. **Patient Stub 創建邏輯**：在 `adapter.go` 的 5 個 mapper 中重複（見 11.4）
2. **Evidence ID 去重邏輯**：`mapRecommendationEvent`（第 306-316 行）、`mapClinicalDecisionEvent`（第 491-502 行）、`mapConsensusEvent`（第 705-716 行）實現了相同的 `dedup` 模式
3. **Python Service 層的 Upstream Data Loading**：`TreatmentPlanService.create_plan()` 和 `_create_revision()` 都從 repository 加載 recommendation、clinical decision、consensus，邏輯重複

#### 12.5 Duplicated SQL

**結果：未發現明顯的 SQL 重複**

儲存庫層使用 SQLAlchemy ORM，無原始 SQL 字串重複。

#### 12.6 Duplicated Validation

**結果：未發現明顯的驗證邏輯重複**

API 層使用 Pydantic 驗證，Service 層有獨立的業務驗證（如 `_validate_upstream_link_consistency`），責任劃分清晰。

### 良好實踐

- 無循環依賴，模塊劃分清晰（service → repository → domain）
- API、Service、Repository 三層分工明確
- 使用 Pydantic 進行輸入驗證，使用 SQLAlchemy ORM 避免 SQL 重複

### 建議

1. **拆分 `TreatmentPlanService`**：將 Persistence 邏輯提取到獨立的 `TreatmentPlanPersistenceService` 或 `TreatmentPlanFactory`
2. **拆分 `report_generator.py`**：按報表類型（臨床報告、基因報告、治療計劃報告）拆分爲多個生成器
3. **將大型 Mapper 函數拆分**：`mapTreatmentPlanEvent` 應拆分爲 `mapPhases`、`mapMonitoring`、`mapSafetyRules` 等子函數

---

## 13. Refactor Candidate

### HIGH（架構性問題，可能導致 Bug 或無法維護）

#### H1. [HIGH] Python ID Factory 缺少 Treatment Plan 相關方法

**檔案：** `src/backend/clinical_graph/id_factory.py`
**問題：** 缺少 `treatment_plan_id()`、`treatment_phase_id()`、`treatment_item_id()`、`monitoring_id()`、`safety_rule_id()` 方法
**影響：** 治療計劃相關實體的跨語言 ID 不一致，導致 Graph Projection 失敗或資料損毀
**建議：** 立即補上缺少的方法，並在 ID Parity 測試中添加對應的測試案例

#### H2. [HIGH] buildProvenance 硬編碼爲 ProvenanceImported

**檔案：** `KnowGraphGo/adapter/clinical/adapter.go:110-112`
**影響：** 所有事件（包括內部派生的事件如 `treatment_plan.approved`）都被標記爲「匯入」，無法區分資料來源類型
**建議：** 根據 EventType 返回不同的 Provenance（Imported / Derived / Generated）

#### H3. [HIGH] Adapter 缺少 Variant/Guideline/Drug 事件處理

**檔案：** `KnowGraphGo/adapter/clinical/adapter.go:66-89`
**影響：** ontology 中註冊的實體類型和關係類型在 adapter 中無法通過事件觸發生產
**建議：** 至少添加 Stub mapping，確保 Variant、Guideline、Drug 相關事件可以被處理

### MEDIUM（可改進但非緊急）

#### M1. [MEDIUM] God Service — TreatmentPlanService（57KB）

**檔案：** `src/backend/services/treatment_plan_service.py`
**問題：** 57KB、約 1,400 行，違反單一職責原則
**建議：** 將 persistence 邏輯、upstream data loading、event creation 分別提取到獨立的類別

#### M2. [MEDIUM] God Class — ClinicalAdapter（40KB）

**檔案：** `KnowGraphGo/adapter/clinical/adapter.go`
**問題：** 約 1,200 行，6 個大型 mapper 函數
**建議：** 將每個 mapper 函數中的 stub 創建、relation 創建提取爲輔助方法

#### M3. [MEDIUM] mapTreatmentPlanEvent 函數過大（~320 行）

**檔案：** `KnowGraphGo/adapter/clinical/adapter.go:783-1103`
**問題：** 單個函數處理 Phase、Item、Monitoring、SafetyRule 的映射
**建議：** 拆分爲 `mapPhases()`、`mapMonitoring()`、`mapSafetyRules()` 輔助方法

#### M4. [MEDIUM] Worker 缺少 Heartbeat 機制

**檔案：** `src/backend/clinical_graph/worker.py:60-84`
**問題：** Phase 2 外部工作期間進程崩潰會導致事件卡在 `processing` 狀態
**建議：** 添加 Heartbeat 更新機制，或在啟動時恢復超時的 processing 事件

### LOW（程式碼風格或微小改進）

#### L1. [LOW] Patient Stub 創建代碼重複

**檔案：** `KnowGraphGo/adapter/clinical/adapter.go`（行 280-291, 438-448, 593-603, 831-841）
**建議：** 提取 `stubPatient(entityID, patientID)` 輔助方法

#### L2. [LOW] Evidence ID 去重邏輯重複

**檔案：** `KnowGraphGo/adapter/clinical/adapter.go`（行 306-316, 491-502, 705-716）
**建議：** 提取 `dedupEvidenceIDs(payload.EvidenceIDs, payload.EvidenceReferences)` 輔助函數

#### L3. [LOW] 註釋中使用非標準 Section 標記

**檔案：** `src/backend/services/treatment_plan_service.py`（多處 `# ──` 標記）
**建議：** 統一使用標準 docstring 或 Sphinx 風格的 Section 標記

#### L4. [LOW] Go 代碼中混用英文和中文註釋

**檔案：** `KnowGraphGo/cmd/knowgraph/main_test.go`（多處）
**建議：** 統一代碼註釋語言

---

## 總結

| 審查項目 | 分數 | 關鍵發現 |
|---------|------|---------|
| 9. Graph Adapter | **7/10** | Python ID Factory 缺少治療計劃方法；buildProvenance 硬編碼；缺少 Variant Event 處理 |
| 10. Tests Coverage | **8/10** | 測試覆蓋良好但缺少真正的 Graph CLI 整合測試和部分單元測試 |
| 11. Dead Code | **9.5/10** | 無 TODO/FIXME 殘留，代碼整潔 |
| 12. Architecture Smell | **6.5/10** | 多個 God Class，treatment_plan_service.py 高達 57KB |
| **整體** | **7.5/10** | **優先處理 H1（ID Factory 缺失方法）和 H2（Provenance 硬編碼）** |

### 優先級行動清單

| 優先級 | 項目 | 預計工時 |
|--------|------|---------|
| P0 | H1: 補上 Python ID Factory 缺少的 5 個方法 | 2h |
| P0 | H2: 改進 buildProvenance | 3h |
| P1 | H3: 添加 Variant/Drug Event 處理 | 4h |
| P1 | M3: 拆分 mapTreatmentPlanEvent | 4h |
| P1 | M4: Worker Heartbeat 機制 | 3h |
| P2 | M1/M2: 重構 God Class | 16h+ |
| P2 | L1/L2: 消除重複代碼 | 4h |
