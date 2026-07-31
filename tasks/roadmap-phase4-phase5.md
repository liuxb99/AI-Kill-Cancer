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

---

## Batch 1：FHIR R4 醫院互通

### 目標
建立完整的 FHIR R4 互通層，使外部 EHR/EMR 系統可透過標準 FHIR REST API 存取本系統的病患資料、檢驗報告、治療計畫等臨床資源，並支援 SMART-on-FHIR 授權框架。

### 前置依賴
- **外部依賴**：FHIR R4 規範（Patient/Observation/DiagnosticReport/CarePlan/MedicationRequest/Condition/Procedure）
- **外部依賴**：SMART-on-FHIR Standalone Launch flow 規格
- **既有依賴**：既有 Domain Model（PatientModel、CancerCaseModel、TreatmentPlanModel）作為 FHIR Resource 映射來源
- **既有依賴**：既有 JWT/RBAC 框架（FHIR 端點需整合既有授權）
- **無內部 Batch 前置依賴**（可與 B2/B3/B4 並行啟動）

### 交付內容
**檔案範圍（18-22 files）**：
| 區域 | 檔案 | 類型 |
|------|------|------|
| FHIR 資源模型 | `src/backend/fhir/models/patient.py`、`observation.py`、`medication_request.py`、`diagnostic_report.py`、`condition.py`、`procedure.py`、`care_plan.py`、`__init__.py` | 新建 |
| FHIR 核心 | `src/backend/fhir/__init__.py`、`fhir/constants.py`、`fhir/validators.py`、`fhir/converters.py` | 新建 |
| FHIR API | `src/backend/api/v1/fhir.py`（路由模組） | 新建 |
| CapabilityStatement | `src/backend/fhir/capability.py` | 新建 |
| SMART-on-FHIR | `src/backend/auth/smart_on_fhir.py` | 新建 |
| 資料庫遷移 | `migrations/versions/026_fhir_resource_tables.py`（若需新建 FHIR 表） | 新建 |
| 測試 | `tests/unit/fhir/test_*.py`（各資源模型測試）、`tests/integration/fhir/test_api.py` | 新建 |
| 文件 | `docs/fhir/integration_guide.md` | 新建 |
| 既有修改 | `src/backend/main.py`（註冊 FHIR 路由）、`src/backend/auth/dependencies.py`（擴充 SMART scope） | 修改 |

### 驗收標準
- [ ] 所有 FHIR R4 核心資源端點（Patient/Observation/Condition/MedicationRequest/DiagnosticReport/CarePlan）支援 Read 與 Search 操作
- [ ] `GET /metadata`（CapabilityStatement）回傳有效 FHIR R4 能力聲明
- [ ] FHIR 資源回應符合 FHIR R4 JSON 格式規範
- [ ] SMART-on-FHIR Standalone Launch flow 完整（取得 token → 存取 FHIR API）
- [ ] FHIR 端點整合既有 JWT/RBAC（未授權請求回傳 401/403）
- [ ] FHIR 驗證（使用 fhirpath/fhir-validator）通過核心資源結構驗證
- [ ] 所有 FHIR 單元測試通過（mock 資料）
- [ ] 所有既有測試不受影響（regression pass）

### ChatGPT Review Gate
1. **FHIR 資源模型正確性**：檢查每個 Resource model 的欄位是否符合 FHIR R4 規範（cardinality、type、required fields）
2. **Converter 映射完整性**：檢查從內部 Domain Model → FHIR Resource 的映射是否涵蓋所有必要欄位，無遺失重要臨床資料
3. **SMART-on-FHIR 實作合規**：檢查授權流程（token exchange、scope validation）是否符合 SMART App Launch Implementation Guide
4. **錯誤處理**：檢查 FHIR OperationOutcome 回應格式是否正確、錯誤案例是否完整覆蓋
5. **測試覆蓋率**：檢查每種 FHIR resource 至少有一個 read 和一個 search 測試案例

### Merge Gate
1. Go/GitHub Actions CI pipeline 全部通過
2. Python CI（unit test + lint）全部通過
3. FHIR 格式化檢查通過（`fhir_validator` 無 error）
4. 所有既有 regression test 通過（~99 Python tests + ~35 Go tests + ~14 Frontend tests）
5. 程式碼審查至少 1 人 approve
6. 無 blocking 級 SAST 安全掃描發現
7. PR 描述包含 FHIR 端點變更摘要

### 下一批解鎖條件
B1 合併至 master 後，B5（Docker + CI/CD）可開始將 FHIR 功能納入 Docker image。B2/B3/B4 不依賴 B1，可隨時獨立啟動。

---

## Batch 2：外部證據 Adapter 真實連接

### 目標
將 8 個外部證據源的 adapter 從 stub/simplified 實作升級為真實 REST API 或本地工具連接，使臨床決策引擎與 Agent 可存取真實世界證據。

### 前置依賴
- **外部依賴**：CIViC REST API（公開端點）、DGIdb REST API（公開）、OncoTree REST API（公開）、MyVariant.info REST API（公開）、DRKG REST API（公開）、PharmCAT（本地工具）、Ensembl VEP REST API（公開）、OpenCRAVAT（本地工具）
- **既有依賴**：既有 `adapters/base.py` 的 adapter 介面合約
- **技術依賴**：外部 API key 管理機制（環境變數或 vault）
- **無內部 Batch 前置依賴**（可與 B1/B3/B4 並行啟動）

### 交付內容
**檔案範圍（16-20 files）**：
| 區域 | 檔案 | 類型 |
|------|------|------|
| CIViC Adapter | `src/backend/pipeline/civic_adapter.py` | 修改（stub → real） |
| DGIdb Adapter | `src/backend/pipeline/dgidb_adapter.py` | 修改（stub → real） |
| OncoTree Adapter | `src/backend/pipeline/oncotree_adapter.py` | 修改（stub → real） |
| MyVariant.info Adapter | `src/backend/pipeline/myvariant_adapter.py` | 修改（stub → real） |
| DRKG Adapter | `src/backend/pipeline/drkg_adapter.py` | 修改（stub → real） |
| PharmCAT Adapter | `src/backend/pipeline/pharmcat_adapter.py` | 修改（stub → real） |
| Ensembl VEP Adapter | `src/backend/pipeline/vep_adapter.py` | 修改（stub → real） |
| OpenCRAVAT Adapter | `src/backend/pipeline/opencravat_adapter.py` | 修改（stub → real） |
| Adapter Registry | `src/backend/adapters/registry.py`（更新註冊資訊） | 修改 |
| 快取層 | `src/backend/adapters/cache.py`（新增快取策略） | 新建 |
| 健康檢查 | `src/backend/adapters/health.py`（adapter 狀態彙總） | 新建 |
| Secrets 管理 | `src/backend/infrastructure/secrets.py`（API key 管理） | 新建 |
| 測試 | `tests/unit/adapters/test_*.py`（各 adapter 單元測試） | 新建 |
| 設定 | `config/adapters.yml`（adapter 端點與 timeout 設定） | 新建 |
| 文件 | `docs/adapters/external_sources.md` | 新建 |
| 其他 | Guideline Adapter（NCCN/ESMO）+ Clinical Trial Matching 強化 | 新建/修改 |

