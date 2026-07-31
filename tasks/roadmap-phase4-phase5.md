# Phase 4 & Phase 5 Development Roadmap

> **產出時間**：2026-08-01  
> **基於文件**：`tasks/plan-phase4-clinical-ai-productization.md`、`tasks/plan-phase5-medical-ai-platform.md`、`tasks/phase4-phase5-dependency-map.md`  
> **負責角色**：doc-writer  

---

## 路線圖結構說明

- 每個 Batch 為一個可獨立交付的功能增量
- Batch 之間以 Gate 銜接，Gate 為明確的檢查點
- **ChatGPT Review Gate**：由 ChatGPT（AI 審查）檢查程式碼品質、架構合規、測試覆蓋
- **Merge Gate**：合併到 master 分支前的所有檢查（CI 通過、程式碼審查、安全掃描）
- 不虛構月份工期，以 Batch 和 Gate 為節奏單位

---

# Phase 4：Clinical AI Productization

Phase 4 從「已開發完成的 AI 原型」升級為「可在臨床環境中產品化運作的 AI 系統」。
採用 **3 個 Vertical Slice Batch** 結構，每個 Batch 為一條跨技術棧的端到端垂直功能切片，預估 4-6 週完成。

---

## Batch 1：病患資料整合與臨床工作流

### 目標
建立從病患資料匯入、證據檢索、AI 推薦、治療計畫制定到 FHIR 輸出與審計的完整垂直工作流，涵蓋前端操作介面。此 Batch 涵蓋 **Patient Import → Evidence → Recommendation → Treatment Plan → FHIR Export → Audit → Frontend** 完整鏈路。

### 前置依賴
- **外部依賴**：FHIR R4 規範（Patient/Observation/DiagnosticReport/CarePlan/MedicationRequest/Condition/Procedure）
- **外部依賴**：SMART-on-FHIR Standalone Launch flow 規格
- **外部依賴**：CIViC / DGIdb / OncoTree 等外部證據 API
- **既有依賴**：既有 Domain Model（PatientModel、CancerCaseModel、TreatmentPlanModel）作為映射來源
- **既有依賴**：既有 JWT/RBAC 框架
- **技術依賴**：Redis 服務（Background Job Queue 與快取）

### 交付內容
**檔案範圍（28-35 files）**：
| 區域 | 檔案 | 類型 |
|------|------|------|
| Patient Import | `src/backend/pipeline/patient_import.py`（病患資料匯入流程） | 新建 |
| Evidence 檢索 | `src/backend/pipeline/evidence_retrieval.py`（證據檢索整合） | 新建 |
| Recommendation | `src/backend/recommendation/service.py`（AI 推薦服務） | 修改 |
| Treatment Plan | `src/backend/clinical/workflows/treatment_plan.py`（治療計畫工作流） | 新建/修改 |
| FHIR Export | `src/backend/fhir/export.py`（治療計畫 FHIR 匯出） | 新建 |
| Audit Logger | `src/backend/observability/audit_logger.py`（審計日誌記錄） | 新建/修改 |
| FHIR 資源模型 | `src/backend/fhir/models/patient.py`、`observation.py`、`medication_request.py`、`diagnostic_report.py`、`condition.py`、`procedure.py`、`care_plan.py`、`__init__.py` | 新建 |
| FHIR 核心 | `src/backend/fhir/__init__.py`、`fhir/constants.py`、`fhir/validators.py`、`fhir/converters.py` | 新建 |
| FHIR API | `src/backend/api/v1/fhir.py`（路由模組） | 新建 |
| CapabilityStatement | `src/backend/fhir/capability.py` | 新建 |
| SMART-on-FHIR | `src/backend/auth/smart_on_fhir.py` | 新建 |
| Adapter 層 | `src/backend/adapters/registry.py`、`cache.py`、`health.py` | 新建 |
| External Adapters | `src/backend/pipeline/civic_adapter.py`、`dgidb_adapter.py`、`oncotree_adapter.py`、`myvariant_adapter.py`、`drkg_adapter.py`、`pharmcat_adapter.py`、`vep_adapter.py`、`opencravat_adapter.py` | 新建/修改 |
| Secrets 管理 | `src/backend/infrastructure/secrets.py`（API key 管理） | 新建 |
| Migration | `migrations/versions/026_fhir_resource_tables.py` | 新建 |
| 前端 - 病患檢視 | `frontend/src/pages/PatientDetail.tsx`、`frontend/src/components/EvidencePanel.tsx` | 新建/修改 |
| 前端 - 治療計畫 | `frontend/src/pages/TreatmentPlan.tsx`、`frontend/src/components/RecommendationView.tsx` | 新建/修改 |
| 前端 - 審計日誌 | `frontend/src/pages/AuditLog.tsx` | 新建 |
| 測試 | `tests/unit/fhir/test_*.py`、`tests/integration/fhir/test_api.py`、`tests/e2e/test_patient_workflow.py` | 新建 |
| 文件 | `docs/fhir/integration_guide.md`、`docs/workflows/patient_import.md` | 新建 |

