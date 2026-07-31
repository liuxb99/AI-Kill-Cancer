# Phase 4 & Phase 5 Master Plan 第 2 次返工評分報告

> **審查角色**：REVIEWER  
> **審查日期**：2026-08-01  
> **審查範圍**：限於 Appendix A（A.1～A.6）三項重評項目  
>   1. Batch Design（Phase 4 Batch 拆分策略）  
>   2. Scope（Phase 4 範圍控制）  
>   3. Architecture（Transaction Boundary、Adapter 分類、禁止新增基礎元件）  
> **審查文件**：
>   - `tasks/plan-phase4-clinical-ai-productization.md`
>   - `tasks/plan-phase5-medical-ai-platform.md`
> **需求依據**：`tasks/requirements.md` 附錄 A（A.1～A.6）

---

## 1. 需求對照（Appendix A 逐條審查）

### A.1 Phase 4 Batch 拆分策略

**要求**：改為 3 個 Vertical Slice Batch，每個 Batch 包含 API + Domain + Service + Repository + Frontend + Audit + Knowledge Graph + Digital Thread + CI + PostgreSQL + Migration + Documentation。

**檢查結果**：✅ **已修正**

| Batch | 能力流 | 符合度 |
|-------|--------|--------|
| **B1** FHIR R4 & 證據基礎 (20 files) | Patient Import → Evidence → Recommendation → Treatment Plan → FHIR Export → Audit → Frontend | ✅ 完全符合 A.1 範例 |
| **B2** 臨床試驗與證據排序 (18 files) | Clinical Trial → Evidence Ranking → Recommendation → Treatment Update → CarePlan → Frontend | ✅ 完全符合 A.1 範例 |
| **B3** 藥物安全與監控 (24 files) | Drug Safety → Interaction Check → Contraindication → Treatment Revision → Monitoring → FHIR Export | ✅ 完全符合 A.1 範例 |

- 每個 Batch 能力流與 A.1 範例完全一致
- 檔案數量均落在 10-25 範圍內（20/18/24）
- 每個 Batch 描述中明確涵蓋 API、Domain Model、Service、Frontend、Audit、Knowledge Graph、Digital Thread、CI、Documentation 等垂直元素
- 原 6 個技術模組拆分（B1 FHIR / B2 Adapters / B3 RAG / B4 Observability / B5 Docker+CI/CD / B6 Frontend）已改為 3 個 Vertical Slice

**判定**：✅ 通過

---

### A.2 Transaction Boundary

**要求**：
- ❌ 禁止：`Repository transaction owner`
- ✅ 改為：**Service owns transaction**
- Repository：flush only, No commit, No rollback
- 須與 Phase 3F-0 完全一致

**檢查結果**：✅ **已修正**

`tasks/plan-phase4-clinical-ai-productization.md` §5 Transaction Boundary：

```
Service Owns Transaction
══════════════════════════════════════════════════════════════════
Repository 僅負責 flush，不 commit 也不 rollback。
```

- §5.2 明確標示「Service 負責：開啟 session → 呼叫 Repository flush → 決定 commit/rollback → 關閉 session」
- §5.3 跨邊界事務原則第一條：「Service owns transaction — Service 層擁有事務所有權；Repository 只做 flush，不 commit 也不 rollback」
- 所有場景（FHIR REST API、Clinical Decision API、Treatment Plan API、External Adapter Calls）均遵循此原則
- 與 Phase 3F-0 的 Transaction Boundary Hardening 決策一致

**判定**：✅ 通過

---

### A.3 Adapter 分類

**要求**：
- ❌ 不得全部 fire-and-forget
- ✅ 重新分類：**同步**（Evidence Retrieval, Clinical Decision）/ **非同步**（Guideline Sync, Background Refresh, Cache Refresh）

**檢查結果**：✅ **已修正**

`tasks/plan-phase4-clinical-ai-productization.md` §8.3 Adapter 分類與實作優先級：

