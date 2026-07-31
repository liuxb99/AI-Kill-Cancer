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
| 2 | **外部證據源真實連接** | 8 個外部 adapter 從 stub 升級為真實 REST API 連接（CIViC, DGIdb, OncoTree, MyVariant.info, DRKG, PharmCAT, Ensembl VEP local, OpenCRAVAT） | P0 |
| 3 | **語義搜尋與 RAG** | 基於 Vector DB 的知識檢索增強生成，支援臨床文獻與證據的語義搜尋 | P1 |
| 4 | **生產級監控** | Metrics（request rate, latency, error rate）、分散式追蹤（OpenTelemetry）、健康儀表板 | P1 |
| 5 | **CI/CD 補全** | Go pipeline（build + test + lint）+ Docker build/push + 後端部署 pipeline | P1 |
| 6 | **前端 API Client 統一封裝** | 建立統一 axios instance + interceptor + 型別生成，消除重複 request helper | P2 |
| 7 | **前端頁面強化** | Tools.tsx, KnowledgeBase.tsx, Research.tsx 從簡略頁面升級為完整功能頁面 | P2 |
| 8 | **Service 重構** | `treatment_plan_service.py`（58842B）依職責拆分為多個子 service | P2 |
| 9 | **OpenCRAVAT Pipeline 完成** | pipeline/opencravat_adapter.py 從 stub 升級為真實實作 | P2 |
| 10 | **Docker 化部署** | 提供 Dockerfile + docker-compose，支援一鍵部署（後端 + 前端 + 知識圖譜） | P1 |
| 11 | **Background Jobs / Queue** | 非同步任務佇列支援（ARQ + Redis），提供 job 註冊/排程/取消 API、定期任務排程器、job 狀態監控；支撐 Evidence Freshness 與 Guideline Sync 等定時任務 | P0 |

### 1.3 明確排除在 Phase 4 之外的能力

以下缺口盤點後確認不在 Phase 4 範圍，預留給 Phase 5：

| 能力 | 排除原因 |
|------|---------|
| ML Model Training Pipeline | 盤點顯示 `models/` 僅有 1 個 JSON manifest，從零建置訓練/評估/部署 pipeline 工作量巨大，且需 Phase 4 的基礎設施完成後才能有效運作 |
| HL7 v2 / DICOM / PACS | 完全缺失，屬於醫院深度整合範疇，需專屬 Phase 進行 |
| Multi-specialty Platform 化 | 屬於 Phase 5 Medical AI Platform 的核心目標 |
| Microservices 拆分 | 目前 monolith 設計足以支撐產品化，拆分為微服務為 Phase 5 選項 |
| Kubernetes 編排 | 目前 Docker Compose 足夠，K8s 為 Phase 5 選項 |

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
                    │  │  RAG  │ │Knowledge │  │
                    │  │Vector │ │  Graph   │  │
                    │  │  DB   │ │(KnowGraph│  │
                    │  │Embed- │ │   Go)    │  │
                    │  │ ding  │ │          │  │
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
| **RAG / Vector DB** | 🔴 新建 | 建置向量資料庫（建議 Chroma 或 Qdrant）、Embedding pipeline（利用既有 clinical 文本）、RAG 檢索服務 |
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
| Reasoning Service | ✅ 既有 | 整合 RAG 檢索結果 |
| Explainable Engine | ✅ 既有 | 無需修改 |
| Agent System（6 Agents + Orchestrator + Consensus） | ✅ 既有 | Agent 可透過 adapter 存取真實外部資料源 |

#### 2.2.4 Production Platform Layer（生產平台層）

本層在 Phase 3 既有基礎上強化，使系統具備生產環境運作能力。

| 元件 | 狀態 | Phase 4 工作 |
|------|------|-------------|
| Auth / ACL | ✅ 既有 | 擴充 SMART-on-FHIR 授權 |
| Observability | 🟡 既有（僅 audit + health） | 新增 metrics（Prometheus）、tracing（OpenTelemetry）、logging 強化 |
| Background Jobs Service | 🔴 新建 | ARQ worker + Redis，提供非同步任務佇列、定期排程器、job 生命週期管理；支撐 Evidence Freshness、Guideline Sync 等定時任務 |
| API Gateway | 🟡 既有（FastAPI router） | 新增 FHIR 端點路由 + rate limiting |
| CI/CD | 🟡 既有（Python CI + Vercel） | 新增 Go pipeline + Docker build + 後端部署 |
| Docker Deployment | 🔴 新建 | 建立 Dockerfile（後端/前端/知識圖譜）+ docker-compose |

### 2.3 既有元件複用說明

根據盤點結果，以下元件在 Phase 4 中直接複用，**不修改**：

- `src/backend/domain/` — 25+ 領域模型（直接複用）
- `src/backend/repositories/` — 23 Repository 類（直接複用）
- `src/backend/api/v1/` — 23 路由模組、100+ 端點（直接複用，僅新增 FHIR 路由）
- `src/backend/services/` — 7 Service 類（直接複用，僅拆分 treatment_plan_service）
- `src/backend/agents/` — 6 Agent + Orchestrator + Consensus（直接複用）
- `src/backend/clinical/` — Clinical/Recommendation/Explainable Engine（直接複用）
- `src/backend/reasoning/` — Reasoning Service（直接複用）
- `src/backend/ranking/` — Ranking Engine（直接複用）
- `src/backend/vcf/` — VCF Parser/Validator（直接複用）
- `src/backend/pipeline/` — 大部分 pipeline（直接複用，僅 OpenCRAVAT 需完成）
- `src/backend/knowledge/` — Knowledge Layer（直接複用）
- `src/backend/reporting/` — Reporting（直接複用，FHIR 部分移入新建的 FHIR 模組）
- `src/backend/workbench/` — Workbench Service（直接複用）
- `src/backend/clinical_graph/` — Clinical Graph/Outbox（直接複用）
- `src/backend/observability/` — Audit/Health 框架（保留，擴充而非改寫）
- `KnowGraphGo/` — 13 Go packages（直接複用）
- `src/frontend/src/components/` — 3 組 UI 元件（直接複用）
- `src/frontend/src/pages/` — 14 頁面（直接複用，僅 Tools/KnowledgeBase/Research 需強化）

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
  ├─ MyVariant.info ────────────→│                  │
  ├─ DRKG ───────────────────────→│                  │
  ├─ PharmCAT ───────────────────→│                  │
  ├─ Ensembl VEP (local) ───────→│                  │
  └─ OpenCRAVAT ────────────────→│                  │
                                  └───────┬──────────┘
                                          │ 結構化證據
                                          ▼
Clinical Literature & Trials      ┌──────────────────┐
  ├─ PubMed ─────────────────────→│ RAG Pipeline     │
  ├─ ClinicalTrials.gov ────────→│ (Phase 4 新建)   │
  └─ Internal Knowledge Base ───→│                  │
                                  │ Embedding →      │
                                  │ Vector DB →      │
                                  │ Semantic Search  │
                                  └───────┬──────────┘
                                          │ 語義相關知識
                                          ▼
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
| Rate Limiting | 對 FHIR API 端點實施 rate limiting，防止濫用 | B4/B5 |
| FHIR API 專屬 Audit | FHIR 端點的操作需記錄完整 audit trail（誰、何時、存取哪個資源） | B1 |
| Adapter API Key 管理 | 外部 adapter 的 API key/secret 需安全儲存（環境變數或 secrets manager） | B2 |
| Vector DB 存取控制 | RAG 服務需有適當認證，防止未授權查詢 | B3 |
| Docker Secrets | Docker Compose 中 secrets 不以明文存在 | B5 |