### 驗收標準
- [ ] 病患資料可透過匯入流程（CSV / HL7 / FHIR）完整匯入系統
- [ ] Evidence 檢索可查詢外部來源（CIViC / DGIdb / OncoTree）並回傳結構化結果
- [ ] AI 推薦引擎可依據病患資料與證據生成治療建議
- [ ] Treatment Plan 可被建立、更新、版本管理
- [ ] FHIR Export 可將治療計畫匯出為 FHIR R4 CarePlan Resource
- [ ] Audit 日誌記錄所有關鍵操作（資料匯入、推薦生成、治療計畫修改）
- [ ] 前端頁面可展示病患詳細資料、證據面板與治療計畫
- [ ] 所有 FHIR 單元測試通過（mock 資料）
- [ ] 所有既有測試不受影響（regression pass）

### ChatGPT Review Gate
1. **垂直切片完整性**：檢查從資料匯入到前端展示的完整鏈路是否通暢
2. **FHIR 映射正確性**：檢查內部 Domain Model → FHIR Resource 的映射是否涵蓋所有必要欄位
3. **SMART-on-FHIR 實作合規**：檢查授權流程是否符合 SMART App Launch IG
4. **Adapter 介面合規**：檢查 adapter 是否遵循 `adapters/base.py` 的抽象介面（query、parse、transform）
5. **錯誤處理**：檢查各環節的錯誤處理與降級策略（API timeout、rate limit 等）
6. **測試覆蓋率**：檢查垂直工作流的 E2E 測試涵蓋所有主要路徑

### Merge Gate
1. Go/GitHub Actions CI pipeline 全部通過
2. Python CI（unit test + lint）全部通過
3. 所有 FHIR 格式化檢查通過（`fhir_validator` 無 error）
4. 所有 adapter unit test 使用 mock，不因外部 API 狀態而失敗
5. 前端 build 與 lint 通過
6. 所有既有 regression test 通過
7. 程式碼審查至少 1 人 approve
8. 無 blocking 級 SAST 安全掃描發現
9. PR 描述包含 Batch 變更摘要

### 下一批解鎖條件
B1 合併至 master 後，B2 可基於 B1 的證據檢索與推薦基礎設施建構臨床試驗匹配。B3 需要 B1 的治療計畫模型作為藥物安全檢查的輸入。

---

## Batch 2：臨床試驗與證據排序

### 目標
實現臨床試驗匹配、證據排序、基於排序結果的推薦更新與 CarePlan 管理，並提供前端試算表操作介面。此 Batch 涵蓋 **Clinical Trial → Evidence Ranking → Recommendation → Treatment Update → CarePlan → Frontend** 完整鏈路。

### 前置依賴
- **B1（病患資料整合與臨床工作流）**：需要 B1 的 Patient Import、Evidence Retrieval 與 Treatment Plan 基礎設施
- **外部依賴**：ClinicalTrials.gov API 或其他臨床試驗資料來源
- **外部依賴**：既有 CIViC / DGIdb 等證據來源（B1 已建立 adapter）
- **既有依賴**：既有 Recommendation Service（擴充排序邏輯）

### 交付內容
**檔案範圍（22-28 files）**：
| 區域 | 檔案 | 類型 |
|------|------|------|
| Clinical Trial Matching | `src/backend/pipeline/clinical_trial_matching.py`（臨床試驗匹配引擎） | 新建 |
| Clinical Trial Adapter | `src/backend/pipeline/clinicaltrials_adapter.py`（ClinicalTrials.gov API） | 新建 |
| Evidence Ranking | `src/backend/ranking/evidence_ranker.py`（證據排序服務） | 新建 |
| Ranking API | `src/backend/api/v1/ranking.py`（排序結果 API） | 新建 |
| Recommendation Update | `src/backend/recommendation/updater.py`（基於排序更新推薦） | 新建 |
| CarePlan 管理 | `src/backend/clinical/workflows/careplan.py`（CarePlan 建立/更新/版本） | 新建 |
| CarePlan API | `src/backend/api/v1/careplans.py` | 新建 |
| 前端 - 臨床試驗比對 | `frontend/src/pages/TrialMatching.tsx`、`frontend/src/components/TrialList.tsx` | 新建 |
| 前端 - 證據排序 | `frontend/src/components/EvidenceRankingPanel.tsx` | 新建 |
| 前端 - CarePlan | `frontend/src/components/CarePlanView.tsx`、`frontend/src/pages/CarePlan.tsx` | 新建 |
| Migration | `migrations/versions/027_careplan_tables.py`（CarePlan 相關表） | 新建 |
| 測試 | `tests/unit/ranking/test_ranking.py`、`tests/integration/test_trial_matching.py`、`tests/e2e/test_trial_workflow.py` | 新建 |
| 文件 | `docs/trials/matching.md`、`docs/ranking/evidence_ranking.md` | 新建 |

### 驗收標準
- [ ] 臨床試驗匹配可根據病患條件（癌症類型、基因突變、分期）回傳匹配的試驗列表
- [ ] Evidence Ranking 可對多個證據來源進行排序（依 relevance / level of evidence）
- [ ] 排序結果可影響 Recommendation Service 的推薦輸出
- [ ] CarePlan 可被建立、更新、版本管理，並關聯至 Treatment Plan
- [ ] 前端 Trial Matching 頁面可展示匹配結果與詳細資訊
- [ ] 前端 CarePlan 管理頁面可檢視/編輯 CarePlan
- [ ] 所有測試通過（含 E2E）
- [ ] 既有 regression test 通過