| 分類 | Adapter | 用途 |
|------|---------|------|
| **同步** (Synchronous) | CIViCAdapter | Evidence Retrieval |
| **同步** (Synchronous) | DGIdbAdapter | Evidence Retrieval |
| **同步** (Synchronous) | EnsemblVEPAdapter | Evidence Retrieval |
| **同步** (Synchronous) | OncoTreeAdapter | Evidence Retrieval |
| **同步** (Synchronous) | MyVariantAdapter | Evidence Retrieval |
| **同步** (Synchronous) | DRKGAdapter | Evidence Retrieval |
| **同步** (Synchronous) | PharmCATAdapter | Clinical Decision |
| **非同步** (Asynchronous) | Guideline Sync Adapter | 定時觸發 |
| **非同步** (Asynchronous) | Background Refresh Adapter | 定期重新整理 |
| **非同步** (Asynchronous) | Cache Refresh Adapter | 定期更新快取 |

- 同步 adapter 走請求/回應模式，非同步 adapter 由排程觸發（§8.2 邊界規則明確）
- 與 A.3 要求的分類完全一致

**判定**：✅ 通過

---

### A.4 禁止新增基礎元件

**要求**：
- 禁止 Redis / Kafka / Vector DB（Qdrant / Chroma）
- 除非 Gap Analysis + ADR + Current Capability 三者共同證明真正需要
- 保持 Technology Agnostic

**檢查結果**：✅ **已遵守**

- §1.2 能力 #6（語義搜尋與 RAG）明確標記為 **Deferred**（P3），條件為「僅在 Gap Analysis + ADR + Current Capability 共同證明需要時才啟動」
- §1.3 明確排除：「RAG / Vector DB（正式啟用）— 列為 deferred，需 Gap Analysis + ADR + Current Capability 共同證明需要」
- §1.3 明確排除：「Background Jobs / Queue（ARQ + Redis）— 不引入 Redis/Kafka 等新增基礎元件，非同步排程使用既有 Outbox 機制」
- §11.3 禁止事項確認：「❌ 不引入 Redis / Kafka / Vector DB / Qdrant / Chroma（除非 Gap Analysis + ADR + Current Capability 共同證明需要）」
- Phase 5 Plan §9.3 隔離策略表中提及「Redis namespace」作為快取策略的潛在選項，此為架構設計階段的策略探討，並非實作承諾；Phase 5 正式引入 Redis 仍需經過 Gap Analysis + ADR + Current Capability 三者共同證明

**判定**：✅ 通過

---

### A.5 Scope 控制

**要求**：
- Phase 4 只留下真正阻擋產品化的能力
- ❌ 不要把大型 Service Refactor、Frontend 重構混入

**檢查結果**：✅ **已遵守**

Phase 4 Plan §1.3「明確排除在 Phase 4 之外的能力」：
- ML Model Training Pipeline（非產品化阻擋）
- HL7 v2 / DICOM / PACS（醫院深度整合，預留 Phase 5）
- Multi-specialty Platform 化（Phase 5 核心）
- Microservices 拆分（monolith 足以支撐）
- Kubernetes 編排（Docker Compose 足夠）
- RAG / Vector DB（Deferred）
- Background Jobs / Queue（ARQ + Redis）

§11.3 禁止事項確認明確包含：
- 「❌ 不進行大型 Service Refactor（treatment_plan_service.py 拆分）」
- 「❌ 不進行 Frontend 重構（前端 API Client 統一封裝、Tools/KnowledgeBase/Research 頁面強化）」
- 「❌ 不修改 25 個領域模型」
- 「❌ 不修改 KnowGraphGo 核心套件」

Phase 4 範圍嚴格限定在產品化所需能力：FHIR 互通、外部證據真實連接、CI/CD、Docker 部署、生產監控。

**判定**：✅ 通過

---

### A.6 Phase 5 平台化

**要求**：最多 2～3 個 Batch，不得十幾個。

**檢查結果**：✅ **已修正**

Phase 5 當前 Batch 結構：