---

## 5. Transaction Boundary

### 5.1 現有事務邊界（Phase 3）

- **Database transactions**: SQLAlchemy session per request (repository 層)
- **Outbox pattern**: ClinicalGraphEventService + Outbox Worker 確保事件不丟失
- **Treatment plan workflow**: 狀態機確保狀態轉換原子性（draft→submit→approve→activate→...）
- **Digital Thread**: DecisionNode 以 trace_id 串聯，每個節點獨立持久化

### 5.2 Phase 4 事務邊界

```
API Request Boundary
═══════════════════════════════════════════════════════════
┌─ Request ──────────────────────────────────────────────┐
│                                                         │
│  FHIR REST API (Phase 4 新建)                           │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Transaction Scope: Single FHIR Resource Operation│   │
│  │ - GET /Patient/{id} → 唯讀，無事務               │   │
│  │ - POST /Patient → 單一 session commit            │   │
│  │ - PUT /Patient/{id} → 單一 session commit        │   │
│  │ - Conditional operations → 單一 session commit   │   │
│  │ Bundle transaction → 原子提交或全部回滾          │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  Clinical Decision API (既有)                           │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Transaction Scope: Decision + Agent Opinions    │   │
│  │ + Consensus + Recommendations + Digital Thread  │   │
│  │ 全部在單一 session 內，失敗則全部回滾            │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  Treatment Plan API (既有)                              │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Transaction Scope: State Machine Transition    │   │
│  │ + Versioning + Outbox Event                    │   │
│  │ submit/approve/activate 等狀態轉換為原子操作    │   │
│  │ 失敗則狀態不變                                   │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  External Adapter Calls (Phase 4 新建)                  │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Transaction Scope: Adapter calls 為外部 API 呼叫 │   │
│  │ 不參與本地 DB 事務。結果以 AdapterResult 封裝    │   │
│  │ 儲存。失敗有 retry policy（既有 Outbox 機制）    │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### 5.3 跨邊界事務原則

| 原則 | 說明 |
|------|------|
| **Local transaction first** | 所有 DB 操作使用本地 SQLAlchemy session 事務 |
| **Outbox for cross-boundary** | 需要跨 service 或跨系統的事務使用既有 Outbox pattern |
| **Adapter calls are fire-and-forget** | 外部 adapter 呼叫不回滾本地事務；失敗由 retry policy 處理 |
| **FHIR Bundle as atomic unit** | FHIR Bundle 操作（batch/transaction）保證原子性 |
| **No distributed transactions** | 不使用 2PC/XA，避免跨資料庫分散式事務 |

---

## 6. FHIR Boundary

### 6.1 現狀

- `src/backend/reporting/renderer.py:L74-135` — FHIRExporter 類（60 行），產出簡化 FHIR R4 Bundle（Composition + Section）
- `src/backend/api/v1/reports.py:L154-162` — 唯讀端點 `GET /{report_id}/fhir`
- 僅支援 Report → FHIR Bundle 的單向匯出
- 無 FHIR API 伺服器、無資源驗證、無 SMART-on-FHIR

### 6.2 Phase 4 FHIR 邊界

```
FHIR Boundary
══════════════════════════════════════════════════════════════════

┌─ Hospital / EHR System ─────────────────────────────────────┐
│                                                               │
│  FHIR R4 Client                                               │
│  (Epic/Cerner/Meditech/自建)                                  │
│                                                               │
│  ┌─ SMART-on-FHIR Launch ───────────────────────────────┐   │
│  │  1. EHR 啟動 → .well-known/smart-configuration       │   │
│  │  2. 授權請求 → authorize endpoint                    │   │
│  │  3. Token 交換 → token endpoint                      │   │
│  │  4. FHIR API 呼叫 → bearer token                    │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────┬───────────────────────────────────┘
                           │
                           ▼
┌─ System FHIR Boundary ───────────────────────────────────────┐
│                                                               │
│  FHIR Base URL: https://[host]/fhir/r4                       │
│                                                               │
│  ┌─ FHIR RESTful API (Phase 4 新建) ───────────────────┐    │
│  │                                                       │    │
│  │  Resource Endpoints (Read/Search/Create/Update):     │    │
│  │  ┌───────────────────────────────────────────────┐  │    │
│  │  │ GET    /Patient/{id}                          │  │    │
│  │  │ POST   /Patient                               │  │    │
│  │  │ GET    /Patient?identifier=...                 │  │    │
│  │  │ GET    /Observation/{id}                      │  │    │
│  │  │ POST   /Observation/$lastupdated              │  │    │
│  │  │ GET    /MedicationRequest/{id}                │  │    │
│  │  │ GET    /DiagnosticReport/{id}                 │  │    │
│  │  │ GET    /Condition/{id}                        │  │    │
│  │  │ GET    /Procedure/{id}                        │  │    │
│  │  │ GET    /CarePlan/{id}                         │  │    │
│  │  │ POST   /CarePlan                              │  │    │
│  │  │ POST   /Bundle (batch/transaction)            │  │    │
│  │  └───────────────────────────────────────────────┘  │    │
│  │                                                       │    │
│  │  Conformance:                                         │    │
│  │  ┌───────────────────────────────────────────────┐  │    │
│  │  │ GET /metadata → CapabilityStatement          │  │    │
│  │  │ GET /.well-known/smart-configuration          │  │    │
│  │  └───────────────────────────────────────────────┘  │    │
│  │                                                       │    │
│  └───────────────────────────────────────────────────────┘    │
│                                                               │
│  ┌─ FHIR Mapping Layer ──────────────────────────────────┐    │
│  │                                                         │    │
│  │  FHIR Resource ↔ Domain Model Mapping:                  │    │
│  │                                                         │    │
│  │  Patient        ↔ patient.PatientModel                 │    │
│  │  Observation    ↔ domain/cancer_case (labs/tests)      │    │
│  │  Condition      ↔ domain/cancer_case (diagnosis)       │    │
│  │  MedicationReq  ↔ domain/treatment_plan (items)        │    │
│  │  DiagnosticRpt  ↔ reporting (clinical reports)        │    │
│  │  CarePlan       ↔ domain/treatment_plan                │    │
│  │  Procedure      ↔ domain/treatment_plan (procedures)  │    │
│  │                                                         │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                               │
│  ┌─ FHIR Validation ───────────────────────────────────┐    │
│  │  - 使用 fhirpath 或 fhir-validator 驗證資源格式      │    │
│  │  - OperationOutcome 回傳驗證錯誤                     │    │
│  │  - 支援 FHIR R4 的 Must Support 標記                │    │
│  └─────────────────────────────────────────────────────┘    │
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
│  │ OpenCRAVATAdapter (Local)│   └─────────────────────────┘  │
│  └──────────────────────────┘                                 │
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
| **RAG 與 KG 互補** | KG 提供結構化事實查詢（精確），RAG 提供非結構化語義檢索（模糊），兩者不互相取代 |

