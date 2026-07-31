# Phase 4 & Phase 5 Master Plan 規劃 — 總結報告

> **文件狀態**：✅ 已完成  
> **產生日期**：2026-08-01  
> **任務代號**：Phase-4-5-Master-Plan  
> **場景**：master-plan（大型規劃與調研）  

---

## 1. 任務概述

| 項目 | 內容 |
|------|------|
| **任務名稱** | Phase 4 & Phase 5 Master Plan 規劃 |
| **場景** | master-plan（大型規劃與調研） |
| **設計時間** | 2026-07-30（計劃制定） |
| **執行期間** | 2026-07-30 ~ 2026-08-01 |
| **總負責角色** | PLANNER |
| **參與角色** | PLANNER, explorer, doc-writer, REVIEWER |
| **總預估工時** | 14～20h（若 doc-writer 僅一位則 18～24h） |
| **評審時間** | 2026-08-01 |
| **評審結果** | **總分 94/100 ✅ 合格**，所有 Gate PASS |

### 執行流程

```
階段 I：專案現況盤點（串行）→ T-01 盤點
階段 II：分析與規劃（可並行）→ T-02 Gap + T-03 Phase 4 Plan + T-04 Phase 5 Plan
階段 III：整合產出（串行）→ T-05 Dependency Map → T-06 Roadmap
                               └→ T-07 ADR（可與 T-05/T-06 並行）
最終 → REVIEWER 評分審查
```

---

## 2. 現況完成度

基於 `tasks/research/current-capability-inventory.md`，共盤點 **29 個維度**，狀態統計如下：

| 狀態 | 數量 | 維度清單 |
|------|:----:|---------|
| ✅ **Complete** | **20** | Domain Models, Services, Repositories, API Routes, Engines, Knowledge Layer, Agents, Pipeline, Auth/ACL, Clinical Graph/Outbox, Reporting, VCF, Workbench, Clinical Graph (Go), Frontend Components, Frontend Tests, Migrations, Backend Tests, Documentation, Digital Thread |
| 🟡 **Partial** | **5** | Adapters, Observability, Frontend Pages, Frontend API Client, CI/CD |
| 🟠 **Stub** | **2** | Models/ML, FHIR |
| 🔴 **Missing** | **2** | HL7/DICOM/PACS, RAG/Vector DB/Embedding |
| ⚠️ **TechDebt** | **0** | 無特定標記為 TechDebt 的維度 |
| **總計** | **29** | |

**關鍵發現**：
- 核心後端（Domain / Service / Repository / API / Engine / Auth）皆為 **Complete**，可直接複用
- 外部 Adapter 8/10 為 stub，需逐一實作（Partial）
- Observability 僅有 audit + health，缺 metrics/tracing/profiling（Partial）
- FHIR 僅有簡化版匯出，HL7/DICOM 完全缺失
- RAG/Vector DB 完全缺失
- Models/ML 僅有 1 個 JSON manifest，幾乎無可用資產

---

## 3. Phase 4 規劃摘要

### 3.1 最終能力

Phase 4（Clinical AI Productization）完成後，系統從「已開發完成的 AI 原型」升級為「可在臨床環境中產品化運作的 AI 系統」。新增 10 項能力，包括 FHIR R4 互通、外部證據源真實連接、RAG 語義搜尋、生產級監控、Docker 化部署等。

### 3.2 預計 Batch 數量：6 個

| Batch | 名稱 | 前置依賴 | 預估檔案數 | 預估工時 |
|:-----:|------|:--------:|:----------:|:--------:|
| **B1** | FHIR R4 醫院互通 | 無 | 18-22 files | 3-4 週 |
| **B2** | 外部證據 Adapter 實作 | 無 | 16-20 files | 2-3 週 |
| **B3** | RAG/Vector DB/Embedding | 無 | 14-18 files | 2-3 週 |
| **B4** | 生產級 Observability | 無 | 12-16 files | 1-2 週 |
| **B5** | Docker + CI/CD 基礎設施 | B1+B2+B3+B4 | 14-18 files | 1-2 週 |
| **B6** | 前端產品化與 Service 重構 | B5 | 18-22 files | 2-3 週 |

