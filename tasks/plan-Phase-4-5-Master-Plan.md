# Phase 4 & Phase 5 Master Plan — 執行計劃

> **計劃代號**：Phase-4-5-Master-Plan  
> **場景**：master-plan（大型規劃與調研）  
> **制定時間**：2026-07-30  
> **總負責角色**：PLANNER  

---

## 1. 執行策略

### 1.1 整體流程

本輪不修改任何 production code，產出 7 項規劃文件。整體採用 **「先盤點、後分析、再規劃」** 的三階段流程，最大化並行效率。

```
階段 I：專案現況盤點（串行起頭）
   └─ T-01 盤點程式碼庫 → 產出 current-capability-inventory.md
   
階段 II：Gap Analysis + 兩份 Master Plan（可並行）
   ├─ T-02 Gap Analysis ──────────────────────→ phase4-phase5-gap-analysis.md
   ├─ T-03 Phase 4 Master Plan（基於盤點 + Gap）→ plan-phase4-clinical-ai-productization.md
   └─ T-04 Phase 5 Master Plan（基於盤點 + Gap）→ plan-phase5-medical-ai-platform.md

階段 III：整合產出（串行）
   ├─ T-05 Dependency Map（基於 T-02/T-03/T-04）→ phase4-phase5-dependency-map.md
   ├─ T-06 Development Roadmap（基於 T-05）    → roadmap-phase4-phase5.md
   └─ T-07 ADR（必要時基於架構決策）            → docs/adr/ 系列
```

### 1.2 執行模式

| 模式 | 說明 |
|------|------|
| **Vertical Batch** | 不切割成小步驟，每次產出一份完整文件 |
| **子代理並行** | T-02、T-03、T-04 可並行執行（互不衝突） |
| **串行閘門** | T-01 完成後方可啟動階段 II；T-05/T-06/T-07 需階段 II 完成後啟動 |

### 1.3 角色分配

| 角色 | 負責任務 | 說明 |
|------|---------|------|
| **PLANNER** | 全流程管控、T-01 盤點、最終品質檢查 | 統籌規劃 |
| **explorer** | T-01 程式碼盤點執行 | 深入檢視程式碼目錄與檔案內容 |
| **doc-writer** | T-02～T-06 文件撰寫 | 根據盤點結果與分析撰寫文件 |
| **REVIEWER** | 最終評分 | 依 AGENTS.md 評分標準審查所有產出 |

---

## 2. 任務清單

### 階段 I：專案現況盤點（必要前置）

| 任務ID | 任務名稱 | 負責角色 | 前置依賴 | 預計產出 | 預估工時 |
|--------|---------|---------|---------|---------|---------|
| **T-01** | 程式碼盤點與現況調查 | PLANNER + explorer | 無 | `tasks/research/current-capability-inventory.md` | 2～3h |

**T-01 詳細說明**：
- 遍歷 `src/backend/`、`frontend/src/`、`KnowGraphGo/`、`models/`、`migrations/`、`tests/`、`config/`、`api/` 目錄
- 對每個維度標記 Complete / Partial / Stub / Missing / TechDebt
- 盤點維度：Domain Models、Services、Repositories、API Routes、Engines（Clinical/Ranking/Reasoning）、Frontend Pages、Adapters、Agents、Pipeline、Auth/ACL、Migration、CI/CD、Knowledge Graph (Go)、Outbox、Observability、Deployment、Testing、Documentation
- 所有標記必須有具體檔案路徑與行號佐證，不得虛構

---

### 階段 II：分析與規劃（可並行）

| 任務ID | 任務名稱 | 負責角色 | 前置依賴 | 預計產出 | 預估工時 |
|--------|---------|---------|---------|---------|---------|
| **T-02** | Gap Analysis 撰寫 | doc-writer | T-01 | `tasks/research/phase4-phase5-gap-analysis.md` | 2～3h |
| **T-03** | Phase 4 Master Plan 撰寫 | doc-writer | T-01 | `tasks/plan-phase4-clinical-ai-productization.md` | 3～4h |
| **T-04** | Phase 5 Master Plan 撰寫 | doc-writer | T-01 | `tasks/plan-phase5-medical-ai-platform.md` | 2～3h |

**T-02 要求**：必須包含 As-Is / To-Be / Gap / Dependencies / Risks / Priority / Blocking Relationships 七個欄位。

**T-03 要求**：
- 最終能力描述
- 架構設計（含 Component Diagram 文字描述）
- Data Flow
- Security / FHIR / KG / Deployment Boundary
- Batch 拆分（每 Batch 10～25 files）
- 驗收標準

