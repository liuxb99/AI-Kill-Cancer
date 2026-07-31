# 專案現況盤點報告

## 生成資訊
- 日期：2026-07-31
- 範圍：全部 production code（src/backend/、src/frontend/、KnowGraphGo/、migrations/、tests/、docs/、models/）
- 方法：逐目錄遍歷 + 關鍵檔案閱讀 + 符號搜索 + grep 模式比對

## 盤點摘要總表

| # | 維度 | 狀態 | 關鍵檔案數 | TODO/FIXME | Phase 4 可複用 | Phase 5 前須重構 |
|---|------|------|-----------|------------|---------------|-----------------|
| 1 | Domain Models | ✅ Complete | 17 模型檔案 + enums.py (~395 行) | 無 | ✅ 可直接複用 | 無 |
| 2 | Services | ✅ Complete | 7 Service 類 | 無 | ✅ 可直接複用 | 治療計畫 service 58842 行需拆分 |
| 3 | Repositories | ✅ Complete | 23 Repository 類 + BaseRepository | 無 | ✅ 可直接複用 | 無 |
| 4 | API Routes | ✅ Complete | 23 路由檔案, 100+ 端點 | 無 | ✅ 可直接複用 | 無 |
| 5 | Engines | ✅ Complete | 5 引擎 (Clinical/Decision/Ranking/Reasoning/Explainable) | 無 | ✅ 可直接複用 | 無 |
| 6 | Adapters | 🟡 Partial | 10 註冊項, 8/10 為 stub | 8 個 stub | ⚠️ 樞紐合用 | 需逐一實作真實連接 |
| 7 | Knowledge Layer | ✅ Complete | 6 檔案 (models/repository/service/identifiers/adapters) | 無 | ✅ 可直接複用 | 無 |
| 8 | Agents | ✅ Complete | 9 檔案 (6 Agent + Orchestrator + Consensus + Base) | 無 | ✅ 可直接複用 | 無 |
| 9 | Pipeline | ✅ Complete | 6 檔案 (VCF pipeline, VEP, CIViC, DGIdb, OpenCRAVAT) | 1 個 placeholder | ✅ 可直接複用 | OpenCRAVAT stub |
| 10 | Auth/ACL | ✅ Complete | 5 檔案 (RBAC + JWT + Case ACL) | 無 | ✅ 可直接複用 | 無 |
| 11 | Observability | 🟡 Partial | 2 檔案 (audit, health) | 無 | ⚠️ 基本架構可用 | 缺 metrics/monitoring/profiling/tracing |
| 12 | Clinical Graph/Outbox | ✅ Complete | 5 檔案 (client/id_factory/retry_policy/worker/schemas) | 無 | ✅ 可直接複用 | 無 |
| 13 | Reporting | ✅ Complete | 6 檔案 (builder/models/renderer/repository/templates/validator) | 無 | ✅ 可直接複用 | FHIR 匯出為簡化版 |
| 14 | VCF | ✅ Complete | 3 檔案 (parser/validator/models) | 無 | ✅ 可直接複用 | 無 |
| 15 | Workbench | ✅ Complete | 3 檔案 (service 28438 行, repository, models) | 無 | ✅ 可直接複用 | 無 |
| 16 | Clinical Graph (Go) | ✅ Complete | 13 Go packages, 35+ 測試檔案, 14 份文檔 | 無 | ✅ 可直接複用 | 無 |
| 17 | Frontend Pages | 🟡 Partial | 17 頁面 | 無 | ✅ 大部分可複用 | 部分頁面較簡略 (Tools, KnowledgeBase) |
| 18 | Frontend Components | ✅ Complete | 3 組 (StatusBanner, charts×3, tabs×6) | 無 | ✅ 可直接複用 | 無 |
| 19 | Frontend API Client | 🟡 Partial | 3 API 模組 | 無 | ⚠️ 可合用但需擴充 | 無統一封裝, 部分硬編碼 fetch |
| 20 | Frontend Tests | ✅ Complete | 14 測試檔案 | 無 | ✅ 可直接複用 | 無 |
| 21 | Migrations | ✅ Complete | 25 版本 (v001~v025) | 無 | ⚠️ SQLite 為主, PG 已加入 | 無 |
| 22 | CI/CD | 🟡 Partial | 2 workflows (Python CI + Vercel) | 無 | ⚠️ 缺 Go pipeline | 需加入 Go 編譯與測試 |
| 23 | Backend Tests | ✅ Complete | ~99 個 Python 測試檔案 | 無 | ✅ 可直接複用 | 無 |
| 24 | Documentation | ✅ Complete | 30+ 文件 (架構/開發/計畫/審查/安全) | 無 | ✅ 可直接複用 | 無 |
| 25 | Models/ML | 🟠 Stub | 1 JSON manifest | 無 | 🔴 幾乎無可用資產 | 需從零建置訓練/eval/deploy pipeline |
| 26 | FHIR | 🟠 Stub | 1 類 (FHIRExporter in renderer.py) | 無 | ⚠️ 簡化版, 需升級 | 需擴充至完整 FHIR R4 |
| 27 | HL7/DICOM/PACS | 🔴 Missing | 0 | — | 🔴 無 | 需從零建置 |
| 28 | RAG/Vector DB/Embedding | 🔴 Missing | 0 | — | 🔴 無 | 需從零建置 |
| 29 | Digital Thread | ✅ Complete | 1 檔案 (decision_thread.py) + API + Service | 無 | ✅ 可直接複用 | 無 |

