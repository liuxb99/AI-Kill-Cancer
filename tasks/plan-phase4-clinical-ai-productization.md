# Phase 4 執行計劃：Clinical AI Productization

> **計劃代號**：Phase-4-Master-Plan  
> **場景**：master-plan（大型規劃）  
> **制定時間**：2026-07-31  
> **基於文件**：`tasks/research/current-capability-inventory.md`  
> **負責角色**：doc-writer  

---

## 目錄

1. [Phase 4 最終能力描述](#1-phase-4-最終能力描述)
2. [完整架構](#2-完整架構)
3. [Data Flow](#3-data-flow)
4. [Security Boundary](#4-security-boundary)
5. [Transaction Boundary](#5-transaction-boundary)
6. [FHIR Boundary](#6-fhir-boundary)
7. [Knowledge Graph Boundary](#7-knowledge-graph-boundary)
8. [External Evidence Boundary](#8-external-evidence-boundary)
9. [Deployment Boundary](#9-deployment-boundary)
10. [Batch 拆分](#10-batch-拆分)
11. [驗收標準](#11-驗收標準)

---

## 1. Phase 4 最終能力描述

Phase 4 完成後，系統從「已開發完成的 AI 原型」升級為「可在臨床環境中產品化運作的 AI 系統」。以下為 Phase 4 結束時系統應具備的全部能力。

### 1.1 核心臨床 AI 能力（繼承 Phase 3，已完整）

| 能力 | 說明 | 來源 |
|------|------|------|
| 變異分析 Pipeline | VCF 上傳 → 正規化 → VEP 註釋 → CIViC/DGIdb 證據查詢 | 既有（Phase 3） |
| 臨床決策引擎 | 規則驅動的臨床決策推薦（5 引擎） | 既有（Phase 3） |
| 多 Agent 協作 | 6 個臨床 Agent（診斷/ guideline/臨床試驗/變異/藥物/抗藥性）+ Orchestrator + Consensus | 既有（Phase 3） |
| 治療計畫管理 | 完整生命週期（草稿→提交→審核→啟動→暫停→完成→取消→修訂） | 既有（Phase 3） |
| 腫瘤委員會工作流 | 多學科團隊審查、投票、共識 | 既有（Phase 3） |
| 知識圖譜（KnowGraphGo） | Go 實作的知識圖譜引擎（推論/模式匹配/遍歷/本體） | 既有（Phase 3） |
| 臨床圖譜事件（Outbox） | 事件驅動的臨床資料變更追蹤 | 既有（Phase 3） |
| Digital Thread | 決策線程完整追蹤（context→evidence→agent→consensus→recommendation） | 既有（Phase 3） |
| 醫師工作台 | 完整的前端工作台（病患摘要/時間線/推薦/腫瘤委員會/筆記） | 既有（Phase 3） |
| RBAC 授權 | 6 角色 + JWT + Case 層級 ACL | 既有（Phase 3） |

### 1.2 Phase 4 新增能力

| # | 能力 | 說明 | 優先級 |
|---|------|------|--------|
| 1 | **FHIR R4 完整互通** | 支援 FHIR R4 核心資源（Patient, Observation, MedicationRequest, DiagnosticReport, Condition, Procedure, CarePlan），提供標準 FHIR REST API，支援 SMART-on-FHIR 授權框架 | P0 |
| 2 | **外部證據源真實連接** | 7 個外部 adapter 從 stub 升級為真實 REST API 連接（CIViC, DGIdb, OncoTree, MyVariant.info, DRKG, PharmCAT, Ensembl VEP local） | P0 |
| 3 | **生產級監控** | Metrics（request rate, latency, error rate）、分散式追蹤（OpenTelemetry）、健康儀表板 | P1 |
| 4 | **CI/CD 補全** | Go pipeline（build + test + lint）+ Docker build/push + 後端部署 pipeline | P1 |
| 5 | **Docker 化部署** | 提供 Dockerfile + docker-compose，支援一鍵部署（後端 + 前端 + 知識圖譜） | P1 |
| 6 | **語義搜尋與 RAG（Deferred）** | 基於 Vector DB 的知識檢索增強生成，支援臨床文獻與證據的語義搜尋。本能力在 Phase 4 中列為 deferred，僅在 Gap Analysis + ADR + Current Capability 共同證明需要時才啟動，否則移至 Phase 5 | P3 |

### 1.3 明確排除在 Phase 4 之外的能力

以下缺口盤點後確認不在 Phase 4 範圍，預留給 Phase 5：

| 能力 | 排除原因 |
|------|---------|
| ML Model Training Pipeline | 盤點顯示 `models/` 僅有 1 個 JSON manifest，從零建置訓練/評估/部署 pipeline 工作量巨大，且需 Phase 4 的基礎設施完成後才能有效運作 |
| HL7 v2 / DICOM / PACS | 完全缺失，屬於醫院深度整合範疇，需專屬 Phase 進行 |
| Multi-specialty Platform 化 | 屬於 Phase 5 Medical AI Platform 的核心目標 |
| Microservices 拆分 | 目前 monolith 設計足以支撐產品化，拆分為微服務為 Phase 5 選項 |
| Kubernetes 編排 | 目前 Docker Compose 足夠，K8s 為 Phase 5 選項 |
| RAG / Vector DB（正式啟用） | 列為 deferred，需 Gap Analysis + ADR + Current Capability 共同證明需要 |
| Background Jobs / Queue（ARQ + Redis） | 不引入 Redis/Kafka 等新增基礎元件，非同步排程使用既有 Outbox 機制 |

---

## 2. 完整架構

### 2.1 高層架構概覽

```
┌─────────────────────────────────────────────────────────────────────┐
│                        External Clinical Data                       │
│  (EHR/EMR · 基因定序儀器 · 公開資料庫 · 臨床試驗登錄 · 文獻資料庫)  │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │   Hospital Integration   │  ← Phase 4 新建
                    │         Layer            │
                    │  ┌──────────────────┐   │
                    │  │  FHIR R4 API     │   │
                    │  │  SMART-on-FHIR   │   │
                    │  │  (Patient/Obser- │   │
                    │  │   vation/MedReq/ │   │
                    │  │   DiagReport/   │   │
                    │  │   CarePlan)     │   │
                    │  └──────────────────┘   │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │   Clinical Intelligence  │  ← Phase 4 擴充
                    │         Layer            │
                    │  ┌───────┐ ┌──────────┐  │
                    │  │ RAG   │ │Knowledge │  │
                    │  │(Defer-│ │  Graph   │  │
                    │  │ red)  │ │(KnowGraph│  │
                    │  │       │ │   Go)    │  │
                    │  └───────┘ └──────────┘  │
                    │  ┌──────────────────┐   │
                    │  │  Evidence Store  │   │
                    │  │(CIViC/DGIdb/    │   │
                    │  │ OncoTree/etc.)  │   │
                    │  └──────────────────┘   │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │      AI Engine Layer     │  ← 既有（Phase 3）
                    │  ┌────┐┌────┐┌──────┐  │
                    │  │Rec-││Cli-││Ranks │  │
                    │  │omm-││nic-││ing   │  │
                    │  │end ││al  ││Eng-  │  │
                    │  │Eng-││Dec-││ine   │  │
                    │  │ine ││isi-││      │  │
                    │  │    ││on  ││      │  │
                    │  └────┘└────┘└──────┘  │
                    │  ┌────┐┌────────────┐  │
                    │  │Rea-││Explainable │  │
                    │  │son-││Engine      │  │
                    │  │ing ││            │  │
                    │  └────┘└────────────┘  │
                    │  ┌──────────────────┐   │
                    │  │  Agent System    │   │
                    │  │(6 Agents + Orch. │   │
                    │  │ + Consensus)     │   │
                    │  └──────────────────┘   │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │    Production Platform   │  ← Phase 4 強化
                    │         Layer            │
                    │  ┌────┐ ┌────┐ ┌────┐  │
                    │  │Auth│ │Obs-│ │API │  │
                    │  │/   │ │erv-│ │Gat-│  │
                    │  │ACL │ │abi-│ │eway│  │
                    │  │    │ │lity│ │    │  │
                    │  └────┘ └────┘ └────┘  │
                    │  ┌────┐ ┌──────────┐   │
                    │  │CI/ │ │  Docker  │   │
                    │  │CD  │ │Deployment│   │
                    │  └────┘ └──────────┘   │
                    └────────────────────────┘
```

### 2.2 各層詳細說明

#### 2.2.1 Clinical Intelligence Layer（臨床智慧層）

本層負責整合所有臨床知識與證據，為上層 AI Engine 提供可信的知識基礎。

| 元件 | 狀態 | Phase 4 工作 |
|------|------|-------------|
| **Knowledge Graph (KnowGraphGo)** | ✅ 既有（13 Go packages） | 無需修改，直接複用。需在 CI 中加入 Go pipeline 確保持續整合 |
| **Evidence Store** | 🟡 既有但 adapter 為 stub | 完成 8 個外部 adapter 的真實實作 |
| **RAG / Vector DB** | 🔴 Deferred | 建置向量資料庫、Embedding pipeline、RAG 檢索服務。Phase 4 中列為 deferred，僅在 Gap Analysis + ADR + Current Capability 共同證明需要時才啟動 |
| **Knowledge Layer (Python)** | ✅ 既有（6 files） | 無需修改，直接複用 |

#### 2.2.2 Hospital Integration Layer（醫院整合層）

本層為 Phase 4 核心新建部分，負責與外部醫院系統互通。

| 元件 | 狀態 | Phase 4 工作 |
|------|------|-------------|
| **FHIR R4 API** | 🟠 既有簡化版（FHIRExporter） | 從 `reporting/renderer.py` 中的 60 行簡化匯出類，升級為完整 FHIR R4 資源模型 + REST API |
| **SMART-on-FHIR** | 🔴 新建 | 實作 SMART-on-FHIR 授權流程，使 EHR 系統可安全啟動本系統 |
| **FHIR Validation** | 🔴 新建 | 導入 FHIR 驗證（fhirpath/fhir-validator），確保產出的 FHIR 資源符合規範 |

#### 2.2.3 AI Engine Layer（AI 引擎層）

本層完全繼承 Phase 3 的既有實作，無需新增引擎，但需與新建的 Clinical Intelligence Layer 和 Hospital Integration Layer 整合。

| 元件 | 狀態 | Phase 4 工作 |
|------|------|-------------|
| Recommendation Engine | ✅ 既有 | 新增 adapter 資料源作為推薦輸入 |
| Clinical Decision Engine | ✅ 既有 | 整合 FHIR 輸入（從 EHR 取得病患資料） |
| Ranking Engine | ✅ 既有 | 無需修改 |
| Reasoning Service | ✅ 既有 | 無需修改（RAG 整合 deferred） |
| Explainable Engine | ✅ 既有 | 無需修改 |
| Agent System（6 Agents + Orchestrator + Consensus） | ✅ 既有 | Agent 可透過 adapter 存取真實外部資料源 |

#### 2.2.4 Production Platform Layer（生產平台層）

本層在 Phase 3 既有基礎上強化，使系統具備生產環境運作能力。

| 元件 | 狀態 | Phase 4 工作 |
|------|------|-------------|
| Auth / ACL | ✅ 既有 | 擴充 SMART-on-FHIR 授權 |
| Observability | 🟡 既有（僅 audit + health） | 新增 metrics（Prometheus）、tracing（OpenTelemetry）、logging 強化 |
| API Gateway | 🟡 既有（FastAPI router） | 新增 FHIR 端點路由 + rate limiting |
| CI/CD | 🟡 既有（Python CI + Vercel） | 新增 Go pipeline + Docker build + 後端部署 |
| Docker Deployment | 🔴 新建 | 建立 Dockerfile（後端/前端/知識圖譜）+ docker-compose |

### 2.3 既有元件複用說明

根據盤點結果，以下元件在 Phase 4 中直接複用，**不修改**：

- `src/backend/domain/` — 25+ 領域模型（直接複用）
- `src/backend/repositories/` — 23 Repository 類（直接複用）
- `src/backend/api/v1/` — 23 路由模組、100+ 端點（直接複用，僅新增 FHIR 路由）
- `src/backend/services/` — 7 Service 類（直接複用）
- `src/backend/agents/` — 6 Agent + Orchestrator + Consensus（直接複用）
- `src/backend/clinical/` — Clinical/Recommendation/Explainable Engine（直接複用）
- `src/backend/reasoning/` — Reasoning Service（直接複用）
- `src/backend/ranking/` — Ranking Engine（直接複用）
- `src/backend/vcf/` — VCF Parser/Validator（直接複用）
- `src/backend/pipeline/` — 所有 pipeline（直接複用）
- `src/backend/knowledge/` — Knowledge Layer（直接複用）
- `src/backend/reporting/` — Reporting（直接複用，FHIR 部分移入新建的 FHIR 模組）
- `src/backend/workbench/` — Workbench Service（直接複用）
- `src/backend/clinical_graph/` — Clinical Graph/Outbox（直接複用）
- `src/backend/observability/` — Audit/Health 框架（保留，擴充而非改寫）
- `KnowGraphGo/` — 13 Go packages（直接複用）
- `src/frontend/src/components/` — 3 組 UI 元件（直接複用）
- `src/frontend/src/pages/` — 14 頁面（直接複用）

---

## 3. Data Flow

### 3.1 核心資料流：從 External Clinical Data 到 Treatment Plan

```
外部臨床資料                           內部系統處理                         最終產出
═══════════════════                   ═══════════════════                 ══════════════

EHR/EMR (FHIR R4)                   ┌──────────────────┐
  ├─ Patient Demographics ──────────→│ FHIR Ingest      │
  ├─ Observations (Labs) ───────────→│ Service          │
  ├─ Conditions (Diagnoses) ────────→│  (Phase 4 新建)  │
  └─ Medication Statements ────────→│                  │
                                     └───────┬──────────┘
                                             │ FHIR→Domain 轉換
                                             ▼
VCF File ( Sequencing )          ┌──────────────────┐
  └─ Somatic/Germline Variants ─→│ VCF Pipeline     │
                                  │ (既有: normaliz- │
                                  │  ation → VEP →   │
                                  │  CIViC/DGIdb)   │
                                  └───────┬──────────┘
                                          │ 變異列表 + 初步證據
                                          ▼
External Knowledge Sources        ┌──────────────────┐
  ├─ CIViC ──────────────────────→│ Adapter Layer    │
  ├─ DGIdb ──────────────────────→│ (Phase 4 實作)  │
  ├─ OncoTree ───────────────────→│ 真實 REST 連接   │
  ├─ MyVariant.info ────────────→│ 同步 / 非同步     │
  ├─ DRKG ───────────────────────→│                  │
  ├─ PharmCAT ───────────────────→│                  │
  └─ Ensembl VEP (local) ───────→│                  │
                                  └───────┬──────────┘
                                          │ 結構化證據
                                          ▼
Clinical Literature & Trials      ┌──────────────────┐
  ├─ PubMed ─────────────────────→│ RAG Pipeline     │
  ├─ ClinicalTrials.gov ────────→│ (Phase 4 Deferred)│
  └─ Internal Knowledge Base ───→│                  │
                                  └──────────────────┘

                          ┌──────────────────────────────────┐
                          │     AI Engine Layer (既有)       │
                          │                                  │
                          │  Agent System                    │
                          │   ├─ Diagnosis Agent             │
                          │   ├─ Guideline Agent             │
                          │   ├─ Clinical Trial Agent        │
                          │   ├─ Variant Agent               │
                          │   ├─ Drug Agent                  │
                          │   └─ Resistance Agent            │
                          │         ↓                        │
                          │  Consensus Engine                │
                          │         ↓                        │
                          │  Recommendation Engine           │
                          │         ↓                        │
                          │  Explainable Engine              │
                          └──────────────┬───────────────────┘
                                         │ 推薦結果 + 推理鏈
                                         ▼
                          ┌──────────────────┐
                          │ Treatment Plan   │
                          │ Service (既有)   │
                          │ Draft → Submit → │
                          │ Approve → Active │
                          │ → (Pause/Complete│
                          │ /Cancel/Revise)  │
                          └───────┬──────────┘
                                  │ 治療計畫
                                  ▼
                          ┌──────────────────┐
                          │ FHIR Export      │
                          │ (Phase 4 升級)   │
                          │ CarePlan Bundle  │
                          │ → EHR            │
                          └──────────────────┘
```

### 3.2 查詢資料流範例：臨床決策請求

```
1. 醫生在前端 Workbench 發起臨床決策請求
   └→ POST /api/v1/clinical/decisions (CaseID)
   
2. 系統收集 Context
   ├→ FHIR Ingest Service → 從 FHIR 端點取得病患 demographics + labs + diagnoses
   ├→ VCF Pipeline → 取得變異列表 + 初步證據
   └→ Knowledge Graph → 查詢已知關係與路徑

3. AI Engine 執行
   ├→ Agent Orchestrator 平行啟動 6 個 Agent
   │   └→ 每個 Agent 從 Adapter Layer 取得外部證據
   │   └→ Consensus Engine 匯聚意見
   ├→ Recommendation Engine 產出推薦
   └→ Explainable Engine 產出推理鏈

4. 結果儲存與呈現
   ├→ Digital Thread 記錄決策線程
   ├→ Clinical Graph Event (Outbox) 發布變更事件
   └→ 前端 Workbench 顯示推薦結果 + 證據 + 推理

5. 醫生審閱後建立治療計畫
   └→ Treatment Plan Service → Draft
   └→ 最終可匯出為 FHIR CarePlan 送回 EHR
```

---

## 4. Security Boundary

### 4.1 現狀（Phase 3）

- ✅ RBAC（6 角色：SYSTEM_ADMIN, DOCTOR, NURSE, RESEARCHER, VIEWER, CASE_MANAGER）
- ✅ JWT Token 認證（AuthService）
- ✅ Case 層級 ACL（CaseACLService）
- ✅ Permission-based 端點保護（require_permission, require_case_access dependencies）
- ✅ 角色-權限映射表（ROLE_PERMISSIONS）

### 4.2 Phase 4 安全邊界擴充

```
┌────────────────────────────────────────────────────────────────────┐
│                        Security Boundary                           │
│                                                                    │
│  ┌──────────────┐    ┌──────────────────┐    ┌────────────────┐   │
│  │  External     │    │  API Gateway     │    │  Internal       │   │
│  │  Request      │───→│                  │───→│  Services      │   │
│  │  (EHR/Doctor) │    │  ┌────────────┐  │    │  (既有)        │   │
│  │               │    │  │ Rate       │  │    │                │   │
│  │               │    │  │ Limiting   │  │    │  ┌──────────┐  │   │
│  │               │    │  └────────────┘  │    │  │ Domain   │  │   │
│  │               │    │  ┌────────────┐  │    │  │ Services │  │   │
│  │               │    │  │ JWT Auth   │  │    │  └──────────┘  │   │
│  │               │    │  └────────────┘  │    │  ┌──────────┐  │   │
│  │               │    │  ┌────────────┐  │    │  │ Engines  │  │   │
│  │               │    │  │ SMART-on-  │  │    │  └──────────┘  │   │
│  │               │    │  │ FHIR Auth  │  │    │  ┌──────────┐  │   │
│  │               │    │  └────────────┘  │    │  │ Agents   │  │   │
│  │               │    │  ┌────────────┐  │    │  └──────────┘  │   │
│  │               │    │  │ RBAC       │  │    │  ┌──────────┐  │   │
│  │               │    │  │ Check      │  │    │  │ Adapters │  │   │
│  │               │    │  └────────────┘  │    │  └──────────┘  │   │
│  │               │    │  ┌────────────┐  │    └────────────────┘   │
│  │               │    │  │ Case ACL   │  │                         │
│  │               │    │  └────────────┘  │    ┌────────────────┐   │
│  └──────────────┘    └──────────────────┘    │  External       │   │
│                                              │  Data Sources   │   │
│  ┌────────────────────────────────────┐      │  (CIViC/DGIdb/  │   │
│  │  Data at Rest Encryption          │      │   OncoTree/... )│   │
│  │  (SQLite/WAL → PG 遷移考量)       │      └────────────────┘   │
│  └────────────────────────────────────┘                           │
│                                                                    │
│  ┌────────────────────────────────────┐                           │
│  │  Audit Log (既有 Observability)   │                           │
│  │  - 所有 FHIR API 存取記錄          │                           │
│  │  - 所有治療計畫修改記錄             │                           │
│  │  - 所有外部 adapter 呼叫記錄       │                           │
│  └────────────────────────────────────┘                           │
└────────────────────────────────────────────────────────────────────┘
```

### 4.3 Phase 4 新增安全需求

| 需求 | 說明 | Batch |
|------|------|-------|
| SMART-on-FHIR 授權 | 支援 EHR 啟動的 SMART-on-FHIR 授權流程（EHR App Launch 或 Standalone Launch） | B1 |
| Rate Limiting | 對 FHIR API 端點實施 rate limiting，防止濫用 | B3 |
| FHIR API 專屬 Audit | FHIR 端點的操作需記錄完整 audit trail（誰、何時、存取哪個資源） | B1 |
| Adapter API Key 管理 | 外部 adapter 的 API key/secret 需安全儲存（環境變數或 secrets manager） | B1/B2 |
| Docker Secrets | Docker Compose 中 secrets 不以明文存在 | B3 |

---

## 5. Transaction Boundary

### 5.1 現有事務邊界（Phase 3）

- **Database transactions**: SQLAlchemy session per request (service 層擁有事務所有權)
- **Outbox pattern**: ClinicalGraphEventService + Outbox Worker 確保事件不丟失
- **Treatment plan workflow**: 狀態機確保狀態轉換原子性（draft→submit→approve→activate→...）
- **Digital Thread**: DecisionNode 以 trace_id 串聯，每個節點獨立持久化

### 5.2 Phase 4 事務邊界

```
Service Owns Transaction
══════════════════════════════════════════════════════════════════
Repository 僅負責 flush，不 commit 也不 rollback。

┌─ Service Layer ──────────────────────────────────────────────┐
│                                                               │
│  Service 負責：                                               │
│  · 開啟 session                                               │
│  · 呼叫 Repository 執行操作（Repository 內部只 flush）        │
│  · 決定 commit 或 rollback                                    │
│  · 關閉 session                                               │
│                                                               │
│  ┌───────────────────────────────────────────────────────┐   │
│  │  FHIR REST API (Phase 4 新建)                         │   │
│  │  ┌──────────────────────────────────────────────┐    │   │
│  │  │ Service: 開啟 session，呼叫 FHIR Repository    │    │   │
│  │  │ Repository: flush only → Service commit       │    │   │
│  │  │ - GET /Patient/{id} → 唯讀，無事務            │    │   │
│  │  │ - POST /Patient → Service commit              │    │   │
│  │  │ - PUT /Patient/{id} → Service commit          │    │   │
│  │  │ - Bundle transaction → Service commit/rollback│    │   │
│  │  └──────────────────────────────────────────────┘    │   │
│  │                                                       │   │
│  │  Clinical Decision API (既有)                         │   │
│  │  ┌──────────────────────────────────────────────┐    │   │
│  │  │ Transaction Scope: Decision + Agent Opinions │    │   │
│  │  │ + Consensus + Recommendations + Digital      │    │   │
│  │  │ Thread                                       │    │   │
│  │  │ Service 管理 session，Repository flush only;  │    │   │
│  │  │ 失敗則 Service rollback                      │    │   │
│  │  └──────────────────────────────────────────────┘    │   │
│  │                                                       │   │
│  │  Treatment Plan API (既有)                            │   │
│  │  ┌──────────────────────────────────────────────┐    │   │
│  │  │ Transaction Scope: State Machine Transition  │    │   │
│  │  │ + Versioning + Outbox Event                  │    │   │
│  │  │ Service 管理 session，Repository flush only;  │    │   │
│  │  │ 失敗則狀態不變（Service rollback）           │    │   │
│  │  └──────────────────────────────────────────────┘    │   │
│  │                                                       │   │
│  │  External Adapter Calls (Phase 4 新建)               │   │
│  │  ┌──────────────────────────────────────────────┐    │   │
│  │  │ Adapter calls 為外部 API 呼叫，不參與本地 DB  │    │   │
│  │  │ 事務。結果以 AdapterResult 封裝儲存。         │    │   │
│  │  │ Service 負責 retry policy（既有 Outbox 機制） │    │   │
│  │  └──────────────────────────────────────────────┘    │   │
│  └───────────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────────────┘
```

### 5.3 跨邊界事務原則

| 原則 | 說明 |
|------|------|
| **Service owns transaction** | Service 層擁有事務所有權；Repository 只做 flush，不 commit 也不 rollback |
| **Local transaction first** | 所有 DB 操作使用本地 SQLAlchemy session 事務 |
| **Outbox for cross-boundary** | 需要跨 service 或跨系統的事務使用既有 Outbox pattern |
| **Adapter calls 不參與本地事務** | 外部 adapter 呼叫不回滾本地事務；失敗由 Service 層 retry policy 處理 |
| **FHIR Bundle as atomic unit** | FHIR Bundle 操作（batch/transaction）保證原子性 |
| **No distributed transactions** | 不使用 2PC/XA，避免跨資料庫分散式事務 |

---

## 6. FHIR Boundary

### 6.1 現狀

- 目前僅有簡化版 FHIR 匯出：`reporting/renderer.py` 中的 `FHIRExporter` 類（~60 行）
- 支援將治療計畫匯出為 FHIR CarePlan Bundle（JSON）
- 僅支援匯出（Export），無完整 REST API、無驗證、無 SMART-on-FHIR

### 6.2 Phase 4 FHIR 邊界

```
FHIR Boundary
══════════════════════════════════════════════════════════════════

┌─ External Clients ──────────────────────────────────────────┐
│                                                               │
│  EHR / EMR System                    SMART App (瀏覽器)       │
│  ┌──────────────────────┐          ┌──────────────────────┐  │
│  │ FHIR REST Client     │          │ SMART-on-FHIR App    │  │
│  │ (Read/Search/Write)  │          │ (EHR Launch /        │  │
│  └──────────┬───────────┘          │  Standalone Launch)  │  │
│             │                      └──────────┬───────────┘  │
│             │                                 │              │
└─────────────┼─────────────────────────────────┼──────────────┘
              │                                 │
              ▼                                 ▼
┌─ FHIR API Layer (Phase 4 新建) ───────────────────────────┐
│                                                               │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  FHIR RESTful Endpoints                              │    │
│  │  GET/POST /fhir/r4/{ResourceType}/{id}              │    │
│  │  GET /fhir/r4/{ResourceType}?param=value            │    │
│  │  PUT /fhir/r4/{ResourceType}/{id}                   │    │
│  │  POST /fhir/r4 (Bundle)                             │    │
│  │  GET /fhir/r4/metadata (CapabilityStatement)        │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  FHIR Resources (Pydantic Models)                    │    │
│  │  Patient, Observation, Condition,                    │    │
│  │  MedicationRequest, DiagnosticReport,                │    │
│  │  Procedure, CarePlan, Bundle, OperationOutcome       │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  FHIR Domain Mapping Layer                          │    │
│  │  Domain Model → FHIR Resource 轉換                   │    │
│  │  FHIR Resource → Domain Model 轉換                   │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  FHIR Validation (fhirpath / fhir-validator)        │    │
│  │  確保產出的 FHIR 資源符合 R4 規範                     │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  SMART-on-FHIR Authorization                         │    │
│  │  - .well-known/smart-configuration                  │    │
│  │  - EHR Launch (後續) / Standalone Launch (初期)     │    │
│  │  - Token exchange + scope validation                │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                               │
└───────────────────────────────────────────────────────────────┘
             │
             ▼
┌─ Backend Services (既有 + 擴充) ────────────────────────────┐
│                                                               │
│  ┌──────────────────────┐  ┌──────────────────────┐          │
│  │ Domain Services     │  │ Clinical Graph +     │          │
│  │ (TreatmentPlan,     │  │ Outbox (既有)        │          │
│  │  ClinicalDecision,  │  │                      │          │
│  │  Workbench, ...)    │  │ 知識圖譜整合         │          │
│  └──────────────────────┘  └──────────────────────┘          │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  Domain Models (既有，不修改)                        │    │
│  │  PatientModel, CancerCaseModel, TreatmentPlanModel,  │    │
│  │  ClinicalDecisionModel, AgentOpinionModel, ...       │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

### 6.3 FHIR 實作原則

| 原則 | 說明 |
|------|------|
| **Incremental** | 先實作唯讀查詢（Read/Search），再實作寫入（Create/Update） |
| **Profile-based** | 使用台灣/美國核心 FHIR Profile 作為參考，但初期不強制符合 |
| **Domain model 為真理來源** | FHIR 資源是 domain model 的序列化視圖，不另建 FHIR 專屬儲存 |
| **向後相容** | 既有 `GET /reports/{id}/fhir` 端點保留，但內部委託給新的 FHIR 模組 |
| **測試優先** | 每個 FHIR 資源端點需有對應的整合測試（使用 FHIR 測試樣本） |

---

## 7. Knowledge Graph Boundary

### 7.1 現狀

- **KnowGraphGo**（Go 實作）：13 packages，35+ 測試檔案，完整知識圖譜引擎
  - 圖資料結構（entity, relation, store, query, evidence, provenance, integrity）
  - 推論引擎（forward/backward chain, rule）
  - 本體論（schema, constraint, inheritance, validator）
  - 模式匹配（matcher, path_pattern）
  - 圖遍歷（BFS, DFS, K-Hop, Cycle, Topo, Path）
  - 解釋引擎（explain）
  - 匯出（CSV, JSON, Markdown）
  - 儲存（memory + SQLite with FTS5）
- **Python 端 Knowledge Layer**：6 檔案（models/repository/service/identifiers/adapters）
- **Clinical Graph (Go)**：Outbox-based 事件驅動同步

### 7.2 Phase 4 知識圖譜邊界

```
Knowledge Graph Boundary
══════════════════════════════════════════════════════════════════

┌─ Knowledge Sources ──────────────────────────────────────────┐
│                                                               │
│  External                                 Internal             │
│  ┌──────────────┐   ┌──────────────┐   ┌─────────────────┐   │
│  │ CIViC        │   │ DGIdb        │   │ Clinical Cases  │   │
│  │ (Variants +  │   │ (Drug-Gene   │   │ (Patient Data,  │   │
│  │  Evidence)   │   │  Interactions)│   │  Diagnoses,     │   │
│  └──────┬───────┘   └──────┬───────┘   │  Treatments)    │   │
│  ┌──────┴───────┐   ┌──────┴───────┐   └────────┬────────┘   │
│  │ OncoTree    │   │ MyVariant    │   ┌─────────────────┐   │
│  │ (Cancer     │   │ (Variant     │   │ Published      │   │
│  │  Types)     │   │  Annotation) │   │ Knowledge      │   │
│  └──────┬───────┘   └──────┬───────┘   │ (PubMed,       │   │
│  ┌──────┴───────┐   ┌──────┴───────┐   │  ClinicalTrials│   │
│  │ DRKG         │   │ PharmCAT     │   │  .gov)        │   │
│  │ (Drug        │   │ (Pharmaco-   │   └────────┬────────┘   │
│  │  Repurposing)│   │  genomics)   │            │            │
│  └──────┬───────┘   └──────┬───────┘            │            │
│         │                  │                     │            │
│         └──────────────────┴─────────────────────┘            │
│                            │                                  │
└────────────────────────────┴──────────────────────────────────┘
                             │
                             ▼
┌─ Ingestion & Mapping ────────────────────────────────────────┐
│                                                               │
│  Adapter Layer (Phase 4 實作)     Knowledge Layer (既有)     │
│  ┌──────────────────────────┐   ┌─────────────────────────┐  │
│  │ CIViCAdapter (REST)      │   │ KnowledgeService       │  │
│  │ DGIdbAdapter (REST)      │──→│ KnowledgeEntityModel   │  │
│  │ OncoTreeAdapter (REST)   │   │ KnowledgeRelationModel │  │
│  │ MyVariantAdapter (REST)  │   │ IdentifierMapper       │  │
│  │ DRKGAdapter (REST)       │   │ Publication Model      │  │
│  │ PharmCATAdapter (REST)   │   │ ClinicalTrial Model    │  │
│  │ EnsemblVEPAdapter (Local)│   │ GuidelineItem Model    │  │
│  └──────────────────────────┘   └─────────────────────────┘  │
│                                                               │
└───────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─ Knowledge Graph Core ────────────────────────────────────────┐
│                                                               │
│  KnowGraphGo (既有，不修改)                                    │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  graph/ (Entity, Relation, Store, Query)             │    │
│  │  inference/ (ForwardChain, BackwardChain, Rule)      │    │
│  │  ontology/ (Schema, Constraint, Validator)           │    │
│  │  traversal/ (BFS, DFS, K-Hop, Cycle, Topo, Path)    │    │
│  │  pattern/ (Matcher, Pattern)                         │    │
│  │  explain/ (Explain)                                  │    │
│  │  export/ (CSV, JSON, Markdown)                       │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                               │
│  Python → Go Bridge (既有)                                    │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  ClinicalGraphService → Outbox Worker → KG Ingest    │    │
│  │  WorkbenchService → KG Query API                    │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                               │
└───────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─ Consumers ───────────────────────────────────────────────────┐
│                                                               │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐   │
│  │ Agent System   │  │ Recommendation │  │ Explainable    │   │
│  │ (6 Agents 查詢 │  │ Engine (規則   │  │ Engine (推理鏈 │   │
│  │  知識圖譜)     │  │  引用 KG 事實) │  │  視覺化 KG 路 │   │
│  └────────────────┘  └────────────────┘  │  徑)           │   │
│                                            └────────────────┘   │
│  ┌────────────────┐  ┌────────────────┐                         │
│  │ Workbench UI   │  │ FHIR Export    │                         │
│  │ (醫師查詢 KG)  │  │ (KG 事實匯出為 │                         │
│  └────────────────┘  │  FHIR 資源)    │                         │
│                       └────────────────┘                         │
└─────────────────────────────────────────────────────────────────┘
```

### 7.3 KG 邊界原則

| 原則 | 說明 |
|------|------|
| **KnowGraphGo 不修改** | Phase 4 不修改 KnowGraphGo 核心程式碼，僅透過 adapter 向其注入新資料 |
| **Adapter 為 KG 的唯一寫入通道** | 所有外部證據源通過 adapter → knowledge layer → KG 這條路徑寫入 |
| **KG 查詢走既有 API** | 既有 `WorkbenchService` 和 `ClinicalGraphService` 的查詢介面不變 |
| **RAG 與 KG 互補（Deferred）** | KG 提供結構化事實查詢（精確），RAG 提供非結構化語義檢索（模糊），兩者不互相取代；RAG 整合移至 Phase 5 |

---

## 8. External Evidence Boundary

### 8.1 現狀

- 7/10 adapter 為 `NotConfiguredAdapter` stub（CIViC, DGIdb, OncoTree, MyVariant, DRKG, PharmCAT, Ensembl VEP）
- 但是 `pipeline/vep_adapter.py`（Ensembl REST API）和 `pipeline/civic_adapter.py`（CIViC REST API）和 `pipeline/dgidb_adapter.py`（DGIdb REST API）有真實實作，但 `adapters/` 目錄下的對應 adapter 仍是 stub
- `knowledge/adapters/` 有 3 個真實 adapter（clinicaltrials.py, clinvar.py, pubmed.py）

### 8.2 Phase 4 External Evidence Boundary

```
External Evidence Boundary
══════════════════════════════════════════════════════════════════

┌─ External Data Sources ───────────────────────────────────────┐
│                                                               │
│  Public APIs                        Local Services            │
│  ┌────────────────────┐  ┌──────────────────────────────┐    │
│  │ CIViC (civicdb.org)│  │ Ensembl VEP (本地或遠端)     │    │
│  │ - Variant Evidence │  │ - Variant Effect Prediction  │    │
│  │ - Clinical Actions │  │ - REST API (既有 pipeline)   │    │
│  └─────────┬──────────┘  └──────────────┬───────────────┘    │
│  ┌─────────┴──────────┐  ┌──────────────┴───────────────┐    │
│  │ DGIdb (dgidb.org)  │  │ PharmCAT (本地)              │    │
│  │ - Drug-Gene Interact│  │ - 藥物基因組學              │    │
│  └─────────┬──────────┘  └──────────────────────────────┘    │
│  ┌─────────┴──────────┐                                        │
│  │ OncoTree           │                                        │
│  │ - Cancer Type Ont. │                                        │
│  └─────────┬──────────┘                                        │
│  ┌─────────┴──────────┐                                        │
│  │ MyVariant.info     │                                        │
│  │ - Variant Annot.   │                                        │
│  └─────────┬──────────┘                                        │
│  ┌─────────┴──────────┐  ┌──────────────┐                     │
│  │ DRKG (Drug Rep.)   │  │ PharmCAT     │                     │
│  │ - Drug Repurposing │  │ - Pharmaco-  │                     │
│  │   Knowledge Graph  │  │   genomics   │                     │
│  └─────────┬──────────┘  └──────┬───────┘                     │
│            │                    │                             │
└────────────┴────────────────────┴─────────────────────────────┘
             │                    │
             ▼                    ▼
┌─ Adapter Layer ────────────────────────────────────────────────┐
│                                                               │
│  **同步 Adapter（Synchronous — 請求/回應即時呼叫）**          │
│  ┌─────────────────────────────────────────────────────┐      │
│  │ · Evidence Retrieval：CIViC, DGIdb, OncoTree,      │      │
│  │   MyVariant.info, DRKG, Ensembl VEP                │      │
│  │ · Clinical Decision：PharmCAT                       │      │
│  │   這類 adapter 在臨床決策請求的同步路徑中被呼叫，   │      │
│  │   回應必須在請求 timeout 內返回。                     │      │
│  └─────────────────────────────────────────────────────┘      │
│                                                               │
│  **非同步 Adapter（Asynchronous — 背景定時觸發）**            │
│  ┌─────────────────────────────────────────────────────┐      │
│  │ · Guideline Sync：定時更新臨床 guideline 資料       │      │
│  │ · Background Refresh：背景重新整理快取知識          │      │
│  │ · Cache Refresh：定期更新 adapter 回應快取          │      │
│  │   這類 adapter 由 scheduler 觸發，不阻塞使用者的    │      │
│  │   臨床決策請求。                                      │      │
│  └─────────────────────────────────────────────────────┘      │
│                                                               │
│  adapters/ (Phase 4 實作)         pipeline/ (既有)           │
│  ┌────────────────────────────┐  ┌────────────────────────┐  │
│  │ CIViCAdapter (新實作)     │  │ vep_adapter.py (既有)  │  │
│  │ DGIdbAdapter (新實作)     │  │ civic_adapter.py (既有)│  │
│  │ OncoTreeAdapter (新實作)  │  │ dgidb_adapter.py (既有)│  │
│  │ MyVariantAdapter (新實作) │  └────────────────────────┘  │
│  │ DRKGAdapter (新實作)      │                               │
│  │ PharmCATAdapter (新實作)  │                               │
│  │ EnsemblVEPAdapter (新實作)│                               │
│  └────────────────────────────┘                               │
│                                                               │
│  注意：pipeline/ 下的 civic/dgidb adapter 已有真實 REST 實作，│
│  但 adapters/ 下的對應項為 stub。Phase 4 策略：               │
│  1. 保留 pipeline/ 既有實作（供 VCF pipeline 使用）           │
│  2. adapters/ 新實作使用 pipeline/ 既有程式碼，            │
│     但以 AdapterRegistry 標準介面包裝                          │
│  3. 最終 registry 中所有 adapter 皆為真實連接                │
│  4. 同步 adapter 走請求/回應模式，非同步 adapter 由排程觸發  │
│                                                               │
└───────────────────────────────────────────────────────────────┘
             │
             ▼
┌─ Cache & Rate Limit ──────────────────────────────────────────┐
│                                                               │
│  - 每個 adapter 需實作 response caching（避免重複呼叫）      │
│  - 遵守上游 API 的 rate limit（CIViC: 10 req/s, DGIdb: ...）│
│  - 使用既有 Outbox retry policy 處理暫時性失敗               │
│  - Health check 端點可查詢每個 adapter 連線狀態              │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

### 8.3 Adapter 分類與實作優先級

| 分類 | 優先級 | Adapter | 資料源類型 | API 文件 | 既有資產 |
|------|--------|---------|-----------|---------|---------|
| **同步** | P0 | CIViCAdapter（Evidence Retrieval） | REST API | ✅ 公開 | pipeline/civic_adapter.py 可參考 |
| **同步** | P0 | DGIdbAdapter（Evidence Retrieval） | REST API | ✅ 公開 | pipeline/dgidb_adapter.py 可參考 |
| **同步** | P1 | EnsemblVEPAdapter（Evidence Retrieval） | REST API | ✅ 公開 | pipeline/vep_adapter.py 可參考（需包裝為標準介面） |
| **同步** | P1 | OncoTreeAdapter（Evidence Retrieval） | REST API | ✅ 公開 | 從零實作 |
| **同步** | P1 | MyVariantAdapter（Evidence Retrieval） | REST API | ✅ 公開 | 從零實作 |
| **同步** | P1 | DRKGAdapter（Evidence Retrieval） | REST API | ✅ 公開 | 從零實作 |
| **同步** | P2 | PharmCATAdapter（Clinical Decision） | Local tool | ✅ 文件 | 從零實作 |
| **非同步** | P1 | Guideline Sync Adapter | REST API | ✅ 公開 | 從零實作 |
| **非同步** | P2 | Background Refresh Adapter | 內部 | N/A | 從零實作（定期重新整理快取知識） |
| **非同步** | P2 | Cache Refresh Adapter | 內部 | N/A | 從零實作（定期更新 adapter 回應快取） |

---

## 9. Deployment Boundary

### 9.1 現狀

- 後端：Python FastAPI，直接 `uvicorn` 啟動
- 前端：React SPA，透過 Vercel 部署
- 知識圖譜：Go CLI，手動編譯執行
- 資料庫：SQLite（開發）+ PostgreSQL（整合測試）
- CI：`.github/workflows/ci.yml`（Python pytest + ruff + mypy）
- CD：`.github/workflows/deploy.yml`（Vercel 前端）

### 9.2 Phase 4 Deployment Boundary

```
Deployment Boundary
══════════════════════════════════════════════════════════════════

┌─ Development Environment ─────────────────────────────────────┐
│                                                               │
│  docker-compose.dev.yml                                       │
│  ┌──────────────────┐  ┌──────────────────┐                  │
│  │ Backend          │  │ Frontend         │                  │
│  │ (FastAPI +       │  │ (React Vite +    │                  │
│  │  uvicorn, :8000) │  │  Vite dev, :5173)│                  │
│  └──────────────────┘  └──────────────────┘                  │
│  ┌──────────────────┐  ┌──────────────────┐                  │
│  │ Knowledge Graph  │  │ Database         │                  │
│  │ (Go, :8080)      │  │ (SQLite / PG)    │                  │
│  └──────────────────┘  └──────────────────┘                  │
│                                                               │
└───────────────────────────────────────────────────────────────┘

┌─ Production Environment ──────────────────────────────────────┐
│                                                               │
│  docker-compose.prod.yml                                      │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  Reverse Proxy (nginx / Caddy)                        │    │
│  │  - TLS termination                                    │    │
│  │  - Rate limiting                                      │    │
│  │  - Static file serving (frontend build)              │    │
│  └────────────────────┬─────────────────────────────────┘    │
│                       │                                      │
│  ┌────────────────────┴─────────────────────────────────┐    │
│  │  Backend (Gunicorn + Uvicorn workers)                │    │
│  │  - Multi-worker (CPU-bound: 2×cores+1)              │    │
│  │  - Health check: /health                             │    │
│  │  - Metrics: /metrics                                 │    │
│  └────────────────────┬─────────────────────────────────┘    │
│                       │                                      │
│  ┌────────────────────┴─────────────────────────────────┐    │
│  │  Knowledge Graph (Go binary)                         │    │
│  │  - Compiled Go server                                │    │
│  │  - Health check endpoint                             │    │
│  └────────────────────┬─────────────────────────────────┘    │
│                       │                                      │
│  ┌────────────────────┴─────────────────────────────────┐    │
│  │  PostgreSQL (Production DB)                         │    │
│  │  - Persistent volume                                │    │
│  │  - Automated backups                                │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                               │
└───────────────────────────────────────────────────────────────┘

┌─ CI/CD Pipeline ──────────────────────────────────────────────┐
│                                                               │
│  GitHub Actions                                               │
│  ┌──────────────────────────────────────────────────────┐    │
│  │ ci.yml (既有，擴充)                                   │    │
│  │   - Python: pytest + ruff + mypy (既有)              │    │
│  │   - Go: go build + go test + golangci-lint (新增)   │    │
│  │   - Frontend: npm test + npm build (既有)            │    │
│  │   - Docker: build + scan (新增)                      │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐    │
│  │ deploy.yml (既有，擴充)                               │    │
│  │   - Vercel frontend deploy (既有)                    │    │
│  │   - Docker image push (新增)                         │    │
│  │   - Backend deploy (新增)                            │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

### 9.3 部署原則

| 原則 | 說明 |
|------|------|
| **Container-first** | 所有元件（後端、前端、知識圖譜）皆容器化（Vector DB deferred） |
| **Single host 起步** | Production 初期使用單一主機 Docker Compose，不引入 K8s |
| **環境分離** | 明確區分 dev/staging/production 三套設定 |
| **Immutable artifact** | CI 產出 Docker image，CD 部署該 image（不 hot-patch） |
| **無狀態後端** | 後端容器不儲存狀態，所有狀態在 PG 中 |
| **Knowledge Graph 獨立** | KnowGraphGo 作為獨立服務部署，透過 gRPC 或 REST 與後端通訊 |

---

## 10. Batch 拆分

### 10.1 Batch 總覽

根據盤點結果，Phase 4 拆分為 **3 個 Vertical Slice Batch**。每個 Batch 皆包含完整端到端能力流，涵蓋 API + Domain + Service + Repository + Frontend + Audit + Knowledge Graph + Digital Thread + CI + PostgreSQL + Migration + Documentation 所有層面。

```
Batch 相依關係：
                 ┌─────────────────────────────────────────────┐
                 │              Phase 4 Foundation              │
                 │  (既有系統 + FHIR Base + Adapter Layer)      │
                 └────────────┬────────────────────┬───────────┘
                              │                    │
           ┌──────────────────┘    ┌───────────────┘
           ▼                       ▼
  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
  │    Batch 1       │  │    Batch 2       │  │    Batch 3       │
  │ 病患資料整合與    │  │ 臨床試驗與        │  │ 藥物安全與監控    │
  │ 臨床工作流        │  │ 證據排序          │  │                  │
  └──────────────────┘  └──────────────────┘  └──────────────────┘
           │                       │                    │
           └───────────────────────┼────────────────────┘
                                   ▼
                      ┌──────────────────────┐
                      │   Phase 4 整合驗收    │
                      │   (所有 Batch 合流)   │
                      └──────────────────────┘
```

| Batch | 名稱 | 核心能力流 | 預估檔案數 | 工時預估 |
|-------|------|-----------|-----------|---------|
| B1 | 病患資料整合與臨床工作流 | Patient Import → Evidence Collection → Recommendation → Treatment Plan → FHIR Export → Audit → Frontend | 18-22 files | 3-4 週 |
| B2 | 臨床試驗與證據排序 | Clinical Trial Matching → Evidence Ranking → Recommendation → Treatment Update → CarePlan → Frontend | 16-20 files | 2-3 週 |
| B3 | 藥物安全與監控 | Drug Safety → Interaction Check → Contraindication → Treatment Revision → Monitoring → FHIR Export | 16-20 files | 2-3 週 |

三個 Batch 可平行啟動，因為每個 Batch 只依賴 Phase 3 既有系統與 Phase 4 Foundation（FHIR Base + Adapter Layer），不互相依賴。

---

### 10.2 Batch 1：病患資料整合與臨床工作流

#### 名稱與目標
**Patient Data Integration & Clinical Workflow** — 建立從病患資料匯入、證據收集、臨床決策推薦、治療計畫管理到 FHIR 匯出的完整端到端能力流。

#### 能力流
```
Patient Import → Evidence Collection → Recommendation → Treatment Plan → FHIR Export → Audit → Frontend
```

#### 功能範圍
1. FHIR R4 資源模型（Patient, Observation, Condition, MedicationRequest, DiagnosticReport, Procedure, CarePlan）
2. FHIR RESTful API（Read/Search/Create/Update 端點）
3. FHIR Domain Model 映射層（Domain Model ↔ FHIR Resource）
4. FHIR 驗證（fhirpath/fhir-validator）
5. CapabilityStatement + SMART-on-FHIR 設定端點
6. 既有 FHIRExporter 整合（reporting/renderer.py 中的簡化版改為委託給新 FHIR 模組）
7. FHIR 端點專屬 Audit Logging
8. 同步 Adapter 整合（CIViC, DGIdb — 證據收集到臨床決策路徑）
9. Clinical Decision Engine 整合 FHIR 輸入
10. Treatment Plan Service 整合（建立/更新治療計畫時寫入 FHIR CarePlan）
11. 前端 Workbench 整合 FHIR 資料展示
12. Digital Thread 記錄決策線程
13. Knowledge Graph 注入（將 FHIR 匯入的臨床資料寫入 KG）
14. 整合測試（使用 FHIR 測試樣本）

#### 預估檔案清單（20 files）

| # | 檔案路徑（預估） | 類型 | 說明 |
|---|----------------|------|------|
| 1 | `src/backend/fhir/__init__.py` | 新建 | FHIR 模組初始化 |
| 2 | `src/backend/fhir/models.py` | 新建 | FHIR R4 資源 Pydantic 模型（Patient, Observation, Condition, MedicationRequest, DiagnosticReport, Procedure, CarePlan, Bundle, OperationOutcome） |
| 3 | `src/backend/fhir/mapping.py` | 新建 | Domain Model ↔ FHIR Resource 映射邏輯 |
| 4 | `src/backend/fhir/validation.py` | 新建 | FHIR 資源驗證（使用 fhirpath 規則） |
| 5 | `src/backend/fhir/service.py` | 新建 | FHIR 服務層（Service 擁有事務所有權） |
| 6 | `src/backend/fhir/repository.py` | 新建 | FHIR 資源儲存庫（flush only，不 commit/rollback） |
| 7 | `src/backend/api/v1/fhir.py` | 新建 | FHIR REST API 路由 |
| 8 | `src/backend/api/v1/fhir_metadata.py` | 新建 | CapabilityStatement + SMART-on-FHIR 端點 |
| 9 | `src/backend/fhir/smart_on_fhir.py` | 新建 | SMART-on-FHIR 授權流程 |
| 10 | `src/backend/fhir/audit.py` | 新建 | FHIR 端點專屬 Audit Logging |
| 11 | `src/backend/reporting/renderer.py` | 修改 | FHIRExporter 改為委託 fhir 模組（向後相容） |
| 12 | `src/backend/adapters/civic.py` | 修改 | CIViCAdapter：從 stub → 真實 REST 實作（同步 Evidence Retrieval） |
| 13 | `src/backend/adapters/dgidb.py` | 修改 | DGIdbAdapter：從 stub → 真實 REST 實作（同步 Evidence Retrieval） |
| 14 | `src/backend/adapters/cache.py` | 新建 | Adapter 回應快取層 |
| 15 | `src/frontend/src/pages/Workbench.tsx` | 修改 | 整合 FHIR 病患資料展示 |
| 16 | `tests/unit/fhir/test_fhir_models.py` | 新建 | FHIR 模型單元測試 |
| 17 | `tests/unit/fhir/test_fhir_mapping.py` | 新建 | FHIR 映射單元測試 |
| 18 | `tests/integration/fhir/test_fhir_api.py` | 新建 | FHIR API 整合測試 |
| 19 | `tests/integration/fhir/test_smart_on_fhir.py` | 新建 | SMART-on-FHIR 流程測試 |
| 20 | `migrations/versions/026_fhir_resource_tables.py` | 新建 | FHIR 資源相關資料庫遷移 |

#### 涉及的角色
- 後端工程師（Python + FHIR 規格 + Adapter 實作）
- 前端工程師（React/TypeScript — Workbench 整合）
- QA 工程師（FHIR 整合測試）
- 架構師（FHIR 映射設計 + Transaction Boundary）

#### 前置依賴
- 無（可直接啟動，基於 Phase 3 既有系統）
- 參考：既有 `reporting/renderer.py` 中的 FHIRExporter 實作
- 參考：既有 Domain Models（PatientModel, CancerCaseModel, TreatmentPlanModel）
- 參考：`pipeline/civic_adapter.py`、`pipeline/dgidb_adapter.py` 既有實作

#### CI 要求
- FHIR 模型單元測試在 Python CI 中執行
- FHIR API 整合測試需要 PostgreSQL service container
- Adapter 單元測試使用 mock，不依賴外部 API
- 整合測試可選標記（需設定 API key）

#### 驗收標準
- [ ] 所有 FHIR 資源端點（Patient/Observation/Condition/MedicationRequest/DiagnosticReport/Procedure/CarePlan）支援 Read/Search
- [ ] Patient 與 CarePlan 支援 Create/Update
- [ ] `GET /fhir/r4/metadata` 回傳有效的 CapabilityStatement
- [ ] 無效 FHIR 資源回傳 OperationOutcome
- [ ] 既有 `GET /reports/{id}/fhir` 向後相容
- [ ] CIViCAdapter 與 DGIdbAdapter 從 stub 升級為真實實作
- [ ] Adapter 快取層實作（TTL 可設定，遵守上游 rate limit）
- [ ] `GET /api/v1/adapters/status` 回傳 adapter 連線狀態
- [ ] 前端 Workbench 可展示 FHIR 匯入的病患資料
- [ ] 所有 FHIR 端點有 audit log
- [ ] Digital Thread 記錄完整決策路徑
- [ ] FHIR 模組整合測試覆蓋率 ≥ 80%

#### 風險
| 風險 | 影響 | 緩解措施 |
|------|------|---------|
| FHIR 規格理解不足導致 mapping 錯誤 | 中 | 使用公開 FHIR 測試樣本驗證；先實作唯讀再實作寫入 |
| SMART-on-FHIR 授權流程複雜 | 高 | 初期只實作 Standalone Launch，EHR Launch 延後 |
| 既有 Domain Model 與 FHIR Resource 不完全對應 | 中 | 建立 mapping layer 而非強求 model 統一；差異部分以 FHIR Extension 處理 |
| 外部 API 變更或下線 | 高 | 每個 adapter 有對應的 mock 測試；registry 支援 graceful degradation |

---

### 10.3 Batch 2：臨床試驗與證據排序

#### 名稱與目標
**Clinical Trial & Evidence Ranking** — 建立臨床試驗匹配與證據排序能力流，從臨床試驗查詢、證據排序、治療建議更新到 CarePlan 產出的完整端到端流程。

#### 能力流
```
Clinical Trial Matching → Evidence Ranking → Recommendation → Treatment Update → CarePlan → Frontend
```

#### 功能範圍
1. 同步 Adapter 實作（OncoTree, MyVariant.info, DRKG, Ensembl VEP — Clinical Trial Matching 與 Evidence Ranking 所需）
2. AdapterRegistry 更新（將 pipeline 既有實作整合進 registry）
3. Ranking Engine 整合外部證據源排序
4. Clinical Trial Matching Service（比對病患變異與臨床試驗條件）
5. Evidence Ranking Service（多來源證據權重排序）
6. Recommendation Engine 整合排序結果
7. Treatment Plan Service 擴充（支援 Clinical Trial 推薦寫入治療計畫）
8. CarePlan FHIR 匯出（治療計畫以 FHIR CarePlan 格式匯出）
9. 前端 Clinical Trial 結果展示
10. Knowledge Graph 注入（臨床試驗匹配結果寫入 KG）
11. Digital Thread 記錄 Clinical Trial 決策線程
12. Audit Log 擴充

#### 預估檔案清單（18 files）

| # | 檔案路徑（預估） | 類型 | 說明 |
|---|----------------|------|------|
| 1 | `src/backend/adapters/oncotree.py` | 修改 | OncoTreeAdapter：從 stub → 真實 REST 實作 |
| 2 | `src/backend/adapters/myvariant.py` | 修改 | MyVariantAdapter：從 stub → 真實 REST 實作 |
| 3 | `src/backend/adapters/drkg.py` | 修改 | DRKGAdapter：從 stub → 真實 REST 實作 |
| 4 | `src/backend/adapters/ensembl_vep.py` | 修改 | EnsemblVEPAdapter：包裝 pipeline/vep_adapter.py 為標準 adapter |
| 5 | `src/backend/adapters/registry.py` | 修改 | 更新 registry 使用真實 adapter 而非 stub |
| 6 | `src/backend/services/clinical_trial_matching.py` | 新建 | 臨床試驗匹配服務 |
| 7 | `src/backend/services/evidence_ranking.py` | 新建 | 證據排序服務（多來源權重計算） |
| 8 | `src/backend/services/treatment_plan_service.py` | 修改 | 擴充支援 Clinical Trial 推薦寫入 |
| 9 | `src/backend/api/v1/clinical_trials.py` | 新建 | 臨床試驗匹配 API 端點 |
| 10 | `src/backend/api/v1/evidence.py` | 新建 | 證據排序查詢 API 端點 |
| 11 | `src/backend/fhir/careplan_export.py` | 新建 | CarePlan FHIR 匯出（治療計畫 → FHIR CarePlan Bundle） |
| 12 | `src/frontend/src/pages/ClinicalTrials.tsx` | 修改 | 臨床試驗結果展示頁面強化 |
| 13 | `src/frontend/src/api/clinical_trials.ts` | 新建 | 臨床試驗 API client |
| 14 | `tests/unit/adapters/test_oncotree_adapter.py` | 新建 | OncoTree adapter 單元測試 |
| 15 | `tests/unit/adapters/test_myvariant_adapter.py` | 新建 | MyVariant adapter 單元測試 |
| 16 | `tests/unit/services/test_clinical_trial_matching.py` | 新建 | 臨床試驗匹配單元測試 |
| 17 | `tests/integration/services/test_evidence_ranking.py` | 新建 | 證據排序整合測試 |
| 18 | `docs/adapters/overview.md` | 新建 | Adapter 架構與使用說明文件 |

#### 涉及的角色
- 後端工程師（Python + REST API 整合 + Ranking）
- 資料工程師（了解各資料源 API 文件與 rate limit）
- 前端工程師（React/TypeScript — Clinical Trial 展示）
- QA 工程師（mock API 測試 + 整合測試）

#### 前置依賴
- 無（可與 Batch 1 平行啟動）
- 參考：`pipeline/vep_adapter.py` 既有實作
- 參考：既有 Ranking Engine 架構
- 參考：既有 Treatment Plan Service 實作

#### CI 要求
- 所有 adapter 單元測試使用 mock，不依賴外部 API
- 整合測試可選標記（需設定 API key）
- 新增 GitHub Actions cache 層減少重複測試

#### 驗收標準
- [ ] OncoTreeAdapter / MyVariantAdapter / DRKGAdapter / EnsemblVEPAdapter 從 stub 升級為真實實作
- [ ] 每個 adapter 至少支援 `annotate()` 和 `health_check()`
- [ ] Clinical Trial Matching Service 可根據病患變異比對臨床試驗條件
- [ ] Evidence Ranking Service 可依權重排序多來源證據
- [ ] Recommendation Engine 可參考排序結果產生推薦
- [ ] Treatment Plan Service 可寫入 Clinical Trial 推薦
- [ ] CarePlan FHIR 匯出產出有效 Bundle
- [ ] `GET /api/v1/adapters/status` 回傳所有 adapter 連線狀態
- [ ] Agent 系統可透過 AdapterRegistry 查詢臨床試驗與證據排序
- [ ] 前端 ClinicalTrials 頁面顯示匹配結果
- [ ] Adapter 單元測試覆蓋率 ≥ 85%

#### 風險
| 風險 | 影響 | 緩解措施 |
|------|------|---------|
| 外部 API 變更或下線 | 高 | 每個 adapter 有對應的 mock 測試；registry 支援 graceful degradation |
| API key 管理不當 | 高 | 使用環境變數搭配 Docker secrets；不在程式碼中硬編碼 |
| Clinical Trial 匹配邏輯複雜 | 中 | 初期以基因變異為主要匹配條件，逐步加入其他條件 |
| Rate limit 導致請求失敗 | 中 | 快取層 + 指數退避 retry（既有 Outbox retry policy） |

---

### 10.4 Batch 3：藥物安全與監控

#### 名稱與目標
**Drug Safety & Monitoring** — 建立藥物安全檢查、交互作用偵測、禁忌症比對、治療方案修訂與監控的完整端到端能力流。

#### 能力流
```
Drug Safety → Interaction Check → Contraindication → Treatment Revision → Monitoring → FHIR Export
```

#### 功能範圍
1. 同步 Adapter 實作（PharmCAT — 臨床決策用）
2. 非同步 Adapter 實作（Guideline Sync, Background Refresh, Cache Refresh — 定時觸發）
3. Drug Safety Service（藥物安全性檢查）
4. Drug Interaction Service（藥物交互作用偵測）
5. Contraindication Service（禁忌症比對）
6. Treatment Revision Service（治療方案修訂建議）
7. Monitoring Service（治療監控指標管理）
8. FHIR Export 擴充（治療監控資料匯出為 FHIR Observation/DiagnosticReport）
9. Knowledge Graph 注入（藥物安全知識寫入 KG）
10. Digital Thread 記錄藥物安全決策線程
11. Audit Log 擴充（藥物安全相關事件記錄）
12. 前端 Monitoring Dashboard 展示
13. CI/CD 基礎設施（Dockerfile + docker-compose + Go CI + Docker CI）
14. 生產級監控（Prometheus metrics + OpenTelemetry tracing + 結構化 logging + Grafana dashboard）
15. 環境設定管理（dev/staging/production 三層設定）
16. 資料庫遷移自動化

#### 預估檔案清單（24 files）

| # | 檔案路徑（預估） | 類型 | 說明 |
|---|----------------|------|------|
| **藥物安全核心（10 files）** |
| 1 | `src/backend/adapters/pharmcat.py` | 修改 | PharmCATAdapter：從 stub → 真實 CLI/REST 實作 |
| 2 | `src/backend/services/drug_safety_service.py` | 新建 | 藥物安全性檢查服務 |
| 3 | `src/backend/services/drug_interaction_service.py` | 新建 | 藥物交互作用偵測服務 |
| 4 | `src/backend/services/contraindication_service.py` | 新建 | 禁忌症比對服務 |
| 5 | `src/backend/services/treatment_revision_service.py` | 新建 | 治療方案修訂建議服務 |
| 6 | `src/backend/services/monitoring_service.py` | 新建 | 治療監控指標管理服務 |
| 7 | `src/backend/api/v1/drug_safety.py` | 新建 | 藥物安全 API 端點 |
| 8 | `src/backend/api/v1/monitoring.py` | 新建 | 監控指標 API 端點 |
| 9 | `src/frontend/src/pages/MonitoringDashboard.tsx` | 新建 | 治療監控儀表板頁面 |
| 10 | `src/frontend/src/api/drug_safety.ts` | 新建 | 藥物安全 API client |
| **CI/CD 與部署（7 files）** |
| 11 | `Dockerfile.backend` | 新建 | 後端 Docker image |
| 12 | `Dockerfile.frontend` | 新建 | 前端 Docker image |
| 13 | `Dockerfile.knowgraph` | 新建 | 知識圖譜 Docker image |
| 14 | `docker-compose.yml` | 新建 | Production Docker Compose |
| 15 | `docker-compose.dev.yml` | 新建 | Development Docker Compose |
| 16 | `.github/workflows/go-ci.yml` | 新建 | Go CI workflow |
| 17 | `.github/workflows/docker-ci.yml` | 新建 | Docker CI workflow |
| **生產監控（7 files）** |
| 18 | `src/backend/observability/metrics.py` | 新建 | Prometheus metrics 定義與收集 |
| 19 | `src/backend/observability/tracing.py` | 新建 | OpenTelemetry 初始化與 middleware |
| 20 | `src/backend/observability/logging.py` | 新建 | 結構化 JSON logging 設定 |
| 21 | `src/backend/observability/health.py` | 修改 | 擴充 health check（加入 adapter/db 健康狀態） |
| 22 | `deploy/observability/prometheus.yml` | 新建 | Prometheus 設定檔 |
| 23 | `deploy/observability/grafana_dashboard.json` | 新建 | Grafana 預設儀表板 |
| 24 | `docs/observability/monitoring.md` | 新建 | 監控架構說明文件 |

#### 涉及的角色
- 後端工程師（Python + Drug Safety + Prometheus + OpenTelemetry）
- DevOps 工程師（Docker + CI/CD + Grafana 儀表板）
- Go 工程師（KG Docker 化）
- 前端工程師（React/TypeScript — Monitoring Dashboard）
- SRE（生產監控策略）

#### 前置依賴
- 無（可與 Batch 1、Batch 2 平行啟動）
- 參考：既有 `observability/audit.py` 實作風格
- 參考：既有 Treatment Plan Service 中的藥物相關邏輯
- 參考：既有 `pipeline/` 中的 adapter 實作

#### CI 要求
- 所有 adapter 單元測試使用 mock，不依賴外部 API
- Metrics 單元測試不依賴實際 Prometheus 實例
- 不引入新的 CI workflow，在既有 Python CI 中擴充
- Go CI 在修改 KnowGraphGo 時自動觸發
- Docker CI 在 main branch push 時觸發

#### 驗收標準
- [ ] PharmCATAdapter 從 stub 升級為真實實作
- [ ] Drug Safety Service 可檢查藥物安全性
- [ ] Drug Interaction Service 可偵測藥物交互作用
- [ ] Contraindication Service 可比對禁忌症
- [ ] Treatment Revision Service 可產生修訂建議
- [ ] Monitoring Service 可管理治療監控指標
- [ ] `GET /api/v1/drug-safety/check` 回傳安全性檢查結果
- [ ] 前端 Monitoring Dashboard 顯示監控指標
- [ ] `GET /metrics` 回傳 Prometheus 格式的 metrics
- [ ] 分散式追蹤可追蹤單一請求跨 service 的完整路徑
- [ ] Health check 端點回傳資料庫、adapter 的詳細狀態
- [ ] 所有 log 為 JSON 結構化格式
- [ ] Grafana 儀表板可視覺化核心指標
- [ ] `docker-compose up` 可一鍵啟動完整系統
- [ ] Go CI workflow 通過 go build + go test + golangci-lint
- [ ] Docker CI workflow 通過 build + security scan
- [ ] 既有 Python CI 和 Vercel 部署不受影響
- [ ] Docker 啟動時自動執行 alembic upgrade
- [ ] 部署文件包含 dev/staging/production 三種情境

#### 風險
| 風險 | 影響 | 緩解措施 |
|------|------|---------|
| 藥物交互作用知識庫不完整 | 中 | 初期支援 PharmCAT 單一來源，後續可擴充 |
| Metrics 引入效能 overhead | 低 | Prometheus client 為低開銷設計；tracing 使用取樣 |
| OpenTelemetry 設定複雜 | 中 | 初期只實作基本 tracing（request → service → adapter），不跨主機 |
| Docker image 過大 | 中 | 使用多階段 build |
| 安全性掃描發現高風險漏洞 | 中 | 使用官方 base image 並定期更新；Trivy 掃描結果納入 CI gate |

---

## 11. 驗收標準

### 11.1 Phase 4 整體 Gate

| Gate | 條件 | 通過標準 |
|------|------|---------|
| **G1: FHIR 互通 Gate** | FHIR R4 API 可供外部 EHR 系統呼叫 | 所有核心資源端點（Patient/Observation/Condition/MedicationRequest/DiagnosticReport/CarePlan）可正常 Read/Search；CapabilityStatement 回傳有效 |
| **G2: 外部證據 Gate** | 7 個外部 adapter 真實連接（同步 + 非同步） | `GET /api/v1/adapters/status` 回傳全部 configured（可能部分 offline 但非 stub）；同步 adapter 走請求/回應模式，非同步 adapter 由排程觸發 |
| **G3: 臨床試驗與證據排序 Gate** | Clinical Trial Matching + Evidence Ranking 可正常運作 | Clinical Trial Matching Service 可比對病患變異與試驗條件；Evidence Ranking Service 可依權重排序多來源證據 |
| **G4: 藥物安全與監控 Gate** | Drug Safety + Interaction Check + Contraindication + Monitoring 完整鏈路 | `GET /api/v1/drug-safety/check` 回傳安全性檢查結果；Monitoring Dashboard 顯示監控指標 |
| **G5: 部署 Gate** | Docker Compose 一鍵啟動 | `docker-compose up` 後系統功能正常；所有 CI pipeline 通過 |
| **G6: 基礎設施與監控 Gate** | Prometheus metrics + OpenTelemetry tracing | `GET /metrics` 回傳有效 metrics；Grafana 儀表板顯示核心指標 |
| **G7: 回歸 Gate** | 既有功能不受影響 | 所有既有測試（~99 Python + 35 Go + 14 Frontend）通過；Service 層擁有正確事務邊界 |

### 11.2 各 Batch 驗收標準

| Batch | 驗收標準摘要 | 測試類型 |
|-------|------------|---------|
| B1 | FHIR R4 資源模型 + REST API + SMART-on-FHIR + CIViC/DGIdb adapter 真實實作 + FHIR Audit + Workbench 整合 | Unit + Integration + FHIR 測試樣本 |
| B2 | OncoTree/MyVariant/DRKG/EnsemblVEP adapter 真實實作 + Clinical Trial Matching + Evidence Ranking + CarePlan FHIR 匯出 | Unit (mock) + Integration (可選) |
| B3 | PharmCAT adapter + Drug Safety + Interaction Check + Contraindication + Monitoring + Docker/CI/CD + Prometheus/OTEL/Grafana | Unit + Integration + CI pipeline + 手動驗證 |

### 11.3 禁止事項確認（Phase 4）

- [ ] ❌ 不修改 KnowGraphGo 核心套件（直接複用，僅透過 CI 確保品質）
- [ ] ❌ 不修改 25 個領域模型（直接複用）
- [ ] ❌ 不建立空殼 API 或 placeholder frontend
- [ ] ❌ 不引入 Kubernetes（Docker Compose 足矣）
- [ ] ❌ 不引入 Redis / Kafka / Vector DB / Qdrant / Chroma（除非 Gap Analysis + ADR + Current Capability 共同證明需要）
- [ ] ❌ 不開始 ML Model Training Pipeline（預留給 Phase 5）
- [ ] ❌ 不開始 HL7/DICOM/PACS Integration（預留給 Phase 5）
- [ ] ❌ 不進行 Microservices 拆分（維持 monolith）
- [ ] ❌ 不進行大型 Service Refactor（treatment_plan_service.py 拆分）
- [ ] ❌ 不進行 Frontend 重構（前端 API Client 統一封裝、Tools/KnowledgeBase/Research 頁面強化）
- [ ] ❌ 不完成 OpenCRAVAT Pipeline（stub 維持 stub）
- [ ] ❌ 不使用 mock 結果聲稱 integration ready

### 11.4 總交付檢查清單

- [ ] **plan-phase4-clinical-ai-productization.md** — 本文件
  - [ ] 最終能力描述（含既有 + 新增能力）
  - [ ] 完整架構（4 層文字 Component Diagram）
  - [ ] Data Flow（外部資料到治療計畫的完整路徑）
  - [ ] Security Boundary（擴充 SMART-on-FHIR）
  - [ ] Transaction Boundary（Service owns transaction，Repository flush only）
  - [ ] FHIR Boundary（從簡化版到完整 R4）
  - [ ] Knowledge Graph Boundary（既有 KG + 新 adapter 注入）
  - [ ] External Evidence Boundary（同步 + 非同步 adapter 分類）
  - [ ] Deployment Boundary（Docker + CI/CD）
  - [ ] 3 個 Vertical Slice Batch（每 Batch 10-25 files，垂直涵蓋所有層面）
  - [ ] 驗收標準（7 個 Gate + 各 Batch 標準）
  - [ ] 禁止事項確認（不含 Service Refactor / Frontend 重構 / OpenCRAVAT / RAG / Redis / Kafka）

### 11.5 退出標準

Phase 4 完成並通過所有 Gate 後，系統可進入 Phase 5（Medical AI Platform）：
- ML Model Training Pipeline 啟動
- HL7/DICOM/PACS 整合開始
- Multi-specialty Platform 化設計
- Microservices 可行性評估
- RAG / Vector DB 正式評估與啟動

---

> **文件結束** — Phase 4 Clinical AI Productization Master Plan