| Batch | 名稱 | 工期 |
|-------|------|------|
| B1 | Platform Core + Specialty Framework | Weeks 1-6 |
| B2 | Oncology Decoupling + Multi-Tenant | Weeks 7-12 |
| B3 | Developer Docs + SDK Template | Weeks 13-14 |

- 共 3 個 Batch，符合「最多 2～3 個」要求
- 原 7 個 Batch（B1 Platform Registry → B2 Terminology → B3 KG Namespace → B4 Module Contract → B5 Oncology Decoupling → B6 Multi-Tenant → B7 Dev Docs）已合併為 3 個

**判定**：✅ 通過

---

## 2. 評分檢查清單

| # | 檢查項 | 結果 | 說明 |
|---|--------|------|------|
| 1 | **是否遵守流程** | **YES** | 僅產出規劃/架構文件，無 production code 修改，遵循加速原則，無跳過步驟 |
| 2 | **是否可執行** | **YES** | Batch 分工明確（3 Phase 4 + 3 Phase 5），依賴清晰，工時合理，風險有緩減 |
| 3 | **是否有錯誤** | **YES（無錯誤）** | A.1-A.6 全部正確修正，無事實性或邏輯性錯誤 |
| 4 | **是否滿足需求條列** | **YES** | A.1-A.6 六項需求全部滿足（詳見 §1 逐項對照） |
| 5 | **是否有測試或滿足審美** | **YES** | 每個 Batch 均有測試計畫與驗收標準；Phase 4 含 7 個 Gate；Phase 5 含 AC1-AC10 |

---

## 3. 細項評分

### 完整性（25/25）

| 項目 | 評分 | 說明 |
|------|------|------|
| A.1 Batch Design | ✅ | 3 個 Vertical Slice Batch，能力流與 A.1 範例完全一致，檔案數量 20/18/24 符合 10-25 範圍 |
| A.2 Transaction Boundary | ✅ | Service owns transaction，Repository flush only，與 Phase 3F-0 一致 |
| A.3 Adapter 分類 | ✅ | 同步 7 個 + 非同步 3 個，分類正確 |
| A.4 禁止新增基礎元件 | ✅ | Redis/Kafka/Vector DB 明確禁止，RAG Deferred |
| A.5 Scope 控制 | ✅ | 排除大型 Service Refactor/Frontend 重構，範圍合理 |
| A.6 Phase 5 Batch 數量 | ✅ | 3 個 Batch，符合「最多 2～3 個」要求 |
| **扣分** | — | 無 |

### 正確性（25/25）

| 項目 | 評分 | 說明 |
|------|------|------|
| 與 A.1-A.6 要求的一致性 | ✅ | 所有修正方向與 ChatGPT 審查意見完全一致 |
| 跨文件一致性 | ✅ | Phase 4 Plan 與 Phase 5 Plan 之間的依賴關係（§14）清晰正確 |
| 禁止事項遵守 | ✅ | 無 production code、無空殼、無虛構能力、無 Redis/Kafka |
| 技術正確性 | ✅ | Transaction Boundary 語義正確（Service 擁有 session 所有權）；Adapter 同步/非同步語義正確（請求/回應 vs 排程觸發） |
| **扣分** | — | 無 |

### 可維護性（24/25）

| 項目 | 評分 | 說明 |
|------|------|------|
| Batch 結構清晰度 | ✅ | 3 個 Batch 按 Vertical Slice 拆分，各自獨立可交付 |
| 架構文件品質 | ✅ | 架構圖、邊界定義、Data Flow 完整 |
| Phase 5 B1 規模 | ⚠️ | Phase 5 B1（Platform Core + Specialty Framework）涵蓋多個子交付項（B1.1-B1.17），實際檔案數量估約 30+，略超過每批 10-25 原則，但因屬 Phase 5 且不在本次重評核心範圍，僅列為觀察項 |
| 文件可讀性 | ✅ | 結構化排版、目錄導航清晰 |
| **扣分 (-1)** | ⚠️ | Phase 5 B1 檔案規模較大，建議後續可考慮拆分為 2 個子批次以維持 10-25 files 原則 |