---

## 詳細盤點

### 1. Domain Models — ✅ Complete

**狀態**：Complete — 25+ 模型類，覆蓋病患、病例、變異、藥物、證據、推薦、治療計畫、腫瘤委員會等核心領域。

**證據**：
- `src/backend/domain/__init__.py` — 公開匯出所有模型 (L1-120)
- `src/backend/domain/enums.py` — 395 行，定義 28 個 enum 類包括 SexEnum, CancerTypeEnum, VariantTypeEnum, EvidenceLevelEnum, Role, Permission 等
- `src/backend/domain/treatment_plan.py` — 6 個模型類 (L25-380)：TreatmentPlanModel, TreatmentPhaseModel, TreatmentItemModel, TreatmentMonitoringModel, TreatmentSafetyRuleModel, TreatmentPlanTraceModel
- `src/backend/domain/cancer_case.py` — CancerCaseModel + Create/Update/Response (L24-130)
- `src/backend/domain/patient.py` — PatientModel + CRUD schema (L31-110)
- `src/backend/domain/variant.py` — VariantModel + Import/Batch/Response (L32-170)
- 每個 domain 檔案均包含 SQLAlchemy ORM 模型 + Pydantic 請求/回應 schema

**技術債**：無 TODO/FIXME 標記。

**Phase 4 可複用性**：✅ 領域模型完整且穩定，可直接導入 Phase 4。

**Phase 5 前需重構**：無。

---

### 2. Services — ✅ Complete

**狀態**：Complete — 7 個 Service 類，涵蓋臨床決策、推薦、腫瘤委員會、治療計畫、臨床圖譜事件、證據攝入、變異攝入。

**證據**：
- `src/backend/services/__init__.py` (L1-27) — 匯出 ClinicalDecisionService, RecommendationService, TumorBoardConsensusService
- `src/backend/services/treatment_plan_service.py` — 58842 位元組，最複雜的 Service (L212: class TreatmentPlanService)
- `src/backend/services/clinical_decision_service.py` — 25548 位元組 (L128: class ClinicalDecisionService)
- `src/backend/services/tumor_board_service.py` — 34102 位元組 (L212: class TumorBoardConsensusService)
- `src/backend/services/recommendation_service.py` — 20499 位元組 (L63: class RecommendationService)
- `src/backend/services/clinical_graph_event_service.py` — 3046 位元組 (L17: class ClinicalGraphEventService)
- `src/backend/services/evidence_ingestion_service.py` — 3049 位元組 (L15: class EvidenceIngestionService)
- `src/backend/services/variant_ingestion_service.py` — 1111 位元組 (L16: class VariantIngestionService)

**技術債**：無 TODO/FIXME。

**Phase 4 可複用性**：✅ 商業邏輯完整，可直接複用。

**Phase 5 前需重構**：`treatment_plan_service.py` (58842 位元組) 過大，建議依職責拆分為多個子 Service。

---

### 3. Repositories — ✅ Complete

**狀態**：Complete — 23 個 Repository 類 + 泛用 BaseRepository。

**證據**：
- `src/backend/repositories/__init__.py` (L1-50) — 匯出所有 Repository 類
- `src/backend/repositories/base.py` — BaseRepository 提供通用 CRUD (L1-100)
- `src/backend/repositories/treatment_plan_repo.py` — 20756 位元組 (最複雜)
- `src/backend/repositories/clinical_decision_repo.py` — 9686 位元組
- `src/backend/repositories/tumor_board_repo.py` — 13050 位元組
- `src/backend/repositories/evidence_item_repo.py` — 8591 位元組
- `src/backend/repositories/recommendation_repo.py` — 8833 位元組

**技術債**：無。

**Phase 4 可複用性**：✅

---

### 4. API Routes — ✅ Complete

**狀態**：Complete — 23 個路由模組，100+ 端點 (RESTful CRUD + 工作流操作)。

**證據**：
- `src/backend/api/v1/router.py` (L1-51) — 聚合所有 v1 路由
- `src/backend/api/v1/workbench.py` — 27459 位元組 (最大路由模組)
- `src/backend/api/v1/upload_vcf.py` — 18405 位元組
- `src/backend/api/v1/clinical.py` — 18088 位元組
- `src/backend/api/v1/treatment_plans.py` — 14110 位元組 (含 submit/approve/activate/pause/complete/cancel/revise)
- `src/backend/api/v1/clinical_graph.py` — 13780 位元組
- 端點範例：`reports.py:L154` → `@router.get("/{report_id}/fhir")` 提供 FHIR 匯出端點

