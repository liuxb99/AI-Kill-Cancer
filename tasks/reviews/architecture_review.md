# 整體架構審查報告（Architecture Review）

> **審查日期**：2025-01  
> **專案版本**：v1.0.1  
> **審查範圍**：Domain 層、Repository 層、Service 層、Engine 層、Migration、API v1、Digital Thread、Trace、Graph Adapter、Tests、Dead Code、Architecture Smell、Refactor Candidates  
> **資料來源**：
> - `tasks/reviews/review_layers.md`（分層架構審查）
> - `tasks/reviews/review_crosscutting.md`（橫切關注點審查）
> - `tasks/reviews/review_quality.md`（程式碼品質審查）

---

## 1. Architecture Score（總體架構分數）

### 加權計算

| 審查維度 | 原始分數（/10） | 權重 | 加權得分 |
|---------|:--------------:|:----:|:--------:|
| 分層架構（Layers）—— Domain / Repository / Service / Engine | 5.75 | 40% | 2.30 |
| 橫切關注點（Crosscutting）—— Migration / API / Digital Thread / Trace | 6.50 | 30% | 1.95 |
| 程式碼品質（Quality）—— Graph Adapter / Tests / Dead Code / Smell | 7.50 | 30% | 2.25 |
| **總和** | | | **6.50** |

### 總體架構分數：**65 / 100**

### 評語

整體架構分數 65/100，處於「需要重大改進」區間。專案在模組劃分、DDD 分層意圖上方向正確，Service 層和 Engine 層的協調職責清晰，橫切關注點（Digital Thread、Outbox Pattern）的設計有前瞻性。然而，以下結構性問題嚴重拖累了整體分數：

1. **Domain 層純淨性崩潰（P0）**：全部 26 個 Domain 檔案均混入 SQLAlchemy ORM 依賴，Domain 層同時充當 ORM 模型和 API Schema 的容器，違反 DDD 分層原則。這是架構上最緊迫的問題。
2. **事務邊界不一致（P0）**：`BaseRepository` 預設 `commit()` 行爲導致事務邊界從 Service 層下沉至 Repository 層，形成資料不一致風險。
3. **Trace 系統碎片化**：三套獨立的 Trace 系統（CalculationTrace、TreatmentPlanTrace、DecisionThread）各自爲政，缺乏統一 Schema 和跨 Engine 的可追蹤性。
4. **多處 God Class / God Function**：`TreatmentPlanService`（57KB）、`ClinicalAdapter`（40KB）、`report_generator.py`（64KB）等檔案嚴重違反單一職責原則。
5. **API 層不一致**：HTTP Status Code、Error Response 格式、Validation 位置均未統一。

---

## 2. Maintainability Score（可維護性分數）

### 加權評估

| 評估因子 | 分數（/10） | 權重 | 加權得分 |
|---------|:----------:|:----:|:--------:|
| God Class / 超大函數 | 4.0 | 30% | 1.20 |
| 重複程式碼（Copy-Paste） | 6.5 | 20% | 1.30 |
| 依賴混亂 / 架構違規 | 5.0 | 25% | 1.25 |
| 命名與註解一致性 | 7.5 | 15% | 1.13 |
| 測試覆蓋對可維護性的支撐 | 8.0 | 10% | 0.80 |
| **總和** | | | **5.68** |

### 可維護性分數：**57 / 100**

### 評語

可維護性分數低於總體架構分數，反映以下關鍵問題：

- **God Class 密集**：`TreatmentPlanService`（57KB, ~1,400 行）、`report_generator.py`（64KB, ~1,600 行）、`KnowGraphGo/adapter/clinical/adapter.go`（40KB, ~1,214 行）等超大類別使得理解、測試和修改變得困難。
- **重複程式碼**：Go Adapter 中的 Patient/Evidence/Drug Stub 創建在 5 個 Mapper 中重複，Evidence ID 去重邏輯在 3 個 Mapper 中重複。
- **依賴方向違規**：Service 層反向依賴 API 層（`recommendation_service.py:248`），破壞了分層依賴規則。
- **正向因素**：測試覆蓋良好（8/10），無 TODO/FIXME 殘留，命名風格相對一致。

---

## 3. Technical Debt（技術債摘要）

### P0（立即修復，Blocking）總覽

| ID | 問題描述 | 影響層 | 檔案路徑 | 行號 |
|----|---------|-------|---------|------|
| P0-01 | **Domain 層混入 SQLAlchemy ORM 依賴**——全部 26 個 Domain 檔案均繼承 `DBBase` 並使用 `Column`、`String` 等 ORM 類型 | Domain | `src/backend/domain/*.py` | 全部檔案 |
| P0-02 | **Service 層反向依賴 API 層**——違反分層依賴方向 | Service | `src/backend/services/recommendation_service.py` | 248 |
| P0-03 | **BaseRepository 預設 commit() 導致事務邊界下移**——影響所有繼承子類 | Repository | `src/backend/repositories/base.py` | 29, 73, 82 |
| P0-04 | **Outbox Repository 混入大量業務邏輯**——CRUD 與業務邏輯未分離 | Repository | `src/backend/repositories/clinical_graph_outbox_repo.py` | 全檔案 |
| P0-05 | **Python ID Factory 缺少 5 個治療計劃相關方法**——跨語言 ID 不一致 | Graph | `src/backend/clinical_graph/id_factory.py` | 全檔案 |
| P0-06 | **buildProvenance 硬編碼爲 ProvenanceImported**——所有事件被標記爲「匯入」 | Graph | `KnowGraphGo/adapter/clinical/adapter.go` | 110-112 |

### P1（短期改善）總覽

| ID | 問題描述 | 影響層 | 檔案路徑 | 行號 |
|----|---------|-------|---------|------|
| P1-01 | `RecommendationEngine.run()` 嚴重違反 Pure Function 原則——產生 I/O 副作用 | Engine | `src/backend/clinical/recommendation_engine.py` | 482-715 |
| P1-02 | ORM 狀態欄位使用 `String(32)` 而非 `SAEnum`——失去資料庫層類型約束 | Domain | 多個 Model 檔案 | 分散 |
| P1-03 | 缺少樂觀鎖版本控制——無 `version_id` 欄位 | Domain | 全部 Model | 全域 |
| P1-04 | Repository 型別註解不完整——17/22 個檔案缺少 `AsyncSession` 型別 | Repository | 17 個 Repository 檔案 | `__init__` |
| P1-05 | **三套獨立 Trace 系統**——Schema 不一致，無法統一查詢 | Trace | `calculation_trace.py`、`treatment_plan_trace.py`、`decision_thread.py` | 全域 |
| P1-06 | **Patient Outbox 事件完全缺失**——Patient 變更不會投射到知識圖譜 | Digital Thread | 無對應服務調用 | - |
| P1-07 | **API Error Response 格式不統一**——三種格式並存 | API | `clinical.py`、`patients.py`、`evidence.py` | 分散 |
| P1-08 | **HTTP Status Code 不一致**——POST 返回 200 而非 201，部分語義錯誤 | API | `recommendation.py:125`、`cases.py:131` | 分散 |
| P1-09 | **Migration SQLite/PostgreSQL 不一致**——部分 Downgrade 不冪等 | Migration | `migrations/versions/015`、`022`、`025` | 分散 |
| P1-10 | **Adapter 缺少 Variant/Guideline/Drug 事件處理** | Graph | `KnowGraphGo/adapter/clinical/adapter.go:66-89` | 66-89 |
| P1-11 | **Worker 缺少 Heartbeat 機制**——Phase 2 崩潰導致事件卡死 | Graph | `src/backend/clinical_graph/worker.py:60-84` | 60-84 |

### P2（長期追蹤）總覽

| ID | 問題描述 | 影響層 | 檔案路徑 |
|----|---------|-------|---------|
| P2-01 | Aggregate 邊界不清晰——無顯式 Aggregate Root 標記 | Domain | 全域 |
| P2-02 | 缺少顯式 ValueObject 模式——無 `@dataclass(frozen=True)` 值物件 | Domain | 全域 |
| P2-03 | Engine 呼叫私有 API——耦合 RuleSet 內部實作 | Engine | `clinical_decision_engine.py:209` |
| P2-04 | 手動 try/commit 重複模式——缺少 `@transactional` 裝飾器 | Service | 全部 4 個 Service |
| P2-05 | **God Class：`TreatmentPlanService`（57KB）**——違反單一職責 | Service | `treatment_plan_service.py` |
| P2-06 | **God Class：`ClinicalAdapter`（40KB）**——6 個大型 Mapper 函數 | Graph | `KnowGraphGo/adapter/clinical/adapter.go` |
| P2-07 | **God File：`report_generator.py`（64KB）** | Clinical | `report_generator.py` |
| P2-08 | `ClinicalDecisionEngine` 完全無 Trace 記錄 | Engine | `clinical_decision_engine.py` |
| P2-09 | Migration 017 trace_id UNIQUE 約束問題（類似 019 未修復） | Migration | `migrations/versions/017` |
| P2-10 | 缺少 KnowGraphGo CLI 端到端整合測試 | Tests | - |
| P2-11 | 缺少 TreatmentPlanStateMachine 獨立單元測試 | Tests | - |

---

## 4. Code Smell（程式碼異味）

| 類別 | 異味描述 | 嚴重程度 | 檔案路徑 | 行號參考 |
|------|---------|---------|---------|---------|
| **God Class** | `TreatmentPlanService` 單一檔案 57KB，同時負責 Orchestration、Persistence、Event Creation、Version Management | 🔴 Critical | `src/backend/services/treatment_plan_service.py` | 全檔案（~1,400 行） |
| **God Class** | `ClinicalAdapter` 約 40KB，包含 6 個大型 Mapper 函數 | 🔴 Critical | `KnowGraphGo/adapter/clinical/adapter.go` | 全檔案（~1,214 行） |
| **God File** | `report_generator.py` 約 64KB，單一檔案處理多種報表類型 | 🔴 Critical | `src/backend/clinical/report_generator.py` | 全檔案（~1,600 行） |
| **God Class** | `RecommendationEngine` + `DrugRanker` + `EvidenceAggregator` 混合在同一檔案 | 🟡 Major | `src/backend/clinical/recommendation_engine.py` | 全檔案（~780 行） |
| **God Class** | `TumorBoardConsensusService` 約 34KB | 🟡 Major | `src/backend/services/tumor_board_service.py` | 全檔案（~850 行） |
| **Long Function** | `mapTreatmentPlanEvent()` 約 320 行 | 🟡 Major | `KnowGraphGo/adapter/clinical/adapter.go` | 783-1103 |
| **Long Function** | `_persist_plan()` 約 158 行 | 🟡 Major | `src/backend/services/treatment_plan_service.py` | 818-976 |
| **Long Function** | `mapRecommendationEvent()` 約 159 行 | 🟡 Major | `KnowGraphGo/adapter/clinical/adapter.go` | 233-392 |
| **Long Function** | `mapConsensusEvent()` 約 212 行 | 🟡 Major | `KnowGraphGo/adapter/clinical/adapter.go` | 539-751 |
| **Long Function** | `create_plan()` 約 120 行 | 🟡 Major | `src/backend/services/treatment_plan_service.py` | 253-376 |
| **Domain 依賴基礎設施** | Domain 層所有 Model 繼承 SQLAlchemy `DBBase`、使用 `Column`/`String` 等 ORM 類型 | 🔴 Critical | `src/backend/domain/*.py` | 全部 26 個檔案 |
| **跨層依賴反向** | Service 層 `from src.backend.api.v1.recommendation import RecommendationResponse` | 🔴 Critical | `src/backend/services/recommendation_service.py` | 248 |
| **Schema 碎片化** | 三套獨立且不相容的 Trace 系統 | 🟡 Major | `calculation_trace.py`、`treatment_plan_trace.py`、`decision_thread.py` | 全域 |
| **Magic String** | `status` 欄位使用 `String(32)` 而非 Enum | 🟡 Major | 多個 Domain Model 檔案 | 分散 |
| **Copy-Paste** | Patient Stub 創建在 5 個 Mapper 中重複 | 🟡 Major | `KnowGraphGo/adapter/clinical/adapter.go` | 280-291, 438-448, 593-603, 831-841 |
| **Copy-Paste** | Evidence ID 去重邏輯在 3 個 Mapper 中重複 | 🟢 Minor | `KnowGraphGo/adapter/clinical/adapter.go` | 306-316, 491-502, 705-716 |
| **不一致的錯誤處理** | API 層存在三種不同的 Error Response 格式 | 🟡 Major | `clinical.py`、`patients.py`、`evidence.py` | 分散 |
| **Hard Code** | `buildProvenance` 始終返回 `ProvenanceImported` | 🟡 Major | `KnowGraphGo/adapter/clinical/adapter.go` | 110-112 |
| **Private API 呼叫** | `self._rule_set._get_top_drug_name()` 呼叫私有方法 | 🟢 Minor | `src/backend/clinical/clinical_decision_engine.py` | 209 |
| **無 Trace 的 Engine** | `ClinicalDecisionEngine` 完全無 Trace 記錄 | 🟡 Major | `src/backend/clinical/clinical_decision_engine.py` | 全檔案 |
| **狀態機未測試** | `TreatmentPlanStateMachine` 4KB 缺乏獨立單元測試 | 🟢 Minor | `src/backend/clinical/treatment_plan_state_machine.py` | 全檔案 |