### 驗收標準
- [ ] 8 個 adapter 全部從 stub 升級為真實實作，`GET /api/v1/adapters/status` 回傳全部 configured（可能部分 offline 但非 stub）
- [ ] 每個 adapter 至少支援 1 個 query method（搜尋/查詢/比對）
- [ ] Adapter 快取層可正常運作（降低外部 API 呼叫次數）
- [ ] 外部 API key 儲存於環境變數（不 hardcode）
- [ ] 單元測試使用 mock 外部 API，不依賴真實網路連線
- [ ] 所有 adapter 整合既有 AdapterRegistry
- [ ] OpenCRAVAT pipeline 可本地執行或回傳有意義的錯誤訊息

### ChatGPT Review Gate
1. **Adapter 介面合規**：每個 adapter 是否遵循 `adapters/base.py` 定義的抽象介面（query、parse、transform）
2. **錯誤處理全面性**：檢查 HTTP timeout、rate limit、API key expired、invalid response 等情況的錯誤處理
3. **資料模型正確性**：adapter 回傳的資料是否正確映射到內部 EvidenceItem/DrugInteraction 等領域模型
4. **快取策略合理性**：檢查快取 TTL、cache key 設計、cache invalidation 時機
5. **Secrets 安全性**：確認沒有任何 API key/secret 出現在程式碼中

### Merge Gate
1. Python CI（unit test + lint）全部通過
2. 所有 adapter unit test 使用 mock，不因外部 API 狀態而失敗
3. 既有 regression test 全部通過
4. 程式碼審查至少 1 人 approve
5. SAST 掃描無 secrets leak 警報
6. PR 包含 adapter 狀態檢查的變更說明

### 下一批解鎖條件
B2 合併至 master 後，B5（Docker + CI/CD）可將 adapter 依賴納入 Docker image。B1/B3/B4 不依賴 B2。

---

## Batch 3：RAG／Vector DB／Embedding Pipeline

### 目標
建立基於 Vector DB 的語義檢索增強生成（RAG）系統，使臨床決策可參考相關文獻、guideline 和既有證據，實現 KnowledgeBase 語義搜尋。

### 前置依賴
- **外部依賴**：Vector DB 服務（Chroma/Qdrant/Pinecone 擇一）
- **外部依賴**：Embedding 模型 API key 或本地部署（OpenAI/BGE 擇一）
- **資料依賴**：既有臨床文檔（guideline items、evidence items、clinical literature）
- **技術依賴**：langchain / chromadb / qdrant-client 等 Python 套件
- **無內部 Batch 前置依賴**（可與 B1/B2/B4 並行啟動）

### 交付內容
**檔案範圍（14-18 files）**：
| 區域 | 檔案 | 類型 |
|------|------|------|
| Vector DB 服務 | `src/backend/rag/vector_store.py`（抽象介面 + Chroma/Qdrant 實作） | 新建 |
| Embedding Pipeline | `src/backend/rag/embedding.py`（embedding 產生 + 批次索引） | 新建 |
| RAG 檢索服務 | `src/backend/rag/retriever.py`（similarity search + hybrid search） | 新建 |
| RAG Service | `src/backend/rag/service.py`（檢索 + context 組裝） | 新建 |
| RAG API | `src/backend/api/v1/rag.py`（`POST /rag/search`、`POST /rag/query`） | 新建 |
| Clinical Context 整合 | `src/backend/rag/clinical_context.py`（病患 context → query 轉換） | 新建 |
| ReasonService 整合 | `src/backend/reasoning/service.py`（整合 RAG 檢索結果） | 修改 |
| 設定 | `config/rag.yml`（embedding model、chunk size、top-k 等） | 新建 |
| Migration | `migrations/versions/027_vector_store_init.py`（向量索引記錄表） | 新建 |
| 測試 | `tests/unit/rag/test_*.py`（各元件測試） | 新建 |
| 文件 | `docs/rag/architecture.md` | 新建 |
| 既有修改 | `src/backend/main.py`（註冊 RAG 路由） | 修改 |

### 驗收標準
- [ ] Embedding pipeline 可對臨床文件進行批次索引（chunk → embed → store）
- [ ] Vector DB 支援語義搜尋（natural language query 回傳相關 document chunks）
- [ ] RAG API 可接收查詢並回傳檢索結果（含 relevance score）
- [ ] ReasonService 可呼叫 RAG 服務取得相關臨床證據
- [ ] KnowledgeBase 頁面（與 B6 整合）可進行語義搜尋
- [ ] 單元測試使用 in-memory Vector DB（不依賴外部服務）
- [ ] Embedding 模型可透過設定檔切換（不 hardcode）

### ChatGPT Review Gate
1. **Vector DB 抽象介面**：是否正確封裝 Vector DB 操作（add/delete/search），使後續可切換底層 DB
2. **Embedding 品質**：檢查 chunk size overlap 策略是否合理；檢查 embedding 模型選擇是否適合臨床文本
3. **RAG 檢索 pipeline**：query → embed → search → rerank → response 流程是否完整
4. **錯誤邊界**：檢查 Vector DB 連線失敗、embedding API timeout 等情況的降級策略
5. **測試覆蓋**：確認每個 RAG 元件至少有一個 unit test

### Merge Gate
1. Python CI（unit test + lint）全部通過
2. 所有 RAG unit test 使用 in-memory 或 mock，不依賴外部 Vector DB 實例
3. 既有 regression test 全部通過
4. 程式碼審查至少 1 人 approve
5. 無 blocking 級安全掃描發現
6. PR 包含 embedding model 設定說明

### 下一批解鎖條件
B3 合併至 master 後，B5（Docker + CI/CD）可將 Vector DB 納入 Docker Compose。B6 的 KnowledgeBase 頁面強化可選擇性依賴 B3（若 B3 未完成，KnowledgeBase 先保留基本功能）。

---

## Batch 4：基礎設施與可觀測性（Infrastructure & Observability）

### 目標
建立生產級基礎設施與可觀測性系統，包括 Background Job Queue（ARQ + Redis）、Job API（enqueue/status/cancel）、Cron-like Job Scheduler、泛化 Retry/Dead-letter 機制，以及 Metrics（Prometheus）、分散式追蹤（OpenTelemetry）、結構化 Logging 和 Grafana 儀表板，使系統具備非同步任務處理能力，並讓營運團隊可即時掌握健康狀態。

### 前置依賴
- **外部依賴**：Prometheus（metrics 收集與儲存）
- **外部依賴**：Grafana（儀表板視覺化）
- **外部依賴**：OpenTelemetry Collector（分散式追蹤）
- **外部依賴**：Redis 服務（Background Job Queue 與快取）
- **技術依賴**：prometheus-client、opentelemetry-sdk、arq、redis、redis-py 等 Python 套件
- **既有依賴**：既有 `observability/audit.py`、`observability/health.py` 框架（擴充而非改寫）；Outbox 模式作為 Retry/Dead-letter 設計參考
- **無內部 Batch 前置依賴**（可與 B1/B2/B3 並行啟動）