**技術債**：無。

**Phase 4 可複用性**：✅ 路由設計完整，可直接複用。

---

### 5. Engines — ✅ Complete

**狀態**：Complete — 5 個核心引擎模組，涵蓋推薦、臨床決策、藥物排序、推理與可解釋性。

**證據**：
- `src/backend/clinical/recommendation_engine.py` — 31224 位元組，規則驅動的推薦引擎 (L6-15: EvidenceAggregator → DrugRanker → RecommendationRule)
- `src/backend/clinical/clinical_decision_engine.py` — 15615 位元組 (L1-15: DecisionRuleSet 規則分類決策類型)
- `src/backend/ranking/engine.py` — 7774 位元組 (L1-6: DrugRankingEngine 整合 6 個 Scorer)
- `src/backend/reasoning/service.py` — 12649 位元組 (L28: ClinicalReasoningService)
- `src/backend/clinical/explainable_recommendation.py` — 23407 位元組 (L1-15: ExplainableEngine 產出 ReasonItem)

**技術債**：無。

**Phase 4 可複用性**：✅

---

### 6. Adapters — 🟡 Partial

**狀態**：Partial — 框架完整 (BaseAdapter + AdapterResult + Registry) 但 8/10 註冊項為 NotConfiguredAdapter stub。

**證據**：
- `src/backend/adapters/base.py` — 完整基底類 (L45-133: BaseAdapter ABC + NotConfiguredAdapter)
- `src/backend/adapters/registry.py` — 完整註冊表 (L10-69: AdapterRegistry + _register_defaults)
- **8 個 stub**：
  - `adapters/civic.py:L7` → `CIViCAdapter = NotConfiguredAdapter`
  - `adapters/dgidb.py:L4` → `DGIdbAdapter = NotConfiguredAdapter`
  - `adapters/drkg.py:L4` → `DRKGAdapter = NotConfiguredAdapter`
  - `adapters/ensembl_vep.py:L12` → `EnsemblVEPAdapter = NotConfiguredAdapter`
  - `adapters/myvariant.py:L4` → `MyVariantAdapter = NotConfiguredAdapter`
  - `adapters/oncotree.py:L4` → `OncoTreeAdapter = NotConfiguredAdapter`
  - `adapters/opencravat.py:L7` → `OpenCRAVATAdapter = NotConfiguredAdapter`
  - `adapters/pharmcat.py:L4` → `PharmCATAdapter = NotConfiguredAdapter`
- **2 個真實實作**：base.py (框架), registry.py (註冊)
- 注意：`pipeline/vep_adapter.py` (Ensembl REST API) 與 `pipeline/civic_adapter.py` (CIViC REST API) 與 `pipeline/dgidb_adapter.py` (DGIdb REST API) 有真實實作，但 registry 中 vep 註冊的是 pipeline 版，civic/dgidb 則註冊 adapters 中的 stub 版。

**技術債**：8 個 adapter 標記為 "placeholder for Phase 2 integration"。

**Phase 4 可複用性**：⚠️ 框架 (BaseAdapter/Registry) 可複用，但 8 個數據源連接需逐一實作。

**Phase 5 前需重構**：需完成 8 個 adapter 的真實實作 (CIViC, DGIdb, OncoTree, MyVariant, DRKG, PharmCAT, Ensembl VEP local, OpenCRAVAT)。

---

### 7. Knowledge Layer — ✅ Complete

**狀態**：Complete — 完整的知識整合層，包含模型/儲存庫/服務/識別器/外部 adapter。

**證據**：
- `src/backend/knowledge/__init__.py` (L1-44) — 匯出 KnowledgeEntity, KnowledgeRelation, Publication, ClinicalTrial, GuidelineItem, RegulatoryApproval 等
- `src/backend/knowledge/models.py` — 3895 位元組
- `src/backend/knowledge/repository.py` — 6100 位元組 (L1: KnowledgeEntityModel + KnowledgeRelationModel)
- `src/backend/knowledge/service.py` — 2221 位元組 (L1: KnowledgeService)
- `src/backend/knowledge/identifiers.py` — 7252 位元組 (IdentifierMapper, normalize_gene_symbol, normalize_hgvs)
- `src/backend/knowledge/adapters/` — 3 個外部知識源 adapter (clinicaltrials.py:3950B, clinvar.py:4907B, pubmed.py:4729B)

**技術債**：無。

**Phase 4 可複用性**：✅

---

### 8. Agents — ✅ Complete

**狀態**：Complete — 6 個臨床決策 Agent + Orchestrator + ConsensusEngine。