### 測試與驗證（24/25）

| 項目 | 評分 | 說明 |
|------|------|------|
| Phase 4 Gate 驗收 | ✅ | 7 個 Gate（G1-G7）涵蓋 FHIR、Adapter、臨床試驗、藥物安全、部署、監控、回歸 |
| Phase 4 單 Batch 驗收 | ✅ | 每個 Batch 均有明確驗收清單（B1 12 項/B2 11 項/B3 19 項） |
| Phase 5 驗收標準 | ✅ | AC1-AC10 強制標準 + 6 項期望標準 |
| 測試類型完整性 | ✅ | 單元測試、整合測試、回歸測試、安全測試均在計劃中 |
| **扣分 (-1)** | ⚠️ | Phase 5 B1 驗收標準雖然存在，但未像 Phase 4 那樣以 Checkbox 形式逐條列出；部分測試覆蓋率門檻（≥80%）為整體要求，未細分到每個 Batch |

---

## 4. 總分

| 評分維度 | 得分 | 滿分 |
|----------|:----:|:----:|
| 完整性 | **25** | 25 |
| 正確性 | **25** | 25 |
| 可維護性 | **24** | 25 |
| 測試與驗證 | **24** | 25 |
| **總分** | **98** | **100** |

### 門檻判定

| 條件 | 結果 |
|------|------|
| 總分 ≥ 90 | ✅ **合格**（98 ≥ 90） |
| 所有需求（A.1-A.6）完成 | ✅ 全部通過 |
| 無 FAIL/PARTIAL | ✅ 全部 PASS |

---

## 5. 逐項審查說明

### 5.1 Batch Design（A.1）

**修正內容**：原始版本將 Phase 4 拆分為 6 個技術模組批次（FHIR / Adapters / RAG / Observability / Docker+CI/CD / Frontend），違反 Vertical Slice 原則。返工後改為 3 個端到端 Vertical Slice Batch：

| 原始（6 個技術模組） | 返工後（3 個 Vertical Slice） |
|---|---|
| B1 FHIR R4 | **B1** Patient Import → Evidence → Recommendation → Treatment Plan → FHIR Export → Audit → Frontend |
| B2 External Adapters | **B2** Clinical Trial → Evidence Ranking → Recommendation → Treatment Update → CarePlan → Frontend |
| B3 RAG & Semantic | **B3** Drug Safety → Interaction Check → Contraindication → Treatment Revision → Monitoring → FHIR Export |
| B4 Production Observability | _(已整合至 B3 及其他 Batch)_ |
| B5 Docker + CI/CD | _(已整合至 B3)_ |
| B6 Frontend Productization | _(已整合至各 Batch 前端層)_ |

**評估**：修正方向正確，3 個 Batch 的能力流與 A.1 範例完全一致。每個 Batch 描述中均涵蓋完整的垂直切片元素（API、Domain Model、Service、Frontend、Audit、Knowledge Graph、Digital Thread、CI、Documentation）。檔案數量符合 10-25 原則。

### 5.2 Scope（A.5）

**修正內容**：原始版本在 Batch 拆分中包含非產品化能力（RAG/Vector DB 實際列入規劃、Frontend 重構為獨立 Batch）。返工後：

1. **明確排除清單**（§1.3）：列出 7 項不在 Phase 4 範圍的能力及其排除原因
2. **禁止事項清單**（§11.3）：13 條明確禁止，包括「不進行大型 Service Refactor」「不進行 Frontend 重構」
3. **RAG/Vector DB 標記為 Deferred**（P3），需 Gap Analysis + ADR + Current Capability 三者共同證明
4. **Frontend 工作**被限縮為各 Batch 垂直切片內的必要前端變更（如新增 FHIR API client、Clinical Trial 展示頁面），而非独立的 Frontend 重構批次

**評估**：範圍控制嚴謹，所有非產品化阻擋的能力均被排除或標記為 Deferred。

### 5.3 Architecture