---

## 8. External Evidence Boundary

### 8.1 現狀

- 8/10 adapter 為 `NotConfiguredAdapter` stub（CIViC, DGIdb, OncoTree, MyVariant, DRKG, PharmCAT, Ensembl VEP, OpenCRAVAT）
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
│  │ DGIdb (dgidb.org)  │  │ OpenCRAVAT (本地)            │    │
│  │ - Drug-Gene Interact│  │ - 綜合變異註釋               │    │
│  └─────────┬──────────┘  └──────────────┬───────────────┘    │
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
│  adapters/ (Phase 4 實作)          pipeline/ (既有+補全)      │
│  ┌────────────────────────────┐  ┌────────────────────────┐  │
│  │ CIViCAdapter (新實作)     │  │ vep_adapter.py (既有)  │  │
│  │ DGIdbAdapter (新實作)     │  │ civic_adapter.py (既有)│  │
│  │ OncoTreeAdapter (新實作)  │  │ dgidb_adapter.py (既有)│  │
│  │ MyVariantAdapter (新實作) │  │ opencravat_adapter.py  │  │
│  │ DRKGAdapter (新實作)      │  │   (Phase 4 完成)       │  │
│  │ PharmCATAdapter (新實作)  │  └────────────────────────┘  │
│  │ EnsemblVEPAdapter (新實作)│                               │
│  │ OpenCRAVATAdapter (新實作)│                               │
│  └────────────────────────────┘                               │
│                                                               │
│  注意：pipeline/ 下的 civic/dgidb adapter 已有真實 REST 實作，│
│  但 adapters/ 下的對應項為 stub。Phase 4 策略：               │
│  1. 保留 pipeline/ 既有實作（供 VCF pipeline 使用）           │
│  2. adapters/ 新實作使用 pipeline/ 既有程式碼，            │
│     但以 AdapterRegistry 標準介面包裝                          │
│  3. 最終 registry 中所有 adapter 皆為真實連接                │
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

### 8.3 Adapter 實作優先級

| 優先級 | Adapter | 資料源類型 | API 文件 | 既有資產 |
|--------|---------|-----------|---------|---------|
| P0 | CIViCAdapter | REST API | ✅ 公開 | pipeline/civic_adapter.py 可參考 |
| P0 | DGIdbAdapter | REST API | ✅ 公開 | pipeline/dgidb_adapter.py 可參考 |
| P1 | EnsemblVEPAdapter | REST API | ✅ 公開 | pipeline/vep_adapter.py 可參考（但 adapters/ 版本需包裝為標準介面） |
| P1 | OncoTreeAdapter | REST API | ✅ 公開 | 從零實作 |
| P1 | MyVariantAdapter | REST API | ✅ 公開 | 從零實作 |
| P2 | OpenCRAVATAdapter | Local tool | ✅ 文件 | pipeline/opencravat_adapter.py 骨架 |
| P2 | DRKGAdapter | REST API | ✅ 公開 | 從零實作 |
| P2 | PharmCATAdapter | Local tool | ✅ 文件 | 從零實作 |

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
│  ┌──────────────────┐  ┌──────────────────┐                  │
│  │ Vector DB        │  │ (Optional)       │                  │
│  │ (Chroma/Qdrant)  │  │ Redis for cache  │                  │
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
│  │  Vector DB (Chroma / Qdrant)                        │    │
│  │  - Persistent storage mount                         │    │
│  │  - API key authentication                           │    │
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
| **Container-first** | 所有元件（後端、前端、知識圖譜、Vector DB）皆容器化 |
| **Single host 起步** | Production 初期使用單一主機 Docker Compose，不引入 K8s |
| **環境分離** | 明確區分 dev/staging/production 三套設定 |
| **Immutable artifact** | CI 產出 Docker image，CD 部署該 image（不 hot-patch） |
| **無狀態後端** | 後端容器不儲存狀態，所有狀態在 PG 或 Vector DB 中 |
| **Knowledge Graph 獨立** | KnowGraphGo 作為獨立服務部署，透過 gRPC 或 REST 與後端通訊 |

---

## 10. Batch 拆分

### 10.1 Batch 總覽

根據盤點結果，Phase 4 拆分為 6 個 Batch。每個 Batch 皆是 vertical slice，涵蓋 backend → frontend → tests → CI → docs 所有層面。

```
Batch 相依關係：
                                 ┌─────────┐
                                 │  B1     │
                                 │ FHIR R4 │
                                 └────┬────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼
              ┌─────────┐     ┌─────────┐     ┌─────────┐
              │  B2     │     │  B3     │     │  B4     │
              │External │     │  RAG &  │     │Product. │
              │Adapters │     │Semantic │     │Observab.│
              └─────────┘     └─────────┘     └─────────┘
                    │              │                 │
                    └──────────────┼─────────────────┘
                                   ▼
                             ┌─────────┐
                             │  B5     │
                             │  Infra  │
                             │(Docker +│
                             │ CI/CD)  │
                             └────┬────┘
                                  │
                             ┌─────────┐
                             │  B6     │
                             │Frontend │
                             │Product. │
                             └─────────┘
```

| Batch | 名稱 | 前置 | 預估檔案數 | 工時預估 |
|-------|------|------|-----------|---------|
| B1 | FHIR R4 醫院互通 | 無 | 18-22 files | 3-4 週 |
| B2 | 外部證據 Adapter 實作 | 無（可與 B1 並行） | 16-20 files | 2-3 週 |
| B3 | RAG/Vector DB/Embedding | 無（可與 B1/B2 並行） | 14-18 files | 2-3 週 |
| B4 | 生產級 Observability | 無（可並行） | 12-16 files | 1-2 週 |
| B5 | Docker + CI/CD 基礎設施 | B1, B2, B3, B4 | 14-18 files | 1-2 週 |
| B6 | 前端產品化與 Service 重構 | B5（需 Docker 環境測試） | 18-22 files | 2-3 週 |

### 10.2 Batch 1：FHIR R4 醫院互通

#### 名稱與目標
**FHIR R4 Integration** — 建立完整 FHIR R4 API，使系統可與 EHR/EMR 系統互通。

#### 功能範圍
1. FHIR R4 資源模型（Patient, Observation, Condition, MedicationRequest, DiagnosticReport, Procedure, CarePlan）
2. FHIR RESTful API（Read/Search/Create/Update 端點）
3. FHIR Domain Model 映射層（Domain Model ↔ FHIR Resource）
4. FHIR 驗證（fhirpath/fhir-validator）
5. CapabilityStatement + SMART-on-FHIR 設定端點
6. 既有 FHIRExporter 整合（reporting/renderer.py 中的簡化版改為委託給新 FHIR 模組）
7. FHIR 端點專屬 Audit Logging
8. 整合測試（使用 FHIR 測試樣本）

#### 預估檔案清單（20 files）