**證據**：
- `src/backend/agents/__init__.py` (L1-14) — 匯出 AgentOrchestrator, BaseAgent, AgentOpinion, ConsensusEngine
- `src/backend/agents/diagnosis_agent.py` — 23062 位元組 (L155: class DiagnosisAgent)
- `src/backend/agents/guideline_agent.py` — 19804 位元組 (L295: class GuidelineAgent)
- `src/backend/agents/clinical_trial_agent.py` — 18007 位元組 (L309: class ClinicalTrialAgent)
- `src/backend/agents/variant_agent.py` — 15716 位元組 (L35: class VariantAgent)
- `src/backend/agents/drug_agent.py` — 13600 位元組 (L46: class DrugAgent)
- `src/backend/agents/resistance_agent.py` — 7938 位元組 (L19: class ResistanceAgent)
- `src/backend/agents/orchestrator.py` — 6305 位元組 (L31: class AgentOrchestrator, 平行執行 6 Agent)
- `src/backend/agents/consensus.py` — 17511 位元組 (L469: class ConsensusEngine + L25: ConsensusResult)
- `src/backend/agents/base.py` — 3960 位元組 (L21: class BaseAgent ABC)
- `src/backend/agents/models.py` — 1825 位元組 (L14: AgentOpinion Pydantic model)

**技術債**：無。

**Phase 4 可複用性**：✅

---

### 9. Pipeline — ✅ Complete

**狀態**：Complete — VCF 變異分析 pipeline，含正規化、VEP 註釋、CIViC/DGIdb 證據查詢。

**證據**：
- `src/backend/pipeline/__init__.py` (L1-19) — 匯出 AnalysisJob, BcftoolsAdapter, VEPAdapter, OpenCRAVATAdapter
- `src/backend/pipeline/normalization.py` — 19933 位元組 (BcftoolsAdapter, normalize_minimal_representation)
- `src/backend/pipeline/analysis_job.py` — 12394 位元組 (AnalysisJob, create_and_run_job)
- `src/backend/pipeline/vep_adapter.py` — 11977 位元組 (Ensembl REST API 真實整合, L1-30)
- `src/backend/pipeline/civic_adapter.py` — 9096 位元組 (CIViC REST API 真實整合, L1-40)
- `src/backend/pipeline/dgidb_adapter.py` — 6699 位元組 (DGIdb REST API 真實整合, L31)
- `src/backend/pipeline/opencravat_adapter.py` — 2382 位元組 (骨架實作但回傳 unavailable)

**技術債**：`opencravat_adapter.py` 僅為骨架，需真實整合。

**Phase 4 可複用性**：✅

**Phase 5 前需重構**：OpenCRAVAT adapter 需完成真實實作。

---

### 10. Auth/ACL — ✅ Complete

**狀態**：Complete — RBAC (6 角色) + JWT Token 認證 + Case 層級 ACL。

**證據**：
- `src/backend/auth/__init__.py` (L1-30) — 匯出完整認證授權系統
- `src/backend/auth/models.py` — 2986 位元組 (Role, Permission, ROLE_PERMISSIONS 映射)
- `src/backend/auth/service.py` — 12675 位元組 (AuthService: JWT 登入/驗證/刷新)
- `src/backend/auth/api.py` — 4162 位元組 (認證端點)
- `src/backend/auth/dependencies.py` — 4400 位元組 (require_auth, require_permission, require_case_access)
- `src/backend/auth/case_acl_service.py` — 8168 位元組 (CaseACLService: CRUD + 權限檢查)
- `src/backend/domain/enums.py:L323-363` — Role 與 Permission enum 定義

**技術債**：無。

**Phase 4 可複用性**：✅

---

### 11. Observability — 🟡 Partial

**狀態**：Partial — 基本 Audit logging 與 Health check 已實作，缺少生產級監控 (metrics, tracing, profiling)。

**證據**：
- `src/backend/observability/__init__.py` (L1-11) — 匯出 AuditLogger, AuditLog, HealthChecker, HealthStatus
- `src/backend/observability/audit.py` — 3461 位元組 (L14-40: AuditLog 資料結構 + AuditLogger 類)
- `src/backend/observability/health.py` — 2877 位元組 (L13-31: HealthStatus + L34: HealthChecker 檢查 DB/Redis/adapters)

**缺失項目**：
- 無 metrics 收集 (Prometheus/OpenTelemetry)
- 無 distributed tracing
- 無 CPU/memory profiling
- 無 structured logging 框架整合

**Phase 4 可複用性**：⚠️ 基本架構可用，但需補上生產級監控。

**Phase 5 前需重構**：需導入 OpenTelemetry 或 Prometheus client，實作 metrics endpoint、tracing middleware、profiling handler。

---

### 12. Clinical Graph / Outbox — ✅ Complete

**狀態**：Complete — 完整的事務性發件箱模式 (Transactional Outbox)，含 CLI 客戶端、ID 工廠、重試策略、工作者。

