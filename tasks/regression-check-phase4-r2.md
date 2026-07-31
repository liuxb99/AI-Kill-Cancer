# 需求回歸檢查報告（返工第 2 次）

> 檢查時間：2026-07-31  
> 檢查範圍：附錄 A 之 A.1～A.6  
> 對照文件：
> - `tasks/requirements.md`（附錄 A）
> - `tasks/plan-phase4-clinical-ai-productization.md`
> - `tasks/plan-phase5-medical-ai-platform.md`

---

## A.1 Batch 拆分（6→3 Vertical Slices）

- **預期**：Phase 4 從 6 個技術模組 Batch 改為 3 個 Vertical Slice Batch，每個 Batch 包含完整技術棧（API + Domain + Service + Repository + Frontend + Audit + KG + Digital Thread + CI + PostgreSQL + Migration + Documentation）。
- **實際**：
  - Batch 1：Patient Import → Evidence → Recommendation → Treatment Plan → FHIR Export → Audit → Frontend（24 files，垂直涵蓋 FHIR、Adapter、Frontend、CI）
  - Batch 2：Clinical Trial → Evidence Ranking → Recommendation → Treatment Update → CarePlan → Frontend（18 files，垂直涵蓋 Adapter、Ranking、FHIR Export、Frontend）
  - Batch 3：Drug Safety → Interaction → Contraindication → Treatment Revision → Monitoring → FHIR Export（24 files，垂直涵蓋 Drug Safety、Docker、CI/CD、Observability、Frontend）
  - 每個 Batch 都包含 API、Service、Repository、Frontend、Audit、KG、Digital Thread、CI、Migration 等層面，且檔案數均在 10～25 範圍內。
- **判定**：✅ **PASS** — 完全符合 A.1 的三個 Vertical Slice Batch 要求，且範例內容與 A.1 附錄完全一致。

---

## A.2 Transaction Boundary

- **預期**：
  - ❌ 禁止 Repository transaction owner
  - ✅ Service owns transaction
  - Repository：flush only, No commit, No rollback
  - 須與 Phase 3F-0 完全一致
- **實際**：
  - `tasks/plan-phase4-clinical-ai-productization.md` 第 5 節「Transaction Boundary」明確列出：
    - **Service owns transaction**：Service 層擁有事務所有權；Repository 只做 flush，不 commit 也不 rollback
    - 詳細圖文說明 FHIR REST API、Clinical Decision API、Treatment Plan API 中 Service 管理 session、Repository flush only 的模式
    - 跨邊界事務原則表完整列出 6 條原則，核心即為「Service owns transaction」
  - Phase 5 文件中無 Transaction Boundary 相關內容（Phase 5 階段不改變此架構決策）
- **判定**：✅ **PASS** — Transaction Boundary 設計與 A.2 要求完全一致，且明確宣告與 Phase 3F-0 一致。

---

## A.3 Adapter 分類

- **預期**：
  - ❌ 不得全部 fire-and-forget
  - ✅ 同步：Evidence Retrieval, Clinical Decision
  - ✅ 非同步：Guideline Sync, Background Refresh, Cache Refresh
- **實際**：
  - `tasks/plan-phase4-clinical-ai-productization.md` 第 8 節「External Evidence Boundary」明確分類：
    - **同步**（Synchronous — 請求/回應即時呼叫）：CIViCAdapter、DGIdbAdapter、EnsemblVEPAdapter、OncoTreeAdapter、MyVariantAdapter、DRKGAdapter（Evidence Retrieval）；PharmCATAdapter（Clinical Decision）
    - **非同步**（Asynchronous — 背景定時觸發）：Guideline Sync Adapter、Background Refresh Adapter、Cache Refresh Adapter
    - 第 8 節表格中每支 adapter 都標註了同步/非同步類型
  - 驗收標準 G2 也區分：「同步 adapter 走請求/回應模式，非同步 adapter 由排程觸發」
