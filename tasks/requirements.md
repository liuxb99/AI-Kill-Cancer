# AI-Kill-Cancer — Phase 3D：Clinical Knowledge Graph Adapter

Repository：
https://github.com/liuxb99/AI-Kill-Cancer

Knowledge Graph Repository：
https://github.com/liuxb99/KnowGraphGo

Branch：
master

AI-Kill-Cancer Base Commit：
437581a330444c2bdf361076437d54ff4a846a84

目前狀態：
Phase 3A：Accepted
Phase 3B：Accepted
Phase 3C：Accepted

本輪開始：
Phase 3D
Clinical Knowledge Graph Adapter

---

# 一、任務定位

本輪目標是把 AI-Kill-Cancer 已完成的臨床主鏈：
Patient → Variant → Evidence → Drug Recommendation → Clinical Decision → Specialist Opinion → Tumor Board Consensus
投影成可查詢、可追溯、可解釋的知識圖譜。

知識圖譜使用 KnowGraphGo，但必須遵守：
Postgres = 唯一 Source of Truth
KnowGraphGo = 可重建的 Knowledge Projection = 關聯查詢層 = 推理層 = Explanation 層

不得讓 KnowGraphGo 成為第二套臨床主資料庫。
不得讓 API 直接依賴圖譜才能完成核心交易。
圖譜同步失敗不得造成 Recommendation、Clinical Decision、Tumor Board Consensus 正式交易資料遺失。

# 二、本輪不做

不得開始：Treatment Plan、Medication Order、Guideline Execution、Follow-up Plan、Phase 3E、Phase 4
不得重寫：Recommendation Engine、Clinical Decision Engine、Tumor Board Consensus Engine、既有 Postgres Models、既有 Migration 017～020、既有 API Contract
不得修改 KnowGraphGo 核心 Graph Engine、Inference Engine、Store 核心
若 KnowGraphGo 缺少 Adapter 能力，只允許新增 Clinical Domain Adapter、必要的交換 DTO、必要的 import command / adapter package

# 三、執行方式

嚴格依照 AGENTS.md：
Step 0A → Step 0B → Scene Identification → Planner → Workflow → Batch Execution → Step 4b → Reviewer → Summary → Git Commit → Git Push

不要中途回報，全部完成後一次回報。

# 四、開始前必讀

## AI-Kill-Cancer 需讀取：
AGENTS.md、tasks/requirements.md
src/backend/domain/recommendation.py
src/backend/domain/clinical_decision.py
src/backend/domain/tumor_board.py
src/backend/domain/patient.py
src/backend/repositories/recommendation_repo.py
src/backend/repositories/clinical_decision_repo.py
src/backend/repositories/tumor_board_repo.py
src/backend/services/recommendation_service.py
src/backend/services/clinical_decision_service.py
src/backend/services/tumor_board_service.py
src/backend/api/v1/recommendation.py
src/backend/api/v1/clinical_decision.py
src/backend/api/v1/tumor_board_consensus.py
src/backend/clinical/calculation_trace.py
src/backend/clinical/tumor_board_engine.py
src/backend/database/session.py
src/backend/main.py
migrations/versions/017*
migrations/versions/018*
migrations/versions/019*
migrations/versions/020*
.github/workflows/ci.yml

## KnowGraphGo 需讀取：
README.md
graph/entity.go
graph/relation.go
graph/provenance.go
graph/evidence.go
graph/lifecycle.go
graph/store.go
ontology/ontology.go
ontology/schema.go
ontology/domain_adapter.go
ontology/constraint.go
service/service.go
service/mutation.go
service/query.go
service/knowledge.go
inference/engine.go
inference/rule.go
explain/explain.go
explain/model.go
export/graphdata.go
export/json.go
store/sqlite/store.go
store/sqlite/migrations.go

必須沿用 KnowGraphGo 現有 Entity、Relation、Evidence、Provenance、Ontology、DomainAdapter、GraphStore、Transaction、Import/Export、Explain、Inference，不得自己建立第二套 Graph Schema。

# 五、整合架構

採用 Transactional Outbox + Graph Projection Worker + Idempotent Upsert + Rebuildable Projection

正式流程：
AI-Kill-Cancer Service Transaction → 寫入 Domain Model → 寫入 Graph Outbox Event → 同一 Postgres Transaction Commit → Background Graph Projector → 投影到 KnowGraphGo

禁止：在 API Request 中同步呼叫 Go CLI 並等待、在 Service commit 前寫圖譜、圖譜失敗導致臨床交易 rollback、使用 fire-and-forget thread、只靠 application log 同步

# 六、Outbox Model

新增 ClinicalGraphOutboxModel

建議欄位：id, event_id, aggregate_type, aggregate_id, event_type, schema_version, payload, status, attempt_count, last_error, available_at, processed_at, created_at, updated_at