| # | 檔案路徑（預估） | 類型 | 說明 |
|---|----------------|------|------|
| 1 | `src/backend/fhir/__init__.py` | 新建 | FHIR 模組初始化 |
| 2 | `src/backend/fhir/models.py` | 新建 | FHIR R4 資源 Pydantic 模型（Patient, Observation, Condition, MedicationRequest, DiagnosticReport, Procedure, CarePlan, Bundle, OperationOutcome） |
| 3 | `src/backend/fhir/mapping.py` | 新建 | Domain Model ↔ FHIR Resource 映射邏輯 |
| 4 | `src/backend/fhir/validation.py` | 新建 | FHIR 資源驗證（使用 fhirpath 規則） |
| 5 | `src/backend/fhir/service.py` | 新建 | FHIR 服務層（CRUD 操作、搜尋、Bundle 處理） |
| 6 | `src/backend/fhir/repository.py` | 新建 | FHIR 資源儲存庫（基於既有 Domain Repository） |
| 7 | `src/backend/api/v1/fhir.py` | 新建 | FHIR REST API 路由（Patient/Observation/Condition/MedicationRequest/DiagnosticReport/Procedure/CarePlan） |
| 8 | `src/backend/api/v1/fhir_metadata.py` | 新建 | CapabilityStatement + .well-known/smart-configuration 端點 |
| 9 | `src/backend/fhir/smart_on_fhir.py` | 新建 | SMART-on-FHIR 授權流程 |
| 10 | `src/backend/fhir/audit.py` | 新建 | FHIR 端點專屬 Audit Logging |
| 11 | `src/backend/reporting/renderer.py` | 修改 | FHIRExporter 改為委託 fhir 模組（向後相容） |
| 12 | `tests/unit/fhir/test_fhir_models.py` | 新建 | FHIR 模型單元測試 |
| 13 | `tests/unit/fhir/test_fhir_mapping.py` | 新建 | FHIR 映射單元測試 |
| 14 | `tests/unit/fhir/test_fhir_validation.py` | 新建 | FHIR 驗證單元測試 |
| 15 | `tests/integration/fhir/test_fhir_api.py` | 新建 | FHIR API 整合測試 |
| 16 | `tests/integration/fhir/test_smart_on_fhir.py` | 新建 | SMART-on-FHIR 流程測試 |
| 17 | `docs/fhir/api.md` | 新建 | FHIR API 文件 |
| 18 | `docs/fhir/profiles.md` | 新建 | FHIR Profile 說明 |
| 19 | `migrations/versions/026_fhir_resource_tables.py` | 新建 | FHIR 資源相關資料庫遷移（若需要） |
| 20 | `scripts/fhir/load_test_data.py` | 新建 | FHIR 測試資料載入腳本 |

#### 涉及的角色
- 後端工程師（Python + FHIR 規格）
- QA 工程師（FHIR 整合測試）
- 架構師（FHIR 映射設計）

#### 前置依賴
- 無（可直接啟動）
- 參考：既有 `reporting/renderer.py` 中的 FHIRExporter 實作
- 參考：既有 Domain Models（PatientModel, CancerCaseModel, TreatmentPlanModel）

#### CI 要求
- FHIR 模型單元測試在 Python CI 中執行
- FHIR API 整合測試需要 PostgreSQL service container
- FHIR 驗證測試使用公開 FHIR 測試樣本

#### 驗收標準
- [ ] 所有 FHIR 資源端點（Patient/Observation/Condition/MedicationRequest/DiagnosticReport/Procedure/CarePlan）支援 Read/Search
- [ ] Patient 與 CarePlan 支援 Create/Update
- [ ] `GET /fhir/r4/metadata` 回傳有效的 CapabilityStatement
- [ ] `GET /.well-known/smart-configuration` 回傳有效的 SMART-on-FHIR 設定
- [ ] FHIR Bundle（batch/transaction）可原子操作
- [ ] 無效 FHIR 資源回傳 OperationOutcome
- [ ] 既有 `GET /reports/{id}/fhir` 向後相容
- [ ] 所有 FHIR 端點有 audit log
- [ ] 整合測試覆蓋率 ≥ 80%（FHIR 模組）

#### 風險
| 風險 | 影響 | 緩解措施 |
|------|------|---------|
| FHIR 規格理解不足導致 mapping 錯誤 | 中 | 使用公開 FHIR 測試樣本驗證；先實作唯讀再實作寫入 |
| SMART-on-FHIR 授權流程複雜 | 高 | 初期只實作 Standalone Launch，EHR Launch 延後；參考 SMART-on-FHIR 官方 SDK |
| 既有 Domain Model 與 FHIR Resource 不完全對應 | 中 | 建立 mapping layer 而非強求 model 統一；差異部分以 FHIR Extension 處理 |
| FHIR 驗證效能問題 | 低 | 驗證放在 API 層，非同步背景驗證 |

---

### 10.3 Batch 2：外部證據 Adapter 實作

#### 名稱與目標
**External Evidence Adapters** — 將 8 個外部資料源 adapter 從 stub 升級為真實 REST API 連接，使 Agent 和 Engine 可即時取得外部臨床證據。

#### 功能範圍
1. CIViCAdapter — 變異臨床證據查詢（參考 pipeline/civic_adapter.py 既有實作）
2. DGIdbAdapter — 藥物-基因交互作用查詢（參考 pipeline/dgidb_adapter.py 既有實作）
3. OncoTreeAdapter — 癌症類型本體查詢
4. MyVariantAdapter — 變異註釋查詢
5. DRKGAdapter — 藥物重定位知識圖譜查詢
6. PharmCATAdapter — 藥物基因組學查詢
7. EnsemblVEPAdapter — 變異效應預測（參考 pipeline/vep_adapter.py 既有實作，包裝為標準 adapter 介面）
8. OpenCRAVATAdapter — 綜合變異註釋（完成 pipeline/opencravat_adapter.py 骨架）
9. AdapterRegistry 更新（將 pipeline 既有實作整合進 registry）
10. Adapter 健康檢查端點擴充
11. Adapter 回應快取機制
12. 整合測試（mock/real API）

#### 預估檔案清單（18 files）

| # | 檔案路徑（預估） | 類型 | 說明 |
|---|----------------|------|------|
| 1 | `src/backend/adapters/civic.py` | 修改 | CIViCAdapter：從 stub → 真實 REST 實作 |
| 2 | `src/backend/adapters/dgidb.py` | 修改 | DGIdbAdapter：從 stub → 真實 REST 實作 |
| 3 | `src/backend/adapters/oncotree.py` | 修改 | OncoTreeAdapter：從 stub → 真實 REST 實作 |
| 4 | `src/backend/adapters/myvariant.py` | 修改 | MyVariantAdapter：從 stub → 真實 REST 實作 |
| 5 | `src/backend/adapters/drkg.py` | 修改 | DRKGAdapter：從 stub → 真實 REST 實作 |
| 6 | `src/backend/adapters/pharmcat.py` | 修改 | PharmCATAdapter：從 stub → 真實 REST/CLI 實作 |
| 7 | `src/backend/adapters/ensembl_vep.py` | 修改 | EnsemblVEPAdapter：從 stub → 包裝 pipeline/vep_adapter.py 為標準 adapter |
| 8 | `src/backend/adapters/opencravat.py` | 修改 | OpenCRAVATAdapter：從 stub → 真實實作 |
| 9 | `src/backend/adapters/registry.py` | 修改 | 更新 registry 使用真實 adapter 而非 stub |
| 10 | `src/backend/adapters/cache.py` | 新建 | Adapter 回應快取層（避免重複 API 呼叫，遵守 rate limit） |
| 11 | `src/backend/pipeline/opencravat_adapter.py` | 修改 | 完成真實 OpenCRAVAT 整合（與 adapters/opencravat.py 共用邏輯） |
| 12 | `src/backend/api/v1/adapters.py` | 修改 | Adapter 健康檢查/狀態端點擴充 |
| 13 | `tests/unit/adapters/test_civic_adapter.py` | 新建 | CIViC adapter 單元測試（mock API） |
| 14 | `tests/unit/adapters/test_dgidb_adapter.py` | 新建 | DGIdb adapter 單元測試（mock API） |
| 15 | `tests/unit/adapters/test_oncotree_adapter.py` | 新建 | OncoTree adapter 單元測試（mock API） |
| 16 | `tests/unit/adapters/test_adapter_cache.py` | 新建 | Adapter 快取單元測試 |
| 17 | `tests/integration/adapters/test_adapter_registry.py` | 新建 | Adapter registry 整合測試 |
| 18 | `docs/adapters/overview.md` | 新建 | Adapter 架構與使用說明文件 |