**證據**：
- `src/backend/clinical_graph/client.py` — 3937 位元組 (L13: ClinicalGraphClient, subprocess 呼叫 knowgraph CLI)
- `src/backend/clinical_graph/id_factory.py` — 3168 位元組 (ID 生成)
- `src/backend/clinical_graph/retry_policy.py` — 1181 位元組 (重試策略)
- `src/backend/clinical_graph/worker.py` — 3795 位元組 (背景工作者)
- `src/backend/domain/clinical_graph_outbox.py` — 1705 位元組 (L11: ClinicalGraphOutboxModel)
- `src/backend/repositories/clinical_graph_outbox_repo.py` — 6535 位元組
- `src/backend/services/clinical_graph_event_service.py` — 3046 位元組
- `src/backend/api/v1/clinical_graph.py` — 13780 位元組 (狀態查詢、事件重試、Patient thread 查詢、Recommendation/Consensus explain)

**技術債**：無。

**Phase 4 可複用性**：✅ 可直接複用。

---

### 13. Reporting — ✅ Complete

**狀態**：Complete — 6 檔案，支援 HTML/JSON/PDF/FHIR 輸出。

**證據**：
- `src/backend/reporting/__init__.py` (L1-18) — 匯出所有報告元件
- `src/backend/reporting/renderer.py` — L11: ReportRenderer (HTML/JSON), L26: PDFRenderer (weasyprint/playwright), L74: FHIRExporter (簡化 FHIR R4 Bundle)
- `src/backend/reporting/builder.py` — 2375 位元組 (ReportBuilder)
- `src/backend/reporting/models.py` — 1481 位元組 (ClinicalReport)
- `src/backend/reporting/templates.py` — 4277 位元組 (ReportTemplateRegistry)
- `src/backend/reporting/repository.py` — 3084 位元組 (ClinicalReportModel, ReportRepository)
- `src/backend/reporting/validator.py` — 1079 位元組 (ReportValidator)

**技術債**：FHIRExporter 為簡化版 (FHIR R4 Bundle with Composition section)，非完整 FHIR Implementation Guide。

**Phase 4 可複用性**：✅

**Phase 5 前需重構**：FHIR 匯出需擴充至完整 R4 資源 (Patient, Observation, MedicationRequest, DiagnosticReport 等)。

---

### 14. VCF — ✅ Complete

**狀態**：Complete — VCF 解析器與驗證器。

**證據**：
- `src/backend/vcf/__init__.py` — L1: VCF module
- `src/backend/vcf/parser.py` — 7149 位元組 (VCF 解析)
- `src/backend/vcf/validator.py` — 13538 位元組 (VCF 格式驗證)
- `src/backend/vcf/models.py` — 685 位元組 (資料結構)

**技術債**：無。

**Phase 4 可複用性**：✅

---

### 15. Workbench — ✅ Complete

**狀態**：Complete — 醫生工作台後端，含服務 (28438 位元組)、儲存庫、模型。

**證據**：
- `src/backend/workbench/__init__.py` (L1-30) — 匯出 WorkbenchService, 圖譜/腫瘤委員會/筆記/時間線模型
- `src/backend/workbench/service.py` — 28438 位元組 (知識圖譜查詢、腫瘤委員會流程、活動紀錄)
- `src/backend/workbench/repository.py` — 3903 位元組
- `src/backend/workbench/models.py` — 4380 位元組

**技術債**：無。

**Phase 4 可複用性**：✅

---

### 16. KnowGraphGo (知識圖譜 Go) — ✅ Complete

**狀態**：Complete — 13 個 Go packages，35+ 測試檔案，14 份文檔。

**證據**：
- **Packages (13)**：
  - `KnowGraphGo/adapter/clinical/` — Clinical adapter + id_factory + ontology
  - `KnowGraphGo/cmd/knowgraph/` — CLI (14 個 .go 檔案, root/crud/query/infer/explain/export/ontology)
  - `KnowGraphGo/explain/` — 解釋引擎 (doc.go, explain.go, format.go, model.go)
  - `KnowGraphGo/export/` — 匯出 (CSV, JSON, Markdown)
  - `KnowGraphGo/graph/` — 核心圖資料結構 (entity, relation, store, query, evidence, provenance, integrity)
  - `KnowGraphGo/inference/` — 推理引擎 (forward/backward chain, rule, relations)
  - `KnowGraphGo/ontology/` — 本體論 (schema, constraint, inheritance, validator, types)
  - `KnowGraphGo/pattern/` — 模式匹配 (matcher, path_pattern, pattern)
  - `KnowGraphGo/service/` — 知識服務層 (knowledge, mutation, query)
  - `KnowGraphGo/store/memory/` — 記憶體儲存
  - `KnowGraphGo/store/sqlite/` — SQLite 儲存 (含 FTS5 全文搜索)
  - `KnowGraphGo/graph/storetest/` — Store contract tests
  - `KnowGraphGo/traversal/` — 圖遍歷 (BFS, DFS, K-Hop, Cycle, Topo, Path)
- **測試檔案**: 35 個 `*_test.go` 檔案
- **文檔**: 14 份 Markdown 文檔 (architecture, data-model, graph-store, inference, ontology, pattern-matching, query, traversal, explain 等)

**技術債**：無。

**Phase 4 可複用性**：✅ 可直接複用。

---

### 17. Frontend Pages — 🟡 Partial