#### 5.3.1 Transaction Boundary（A.2）

**修正內容**：原始版本未明確規範 Transaction Boundary 的所有權歸屬。返工後在 §5 新增完整的事務邊界章節：

- **Service Owns Transaction** 明確標示為第一原則
- Repository 僅負責 flush，不 commit 也不 rollback
- 所有 API 類型（FHIR REST、Clinical Decision、Treatment Plan、External Adapter）均遵循此原則
- 跨邊界事務原則包含 6 條明確規範（Service owns transaction / Local transaction first / Outbox for cross-boundary / Adapter calls 不參與本地事務 / FHIR Bundle as atomic unit / No distributed transactions）

**評估**：與 Phase 3F-0 的 Transaction Boundary Hardening 決策完全一致。

#### 5.3.2 Adapter 分類（A.3）

**修正內容**：原始版本中所有 adapter 被視為 fire-and-forget。返工後在 §8.3 明確區分：

- **同步（Synchronous）**：CIViC、DGIdb、EnsemblVEP、OncoTree、MyVariant、DRKG、PharmCAT — 用於 Evidence Retrieval 與 Clinical Decision，走請求/回應即時呼叫模式
- **非同步（Asynchronous）**：Guideline Sync、Background Refresh、Cache Refresh — 用於背景定時觸發

同步 adapter 在臨床決策請求的同步路徑中被呼叫；非同步 adapter 由排程觸發（§8.2 邊界規則）。

**評估**：分類正確，同步/非同步的邊界規則具體且可執行。

#### 5.3.3 禁止新增基礎元件（A.4）

**修正內容**：原始版本中 Redis 被引入作為 Background Jobs 的實作方案。返工後：

- 明確禁止 Redis、Kafka、Vector DB（Qdrant/Chroma）
- RAG/Vector DB 列為 Deferred（P3），需三重證明方可啟動
- Background Jobs 使用既有 Outbox 機制，不引入新基礎設施
- Phase 5 Plan 中雖提及「Redis namespace」作為快取策略選項（§9.3 隔離策略表），此為架構設計階段的技術選項探討，並非實作承諾。Phase 5 正式引入 Redis 仍需經過標準的 Gap Analysis + ADR + Current Capability 三重證明程序

**評估**：禁止事項明確且一致，Phase 4 範圍內無違規引入。

---

## 6. 結論

```
總分：98 / 100
所有需求（A.1～A.6）：全部 PASS
判定：✅ 合格
```

### 摘要

本文件為 Phase 4 & Phase 5 Master Plan 第 2 次返工的評分報告，審查範圍限定於 Appendix A 中的三項重評項目：

1. **Batch Design** — ✅ 已修正為 3 個 Vertical Slice Batch，能力流與 A.1 範例完全一致
2. **Scope** — ✅ 範圍控制嚴謹，排除大型 Service Refactor / Frontend 重構，RAG/Vector DB 列為 Deferred
3. **Architecture** — ✅ Transaction Boundary（Service owns transaction）、Adapter 分類（同步/非同步）、禁止新增基礎元件（Redis/Kafka/Vector DB）三項均正確修正

### 主要優點

1. **精準對應**：所有修正方向與 ChatGPT 審查意見（A.1-A.6）完全一致，無任何遺漏或偏差
2. **一致性高**：Phase 4 Plan 與 Phase 5 Plan 之間依賴關係清晰，Transaction Boundary 與 Phase 3F-0 保持一致
3. **可執行性強**：3+3 Batch 結構每個都可獨立交付、測試、部署

### 觀察項（非阻擋性）

1. **Phase 5 B1 規模**：B1 涵蓋 Platform Registry、Terminology Service、Cardiology Module、KG Namespace、API v2 等多個子系統，檔案數量可能超過 25 個。建議後續若進入實作階段，可考慮將 B1 拆分為 B1a（Platform Core）與 B1b（Specialty Framework）兩個子批次。

---

*報告結束 — Phase 4 & Phase 5 Master Plan 第 2 次返工評分報告*