**T-04 要求**：
- Oncology 耦合盤點
- Registry / Plugin 化設計
- Specialty Module Contract
- Batch 拆分

---

### 階段 III：整合產出（串行）

| 任務ID | 任務名稱 | 負責角色 | 前置依賴 | 預計產出 | 預估工時 |
|--------|---------|---------|---------|---------|---------|
| **T-05** | Dependency Map 撰寫 | doc-writer | T-02, T-03, T-04 | `tasks/phase4-phase5-dependency-map.md` | 1.5～2h |
| **T-06** | Development Roadmap 撰寫 | doc-writer | T-05 | `tasks/roadmap-phase4-phase5.md` | 1.5～2h |
| **T-07** | Architecture Decision Records | doc-writer | T-03, T-04 | `docs/adr/` 系列（僅必要） | 1～2h |

**T-05 要求**：
- 標示 Parallel / Sequential / External Dependencies
- 包含 Gantt 圖表文字描述

**T-06 要求**：
- 以 Batch 和 Gate 表示開發路線圖
- 每個 Gate 定義驗收標準

**T-07 原則**：
- 只建立確實必要的 ADR
- 預計 ADR 主題：
  - ADR-001: Phase 4 階段劃分策略
  - ADR-002: FHIR 整合策略（若需要）
  - ADR-003: Platform 化註冊機制設計（若需要）
- 不為了數量大量產出空文件

---

## 3. 並行策略

```
時間軸 →
─────────────────────────────────────────────

T-01 [串行] 程式碼盤點
  │
  ├──→ T-02 [並行] Gap Analysis ──→
  ├──→ T-03 [並行] Phase 4 Plan ──→
  └──→ T-04 [並行] Phase 5 Plan ──→
                                      │
                                      ├──→ T-05 [串行] Dependency Map
                                      │         │
                                      │         └──→ T-06 [串行] Roadmap
                                      │
                                      └──→ T-07 [並行] ADR（可與 T-05/T-06 並行）

                                      └──→ REVIEWER [最終] 評分審查
```

### 3.1 並行組合說明

| 並行組 | 任務 | 條件 |
|--------|------|------|
| 組 A（3 個子代理並行） | T-02 + T-03 + T-04 | T-01 完成後同時啟動 |
| 組 B（2 個子代理並行） | T-05 + T-07 | T-02～T-04 完成後可同時啟動 |
| 組 C（獨立） | T-06 | T-05 完成後啟動 |

### 3.2 並行注意事項

- T-02/T-03/T-04 雖然並行，但 doc-writer 需先閱讀 T-01 產出的盤點文件
- 如果 doc-writer 只有一個，則組 A 內任務改為串行執行，順序為 T-02 → T-03 → T-04
- T-07（ADR）可與 T-05/T-06 並行，因為 ADR 僅記錄架構決策，不依賴 dependency map 或 roadmap

---

## 4. 調研方法（T-01 程式碼盤點）

### 4.1 盤點範圍

```
src/backend/          → 後端核心（Domain / Service / Repository / API / Engine / Adapter / Agent / Pipeline / Auth / VCF / Workbench / Reasoning / Ranking / Reporting / Clinical Graph / Observability）
frontend/src/         → 前端（Pages / Components / API Client / Tests）
KnowGraphGo/          → Go 知識圖譜引擎（Store / Inference / Traversal / Pattern / Ontology / Export / Explain / CLI）
models/               → Python AI 模型（Classifier / Drug Discovery / Literature Analyzer / etc.）
migrations/versions/  → Alembic Migration（25 個版本）
tests/                → 後端測試（Unit / Integration / Acceptance）
config/               → 配置設定
api/                  → API 路由 index
docs/                 → 技術文件
.github/workflows/    → CI/CD 配置
```

### 4.2 盤點方法

1. **目錄掃描**：使用 `ls -R` 了解每個目錄的檔案構成
2. **索引查詢**：使用 `code_index` 工具進行 outline 和 search
3. **關鍵檔案閱讀**：對每個維度選擇 1～3 個核心檔案確認其實作深度
4. **Grep 搜索**：對特定 pattern（如 `commit()`、`synthetic`、`TODO`、`FIXME`、`MOCK`、`placeholder`）搜索以確認技術債
5. **測試覆蓋**：瀏覽 tests/ 目錄確認測試存在性與覆蓋範圍

### 4.3 盤點維度與證據要求