#### 涉及的角色
- 後端工程師（Python + REST API 整合）
- 資料工程師（了解各資料源 API 文件與 rate limit）
- QA 工程師（mock API 測試）

#### 前置依賴
- 無（可直接啟動，與 B1 並行）
- 參考：`pipeline/civic_adapter.py`、`pipeline/dgidb_adapter.py`、`pipeline/vep_adapter.py` 既有實作
- 參考：`knowledge/adapters/` 中的 3 個真實 adapter 實作風格

#### CI 要求
- 所有 adapter 單元測試使用 mock，不依賴外部 API
- 整合測試可選標記（需設定 API key）
- 新增 GitHub Actions cache 層減少重複測試

#### 驗收標準
- [ ] 8 個 adapter 全部從 `NotConfiguredAdapter` 升級為真實實作
- [ ] 每個 adapter 至少支援 `annotate()` 和 `health_check()`
- [ ] Adapter 快取層實作（TTL 可設定，遵守上游 rate limit）
- [ ] `GET /api/v1/adapters/status` 回傳所有 adapter 連線狀態
- [ ] Agent 系統可透過 AdapterRegistry 查詢真實外部證據
- [ ] 既有 pipeline 功能不受影響（civic/dgidb/vep 既有端點保持運作）
- [ ] Adapter 單元測試覆蓋率 ≥ 85%

#### 風險
| 風險 | 影響 | 緩解措施 |
|------|------|---------|
| 外部 API 變更或下線 | 高 | 每個 adapter 有對應的 mock 測試；registry 支援 graceful degradation |
| API key 管理不當 | 高 | 使用環境變數搭配 Docker secrets；不在程式碼中硬編碼 |
| 部分資料源需要本地安裝（PharmCAT, OpenCRAVAT） | 中 | 支援 CLI 模式 + REST API 模式兩種整合方式 |
| Rate limit 導致請求失敗 | 中 | 快取層 + 指數退避 retry（既有 Outbox retry policy） |

---

### 10.4 Batch 3：RAG / Vector DB / Embedding

#### 名稱與目標
**RAG & Semantic Search** — 建立向量資料庫與 Embedding pipeline，為臨床知識檢索提供語義搜索能力。

#### 功能範圍
1. Vector DB 整合（建議 Chroma，輕量且支援 Python first-class）
2. Embedding 服務（使用 sentence-transformers 或 OpenAI/text-embedding-ada-002）
3. 臨床文本 Embedding pipeline（將既有 KnowledgeEntity/Publication/ClinicalTrial 文本向量化）
4. RAG 檢索服務（semantic search + hybrid search）
5. RAG 與 ReasonService 整合（推理時檢索相關知識）
6. RAG 與 Agent System 整合（Agent 可查詢語義相關證據）
7. Embedding 背景更新工作（增量更新）
8. Vector DB 管理 API（索引狀態、重新索引）

#### 預估檔案清單（16 files）

| # | 檔案路徑（預估） | 類型 | 說明 |
|---|----------------|------|------|
| 1 | `src/backend/rag/__init__.py` | 新建 | RAG 模組初始化 |
| 2 | `src/backend/rag/vector_store.py` | 新建 | Vector DB 用戶端封裝（Chroma Client wrapper） |
| 3 | `src/backend/rag/embedding.py` | 新建 | Embedding 服務（model 載入、向量生成） |
| 4 | `src/backend/rag/pipeline.py` | 新建 | Embedding pipeline（文本擷取→清洗→chunk→embed→store） |
| 5 | `src/backend/rag/retriever.py` | 新建 | RAG 檢索器（semantic search + keyword hybrid） |
| 6 | `src/backend/rag/service.py` | 新建 | RAG 服務層（供其他 service 呼叫的統一介面） |
| 7 | `src/backend/rag/sync.py` | 新建 | 背景同步工作（增量更新 vector store） |
| 8 | `src/backend/api/v1/rag.py` | 新建 | RAG API 端點（查詢、索引狀態、重新索引） |
| 9 | `src/backend/reasoning/service.py` | 修改 | 整合 RAG 檢索結果作為推理依據 |
| 10 | `src/backend/agents/base.py` | 修改 | Agent 基底類加入 RAG 查詢能力（選擇性） |
| 11 | `src/frontend/src/api/rag.ts` | 新建 | 前端 RAG API 客戶端 |
| 12 | `src/frontend/src/pages/KnowledgeBase.tsx` | 修改 | 強化知識庫頁面，加入語義搜尋 UI |
| 13 | `tests/unit/rag/test_embedding.py` | 新建 | Embedding 單元測試 |
| 14 | `tests/unit/rag/test_retriever.py` | 新建 | RAG 檢索單元測試 |
| 15 | `tests/integration/rag/test_rag_pipeline.py` | 新建 | RAG pipeline 整合測試 |
| 16 | `docs/rag/architecture.md` | 新建 | RAG 架構說明文件 |

#### 涉及的角色
- 後端工程師（Python + Chroma/Qdrant）
- ML 工程師（Embedding model 選擇與調校）
- 前端工程師（語義搜尋 UI）

#### 前置依賴
- 無（可直接啟動，與 B1/B2 並行）
- 參考：既有 Knowledge Layer 中的文本資料
- 參考：既有 `knowledge/adapters/pubmed.py`, `knowledge/adapters/clinicaltrials.py`

#### CI 要求
- Unit test 使用 in-memory Vector DB
- Integration test 使用 Chroma in-memory 模式
- Embedding model 需下載（CI cache 加速）

#### 驗收標準
- [ ] Vector DB 可儲存與檢索臨床文本 embedding
- [ ] Embedding pipeline 可將 KnowledgeEntity/Publication 文本向量化
- [ ] RAG 檢索支援語義搜尋（給定 query 回傳 top-k 相關文本）
- [ ] RAG 檢索支援 hybrid 模式（語義 + 關鍵字）
- [ ] ReasonService 可呼叫 RAG 取得相關知識
- [ ] KnowledgeBase 前端頁面加入語義搜尋功能
- [ ] 背景同步工作可增量更新（不重複計算已有 embedding）
- [ ] Embedding 單元測試覆蓋率 ≥ 80%

