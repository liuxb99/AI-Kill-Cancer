# Phase 4 & Phase 5 Master Plan — 返工計劃 (R2)

> **計劃類型**：文件修改計劃  
> **適用場景**：ChatGPT 審查 Phase 4 & Phase 5 Master Plan 後判定 Accepted = NO，需返工修訂  
> **負責角色**：doc-writer（所有文件修改由 doc-writer 執行）  
> **預計總工時**：1-2 days（文件修改）  
> **生成日期**：2026-08-02  

---

## 目錄

1. [審查要求摘要](#1-審查要求摘要)
2. [受影響文件總覽](#2-受影響文件總覽)
3. [任務清單](#3-任務清單)
4. [依賴關係](#4-依賴關係)
5. [負責角色](#5-負責角色)
6. [注意事項](#6-注意事項)
7. [附錄：Vertical Slice Batch 設計](#7-附錄vertical-slice-batch-設計)

---

## 1. 審查要求摘要

ChatGPT 審查判定 **Accepted = NO**，以下為必須修正的 6 個面向：

| # | 要求 | 現狀（問題） | 改為 |
|---|------|-------------|------|
| **R1** | **Phase 4 Batch 拆分** | 6 個技術模組 Batch（FHIR / Adapters / RAG / Observability / Docker+CI/CD / Frontend） | **3 個 Vertical Slice Batch**，每個 Batch 為完整端到端工作流（API + Domain + Service + Repository + Frontend + Audit + Knowledge Graph + Digital Thread + CI + PostgreSQL + Migration + Documentation） |
| **R2** | **Transaction Boundary** | Repository 為 transaction owner | **Service 擁有 transaction**，Repository 僅 flush（無 commit/rollback） |
| **R3** | **Adapter 分類** | 全部 fire-and-forget | **同步**：Evidence Retrieval, Clinical Decision；**非同步**：Guideline Sync, Background Refresh, Cache Refresh |
| **R4** | **禁止新增基礎元件** | 引入 Redis（Background Jobs）、Vector DB（RAG/Chroma/Qdrant） | 除非 Gap Analysis + ADR + Current Capability 共同證明需要，否則禁止 Redis / Kafka / Vector DB / Qdrant / Chroma，保持 Technology Agnostic |
| **R5** | **Scope 控制** | 包含大型 Service Refactor（treatment_plan_service 拆分）與 Frontend 重構 | ❌ 排除大型 Service Refactor；❌ 排除 Frontend 重構；只保留真正阻擋產品化的能力 |
| **R6** | **Phase 5 Batch** | 7 個 Batch | 最多 **2～3 個 Batch** |

---

## 2. 受影響文件總覽

| # | 文件路徑 | 修改程度 | 說明 |
|---|---------|---------|------|
| F1 | `tasks/plan-phase4-clinical-ai-productization.md` | 🔴 **大幅重寫** | Section 10 Batch 拆分、Section 5 Transaction Boundary、Section 8 Adapter 分類、Section 2 架構圖、Section 11 驗收標準、Section 1 能力描述 |
| F2 | `tasks/plan-phase5-medical-ai-platform.md` | 🟡 **中度修改** | Section 12 Batch 拆分（7→3）、Section 13 驗收標準、Section 14 Phase 4 依賴項目 |
| F3 | `tasks/phase4-phase5-dependency-map.md` | 🟡 **中度修改** | Batch 依賴關係重繪、對應矩陣更新 |
| F4 | `tasks/roadmap-phase4-phase5.md` | 🟡 **中度修改** | 整個 roadmap 依新 Batch 結構重寫 |
| F5 | `tasks/research/phase4-phase5-gap-analysis.md` | 🟢 **輕度修改** | 更新 RAG (#1)、Background Jobs (#16) 的優先級與範圍標記 |

---

## 3. 任務清單

### 3.1 Task A — Phase 4 Section 5：Transaction Boundary 修改

**修改檔案**：`tasks/plan-phase4-clinical-ai-productization.md`

**修改內容摘要**：將 Transaction Boundary 從「Repository 為 transaction owner」改為「Service 為 transaction owner；Repository 僅 flush，無 commit/rollback」。

**具體修改點**：

| # | 位置 | 現有內容 | 改為 |
|---|------|---------|------|
| A.1 | Section 5.1 Fig 1（Transaction Boundary 現狀圖） | Repository 層顯示 `begin() / commit() / rollback()` | Repository 層僅顯示 `flush()`；Service 層顯示 `begin() / commit() / rollback()` |
| A.2 | Section 5.2 Fig 2（Phase 4 Transaction Boundary 圖） | Repository 擁有 transaction scope | Service 擁有 transaction scope；Repository 僅執行 flush |
| A.3 | Section 5.2 說明文字（Repository 段落） | "Repository 負責…" 含 transaction 語義 | Repository 負責資料持久化操作（add/get/update/delete + flush），不管理 transaction |
| A.4 | Section 5.3（跨邊界事務原則表） | "Local transaction first" 說明不明確 | 新增原則：「Service owns transaction — Service 層使用 @transactional decorator 或 context manager 管理 transaction 生命週期；Repository 僅負責 flush 操作」 |
| A.5 | Section 5.3 | "Adapter calls are fire-and-forget" | 改為「Adapter calls are sync or async based on classification」— 同步 adapter 回傳結果；非同步 adapter 透過 job queue（若存在）或背景執行緒處理 |

**備註**：不修改 production code，只修改文件中的 boundary 描述。

---

### 3.2 Task B — Phase 4 Section 8：Adapter 同步/非同步分類

**修改檔案**：`tasks/plan-phase4-clinical-ai-productization.md`

**修改內容摘要**：將 adapter 從「全部 fire-and-forget」改為明確分類同步與非同步。

**具體修改點**：

| # | 位置 | 現有內容 | 改為 |
|---|------|---------|------|
| B.1 | Section 8.3（Adapter 實作優先級表） | 無同步/非同步分類 | 新增「同步/非同步」欄位：CIViCAdapter→同步, DGIdbAdapter→同步, OncoTreeAdapter→同步, MyVariantAdapter→同步, EnsemblVEPAdapter→同步, OpenCRAVATAdapter→同步（local tool）DRKGAdapter→同步, PharmCATAdapter→同步（local tool） |
| B.2 | Section 8.2 Fig | 無 async/sync 標記 | 在 diagram 中標記 Sync Adapter（即時查詢）與 Async Adapter（背景更新） |
| B.3 | Section 8.2 快取說明段落 | "每個 adapter 需實作 response caching" | 新增：「同步 adapter 必須 real-time 回應；非同步 adapter（Guideline Sync, Background Refresh, Cache Refresh）可透過排程更新或事件驅動觸發」 |
| B.4 | Section 5.3 跨邊界原則 | "Adapter calls are fire-and-forget" | 改為：「同步 adapter 呼叫在 request 生命週期內完成，失敗由 retry policy 處理；非同步 adapter 呼叫透過背景機制處理，不阻塞 request 回應」 |

**備註**：由於 R4 禁止 Redis/ARQ，非同步 adapter 的排程機制改用 PostgreSQL-based 簡單實作或背景 threading（Technology Agnostic 方案），不在 Phase 4 引入訊息佇列。

---

### 3.3 Task C — Phase 4 Section 10：Batch 拆分全面重寫（6 → 3 Vertical Slices）

**修改檔案**：`tasks/plan-phase4-clinical-ai-productization.md`

**修改內容摘要**：將 6 個技術模組 Batch（B1-B6）替換為 3 個 Vertical Slice Batch，每個 Batch 涵蓋完整技術棧。

**具體修改點**：

| # | 位置 | 現有內容 | 改為 |
|---|------|---------|------|
| C.1 | Section 10.1（Batch 總覽） | 6 Batch + 相依圖 | 3 Batch + 新的垂直分層相依圖（各 Batch 可並行，相依於 PostgreSQL migration 順序） |
| C.2 | Section 10.2-10.7（各 Batch 定義） | B1-B6 共 6 個小節 | B1-B3 共 3 個小節，每節包含：功能範圍、檔案清單、角色、前置依賴、CI 要求、驗收標準、風險 |
| C.3 | Section 10.2（新 B1） | FHIR R4（純技術 Batch） | **Batch 1：病患資料整合與證據匯入** — 端到端工作流：VCF 上傳→變異分析→外部證據查詢（CIViC/DGIdb）→知識圖譜更新→FHIR Patient/Observation 匯出→Audit→Frontend 顯示。涵蓋 FHIR（Patient/Observation）、Adapter（CIViC/DGIdb P0）、CI/CD、Docker、Observability |
| C.4 | Section 10.3（新 B2） | External Adapters（純技術 Batch） | **Batch 2：臨床決策與治療計畫** — 端到端工作流：臨床決策請求→Agent 系統→證據檢索→推薦生成→治療計畫建立→FHIR CarePlan/DiagnosticReport/Condition 匯出→Audit→Digital Thread→Frontend 顯示。涵蓋 FHIR（CarePlan/DiagnosticReport/Condition）、Adapter（OncoTree/MyVariant/EnsemblVEP P1）、CI/CD、Docker、Observability |
| C.5 | Section 10.4（新 B3） | RAG/Vector DB（被移除） | **Batch 3：藥物安全與治療監控** — 端到端工作流：藥物交互檢查→禁忌症偵測→治療修訂→監控設定→FHIR MedicationRequest/Procedure 匯出→Audit→Frontend 安全儀表板。涵蓋 FHIR（MedicationRequest/Procedure）、Adapter（OpenCRAVAT/DRKG/PharmCAT P2）、CI/CD、Docker、Observability（監控儀表板+健康檢查） |
| C.6 | Section 10 前置依賴圖 | B1→B5→B6 等複雜鏈 | 3 個 Batch 可並行啟動（各自獨立），僅有的相依為 PostgreSQL migration 順序 |
| C.7 | Section 10 檔案清單總表 | 舊 Batch 檔案（含 RAG/Redis/Service 拆分/Frontend 重構） | 移除 RAG/Vector DB 相關檔案、移除 Redis/ARQ 相關檔案、移除 Frontend 重構檔案、移除 Service 重構檔案 |

**新 Batch 結構詳見 [附錄](#7-附錄vertical-slice-batch-設計)**。

---

### 3.4 Task D — Phase 4 Section 1 & 2：能力描述與架構圖更新

**修改檔案**：`tasks/plan-phase4-clinical-ai-productization.md`

**修改內容摘要**：移除被排除的能力（RAG、Background Jobs/Redis、Service Refactor、Frontend 重構），更新架構圖。

**具體修改點**：

| # | 位置 | 現有內容 | 改為 |
|---|------|---------|------|
| D.1 | Section 1.2（新增能力表） | #3 RAG (P1)、#6 前端 API Client (P2)、#7 前端頁面強化 (P2)、#8 Service 重構 (P2)、#11 Background Jobs/Queue (P0) | 刪除 #3、#6、#7、#8、#11；重新編號和能力列表 |
| D.2 | Section 1.3（排除能力） | 無對應排除項目 | 新增排除：「RAG/Vector DB（推遲至 Phase 5+，因禁止引入新基礎元件）」、「Background Jobs Queue（推遲至 Phase 5+，因 Redis 為禁止引入的元件）」、「Frontend 重構與 Service 重構（不屬於產品化阻擋項）」 |
| D.3 | Section 2.1 高層架構圖 | Clinical Intelligence Layer 含 Vector DB、RAG | 移除 Vector DB 與 RAG 標示；Production Platform Layer 移除 Redis/Queue 標示 |
| D.4 | Section 2.2.1（Clinical Intelligence Layer 表） | "RAG / Vector DB 🔴 新建" | 刪除該行 |
| D.5 | Section 2.2.4（Production Platform Layer 表） | "Background Jobs Service 🔴 新建" | 刪除該行；Observability 保留但簡化（Prometheus metrics + health check，無 Redis/ARQ） |
| D.6 | Section 2.3（既有元件複用表） | "僅拆分 treatment_plan_service"、"僅 Tools/KnowledgeBase/Research 需強化" | 移除 treatment_plan_service 拆分和 KnowledgeBase/Research 強化描述 |

---

### 3.5 Task E — Phase 4 Section 9 & 11：Deployment Boundary 與驗收標準更新

**修改檔案**：`tasks/plan-phase4-clinical-ai-productization.md`

**修改內容摘要**：移除 Redis/Vector DB 相關部署設定，更新驗收 Gate。

**具體修改點**：

| # | 位置 | 現有內容 | 改為 |
|---|------|---------|------|
| E.1 | Section 9.2 Deployment Boundary 圖 | Vector DB 和 Redis 出現在 dev 與 prod 環境中 | 移除 Vector DB 和 Redis 服務 |
| E.2 | Section 9.3 部署原則 | "Container-first" 提到 Vector DB | 移除 Vector DB 相關描述 |
| E.3 | Section 11.1 整體 Gate | G3（語義檢索 Gate）、G4（基礎設施與監控 Gate 含 Redis/Job queue）、G6（程式碼品質 Gate 含 Service 拆分） | 移除 G3、G4、G6；重新編號為 G1-G4 |
| E.4 | Section 11.2 Batch 驗收標準 | B3（RAG）、B4（Observability+Jobs）、B6（Frontend+Service） | 更新為新 Batch 1/2/3 的驗收標準 |
| E.5 | Section 11.3 禁止事項 | "不引入 Kafka/其他 message broker（Redis 因 Background Jobs 需要而引入）" | 「不引入 Redis、Kafka、Vector DB、Qdrant、Chroma 等新基礎元件。保持 Technology Agnostic，除非 Gap Analysis + ADR + Current Capability 共同證明必要」 |
| E.6 | Section 11.4 交付檢查清單 | "6 個 Batch"、"RAG"、"Background Jobs" | 「3 個 Vertical Slice Batch」；移除 RAG/Jobs 相關行 |

---

### 3.6 Task F — Phase 4 其他 Sections 文案更新

**修改檔案**：`tasks/plan-phase4-clinical-ai-productization.md`

**修改內容摘要**：全文件文案中參照被刪除項目的文字同步清理。

**具體修改點**：

| # | 位置 | 現有內容 | 改為 |
|---|------|---------|------|
| F.1 | Section 3（Data Flow） | 若提及 RAG、Vector DB、Background Jobs | 移除相關路徑 |
| F.2 | Section 4（Security Boundary） | 若提及 SMART-on-FHIR 與 Background Jobs 安全 | 移除 Background Jobs 安全描述 |
| F.3 | Section 6（FHIR Boundary） | 若有對 RAG 的參照 | 移除 |
| F.4 | Section 7（Knowledge Graph Boundary） | 若有對 RAG 的參照 | 移除「RAG 與 KG 互補」段落 |
| F.5 | Section 0 標題行 | "6 個技術模組 Batch" | 改為「3 個 Vertical Slice Batch」 |

---

### 3.7 Task G — Phase 5 Section 12：Batch 拆分（7 → 2/3 Batches）

**修改檔案**：`tasks/plan-phase5-medical-ai-platform.md`

**修改內容摘要**：將 7 個 Batch 合併為 2-3 個，重新設計交付順序。

**具體修改點**：

| # | 位置 | 現有內容 | 改為 |
|---|------|---------|------|
| G.1 | Section 12.1（整體時程） | 16-20 週 | 更新為新結構的時程預估 |
| G.2 | Section 12.2-12.8（B1-B7） | 7 個獨立 Batch | 合併為 2 或 3 個 Batch |
| G.3 | Section 12.2（新 B1） | B1（Platform Core）+ B2（Specialty Contract + Cardiology）+ B4（KG Namespace + Terminology）部分 | **Batch 1：Platform Core + Specialty Framework** — 包含所有 Registry、Specialty Module Contract、TerminologyService、KnowGraphGo Namespace。目標：完成 Platform 骨架 + Cardiology Sample Module |
| G.4 | Section 12.3（新 B2） | B3（Oncology 抽象化）+ B5（Tenant Isolation）+ B6（Neurology + Radiology）部分 | **Batch 2：Oncology Decoupling + Multi-Tenant** — 包含 Oncology 抽象化、Tenant Isolation、API Versioning。目標：提取通用介面 + 多租戶資料隔離 |
| G.5 | Section 12.4（新 B3，選擇性） | B6（Neurology + Radiology）+ B7（Docs） | **Batch 3（選擇性）：Specialty 樣板 + 驗收** — 包含 Neurology/Radiology Sample、文件、遷移指南、安全審查。目標：驗證 Platform 跨專科能力 + 完成文檔 |

**推薦方案**：2 個 Batch（B1+B2），B3 為選擇性延伸。若時間充足可擴充至 3 個。

---

### 3.8 Task H — Phase 5 Section 13 & 14：驗收標準與跨期依賴更新

**修改檔案**：`tasks/plan-phase5-medical-ai-platform.md`

**修改內容摘要**：移除對 Phase 4 RAG/Redis/Service Refactor 的依賴引用，更新驗收標準。

**具體修改點**：

| # | 位置 | 現有內容 | 改為 |
|---|------|---------|------|
| H.1 | Section 13.1（強制標準 AC1-AC9） | 保持 AC1-AC9 內容 | 新增 AC10：「未引入禁止清單的新基礎元件（Technology Agnostic）」 |
| H.2 | Section 14（Phase 4 依賴項目表） | 含「RAG/Vector DB/Embedding Pipeline」、「Frontend API Client 統一封裝」 | 移除 RAG 和 Frontend API Client 行 |
| H.3 | Section 14.1 相依性矩陣 | RAG / Frontend 行 | 刪除對應行 |
| H.4 | Section 14.2/3（若存在文案） | 對 Phase 4 RAG 的參照 | 清理 |

---

### 3.9 Task I — Phase 5 附錄 A：檔案變更清單更新

**修改檔案**：`tasks/plan-phase5-medical-ai-platform.md`

**修改內容摘要**：反映新的 Batch 結構。

**具體修改點**：

| # | 位置 | 現有內容 | 改為 |
|---|------|---------|------|
| I.1 | 附錄 A.1（新檔案） | 按 7-Batch 結構排列 | 按 2-3 Batch 結構重新整理 |
| I.2 | 附錄 A.2（修改檔案） | 同上 | 更新 |
| I.3 | 附錄 A.3（無需修改） | 同上 | 更新 |

---

### 3.10 Task J — Dependency Map 更新

**修改檔案**：`tasks/phase4-phase5-dependency-map.md`

**修改內容摘要**：重新繪製依賴圖，反映新的 3-Batch（Phase 4）+ 2-3 Batch（Phase 5）結構。

**具體修改點**：

| # | 位置 | 現有內容 | 改為 |
|---|------|---------|------|
| J.1 | Section 2（Phase 4 Batch 依賴總圖 + Mermaid） | 6-Batch 圖 | 3-Batch 圖（B1/B2/B3 可並行） |
| J.2 | Section 3（Phase 4 詳細依賴矩陣） | B1-B6 各矩陣 | 新 B1-B3 各矩陣，移除 RAG/Redis/Service Refactor 依賴 |
| J.3 | Section 4（Phase 5 Batch 依賴總圖 + Mermaid） | 7-Batch 圖 | 2-3 Batch 圖 |
| J.4 | Section 5（Phase 5 詳細依賴矩陣） | B1-B7 各矩陣 | 新 B1-B3 各矩陣 |
| J.5 | Section 6（Phase 4 → Phase 5 跨期依賴） | 含 RAG/Frontend/Queue | 移除 RAG、Frontend API Client、Background Jobs 行 |
| J.6 | Section 7（關鍵依賴鏈） | 舊 Batch 鏈 | 新 Batch 鏈 |
| J.7 | Section 8（並行組合建議） | 子代理 9 個 | 重新配置子代理（FHIR+Adapter、Observability+Docker、Platform Core 等） |
| J.8 | Section 9（風險緩解） | R2（Vector DB）、R13/R14/R15（Redis/ARQ） | 移除 R2（Vector DB）、R13/R14/R15（Redis/ARQ）；保留 R1/FHIR、R5/Oncology Decoupling 等 |
| J.9 | Section 11（Gap Analysis 對應矩陣） | #1 RAG→B3、#16 Background Jobs→B4 | #1 RAG→標記為「Deferred to Phase 5+ (per R2 review)」；#16 Background Jobs→標記為「Deferred」 |

---

### 3.11 Task K — Roadmap 更新

**修改檔案**：`tasks/roadmap-phase4-phase5.md`

**修改內容摘要**：完全根據新 Batch 結構重寫。

**具體修改點**：

| # | 位置 | 現有內容 | 改為 |
|---|------|---------|------|
| K.1 | Phase 4 全部 Batch 定義（B1-B6） | 舊 6 Batch 的目標/依賴/交付/驗收/Gate | 新 3 Batch 的完整定義 |
| K.2 | Phase 5 全部 Batch 定義（B1-B7） | 舊 7 Batch | 新 2-3 Batch |
| K.3 | 跨 Phase 依賴概要表 | RAG/Frontend | 移除 |
| K.4 | 附錄 Batch 依賴關係 | 舊結構 | 新結構 |

---

### 3.12 Task L — Gap Analysis 更新

**修改檔案**：`tasks/research/phase4-phase5-gap-analysis.md`

**修改內容摘要**：輕度修改，標記 RAG 與 Background Jobs 的優先級/範圍變更。

**具體修改點**：

| # | 位置 | 現有內容 | 改為 |
|---|------|---------|------|
| L.1 | Section 1（RAG/Evidence Retrieval） | Priority=P0, Phase 4 範圍 | Priority=Deferred to Phase 5+, 因審查要求禁止引入 Vector DB 等新基礎元件；Phase 4 內以純文字搜尋/關鍵字搜尋補位（若有） |
| L.2 | Section 16（Background Jobs/Queue） | Priority=P1, ✅ 已實現 | Priority=Deferred to Phase 5+, 因審查要求禁止 Redis；Phase 4 內以簡化方案處理 async adapter（如背景 threading 或 PostgreSQL-based queue） |
| L.3 | 總結優先級矩陣（Phase 4 必須完成） | #1 RAG P0、#16 Background Jobs P0 | 移除 #1、#16；相應調整工時估計 |
| L.4 | 關鍵風險摘要 | RAG 技術選擇風險、NCCN API 授權風險等 | 新增風險：「R4. 審查禁止新基礎元件 — Vector DB/Redis 被排除，Phase 4 RAG 與 Background Jobs 需重新設計或延後」 |

---

## 4. 依賴關係

### 4.1 任務執行順序

```
Phase 1：核心語義修改（不可並行）
  Task A (Transaction Boundary) ─── 無前置，優先處理
  Task B (Adapter 分類)        ─── 無前置，可與 A 並行
  Task C (Batch 拆分)          ─── 無前置，但建議 A/B 完成後再改，因 Batch 內可能引用 Boundary 定義

Phase 2：架構與能力更新
  Task D (能力描述+架構圖)    ─── 依賴 Task C（Batch 結構決定能力列表）
  Task E (Deployment+驗收)    ─── 依賴 Task C（Gate 對應 Batch）
  Task F (其他文案清理)       ─── 依賴 Task D/E（等大改完成後做 cleanup）

Phase 3：Phase 5 相關
  Task G (Phase 5 Batch 重組) ─── 依賴 Task C（Phase 5 Batch 結構參考 Phase 4 新結構）
  Task H (Phase 5 驗收+依賴)  ─── 依賴 Task G
  Task I (Phase 5 附錄)       ─── 依賴 Task G

Phase 4：相關文件同步
  Task J (Dependency Map)      ─── 依賴 Task C + Task G
  Task K (Roadmap)             ─── 依賴 Task C + Task G + Task J
  Task L (Gap Analysis)        ─── 依賴 Task C（需知道哪些維度被延後）
```

### 4.2 並行建議

```
Day 1:     Task A ────────┐
           Task B ────────┤ → 可並行
           Task C ────────┘
Day 2:     Task D ────────┐
           Task E ────────┤ → 可並行（依賴 C 完成）
           Task F ────────┘
           Task G ──────── (可與 D/E/F 並行)
Day 3:     Task H ────────┐
           Task I ────────┤ → 可並行（依賴 G 完成）
           Task J ────────┘
           Task K ──────── (依賴 J)
           Task L ──────── (依賴 C，可提前)
```

---

## 5. 負責角色

所有文件修改由 **doc-writer** 角色統一執行。無需其他角色介入。

修改原則：
- **不修改 production code**（僅修改計劃文件）
- **不引入新的 infrastructure 決策**（不決定用什麼替代 Redis/Vector DB，只標記為 deferred）
- **保持文件間一致性**（每完成一個 Task，檢查其他文件是否有交叉引用需要更新）
- **每個 Task 完成後需 self-review**（確認修改內容與審查要求一致）

---

## 6. 注意事項

### 6.1 不要動的內容

1. **Phase 3 既有能力描述**（Section 1.1）— 繼承自 Phase 3 的能力不修改，僅移除 Phase 4 新增項
2. **KnowGraphGo 相關描述**（Section 7）— 保持不修改，僅移除對 RAG 的參照
3. **既有 Domain Models / Repositories / Engines / Agents 描述**（Section 2.3）— 僅移除被排除的修改項，不改變既有複用描述
4. **Phase 5 的 Oncology 耦合盤點**（Section 1）— 保持不變
5. **Phase 5 的 Registry/Plugin 設計**（Section 2-10）— 保持不變，僅 Batch 拆分和依賴需要更新

### 6.2 要特別小心的部分

1. **跨文件引用一致性** — Phase 4 Batch 編號變更後，Dependency Map、Roadmap、Gap Analysis 中所有引用必須同步更新
2. **Gate 編號重新映射** — 舊 G1-G7 刪除 G3/G4/G6 後變為 G1-G4，所有交叉引用需更新
3. **Batch 檔案清單** — 刪除 RAG/Redis/Service 重構/Frontend 重構的檔案時，確保不移除仍然需要的檔案（如既有 Frontend 檔案）
4. **架構圖 ASCII art** — 手動更新架構圖時注意對齊，確保圖形仍可讀
5. **Transaction Boundary 修改** — 只改文件中的 boundary 描述，不改對應的 codebase 位置描述（Repository 的實際 code 不在本計劃範圍）
6. **Adapter 分類** — 同步/非同步分類僅是文件層面的設計決策，不影響實際的 adapter 實作順序
7. **Phase 5 Batch 合併** — 合併時確保不遺失任何既有的交付項內容（只是重新分組，不刪除功能）

### 6.3 修改完成後的驗證

1. 全文搜尋 `RAG|Vector|Redis|ARQ|Chroma|Qdrant|Kafka` 確認無遺留引用（在 Phase 4 文件中）
2. 確認 Phase 4 文件中無 `treatment_plan_service` 拆分或前端重構的相關描述
3. 確認 Phase 5 文件中的相依性矩陣不引用被刪除的 Phase 4 交付項
4. 確認 3 個新 Batch 的驗收標準不包含「引入新基礎元件」的要求
5. 確認每個 Batch 描述中有明確列出「端到端工作流路徑」

---

## 7. 附錄：Vertical Slice Batch 設計

### 7.1 設計原則

1. **每個 Batch 是一個完整的端到端臨床工作流**
2. **每個 Batch 涵蓋所有技術層**：API → Domain → Service → Repository → Frontend → Audit → Knowledge Graph → Digital Thread → CI → PostgreSQL → Migration → Documentation
3. **每個 Batch 可獨立交付和測試** — 不依賴其他 Batch 的完成
4. **每個 Batch 不引入新的基礎元件** — 無 Redis/Vector DB/Kafka/Chroma/Qdrant
5. **Frontend 變更最小化** — 僅新增必要顯示元件，不重構既有頁面

### 7.2 Batch 1：病患資料整合與證據匯入

**端到端工作流**：
```
External EHR → FHIR Patient Import → VCF Upload → Variant Analysis
→ External Evidence Query (CIViC, DGIdb) → Knowledge Graph Update
→ FHIR Patient/Observation Export → Audit Log → Frontend Display
```

**技術棧覆蓋**：

| 層級 | 涵蓋內容 |
|------|---------|
| API | FHIR Patient Read/Search/Create, FHIR Observation Read/Search, VCF Upload 端點 |
| Domain | PatientModel, CancerCaseModel, VariantModel, EvidenceItem |
| Service | FHIRService (Patient+Observation), EvidenceQueryService, KnowledgeIngestionService |
| Repository | PatientRepository, CancerCaseRepository, EvidenceRepository, ClinicalGraphRepository |
| Frontend | Patient 顯示、Evidence 狀態面板（既有頁面擴充） |
| Audit | FHIR 端點 Audit Log、Evidence 查詢 Audit |
| KG | KnowGraphGo 注入（既有，使用 adapter 寫入通道） |
| Digital Thread | VCF→Evidence 路徑追蹤 |
| CI | Go CI（KnowGraphGo）、Python CI 擴充 |
| PostgreSQL | FHIR 資源表 migration（若需） |
| Document | FHIR API 文件、Evidence Adapter 文件 |

**Adapters**（同步）：CIViCAdapter, DGIdbAdapter

### 7.3 Batch 2：臨床決策與治療計畫

**端到端工作流**：
```
Clinical Decision Request → Agent System (Diagnosis/Guideline/Trial/Drug)
→ Evidence Retrieval (OncoTree, MyVariant, Ensembl VEP)
→ Recommendation Engine → Ranking Engine → Treatment Plan
→ FHIR CarePlan/DiagnosticReport/Condition Export
→ Audit → Digital Thread → Frontend Display (Recommendation, Treatment Plan)
```

**技術棧覆蓋**：

| 層級 | 涵蓋內容 |
|------|---------|
| API | FHIR CarePlan/DiagnosticReport/Condition Read/Search/Create, Decision API 端點 |
| Domain | TreatmentPlanModel, CarePlanModel, ClinicalContext |
| Service | ClinicalDecisionService, RecommendationService, TreatmentPlanService, FHIRService (CarePlan) |
| Repository | TreatmentPlanRepository, RecommendationRepository |
| Frontend | Recommendation 面板、Treatment Plan 面板（既有頁面擴充） |
| Audit | Decision Audit Log、Plan Audit |
| KG | KnowGraphGo 查詢（既有） |
| Digital Thread | Decision→Plan 路徑 |
| CI | Docker CI（Dockerfile 建置） |
| PostgreSQL | CarePlan/FHIR 相關 migration |
| Docker | docker-compose.yml（含 backend+frontend+KG+PG） |
| Document | 部署指南 |

**Adapters**（同步）：OncoTreeAdapter, MyVariantAdapter, EnsemblVEPAdapter

### 7.4 Batch 3：藥物安全與治療監控

**端到端工作流**：
```
Drug Interaction Check (DRKG, PharmCAT) → Contraindication Detection
→ Treatment Revision → Monitoring Setup
→ FHIR MedicationRequest/Procedure Export
→ Audit → Frontend Safety Dashboard
→ Health Check → Metrics Endpoint → Observability Dashboard
```

**技術棧覆蓋**：

| 層級 | 涵蓋內容 |
|------|---------|
| API | FHIR MedicationRequest/Procedure Read/Search/Create, Drug Interaction API, Health Check /metrics |
| Domain | DrugInteractionModel, ContraindicationModel, MonitoringModel |
| Service | DrugSafetyService, MonitoringService, FHIRService (MedicationRequest) |
| Repository | DrugInteractionRepository, MonitoringRepository |
| Frontend | 安全儀表板（既有頁面擴充） |
| Audit | Drug Safety Audit Log |
| KG | KnowGraphGo 查詢（既有） |
| Digital Thread | Drug→Safety→Revision 路徑 |
| CI | Docker CI 完成、Security Scan |
| Docker | docker-compose.prod.yml 完成、Nginx 設定 |
| Observability | Prometheus metrics, Health Check 擴充, 結構化 logging |
| Document | 部署指南完成、安全文件 |

**Adapters**（同步）：OpenCRAVATAdapter, DRKGAdapter, PharmCATAdapter

### 7.5 Batch 相依關係總結

```
Phase 4 三個 Vertical Slice Batch 可完全並行執行：

┌─────────────────────────────────────────────────────────────────┐
│                    Phase 4 啟動 Gate                             │
│  ┌─ 既有 Phase 3 功能齊全                                       │
│  └─ 所有既有 test suite pass (~148 tests)                       │
└─────────────────────────────┬───────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
    │   Batch 1   │    │   Batch 2   │    │   Batch 3   │
    │   病患資料    │    │   臨床決策    │    │   藥物安全    │
    │   整合與     │    │   與治療      │    │   與監控     │
    │   證據匯入   │    │   計畫       │    │             │
    │  (P0/P1)    │    │  (P0/P1)    │    │  (P1/P2)   │
    └──────┬──────┘    └──────┬──────┘    └──────┬──────┘
           │                  │                  │
           └──────────────────┼──────────────────┘
                              ▼
                    ┌───────────────────┐
                    │   Phase 4 Exit Gate │
                    │   (G1-G4)         │
                    └───────────────────┘
```

每個 Batch 內部依賴順序（非跨 Batch）：
```
API 端點 → Domain 模型（既有）→ Service 邏輯 → Repository（既有）
                                                ↓
→ Frontend 顯示 → Audit → KG 注入 → CI → Docker
```

---

> **文件結束** — 本計劃定義了 Phase 4 & Phase 5 Master Plan R2 返工的所有任務、依賴關係與注意事項。
> 執行順序：doc-writer 按 Phase 1 → Phase 2 → Phase 3 → Phase 4 依序執行，每完成一個 Task 後 self-review。