**狀態**：Partial — 17 頁面，部分頁面較簡略 (Tools.tsx 2130B, KnowledgeBase.tsx 2002B)。

**證據**：
- `src/frontend/src/pages/` 目錄包含 17 頁面 + 1 子目錄：
  - `Workbench.tsx` — 44713 位元組 (最完整)
  - `TreatmentPlanDetailPage.tsx` — 34439 位元組
  - `TumorBoardConsensusPage.tsx` — 21354 位元組
  - `ClinicalDecisionPage.tsx` — 20192 位元組
  - `RecommendationPage.tsx` — 19453 位元組
  - `TreatmentPlanCreatePage.tsx` — 14179 位元組
  - `ResearchPortal.tsx` — 14061 位元組
  - `TreatmentPlanRevisionPage.tsx` — 13447 位元組
  - `TreatmentPlanListPage.tsx` — 12174 位元組
  - `TumorBoardConsensusListPage.tsx` — 12049 位元組
  - `ClinicalDecisionListPage.tsx` — 6125 位元組
  - `Dashboard.tsx` — 4945 位元組
  - `Home.tsx` — 3725 位元組
  - `ClinicalGraphPage.tsx` — 3360 位元組
  - `Research.tsx` — 2447 位元組
  - `Tools.tsx` — 2130 位元組
  - `KnowledgeBase.tsx` — 2002 位元組
  - `workbench/` — 子目錄

**技術債**：Tools.tsx、KnowledgeBase.tsx、Research.tsx 較簡略，功能有限。

**Phase 4 可複用性**：✅ 大部分頁面可複用，簡略頁面需擴充。

---

### 18. Frontend Components — ✅ Complete

**狀態**：Complete — 3 組 UI 元件。

**證據**：
- `src/frontend/src/components/StatusBanner.tsx` — 1584 位元組
- `src/frontend/src/components/charts/` — 3 檔案：CancerStats.tsx (3696B), PredictionResults.tsx (4149B), ResearchTrends.tsx (4074B)
- `src/frontend/src/components/tabs/` — 6 檔案：AgentsTab.tsx (8099B), ConsensusTab.tsx (8194B), ContextTab.tsx (10108B), DecisionThreadTab.tsx (8546B), EvidenceTab.tsx (13358B), RecommendationTab.tsx (12593B)

**技術債**：無。

**Phase 4 可複用性**：✅

---

### 19. Frontend API Client — 🟡 Partial

**狀態**：Partial — 3 個 API 模組 (clinical_decision.ts, treatmentPlan.ts, workbench.ts)，但 workbench.ts 極其全面涵蓋臨床情境/證據/Agent/共識/推薦/決策線程等 API。

**證據**：
- `src/frontend/src/api/clinical_decision.ts` — 3 個 API 函數 (fetchClinicalDecisionById, createClinicalDecision, fetchClinicalDecisionsByPatientId)
- `src/frontend/src/api/treatmentPlan.ts` — 13 個 API 函數 (create/get/list/versions/trace/submit/approve/activate/pause/complete/cancel/revise)
- `src/frontend/src/api/workbench.ts` — 30+ API 函數，涵蓋：
  - 知識圖譜查詢 (L139-145)
  - 病患摘要/時間線/活動紀錄 (L147-165)
  - 治療推薦 (L159-165)
  - 腫瘤委員會審查/投票/評論 (L167-183)
  - 案例比較 (L185-187)
  - 腫瘤委員會共識 CRUD (L228-247)
  - 臨床圖譜查詢 (L251-279)
  - 筆記 CRUD (L281-312)
  - 推理對話 (L315-348)
  - 附件查詢 (L351-366)
  - 變異查詢 (L370-390)
  - 臨床情境/證據/Agent/共識/推薦 (L476-511)

**缺失**：無統一 axios/fetch 封裝 (每個檔案重複寫 request helper)，無 interceptors，無 TypeScript 生成。

**Phase 4 可複用性**：⚠️ 可合用但需統一封裝。

**Phase 5 前需重構**：建議建立統一 API client (axios instance + interceptors + 型別生成)。

---

### 20. Frontend Tests — ✅ Complete

**狀態**：Complete — 14 測試檔案，使用 Vitest + React Testing Library。

**證據**：
- `src/frontend/src/test/App.test.tsx`
- `src/frontend/src/test/ClinicalDecisionListPage.test.tsx`
- `src/frontend/src/test/ClinicalDecisionPage.test.tsx`
- `src/frontend/src/test/RecommendationPage.test.tsx`
- `src/frontend/src/test/TreatmentPlanPages.test.tsx`
- `src/frontend/src/test/TumorBoardConsensusListPage.test.tsx`
- `src/frontend/src/test/TumorBoardConsensusPage.test.tsx`
- `src/frontend/src/test/Workbench.test.tsx`
- `src/frontend/src/test/setup.ts`
- `src/frontend/src/test/tabs/AgentsTab.test.tsx`
- `src/frontend/src/test/tabs/ConsensusTab.test.tsx`
- `src/frontend/src/test/tabs/ContextTab.test.tsx`
- `src/frontend/src/test/tabs/DecisionThreadTab.test.tsx`
- `src/frontend/src/test/tabs/EvidenceTab.test.tsx`
- `src/frontend/src/test/tabs/RecommendationTab.test.tsx`