---

## 5. Duplicate Code（重複程式碼）

### 5.1 Patient Stub 建立（Go Adapter）

**檔案：** `KnowGraphGo/adapter/clinical/adapter.go`

以下位置重複相同的 Patient Stub 建立模式（建立 `EntityKindPatient` 實體並設定基礎屬性）：

| 出現位置（行號） | Mapper 函數 | From Entity |
|-----------------|------------|-------------|
| 280-291 | `mapPatientEvent` | Patient Event 自身 |
| 438-448 | `mapRecommendationEvent` | Recommendation |
| 593-603 | `mapClinicalDecisionEvent` | Clinical Decision |
| 831-841 | `mapConsensusEvent` | Consensus |

**重複模式**：每個 Mapper 都建立相同的 Patient Stub，僅關聯的 From Entity 不同。

**建議**：提取 `stubPatient(entityID, patientID)` 輔助方法（L1）。

### 5.2 Evidence Stub 建立（Go Adapter）

**檔案：** `KnowGraphGo/adapter/clinical/adapter.go`

| 出現位置（行號） | Mapper 函數 |
|-----------------|------------|
| 360-371 | `mapRecommendationEvent` |
| 505-516 | `mapClinicalDecisionEvent` |
| 719-730 | `mapConsensusEvent` |
| 1008-1019 | `mapTreatmentPlanEvent` |

**重複模式**：4 處重複的 Evidence Stub 建立（`EntityKindEvidence`），屬性設定完全相同。

### 5.3 Evidence ID 去重邏輯（Go Adapter）

**檔案：** `KnowGraphGo/adapter/clinical/adapter.go`

| 出現位置（行號） | Mapper 函數 |
|-----------------|------------|
| 306-316 | `mapRecommendationEvent` |
| 491-502 | `mapClinicalDecisionEvent` |
| 705-716 | `mapConsensusEvent` |

**重複模式**：相同的 `dedup` 模式——將 `payload.EvidenceIDs` 和 `payload.EvidenceReferences` 合併去重。

**建議**：提取 `dedupEvidenceIDs(evidenceIDs, evidenceReferences)` 輔助函數（L2）。

### 5.4 Upstream Data Loading 重複（Python Service）

**檔案：** `src/backend/services/treatment_plan_service.py`

`create_plan()` 和 `_create_revision()` 都從 Repository 加載 Recommendation、Clinical Decision、Consensus 的上游資料，邏輯高度相似。

### 5.5 Relation Provenance 設置（Go Adapter）

所有 Relation 的 Properties 設置完全相同（`relationProps(event)`），可提取統一 Builder。

---

## 6. Refactor List（重構清單）

### HIGH（架構性問題，可能導致 Bug 或無法維護）

| ID | 重構項目 | 受影響檔案 | 預估工時 | 說明 |
|----|---------|-----------|---------|------|
| **R-H1** | **分離 Domain/ORM 模型**——將 `*Model` 類移到 `database/models.py`，在 `domain/` 中建立純 Python 領域模型 | `src/backend/domain/*.py`（26 個檔案） | 40h+ | 最優先的結構性重構，需要重新設計 Repository 層做 ORM↔Domain 轉換 |
| **R-H2** | **修復 Service→API 反向依賴**——將 `RecommendationResponse` 提取到共享 `schemas/` 包 | `src/backend/services/recommendation_service.py:248` | 2h | 簡單但重要的依賴方向修正 |
| **R-H3** | **統一事務策略**——`BaseRepository.create/update/delete` 改爲 `flush()`，審計所有 `commit()` 子類 | `src/backend/repositories/base.py` + 5 個子類 | 8h | 消除資料不一致風險 |
| **R-H4** | **重構 Outbox Repository**——拆分 CRUD Repository 和 Outbox Processor Service | `src/backend/repositories/clinical_graph_outbox_repo.py` | 8h | 業務邏輯應回歸 Service 層 |
| **R-H5** | **補上 Python ID Factory 缺少的 5 個方法**——`treatment_plan_id()`、`treatment_phase_id()`、`treatment_item_id()`、`monitoring_id()`、`safety_rule_id()` | `src/backend/clinical_graph/id_factory.py` | 2h | 跨語言 ID 一致性 |
| **R-H6** | **改進 `buildProvenance`**——根據 EventType 返回不同的 Provenance 值 | `KnowGraphGo/adapter/clinical/adapter.go:110-112` | 3h | 圖譜資料來源可區分性 |
| **R-H7** | **修復 `RecommendationEngine.run()` 純函數違規**——將 I/O 和狀態管理移到呼叫方 | `src/backend/clinical/recommendation_engine.py` | 12h | 將 Collector 和 TraceManager 移至 Service 層 |

### MEDIUM（可改進但非緊急）

| ID | 重構項目 | 受影響檔案 | 預估工時 | 說明 |
|----|---------|-----------|---------|------|
| **R-M1** | **拆分 `TreatmentPlanService`**——將 Persistence、Upstream Loading、Event Creation 分別提取 | `src/backend/services/treatment_plan_service.py` | 16h | 57KB → 多個職責清晰的類別 |
| **R-M2** | **拆分 `ClinicalAdapter`**——將 6 個大型 Mapper 中的 Stub 創建、Relation 創建提取爲輔助方法 | `KnowGraphGo/adapter/clinical/adapter.go` | 8h | 40KB → 可維護的 Adapter |
| **R-M3** | **拆分 `mapTreatmentPlanEvent`**——拆分爲 `mapPhases()`、`mapMonitoring()`、`mapSafetyRules()` | `KnowGraphGo/adapter/clinical/adapter.go:783-1103` | 4h | 320 行函數 |
| **R-M4** | **統一 Trace Schema**——定義通用 `TraceStep` 模型，在所有 Engine 中統一使用 | `calculation_trace.py`、`treatment_plan_trace.py`、`decision_thread.py` | 12h | 消除三套獨立 Trace |
| **R-M5** | **Worker 添加 Heartbeat 機制**——防止 Phase 2 崩潰導致事件卡死 | `src/backend/clinical_graph/worker.py:60-84` | 3h | 恢復卡住的 Processing 事件 |
| **R-M6** | **統一 API Error Response 格式**——定義全局 `ErrorResponse` 模型 | `src/backend/api/v1/*.py` | 6h | 消除三種 Error 格式 |
| **R-M7** | **統一狀態欄位使用 SAEnum**——替換所有 `String(32)` 狀態欄位 | 多個 Domain Model 檔案 | 6h | 資料庫層類型安全 |
| **R-M8** | **添加樂觀鎖版本控制**——爲 Aggregate Root Model 添加 `version_id` | 全部 Model | 6h | 並發寫入衝突偵測 |
| **R-M9** | **補上 Patient Outbox 事件**——在 Patient 創建/更新服務中添加 Events | `src/backend/services/patient_service.py`（如存在） | 4h | 完整的 Digital Thread |
| **R-M10** | **添加 Variant/Drug Event 處理**——至少提供 Stub 實體映射 | `KnowGraphGo/adapter/clinical/adapter.go:66-89` | 4h | 完整的 Adapter 覆蓋 |

### LOW（程式碼風格或微小改進）

| ID | 重構項目 | 受影響檔案 | 預估工時 | 說明 |
|----|---------|-----------|---------|------|
| **R-L1** | 提取 Patient Stub Factory——消除 4 處重複 | `KnowGraphGo/adapter/clinical/adapter.go` | 2h | 消除 Copy-Paste |
| **R-L2** | 提取 Evidence ID 去重輔助函數 | `KnowGraphGo/adapter/clinical/adapter.go` | 1h | 消除重複邏輯 |
| **R-L3** | 爲 `ClinicalDecisionEngine` 添加 Trace 記錄 | `src/backend/clinical/clinical_decision_engine.py` | 4h | 補全 Trace 覆蓋 |
| **R-L4** | 補充 Repository 型別註解——統一使用 `AsyncSession` | 17 個 Repository 檔案 | 3h | 型別安全 |
| **R-L5** | 引入 `@transactional` 裝飾器消除手動 try/commit 重複模式 | 全部 4 個 Service | 4h | 減少重複程式碼 |
| **R-L6** | 修正 Migration 015/022/025 的 Downgrade 不冪等問題 | `migrations/versions/015`、`022`、`025` | 6h | Migration 可靠的升降級 |
| **R-L7** | 統一 HTTP Status Code——POST → 201、部分 PUT → PATCH | `src/backend/api/v1/recommendation.py:125`、`cases.py:131` | 2h | RESTful 規範 |
| **R-L8** | 爲所有 POST 端點添加 409 Conflict 處理 | `src/backend/api/v1/patients.py:33-38` 等 | 3h | 恰當的錯誤狀態碼 |
| **R-L9** | 統一代碼中的 Section 標記和註釋語言 | `treatment_plan_service.py`、`main_test.go` | 2h | 編碼風格一致性 |
| **R-L10** | 補上 Missing Unit Tests（StateMachine、Trace、Outbox 邊界案例） | 對應測試檔案 | 8h | 提升測試覆蓋 |

---

## 7. Risk List（風險清單）