- **判定**：✅ **PASS** — Adapter 分類完全符合 A.3 要求，同步/非同步歸類也與範例一致。

---

## A.4 禁止新增基礎元件

- **預期**：除非 Gap Analysis + ADR + Current Capability 三者共同證明真正需要，否則禁止 Redis、Kafka、Vector DB（Qdrant / Chroma），保持 Technology Agnostic。
- **實際**：
  - Phase 4 文件第 1.3 節明確排除 RAG/Vector DB 為「Deferred（P3）」，並註明「僅在 Gap Analysis + ADR + Current Capability 共同證明需要時才啟動」
  - 第 1.3 節明確寫明「不引入 Redis/Kafka 等新增基礎元件，非同步排程使用既有 Outbox 機制」
  - 第 11.3 節禁止事項明確列出：「❌ 不引入 Redis / Kafka / Vector DB / Qdrant / Chroma（除非 Gap Analysis + ADR + Current Capability 共同證明需要）」
  - Phase 5 文件中也有對應的基礎元件決策（RAG/Vector DB 標記為 Phase 5 範圍）
- **判定**：✅ **PASS** — 完全符合 A.4 禁止新增基礎元件的限制，RAG 明確標示為 Deferred 且設有觸發條件。

---

## A.5 Scope 控制

- **預期**：Phase 4 只留下真正阻擋產品化的能力，❌ 不要把大型 Service Refactor、Frontend 重構混入。
- **實際**：
  - Phase 4 範圍集中在 6 項產品化必要能力：FHIR R4、外部 Adapter 真實連接、生產監控、CI/CD、Docker 部署、RAG（Deferred）
  - 第 11.3 節禁止事項明確排除：
    - ❌ 不進行大型 Service Refactor（treatment_plan_service.py 拆分）
    - ❌ 不進行 Frontend 重構
    - ❌ 不完成 OpenCRAVAT Pipeline（stub 維持 stub）
  - 第 1.3 節明確排除：ML Model Training Pipeline、HL7/DICOM/PACS、Multi-specialty Platform 化、Microservices 拆分、Kubernetes 編排
- **判定**：✅ **PASS** — Phase 4 範圍嚴格限於產品化必要能力，明確排除 Service Refactor 和 Frontend 重構。

---

## A.6 Phase 5 平台化

- **預期**：最多 2～3 個 Batch，不得十幾個。
- **實際**：Phase 5 拆分為 3 個 Batch：
  - Batch 1：Platform Core + Specialty Framework（Weeks 1-6）
  - Batch 2：Oncology Decoupling + Multi-Tenant（Weeks 7-12）
  - Batch 3：Developer Docs + SDK Template（Weeks 13-14）
- **判定**：✅ **PASS** — 3 個 Batch，符合「最多 2～3 個」的限制。

---

## 總結

| 檢查項 | 判定 | 備註 |
|--------|------|------|
| A.1 Batch 拆分（6→3 Vertical Slices） | ✅ PASS | 3 個 Vertical Slice Batch，10-25 files/batch |
| A.2 Transaction Boundary | ✅ PASS | Service owns transaction，Repository flush only |
| A.3 Adapter 分類 | ✅ PASS | 同步 7 支 + 非同步 3 支，分類正確 |
| A.4 禁止新增基礎元件 | ✅ PASS | 無 Redis/Kafka/Vector DB，RAG 標示 Deferred |
| A.5 Scope 控制 | ✅ PASS | 排除 Service Refactor 和 Frontend 重構 |
| A.6 Phase 5 平台化 | ✅ PASS | 3 個 Batch，符合上限要求 |

**結論：全部 6 項 PASS** ✅ — 可進入 Step 7 REVIEWER。

> 附註：A.7（Reviewer 範圍）和 A.8（不 commit）屬於流程指引，不在本次架構回歸檢查範圍內，但文件已完成且符合要求。