### ChatGPT Review Gate
1. **臨床試驗匹配正確性**：檢查匹配邏輯是否正確解讀病患條件與試驗 eligibility criteria
2. **證據排序合理性**：檢查排序演算法（level of evidence、publication date、relevance score）是否合理
3. **Recommendation 更新流程**：檢查排序結果如何影響推薦輸出（override / append / adjust）
4. **CarePlan 資料模型**：檢查 CarePlan 是否涵蓋必要臨床欄位（interventions、goals、period）
5. **前端整合**：檢查前端是否正確顯示排序結果與 trial 詳細資訊
6. **錯誤處理**：檢查 ClinicalTrials.gov API 不可用時的降級策略

### Merge Gate
1. Python CI（unit test + lint）全部通過
2. 臨床試驗匹配 unit test 使用 mock 資料
3. 既有 regression test 全部通過
4. 前端 build 與 lint 通過
5. 程式碼審查至少 1 人 approve
6. 無 blocking 級安全掃描發現
7. PR 包含臨床試驗匹配的設定說明

### 下一批解鎖條件
B2 合併至 master 後，B3 可基於 B1 / B2 的治療計畫與 CarePlan 基礎進行藥物安全檢查。

---

## Batch 3：藥物安全與監控

### 目標
實現藥物安全性檢查（交互作用、禁忌症）、治療方案修訂建議、用藥監控與警報，並整合 RAG 語義檢索、基礎設施可觀測性、容器化部署與前端儀表板。此 Batch 涵蓋 **Drug Safety → Interaction → Contraindication → Treatment Revision → Monitoring → FHIR Export → Audit** 完整鏈路，並補齊 Phase 4 的基礎設施（RAG、Jobs、Observability、Docker、CI/CD）與前端統一入口。

### 前置依賴
- **B1（病患資料整合與臨床工作流）**：需要 B1 的 Patient Import、Treatment Plan、FHIR Export 基礎
- **B2（臨床試驗與證據排序）**：需要 B2 的 CarePlan 管理與 Recommendation 更新機制
- **外部依賴**：DrugBank / Drug Interaction API（或本地知識庫）
- **外部依賴**：RxNorm（藥物標準化編碼）
- **外部依賴**：Vector DB 服務（Chroma / Qdrant / Pinecone 擇一）
- **外部依賴**：Embedding 模型 API key 或本地部署（OpenAI / BGE 擇一）
- **外部依賴**：Prometheus、Grafana、Redis 服務
- **技術依賴**：Docker、Docker Compose

### 交付內容
**檔案範圍（38-48 files）**：
| 區域 | 檔案 | 類型 |
|------|------|------|
| Drug Safety Engine | `src/backend/safety/drug_safety_engine.py`（藥物安全檢查核心） | 新建 |
| Interaction Check | `src/backend/safety/interaction_checker.py`（藥物交互作用檢查） | 新建 |
| Contraindication | `src/backend/safety/contraindication_checker.py`（禁忌症檢查） | 新建 |
| Treatment Revision | `src/backend/safety/treatment_revision.py`（治療方案修訂建議） | 新建 |
| Monitoring Service | `src/backend/safety/monitoring.py`（用藥監控與警報服務） | 新建 |
| Safety API | `src/backend/api/v1/safety.py`（安全檢查端點） | 新建 |
| Monitoring API | `src/backend/api/v1/monitoring.py`（監控警報端點） | 新建 |
| RAG - Vector DB | `src/backend/rag/vector_store.py`、`embedding.py` | 新建 |
| RAG - 檢索服務 | `src/backend/rag/retriever.py`、`service.py` | 新建 |
| RAG - API | `src/backend/api/v1/rag.py` | 新建 |
| RAG - Clinical Context | `src/backend/rag/clinical_context.py` | 新建 |
| ReasonService 整合 | `src/backend/reasoning/service.py`（整合 RAG 安全文獻） | 修改 |
| Background Jobs | `src/backend/jobs/queue.py`、`scheduler.py`、`worker.py`、`retry_policy.py` | 新建 |
| Job API | `src/backend/api/v1/jobs.py` | 新建 |
| Observability | `src/backend/observability/metrics.py`、`tracing.py`、`logging.py`、`alerts.py`、`profiling.py` | 新建 |
| Health API 擴充 | `src/backend/api/v1/health.py`、`src/backend/observability/health.py` | 修改 |
| Prometheus / Grafana | `deploy/observability/prometheus.yml`、`grafana_dashboard.json`、`otel-collector.yml` | 新建 |
| Docker Compose - Obs | `docker-compose.observability.yml`、`docker-compose.redis.yml` | 新建 |
| FHIR Export（藥物） | `src/backend/fhir/export_medication.py`（藥物 FHIR 匯出） | 新建 |
| Audit 強化 | `src/backend/observability/audit_extension.py`（藥物操作審計） | 新建 |
| Docker - App | `Dockerfile`（多階段建置） | 新建 |
| Docker Compose - App | `docker-compose.yml`（完整堆疊）、`docker-compose.override.yml` | 新建 |
| K8s Config | `deploy/k8s/deployment.yml`、`service.yml`、`configmap.yml`、`secret.yml` | 新建 |
| CI/CD Pipelines | `.github/workflows/ci.yml`、`docker-publish.yml`、`security-scan.yml` | 新建 |
| Makefile | `Makefile`（常用開發指令） | 新建 |
| 前端 - 安全儀表板 | `frontend/src/pages/SafetyDashboard.tsx`、`frontend/src/components/AlertPanel.tsx` | 新建 |
| 前端 - 藥物交互 | `frontend/src/components/DrugInteractionView.tsx` | 新建 |
| 前端 - 監控中心 | `frontend/src/pages/MonitoringCenter.tsx` | 新建 |
| 前端 - 統一入口 | `frontend/src/App.tsx`（路由整合）、`frontend/src/components/NavBar.tsx` | 修改 |
| 前端 - 共用元件 | `frontend/src/components/common/Table.tsx`、`Chart.tsx`、`Card.tsx`、`Modal.tsx` | 新建 |
| 前端 - 報表中心 | `frontend/src/pages/Reports.tsx` | 新建 |
| Migration | `migrations/versions/028_safety_tables.py`、`029_vector_store_init.py` | 新建 |
| 測試 | `tests/unit/safety/test_*.py`、`tests/integration/safety/test_interaction.py`、`tests/e2e/test_safety_workflow.py`、`tests/unit/rag/test_*.py`、`tests/unit/observability/test_*.py`、`tests/unit/jobs/test_queue.py`、`tests/integration/docker/test_docker_compose.py` | 新建 |
| 文件 | `docs/safety/drug_safety.md`、`docs/rag/architecture.md`、`docs/deployment/docker_guide.md`、`docs/deployment/k8s_guide.md`、`docs/observability/monitoring.md` | 新建 |