| ID | 風險描述 | 嚴重程度 | 可能性 | 影響範圍 | 緩解措施 |
|----|---------|---------|-------|---------|---------|
| **RSK-01** | **Domain 層 ORM 耦合導致架構僵化**——未來更換 ORM 或資料庫需要改動全部 26 個 Domain 檔案 | 🔴 Critical | High | 全部 Domain 層 | 立即執行 R-H1（分離 Domain/ORM） |
| **RSK-02** | **BaseRepository 預設 commit() 導致部分更新**——Service 層多步驟操作中，若第一步 commit 成功後後續失敗，資料處於不一致狀態 | 🔴 Critical | Medium | 全部依賴 BaseRepository 的操作 | 立即執行 R-H3（統一事務策略） |
| **RSK-03** | **跨語言 ID 不一致導致圖譜資料損毀**——Python ID Factory 缺少 5 個方法，Go 端無法生成一致的確定性 ID | 🔴 Critical | High | Treatment Plan 圖譜資料 | 立即執行 R-H5（補上 ID Factory 方法） |
| **RSK-04** | **Patient 資料永遠不會投射到知識圖譜**——Python 端完全沒有發出 Patient Outbox 事件 | 🔴 Critical | Certain | Patient 知識圖譜 | 執行 R-M9（補上 Patient 事件） |
| **RSK-05** | **Trace 系統碎片化導致除錯困難**——三套不相容的 Trace 無法提供跨 Engine 的端到端可追蹤性 | 🟡 High | High | 全部 Engine + Service | 執行 R-M4（統一 Trace Schema） |
| **RSK-06** | **Worker Phase 2 崩潰導致事件永久卡死**——缺少 Heartbeat 機制，Processing 事件無法自動恢復 | 🟡 High | Medium | Outbox Worker | 執行 R-M5（添加 Heartbeat） |
| **RSK-07** | **API Error Response 不一致導致前端整合困難**——前端無法以統一邏輯處理錯誤 | 🟡 High | High | 全部 API 消費者 | 執行 R-M6（統一 Error Schema） |
| **RSK-08** | **Migration 不冪等導致生產環境升降級失敗**——015/022/025 的 Downgrade 在 SQLite 下無法正確還原 | 🟡 High | Low | 生產資料庫 Migration | 執行 R-L6（修正 Migration） |
| **RSK-09** | **God Class 難以維護和測試**——`TreatmentPlanService`（57KB）修改風險高，新人理解成本大 | 🟡 High | Certain | Treatment Plan 功能 | 執行 R-M1（拆分 God Service） |
| **RSK-10** | **缺少樂觀鎖導致並發寫入遺失更新**——多個請求同時修改同一 Aggregate 時，後寫入者會覆蓋前寫入者的修改 | 🟡 High | Medium | 全部 Aggregate Root | 執行 R-M8（添加樂觀鎖） |
| **RSK-11** | **Recommendation Engine 的 Exception 靜默吞沒**——`except Exception` 僅記錄日誌後繼續，可能隱藏 Pipeline 錯誤 | 🟡 High | Medium | Recommendation Pipeline | 執行 R-H7（重構 Engine） |
| **RSK-12** | **KnowGraphGo 缺少端到端整合測試**——目前所有測試使用 Mock Client，真實 Graph Projection 路徑未驗證 | 🟡 High | High | 全部 Graph 功能 | 補上 CLI 端到端測試 |
| **RSK-13** | **臨床決策 Engine 無 Trace**——決策過程無法追溯，稽核和除錯困難 | 🟡 Medium | High | Clinical Decision 功能 | 執行 R-L3（添加 Trace） |
| **RSK-14** | **Aggregate 邊界模糊導致跨 Aggregate 直接參考**——`TreatmentPlanModel` 直接 FK 參考 4 個不同 Aggregate | 🟡 Medium | Medium | Aggregate 一致性 | 執行 P2-01 相關 Refactor |

---

## 8. Phase 3F 建議（下一階段的具體建議）

根據本次 Review 發現，建議 Phase 3F 按以下優先級處理：

### 必須完成（Phase 3F 阻斷項）

1. **P0-01: Domain/ORM 分離（R-H1）**
   - 將現有 `*Model` 類遷移至 `database/models.py` 或 `infrastructure/orm/`
   - 在 `domain/` 中建立純 Python `@dataclass` 領域模型
   - 調整 Repository 層實作 ORM↔Domain 轉換
   - **這是 Phase 3F 最核心的架構改善，其他所有重構建議都以此爲前提**

2. **P0-05: 補上 Python ID Factory 缺少方法（R-H5）**
   - 新增 `treatment_plan_id()`、`treatment_phase_id()`、`treatment_item_id()`、`monitoring_id()`、`safety_rule_id()`
   - 更新 ID Parity 測試

3. **P1-06: 補上 Patient Outbox 事件（R-M9）**
   - 在 Patient 創建和更新服務中調用 `ClinicalGraphEventService.create_event()`

### 高度建議（Phase 3F 應完成）

4. **P0-03: 統一事務策略（R-H3）**
   - `BaseRepository` 改爲 `flush()` 模式
   - 審計所有 `commit()` 子類

5. **P1-05: 統一 Trace Schema（R-M4）**
   - 定義通用 `TraceStep` 模型
   - 在所有 Engine 中統一使用

6. **P0-06: 改進 buildProvenance（R-H6）**
   - 根據 EventType 返回不同 Provenance 值

7. **P0-02: 修復 Service→API 反向依賴（R-H2）**
   - 提取共享 Schema

### 若有餘力（Phase 3F 或 3G）

8. **R-M1: 拆分 TreatmentPlanService**
9. **R-M5: Worker Heartbeat 機制**
10. **R-M6: 統一 API Error Response**
11. **P1-02: 統一狀態欄位使用 SAEnum**

---

## 9. P0 / P1 / P2 改善清單

### P0（立即修復，Blocking）

| 優先序 | ID | 問題 | 檔案 | 行號 | 建議做法 | 預估工時 |
|-------|----|------|------|------|---------|---------|
| **1** | P0-01 | Domain 層全部 26 個檔案混入 SQLAlchemy ORM 依賴 | `src/backend/domain/*.py` | 全部 | 分離 ORM 模型與純領域模型 | 40h+ |
| **2** | P0-05 | Python ID Factory 缺少 5 個治療計劃方法 | `src/backend/clinical_graph/id_factory.py` | 全檔案 | 補上 `treatment_plan_id()` 等 5 個方法 | 2h |
| **3** | P0-03 | BaseRepository 預設 commit() 導致事務邊界下沉 | `src/backend/repositories/base.py` | 29,73,82 | 改爲 flush()，審計子類 | 8h |
| **4** | P0-04 | Outbox Repository 混入大量業務邏輯 | `src/backend/repositories/clinical_graph_outbox_repo.py` | 全檔案 | 拆分 CRUD 與業務邏輯 | 8h |
| **5** | P0-06 | buildProvenance 硬編碼爲 ProvenanceImported | `KnowGraphGo/adapter/clinical/adapter.go` | 110-112 | 根據事件類型回傳不同 Provenance | 3h |
| **6** | P0-02 | Service 層反向依賴 API 層 | `src/backend/services/recommendation_service.py` | 248 | 提取共享 Schema | 2h |

### P1（短期改善）

| 優先序 | ID | 問題 | 檔案 | 行號參考 | 建議做法 | 預估工時 |
|-------|----|------|------|---------|---------|---------|
| **1** | P1-06 | Patient Outbox 事件完全缺失 | 無對應服務調用 | - | 在 Patient 操作中添加 Event | 4h |
| **2** | P1-05 | 三套獨立 Trace 系統 | `calculation_trace.py`、`treatment_plan_trace.py`、`decision_thread.py` | 全域 | 統一 Trace Schema 和 Manager | 12h |
| **3** | P1-01 | RecommendationEngine.run() 嚴重違反 Pure Function | `src/backend/clinical/recommendation_engine.py` | 482-715 | 將 I/O 和狀態管理移至呼叫方 | 12h |
| **4** | P1-07 | API Error Response 格式不統一 | `clinical.py`、`patients.py`、`evidence.py` | 分散 | 定義全局 ErrorResponse 模型 | 6h |
| **5** | P1-08 | HTTP Status Code 不一致 | `recommendation.py:125`、`cases.py:131` | 分散 | 統一 POST→201、語義修正 | 2h |
| **6** | P1-09 | Migration SQLite/PostgreSQL 不一致、不冪等 | `migrations/versions/015`、`022`、`025` | 分散 | 修正 Downgrade 邏輯 | 6h |
| **7** | P1-10 | Adapter 缺少 Variant/Guideline/Drug 事件處理 | `KnowGraphGo/adapter/clinical/adapter.go` | 66-89 | 添加 Stub 映射 | 4h |
| **8** | P1-11 | Worker 缺少 Heartbeat 機制 | `src/backend/clinical_graph/worker.py` | 60-84 | 添加 Heartbeat 更新 | 3h |
| **9** | P1-02 | ORM 狀態欄位使用 String(32) 而非 SAEnum | 多個 Domain Model 檔案 | 分散 | 替換爲 SAEnum | 6h |
| **10** | P1-03 | 缺少樂觀鎖版本控制 | 全部 Model | 全域 | 添加 version_id 欄位 | 6h |
| **11** | P1-04 | Repository 型別註解不完整 | 17 個 Repository 檔案 | `__init__` 等 | 補上 `AsyncSession` 型別 | 3h |

### P2（長期追蹤）

| 優先序 | ID | 問題 | 檔案 | 建議做法 | 預估工時 |
|-------|----|------|------|---------|---------|
| **1** | P2-05 | God Class：TreatmentPlanService（57KB） | `src/backend/services/treatment_plan_service.py` | 拆分爲多個職責清晰的類別 | 16h |
| **2** | P2-06 | God Class：ClinicalAdapter（40KB） | `KnowGraphGo/adapter/clinical/adapter.go` | 提取輔助方法，拆分大型 Mapper | 8h |
| **3** | P2-07 | God File：report_generator.py（64KB） | `src/backend/clinical/report_generator.py` | 按報表類型拆分 | 12h |
| **4** | P2-08 | ClinicalDecisionEngine 完全無 Trace | `src/backend/clinical/clinical_decision_engine.py` | 添加 Trace 記錄 | 4h |
| **5** | P2-01 | Aggregate 邊界不清晰 | 全域 Domain | 定義 Aggregate Root 標記模式 | 4h |
| **6** | P2-02 | 缺少顯式 ValueObject 模式 | 全域 Domain | 定義 `@dataclass(frozen=True)` 值物件 | 4h |
| **7** | P2-09 | Migration 017 trace_id UNIQUE 約束問題 | `migrations/versions/017` | 添加複合 UNIQUE(trace_id, step_order) | 2h |
| **8** | P2-10 | 缺少 KnowGraphGo CLI 端到端整合測試 | 測試檔案 | 建立完整 Graph Projection 整合測試 | 8h |
| **9** | P2-11 | 缺少 TreatmentPlanStateMachine 單元測試 | 測試檔案 | 爲 4KB 狀態機補上獨立測試 | 3h |
| **10** | P2-03 | Engine 呼叫私有 API | `clinical_decision_engine.py:209` | 改爲公開方法或重構呼叫方式 | 2h |
| **11** | P2-04 | 手動 try/commit 重複模式 | 全部 4 個 Service | 引入 `@transactional` 裝飾器 | 4h |
| **12** | P2-12 | 重複程式碼（Stub 建立、去重邏輯） | `KnowGraphGo/adapter/clinical/adapter.go` | 提取輔助函數消除 Copy-Paste | 3h |

---

## 10. Domain Architecture — 逐檔案審查表

### 10.1 總覽

`src/backend/domain/` 目錄下共 **26 個 Python 檔案**，承載三種截然不同的職責：

1. **SQLAlchemy ORM 模型**（`*Model(DBBase)`）— 資料庫持久化
2. **Pydantic Schema**（`*Create/*Response/*Request(BaseModel)`）— API 請求/回應
3. **Enum/ValueObject**（`class *(str, enum.Enum)`）— 列舉與常數

### 10.2 逐檔案審查表