### 交付內容
**檔案範圍（22-26 files）**：
| 區域 | 檔案 | 類型 |
|------|------|------|
| Background Jobs | `src/backend/jobs/__init__.py` | 新建 |
| Job Queue | `src/backend/jobs/queue.py`（ARQ queue 定義與 worker 管理） | 新建 |
| Job Scheduler | `src/backend/jobs/scheduler.py`（cron-like 定時任務排程器） | 新建 |
| Job Worker | `src/backend/jobs/worker.py`（ARQ worker 啟動腳本） | 新建 |
| Retry/Dead-letter | `src/backend/jobs/retry_policy.py`（泛化重試與死信策略） | 新建 |
| Job API | `src/backend/api/v1/jobs.py`（enqueue/status/cancel 端點） | 新建 |
| Metrics | `src/backend/observability/metrics.py`（Prometheus metrics 定義，含 job queue depth） | 新建 |
| Tracing | `src/backend/observability/tracing.py`（OpenTelemetry middleware） | 新建 |
| Logging | `src/backend/observability/logging.py`（JSON 結構化 logging） | 新建 |
| Profiling | `src/backend/observability/profiling.py`（slow query / memory） | 新建 |
| Health | `src/backend/observability/health.py`（擴充 adapter/db/vector/redis 狀態） | 修改 |
| Alerts | `src/backend/observability/alerts.py`（PrometheusAlertManager 規則） | 新建 |
| API 端點 | `src/backend/api/v1/health.py`（擴充詳細健康狀態） | 修改 |
| Middleware | `src/backend/main.py`（註冊 metrics/tracing middleware） | 修改 |
| Prometheus 設定 | `deploy/observability/prometheus.yml` | 新建 |
| Grafana Dashboard | `deploy/observability/grafana_dashboard.json`（含 job queue depth 面板） | 新建 |
| OTEL Collector | `deploy/observability/otel-collector.yml` | 新建 |
| Docker Compose | `docker-compose.observability.yml`（Observability stack） | 新建 |
| Docker Compose | `docker-compose.redis.yml`（Redis 服務設定） | 新建 |
| 測試 | `tests/unit/observability/test_metrics.py` | 新建 |
| 測試 | `tests/unit/jobs/test_queue.py` | 新建 |
| 測試 | `tests/unit/jobs/test_scheduler.py` | 新建 |
| 文件 | `docs/observability/monitoring.md` | 新建 |
| 文件 | `docs/jobs/background-jobs.md` | 新建 |

### 驗收標準
- [ ] `GET /metrics` 回傳 Prometheus 格式的 metrics（request count、latency、error rate、job queue depth、job duration）
- [ ] 分散式追蹤可追蹤單一請求跨 service 的完整路徑（API → service → adapter），job worker span 包含在追蹤中
- [ ] Health check 端點回傳資料庫、adapter、Vector DB、Redis Queue 的詳細健康狀態
- [ ] 所有 log 為 JSON 結構化格式（可被 log aggregator 解析），job log 包含 job_id 與 job_type
- [ ] Grafana 儀表板可視覺化核心指標（request rate、error rate、P99 latency、job queue depth、job duration）
- [ ] 警報規則可匯入 Prometheus AlertManager
- [ ] `POST /api/v1/jobs` 可提交 job，`GET /api/v1/jobs/{id}` 回傳正確狀態，`DELETE /api/v1/jobs/{id}` 可取消 job
- [ ] Job Scheduler 可註冊定時任務（cron expression），並在指定時間觸發
- [ ] Job 失敗後自動重試（可設定 max_retries），超過次數進入 dead-letter queue
- [ ] Redis 服務可透過 `docker-compose.redis.yml` 一鍵啟動
- [ ] 既有 audit log 不受影響

### ChatGPT Review Gate
1. **Metrics 命名規範**：檢查 metrics 名稱是否符合 Prometheus naming convention（`snake_case`、`_total` suffix 等）；確認 job queue metrics 涵蓋 depth、enqueue count、failure count
2. **Tracing 完整性**：確認 span 涵蓋 API → service → adapter 的完整 chain；檢查是否正確傳遞 trace context（W3C traceparent）；確認 job worker span 包含在追蹤中
3. **Logging 結構**：確認 JSON log 包含必要欄位（timestamp、level、request_id、service、message），job log 包含 job_id 與 job_type
4. **Job Queue 設計**：檢查 ARQ queue 設定是否合理（timeout、max_retries、retry_delay）；確認與既有 Outbox 模式的 Retry/Dead-letter 設計一致
5. **Job Scheduler 正確性**：檢查 cron expression 解析與觸發邏輯；確認 scheduler 在 worker crash 後可恢復
6. **Redis 配置合理性**：檢查 Redis connection pool 設定、key prefix 隔離、是否支援高可用（Sentinel/Cluster 選項）
7. **效能開銷評估**：檢查 metrics 收集是否使用 Prometheus client 的預設低開銷模式；tracing 是否設定合理取樣率
8. **安全防護**：確認 `/metrics` 端點不洩漏敏感資料（如 API key、病患 PII）

### Merge Gate
1. Python CI（unit test + lint）全部通過
2. Metrics unit test 不依賴實際 Prometheus 實例
3. Job unit test 使用 Redis mock（不依賴實際 Redis 實例）
4. 既有 regression test 全部通過
5. 程式碼審查至少 1 人 approve
6. 安全審查確認 `/metrics` 端點無資料外洩風險
7. PR 包含 observability stack 與 background jobs 的部署說明

### 下一批解鎖條件
B4 合併至 master 後，B5（Docker + CI/CD）可將 observability stack 與 Redis/Job worker 納入 Docker Compose。

---

## Batch 5：Docker + CI/CD 基礎設施

### 目標
建立完整的容器化部署方案與 CI/CD pipeline，支援一鍵啟動（後端 + 前端 + 知識圖譜 + 資料庫 + Vector DB + Observability stack），並補全 Go CI pipeline 與 Docker CI pipeline。

### 前置依賴
- **B1（FHIR R4）**：FHIR 功能需存在於 Docker image 中
- **B2（External Adapters）**：Adapter 依賴需存在於 Docker image 中
- **B3（RAG/Vector DB）**：Vector DB 需存在於 Docker Compose 中
- **B4（Observability）**：Observability stack 需存在於 Docker Compose 中
- **技術依賴**：Docker、Docker Compose、GitHub Actions（CI/CD）
- **Migration 依賴**：Docker entrypoint 需自動執行 alembic upgrade

### 交付內容
**檔案範圍（16 files）**：
| 區域 | 檔案 | 類型 |
|------|------|------|
| Dockerfile | `Dockerfile.backend`、`Dockerfile.frontend`、`Dockerfile.knowgraph` | 新建 |
| Docker Compose | `docker-compose.yml`（production）、`docker-compose.dev.yml` | 新建 |
| CI Workflow | `.github/workflows/go-ci.yml`（Go pipeline） | 新建 |
| CI Workflow | `.github/workflows/docker-ci.yml`（Docker build + scan + push） | 新建 |
| CI Workflow | `.github/workflows/deploy.yml`（擴充後端部署） | 修改 |
| 設定 | `.dockerignore`、`deploy/env/backend.env.example`、`deploy/env/frontend.env.example` | 新建 |
| 部署腳本 | `deploy/scripts/startup.sh`（含 alembic upgrade）、`deploy/scripts/init_db.sh` | 新建 |
| Nginx | `deploy/nginx/default.conf` | 新建 |
| 文件 | `docs/deployment/guide.md`、`docs/deployment/environments.md` | 新建 |