狀態至少：pending, processing, completed, failed, dead_letter

要求：event_id 唯一、aggregate_type + aggregate_id 可索引、status + available_at 可索引、payload 使用 JSON/JSONB

不得用 memory queue 作正式同步機制。

# 七、Migration 021

新增 Migration 021，建立 domain_clinical_graph_outbox 表
不得修改 017、018、019、020

Migration 必須驗證：020 → 021 upgrade、021 → 020 empty downgrade、020 → 021 re-upgrade、Indexes、Unique Constraints、JSON round-trip

若 Outbox 已有資料：有資料 → 明確拒絕 downgrade 不刪資料；空資料 → 允許 downgrade

# 八、Graph Event Types

至少支援：patient.created, patient.updated, recommendation.created, recommendation.updated, clinical_decision.created, clinical_decision.updated, tumor_board_consensus.created, tumor_board_consensus.updated

如果目前 Variant、Evidence 已有獨立正式 Model，可增加：variant.upserted, evidence.upserted

# 九、事件 Schema

建立版本化 DTO：ClinicalGraphEvent

至少包含：event_id, event_type, schema_version, aggregate_type, aggregate_id, occurred_at, correlation_id, causation_id, actor_id, payload

要求：schema_version 從 1 開始、payload 不得直接 dump 整個 SQLAlchemy __dict__、不得包含 password_hash、token、DB URL、未授權個資

Patient 資料投影必須最小化：patient_id, display_name 或 pseudonym, sex, age_range, diagnosis/cancer type

# 十、Clinical Graph Ontology

在 KnowGraphGo 新增 clinical Namespace 或 Domain Adapter。

Entity Kinds：patient, variant, gene, cancer_type, evidence, publication, drug, recommendation, clinical_decision, specialist_opinion, specialty, tumor_board_consensus, contraindication, guideline

本輪至少真正實作：patient, recommendation, clinical_decision, specialist_opinion, specialty, tumor_board_consensus, evidence, drug, variant

# 十一、Relation Kinds

至少定義：HAS_VARIANT, LOCATED_IN_GENE, SUPPORTED_BY, CONTRADICTED_BY, RECOMMENDS, FOR_PATIENT, BASED_ON, HAS_OPINION, PROVIDED_BY_SPECIALTY, DERIVED_FROM, HAS_CONTRAINDICATION, ALTERNATIVE_TO, HAS_TRACE

至少要真正投影的關係：
Patient ─HAS_VARIANT→ Variant
Recommendation ─FOR_PATIENT→ Patient
Recommendation ─SUPPORTED_BY→ Evidence
Recommendation ─RECOMMENDS→ Drug
ClinicalDecision ─BASED_ON→ Recommendation
ClinicalDecision ─FOR_PATIENT→ Patient
TumorBoardConsensus ─DERIVED_FROM→ ClinicalDecision
TumorBoardConsensus ─HAS_OPINION→ SpecialistOpinion
SpecialistOpinion ─PROVIDED_BY_SPECIALTY→ Specialty
TumorBoardConsensus ─SUPPORTED_BY→ Evidence

# 十二、穩定 ID 策略

使用 deterministic key：
patient:{patient_id}, recommendation:{recommendation_id}, clinical_decision:{decision_id}, consensus:{consensus_id}, opinion:{opinion_id}, drug:{normalized_drug_name}, evidence:{evidence_id}, variant:{normalized_variant}, specialty:{specialty_name}

要求：相同 Domain Object 重跑同步 → 同一 Entity 不重複建立；相同 Relation 重跑 → 不重複建立
必須支援 At-least-once delivery、Idempotent projection

# 十三、Provenance

每個重要 Entity/Relation 都必須帶 Provenance：
source_system = AI-Kill-Cancer, source_table, source_id, event_id, schema_version, created_at, updated_at, actor_id, correlation_id

Evidence 關係還必須保存：evidence_id, evidence_level, source, citation, confidence

# 十四、AI-Kill-Cancer Outbox Repository

新增 ClinicalGraphOutboxRepository
至少提供：create, get_by_event_id, claim_pending, mark_completed, mark_failed, mark_dead_letter, list_failed

要求：Repository 不得 commit、不得 rollback
若使用多 Worker，claim 必須避免同一事件被同時處理（Postgres 使用 SELECT ... FOR UPDATE SKIP LOCKED，SQLite 測試使用相容替代）

# 十五、Outbox Service

新增 ClinicalGraphEventService
由 RecommendationService、ClinicalDecisionService、TumorBoardConsensusService 呼叫，在同一 Transaction 中建立 Outbox Event

要求：Domain Model 寫入成功 + Outbox 寫入成功 → commit
Outbox 寫入失敗 → 整個 Domain Transaction rollback
Graph Projection 執行失敗不得回滾已完成的臨床交易，只能重試 Outbox