| 檔案名稱 | 包含類別 | 分類 | 有明確 ID | ORM 依賴 | API/HTTP 混入 | 建議 |
|---------|---------|------|:--------:|:--------:|:------------:|------|
| `__init__.py` | Package re-exports | Package | - | - | - | 部分 Enum 未 re-export（見下文） |
| `analysis_run.py` | `AnalysisRunModel` + `AnalysisRunCreate/Response` | Entity + **API Schema** | ✅ `CompatUUID PK` | ✅ sqlalchemy `Column`/`String`/`ForeignKey` | ✅ `AnalysisRunCreate`/`Response`(Pydantic) | 拆分 Schema 到 `schemas/` |
| `audit_log.py` | `AuditLogModel` + `AuditLogEntry` | Entity + **API Schema** | ✅ `CompatUUID PK` | ✅ sqlalchemy `Column`/`String`/`ForeignKey` | ✅ `AuditLogEntry`(Pydantic) | 拆分 Schema 到 `schemas/` |
| `cancer_case.py` | `CancerCaseModel` + `CancerCaseCreate/Update/Response/ListResponse` | Aggregate + **API Schema** | ✅ `CompatUUID PK` | ✅ sqlalchemy `Column`/`String`/`ForeignKey` | ✅ 4 個 Pydantic Schema | 拆分 Schema 到 `schemas/` |
| `case_acl.py` | `CaseACLModel` + `CaseRole` + `CaseACLCreate/Response` + `CasePermissionCheck` | Entity + ValueObject + **API Schema** | ✅ `CompatUUID PK` | ✅ sqlalchemy `Column`/`String`/`ForeignKey` | ✅ `CaseACLCreate`/`Response`/`PermissionCheck`(Pydantic) | 拆分 Schema 到 `schemas/` |
| `clinical_decision.py` | `ClinicalDecisionModel` + `ClinicalDecisionTraceModel` | Entity + Trace | ✅ `CompatUUID PK` | ✅ sqlalchemy `Column`/`String`/`ForeignKey` | ❌ 無 Pydantic | 純 ORM 模型，可保留但在新架構中需分離 |
| `clinical_graph_outbox.py` | `ClinicalGraphOutboxModel` | Entity（Outbox） | ✅ `CompatUUID PK` | ✅ sqlalchemy `Column`/`String`(使用 `Base` 非 `DBBase`) | ❌ 無 Pydantic | `Base` vs `DBBase` 不一致，統一基底類別 |
| `clinical_trial.py` | `ClinicalTrialModel` | Entity | ✅ `CompatUUID PK` | ✅ sqlalchemy `Column`/`String`/`JSON` | ❌ 無 Pydantic | 純 ORM 模型 |
| `consent.py` | `ConsentModel` + `ConsentCreate/Response` | Entity + **API Schema** | ✅ `CompatUUID PK` | ✅ sqlalchemy `Column`/`String`/`ForeignKey` | ✅ `ConsentCreate`/`Response`(Pydantic) | 拆分 Schema 到 `schemas/` |
| `drug.py` | `DrugModel` + `DrugTargetModel` + `DrugCreate/Response` | Entity + **API Schema** | ✅ `CompatUUID PK` | ✅ sqlalchemy `Column`/`String`/`ForeignKey` | ✅ `DrugCreate`/`Response`(Pydantic) | 拆分 Schema 到 `schemas/` |
| `drug_candidate.py` | `DrugCandidateModel` + `DrugCandidateResponse/ListResponse` | Entity + **API Schema** | ✅ `CompatUUID PK` | ✅ sqlalchemy `Column`/`String`/`ForeignKey` | ✅ `DrugCandidateResponse`/`ListResponse`(Pydantic) | 拆分 Schema 到 `schemas/` |
| `enums.py` | 32 個 Enum 類別 | **ValueObject**（純 Enum） | ❌ 無 PK | ❌ 無 ORM 匯入 | ❌ 無 API 依賴 | ✅ **唯一純淨的 Domain 檔案**，保持不變 |
| `evidence.py` | `EvidenceModel` + `EvidenceCreate/Response/SearchResult` | Entity + **API Schema** | ✅ `CompatUUID PK` | ✅ sqlalchemy `Column`/`String`/`ForeignKey` | ✅ `EvidenceCreate`/`Response`/`SearchResult`(Pydantic) | 拆分 Schema 到 `schemas/` |
| `gene.py` | `GeneModel` + `ProteinModel` + `PathwayModel` + `GeneCreate/Response` | Entity + **API Schema** | ✅ `CompatUUID PK` | ✅ sqlalchemy `Column`/`String`/`ForeignKey` | ✅ `GeneCreate`/`Response`(Pydantic) | 拆分 Schema 到 `schemas/` |
| `patient.py` | `PatientModel` + `PatientCreate/Update/Response/ListResponse` | Aggregate + **API Schema** | ✅ `CompatUUID PK` | ✅ sqlalchemy `Column`/`String`/`ForeignKey` | ✅ `PatientCreate`/`Update`/`Response`/`ListResponse`(Pydantic) | 拆分 Schema 到 `schemas/` |
| `publication.py` | `PublicationModel` | Entity | ✅ `CompatUUID PK` | ✅ sqlalchemy `Column`/`String`/`JSON` | ❌ 無 Pydantic | 純 ORM 模型 |
| `recommendation.py` | `RecommendationModel` + `RecommendationTraceModel` + `RecommendationTraceStepModel` | Entity + Trace | ✅ `CompatUUID PK` | ✅ sqlalchemy `Column`/`String`/`ForeignKey` | ❌ 無 Pydantic | 純 ORM 模型，可保留 |
| `report.py` | `ReportModel` | Entity | ✅ `CompatUUID PK` | ✅ sqlalchemy `Column`/`String`/`ForeignKey` | ❌ 無 Pydantic | 純 ORM 模型 |
| `sequencing.py` | `SequencingTestModel` + `SequencingTestCreate/Response` | Entity + **API Schema** | ✅ `CompatUUID PK` | ✅ sqlalchemy `Column`/`String`/`ForeignKey` | ✅ `SequencingTestCreate`/`Response`(Pydantic) | 拆分 Schema 到 `schemas/` |
| `specimen.py` | `SpecimenModel` + `SpecimenCreate/Update/Response` | Entity + **API Schema** | ✅ `CompatUUID PK` | ✅ sqlalchemy `Column`/`String`/`ForeignKey` | ✅ `SpecimenCreate`/`Update`/`Response`(Pydantic) | 拆分 Schema 到 `schemas/` |
| `treatment_plan.py` | `TreatmentPlanModel` + `TreatmentPhaseModel` + `TreatmentItemModel` + `TreatmentMonitoringModel` + `TreatmentSafetyRuleModel` + `TreatmentPlanTraceModel` | **Aggregate Root** + Sub-Entities + Trace | ✅ `CompatUUID PK`（6 個模型） | ✅ sqlalchemy `Column`/`String`/`ForeignKey`/`JSON` | ❌ 無 Pydantic | 最大的 Aggregate（6 個 ORM 類別），重構時注意邊界 |
| `tumor_board.py` | `TumorBoardConsensusModel` + `TumorBoardOpinionModel` + `TumorBoardConsensusTraceModel` | Entity + Trace | ✅ `CompatUUID PK`（3 個模型） | ✅ sqlalchemy `Column`/`String`/`ForeignKey` | ❌ 無 Pydantic | 純 ORM 模型，可保留 |
| `uploaded_file.py` | `UploadedFileModel` + `UploadedFileCreate/Response` | Entity + **API Schema** | ✅ `CompatUUID PK` | ✅ sqlalchemy `Column`/`String`/`ForeignKey` | ✅ `UploadedFileCreate`/`Response`(Pydantic) | 拆分 Schema 到 `schemas/` |
| `user.py` | `UserModel` + `TokenBlacklistModel` + `UserCreate/Response` + `TokenResponse` + `LoginRequest`/`RefreshRequest`/`LogoutRequest` | Entity + **API Schema**（含 Login） | ✅ `CompatUUID PK` | ✅ sqlalchemy `Column`/`String`/`Boolean` | ✅ 7 個 Pydantic Schema（含登入/登出請求） | **Login/Logout 完全不該在 Domain 層**，緊急拆分 |
| `variant.py` | `VariantModel` + `VariantImport`/`VariantImportBatch` + `VariantResponse`/`ListResponse` | Entity + **API Schema** | ✅ `CompatUUID PK` | ✅ sqlalchemy `Column`/`String`/`ForeignKey` | ✅ `VariantImport`/`ImportBatch`/`Response`/`ListResponse`(Pydantic) | 拆分 Schema 到 `schemas/` |
| `visualization_graph.py` | `GraphNode` + `GraphEdge` + `VisualizationGraph` + `GraphAnalysisResponse` | **ViewModel**（純 Pydantic） | ❌ 無 PK（無 ORM） | ❌ 無 ORM 匯入 | ✅ 全部爲 API Response Schema | 移至 `schemas/visualization.py`，不該在 `domain/` |

### 10.3 關鍵發現

| 發現項目 | 數量 | 比例 |
|---------|:---:|:----:|
| 檔案總數 | 26 | 100% |
| 包含 ORM 依賴的檔案 | 24 | 92.3% |
| 混入 API Schema 的檔案 | 16 | 61.5% |
| 純 ORM 無 Pydantic 的檔案 | 8 | 30.8% |
| 純 Enum/ValueObject 的檔案 | 1（`enums.py`） | 3.8% |
| 純 ViewModel 的檔案 | 1（`visualization_graph.py`） | 3.8% |
| 基底類別不一致（`Base` vs `DBBase`） | 1（`clinical_graph_outbox.py`） | 3.8% |
| 包含業務無關請求（Login/Logout）的檔案 | 1（`user.py`） | 3.8% |
| 未在 `__init__.py` 中 re-export 的 Enum | 9（`ConsequenceEnum`/`VCFStatusEnum`/`NormalizationMethodEnum`/`NormalizationResultEnum`/`NormalizationSemanticsEnum`/`GenomeBuildConfidenceEnum`/`UploadDuplicateStrategyEnum`/`UploadEligibilityEnum`/`ConsentStatusEnum`） | 28.1% of enums |

### 10.4 總結建議

1. **P0**：建立 `schemas/` 目錄，將 16 個檔案中的 Pydantic Schema 遷移出去，Domain 層只保留純 ORM 模型
2. **P0**：將 `user.py` 中的 `LoginRequest`/`LogoutRequest`/`RefreshRequest`/`TokenResponse` 移出 Domain 層
3. **P1**：統一基底類別 — 全部使用 `DBBase`，消除 `Base` 的例外用法
4. **P2**：補上 `__init__.py` 中遺漏的 9 個 Enum 的 re-export
5. **P2**：`visualization_graph.py` 整檔案移至 `schemas/`，不屬於 Domain 層

### 10.5 Domain State/Status 字段審查

本節逐一檢視 `src/backend/domain/` 下所有具有「狀態」語意的欄位，評估其使用 Enum 還是 String，以及是否有明確的 State Transition 定義。