### 驗收標準
- [ ] Drug Safety Engine 可檢查藥物交互作用（drug-drug interaction）
- [ ] Contraindication Checker 可根據病患狀況（過敏、肝腎功能、懷孕等）檢查禁忌症
- [ ] Treatment Revision 可根據安全檢查結果提出治療方案修訂建議
- [ ] Monitoring Service 可設定監控規則並在異常發生時觸發警報
- [ ] RAG / Vector DB 可對藥物安全文獻進行語義搜尋，ReasonService 整合檢索結果
- [ ] Background Job Queue 可正確 enqueue / dequeue 任務，worker 可正常消費
- [ ] Metrics 端點（`/metrics`）暴露 Prometheus 格式指標；分散式追蹤與 JSON Logging 正常運作
- [ ] FHIR Export 可將藥物處方匯出為 MedicationRequest Resource
- [ ] 前端 Safety Dashboard 展示即時警報與安全檢查結果
- [ ] 前端統一入口（NavBar、路由）整合所有 Phase 4 功能
- [ ] Docker Compose 可一鍵啟動完整堆疊（app + redis + vector db + observability）
- [ ] CI/CD Pipeline 包含 lint → unit test → build → security scan
- [ ] 所有測試通過（含 E2E 與 Docker integration test）
- [ ] 所有既有測試不受影響（regression pass）

### ChatGPT Review Gate
1. **藥物安全邏輯正確性**：檢查 interaction 與 contraindication 的規則引擎是否基於已知藥物知識庫
2. **RAG 安全檢索**：檢查 RAG pipeline 是否可正確檢索藥物安全相關文獻，embedding 模型選擇合理性
3. **Infrastructure 穩定性**：檢查 Job Queue 的 retry/dead-letter 機制、metrics 與 tracing 的完整性
4. **容器化完整性**：檢查 Docker Compose 是否涵蓋所有服務（app、redis、vector db、prometheus、grafana）
5. **前端可用性**：檢查安全儀表板是否直觀呈現警報資訊、交互作用圖表；共用元件設計是否通用
6. **CI/CD 安全性**：檢查 GitHub Actions secrets 管理、container registry 認證方式
7. **錯誤邊界**：檢查藥物知識庫不可用、Vector DB 連線失敗等情況的降級策略
8. **測試覆蓋**：確認每種安全檢查至少有一個 unit test 與一個 integration test

### Merge Gate
1. Python CI（unit test + lint）全部通過
2. 前端 build + lint + test 全部通過
3. Docker image build 成功（size < 500MB）
4. Docker Compose 完整啟動測試通過（smoke test）
5. CI Pipeline 全部通過（lint + test + build + security scan）
6. 所有 E2E test 通過
7. 所有既有 regression test 通過
8. 程式碼審查至少 1 人 approve
9. 無 blocking 級 SAST 安全掃描發現
10. PR 包含部署說明與環境變數列表

### 下一批解鎖條件
B3 合併至 master 後，Phase 4 全部完成，可進入 Phase 5 Platform 建置階段。

---

---

# Gate 0：Phase 4 規劃完成 ✅

Phase 4 所有的 3 個 Vertical Slice Batch 均已定義完成，依賴關係明確，Gate 條件完整。

## Phase 4 整合 Gate

Phase 4 採用漸進整合策略：每個 Batch 完成後自動觸發下一 Batch，最終由 B3 承擔全功能回歸驗證。

| 檢查點 | 條件 | 對應 Batch |
|--------|------|-----------|
| **B1 完成 Gate** | 病患資料匯入、證據檢索、AI 推薦、治療計畫、FHIR Export、Audit、前端展示完整鏈路通過 | B1 |
| **B2 完成 Gate** | 臨床試驗匹配、Evidence Ranking、Recommendation Update、CarePlan 管理、前端整合通過 | B2 |
| **B3 完成 Gate** | 藥物安全檢查、RAG 語義檢索、Background Jobs、Observability、Docker/CI/CD、前端統一入口全部通過 | B3 |
| **回歸 Gate** | 所有既有測試（~99 Python + ~35 Go + ~14 Frontend）通過 | 全部 |

## Phase 4 退出條件