#### 風險
| 風險 | 影響 | 緩解措施 |
|------|------|---------|
| Embedding model 選擇錯誤導致檢索品質差 | 中 | 初期使用 sentence-transformers/all-MiniLM-L6-v2（輕量）；預留 model 抽換介面 |
| Vector DB 資料量增長影響效能 | 中 | 使用 Chroma persistent 模式；建立索引定期最佳化 |
| Embedding pipeline 執行過久 | 中 | 支援增量更新；大型文本 chunk 策略最佳化 |
| 與既有 Knowledge Graph 功能重疊 | 低 | 明確區分：KG 負責結構化事實，RAG 負責非結構化語義檢索 |

---

### 10.5 Batch 4：基礎設施與可觀測性（Infrastructure & Observability）

#### 名稱與目標
**Infrastructure & Observability** — 將基礎生產基礎設施一次到位：既有 Observability 擴充為完整監控方案，並新增 Background Jobs/Queue 非同步任務佇列，為 Evidence Freshness、Guideline Sync 等定時任務提供基礎。

#### 功能範圍
1. Prometheus metrics 端點（request rate, latency P50/P95/P99, error rate, active users）
2. OpenTelemetry 分散式追蹤（跨 service 的請求追蹤）
3. Logging 強化（結構化 JSON log + log level 動態調整）
4. Health check 擴充（adapter 健康狀態、資料庫連線、Vector DB 狀態）
5. 效能 profiling（slow query 偵測、記憶體使用監控）
6. 警報規則（error rate spike、high latency、adapter 離線）
7. Grafana 儀表板（預設 dashboard 設定檔）
8. 既有 audit log 整合（audit 事件也送入 metrics）
9. **ARQ job queue 整合**（Redis + ARQ worker，非同步任務佇列）
10. **Job 模型與管理 API**（enqueue/status/cancel）
11. **Cron-like scheduler**（定時任務：證據更新、guideline sync）
12. **Retry/Dead-letter 泛化**（複用 Outbox 設計模式，從 outbox 專用變通用）
13. **Redis 服務設定**（docker-compose.redis.yml）

#### 預估檔案清單（24 files）

| # | 檔案路徑（預估） | 類型 | 說明 |
|---|----------------|------|------|
| **Observability（原 14 files）** |
| 1 | `src/backend/observability/metrics.py` | 新建 | Prometheus metrics 定義與收集（request count, latency, error） |
| 2 | `src/backend/observability/tracing.py` | 新建 | OpenTelemetry 初始化與 middleware |
| 3 | `src/backend/observability/logging.py` | 新建 | 結構化 JSON logging 設定 |
| 4 | `src/backend/observability/profiling.py` | 新建 | 效能 profiling（slow query, memory） |
| 5 | `src/backend/observability/health.py` | 修改 | 擴充 health check（加入 adapter/db/vector/queue 健康狀態） |
| 6 | `src/backend/observability/alerts.py` | 新建 | 警報規則定義（可匯入 PrometheusAlertManager） |
| 7 | `src/backend/main.py` | 修改 | 註冊 metrics/tracing middleware + job worker |
| 8 | `src/backend/api/v1/health.py` | 修改 | 擴充 health 端點回傳詳細狀態（含 queue） |
| 9 | `deploy/observability/prometheus.yml` | 新建 | Prometheus 設定檔 |
| 10 | `deploy/observability/grafana_dashboard.json` | 新建 | Grafana 預設儀表板 |
| 11 | `deploy/observability/otel-collector.yml` | 新建 | OpenTelemetry Collector 設定 |
| 12 | `docker-compose.observability.yml` | 新建 | Observability stack（Prometheus + Grafana + OTEL） |
| 13 | `tests/unit/observability/test_metrics.py` | 新建 | Metrics 單元測試 |
| 14 | `docs/observability/monitoring.md` | 新建 | 監控架構說明文件 |
| **Background Jobs（新增 10 files）** |
| 15 | `src/backend/jobs/__init__.py` | 新建 | Jobs 模組 |
| 16 | `src/backend/jobs/config.py` | 新建 | ARQ worker 設定（Redis 連線、worker 並行數） |
| 17 | `src/backend/jobs/models.py` | 新建 | Job 領域模型（JobModel, JobStatus） |
| 18 | `src/backend/jobs/repository.py` | 新建 | Job 持久化（SQLAlchemy repository） |
| 19 | `src/backend/jobs/service.py` | 新建 | Job 生命週期管理（submit/cancel/retry） |
| 20 | `src/backend/jobs/scheduler.py` | 新建 | Cron-like scheduler（證據更新、guideline sync） |
| 21 | `src/backend/jobs/worker.py` | 新建 | ARQ worker 啟動腳本 |
| 22 | `src/backend/jobs/retry_policy.py` | 新建 | 泛化 Retry/Dead-letter 策略（複用 Outbox 設計模式） |
| 23 | `src/backend/api/v1/jobs.py` | 新建 | Job 管理 API 端點（enqueue/status/cancel） |
| 24 | `docker-compose.redis.yml` | 新建 | Redis 服務設定（Docker Compose） |

#### 涉及的角色
- 後端工程師（Python + Prometheus + OpenTelemetry + ARQ + Redis）
- DevOps 工程師（Grafana 儀表板 + 警報設定 + Redis 管理）
- SRE（生產監控策略 + 背景任務排程策略）

#### 前置依賴
- 無（可直接啟動，與 B1/B2/B3 並行）
- 參考：既有 `observability/audit.py` 實作風格；Outbox 模式作為 Retry/Dead-letter 設計參考

#### CI 要求
- Metrics 單元測試不依賴實際 Prometheus 實例
- Job 單元測試使用 Redis mock（不依賴實際 Redis 實例）
- 不引入新的 CI workflow，在既有 Python CI 中擴充

#### 驗收標準
- [ ] `GET /metrics` 回傳 Prometheus 格式的 metrics（request count, latency, error rate）
- [ ] 分散式追蹤可追蹤單一請求跨 service 的完整路徑
- [ ] Health check 端點回資料庫、adapter、Vector DB、Redis Queue 的詳細狀態
- [ ] 所有 log 為 JSON 結構化格式（可被 log aggregator 解析）
- [ ] Grafana 儀表板可視覺化核心指標（含 job queue depth、job duration）
- [ ] 警報規則可匯入 Prometheus AlertManager
- [ ] `POST /api/v1/jobs` 可提交 job，`GET /api/v1/jobs/{id}` 回傳正確狀態
- [ ] Scheduler 可註冊定時任務（cron expression），並在指定時間觸發
- [ ] Job 失敗後自動重試（可設定 max_retries），超過次數進入 dead-letter
- [ ] Redis 服務可透過 `docker-compose.redis.yml` 一鍵啟動
- [ ] 既有 audit log 不受影響

#### 風險
| 風險 | 影響 | 緩解措施 |
|------|------|---------|
| Metrics 引入效能 overhead | 低 | Prometheus client 為低開銷設計；tracing 使用取樣 |
| OpenTelemetry 設定複雜 | 中 | 初期只實作基本 tracing（request → service → adapter），不跨主機 |
| 既有 logging 全部改 JSON 可能影響除錯 | 低 | 開發環境保留 human-readable 格式；production 使用 JSON |
| Redis 服務增加運維成本 | 低 | Redis 為成熟開源方案，Docker 一鍵啟動；初期不要求叢集，單實例即可；可選用 Upstash/Railway 等託管服務 |
| ARQ 生態較 Celery 小，社群支援有限 | 低 | ARQ 足以支撐 Phase 4 需求（非同步任務量不大）；若未來擴充可遷移至 Celery，Retry 策略可複用 |