| 檔案 | Model 類別 | Status 欄位 | 類型 | 使用 Enum？ | State Transition 定義？ | 風險 |
|------|-----------|------------|:----:|:----------:|:---------------------:|:----:|
| `analysis_run.py` | `AnalysisRunModel` | `status` | `SAEnum(AnalysisStatusEnum)` | ✅ `AnalysisStatusEnum` | ✅ 隱含（PENDING→RUNNING→COMPLETED/FAILED） | 🟢 低 |
| `clinical_decision.py` | `ClinicalDecisionModel` | `status` | `String(32)` (default="active") | ❌ String | ❌ 無定義 | 🟡 中 — Magic String，無法在 DB 層約束 |
| `clinical_graph_outbox.py` | `ClinicalGraphOutboxModel` | `status` | `String(32)` (default="pending") | ❌ String | ❌ 無定義 | 🟡 中 — PENDING→PROCESSING→COMPLETED/FAILED 僅在程式碼中隱含 |
| `clinical_trial.py` | `ClinicalTrialModel` | `status` | `String(64)` | ❌ String | ❌ 無定義 | 🟢 低 — 僅爲資訊欄位 |
| `drug.py` | `DrugModel` | `approval_status` | `String(64)` | ❌ String | ❌ 無定義 | 🟢 低 — 僅爲資訊欄位 |
| `drug_candidate.py` | `DrugCandidateModel` | `approval_status` | `String(64)` | ❌ String | ❌ 無定義 | 🟢 低 — 僅爲資訊欄位 |
| `patient.py` | `PatientModel` | `consent_status` | `SAEnum(ConsentStatusEnum)` | ✅ `ConsentStatusEnum` | ✅ 隱含（PENDING→GIVEN/DENIED/WITHDRAWN） | 🟢 低 |
| `recommendation.py` | `RecommendationModel` | `status` | `String(32)` (default="pending") | ❌ String | ❌ 無定義 | 🟡 中 — PENDING→COMPLETED/FAILED 無 DB 層約束 |
| `treatment_plan.py` | `TreatmentPlanModel` | `plan_status` | `String(32)` (default="draft") | ❌ String | ✅ `TreatmentPlanStateMachine` 定義 transition | 🟡 中 — 雖有狀態機但 DB 層仍爲 String，無 FK 或 Enum 約束 |
| `treatment_plan.py` | `TreatmentPhaseModel` | `status` | `String(32)` (default="planned") | ❌ String | ❌ 無定義 | 🟡 中 |
| `treatment_plan.py` | `TreatmentItemModel` | `status` | `String(32)` (default="planned") | ❌ String | ❌ 無定義 | 🟡 中 |
| `tumor_board.py` | `TumorBoardConsensusModel` | `consensus_status` | `String(32)` (default="pending") | ❌ String | ❌ 無定義 | 🟡 中 — 雖有 `ConsensusStatus` Enum 定義但未被 ORM 使用 |
| `uploaded_file.py` | `UploadedFileModel` | `upload_status` | `SAEnum(UploadStatusEnum)` | ✅ `UploadStatusEnum` | ✅ 隱含（UPLOADING→UPLOADED/FAILED） | 🟢 低 |
| `uploaded_file.py` | `UploadedFileModel` | `validation_status` | `SAEnum(ValidationStatusEnum)` | ✅ `ValidationStatusEnum` | ✅ 隱含（PENDING→VALIDATED/INVALID） | 🟢 低 |
| `uploaded_file.py` | `UploadedFileModel` | `analysis_eligible` | `SAEnum(UploadEligibilityEnum)` | ✅ `UploadEligibilityEnum` | ✅ 隱含 | 🟢 低 |
| `variant.py` | `VariantModel` | `driver_status` | `SAEnum(DriverStatusEnum)` | ✅ `DriverStatusEnum` | ✅ 隱含 | 🟢 低 |
| `variant.py` | `VariantModel` | `normalization_status` | `SAEnum(NormalizationStatusEnum)` | ✅ `NormalizationStatusEnum` | ✅ 隱含 | 🟢 低 |
| `cancer_case.py` | `CancerCaseModel` | `radioiodine_status` / `recurrence_status` | `String(64)` | ❌ String | ❌ 無定義 | 🟢 低 — 僅爲資訊欄位 |

**關鍵發現**：
1. **6 個狀態欄位使用 `SAEnum`**（`analysis_run.status`、`patient.consent_status`、`uploaded_file.upload_status` / `validation_status` / `analysis_eligible`、`variant.driver_status` / `normalization_status`）— 最佳實踐，建議推廣
2. **8 個狀態欄位使用 `String(32)`**（`clinical_decision.status`、`clinical_graph_outbox.status`、`recommendation.status`、`treatment_plan.plan_status`、`treatment_phase.status`、`treatment_item.status`、`tumor_board.consensus_status`）— 失去資料庫層類型約束
3. **僅 `TreatmentPlanModel.plan_status` 有顯式 State Machine**（`TreatmentPlanStateMachine`），其餘 String 欄位無任何 Transition 定義
4. **`ConsensusStatus` Enum 已定義於 `enums.py`** 但 `TumorBoardConsensusModel` 仍使用 `String(32)`，爲明顯缺失

### 10.6 Domain Version 控制審查

本節檢視 `src/backend/domain/` 下所有與版本控制相關的實作。

| 檔案 | Model 類別 | Version 欄位 | 類型 | 樂觀鎖？ | 說明 |
|------|-----------|-------------|:----:|:--------:|------|
| `analysis_run.py` | `AnalysisRunModel` | `pipeline_version`、`dataset_version`、`annotation_version`、`evidence_version`、`schema_version` | `String(64)` | ❌ | 僅爲資料版本標記，非併發控制 |
| `clinical_graph_outbox.py` | `ClinicalGraphOutboxModel` | `schema_version` | `Integer` (default=1) | ❌ | Outbox Event Schema 版本，非樂觀鎖 |
| `evidence.py` | `EvidenceModel` | `source_version` | `String(64)` | ❌ | 外部資料來源版本 |
| `recommendation.py` | `RecommendationModel` | `engine_version` | `String(32)` (default="1.0.0") | ❌ | Engine 版本標記 |
| `report.py` | `ReportModel` | `version` | `String(32)` | ❌ | 報表版本標記 |
| `sequencing.py` | `SequencingTestModel` | `assay_version` | `String(64)` | ❌ | 檢測版本標記 |
| `treatment_plan.py` | `TreatmentPlanModel` | `version` + `previous_version_id` + `supersedes_version_id` + `is_current` | `Integer` + `CompatUUID FK` | ❌ **無樂觀鎖** | ✅ **唯一具備顯式版本控制的 Aggregate** — 有 `version` 遞增、`UniqueConstraint("plan_id", "version")`、版本鏈 FK 自引用 |
| `variant.py` | `VariantModel` | `annotation_version` | `String(64)` | ❌ | 註解版本標記 |

**關鍵發現**：
1. **無任何 Domain Model 實作樂觀鎖（`version_id` / `__version__` / `row_version`）** — 所有更新操作依賴資料庫層的隱含鎖定，存在遺失更新風險
2. **僅 `TreatmentPlanModel` 具備完整的顯式版本控制**：包含 `version` 欄位（自動遞增）、`plan_id + version` 複合唯一約束、`previous_version_id` / `supersedes_version_id` 自引用 FK 串聯版本鏈、`is_current` 標記當前版本
3. **其餘 Model 的「版本」欄位均爲資訊性標記**（資料來源版本、Engine 版本），不提供併發控制或版本鏈功能
4. **缺少通用樂觀鎖模式**：建議引進 `__version__` 或 `version_id`（Integer，每次 update 時 +1），在 Repository 層做樂觀鎖檢查

---

## 11. Dead Code Analysis（死代碼分析）

### 11.1 掃描範圍

| 目錄 | 涵蓋內容 |
|------|---------|
| `src/` | 全部 Python 後端原始碼 |
| `tests/` | 全部測試程式碼 |
| `migrations/` | 資料庫遷移腳本 |
| `KnowGraphGo/` | Go 後端原始碼（含 `adapter/`、`client/`、`handler/`、`model/`） |
| `src/frontend/` | TypeScript 前端程式碼 |

### 11.2 TODO 註解掃描

| 目錄 | 結果 | 說明 |
|------|:----:|------|
| `src/` | ✅ **0 個** | 無 TODO 殘留 |
| `tests/` | ✅ **0 個** | 無 TODO 殘留 |
| `migrations/` | ✅ **0 個** | 無 TODO 殘留 |

**結論**：專案中無任何 TODO 註解殘留，團隊在提交前已清理完畢。

### 11.3 FIXME 註解掃描

| 目錄 | 結果 | 說明 |
|------|:----:|------|
| `src/` | ✅ **0 個** | 無 FIXME 殘留 |
| `tests/` | ✅ **0 個** | 無 FIXME 殘留 |
| `migrations/` | ✅ **0 個** | 無 FIXME 殘留 |

**結論**：專案中無任何 FIXME 註解殘留。

### 11.4 HACK / XXX 註解掃描

| 目錄 | 結果 | 說明 |
|------|:----:|------|
| `src/` | ✅ **0 個** | 無 HACK/XXX 殘留 |
| `tests/` | ✅ **0 個** | 無 HACK/XXX 殘留 |
| `migrations/` | ✅ **0 個** | 無 HACK/XXX 殘留 |
| `KnowGraphGo/` | ✅ **0 個**（僅任務文件中有提及，正式程式碼中無） | 無 HACK/XXX 殘留 |

**結論**：專案中無任何 HACK/XXX 註解殘留。

### 11.5 Deprecated 標記掃描

| 目錄 | 結果 | 說明 |
|------|:----:|------|
| `src/` | ✅ **0 個** | 無 `@deprecated` / `DeprecationWarning` |
| `tests/` | ✅ **0 個** | 無 Deprecated 標記 |
| `migrations/` | ✅ **0 個** | 無 Deprecated 標記 |

**結論**：專案中無任何 Deprecated 標記或棄用警告。

### 11.6 未使用匯入（Unused Imports）分析

#### 11.6.1 Domain `__init__.py` 中遺漏 re-export 的 Enum

以下 Enum 定義於 `src/backend/domain/enums.py`，但 **未在 `__init__.py` 的 `__all__` 中匯出**：

| Enum 名稱 | 定義行號 | 是否在其他模組中被直接引用 |
|-----------|:-------:|:------------------------:|
| `ConsequenceEnum` | 172 | 需確認 |
| `VCFStatusEnum` | 204 | 需確認 |
| `NormalizationMethodEnum` | 217 | 需確認 |
| `NormalizationResultEnum` | 224 | 需確認 |
| `NormalizationSemanticsEnum` | 233 | 需確認 |
| `GenomeBuildConfidenceEnum` | 240 | 需確認 |
| `UploadDuplicateStrategyEnum` | 250 | 需確認 |
| `UploadEligibilityEnum` | 257 | 需確認 |
| `ConsentStatusEnum` | 19 | 需確認（`ConsentStatusEnum` 存在但未被 `__init__` 匯出） |

#### 11.6.2 其他未使用匯入觀察

- `clinical_graph_outbox.py` 匯入 `from src.backend.database.models import Base, CompatUUID`，而其他 Domain 檔案使用 `from src.backend.database.models import Base as DBBase` — 存在命名不一致但非真正未使用
- 部分 Domain 檔案（如 `clinical_decision.py`、`recommendation.py`、`treatment_plan.py`、`tumor_board.py`）**沒有匯入 pydantic**，因此無 API Schema 污染
- 所有 Domain 檔案中的 `uuid` 匯入和 `_uuid()` helper 皆被使用（用於 Column default）

### 11.7 Dead Code 總結

| 類別 | 結果 | 評分驗證 |
|------|:----:|:--------:|
| TODO 殘留 | ✅ **0 個** | 驗證原始 Dead Code 分數 9.5/10 |
| FIXME 殘留 | ✅ **0 個** | 同上 |
| HACK / XXX 殘留 | ✅ **0 個** | 同上 |
| Deprecated 標記 | ✅ **0 個** | 同上 |
| 未使用匯入（顯著） | ⚠️ 9 個 Enum 未 re-export | 輕微問題，不影響執行但影響 IDE 自動補全 |
| **整體評估** | ✅ **Dead Code 極少，程式碼品質良好** | **分數維持 9.5/10** |

---

## 12. Architecture Smell — 重複 SQL 與 Validation

### 12.1 重複 SQL 查詢分析

使用 `grep` 掃描 `src/`、`tests/`、`migrations/` 中所有 SQLAlchemy 查詢模式。

#### 12.1.1 BaseRepository 標準 CRUD 重複

`BaseRepository` 已提供通用的 `get()`、`list()`、`create()`、`update()`、`delete()`、`count()` 方法。以下 Repository 重複了幾乎相同的 `select + execute` 模式：