### 3.3 可並行 Batch

| 並行組 | Batch | 說明 |
|:------:|:-----:|------|
| **組 A** | **B1、B2、B3、B4** | 四個 Batch 無前置依賴，可完全並行開發 |
| 串行 | B5 | 依賴 B1～B4 全部完成 |
| 串行 | B6 | 依賴 B5（Docker 環境測試） |

### 3.4 第一個建議執行的 Batch：**B1 — FHIR R4 醫院互通**

**交付範圍**：
- FHIR R4 資源模型（Patient, Observation, Condition, MedicationRequest, DiagnosticReport, Procedure, CarePlan）
- FHIR RESTful API（Read/Search/Create/Update）
- Domain Model ↔ FHIR Resource 映射層
- FHIR 驗證（fhirpath/fhir-validator）
- CapabilityStatement + SMART-on-FHIR 設定
- 既有 FHIRExporter 整合（向後相容）
- FHIR 端點 Audit Logging
- 整合測試（使用 FHIR 測試樣本）
- **預估 20 個檔案**，工期 3-4 週

### 3.5 Phase 4 整體 Gate

| Gate | 名稱 | 通過條件 |
|:----:|------|---------|
| G1 | FHIR 互通 Gate | 所有核心資源端點可正常 Read/Search |
| G2 | 外部證據 Gate | 8 adapter 全部 configured（非 stub） |
| G3 | 語義檢索 Gate | Embedding pipeline 完成；KnowledgeBase 可語義搜尋 |
| G4 | 生產監控 Gate | Prometheus metrics + OTEL tracing |
| G5 | 部署 Gate | Docker Compose 一鍵啟動 |
| G6 | 程式碼品質 Gate | Service 拆分完成、前端統一 |
| G7 | 回歸 Gate | 所有既有測試通過 |

---

## 4. Phase 5 規劃摘要

### 4.1 預計 Batch 數量：7 個

| Batch | 名稱 | 前置依賴 | 預估工期 |
|:-----:|------|:--------:|:--------:|
| **B1** | Platform Core（Registry 基礎） | 無（Phase 4 完成後） | Weeks 1-3 |
| **B2** | Specialty Module Contract + Cardiology Sample | B1 | Weeks 4-7 |
| **B3** | Oncology 抽象化 | B1, B2 | Weeks 8-10 |
| **B4** | KG Namespace + Terminology | B2, B3 | Weeks 11-12 |
| **B5** | Tenant Isolation + API Versioning | B1 | Weeks 13-14 |
| **B6** | Neurology + Radiology Samples | B2, B4, B5 | Weeks 15-17 |
| **B7** | 文件、遷移指南、驗收 | 全部 | Week 18 |

**總預估工期**：16-20 週（4-5 個月）

### 4.2 關鍵架構改造

1. **Registry / Plugin 化架構**
   - 5 個 Registry：SpecialtyRegistry、AgentRegistry、WorkflowRegistry、EvidenceSourceRegistry、RuleSetRegistry
   - 完整 Plugin Lifecycle：DISCOVERED → REGISTERED → LOADED → ACTIVE → STOP/ERROR → UNREGISTERED
   - PlatformContainer + DI 注入機制

2. **Specialty Module Contract**
   - `SpecialtyBase` 抽象基底類（強制介面：manifest, initialize, health_check, shutdown）
   - 選擇性 Mixin（SpecialtyConfigMixin, SpecialtyMigrationMixin, SpecialtySeedDataMixin）
   - 標準化目錄結構（`.template/` 模版）
   - `manifest.json` 定義版本、依賴、描述

3. **Oncology 耦合解耦**
   - 盤點結果：65% 可通用、26% 需抽象化、9% Oncology 專屬
   - 提取 AbstractCase、AbstractConsensus 介面
   - ClinicalContext 擴充 `diagnosis_code`/`diagnosis_system`/`specialty_id`