---

### 10.6 Batch 5：Docker + CI/CD 基礎設施

#### 名稱與目標
**Deployment Infrastructure** — 建立完整的容器化部署方案與 CI/CD pipeline。

#### 功能範圍
1. Dockerfile（後端 + 前端 + 知識圖譜）
2. docker-compose.yml（dev + prod 兩套設定）
3. Go CI pipeline（go build + go test + golangci-lint）
4. Docker CI pipeline（build + security scan + push）
5. 後端部署 pipeline（Docker image push + deploy）
6. 環境設定管理（dev/staging/production 三層設定）
7. Health check 整合 Docker Compose（依賴啟動順序控制）
8. 資料庫遷移自動化（Docker entrypoint 執行 alembic upgrade）
9. 文件更新（部署指南）

#### 預估檔案清單（16 files）

| # | 檔案路徑（預估） | 類型 | 說明 |
|---|----------------|------|------|
| 1 | `Dockerfile.backend` | 新建 | 後端 Docker image（Python + uvicorn） |
| 2 | `Dockerfile.frontend` | 新建 | 前端 Docker image（Nginx + static build） |
| 3 | `Dockerfile.knowgraph` | 新建 | 知識圖譜 Docker image（Go binary + scratch） |
| 4 | `docker-compose.yml` | 新建 | Production Docker Compose（後端+前端+KG+PG+Vector DB） |
| 5 | `docker-compose.dev.yml` | 新建 | Development Docker Compose（+ hot reload） |
| 6 | `.github/workflows/go-ci.yml` | 新建 | Go CI workflow（build + test + lint） |
| 7 | `.github/workflows/docker-ci.yml` | 新建 | Docker CI workflow（build + scan + push） |
| 8 | `.github/workflows/deploy.yml` | 修改 | 擴充部署 workflow（加入 Docker push + backend deploy） |
| 9 | `.dockerignore` | 新建 | Docker ignore 規則 |
| 10 | `deploy/env/backend.env.example` | 新建 | 後端環境變數範例 |
| 11 | `deploy/env/frontend.env.example` | 新建 | 前端環境變數範例 |
| 12 | `deploy/scripts/startup.sh` | 新建 | Docker entrypoint 腳本（含 alembic upgrade） |
| 13 | `deploy/scripts/init_db.sh` | 新建 | 資料庫初始化腳本 |
| 14 | `deploy/nginx/default.conf` | 新建 | Nginx 反向代理設定（production） |
| 15 | `docs/deployment/guide.md` | 新建 | 部署指南 |
| 16 | `docs/deployment/environments.md` | 新建 | 環境設定說明 |

#### 涉及的角色
- DevOps 工程師（Docker + CI/CD）
- 後端工程師（Python Docker 化）
- Go 工程師（KG Docker 化）
- 前端工程師（Frontend Docker 化）

#### 前置依賴
- B1（FHIR 功能需在 Docker image 中）
- B2（Adapter 需在 Docker image 中）
- B3（RAG/Vector DB 需在 Docker Compose 中）
- B4（Infrastructure & Observability — Redis 服務、Job worker 需在 Docker Compose 中）

#### CI 要求
- 每個 PR 自動觸發 Go CI（若修改 KnowGraphGo）
- Docker CI 在 main branch push 時觸發
- Docker image 使用 GitHub Container Registry 或 Docker Hub