| Repository 檔案 | 自訂方法 | 重複模式 | 說明 |
|---------------|---------|---------|------|
| `repositories/patient_repo.py:12` | `find_by_external_id()` | `select(PatientModel).where(PatientModel.external_id == ...)` | 標準查詢，可改爲通用 filter |
| `repositories/evidence_repo.py:13-24` | `find_by_gene()`, `find_by_drug()`, `find_by_variant()` | `select(EvidenceModel).where(... == ...)` | 三個幾乎相同的查詢，僅 WHERE 欄位不同 |
| `repositories/evidence_item_repo.py` | 多個 find_by 方法 | `select(EvidenceItemModel).where(...)` 重複 6 次 | 高度重複的查詢模式 |
| `repositories/knowledge_source_repo.py:25-53` | `find_by_name()`, `find_active_sources()` | `select(KnowledgeSourceModel).where(...)` 重複 3 次 | 可合併爲通用查詢 |
| `repositories/drug_interaction_repo.py:41-91` | 多個 find_by 方法 | `select(DrugInteractionModel).where(...)` 重複 3 次 | 可合併爲通用查詢 |
| `repositories/drug_repo.py:13-25` | `search_by_name()`, `list_all()` | `select(DrugModel).where(...)` | 標準 CRUD 模式 |
| `repositories/clinical_graph_outbox_repo.py` | 大量自訂查詢（~15 個 stmt） | `select(ClinicalGraphOutboxModel).where(...)` + `update(...)` + `with_for_update()` | ⚠️ **高風險**：Outbox Repository 混入最多自訂 SQL |
| `repositories/clinical_decision_repo.py` | 多個 list/find 方法 | `select(ClinicalDecisionModel).where(...)` 重複 5+ 次 | 可提取通用查詢建構器 |
| `repositories/recommendation_repo.py` | 多個 list/find 方法 | `select(RecommendationModel/RecommendationTraceModel).where(...)` 重複 5+ 次 | 可提取通用查詢建構器 |
| `repositories/treatment_plan_repo.py` | 多個 list/find 方法 | `select(TreatmentPlanModel).where(...)` 重複 5+ 次 | 可提取通用查詢建構器 |
| `repositories/case_acl_repo.py:14-34` | 4 個查詢 + 1 個 delete | `select(CaseACLModel).where(...)` 重複 4 次 | 標準 CRUD 模式 |
| `api/v1/workbench.py:426-793` | 多個內聯查詢 | `select(...).where(...)` 重複 10+ 次 | ⚠️ **API 層直接查詢**，違反分層原則 |
| `clinical/decision_thread.py:216-256` | 2 個查詢 | `select(DecisionNodeModel).where(...)` 重複 2 次 | 可提取 helper |
| `knowledge/repository.py:59-139` | 多個自訂查詢 | `select(KnowledgeEntityModel).where(...)` 重複 5 次 | 自訂 Knowledge Repository |
| `database/crud.py:44-268` | CRUD helper | `select(Patient/Diagnosis/Treatment/Drug/ResearchPaper)...` | ⚠️ **第二套 CRUD**：與 BaseRepository 功能重疊 |
| `auth/service.py:297-321` | Token/User 查詢 | `select(TokenBlacklistModel/UserModel).where(...)` 重複 4 次 | Auth 服務直接查詢 |
| `auth/case_acl_service.py:111-112` | 1 個查詢 | `select(ClinicalReportModel).where(...)` | 單一查詢，可接受 |
| `cli/clinical_graph.py:40-83` | 3 個查詢 | `select(...Model)` 重複 3 次 | CLI 工具，可接受 |
| `ranking/repository.py:64-74` | 2 個查詢 | `select(RankingRunModel).where(...)` 重複 2 次 | 標準 CRUD |
| `reasoning/repository.py:67-68` | 1 個查詢 | `select(ReasoningRunModel).where(...)` | 可接受 |
| `reporting/repository.py:57-76` | 2 個查詢 | `select(ClinicalReportModel).where(...)` 重複 2 次 | 標準 CRUD |
| `clinical/builder.py:119-130` | 1 個查詢 | `select(VariantModel).where(...)` | 單一查詢 |

#### 12.1.2 關鍵重複 SQL 模式摘要

| 重複模式 | 出現次數 | 涉及檔案數 | 嚴重程度 |
|---------|:-------:|:---------:|:--------:|
| `select(Model).where(Model.id == id)` (get_by_id) | **20+ 次** | 15+ | 🟢 Minor（繼承自 BaseRepository，可接受） |
| `select(Model).where(Model.xxx == yyy)` (find_by_field) | **30+ 次** | 12+ | 🟡 Major（應提取通用 filter 方法） |
| `select(...).where(...filter...).order_by(...)` (list_with_filters) | **15+ 次** | 8+ | 🟡 Major（應提取通用查詢建構器） |
| 多表 join 查詢（`workbench.py`） | **10+ 次** | 1 | 🔴 Critical（API 層不應直接查詢） |
| `database/crud.py` vs `repositories/base.py` 功能重疊 | 2 套 CRUD | 2 個基底檔案 | 🔴 Critical（兩套 CRUD 系統並存） |
| Outbox 專屬查詢（含 `with_for_update`） | **15+ 次** | 1 | 🟡 Major（過度集中的自訂 SQL） |

### 12.2 重複 Validation 邏輯分析

#### 12.2.1 Adapter `validate_input()` 重複

以下 5 個 Adapter 實作了簽名完全相同的 `validate_input()` 方法：

| 檔案 | 方法簽名 | 實作差異 |
|------|---------|---------|
| `adapters/base.py:74` | `async def validate_input(self, payload: Any) -> list[str]` | 基底類別（抽象） |
| `adapters/base.py:112` | `async def validate_input(self, payload: Any) -> list[str]` | 另一個基底類別實作 |
| `pipeline/civic_adapter.py:69` | `async def validate_input(self, payload: Any) -> list[str]` | CIViC 特定邏輯 |
| `pipeline/dgidb_adapter.py:53` | `async def validate_input(self, payload: Any) -> list[str]` | DGIdb 特定邏輯 |
| `pipeline/normalization.py:333` | `async def validate_input(self, payload: Any) -> list[str]` | Normalization 特定邏輯 |
| `pipeline/opencravat_adapter.py:40` | `async def validate_input(self, payload: Any) -> list[str]` | OpenCravat 特定邏輯 |
| `pipeline/vep_adapter.py:179` | `async def validate_input(self, payload: Any) -> list[str]` | VEP 特定邏輯 |

**分析**：雖然方法簽名相同，但各 Adapter 的具體驗證邏輯依賴於外部 API 的輸入格式，一定程度上的重複是合理的。不過可考慮提取 `BaseAdapter.validate_input()` 的共用模式（如 Null/Empty 檢查）。

#### 12.2.2 API 層 Null Check 重複

以下 API 端點重複了 `if not x: raise HTTPException` 模式：

| 模式 | 出現次數 | 範例位置 |
|------|:-------:|---------|
| `if not model: raise HTTPException(404, ...)` | **25+ 次** | `cases.py:78,145,163`、`patients.py:53,88,105`、`clinical_graph.py:158,328`、`analyses.py:65,91,126,150`、`evidence.py:90`、`knowledge.py:47,61` 等 |
| `if not case_id: raise HTTPException(400, ...)` | **5+ 次** | `clinical.py:112,149,197`、`analyses.py:69,94,129,153` |
| `if not result / result is None: raise HTTPException(404, ...)` | **8+ 次** | `recommendation.py:237`、`treatment_plans.py:149`、`tumor_board_consensus.py:107`、`clinical_decision.py:123`、`reasoning.py:75,115` 等 |
| `if not updates / not deleted: raise...` | **4+ 次** | `patients.py:84,105`、`specimens.py:70`、`sequencing.py:78` |

**分析**：這些 Null Check 模式高度重複，可提取爲 Decorator 或 Helper Function（如 `require_exists`）。

#### 12.2.3 Pydantic `model_validator` / `field_validator` 重複

| 位置 | Validator | 用途 |
|------|----------|------|
| `domain/cancer_case.py:103` | `@model_validator(mode="before")` | 類別轉換 |
| `domain/patient.py:96` | `@field_validator("id", mode="before")` | ID 格式驗證 |
| `clinical/decision_thread.py:102` | `@model_validator(mode="before")` | 輸入清理 |
| `clinical/evidence_weight.py:134` | `@field_validator("tier_mapping")` | 權重映射驗證 |

**分析**：Validator 數量不多且用途各異，目前無顯著重複。

#### 12.2.4 前端 Validation 重複

| 檔案 | 函數 | 重複說明 |
|------|------|---------|
| `src/frontend/src/pages/TreatmentPlanCreatePage.tsx:109` | `validate()` | 表單驗證邏輯 |
| `src/frontend/src/pages/TreatmentPlanRevisionPage.tsx:110` | `validate()` | 幾乎相同的表單驗證邏輯 |

**分析**：兩個 Treatment Plan 頁面的 `validate()` 函數邏輯高度相似，可提取共用 Hook。

#### 12.2.5 Agents 中重複的 None/Empty 檢查

多個 Agent 中有以下重複的 Guard Clause 模式：

```python
if not cancer_type:
    return []
if not disease:
    return []
if not biomarkers:
    return []
if not stage:
    return []
```

| Agent 檔案 | Guard Clause 數量 |
|-----------|:----------------:|
| `agents/clinical_trial_agent.py` | 8+ |
| `agents/guideline_agent.py` | 10+ |
| `agents/drug_agent.py` | 6+ |
| `agents/diagnosis_agent.py` | 15+ |
| `agents/variant_agent.py` | 6+ |
| `agents/consensus.py` | 8+ |
| `agents/resistance_agent.py` | 3+ |

**分析**：Agent 層的 Guard Clause 模式高度一致（`if not x: return []/None`），可提取 `require_non_empty` 裝飾器或共用 `InputValidator` 類別。

### 12.3 Architecture Smell 總結

| 類別 | 發現數量 | 嚴重程度 | 建議 |
|------|:-------:|:--------:|------|
| 重複 SQL select/where 模式 | **30+ 次**（分散在 20+ 檔案） | 🟡 Major | 提取通用 Query Builder 或 Specification Pattern |
| 兩套 CRUD 系統並存 | **2 套**（`BaseRepository` + `database/crud.py`） | 🔴 Critical | 廢棄 `database/crud.py`，統一使用 Repository 模式 |
| API 層直接執行 SQL 查詢 | **10+ 次**（在 `workbench.py`） | 🔴 Critical | 將查詢移至對應 Repository 或 Service |
| 重複的 `validate_input()` 模式 | **7 個 Adapter** | 🟢 Minor | 提取基底類別共用邏輯 |
| API 層 Null Check 重複 | **25+ 次** | 🟡 Major | 提取 `@require_exists` Decorator |
| Agent Guard Clause 重複 | **50+ 次**（分散在 7 個 Agent） | 🟡 Major | 提取 `InputValidator` 或 Guard Decorator |
| 前端表單驗證重複 | **2 次** | 🟢 Minor | 提取共用 `useFormValidation` Hook |
| **整體評估** | **多處結構性重複** | **分數維持 6.5/10** | 需透過架構工具（Query Builder、Decorator）減少重複 |

---

## 13. Trace 字段一致性對比表

### 13.1 現有 Trace 系統盤點

專案中存在**四套**獨立的 Trace ／ 記錄機制：

| # | 系統名稱 | 位置 | 儲存方式 | 用途 |
|:-:|---------|------|:-------:|------|
| 1 | **CalculationTrace** | `clinical/calculation_trace.py` | 純記憶體（in-memory dict） | 記錄 Recommendation Engine 各步驟 |
| 2 | **TreatmentPlanTrace** | `clinical/treatment_plan_trace.py` | 純記憶體（Builder 模式）→ 最終由 Repository 持久化 | 記錄 Treatment Plan Engine 各步驟 |
| 3 | **DecisionNode / DecisionThread** | `clinical/decision_thread.py` | SQLAlchemy ORM（`clinical_decision_nodes` 表） | 持久化臨床推理鏈中的每個決策節點 |
| 4 | **TumorBoardEngine trace_steps** | `clinical/tumor_board_engine.py` | `ConsensusResult.trace_steps: List[Dict]`（記憶體中） | 記錄 Consensus Engine 各步驟 |