完成以上所有 Gate 後，系統可進入 Phase 5（Medical AI Platform）：
- ML Model Training Pipeline 啟動（Phase 5 範疇）
- HL7/DICOM/PACS 整合開始（Phase 5 範疇）
- Multi-specialty Platform 化設計（Phase 5 範疇）
- Microservices 可行性評估（Phase 5 範疇）

---

# Phase 5：Medical AI Platform

Phase 5 將以 Oncology（精準腫瘤學）為主的系統，提煉為多專科 Medical AI Platform，支援 Cardiology、Neurology、Radiology 等專科模組的插件式擴充。
採用 **3 個 Batch** 結構，每個 Batch 預估 4-6 週完成。

**啟動 Gate**：Phase 4 全部 3 個 Batch 完成並通過整合 Gate。

---

## Batch 1：Platform Core + Specialty Framework

### 目標
建立 Medical AI Platform 的核心骨架，包括 Platform Core（PlatformContainer DI 框架、基礎 Config 與 Version 管理）、Specialty Contract（SpecialtyBase 抽象介面、模版目錄 .template/）以及 Registry 系統（SpecialtyRegistry、AgentRegistry、WorkflowRegistry、EvidenceSourceRegistry、RuleSetRegistry），使後續專科模組可透過 Registry 動態註冊，並提供標準化的專科模組開發範本。

### 前置依賴
- **Phase 4 全部完成**（3 個 Batch 通過整合 Gate）
- **既有依賴**：既有 oncologymodule 作為第一個被自動註冊的 built-in specialty
- **技術依賴**：Python DI 框架（依既有 FastAPI Depends 擴充）
- **外部依賴**：ICD-10 心臟科編碼、LOINC 心臟檢驗編碼

### 交付內容
**檔案範圍（25-32 files）**：
| 區域 | 檔案 | 類型 |
|------|------|------|
| Platform Package | `src/backend/platform/__init__.py`、`config.py`、`di.py`、`version.py` | 新建 |
| Platform Container | `src/backend/platform/container.py`（DI 容器 + 生命週期） | 新建 |
| Base Registry | `src/backend/platform/registry/__init__.py`、`registry/base.py`（BaseRegistry 抽象） | 新建 |
| Specialty Registry | `src/backend/platform/registry/specialty_registry.py`（註冊/生命週期/版本管理） | 新建 |
| Agent Registry | `src/backend/platform/registry/agent_registry.py`（Agent 動態選擇） | 新建 |
| Workflow Registry | `src/backend/platform/registry/workflow_registry.py`（Workflow 定義管理） | 新建 |
| EvidenceSource Registry | `src/backend/platform/registry/evidence_source_registry.py` | 新建 |
| RuleSet Registry | `src/backend/platform/registry/rule_registry.py` | 新建 |
| SpecialtyBase | `src/backend/specialties/base.py`（AbstractBaseSpecialty） | 新建 |
| 模版目錄 | `src/backend/specialties/.template/__init__.py`、`manifest.json`、`config.py`、`models.py` | 新建 |
| Cardiology Module | `src/backend/specialties/cardiology/__init__.py`（含 SPECIALTY_MANIFEST） | 新建 |
| Cardiology Domain | `src/backend/specialties/cardiology/models.py`（CardioCaseModel、ECGModel、RiskScore 等） | 新建 |
| Cardiology Agent | `src/backend/specialties/cardiology/agents/diagnosis_agent.py`、`guideline_agent.py`、`risk_agent.py` | 新建 |
| Cardiology Workflow | `src/backend/specialties/cardiology/workflows/chest_pain_assessment.py` | 新建 |
| Cardiology Terminology | `src/backend/specialties/cardiology/terminology/icd10_cardiac.json`、`loinc_cardiac.json` | 新建 |
| Terminology Service | `src/backend/platform/terminology/service.py`、`models.py`、`repository.py` | 新建 |
| Platform API | `src/backend/api/v1/platform.py`（health/version/specialties 端點） | 新建 |
| Migration | `migrations/versions/026_platform_registry_tables.py` | 新建 |
| 既有修改 | `src/backend/main.py`（初始化 PlatformContainer + Registry 掃描） | 修改 |
| 既有修改 | `src/backend/domain/enums.py`（SpecialtyType 移至 platform） | 修改 |
| 測試 | `tests/unit/platform/test_*.py`（各 Registry unit tests + contract tests） | 新建 |
| 測試 | `src/backend/specialties/cardiology/tests/`（Cardiology 專屬測試） | 新建 |

### 驗收標準
- [ ] 系統啟動時自動掃描並註冊 oncology 模組為 built-in specialty
- [ ] API `GET /api/v1/platform/specialties` 回傳 oncology 模組資訊（id、version、display_name）
- [ ] API `GET /api/v1/platform/health` 回傳各 registry 健康狀態
- [ ] AgentRegistry 可依 specialty_id 查詢對應的 agent 集合
- [ ] WorkflowRegistry 可註冊/查詢 specialty 專屬 workflow
- [ ] Cardiology module 可獨立註冊/啟動/停止（透過 SpecialtyRegistry）
- [ ] `POST /api/v1/workflows/cardiology.chest_pain/execute` 可執行胸痛評估工作流
- [ ] `GET /api/v1/terminology/normalize?code=I21.0&system=ICD-10` 正確映射心臟科 code
- [ ] Cardiology diagnosis agent 可分析 CardioCaseModel 並回傳有意義的意見（opinion）
- [ ] .template/ 目錄可供第三方開發者複製作為新 specialty 起點
- [ ] 既有 oncology 功能完全不受影響（regression test pass）
- [ ] 所有 registry unit tests 與 contract tests 通過
- [ ] 所有 Cardiology 專屬測試通過