| 維度 | 證據收集方式 |
|------|------------|
| Domain Models | 閱讀 `src/backend/domain/` 各檔案，確認模型欄位與方法 |
| Services | 閱讀 `src/backend/services/` 各檔案，確認方法完整性 |
| Repositories | 閱讀 `src/backend/repositories/` 各檔案，確認 CRUD + 特殊方法 |
| API Routes | 閱讀 `src/backend/api/v1/` 各檔案，確認端點清單 |
| Engines | 閱讀 `src/backend/clinical/`、`ranking/`、`reasoning/` |
| Adapters | 閱讀 `src/backend/adapters/` 和 `knowledge/adapters/` |
| Agents | 閱讀 `src/backend/agents/` |
| Pipeline | 閱讀 `src/backend/pipeline/` |
| Frontend | 閱讀 `frontend/src/pages/`、`components/`、`api/` |
| Knowledge Graph | 閱讀 `KnowGraphGo/` 各套件 |
| Migration | 閱讀 `migrations/versions/` 確認版本演進 |
| CI/CD | 閱讀 `.github/workflows/` |
| Tests | 閱讀 `tests/` 目錄結構與檔案大小 |
| Observability | 閱讀 `src/backend/observability/` |
| Auth | 閱讀 `src/backend/auth/` |
| Technical Debt | grep 搜索 TODO / FIXME / synthetic / placeholder / MOCK |

### 4.4 盤點輸出格式

每個維度使用以下格式輸出：

```markdown
### [維度名稱] — [狀態標籤]

**狀態**：✅ Complete / 🟡 Partial / 🟠 Stub / 🔴 Missing / ⚠️ TechDebt

**證據**：
- `path/to/file.py`：具體實作內容說明
- `path/to/file.py:L123-150`：關鍵方法行號

**備註**：
- 已知問題 / TODO 項目
- 與其他維度的關係
```

---

## 5. 返工預案

### 5.1 評分標準

| 評分維度 | 權重 | 說明 |
|----------|------|------|
| 完整性 | 25 | 7 項產出是否完整、盤點是否全面 |
| 正確性 | 25 | 盤點是否基於真實程式碼、分析是否準確 |
| 可執行性 | 25 | 規劃是否可行、Batch 拆分是否合理 |
| 架構與風險控制 | 25 | 風險識別是否充分、架構決策是否合理 |
| **總分** | **100** | **≥90 合格** |

### 5.2 Gate 檢查

| Gate 名稱 | 檢查重點 | 一票否決 |
|-----------|---------|---------|
| Current State Evidence Gate | 所有盤點必須有檔案路徑與行號佐證 | ✅ 任一維度無證據即 FAIL |
| Vertical Slice Quality Gate | Phase 4 Batch 須涵蓋所有層面 | ✅ 遺漏任何層面即 FAIL |
| Dependency Gate | 依賴關係無循環、明確 | ✅ 有循環依賴即 FAIL |
| Scope Control Gate | 不超出規劃範圍（不寫 production code） | ✅ 超出即 FAIL |
| Phase 4 Feasibility Gate | 技術與資源上可行 | ✅ 明顯不可行即 FAIL |
| Phase 5 Platformization Gate | 真正平台化，非僅 rename | ✅ 未達平台化即 FAIL |

**任一 Gate FAIL → 無論總分多少，直接判定不合格，啟動返工。**

### 5.3 返工流程

```
if 總分 < 90 或任一 Gate FAIL:
    循環次數 = 0
    do:
        1. PLANNER 讀取評分報告，重新規劃（修正缺失項目）
        2. 對應子代理按新計劃重新執行
        3. 需求回歸檢查
        4. REVIEWER 重新評分
        5. 循環次數 + 1
    while (總分 < 90 && 循環次數 < 5)
    
    if 循環次數 >= 5 且仍 < 90:
        標記「阻塞⚠️ → 啟動 DeepSeek MCP 顧問」
```

### 5.4 常見返工原因與對策

| 返工原因 | 對策 |
|---------|------|
| 盤點不完整（漏掉某個維度） | 補盤點，重新檢查對應目錄 |
| 盤點無檔案證據 | explorer 重新提取具體檔案路徑與行號 |
| Batch 拆分不合理 | 重新分析依賴關係，調整 Batch 邊界 |
| Gap Analysis 不準確 | 重新對比 As-Is 與 To-Be |
| 平台化設計不足 | 深入分析 Oncology 耦合，提出具體解耦方案 |
| ADR 缺失關鍵決策 | 補寫對應 ADR |

---

## 6. 里程碑與交付檢查清單

### 6.1 里程碑

| 里程碑 | 完成條件 | 預計時間點 |
|--------|---------|-----------|
| M1: 盤點完成 | T-01 產出 `current-capability-inventory.md` | 階段 I 結束 |
| M2: 分析完成 | T-02/T-03/T-04 產出完成 | 階段 II 結束 |
| M3: 整合完成 | T-05/T-06/T-07 產出完成 | 階段 III 結束 |
| M4: 評分通過 | REVIEWER 評分 ≥ 90，所有 Gate PASS | 最終 |