此外，`clinical_decision_engine.py`（`ClinicalDecisionEngine`）**完全無 Trace 記錄**（已於 P2-08 標記）。

### 13.2 字段級一致性對比

| 對比維度 | CalculationTrace | TreatmentPlanTrace | DecisionNode | TumorBoardEngine trace_steps |
|---------|:----------------:|:------------------:|:------------:|:---------------------------:|
| **trace_id 命名方式** | `uuid.uuid4().hex`（32 字元 hex） | ❌ 無獨立 trace_id（由 Repository 產生） | `uuid.uuid4()`（UUID 物件） | ❌ 無獨立 trace_id（嵌入 ConsensusResult） |
| **trace_id 類型** | `str` | ❌ 無 | `uuid.UUID` → `str`（序列化時） | ❌ 無 |
| **step_order 實現** | 列表順序隱含（`list.append`） | 顯式 `step_order: int`（自動遞增） | ❌ 無 step_order（依賴 `timestamp` 排序） | 列表順序隱含（`list.append`） |
| **step_name/step_type** | `step_name: str` + `step_type: str`（5 類） | `step_type: str`（11 類，有 `TRACE_STEP_TYPES` 常數） | `node_type: NodeType`（5 類 Literal） | `step_type: str`（8 類，有 `TRACE_STEP_TYPES` 常數） |
| **input 儲存方式** | `input_data: dict` | `input_summary: dict` | `input_snapshot: dict` + `evidence_snapshot: dict` | `input_summary: dict`（嵌入 step dict） |
| **output 儲存方式** | `output_data: dict` | `output_summary: dict` | ❌ 無獨立的 output 字段（僅 `reasoning` / `decision_label`） | `output_summary: dict`（嵌入 step dict） |
| **created_at / timestamp** | `timestamp: datetime`（per step）+ `started_at` / `completed_at`（per trace） | ❌ 無時間戳（per step） | `timestamp: datetime`（per node） | ❌ 無時間戳（per step） |
| **status** | `status: str`（"running" \| "completed" \| "failed"） | ❌ 無（由 TraceManager 隱含） | ❌ 無 | `consensus_status: ConsensusStatus`（整體結果） |
| **parent 鏈接** | `parent_trace_id: str \| None` | ❌ 無 | `parent_id: uuid.UUID \| None` | ❌ 無 |
| **持久化** | ❌ 僅記憶體 | ✅ Builder → Repository → DB | ✅ ORM → DB | ❌ 僅記憶體（trace_steps 隨結果返回） |
| **序列化格式** | Pydantic `model_dump()` | 自訂 `to_dict()` | Pydantic `model_validate()` | 純 `dict` |
| **模型基底** | Pydantic `BaseModel` | `@dataclass` | Pydantic `BaseModel` + SQLAlchemy `DBBase` | `@dataclass` + 純 `dict` |

### 13.3 一致性判定

| 維度 | 判定 | 說明 |
|------|:----:|------|
| **trace_id 命名** | ❌ **不一致** | 3 種不同產生方式（hex / UUID 物件 / 無） |
| **step_order 實現** | ❌ **不一致** | 顯式索引 vs 隱含順序 vs 時間戳排序 |
| **step_name 實現** | ❌ **不一致** | `step_name`+`step_type` vs 僅 `step_type` vs `node_type` |
| **input 儲存方式** | ⚠️ **部分一致** | 均有 dict 結構，但字段名不同（`input_data` / `input_summary` / `input_snapshot`）|
| **output 儲存方式** | ❌ **不一致** | DecisionNode 完全缺少 output 字段 |
| **created_at/timestamp** | ❌ **不一致** | TreatmentPlanTrace 和 TumorBoardEngine trace_steps 均無時間戳 |
| **parent 鏈接** | ❌ **不一致** | 僅 CalculationTrace 和 DecisionNode 支援，其餘兩者無 |
| **持久化策略** | ❌ **不一致** | 記憶體 only / Builder→DB / ORM→DB |
| **模型基底** | ❌ **不一致** | Pydantic / dataclass / 混合 |

### 13.4 建議

1. **P1**：建立統一的 `TraceSchema`（Pydantic BaseModel），涵蓋 `trace_id`、`step_order`、`step_type`、`input`、`output`、`timestamp`、`parent_id` 等共通字段
2. **P1**：所有 Engine 層強制整合 Trace 記錄，包含 `ClinicalDecisionEngine`（解決 P2-08）
3. **P2**：統一持久化策略 — 建議全部走 Repository 模式，廢除純記憶體 Trace
4. **P2**：引入 `trace_id` 生成標準（UUID v4 hex 或 ULID），確保跨系統可追蹤

---

## 14. Tests Coverage 8 類別逐類審查表

### 14.1 Engine 測試

| 測試標的 | 測試檔案 | 測試類別 / 函數數量 | 覆蓋範圍 | 缺失案例 |
|---------|---------|:-----------------:|---------|:--------:|
| `RecommendationEngine` | `tests/test_recommendation_engine.py` | ~85 個 test（含 `TestDrugRankingEngine`） | WeightRegistry、EvidenceAggregator、DrugRanker、規則引擎、分數計算、Ranking | ❌ `run()` 完整管線整合測試（含 trace_manager 實際寫入） |
| `DrugRanker` | `tests/test_drug_ranking.py` | ~35 個 test | 評分子系統、抵抗性/敏感性/指引/FDA 各維度、完整 Ranking 流程 | ✅ 相對完整 |
| `TumorBoardEngine (ConsensusEngine)` | `tests/test_tumor_board_engine.py` | ~35 個 test（含 `TestEngineTrace`、`TestEngineValidation`） | 共識分類、權重計算、異議處理、放棄投票、信心門檻、trace 完整性 | ✅ 相對完整 |
| `ConsensusEngine (unit)` | `tests/unit/test_consensus.py` | ~15 個 test（`TestConsensusEngine`） | 共識引擎單元測試 | ✅ |
| `TreatmentPlanEngine` | `tests/backend/clinical/test_treatment_plan_engine.py` | ~35 個 test（`TestTreatmentPlanStateMachine`、`TestRuleRegistry`、`TestTreatmentPlanRuleSet`、`TestTreatmentPlanTraceBuilder`、`TestTreatmentPlanEngine`） | 狀態機轉換、規則註冊、階段序列、監控產生、安全性規則、替代方案、Trace Builder | ❌ 缺少邊界案例（空輸入、極端值） |
| `ClinicalDecisionEngine` | ❌ **無專屬測試** | 0 | ❌ 完全無測試覆蓋 | ❌ 需要完整的單元測試套件 |

### 14.2 Repository 測試

| 測試標的 | 測試檔案 | 測試類別 / 函數數量 | 覆蓋範圍 | 缺失案例 |
|---------|---------|:-----------------:|---------|:--------:|
| `PatientRepository` | `tests/test_repositories.py`（`TestPatientRepository`） | ~6 個 test | CRUD、`find_by_external_id` | ❌ 缺少 batch/分頁測試 |
| `VariantRepository` | `tests/test_repositories.py`（`TestVariantRepository`） | ~6 個 test | CRUD、篩選查詢 | ❌ 同上 |
| `AnalysisRunRepository` | `tests/test_repositories.py`（`TestAnalysisRunRepository`） | ~4 個 test | CRUD | ✅ |
| `RecommendationRepository` | `tests/test_repositories.py`（`TestRecommendationRepository`） | ~15 個 test | CRUD、`find_by_patient`、List | ❌ 缺少 transaction rollback 測試 |
| `TraceRepository` | `tests/test_repositories.py`（`TestTraceRepository`） | ~8 個 test | CRUD、依 recommendation_id 查詢 | ❌ 缺少依 trace_id 查詢測試 |
| `ClinicalDecisionRepository` | `tests/test_clinical_decision_repo.py`（`TestClinicalDecisionRepository`、`TestClinicalDecisionTraceRepository`、`TestClinicalDecisionRepositoryCount`） | ~25 個 test | CRUD、Trace、Count | ✅ 相對完整 |
| `TumorBoardConsensusRepository` | `tests/test_tumor_board_repo.py`（`TestTumorBoardConsensusRepository`、`TestTumorBoardOpinionRepository`、`TestTumorBoardConsensusTraceRepository`） | ~25 個 test | CRUD、Opinion、Trace | ✅ 相對完整 |
| `TreatmentPlanRepository` + `TreatmentPhaseRepository` + `TreatmentItemRepository` + `TreatmentMonitoringRepository` + `TreatmentSafetyRuleRepository` + `TreatmentPlanTraceRepository` | `tests/backend/repositories/test_treatment_plan_repos.py` | ~55 個 test | CRUD、版本查詢、`mark_superseded`、Transaction rollback、分頁 | ✅ **覆蓋最完整的 Repository 測試** |
| `KnowledgeSourceRepository` | `tests/test_phase2b_hardening.py`（`TestKnowledgeSourceRepository`） | ~8 個 test | CRUD、`find_by_name`、`find_active_sources` | ✅ |
| `EvidenceItemRepository` | `tests/test_phase2b_hardening.py`（`TestEvidenceItemRepository`） | ~10 個 test | CRUD、多欄位查詢 | ✅ |
| `DrugInteractionRepository` | `tests/test_phase2b_hardening.py`（`TestDrugInteractionRepository`） | ~8 個 test | CRUD、藥物交互作用查詢 | ✅ |
| `TumorBoardRepository (workbench)` | `tests/test_workbench.py`（`TestTumorBoardRepository`） | ~5 個 test | CRUD | ❌ 覆蓋較低 |
| `OutboxRepository` | `tests/unit/test_phase3d_outbox_repo.py`（`TestOutboxRepository`） | ~8 個 test | CRUD、`with_for_update`、狀態過濾 | ✅ |

### 14.3 Service 測試

| 測試標的 | 測試檔案 | 測試類別 / 函數數量 | 覆蓋範圍 | 缺失案例 |
|---------|---------|:-----------------:|---------|:--------:|
| `RecommendationService` | `tests/test_recommendation_service.py` | ~6 個 test | 基本 Service 流程 | ❌ 覆蓋偏低 |
| `ClinicalDecisionService` | `tests/test_clinical_decision_service.py` | ~8 個 test | CRUD Service 層 | ❌ |
| `ClinicalReasoningService` | `tests/test_clinical_reasoning.py`（`TestClinicalReasoningService`） | ~10 個 test | Reasoning 流程 Service | ✅ |
| `TreatmentPlanService` | `tests/backend/services/test_treatment_plan_service.py` | ~40 個 test（`TestCreatePlanSuccess`、`TestValidationErrors`、`TestTransactionRollback`、`TestRevision`、`TestEngineFailures`） | 建立成功流程、驗證錯誤、交易回滾、版本修訂、Engine 失敗處理 | ✅ **覆蓋最完整的 Service 測試** |
| `TumorBoardService` | `tests/test_tumor_board_service.py` | ~10 個 test | CRUD、Consensus 流程 | ❌ |
| `WorkbenchService` | `tests/test_workbench.py`（`TestWorkbenchService`） | ~6 個 test | 基本查詢 | ❌ 覆蓋偏低 |
| `EventService (Outbox)` | `tests/unit/test_phase3d_outbox_service.py`（`TestEventService`） | ~6 個 test | Event 建立、發送 | ✅ |
| `AuthService` | `tests/test_production_hardening.py`（`TestAuthService`） + `tests/test_auth_hardening.py`（`TestAuthServiceUnit`） | ~15 個 test | 認證、授權、Token 管理 | ✅ |
| `KnowledgeService` | `tests/test_knowledge_layer.py`（`TestKnowledgeService`） | ~6 個 test | 知識查詢 Service | ❌ |