# 十六、Graph Adapter 邊界

在 AI-Kill-Cancer 建立 ClinicalGraphClient 或 KnowGraphAdapter
Python 不得直接 import Go Library

建議採：JSONL Exchange + KnowGraphGo CLI Import
流程：Outbox Worker → 將單一 Event 轉成 GraphDelta JSON → 呼叫 knowgraph clinical apply --input - → KnowGraphGo Transaction → 回傳成功/錯誤

推薦在 KnowGraphGo 增加：cmd/knowgraph clinical apply、cmd/knowgraph clinical rebuild、cmd/knowgraph clinical verify
輸入使用 stdin，避免臨時檔案污染

禁止：拼接未轉義 shell command、把 JSON 直接放 command argument、使用 os.system
Python 使用 subprocess.run([...], input=json_bytes, shell=False, timeout=...)

# 十七、KnowGraphGo Clinical Domain Adapter

在 KnowGraphGo 新增 adapter/clinical（或符合現有專案風格的位置）
至少提供：RegisterOntology(), ValidateEvent(), MapEventToGraphDelta(), ApplyEvent(), Rebuild(), Verify()

支援 patient.created, recommendation.created, clinical_decision.created, tumor_board_consensus.created
其餘 update event 可共享 upsert 邏輯

要求：一個 Event 在單一 Graph Transaction 中完成，失敗則整個 GraphDelta rollback

# 十八、Graph Projection Worker

在 AI-Kill-Cancer 新增 ClinicalGraphProjectionWorker

單次執行流程：
claim pending events → 逐筆呼叫 Adapter → 成功 mark_completed → 失敗 attempt_count + 1 → 設定 next available_at → 超過 max attempts → dead_letter

重試間隔：1 min → 5 min → 15 min → 1 hr → 6 hr
設定集中於 GraphProjectionRetryPolicy，不得散落 magic numbers

# 十九、重建能力

必須支援完整重建：Postgres → 讀取正式 Domain Records → 產生 Graph Events/GraphDelta → 重建 KnowGraphGo Projection

建立命令：python -m src.backend.cli.clinical_graph rebuild（或沿用專案現有 CLI 架構）
功能：--patient-id, --from-date, --full, --dry-run
要求：Graph 可刪除後完整重建、不得依賴舊 Outbox Event 才能重建

# 二十、同步狀態 API

新增只讀管理 API：
GET /api/v1/clinical-graph/status
GET /api/v1/clinical-graph/failed-events
POST /api/v1/clinical-graph/retry/{event_id}

權限：只有 Admin/Researcher 或現有適當角色
一般 Viewer 不得重試事件
不得在本輪提供任意 Graph mutation API

# 二十一、Graph Query API

新增只讀查詢 API：
GET /api/v1/clinical-graph/patient/{patient_id}/thread
GET /api/v1/clinical-graph/recommendation/{recommendation_id}/explain
GET /api/v1/clinical-graph/consensus/{consensus_id}/explain

回傳至少包括：entities, relations, provenance, evidence, paths, explanation, projection_status
圖譜查不到資料時不得回傳假資料，應回傳 404 或 projection_pending

# 二十二、Digital Thread 查詢

Patient Thread 至少可還原：Patient → Recommendation → Clinical Decision → Tumor Board Consensus → Specialist Opinions
如果 Variant/Evidence/Drug 已有資料，也應包含

至少驗證一條完整路徑：
Patient → Recommendation → Clinical Decision → Tumor Board Consensus
以及：Consensus → Specialist Opinion → Specialty

# 二十三、Explain Query

必須使用 KnowGraphGo 現有 Explain 能力，不能在 Python 重新寫一套解釋引擎

至少支援：
Why was this drug recommended?
Why was this Clinical Decision produced?
Why did the Tumor Board reach this consensus?
Which evidence and opinions contributed?

回傳內容包含：path, relations, provenance, evidence citations, rule citations

# 二十四、Frontend

新增 ClinicalGraphPage，路由 /clinical-graph
功能：輸入 patient_id、顯示 Clinical Digital Thread、顯示 Entity/Relation 數量、顯示 Recommendation → Decision → Consensus 路徑、顯示 Evidence/Provenance、顯示 Projection Status

在 Recommendation Page、Clinical Decision Page、Tumor Board Consensus Page 新增「View in Knowledge Graph」連結

不得：hardcoded graph、fake nodes、sample ID
第一版可先使用 Timeline、Path cards、Expandable relation list，不做大型互動式力導向圖

# 二十五、測試要求