**技術債**：無。

**Phase 4 可複用性**：✅

---

### 21. Migrations — ✅ Complete

**狀態**：Complete — 25 個 Alembic 遷移版本 (v001~v025)，從初始結構到治療計畫版本複合唯一約束。

**證據**：
- `migrations/versions/001_initial_precision_oncology_foundation.py` — 27545 位元組 (基礎表結構)
- `migrations/versions/016_phase2_clinical_workspace.py` — 5150 位元組 (決策節點表)
- `migrations/versions/023_phase3e_treatment_plan_tables.py` — 11579 位元組 (治療計畫表)
- `migrations/versions/025_phase3e_version_composite_unique.py` — 12128 位元組 (最新版本)
- 支援 PostgreSQL (integration/test_migration_025_pg_full_cycle.py, test_migration_025_pg_schema_compare.py)

**技術債**：主要測試與開發使用 SQLite，PostgreSQL 支援已加入但僅限整合測試。

**Phase 4 可複用性**：⚠️ 可複用，PG 遷移需更多測試。

---

### 22. CI/CD — 🟡 Partial

**狀態**：Partial — Python 後端 CI (pytest + ruff + mypy) 與 Vercel 前端部署已完整，但缺少 Go pipeline (KnowGraphGo)。

**證據**：
- `.github/workflows/ci.yml` — Python CI (pytest + ruff + mypy, PostgreSQL service container)
- `.github/workflows/deploy.yml` — Vercel 前端部署 (only on CI success)

**缺失**：
- 無 KnowGraphGo 的 Go 編譯與測試 workflow
- 無 Docker build/push
- 無後端部署 pipeline

**Phase 4 可複用性**：⚠️ 需補上 Go pipeline。

**Phase 5 前需重構**：需新增 Go pipeline workflow (go build, go test, golangci-lint)。

---

### 23. Backend Tests — ✅ Complete

**狀態**：Complete — ~99 個 Python 測試檔案，涵蓋單元測試、整合測試、端到端測試。

**證據**：
- `tests/backend/` — 13 個測試檔案 (treatment_plan 系列)
- `tests/integration/` — 14 個測試檔案 (phase2/phase3 工作流、授權、遷移、報告)
- `tests/unit/` — 12 個測試檔案 (agents, consensus, decision_thread, evidence, outbox, workbench)
- `tests/test_*.py` — 50+ 頂層測試檔案 (API, 模型, 儲存庫, 引擎, 服務, VCF, adapter)
- 關鍵測試：test_recommendation_engine.py (47376B), test_clinical_decision_service.py (35703B), test_tumor_board_service.py (34363B)

**技術債**：無。

**Phase 4 可複用性**：✅

---

### 24. Documentation — ✅ Complete

**狀態**：Complete — 30+ 文檔涵蓋架構、開發、發布計畫、安全審查、API 合約。

**證據**：
- `docs/` — API_CONTRACT.md, DATABASE_SCHEMA.md, CURRENT_STATE.md, MEDICAL_SAFETY.md, MODEL_CARD.md, PHASE1_* 系列
- `docs/plans/` — 版本計畫 (0.4.1 ~ 1.0.0)
- `docs/reports/` — 驗證報告
- `docs/reviews/` — 程式審查報告
- `docs/audits/` — 安全審計
- `docs/api.md`, `docs/guide.md`, `docs/development.md`, `docs/models.md`

**技術債**：部分計畫文件可能已過時。

**Phase 4 可複用性**：✅

---

### 25. Models/ML — 🟠 Stub

**狀態**：Stub — 僅包含一個 JSON manifest 檔案，無訓練/評估/部署 pipeline。

**證據**：
- `models/manifests/cancer_classifier_v1.json` — 2042 位元組 (模型描述檔)
- `models/.gitkeep` — 空佔位

**缺失**：
- 無模型訓練程式碼
- 無模型評估 pipeline
- 無模型部署服務
- 無特徵工程
- 無 MLflow/Kubeflow 追蹤

**Phase 4 可複用性**：🔴 幾乎無可用資產，需從零建置。

**Phase 5 前需重構**：需完整的 ML pipeline (train/eval/deploy/monitor)。

---

### 26. FHIR — 🟠 Stub

**狀態**：Stub — 僅 `reporting/renderer.py` 中的 FHIRExporter 類，產出簡化 FHIR R4 Bundle。

**證據**：
- `src/backend/reporting/renderer.py:L74-135` — FHIRExporter.export() 產出簡化 Bundle + Composition + Section
- `src/backend/api/v1/reports.py:L154` — `@router.get("/{report_id}/fhir")` FHIR 匯出端點