### 驗收標準
- [ ] `docker-compose up` 可一鍵啟動完整系統（後端 + 前端 + KG + PostgreSQL + Vector DB + Prometheus + Grafana）
- [ ] 後端 Docker image 包含所有 adapter 依賴（Python packages + system dependencies）
- [ ] Go CI workflow 通過 go build + go test + golangci-lint
- [ ] Docker CI workflow 通過 build + security scan（Trivy/Docker Scout）
- [ ] 既有 Python CI 和 Vercel 部署不受影響
- [ ] Nginx 反向代理正確 routing（`/api/*` → backend、`/` → frontend）
- [ ] Docker 啟動時自動執行 alembic upgrade
- [ ] 部署文件包含 dev/staging/production 三種情境

### ChatGPT Review Gate
1. **Dockerfile 最佳實踐**：檢查 multi-stage build、最小 base image、減少 layer 數量、`.dockerignore` 是否完整
2. **安全性**：檢查 Docker image 是否以非 root 使用者執行；檢查 Trivy/Docker Scout 掃描結果
3. **CI pipeline 效率**：檢查 Go build cache 設定；檢查 Docker layer cache 最佳化
4. **依賴啟動順序**：檢查 docker-compose depends_on + healthcheck 是否正確控制啟動順序（DB → backend → frontend）
5. **環境隔離**：檢查 dev/staging/production 三套設定是否正確隔離 secrets 和 config

### Merge Gate
1. Go CI workflow 通過（build + test + lint）
2. Docker CI workflow 通過（build + scan）
3. Python CI 與既有 CI 全部通過
4. 手動驗證：`docker-compose up` 可正常啟動且 API 回應正常
5. 程式碼審查至少 1 人 approve
6. 安全掃描無 critical 級漏洞（如有需記錄緩解措施）
7. PR 包含變更的部署架構圖示

### 下一批解鎖條件
B5 合併至 master 後，B6（前端產品化 + Service 重構）可開始。B5 提供穩定的 Docker 環境供端到端測試。

---

## Batch 6：前端產品化與 Service 重構

### 目標
強化前端使用者體驗（Tools/KnowledgeBase/Research 頁面）、統一前端 API Client、重構過大的 `treatment_plan_service.py`（58842B）為多個子 service。

### 前置依賴
- **B5（Docker + CI/CD）**：需 Docker 環境進行端到端測試
- **B3（RAG/Vector DB）**：選擇性依賴—KnowledgeBase 頁面若整合 RAG 語義搜尋，需 B3 完成；若 B3 未完成則先保留基本功能
- **既有依賴**：前端既有頁面與元件（直接複用）

### 交付內容
**檔案範圍（20 files）**：
| 區域 | 檔案 | 類型 |
|------|------|------|
| 統一 API Client | `src/frontend/src/api/client.ts`（axios instance + interceptor） | 新建 |
| TypeScript 型別 | `src/frontend/src/api/types.ts`（對應後端 Pydantic model） | 新建 |
| API Client 遷移 | `src/frontend/src/api/clinical_decision.ts`、`treatmentPlan.ts`、`workbench.ts` 改用統一 client | 修改 |
| RAG API Client | `src/frontend/src/api/rag.ts`（若 B3 已建立） | 新建 |
| 頁面強化 | `src/frontend/src/pages/Tools.tsx`、`KnowledgeBase.tsx`、`Research.tsx` | 修改 |
| 通用元件 | `src/frontend/src/components/ErrorBoundary.tsx`（統一錯誤邊界）、`LoadingState.tsx`（統一載入狀態） | 新建 |
| 統一 Hook | `src/frontend/src/hooks/useApi.ts`（loading/error/data 狀態管理） | 新建 |
| Service 拆分 | `src/backend/services/treatment_plan/__init__.py`、`service.py`、`phase_service.py`、`monitoring_service.py`、`safety_service.py` | 新建 |
| Service Facade | `src/backend/services/treatment_plan_service.py`（保留為 façade pattern） | 修改 |
| 測試 | `tests/unit/services/test_treatment_plan_service.py`（拆分後測試）、`tests/frontend/test_tools_page.py` | 新增/修改 |

### 驗收標準
- [ ] 所有前端 API 呼叫使用統一 axios instance（攔截器統一處理 auth/error/logging）
- [ ] Tools.tsx 頁面功能完整（不低於 Dashboard/Workbench 的功能密度）
- [ ] KnowledgeBase.tsx 整合 RAG 語義搜尋（若 B3 完成）或保留基本關鍵字搜尋
- [ ] Research.tsx 頁面顯示研究相關功能入口與查詢介面
- [ ] `treatment_plan_service.py` 拆分為 ≤ 4 個子 service，每個 ≤ 20000 bytes
- [ ] 拆分後的 façade 保持向後相容（所有既有端點不受影響）
- [ ] 前端 error handling 統一顯示 toast/alert
- [ ] 前端 loading state 統一使用 Skeleton/Spinner
- [ ] 所有前端測試通過（regression）
- [ ] 所有既有後端測試通過（regression）

### ChatGPT Review Gate
1. **API Client 設計**：檢查 interceptor 鏈順序（auth → logging → error handling）；確認 token refresh 邏輯正確
2. **Service 拆分邊界**：檢查新拆分的子 service 職責是否單一、耦合度是否適當；確認 facade pattern 是否完整委託
3. **前端元件設計**：檢查 ErrorBoundary 與 LoadingState 是否遵循既有 design system；檢查 props interface 是否完整
4. **向後相容性**：確認拆分後的 service facade 所有公用方法簽名相同；確認前端 API client 遷移無遺漏端點
5. **測試策略**：檢查拆分後的 service 測試是否涵蓋所有子 service 的核心邏輯

### Merge Gate
1. Python CI + Frontend CI 全部通過
2. 所有 regression test 通過（~99 backend + ~14 frontend）
3. Service 拆分後 coverage 不低於拆分前
4. 前端 build 無 error / warning
5. 程式碼審查至少 1 人 approve（Service 拆分需架構師 review）
6. PR 包含「Service 拆分映射表」（舊 method → 新 service 對應）

### 下一批解鎖條件
B6 合併至 master 後，Phase 4 全部 Batch 完成。

---

# Gate 0：Phase 4 規劃完成 ✅

Phase 4 所有的 Batch（B1~B6）均已定義完成，依賴關係明確，Gate 條件完整。

## Phase 4 整體 Gate 檢查清單

| Gate | 條件 | 來源 |
|------|------|------|
| **G1：FHIR 互通 Gate** | FHIR R4 API 可供外部 EHR 系統呼叫；所有核心資源端點可正常 Read/Search；CapabilityStatement 回傳有效 | B1 |
| **G2：外部證據 Gate** | 8 個外部 adapter 真實連接；`GET /api/v1/adapters/status` 回傳全部 configured | B2 |
| **G3：語義檢索 Gate** | Embedding pipeline 完成索引；RAG API 可檢索；KnowledgeBase 可語義搜尋 | B3 |
| **G4：基礎設施與監控 Gate** | Prometheus metrics + OpenTelemetry tracing + Background Jobs（ARQ + Redis）；Grafana 儀表板顯示核心指標與 job queue depth；`POST /api/v1/jobs` 可提交 job | B4 |
| **G5：部署 Gate** | Docker Compose 一鍵啟動；所有 CI pipeline 通過 | B5 |
| **G6：程式碼品質 Gate** | Service 拆分完成；前端無硬編碼 fetch；統一 error/loading 處理 | B6 |
| **G7：回歸 Gate** | 所有既有測試（~99 Python + ~35 Go + ~14 Frontend）通過 | 全部 |