### ChatGPT Review Gate
1. **Registry 介面設計**：檢查各 Registry 的抽象介面是否一致（register/unregister/get/list）；確認 lifecycle hook（load/start/stop/unload）完整
2. **DI 注入正確性**：檢查 PlatformContainer 是否正確管理 singleton vs. scoped 依賴；確認無循環依賴
3. **Oncology 自動註冊**：檢查 startup 時如何掃描並註冊既有 oncology 模組；確認註冊後不影響既有功能
4. **Contract 完整性**：檢查 SpecialtyBase 是否定義了 specialty 模組必須實作的所有方法；檢查 manifest.json 欄位是否完整
5. **Cardiology Agent 品質**：檢查診斷邏輯是否基於 ACC/AHA guideline；檢查 guideline version 註明
6. **Terminology mapping 正確性**：檢查 ICD-10 cardiac codes 映射是否正確（至少涵蓋常見 heart disease codes）
7. **錯誤處理**：檢查 specialty 註冊失敗時的 graceful degradation；確認 registry 可處理重複註冊
8. **測試覆蓋**：確認每個 registry 至少有 register、get、list、unregister 四個操作測試

### Merge Gate
1. Python CI（unit test + lint）全部通過
2. 所有 registry unit tests 與 contract tests 通過
3. 所有 Cardiology module tests 通過
4. 既有 regression test 全部通過（~99 + ~35 + ~14）
5. 程式碼審查至少 1 人 approve（架構師必須參與）
6. SAST 掃描無 blocking 發現
7. PR 包含 platform package 的 API 文件

### 下一批解鎖條件
B1 合併至 master 後，B2（Oncology Decoupling + Multi-Tenant）可啟動。

---

## Batch 2：Oncology Decoupling + Multi-Tenant

### 目標
將 Oncology 模組從平台核心解耦（提取 AbstractCase、AbstractConsensus，保持向下相容），引入 Multi-Tenant 架構支援多家醫院/租戶資料隔離，擴充 Knowledge Graph Namespace 支援跨專科隔離，完善 Terminology Service 跨專科術語映射，並建立 API 版本管理機制（v1/v2 共存）。

### 前置依賴
- **B1（Platform Core + Specialty Framework）**：需要 Platform Registry 與 Specialty Contract 基礎
- **外部依賴**：ICD-10、SNOMED CT、LOINC、RxNorm 術語資料集
- **既有依賴**：既有 Oncology 模組（作為抽象化對象）

### 交付內容
**檔案範圍（30-38 files）**：
| 區域 | 檔案 | 類型 |
|------|------|------|
| AbstractCase | `src/backend/domain/abstract_case.py`（通用 case 介面） | 新建 |
| AbstractConsensus | `src/backend/domain/abstract_consensus.py`（通用 consensus 介面） | 新建 |
| CancerCase 修改 | `src/backend/domain/cancer_case.py`（繼承 AbstractCase） | 修改 |
| TumorBoard 修改 | `src/backend/domain/tumor_board.py`（提取 AbstractConsensus） | 修改 |
| ClinicalContext 擴充 | `src/backend/clinical/models.py`（加 diagnosis_code、diagnosis_system、specialty_id） | 修改 |
| Agent 改造 | `src/backend/agents/base.py`（加 SpecialtyAgentMixin）、`src/backend/agents/diagnosis_agent.py` 等 | 修改 |
| Rule 提取 | `src/backend/clinical/treatment_plan_rules.py`（oncology-specific 邏輯提取） | 修改 |
| Scorer 提取 | `src/backend/ranking/scorers.py`（oncology mapping 提取） | 修改 |
| Orchestrator 改造 | `src/backend/agents/orchestrator.py`（使用 AgentRegistry 動態選擇 agent） | 修改 |
| 回歸測試 | `tests/regression/test_oncology_compatibility.py` | 新建 |
| Tenant Middleware | `src/backend/platform/middleware/tenant_middleware.py`（JWT tenant claims 解析） | 新建 |
| Tenant Model | `src/backend/platform/models/tenant.py`（Tenant 領域模型） | 新建 |
| Tenant Repository | `src/backend/platform/repositories/tenant_repository.py` | 新建 |
| Tenant API | `src/backend/api/v1/tenants.py`（Tenant CRUD admin API） | 新建 |
| TenantAwareRepository | `src/backend/repositories/base.py`（共用表 + tenant_id 過濾） | 修改 |
| Database Base | `src/backend/database/base.py`（加 tenant_id mixin） | 修改 |
| Auth 擴充 | `src/backend/auth/dependencies.py`（加 tenant dependency） | 修改 |
| API v2 路由 | `src/backend/api/v2/__init__.py`、`router.py` | 新建 |
| API v2 端點 | `src/backend/api/v2/workflows.py`（首個 v2 端點） | 新建 |
| 隔離策略 | `deploy/config/tenant_isolation.yml`（檔案/queue/cache 隔離設定） | 新建 |
| NamespacedStore | `KnowGraphGo/graph/store/namespace.go`（namespace-aware store wrapper） | 新建 |
| Namespace Test | `KnowGraphGo/graph/store/namespace_test.go` | 新建 |
| KG API 擴充 | `src/backend/knowledge/api.py`（支援 namespace 參數查詢） | 修改 |
| Terminology Service 強化 | `src/backend/platform/terminology/service.py`（完成 cache + bulk lookup） | 修改 |
| Terminology Mappings | `src/backend/platform/terminology/mappings/icd10.json`、`snomed.json`、`loinc.json`、`rxnorm.json` | 新建 |
| Terminology CLI | `scripts/terminology/import_mappings.py`（匯入 CLI 工具） | 新建 |
| Oncology Namespace 遷移 | `scripts/migrations/migrate_kg_namespace.py`（現有資料加 prefix） | 新建 |
| Migration - Tenant | `migrations/versions/027_tenant_id_add.py` | 新建 |
| Go CI | `.github/workflows/go-ci.yml`（若 Phase 4 未建） | 新建 |
| 測試 | `tests/unit/platform/test_tenant.py`、`tests/integration/test_tenant_isolation.py`、`tests/unit/platform/test_*.py`（Tenant unit tests） | 新建 |