### 6.2 最終交付檢查清單

- [ ] `tasks/research/current-capability-inventory.md` — 專案現況盤點
  - [ ] Domain Models 盤點
  - [ ] Services 盤點
  - [ ] Repositories 盤點
  - [ ] API Routes 盤點
  - [ ] Engines 盤點（Clinical / Ranking / Reasoning）
  - [ ] Adapters 盤點
  - [ ] Agents 盤點
  - [ ] Pipeline 盤點
  - [ ] Frontend 盤點
  - [ ] Knowledge Graph (Go) 盤點
  - [ ] Migration 盤點
  - [ ] CI/CD 盤點
  - [ ] Auth/ACL 盤點
  - [ ] Observability 盤點
  - [ ] Testing 盤點
  - [ ] Documentation 盤點
  - [ ] 每個維度都有檔案路徑佐證

- [ ] `tasks/research/phase4-phase5-gap-analysis.md` — Gap Analysis
  - [ ] As-Is 現況描述
  - [ ] To-Be 目標描述
  - [ ] Gap 缺口分析
  - [ ] Dependencies 依賴關係
  - [ ] Risks 風險識別
  - [ ] Priority 優先級排序
  - [ ] Blocking Relationships 阻擋關係

- [ ] `tasks/plan-phase4-clinical-ai-productization.md` — Phase 4 Master Plan
  - [ ] 最終能力描述
  - [ ] 架構設計
  - [ ] Data Flow
  - [ ] Component Diagram
  - [ ] Security / FHIR / KG / Deployment Boundary
  - [ ] Batch 拆分（每 Batch 10～25 files）
  - [ ] 驗收標準
  - [ ] 每個 Vertical Slice 涵蓋所有層面

- [ ] `tasks/plan-phase5-medical-ai-platform.md` — Phase 5 Master Plan
  - [ ] Oncology 耦合盤點
  - [ ] Registry / Plugin 化設計
  - [ ] Specialty Module Contract
  - [ ] Batch 拆分

- [ ] `tasks/phase4-phase5-dependency-map.md` — Dependency Map
  - [ ] Parallel 任務標示
  - [ ] Sequential 任務標示
  - [ ] External Dependencies 標示
  - [ ] 無循環依賴

- [ ] `tasks/roadmap-phase4-phase5.md` — Development Roadmap
  - [ ] 以 Batch 和 Gate 表示
  - [ ] 每個 Gate 定義驗收標準

- [ ] Architecture Decision Records（必要才建立）
  - [ ] ADR-001: Phase 4 階段劃分策略
  - [ ] ADR-002: FHIR 整合策略（若需要）
  - [ ] ADR-003: Platform 化註冊機制設計（若需要）

### 6.3 Gate 驗收確認

- [ ] **Current State Evidence Gate**：所有盤點可追溯至真實檔案 ✅
- [ ] **Vertical Slice Quality Gate**：Phase 4 Batch 涵蓋所有層面 ✅
- [ ] **Dependency Gate**：依賴無循環 ✅
- [ ] **Scope Control Gate**：未超出規劃範圍 ✅
- [ ] **Phase 4 Feasibility Gate**：技術與資源可行 ✅
- [ ] **Phase 5 Platformization Gate**：真正平台化設計 ✅

### 6.4 禁止事項確認

- [ ] ❌ 未修改任何 production code
- [ ] ❌ 未建立空殼 API 或 placeholder frontend
- [ ] ❌ 未引入 Kubernetes 或 microservices
- [ ] ❌ 未無證據引入 Kafka / Redis / Vector DB
- [ ] ❌ 未虛構已有能力
- [ ] ❌ 未使用 mock 結果宣稱 integration ready

---

## 7. 附錄：預估總工時

| 任務 | 預估工時 | 角色 |
|------|---------|------|
| T-01 程式碼盤點 | 2～3h | PLANNER + explorer |
| T-02 Gap Analysis | 2～3h | doc-writer |
| T-03 Phase 4 Master Plan | 3～4h | doc-writer |
| T-04 Phase 5 Master Plan | 2～3h | doc-writer |
| T-05 Dependency Map | 1.5～2h | doc-writer |
| T-06 Roadmap | 1.5～2h | doc-writer |
| T-07 ADR | 1～2h | doc-writer |
| REVIEWER 評分 | 1h | REVIEWER |
| **總計** | **14～20h** | |

> 若 doc-writer 僅有一位，階段 II 改為串行執行，總工時約 18～24h。