## Phase 4 退出條件

完成以上所有 Gate 後，系統可進入 Phase 5（Medical AI Platform）：
- ML Model Training Pipeline 啟動（Phase 5 範疇）
- HL7/DICOM/PACS 整合開始（Phase 5 範疇）
- Multi-specialty Platform 化設計（Phase 5 範疇）
- Microservices 可行性評估（Phase 5 範疇）

---

# Phase 5：Medical AI Platform

Phase 5 將以 Oncology（精準腫瘤學）為主的系統，提煉為多專科 Medical AI Platform，支援 Cardiology、Neurology、Radiology 等專科模組的插件式擴充。

**啟動 Gate**：Phase 4 全部 7 個 Gate（G1~G7）通過。

---

## Batch 1：Platform Core

### 目標
建立 Medical AI Platform 的核心骨架，包括 Specialty Registry、Agent Registry、Workflow Registry、EvidenceSource Registry、RuleSet Registry 以及 PlatformContainer DI 框架，使後續專科模組可透過 Registry 動態註冊。

### 前置依賴
- **Phase 4 全部完成**（G1~G7 通過）
- **既有依賴**：既有 oncologymodule 作為第一個被自動註冊的 built-in specialty
- **技術依賴**：Python DI 框架（依既有 FastAPI Depends 擴充）

### 交付內容
**檔案範圍（15-20 files）**：
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
| Platform API | `src/backend/api/v1/platform.py`（health/version/specialties 端點） | 新建 |
| Migration | `migrations/versions/026_platform_registry_tables.py` | 新建 |
| 既有修改 | `src/backend/main.py`（初始化 PlatformContainer + Registry 掃描） | 修改 |
| 既有修改 | `src/backend/domain/enums.py`（SpecialtyType 移至 platform） | 修改 |
| 測試 | `tests/unit/platform/test_*.py`（各 Registry unit tests + contract tests） | 新建 |

### 驗收標準
- [ ] 系統啟動時自動掃描並註冊 oncology 模組為 built-in specialty
- [ ] API `GET /api/v1/platform/specialties` 回傳 oncology 模組資訊（id、version、display_name）
- [ ] API `GET /api/v1/platform/health` 回傳各 registry 健康狀態
- [ ] AgentRegistry 可依 specialty_id 查詢對應的 agent 集合
- [ ] WorkflowRegistry 可註冊/查詢 specialty 專屬 workflow
- [ ] 既有 oncology 功能完全不受影響（regression test pass）
- [ ] 所有 registry unit tests 與 contract tests 通過

### ChatGPT Review Gate
1. **Registry 介面設計**：檢查各 Registry 的抽象介面是否一致（register/unregister/get/list）；確認 lifecycle hook（load/start/stop/unload）完整
2. **DI 注入正確性**：檢查 PlatformContainer 是否正確管理 singleton vs. scoped 依賴；確認無循環依賴
3. **Oncology 自動註冊**：檢查 startup 時如何掃描並註冊既有 oncology 模組；確認註冊後不影響既有功能
4. **錯誤處理**：檢查 specialty 註冊失敗時的 graceful degradation；確認 registry 可處理重複註冊
5. **測試覆蓋**：確認每個 registry 至少有 register、get、list、unregister 四個操作測試

### Merge Gate
1. Python CI（unit test + lint）全部通過
2. 所有 registry unit tests 與 contract tests 通過
3. 既有 regression test 全部通過（~99 + ~35 + ~14）
4. 程式碼審查至少 1 人 approve（架構師必須參與）
5. SAST 掃描無 blocking 發現
6. PR 包含 platform package 的 API 文件

### 下一批解鎖條件
B1 合併至 master 後，Batch 2（Specialty Contract + Cardiology）、Batch 3（Oncology 抽象化）、Batch 4（KG Namespace + Terminology）可同時啟動（彼此部分並行）。

---

## Batch 2：Specialty Module Contract + Cardiology Sample

### 目標
定義 Specialty Module Contract（SpecialtyBase 介面、模版目錄 .template/），並實作第一個非 oncology 樣板模組：Cardiology Module。

### 前置依賴
- **B1（Platform Core）**：需要 SpecialtyRegistry 與 AgentRegistry 基礎
- **外部依賴**：ICD-10 心臟科編碼、LOINC 心臟檢驗編碼
- **領域依賴**：Cardiology 臨床知識（ACC/AHA guidelines、心臟疾病分類）

### 交付內容
**檔案範圍（20-25 files）**：
| 區域 | 檔案 | 類型 |
|------|------|------|
| SpecialtyBase | `src/backend/specialties/base.py`（AbstractBaseSpecialty） | 新建 |
| 模版目錄 | `src/backend/specialties/.template/__init__.py`、`manifest.json`、`config.py`、`models.py` | 新建 |
| Cardiology Module | `src/backend/specialties/cardiology/__init__.py`（含 SPECIALTY_MANIFEST） | 新建 |
| Cardiology Domain | `src/backend/specialties/cardiology/models.py`（CardioCaseModel、ECGModel、RiskScore 等） | 新建 |
| Cardiology Agent | `src/backend/specialties/cardiology/agents/diagnosis_agent.py`、`guideline_agent.py`、`risk_agent.py` | 新建 |
| Cardiology Workflow | `src/backend/specialties/cardiology/workflows/chest_pain_assessment.py` | 新建 |
| Cardiology Terminology | `src/backend/specialties/cardiology/terminology/icd10_cardiac.json`、`loinc_cardiac.json` | 新建 |
| Terminology Service | `src/backend/platform/terminology/service.py`、`models.py`、`repository.py` | 新建 |
| Cardiology Tests | `src/backend/specialties/cardiology/tests/` | 新建 |
| Migration | `migrations/specialties/cardiology/001_cardiology_base.py` | 新建 |

### 驗收標準
- [ ] Cardiology module 可獨立註冊/啟動/停止（透過 SpecialtyRegistry）
- [ ] `POST /api/v1/workflows/cardiology.chest_pain/execute` 可執行胸痛評估工作流
- [ ] `GET /api/v1/terminology/normalize?code=I21.0&system=ICD-10` 正確映射心臟科 code
- [ ] Cardiology diagnosis agent 可分析 CardioCaseModel 並回傳有意義的意見（opinion）
- [ ] 所有 Cardiology 專屬測試通過
- [ ] .template/ 目錄可供第三方開發者複製作為新 specialty 起點