#### 驗收標準
- [ ] `docker-compose up` 可一鍵啟動完整系統
- [ ] 後端 Docker image 包含所有 adapter 依賴
- [ ] Go CI workflow 通過 go build + go test + golangci-lint
- [ ] Docker CI workflow 通過 build + security scan（Trivy/Docker Scout）
- [ ] 既有 Python CI 和 Vercel 部署不受影響
- [ ] Nginx 反向代理正確 routing（/api/* → backend, / → frontend）
- [ ] Docker 啟動時自動執行 alembic upgrade
- [ ] 部署文件包含 dev/staging/production 三種情境

#### 風險
| 風險 | 影響 | 緩解措施 |
|------|------|---------|
| Docker image 過大（Python + ML model） | 中 | 使用多階段 build；model 下載放在 runtime volume |
| Go CI 新增導致 pipeline 時間過長 | 低 | Go build 使用 cache；與 Python CI 並行執行 |
| 安全性掃描發現高風險漏洞 | 中 | 使用官方 base image 並定期更新；Trivy 掃描結果納入 CI gate |

---

### 10.7 Batch 6：前端產品化與 Service 重構

#### 名稱與目標
**Frontend Productization & Code Quality** — 強化前端使用者體驗、統一 API client、重構過大的後端 Service。

#### 功能範圍
1. 統一前端 API Client（axios instance + interceptors + TypeScript 型別圖譜）
2. Tools.tsx 頁面強化（從 2130B 的簡略頁面升級為完整工具入口）
3. KnowledgeBase.tsx 頁面強化（與 Batch 3 RAG 整合）
4. Research.tsx 頁面強化（從 2447B 擴充為研究入口）
5. treatment_plan_service.py（58842B）依職責拆分
6. 前端 API Client 全面改用統一封裝（消除各頁面重複的 request helper）
7. 前端 error handling 統一化
8. 前端 loading state 統一化

#### 預估檔案清單（20 files）

| # | 檔案路徑（預估） | 類型 | 說明 |
|---|----------------|------|------|
| 1 | `src/frontend/src/api/client.ts` | 新建 | 統一 axios instance + interceptor（auth/error/logging） |
| 2 | `src/frontend/src/api/types.ts` | 新建 | TypeScript 型別定義（與後端 Pydantic model 對應） |
| 3 | `src/frontend/src/api/clinical_decision.ts` | 修改 | 改用統一 client 封裝 |
| 4 | `src/frontend/src/api/treatmentPlan.ts` | 修改 | 改用統一 client 封裝 |
| 5 | `src/frontend/src/api/workbench.ts` | 修改 | 改用統一 client 封裝 |
| 6 | `src/frontend/src/api/rag.ts` | 新建 | RAG API client（若 B3 已建立） |
| 7 | `src/frontend/src/pages/Tools.tsx` | 修改 | 擴充為完整工具入口 |
| 8 | `src/frontend/src/pages/KnowledgeBase.tsx` | 修改 | 強化知識庫頁面（與 B3 整合） |
| 9 | `src/frontend/src/pages/Research.tsx` | 修改 | 強化研究入口頁面 |
| 10 | `src/frontend/src/components/ErrorBoundary.tsx` | 新建 | 統一錯誤邊界元件 |
| 11 | `src/frontend/src/components/LoadingState.tsx` | 新建 | 統一載入狀態元件 |
| 12 | `src/backend/services/treatment_plan/__init__.py` | 新建 | 拆分後的 treatment plan service 套件 |
| 13 | `src/backend/services/treatment_plan/service.py` | 新建 | 核心治療計畫 service（從原檔拆分） |
| 14 | `src/backend/services/treatment_plan/phase_service.py` | 新建 | 治療階段管理 service（從原檔拆分） |
| 15 | `src/backend/services/treatment_plan/monitoring_service.py` | 新建 | 治療監控 service（從原檔拆分） |
| 16 | `src/backend/services/treatment_plan/safety_service.py` | 新建 | 治療安全規則 service（從原檔拆分） |
| 17 | `src/backend/services/treatment_plan_service.py` | 修改 | 保留為 façade pattern（委託給新拆分的子 service） |
| 18 | `tests/unit/services/test_treatment_plan_service.py` | 修改 | 拆分後的 service 測試 |
| 19 | `tests/frontend/test_tools_page.py` | 新建 | Tools 頁面測試 |
| 20 | `src/frontend/src/hooks/useApi.ts` | 新建 | 統一 API hook（loading/error/data 狀態管理） |

#### 涉及的角色
- 前端工程師（React/TypeScript）
- 後端工程師（Service 拆分）
- QA 工程師（前端測試）

#### 前置依賴
- B5（需 Docker 環境進行端到端測試）
- B3 的 KnowledgeBase 整合（選擇性）

#### CI 要求
- 前端測試在既有 Vercel CI 中執行
- Service 重構需確保既有測試通過（regression test）

#### 驗收標準
- [ ] 所有前端 API 呼叫使用統一 axios instance（攔截器統一處理 auth/error/logging）
- [ ] Tools.tsx 頁面功能完整（不低於其他頁面的功能密度）
- [ ] KnowledgeBase.tsx 整合 RAG 語義搜尋
- [ ] Research.tsx 頁面顯示研究相關功能
- [ ] `treatment_plan_service.py` 拆分為 ≤ 4 個子 service，每個 ≤ 20000 bytes
- [ ] 拆分後的 façade 保持向後相容（所有既有端點不受影響）
- [ ] 前端 error handling 統一顯示 toast/alert
- [ ] 前端 loading state 統一使用 Skeleton/Spinner
- [ ] 所有前端測試通過（regression）

#### 風險
| 風險 | 影響 | 緩解措施 |
|------|------|---------|
| Service 拆分導致 regression | 高 | 拆分前補齊 test coverage；拆分後跑 full regression |
| 前端統一 client 改動影響所有頁面 | 中 | 先建立新 client，逐步遷移（不一次全改） |
| Tools/KnowledgeBase/Research 頁面需求不明確 | 中 | 以既有 Dashboard 和 Workbench 的功能密度為基準 |

---

## 11. 驗收標準

### 11.1 Phase 4 整體 Gate

| Gate | 條件 | 通過標準 |
|------|------|---------|
| **G1: FHIR 互通 Gate** | FHIR R4 API 可供外部 EHR 系統呼叫 | 所有核心資源端點（Patient/Observation/Condition/MedicationRequest/DiagnosticReport/CarePlan）可正常 Read/Search；CapabilityStatement 回傳有效 |
| **G2: 外部證據 Gate** | 8 個外部 adapter 真實連接 | `GET /api/v1/adapters/status` 回傳全部 configured（可能部分 offline 但非 stub） |
| **G3: 語義檢索 Gate** | RAG 系統可檢索臨床知識 | Embedding pipeline 完成索引；KnowledgeBase 可語義搜尋 |
| **G4: 基礎設施與監控 Gate** | Prometheus metrics + OpenTelemetry tracing + Background Jobs queue | `GET /metrics` 回傳有效 metrics；Grafana 儀表板顯示核心指標與 job queue depth；`POST /api/v1/jobs` 可提交 job；Redis 服務正常運作 |
| **G5: 部署 Gate** | Docker Compose 一鍵啟動 | `docker-compose up` 後系統功能正常；所有 CI pipeline 通過 |
| **G6: 程式碼品質 Gate** | Service 拆分完成、前端統一 | `treatment_plan_service.py` ≤ 20000 bytes；前端無硬編碼 fetch |
| **G7: 回歸 Gate** | 既有功能不受影響 | 所有既有測試（~99 Python + 35 Go + 14 Frontend）通過 |

### 11.2 各 Batch 驗收標準

| Batch | 驗收標準摘要 | 測試類型 |
|-------|------------|---------|
| B1 | FHIR R4 資源模型 + REST API + 驗證 + SMART-on-FHIR 設定 | Unit + Integration + FHIR 測試樣本 |
| B2 | 8 adapter 真實實作 + 快取 + registry 更新 | Unit (mock) + Integration (可選) |
| B3 | Vector DB + Embedding + RAG 檢索 + ReasonService 整合 | Unit + Integration (in-memory DB) |
| B4 | Prometheus + OTEL + 結構化 log + Grafana dashboard + Background Jobs（ARQ + Redis + Job API + Scheduler + Retry/Dead-letter） | Unit + Integration + Redis mock |
| B5 | Dockerfile + docker-compose + Go CI + Docker CI | CI pipeline + 手動驗證 |
| B6 | 統一 API client + 頁面強化 + Service 拆分 | Unit + Regression + Frontend |

### 11.3 禁止事項確認（Phase 4）

- [ ] ❌ 不修改 KnowGraphGo 核心套件（直接複用，僅透過 CI 確保品質）
- [ ] ❌ 不修改 25 個領域模型（直接複用）
- [ ] ❌ 不建立空殼 API 或 placeholder frontend
- [ ] ❌ 不引入 Kubernetes（Docker Compose 足矣）
- [ ] ❌ 不引入 Kafka/其他 message broker（Redis 因 Background Jobs 需要而引入）
- [ ] ❌ 不開始 ML Model Training Pipeline（預留給 Phase 5）
- [ ] ❌ 不開始 HL7/DICOM/PACS Integration（預留給 Phase 5）
- [ ] ❌ 不進行 Microservices 拆分（維持 monolith）
- [ ] ❌ 不使用 mock 結果聲稱 integration ready

### 11.4 總交付檢查清單

- [ ] **plan-phase4-clinical-ai-productization.md** — 本文件
  - [ ] 最終能力描述（含既有 + 新增能力）
  - [ ] 完整架構（4 層文字 Component Diagram）
  - [ ] Data Flow（外部資料到治療計畫的完整路徑）
  - [ ] Security Boundary（擴充 SMART-on-FHIR）
  - [ ] Transaction Boundary（既有 + 新增事務邊界）
  - [ ] FHIR Boundary（從簡化版到完整 R4）
  - [ ] Knowledge Graph Boundary（既有 KG + 新 adapter 注入）
  - [ ] External Evidence Boundary（8 adapter 真實連接）
  - [ ] Deployment Boundary（Docker + CI/CD）
  - [ ] 6 個 Batch（每 Batch 10-25 files，垂直涵蓋所有層面）
  - [ ] 驗收標準（7 個 Gate + 各 Batch 標準）
  - [ ] 禁止事項確認

### 11.5 退出標準

Phase 4 完成並通過所有 Gate 後，系統可進入 Phase 5（Medical AI Platform）：
- ML Model Training Pipeline 啟動
- HL7/DICOM/PACS 整合開始
- Multi-specialty Platform 化設計
- Microservices 可行性評估

---

> **文件結束** — Phase 4 Clinical AI Productization Master Plan