**缺失**：
- 無完整 FHIR R4 資源模型 (Patient, Observation, MedicationRequest, DiagnosticReport 等)
- 無 FHIR 驗證 (无 fhirpath/fhir-validator)
- 無 FHIR Server 整合
- 無 SMART-on-FHIR 授權

**Phase 4 可複用性**：⚠️ 簡化版可作起點，但需大幅擴充。

**Phase 5 前需重構**：需導入 FHIR R4 完整資源模型，支援 FHIR API 標準。

---

### 27. HL7/DICOM/PACS — 🔴 Missing

**狀態**：Missing — 完全無實作。

**證據**：全域 grep "HL7\|hl7\|DICOM\|dicom\|PACS\|pacs" 無 production code 匹配。

**Phase 4 可複用性**：🔴 無。

**Phase 5 前需重構**：需從零建置 HL7 v2 訊息解析、DICOM 影像管理、PACS 查詢/擷取。

---

### 28. RAG/Vector DB/Embedding — 🔴 Missing

**狀態**：Missing — 完全無實作。

**證據**：全域 grep "vector\|embedding\|rag\|RAG\|chroma\|pinecone\|weaviate\|qdrant\|langchain" 無生產程式碼匹配。

**Phase 4 可複用性**：🔴 無。

**Phase 5 前需重構**：需導入 Vector DB (如 Chroma/Pinecone/Qdrant)、Embedding pipeline、RAG 檢索架構。

---

### 29. Digital Thread — ✅ Complete

**狀態**：Complete — DecisionNode 模型 + Repository + Service + API + 前端支援。

**證據**：
- `src/backend/clinical/decision_thread.py` — 16798 位元組
  - L28: NodeType Literal (context_built, evidence_collected, agent_opinion, consensus_reached, recommendation_generated)
  - L39: DecisionNodeModel (SQLAlchemy ORM)
- `src/backend/api/v1/clinical.py` — L425-501: 決策線程端點 (GET /thread/{case_id}, /thread/{case_id}/tree, /thread/node/{node_id})
- `src/backend/api/v1/clinical_decision.py` — 4724 位元組 (ClinicalDecisionResponse.trace_id)
- 前端支援：`src/frontend/src/components/tabs/DecisionThreadTab.tsx` (8546B)

**技術債**：無。

**Phase 4 可複用性**：✅ 可直接複用。

---

### 30. Background Jobs/Queue — 🔴 Missing

**狀態**：Missing — 目前無通用背景任務佇列實作。

**證據**：
- `src/backend/clinical_graph/worker.py` — 僅 outbox 專用 worker，非通用 job queue
- 全域 grep "arq\|celery\|rq\|dramatiq\|huey\|job.*queue\|task.*queue" — 無匹配
- 全域 grep "redis" — 僅在 test fixture 中使用，無生產 Redis 連線

**技術債**：Outbox worker 為單一用途 (98 行)，無法處理非 KG 投影的任務。

**Phase 4 可複用性**：🟡 Phase 4 B4 將引入 ARQ + Redis。

---

### 31. Deployment — 🔴 Missing

**狀態**：Missing — 目前無容器化部署方案。

**證據**：
- 搜尋 Dockerfile / docker-compose / Docker — 無匹配
- `.github/workflows/deploy.yml` — 僅 Vercel 前端部署
- `src/backend/` — 無 gunicorn/uvicorn 啟動腳本或容器設定

**技術債**：目前僅能透過 `uvicorn src.backend.main:app` 直接執行，無 container image、無 orchestration、無 health check endpoint。

**Phase 4 可複用性**：🟡 Phase 4 B5 將引入 Docker + CI/CD 基礎設施。

---

## 總結

### 強項
- **Domain Model 完整性**：25+ 領域模型覆蓋精準腫瘤學全部核心實體
- **API 覆蓋率**：23 路由模組、100+ REST 端點，包含完整 CRUD + 工作流操作
- **引擎品質**：5 個規則驅動引擎完全可追溯、無硬編碼
- **測試覆蓋**：~99 後端測試 + 35 Go 測試 + 14 前端測試
- **KnowGraphGo**：13 packages 的高品質 Go 知識圖譜實作

### 缺口 (Phase 5 前必填)
| 優先級 | 缺口 | 影響 |
|--------|------|------|
| 🔴 P0 | ML/Model Pipeline | 無模型訓練/評估/部署，無法實現 AI 核心功能 |
| 🔴 P0 | RAG/Vector DB/Embedding | 無法實現語義搜尋與知識增強生成 |
| 🟠 P1 | HL7/DICOM/PACS 整合 | 無法與醫院資訊系統互通 |
| 🟠 P1 | FHIR 完整實作 | 目前僅簡化版，無法符合醫療互操作性標準 |
| 🟡 P2 | Observability 強化 | 缺 metrics/tracing，無法生產監控 |
| 🟡 P2 | Adapters 實作 | 8/10 adapter 為 stub，需逐一連接真實數據源 |
| 🟡 P2 | CI/CD 補全 | 缺 Go pipeline |