### ChatGPT Review Gate
1. **Contract 完整性**：檢查 SpecialtyBase 是否定義了 specialty 模組必須實作的所有方法；檢查 manifest.json 欄位是否完整（id/version/entry_point/dependencies/config_schema）
2. **Cardiology Agent 品質**：檢查診斷邏輯是否基於 ACC/AHA guideline；檢查 guideline version 註明
3. **Terminology mapping 正確性**：檢查 ICD-10 cardiac codes 映射是否正確（至少涵蓋常見 heart disease codes）
4. **Workflow 設計**：檢查 chest_pain_assessment workflow 步驟是否反映真實臨床路徑
5. **模版可用性**：確認開發者複製 .template/ 後，修改 manifest 即可註冊為新 specialty

### Merge Gate
1. Python CI 全部通過
2. 所有 Cardiology module tests 通過
3. 既有 oncology regression test 通過
4. 程式碼審查至少 1 人 approve（含 domain expert review）
5. SAST 無 blocking 發現
6. PR 包含 Cardiology module 的使用文件

### 下一批解鎖條件
B2 合併至 master 後，B5（Tenant Isolation）與 B6（Neurology + Radiology）的前置條件部分滿足。

---

## Batch 3：Oncology 抽象化

### 目標
逐步提取 Oncology 模組中的通用介面（AbstractCase、AbstractConsensus），同時保持既有 Oncology 功能的完全向下相容，為跨專科共用做準備。

### 前置依賴
- **B1（Platform Core）**：需要 SpecialtyRegistry、AgentRegistry 基礎
- **B2（TerminologyService）**：B3.3（ClinicalContext 擴充 diagnosis_code）部分依賴 B2.9 TerminologyService

### 交付內容
**檔案範圍（10-15 files）**：
| 區域 | 檔案 | 類型 |
|------|------|------|
| AbstractCase | `src/backend/domain/abstract_case.py`（通用 case 介面） | 新建 |
| AbstractConsensus | `src/backend/domain/abstract_consensus.py`（通用 consensus 介面） | 新建 |
| CancerCase 修改 | `src/backend/domain/cancer_case.py`（繼承 AbstractCase） | 修改 |
| TumorBoard 修改 | `src/backend/domain/tumor_board.py`（提取 AbstractConsensus） | 修改 |
| ClinicalContext 擴充 | `src/backend/clinical/models.py`（加 diagnosis_code、diagnosis_system、specialty_id） | 修改 |
| Agent 改造 | `src/backend/agents/base.py`（加 SpecialtyAgentMixin）、`src/backend/agents/diagnosis_agent.py` 等（移除 cancer-specific hardcode） | 修改 |
| Rule 提取 | `src/backend/clinical/treatment_plan_rules.py`（oncology-specific 邏輯提取至 plugin） | 修改 |
| Scorer 提取 | `src/backend/ranking/scorers.py`（oncology mapping 提取） | 修改 |
| Orchestrator 改造 | `src/backend/agents/orchestrator.py`（使用 AgentRegistry 動態選擇 agent） | 修改 |
| 回歸測試 | `tests/regression/test_oncology_compatibility.py` | 新建 |

### 驗收標準
- [ ] Oncology module 仍可正常運作（regression test suite pass）
- [ ] CancerCaseModel 仍可正常 CRUD（繼承 AbstractCase，所有既有 API 端點不變）
- [ ] ClinicalContext.cancer_type 仍可讀取（作為 diagnosis_code 的 alias 保留）
- [ ] Agent selection 可正確選擇 oncology agent（Orchestrator 依 specialty 路由）
- [ ] 無任何 breaking change（所有既有端點、model、API 回應格式不變）
- [ ] `CancerTypeEnum` 保留為 built-in oncology 實例

### ChatGPT Review Gate
1. **向後相容性**：檢查 AbstractCase 引入後，CancerCase 的所有公有方法簽名是否完全一致；檢查 `cancer_type` alias 是否正確委託到 `diagnosis_code`
2. **抽象化邊界**：檢查 AbstractCase 是否僅提取真正通用的欄位（patient_id、diagnosis_code、stage、status），而非過度抽象
3. **Agent 改造影響**：確認移除 cancer-specific hardcode 後，agent 的行為邏輯不變（透過註冊的 specialty data 載入）
4. **測試策略**：確認 B3.9 回歸測試涵蓋所有 oncology 核心 API 端點
5. **Feature Flag**：若使用 feature toggle，確認 toggle 關閉時行為完全回退至既有邏輯

### Merge Gate
1. Python CI 全部通過
2. **強制**：完整 regression test suite 通過（含新加的 oncology 相容性測試）
3. 程式碼審查至少 2 人 approve（架構師 + 領域專家）
4. SAST 無 blocking 發現
5. PR 需包含「向後相容性檢查清單」
6. 不得同時合併其他可能衝突的 PR

### 下一批解鎖條件
B3 合併至 master 後，B5（Tenant Isolation）可等待 B3 的 ClinicalContext 擴充。

---

## Batch 4：Knowledge Graph Namespace + Terminology

### 目標
擴充 KnowGraphGo 支援 Namespace 隔離，使不同專科的知識圖譜資料可獨立存放與查詢；完善 Terminology Service 支援跨專科術語映射。

### 前置依賴
- **B1（Platform Core）**：需要 Platform 基礎
- **B2（TerminologyService）**：B4.3 依賴 B2.9 的 TerminologyService 實作
- **外部依賴**：ICD-10、SNOMED CT、LOINC、RxNorm 術語資料集

### 交付內容
**檔案範圍（10-15 files）**：
| 區域 | 檔案 | 類型 |
|------|------|------|
| NamespacedStore | `KnowGraphGo/graph/store/namespace.go`（namespace-aware store wraper） | 新建 |
| Namespace Test | `KnowGraphGo/graph/store/namespace_test.go` | 新建 |
| KG API 擴充 | `src/backend/knowledge/api.py`（支援 namespace 參數查詢） | 修改 |
| Terminology Service | `src/backend/platform/terminology/service.py`（完成 cache + bulk lookup） | 修改 |
| Terminology Mappings | `src/backend/platform/terminology/mappings/icd10.json`、`snomed.json`、`loinc.json`、`rxnorm.json` | 新建 |
| Terminology CLI | `scripts/terminology/import_mappings.py`（匯入 CLI 工具） | 新建 |
| Oncology Namespace 遷移 | `scripts/migrations/migrate_kg_namespace.py`（現有資料加 prefix） | 新建 |
| 既有修改 | KnowGraphGo 其他 store 檔案（必要的最小改動） | 修改 |
| Go CI | `.github/workflows/go-ci.yml`（若 Phase 4 未建） | 新建 |

### 驗收標準
- [ ] KnowGraphGo 支援 `WithNamespace(ns)` 查詢過濾
- [ ] 跨 namespace 查詢正確路由至對應 namespace 的 store
- [ ] TerminologyService 可解析 ICD-10 / SNOMED / LOINC codes（含 cache）
- [ ] Bulk lookup API 支援一次查詢多個 code
- [ ] 現有 oncology 知識圖譜資料遷移至 oncology namespace（加 prefix）
- [ ] Go CI 包含 go build + go test + golangci-lint（若 Phase 4 未建）
- [ ] 所有既有 Go test 通過