4. **Knowledge Graph Namespace**
   - KnowGraphGo 擴充 `NamespacedStore`，支援 `{namespace}:{type}:{id}` 格式
   - 跨命名空間查詢路由

5. **Multi-tenant 隔離**
   - 9 層隔離策略（資料庫、資料列、配置、快取、檔案、Queue、認證、Rate Limit、計費）
   - TenantAwareRepository（BaseRepository 擴充）

6. **Sample Specialty Modules**
   - Cardiology（完整模組：domain + agents + workflow + evidence + rules + terminology）
   - Neurology（基礎結構 + MS/Stroke 診斷）
   - Radiology（DICOM 整合 + AI 推理 stub）

---

## 5. 評分結果

### 5.1 總分

| 評分維度 | 分數 | 權重後 |
|----------|:----:|:------:|
| 完整性（Completeness） | 22 | 22 |
| 正確性（Correctness） | 24 | 24 |
| 可執行性（Executability） | 24 | 24 |
| 架構與風險控制（Architecture & Risk Control） | 24 | 24 |
| **總分** | | **94 ✅ 合格（≥ 90）** |

### 5.2 扣分原因

| 維度 | 扣分 | 原因 |
|------|:----:|------|
| 完整性 | -3 | Gap Analysis 將 #16 Background Jobs/Queue 列為 P0，但 Phase 4 Master Plan 未包含實作計畫也無說明為何延後 |
| 正確性 | -1 | 同上，跨文件不一致 |
| 可執行性 | -1 | Background Jobs 基礎設施缺失可能影響 Evidence Freshness 等功能時程 |
| 架構與風險控制 | -1 | 風險登記冊未涵蓋「Gap Analysis 與 Phase 4 Plan 之間不一致」此風險 |

### 5.3 Gate 檢查結果

| Gate 名稱 | 結果 |
|-----------|:----:|
| ✅ Current State Evidence Gate | PASS — 所有盤點可追溯至真實檔案路徑與行號 |
| ✅ Vertical Slice Quality Gate | PASS — 每個 Batch 涵蓋 Clinical AI / Evidence / KG / Hospital Integration / Security / Persistence / Observability / CI / Frontend / Deployment |
| ✅ Dependency Gate | PASS — 無循環依賴，依賴關係明確 |
| ✅ Scope Control Gate | PASS — 未超出規劃範圍，未寫 production code |
| ✅ Phase 4 Feasibility Gate | PASS — 技術與資源可行（FHIR R4 成熟標準、Adapter 有公開 API、RAG 有成熟開源方案） |
| ✅ Phase 5 Platformization Gate | PASS — 5 個 Registry + Module Contract + 3 sample specialties，非僅 rename |

---

## 6. 交付產出清單

### 6.1 規劃文件（7 項）

| # | 文件路徑 | 大小 | 說明 |
|:-:|----------|:----:|------|
| 1 | `tasks/research/current-capability-inventory.md` | 30,963 B | 專案現況盤點（29 維度） |
| 2 | `tasks/research/phase4-phase5-gap-analysis.md` | 37,023 B | Gap Analysis（23 維度 As-Is/To-Be/Gap） |
| 3 | `tasks/plan-phase4-clinical-ai-productization.md` | 96,231 B | Phase 4 Master Plan（6 Batch） |
| 4 | `tasks/plan-phase5-medical-ai-platform.md` | 45,000 B | Phase 5 Master Plan（7 Batch） |
| 5 | `tasks/phase4-phase5-dependency-map.md` | 38,460 B | 依賴關係圖（含相鄰矩陣與關鍵路徑） |
| 6 | `tasks/roadmap-phase4-phase5.md` | 50,423 B | 開發路線圖（Batch + Gate） |
| 7 | `docs/adr/` 系列（6 份 ADR） | 共 37,198 B | 架構決策記錄 |

### 6.2 ADR 清單