### 驗收標準
- [ ] Oncology module 仍可正常運作（regression test suite pass）
- [ ] CancerCaseModel 仍可正常 CRUD（繼承 AbstractCase，所有既有 API 端點不變）
- [ ] ClinicalContext.cancer_type 仍可讀取（作為 diagnosis_code 的 alias 保留）
- [ ] Agent selection 可正確選擇 oncology agent（Orchestrator 依 specialty 路由）
- [ ] 無任何 breaking change（所有既有端點、model、API 回應格式不變）
- [ ] Multi-tenant 可正常運作：至少 2 個 tenant 各自登入後僅能看到自己的資料
- [ ] 無 tenant 可透過 API 存取另一 tenant 資料（security test 驗證）
- [ ] Tenant config 可動態 overlay（specified tenant 可覆蓋 platform default config）
- [ ] API 端點同時支援 v1（不變）與 v2（新增 tenant-aware path）
- [ ] Tenant admin API 需有權限控制（僅 super admin 可操作）
- [ ] KnowGraphGo 支援 `WithNamespace(ns)` 查詢過濾
- [ ] TerminologyService 可解析 ICD-10 / SNOMED / LOINC codes（含 cache）
- [ ] 現有 oncology 知識圖譜資料遷移至 oncology namespace（加 prefix）
- [ ] Go CI 包含 go build + go test + golangci-lint（若 Phase 4 未建）
- [ ] 所有既有 API v1 端點行為不變

### ChatGPT Review Gate
1. **向後相容性**：檢查 AbstractCase 引入後，CancerCase 的所有公有方法簽名是否一致；檢查 `cancer_type` alias 是否正確委託
2. **抽象化邊界**：檢查 AbstractCase 是否僅提取真正通用的欄位（patient_id、diagnosis_code、stage、status）
3. **Agent 改造影響**：確認移除 cancer-specific hardcode 後，agent 的行為邏輯不變
4. **Tenant 隔離策略**：檢查 tenant_id 過濾是否應用於所有 repository 查詢；檢查 JWT tenant claims 防竄改
5. **API 版本策略**：檢查 v1/v2 router 是否完全隔離；確認 v2 不影響 v1 行為
6. **Namespace 設計**：檢查 namespace 隔離方案不影響跨 namespace 查詢效能
7. **Terminology Mapping 正確性**：抽樣檢查 ICD-10 心臟科編碼、SNOMED 神經科編碼
8. **Migration 安全性**：檢查 namespace 遷移腳本是否包含 dry-run 模式、rollback 機制
9. **測試完整性**：確認 tenant isolation test 包含正反案例；回歸測試涵蓋所有 oncology 核心 API

### Merge Gate
1. Python CI 全部通過
2. **強制**：完整 regression test suite 通過（含新加的 oncology 相容性測試）
3. Tenant isolation security test 全部通過（含穿透測試）
4. Go CI pipeline 通過（build + test + lint）
5. 既有 regression test 全部通過
6. 程式碼審查至少 2 人 approve（架構師 + 領域專家）
7. SAST + DAST 掃描通過
8. PR 需包含「向後相容性檢查清單」與 tenant 管理的使用說明
9. 不得同時合併其他可能衝突的 PR

### 下一批解鎖條件
B2 合併至 master 後，B3（Developer Docs + SDK Template）可啟動。

---

## Batch 3：Developer Docs + SDK Template

### 目標
完成 Phase 5 開發者文件、SDK Template 專案、API 文件更新、從單一 Oncology 遷移至 Multi-Specialty 的指南、效能測試與安全審查，並進行最終驗收測試，確保平台可供外部開發者使用。

### 前置依賴
- **B2（Oncology Decoupling + Multi-Tenant）**：需所有平台功能完成
- **全部 Phase 5 Batch**：驗收測試需基於完整系統

### 交付內容
**檔案範圍（18-25 files）**：
| 區域 | 檔案 | 類型 |
|------|------|------|
| 開發者文件 | `docs/platform/developer-guide.md`（如何建立新 Specialty） | 新建 |
| SDK Template | `sdk/template/`（Python SDK 樣板專案，含 client library、CLI 工具、範例程式碼） | 新建 |
| API 文件 | `docs/api/openapi-v2.yaml`（v2 API 規格） | 新建 |
| 遷移指南 | `docs/platform/migration-guide.md`（Oncology-only → Multi-Specialty） | 新建 |
| 效能報告 | `docs/platform/performance-report.md`（multi-tenant + multi-specialty） | 新建 |
| 安全審查 | `docs/platform/security-review.md`（tenant isolation + specialty isolation） | 新建 |
| 測試報告 | `tests/reports/phase5-test-report.md` | 新建 |
| 既有文件更新 | `README.md`（更新架構描述）、`docs/architecture/overview.md` | 修改 |