### ChatGPT Review Gate
1. **Namespace 設計**：檢查 namespace 隔離是邏輯隔離（prefix/suffix）還是實體隔離（separate store）；確認隔離方案不影響跨 namespace 查詢效能
2. **KnowGraphGo 改動最小化**：確認僅新增 namespace.go，最小修改既有 store 程式碼（不修改核心 graph 演算法）
3. **Terminology Mapping 正確性**：抽樣檢查 ICD-10 心臟科編碼、SNOMED 神經科編碼的映射正確性
4. **效能考量**：檢查 namespace prefix 查詢是否使用 index；檢查 terminology cache 策略（TTL、LRU）
5. **Migration 安全性**：檢查 namespace 遷移腳本是否包含 dry-run 模式、rollback 機制

### Merge Gate
1. Go CI pipeline 通過（build + test + lint）
2. Python CI 全部通過
3. 所有既有 Go test + 新 namespace test 通過
4. 既有 regression test 通過
5. 程式碼審查至少 1 人 approve
6. Go 專案的 lint 與 formatting 檢查通過

### 下一批解鎖條件
B4 合併至 master 後，B5（Tenant Isolation）與 B6（Neurology + Radiology）可獲取 namespace 與 terminology 支援。

---

## Batch 5：Tenant Isolation + API Versioning

### 目標
引入 Multi-tenant 架構支援多家醫院/租戶資料隔離，並建立 API 版本管理機制（v1/v2 共存），確保 Phase 6 可安全擴充端點。

### 前置依賴
- **B1（Platform Core）**：需要 Platform 基礎設施
- **B2（Specialty Contract）**：Tenant-aware 的 specialty 配置需要 B2 的註冊機制
- **B3（Oncology 抽象化）**：ClinicalContext.specialty_id 欄位
- **B4（Terminology）**：Tenant-specific terminology mapping

### 交付內容
**檔案範圍（12-18 files）**：
| 區域 | 檔案 | 類型 |
|------|------|------|
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
| Migration | `migrations/versions/027_tenant_id_add.py` | 新建 |
| 測試 | `tests/unit/platform/test_tenant.py`、`tests/integration/test_tenant_isolation.py` | 新建 |

### 驗收標準
- [ ] Multi-tenant 可正常運作：至少 2 個 tenant 各自登入後僅能看到自己的資料
- [ ] 無 tenant 可透過 API 存取另一 tenant 資料（security test 驗證）
- [ ] Tenant config 可動態 overlay（specified tenant 可覆蓋 platform default config）
- [ ] API 端點同時支援 v1（不變）與 v2（新增 tenant-aware path）
- [ ] Tenant admin API 需有權限控制（僅 super admin 可操作）
- [ ] 所有既有 API v1 端點行為不變

### ChatGPT Review Gate
1. **Tenant 隔離策略**：檢查 tenant_id 過濾是否應用於所有 repository 查詢；檢查是否有遺漏的 SQL query 未加 tenant_id 條件
2. **安全性**：檢查 JWT tenant claims 是否可被竄改（signature verification）；檢查 tenant switching 防止水平越權
3. **API 版本策略**：檢查 v1/v2 router 是否完全隔離；確認 v2 不影響 v1 行為
4. **Migration 影響**：檢查既有資料表加 tenant_id 的 migration 是否設定合理預設值（對應既有資料設為 default tenant）
5. **測試完整性**：確認 tenant isolation test 包含正反案例（應存取成功 vs 應拒絕存取）

### Merge Gate
1. Python CI 全部通過
2. Tenant isolation security test 全部通過（含穿透測試）
3. 既有 regression test 全部通過
4. 程式碼審查至少 2 人 approve（含 security review）
5. SAST + DAST 掃描通過
6. PR 包含 tenant 管理的使用說明

### 下一批解鎖條件
B5 合併至 master 後，B6（Neurology + Radiology）可取得 multi-tenant 基礎設施。

---

## Batch 6：Neurology + Radiology Sample Modules

### 目標
基於完成的 Platform 快速建立 Neurology 與 Radiology 樣板模組，驗證 Platform 的跨專科能力，並展示 Cardiology/Neurology/Radiology 三專科同時運作。

### 前置依賴
- **B2（Specialty Contract + Cardiology）**：特殊模組建置方法論與模版
- **B4（KG Namespace + Terminology）**：跨專科術語映射與 namespace 隔離
- **B5（Tenant Isolation）**：multi-tenant 基礎設施
- **Phase 4 FHIR R4（B1）**：Radiology 模組需 FHIR 資源互通
- **Phase 4 DICOM 基礎（若 Phase 4 有完成）**：Radiology 影像整合

### 交付內容
**檔案範圍（25-30 files）**：
| 區域 | 檔案 | 類型 |
|------|------|------|
| Neurology Module | `src/backend/specialties/neurology/`（manifest、models、agents、workflows、terminology、tests） | 新建 |
| Neurology Domain | NeuroCaseModel、LesionModel、MSAssessment、StrokeScale | 新建 |
| Neurology Agents | DiagnosisAgent（MS 診斷 criteria）、ImagingAgent（MRI lesion）、StrokeAgent（NIHSS） | 新建 |
| Neurology Workflow | 多發性硬化症診斷流程、急性中風評估流程 | 新建 |
| Neurology Terminology | ICD-10 G00-G99、SNOMED neuro concepts | 新建 |
| Radiology Module | `src/backend/specialties/radiology/`（基礎結構 + DICOM study model） | 新建 |
| Radiology Domain | RadiologyStudy、ImageFinding、AIFinding、ReportTemplate | 新建 |
| Radiology Agent | ImageAnalysisAgent（stub）、ReportAgent（stub） | 新建 |
| Radiology Workflow | 影像上傳 → AI 推論 → 放射師審閱 → 報告產出 | 新建 |
| Cross-specialty 測試 | `tests/integration/test_cross_specialty.py` | 新建 |

### 驗收標準
- [ ] Neurology module 可獨立註冊/啟動/停止，DiagnosisAgent 可分析 NeuroCaseModel
- [ ] Radiology module 可接收 DICOM study 或 FHIR DiagnosticReport 作為輸入
- [ ] 跨專科 Workflow 可查詢（例如 Cardiology 轉診至 Radiology）
- [ ] 全部 3 個 sample specialty（Cardiology + Neurology + Radiology）在 production 配置中同時啟用
- [ ] 跨專科 terminology lookup 可正確運作
- [ ] 所有測試通過

### ChatGPT Review Gate
1. **Module 結構一致性**：檢查 Neurology/Radiology 的模組結構是否遵循 .template/ 規範（manifest、config、models、agents、workflows）
2. **Neurology Agent 正確性**：檢查 MS 診斷 criteria 是否基於 McDonald criteria；檢查 NIHSS scoring 邏輯是否正確
3. **Radiology DICOM 整合**：檢查 DICOM study model 是否涵蓋必要欄位（SOP Class UID、StudyInstanceUID、Series 等）
4. **Cross-specialty 路由**：檢查跨專科工作流的 routing 邏輯是否正確（specialty_id → 對應 workflow registry）
5. **運作穩定性**：確認 3 個 specialty 同時載入時無註冊衝突或循環依賴

### Merge Gate
1. Python CI 全部通過
2. 所有 Neurology + Radiology module tests 通過
3. 既有 oncology + cardiology regression test 通過
4. Cross-specialty integration test 通過
5. 程式碼審查至少 1 人 approve（Neurology 需 domain expert）
6. SAST 無 blocking 發現
7. PR 包含各 specialty 的啟用設定說明