| # | 文件路徑 | 大小 |
|:-:|----------|:----:|
| 1 | `docs/adr/ADR-001-fhir-canonical-model-strategy.md` | 4,655 B |
| 2 | `docs/adr/ADR-002-external-evidence-adapter-strategy.md` | 5,401 B |
| 3 | `docs/adr/ADR-003-rag-knowledge-graph-responsibilities.md` | 5,586 B |
| 4 | `docs/adr/ADR-004-clinical-terminology-strategy.md` | 5,649 B |
| 5 | `docs/adr/ADR-005-multi-tenant-isolation-strategy.md` | 6,352 B |
| 6 | `docs/adr/ADR-006-specialty-module-architecture.md` | 9,555 B |

### 6.3 管理文件

| # | 文件路徑 | 大小 | 說明 |
|:-:|----------|:----:|------|
| 1 | `tasks/requirements.md` | 5,163 B | 原始需求定義 |
| 2 | `tasks/plan-Phase-4-5-Master-Plan.md` | 15,307 B | 執行計劃 |
| 3 | `tasks/reviews/review_Phase-4-5-Master-Plan_0.md` | 9,590 B | REVIEWER 評分報告 |
| 4 | `tasks/summary-report-phase4-5-master-plan.md` | (本文件) | 總結報告 |

---

## 7. 具體改進建議（來自 REVIEWER）

### 必須處理（建議納入修訂）

1. **明確 Background Jobs/Queue 的定位**
   - Gap Analysis 將 #16 列為 P0，但 Phase 4 Master Plan 未包含
   - 建議在 Phase 4 Plan §1.3「明確排除」中補充說明為何延後，或在 B3/B5 中追加最小可行 Background Jobs 支援

### 建議改善

2. **Gap Analysis 與 Master Plan 之間的追蹤矩陣** — 建立對照表
3. **風險登記冊擴充** — 增加不一致風險與 Background Jobs 缺失風險
4. **Phase 4 Batch 順序微調** — 考慮將 Go CI pipeline 提前
5. **跨 Batch 共用元件識別** — B1/B2 之間建立共用快取與錯誤處理模式

---

## 8. 禁止事項確認

| # | 禁止事項 | 狀態 |
|:-:|---------|:----:|
| 1 | ❌ 未修改任何 production code | ✅ 確認 |
| 2 | ❌ 未建立空殼 API 或 placeholder frontend | ✅ 確認 |
| 3 | ❌ 未引入 Kubernetes 或拆 microservices | ✅ 確認 |
| 4 | ❌ 未無證據引入 Kafka / Redis / Vector DB | ✅ 確認 |
| 5 | ❌ 未虛構已有能力 | ✅ 確認 |
| 6 | ❌ 未使用 mock 結果宣稱 integration ready | ✅ 確認 |

---

## 9. Git Status（僅供參考，不執行 commit/push）

> 以下為本輪產出檔案清單，實際 Git 操作由後續流程執行。

**新增檔案**（規劃與架構文件，無 production code）：
- `tasks/research/current-capability-inventory.md`
- `tasks/research/phase4-phase5-gap-analysis.md`
- `tasks/plan-phase4-clinical-ai-productization.md`
- `tasks/plan-phase5-medical-ai-platform.md`
- `tasks/phase4-phase5-dependency-map.md`
- `tasks/roadmap-phase4-phase5.md`
- `docs/adr/ADR-001-fhir-canonical-model-strategy.md`
- `docs/adr/ADR-002-external-evidence-adapter-strategy.md`
- `docs/adr/ADR-003-rag-knowledge-graph-responsibilities.md`
- `docs/adr/ADR-004-clinical-terminology-strategy.md`
- `docs/adr/ADR-005-multi-tenant-isolation-strategy.md`
- `docs/adr/ADR-006-specialty-module-architecture.md`

---

> **總結**：Phase 4 & Phase 5 Master Plan 規劃任務已全部完成。7 項交付物齊全、6 份 ADR 完整、評分 94/100 合格、所有 Gate PASS。後續可依規劃進入 Phase 4 Clinical AI Productization 的 Batch 實作階段，建議從 **B1 — FHIR R4 醫院互通** 開始執行。
