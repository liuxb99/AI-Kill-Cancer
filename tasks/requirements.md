# Phase 4 & Phase 5 Master Plan 规划需求

> 本文件定義 Phase 4 與 Phase 5 的 Master Plan 規劃任務範圍、產出交付物、品質標準與禁止事項。

---

## 1. 任務名稱

**Phase 4 & Phase 5 Master Plan 規劃**

---

## 2. 當前狀態

| 項目 | 狀態 |
|------|------|
| Phase 1～3E | ✅ 已完成 |
| Phase 3F-0 Transaction Boundary Hardening | ✅ 正式 Accepted |
| master 分支合併 | ✅ 已完成 |
| 原 Phase 4 / 5 / 6 / 7 四個獨立大階段 | 🔄 合併為兩大階段（詳下） |

---

## 3. 新階段總覽

### Phase 4：Clinical AI Productization

> 合併原本 Clinical Intelligence + Hospital Integration + Production Platform

**目標**：按大型端到端 Vertical Slice 推進，每個 Slice 包含：
- Clinical AI
- Evidence
- Knowledge Graph
- Hospital Integration
- Security / Audit
- Persistence
- Observability
- CI
- Frontend
- Deployment readiness

### Phase 5：Medical AI Platform

> 將 AI-Kill-Cancer 從 Oncology application 提升為可支援多疾病、多專科的 Medical AI Platform

**目標**：
- Oncology 耦合盤點與解耦
- Registry / Plugin 化架構
- Specialty Module Contract 定義
- 多疾病、多專科支援能力

---

## 4. 本輪任務範圍

**只產出規劃與架構文件，不修改 production code。**

必須產出以下文件（共 7 項）：

### 4.1 專案現況盤點

**文件**：`tasks/research/current-capability-inventory.md`

盤點項目（每項標示狀態）：

| 盤點維度 | 狀態標籤選項 |
|----------|-------------|
| Domain / Service / Repository / API / Engine / Frontend | Complete / Partial / Stub / Missing / TechDebt |
| Migration / CI / Auth / Audit / KG / DT / Outbox / Background / Deployment / FHIR / RAG | Complete / Partial / Stub / Missing / TechDebt |

### 4.2 Gap Analysis

**文件**：`tasks/research/phase4-phase5-gap-analysis.md`

內容須包含：
- 現況（As-Is）
- 目標（To-Be）
- 缺口（Gap）
- 依賴（Dependencies）
- 風險（Risks）
- 優先級（Priority）
- 阻擋關係（Blocking Relationships）

### 4.3 Phase 4 Master Plan

**文件**：`tasks/plan-phase4-clinical-ai-productization.md`

內容須包含：
- 最終能力描述
- 架構設計
- Data Flow
- Component Diagram
- Security / FHIR / KG / Deployment Boundary
- Batch 拆分（每個 Batch 10～25 files）
- 驗收標準（Acceptance Criteria）

### 4.4 Phase 5 Master Plan

**文件**：`tasks/plan-phase5-medical-ai-platform.md`

內容須包含：
- Oncology 耦合盤點
- Registry / Plugin 化設計
- Specialty Module Contract
- Batch 拆分

### 4.5 Dependency Map

**文件**：`tasks/phase4-phase5-dependency-map.md`

內容須標示：
- 可並行（Parallel）任務
- 串行（Sequential）任務
- 外部依賴（External Dependencies）

### 4.6 Development Roadmap

**文件**：`tasks/roadmap-phase4-phase5.md`

以 **Batch** 和 **Gate** 表示開發路線圖。

### 4.7 Architecture Decision Records（ADR）

**原則**：只建立確實必要的 ADR，不要為了數量大量產生空文件。

---

## 5. 加速原則

1. **不再把任務切成過小步驟**
2. **每次完成一個大型 Vertical Batch**
3. **子代理可並行處理互不衝突的模組**
4. **中途不要頻繁詢問使用者**
5. **完成後統一執行以下檢查與提交流程**：
   - Lint
   - Unit tests
   - PostgreSQL tests
   - Integration tests
   - Frontend 驗證
   - Migration gate
   - Security gate
   - Reviewer 審查
   - Commit + Push
6. **每批 production scope 原則為 10～25 files**

---

## 6. Reviewer 評分標準

| 評分維度 | 權重 |
|----------|------|
| 完整性（Completeness） | 25 |
| 正確性（Correctness） | 25 |
| 可執行性（Executability） | 25 |
| 架構與風險控制（Architecture & Risk Control） | 25 |
| **總分** | **100** |

- **總分低於 90 必須返工**

### 額外 Gate

| Gate 名稱 | 說明 |
|-----------|------|
| Current State Evidence Gate | 必須基於真實專案現況，不可虛構 |
| Vertical Slice Quality Gate | 每個 Vertical Slice 須完整涵蓋所有層面 |
| Dependency Gate | 依賴關係須明確且無循環依賴 |
| Scope Control Gate | 不得超出規劃範圍 |
| Phase 4 Feasibility Gate | Phase 4 規劃必須在技術與資源上可行 |
| Phase 5 Platformization Gate | Phase 5 須真正達成平台化，非僅 rename |

---

## 7. 禁止事項

| # | 禁止事項 |
|---|---------|
| 1 | ❌ 禁止開始寫 production code |
| 2 | ❌ 禁止建立大量空殼 API 或 placeholder frontend |
| 3 | ❌ 禁止一開始就做 Kubernetes 或拆 microservices |
| 4 | ❌ 禁止無證據引入 Kafka / Redis / Vector DB |
| 5 | ❌ 禁止虛構已有能力 |
| 6 | ❌ 禁止使用 mock 結果宣稱 integration ready |

---

## 8. 交付檢查清單

- [ ] `tasks/research/current-capability-inventory.md`
- [ ] `tasks/research/phase4-phase5-gap-analysis.md`
- [ ] `tasks/plan-phase4-clinical-ai-productization.md`
- [ ] `tasks/plan-phase5-medical-ai-platform.md`
- [ ] `tasks/phase4-phase5-dependency-map.md`
- [ ] `tasks/roadmap-phase4-phase5.md`
- [ ] Architecture Decision Records（必要才建立）