### 驗收標準
- [ ] 開發者文件涵蓋：建立新 Specialty 的完整步驟（複製 .template/ → 修改 manifest → 實作 agents/workflows → 註冊）
- [ ] SDK Template 包含 client library、CLI 工具與範例程式碼，可直接複製開始開發
- [ ] API 文件完整（含 v1 + v2 端點）
- [ ] 遷移指南說明既有 oncology 使用者如何無痛過渡
- [ ] 效能測試報告包含 multi-tenant 與 multi-specialty 情境
- [ ] 安全審查確認 tenant isolation 無漏洞
- [ ] 所有 Phase 5 強制驗收標準（AC1~AC8）通過

### ChatGPT Review Gate
1. **文件完整性**：檢查開發者文件是否涵蓋 registry 註冊、agent 開發、workflow 定義、terminology 映射等核心概念
2. **SDK Template 可用性**：檢查 SDK 是否提供直觀的 API 封裝、範例程式碼是否可直接執行
3. **API 文件正確性**：檢查 OpenAPI spec 與實際端點行為一致（request/response schema、status code）
4. **遷移指南實用性**：確認指南包含完整的檢查清單、常見問題、rollback 程序
5. **安全審查完整性**：確認 tenant isolation 測試案例涵蓋所有存取路徑（API、database、cache、queue）
6. **測試覆蓋**：確認最終測試報告顯示 coverage ≥ 80%

### Merge Gate
1. 所有 Python CI + Go CI 通過
2. 完整 regression test suite 通過
3. SDK Template build 與 test 通過
4. 效能測試結果符合 SLO（如：P99 latency < 500ms under 100 concurrent requests）
5. 安全審查簽署通過
6. 程式碼審查至少 1 人 approve
7. 所有文件格式檢查通過（markdown lint）

### 下一批解鎖條件
B3 合併至 master 後，Phase 5 全部完成。

---

## Phase 5 整體驗收標準

### 強制標準（Must-Have）

| # | 標準 | 驗證方式 | 對應 Batch |
|---|------|---------|-----------|
| AC1 | Oncology 模組完全不受影響 | 全部現有 test suite pass | B2 |
| AC2 | 至少 1 個非 oncology specialty（cardiology）可完整運作 | E2E test | B1 |
| AC3 | Registry 可正確註冊/啟動/停止 specialty | API test | B1 |
| AC4 | Agent selection 依 specialty 正確路由 | Integration test | B2 |
| AC5 | Knowledge Graph 支援 namespace 隔離 | Go test | B2 |
| AC6 | Terminology Service 可正確映射 ICD-10/SNOMED | Unit test | B1/B2 |
| AC7 | Multi-tenant 資料隔離 | Security test | B2 |
| AC8 | API 向下相容（v1 端點不改） | Regression test | B2 |
| AC9 | SDK Template 可被第三方複製使用 | Integration test | B3 |

### 期望標準（Should-Have）

| # | 標準 | 優先級 | 對應 Batch |
|---|------|--------|-----------|
| SC1 | 開發者文件完成 | P1 | B3 |
| SC2 | 遷移指南發布 | P1 | B3 |
| SC3 | 效能測試報告完成 | P1 | B3 |
| SC4 | 安全審查通過 | P1 | B3 |
| SC5 | CI/CD 包含 Go pipeline | P1 | B2 |

---

## 跨 Phase 依賴概要

```
Phase 4 完成度                    Phase 5 影響
─────────────────────────────────────────────────
病患資料整合與臨床工作流  ──────  B1 (Platform Core + Specialty Framework)
臨床試驗與證據排序        ──────  B2 (Oncology Decoupling + Multi-Tenant)
藥物安全與監控            ──────  B1-B3 (基礎設施支撐)
FHIR R4 互通層            ──────  B1 (Specialty Contract)
Adapters 證據層           ──────  B2 (Oncology Decoupling)
RAG/Vector DB             ──────  B2-B3 (語義搜尋與 SDK)
Infrastructure & Observability ─  B1-B3 (平台監控)
Docker/CI/CD              ──────  B1-B3 (容器化部署)
```

---

## 附錄：Batch 依賴關係一覽

```
Phase 4
═══════
B1 (病患資料整合與臨床工作流)  ─── 無前置，獨立啟動 ──→ B2
B2 (臨床試驗與證據排序)        ─── 依賴 B1 ──────────→ B3
B3 (藥物安全與監控)            ─── 依賴 B1/B2 ───────→ Phase 5

Phase 5
═══════
B1 (Platform Core + Specialty Framework) ─── 依賴 Phase 4 全部完成 ────→ B2
B2 (Oncology Decoupling + Multi-Tenant)    ─── 依賴 B1 ──────────────────→ B3
B3 (Developer Docs + SDK Template)         ─── 依賴 B2
```

---

> **文件結束** — Phase 4 & Phase 5 Development Roadmap
>
> 本路線圖以 Batch 和 Gate 為單位，基於 Phase 4 Master Plan、Phase 5 Master Plan 及 Dependency Map 產出。
> 所有 Batch 的目標、依賴與驗收標準均可追溯至對應的 Master Plan 文件。