### 下一批解鎖條件
B6 合併至 master 後，B7（文件 + 驗收）可開始。

---

## Batch 7：文件、遷移指南、最終驗收

### 目標
完成 Phase 5 開發者文件、API 文件更新、從單一 Oncology 遷移至 Multi-Specialty 的指南、效能測試與安全審查，並進行最終驗收測試。

### 前置依賴
- **B6（Neurology + Radiology）**：需所有 sample specialty 完成
- **全部 Phase 5 Batch**：驗收測試需基於完整系統

### 交付內容
**檔案範圍（8-12 files）**：
| 區域 | 檔案 | 類型 |
|------|------|------|
| 開發者文件 | `docs/platform/developer-guide.md`（如何建立新 Specialty） | 新建 |
| API 文件 | `docs/api/openapi-v2.yaml`（v2 API 規格） | 新建 |
| 遷移指南 | `docs/platform/migration-guide.md`（Oncology-only → Multi-Specialty） | 新建 |
| 效能報告 | `docs/platform/performance-report.md`（multi-tenant + multi-specialty） | 新建 |
| 安全審查 | `docs/platform/security-review.md`（tenant isolation + specialty isolation） | 新建 |
| 測試報告 | `tests/reports/phase5-test-report.md` | 新建 |
| 既有文件更新 | `README.md`（更新架構描述）、`docs/architecture/overview.md` | 修改 |

### 驗收標準
- [ ] 開發者文件涵蓋：建立新 Specialty 的完整步驟（複製 .template/ → 修改 manifest → 實作 agents/workflows → 註冊）
- [ ] API 文件完整（含 v1 + v2 端點）
- [ ] 遷移指南說明既有 oncology 使用者如何無痛過渡
- [ ] 效能測試報告包含 multi-tenant 與 multi-specialty 情境
- [ ] 安全審查確認 tenant isolation 無漏洞
- [ ] 所有 Phase 5 強制驗收標準（AC1~AC9）通過

### ChatGPT Review Gate
1. **文件完整性**：檢查開發者文件是否涵蓋 registry 註冊、agent 開發、workflow 定義、terminology 映射等核心概念
2. **API 文件正確性**：檢查 OpenAPI spec 與實際端點行為一致（request/response schema、status code）
3. **遷移指南實用性**：確認指南包含完整的檢查清單、常見問題、rollback 程序
4. **安全審查完整性**：確認 tenant isolation 測試案例涵蓋所有存取路徑（API、database、cache、queue）
5. **測試覆蓋**：確認最終測試報告顯示 coverage ≥ 80%

### Merge Gate
1. 所有 Python CI + Go CI 通過
2. 完整 regression test suite 通過
3. 效能測試結果符合 SLO（如：P99 latency < 500ms under 100 concurrent requests）
4. 安全審查簽署通過
5. 程式碼審查至少 1 人 approve
6. 所有文件格式檢查通過（markdown lint）

### 下一批解鎖條件
B7 合併至 master 後，Phase 5 全部完成。

---

## Phase 5 整體驗收標準

### 強制標準（Must-Have）

| # | 標準 | 驗證方式 | 對應 Batch |
|---|------|---------|-----------|
| AC1 | Oncology 模組完全不受影響 | 全部現有 test suite pass | B3 |
| AC2 | 至少 1 個非 oncology specialty（cardiology）可完整運作 | E2E test | B2 |
| AC3 | Registry 可正確註冊/啟動/停止 specialty | API test | B1 |
| AC4 | Agent selection 依 specialty 正確路由 | Integration test | B3 |
| AC5 | Knowledge Graph 支援 namespace 隔離 | Go test | B4 |
| AC6 | Terminology Service 可正確映射 ICD-10/SNOMED | Unit test | B2/B4 |
| AC7 | Multi-tenant 資料隔離 | Security test | B5 |
| AC8 | API 向下相容（v1 端點不改） | Regression test | B5 |
| AC9 | 所有 Batch 測試覆蓋率 ≥ 80% | Coverage report | B7 |

### 期望標準（Should-Have）

| # | 標準 | 優先級 | 對應 Batch |
|---|------|--------|-----------|
| SC1 | Neurology module 可基本運作 | P1 | B6 |
| SC2 | Radiology module 可接收 DICOM study | P2 | B6 |
| SC3 | Cross-specialty terminology lookup | P1 | B4/B6 |
| SC4 | Platform API 版本管理（v1/v2） | P1 | B5 |
| SC5 | CI/CD 包含 Go pipeline | P1 | B4 |
| SC6 | 開發者文件完成 | P1 | B7 |

---

## 跨 Phase 依賴概要

```
Phase 4 完成度                    Phase 5 影響
─────────────────────────────────────────────────
FHIR R4 完整實作  ──────────────  B6.4 (Radiology DICOM→FHIR)
HL7/DICOM 基礎    ──────────────  B6.4 (Radiology Module)
RAG/Vector DB     ──────────────  B6.1-B6.6 (語義搜尋)
ML Model Pipeline ──────────────  B6.5 (Radiology AI Agent)
Adapters 實作     ──────────────  B2.7, B6.1 (Cardio/Neuro evidence)
Infrastructure & Observability ──  B1-B7 (非同步任務處理 + 平台監控)
Frontend 統一     ──────────────  B2-B6 (新 specialty 前端整合)
```

---

## 附錄：Batch 依賴關係一覽

```
Phase 4
═══════
B1 (FHIR R4)       ─── 無前置，與 B2/B3/B4 並行 ──→ B5
B2 (Adapters)      ─── 無前置，與 B1/B3/B4 並行 ──→ B5
B3 (RAG/Vector DB) ─── 無前置，與 B1/B2/B4 並行 ──→ B5 ──(選擇性)──→ B6
B4 (Infra & Observability) ─── 無前置，與 B1/B2/B3 並行 ──→ B5
B5 (Docker/CI/CD)  ─── 依賴 B1/B2/B3/B4 ──────────→ B6
B6 (Frontend/Re)   ─── 依賴 B5 (+B3 選擇性)

Phase 5
═══════
B1 (Platform Core) ─── 依賴 Phase 4 全部完成 ────→ B2/B3/B4
B2 (Specialty+C)   ─── 依賴 B1 ──────────────────→ B5/B6
B3 (Oncology Abs)  ─── 依賴 B1 (+B2.9 部分) ─────→ B5
B4 (KG Namespace)  ─── 依賴 B1 (+B2.9 部分) ─────→ B5/B6
B5 (Tenant+Ver)    ─── 依賴 B2/B3/B4 ─────────────→ B6
B6 (Neuro+Rad)     ─── 依賴 B2/B4/B5 (+P4 FHIR) ─→ B7
B7 (Docs+Verify)   ─── 依賴 B6
```

---

> **文件結束** — Phase 4 & Phase 5 Development Roadmap
>
> 本路線圖以 Batch 和 Gate 為單位，基於 Phase 4 Master Plan、Phase 5 Master Plan 及 Dependency Map 產出。
> 所有 Batch 的目標、依賴與驗收標準均可追溯至對應的 Master Plan 文件。