Event Schema Tests：serialization, schema version, sensitive field exclusion, invalid event rejection
Outbox Repository Tests：create, unique event_id, claim pending, mark completed, mark failed, dead letter, concurrent claim
Service Transaction Tests：Recommendation + Outbox same transaction, Clinical Decision + Outbox same transaction, Consensus + Outbox same transaction, Outbox failure rollback
Adapter Tests：Patient event → Entity, Recommendation event → Entities + Relations, Clinical Decision event → Relations, Consensus event → Opinions + Specialty Relations, Provenance preserved, Idempotent replay
Worker Tests：success, retry, dead letter, timeout, malformed adapter response
Rebuild Tests：empty graph, full rebuild, patient-only rebuild, repeat rebuild idempotent
Query Tests：patient thread, recommendation explain, consensus explain, projection pending, not found
Digital Thread Integration：必須真實建立 Patient → Recommendation → Clinical Decision → Tumor Board Consensus → Opinions，執行 Projector 後從 KnowGraphGo 查回完整 Graph Path
Restart Recovery：App 1 建立 Domain Data + Outbox → Shutdown → App 2 啟動 Worker → 完成 Projection → Graph Query 可讀
Frontend Tests：route, patient search, thread rendering, projection pending, error state, View in Knowledge Graph links

# 二十六、Postgres CI 與 Go CI

GitHub Actions 必須同時驗證：

AI-Kill-Cancer：Migration 021, Outbox transaction, Worker, Restart recovery, Digital thread, Query API
KnowGraphGo：go test ./..., go vet ./..., go build ./cmd/knowgraph, Clinical Adapter tests, CLI apply tests, Idempotency tests

Cross-repository Integration：build KnowGraphGo CLI → AI-Kill-Cancer 產生 Event → CLI apply → CLI query/export → 驗證 Graph Path

不得將 Token 寫入程式或 workflow

# 二十七、失敗策略

Domain Transaction Failure：Domain Data + Outbox 全部 rollback
Graph Projection Failure：Domain Data 保留、Outbox mark_failed、後續重試
Graph Query Failure：回傳 projection_unavailable、不得影響核心 Clinical API
Dead Letter：必須保存 event_id, attempt_count, last_error, payload, created_at，不得靜默丟棄

# 二十八、安全要求

不得投影 password_hash、refresh token、access token、private keys、database credentials、完整原始病歷自由文字、未去識別化的敏感附件
Graph Export 必須支援 redacted mode
管理 API 必須受 Auth/Role 保護

# 二十九、Commit Scope

AI-Kill-Cancer Commit 只能包含：Migration 021, Outbox Model/Repository/Service, Graph Event Schema, Projection Worker, KnowGraph Adapter Client, Graph Query API, Frontend Graph Page, Tests, Workflow, Review, Summary
KnowGraphGo Commit 只能包含：Clinical Domain Adapter, Clinical Ontology, Clinical CLI commands, Adapter tests, Integration tests, Documentation

# 三十、Git 提交

AI-Kill-Cancer：feat(phase3d): add clinical knowledge graph projection
KnowGraphGo：feat(clinical): add AI-Kill-Cancer graph adapter

不得：force push、rebase master/main、混入 Phase 3E

# 三十一、Reviewer Gate

Reviewer 必須確認以下 15 項：
[ ] Postgres 是唯一 Source of Truth
[ ] Outbox 與 Domain 同 Transaction
[ ] Graph failure 不影響 Domain Transaction
[ ] Projection 可重試
[ ] Dead Letter 可查
[ ] 同 Event 重放不產生重複 Entity/Relation
[ ] Provenance 完整
[ ] Sensitive data 未投影
[ ] Patient Digital Thread 可查
[ ] Recommendation Explain 可查
[ ] Consensus Explain 可查
[ ] Graph 可完整重建
[ ] Python 未直接嵌入 Go Library
[ ] KnowGraphGo Adapter 測試全綠
[ ] Cross-repository Integration 全綠

任一項 FAIL/PARTIAL/未驗證則：滿足需求=NO、Reviewer 最高 89、Ready for Next Phase=NO
Reviewer ≥95 才可完成

# 三十二、完成後只回報

全部完成後輸出：
AI-Kill-Cancer Commit SHA
KnowGraphGo Commit SHA
AI-Kill-Cancer Files Changed
KnowGraphGo Files Changed
所有技術細節
測試結果
CI Run IDs
Reviewer Score

最終判定：
Phase 3D Clinical Knowledge Graph Adapter：PASS / PARTIAL / FAIL
Accepted：YES / NO
Ready for ChatGPT GitHub Review：YES / NO
Ready for Treatment Plan Phase：YES / NO

只有 Outbox Transaction: PASS, Idempotent Projection: PASS, Digital Thread: PASS, Explain Query: PASS, Rebuild: PASS, Cross-repository CI: PASS, Reviewer >=95 才允許 Accepted: YES 和 Ready for Treatment Plan Phase: YES

推送後停止。不要自行開始 Treatment Plan。