### 14.4 API 測試

| 測試標的 | 測試檔案 | 測試類別 / 函數數量 | 覆蓋範圍 | 缺失案例 |
|---------|---------|:-----------------:|---------|:--------:|
| 通用 API | `tests/test_api.py`、`tests/test_api_v1.py` | ~20 個 test | 基本端點可用性 | ❌ 缺少邊界案例 |
| Recommendation API | `tests/test_api_recommendation.py` | ~8 個 test | Recommendation CRUD API | ❌ |
| Clinical Decision API | `tests/test_api_clinical_decision.py` | ~8 個 test | Clinical Decision CRUD API | ❌ |
| Tumor Board API | `tests/test_api_tumor_board.py` | ~8 個 test | Tumor Board CRUD API | ❌ |
| Treatment Plan API | `tests/backend/api/test_treatment_plan_api.py` | ~30 個 test（`TestCreateTreatmentPlan` ~ `TestErrorScenarios`） | 建立/取得/列表/版本/Trace/提交/審核/核准/啓動/暫停/完成/取消/修訂 + 錯誤情境 | ✅ **覆蓋最完整的 API 測試** |
| Phase 2 API | `tests/integration/test_phase2_api.py` | ~10 個 test | Phase 2 端點整合 | ✅ |
| Workbench API | `tests/integration/test_workbench_api.py`（`TestWorkbenchAPIFlow`）+ `tests/integration/test_workbench_v11.py` | ~15 個 test | Workbench API 流程 | ✅ |
| Phase 3D Query API | `tests/integration/test_phase3d_query_api.py`（`TestGraphAPI`） | ~8 個 test | 圖譜查詢 API | ✅ |
| Charts API | `tests/test_api.py`（`TestChartsAPI`） | ~5 個 test | Charts 端點 | ❌ 覆蓋偏低 |
| Research API | `tests/test_api.py`（`TestResearchAPI`） | ~4 個 test | Research 端點 | ❌ 覆蓋偏低 |
| Clinical Reports API | `tests/test_clinical_reports.py` | ~6 個 test | 報告 API | ❌ |

### 14.5 Restart Recovery 測試

| 測試標的 | 測試檔案 | 測試類別 / 函數數量 | 覆蓋範圍 | 缺失案例 |
|---------|---------|:-----------------:|---------|:--------:|
| Recommendation Restart | `tests/test_restart_recovery.py` | ~8 個 test（含 `TestPostgresRestart`） | App 重啓後資料完整性、Postgres 特定 engine/sessionmaker 重新建立檢查 | ✅ 良好 |
| Treatment Plan Restart | `tests/backend/integration/test_treatment_plan_restart.py`（`TestTreatmentPlanRestartRecovery`） | ~6 個 test | 完整 Plan 重啓恢復、不存在的 Plan、監控欄位持久化、Trace 正確性、多 Plan 情境 | ✅ 良好 |
| Tumor Board Restart | `tests/test_tumor_board_restart_recovery.py` | ~5 個 test | Consensus 重啓恢復 | ❌ 覆蓋偏低（僅基本流程） |

### 14.6 Migration 測試

| 測試標的 | 測試檔案 | 測試類別 / 函數數量 | 覆蓋範圍 | 缺失案例 |
|---------|---------|:-----------------:|---------|:--------:|
| 基本 Migration | `tests/test_migration.py` | ~25 個 test（migration 001/017/018/019/020/023/025 等） | Upgrade/Downgrade 檔案存在性、Schema 正確性 | ❌ 多數 migration 僅檢查檔案存在，未驗證資料遷移正確性 |
| Migration 016 | `tests/integration/test_migration_016.py` | ~5 個 test | clinical_decision_nodes 表建立、索引 | ✅ |
| Migration 025 PG 完整循環 | `tests/integration/test_migration_025_pg_full_cycle.py` | 1 個 test | PostgreSQL 上 Upgrade→Downgrade→Re-upgrade 完整循環 | ✅ 但僅覆蓋 025 |
| Migration 025 PG Schema 比較 | `tests/integration/test_migration_025_pg_schema_compare.py` | 2 個 test | Downgrade 後 Schema 與原始 024 一致、Re-upgrade 後與原始 025 一致 | ✅ |
| Migration 025 PG Trace Constraint | `tests/integration/test_migration_025_pg_trace_constraint.py` | 1 個 test | 驗證 025 放寬 trace_id UNIQUE 約束 | ✅ |
| Migration Gate | `tests/test_migration_gate.py` | 4 個 test | Composite Unique Constraint、trace_id UNIQUE 移除、Foreign Keys、plan_id + version Unique | ✅ PostgreSQL 特定約束驗證 |

### 14.7 Postgres 測試

| 測試標的 | 測試檔案 | 測試類別 / 函數數量 | 覆蓋範圍 | 缺失案例 |
|---------|---------|:-----------------:|---------|:--------:|
| Migration PG 專屬 | `tests/integration/test_migration_025_pg_full_cycle.py`、`test_migration_025_pg_schema_compare.py`、`test_migration_025_pg_trace_constraint.py` | 4 個 test | 025 Migration PostgreSQL 專屬驗證 | ❌ 僅覆蓋 migration 025，缺少其他 migration 的 PG 測試 |
| Migration Gate PG | `tests/test_migration_gate.py` | 4 個 test | 約束存在性、FK 存在性、Unique 約束 | ✅ 但僅限 schema 層級 |
| Restart Recovery PG | `tests/test_restart_recovery.py`（`TestPostgresRestart`） | 2 個 test | Postgres 特定 engine/sessionmaker 重新建立 | ✅ |

### 14.8 Graph 測試（KnowGraphGo Integration）

| 測試標的 | 測試檔案 | 測試類別 / 函數數量 | 覆蓋範圍 | 缺失案例 |
|---------|---------|:-----------------:|---------|:--------:|
| Adapter Clinical | `KnowGraphGo/adapter/clinical/clinical_test.go` | ~15 個 test | Adapter 事件映射 | ❌ 缺少 Variant/Guideline/Drug 事件處理測試（對應 P1-10） |
| ID Factory | `KnowGraphGo/adapter/clinical/id_factory_test.go` | ~8 個 test | ID 工廠方法 | ❌ 缺少 5 個治療計劃相關方法測試（對應 P0-05） |
| Graph Entity | `KnowGraphGo/graph/entity_test.go` | ~10 個 test | Entity 操作 | ✅ |
| Graph Relation | `KnowGraphGo/graph/relation_test.go` | ~8 個 test | Relation 操作 | ✅ |
| Graph Property | `KnowGraphGo/graph/property_equal_test.go` | ~5 個 test | Property 比較 | ✅ |
| Graph Errors | `KnowGraphGo/graph/errors_test.go` | ~5 個 test | 錯誤處理 | ✅ |
| Inference | `KnowGraphGo/inference/*_test.go`（5 個檔案） | ~30 個 test | 前向/後向推理、規則引擎、關係 | ✅ 良好 |
| Ontology | `KnowGraphGo/ontology/*_test.go`（3 個檔案） | ~15 個 test | 本體約束、繼承 | ✅ 良好 |
| Pattern | `KnowGraphGo/pattern/*_test.go`（3 個檔案） | ~15 個 test | 模式匹配、增強匹配器 | ✅ 良好 |
| Traversal | `KnowGraphGo/traversal/*_test.go`（4 個檔案） | ~15 個 test | DFS、K-Hop、遍歷 | ✅ 良好 |
| Service | `KnowGraphGo/service/*_test.go`（2 個檔案） | ~10 個 test | 知識服務、一般服務 | ✅ |
| Store/SQLite | `KnowGraphGo/store/sqlite/*_test.go`（2 個檔案） | ~15 個 test | SQLite 儲存、併發 | ✅ 良好 |
| Store/Memory | `KnowGraphGo/store/memory/store_test.go` | ~5 個 test | 記憶體儲存 | ✅ |
| Export | `KnowGraphGo/export/*_test.go`（5 個檔案） | ~15 個 test | CSV、JSON、Markdown 匯出、Constructor | ✅ 良好 |
| Explain | `KnowGraphGo/explain/*_test.go`（2 個檔案） | ~8 個 test | 可解釋性 | ✅ |
| CLI Main | `KnowGraphGo/cmd/knowgraph/main_test.go` | ~3 個 test | CLI 基本功能 | ❌ 覆蓋偏低 |

### 14.9 總結

| 類別 | 測試覆蓋等級 | 估計總 test 數 | 主要強項 | 主要缺口 |
|:----:|:----------:|:-------------:|---------|---------|
| Engine | 🟡 中等 | ~170 | DrugRanker、TumorBoardEngine、TreatmentPlanEngine | **ClinicalDecisionEngine 完全無測試**（P0） |
| Repository | 🟢 良好 | ~145 | TreatmentPlan Repos、ClinicalDecision Repo、TumorBoard Repo | 部分 Repository 覆蓋偏低（Workbench、Knowledge） |
| Service | 🟡 中等 | ~100 | TreatmentPlanService（40 tests）、AuthService | RecommendationService、TumorBoardService、WorkbenchService 覆蓋偏低 |
| API | 🟢 良好 | ~115 | TreatmentPlan API（30 tests）、Workbench API、Phase 3D API | Charts/Research/Reports API 偏低 |
| Restart Recovery | 🟢 良好 | ~20 | Recommendation、Treatment Plan、Tumor Board 三者均覆蓋 | Tumor Board 恢復測試需強化 |
| Migration | 🟡 中等 | ~35 | 多版本覆蓋、025 PG 完整循環驗證 | 多數 migration 僅檢查檔案存在，未驗證資料遷移 |
| Postgres | 🟡 中等 | ~10 | Migration 025 PG 專屬測試、Migration Gate | 僅限 migration 025，缺少其他 migration 的 PG 測試 |
| Graph (KnowGraphGo) | 🟢 良好 | ~150 | Inference、Ontology、Pattern、Traversal、Export 均良好 | Adapter 事件處理測試缺口（Variant/Guideline/Drug） |

**整體評估**：Tests Coverage 分數維持 **8.0/10**，但 `ClinicalDecisionEngine` 零測試覆蓋爲 P0 缺陷，建議優先補上。

---

## 附錄 A：各審查維度原始分數對照

| 審查項目 | 原始分數（/10） | 來源報告 |
|---------|:--------------:|---------|
| Domain 層 | 4.0 | `review_layers.md` |
| Repository 層 | 5.0 | `review_layers.md` |
| Service 層 | 7.0 | `review_layers.md` |
| Engine 層 | 7.0 | `review_layers.md` |
| Migration | 6.0 | `review_crosscutting.md` |
| API Layer | 7.0 | `review_crosscutting.md` |
| Digital Thread | 7.5 | `review_crosscutting.md` |
| Trace | 5.5 | `review_crosscutting.md` |
| Graph Adapter | 7.0 | `review_quality.md` |
| Tests Coverage | 8.0 | `review_quality.md` |
| Dead Code | 9.5 | `review_quality.md` |
| Architecture Smell | 6.5 | `review_quality.md` |

## 附錄 B：重構工時估算摘要

| 等級 | 項目數 | 總預估工時 |
|------|:------:|:---------:|
| HIGH (R-H) | 7 | 75h+ |
| MEDIUM (R-M) | 10 | 69h |
| LOW (R-L) | 10 | 35h+ |
| **合計** | **27** | **~179h** |

> **注意**：P0-01（Domain/ORM 分離）的 40h 爲初期估算，實際工時取決於是否採用漸進式重構策略（保留舊 Model 向後相容、逐步遷移），建議 Phase 3F 初期進行技術 Spike 後重新估算。

---

*報告結束——基於三份子報告（review_layers.md、review_crosscutting.md、review_quality.md）綜合分析產出。*
