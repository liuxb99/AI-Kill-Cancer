# Phase 3D：Clinical Knowledge Graph Adapter — 執行計劃

## 總體策略

採用 **Transactional Outbox + Graph Projection Worker + Idempotent Upsert + Rebuildable Projection** 模式。
AI-Kill-Cancer 負責產生事件、KnowGraphGo 負責圖譜投影。兩個倉庫獨立提交。

### 重要前提

1. **KnowGraphGo 倉庫狀態**：`https://github.com/liuxb99/KnowGraphGo` 目前返回 404（可能為私有倉庫或尚未建立）。若 clone 失敗，需先建立 KnowGraphGo 專案骨架。
2. **兩個獨立 Git Commit**：AI-Kill-Cancer 修改與 KnowGraphGo 修改分開提交。
3. **所有 Test 必須在 CI 中可重現**。
4. **Reviewer Gate ≥95 分**。

---

## Phase A：環境準備與基礎了解

### P3D-A1：Clone KnowGraphGo + 了解專案結構

| 屬性 | 內容 |
|------|------|
| **描述** | Clone KnowGraphGo 倉庫，如果不可用則建立基礎骨架。閱讀所有指定檔案，了解 Graph Entity/Relation/Ontology/Store/Adapter 等 API |
| **依賴** | 無 |
| **負責角色** | backend-dev |
| **產出檔案** | `KnowGraphGo/` (完整目錄) |
| **預計工時** | 2h |
| **返工預案** | 若倉庫不可用，依照 `requirements.md` 和推測的 API 設計建立最小 Go 專案；或向用戶請求存取權限 |

**閱讀清單**：
- README.md, go.mod
- graph/entity.go, relation.go, provenance.go, evidence.go, lifecycle.go, store.go
- ontology/ontology.go, schema.go, domain_adapter.go, constraint.go
- service/service.go, mutation.go, query.go, knowledge.go
- inference/engine.go, rule.go
- explain/explain.go, model.go
- export/graphdata.go, json.go
- store/sqlite/store.go, migrations.go
- cmd/ 目錄結構

### P3D-A2：閱讀並理解 Outbox 模式需求

| 屬性 | 內容 |
|------|------|
| **描述** | 閱讀 `tasks/requirements.md` 第 5-13 章（Outbox Model、Migration 021、Event Schema），確定欄位設計、狀態機、交易邊界 |
| **依賴** | P3D-A1 |
| **負責角色** | backend-dev |
| **產出檔案** | 無（知識儲備） |
| **預計工時** | 0.5h |
| **返工預案** | — |

### P3D-A3：確定兩專案間的整合邊界

| 屬性 | 內容 |
|------|------|
| **描述** | 確定 JSONL Exchange 協議格式：Python 端產生 `GraphDelta` JSON，透過 subprocess stdin 傳給 `knowgraph clinical apply`。確定 Entity/Relation ID 格式、Provenance 結構 |
| **依賴** | P3D-A1, P3D-A2 |
| **負責角色** | backend-dev |
| **產出檔案** | 無（設計文檔可選） |
| **預計工時** | 1h |
| **返工預案** | — |

---

## Phase B：AI-Kill-Cancer 基礎建設

### P3D-B1：ClinicalGraphOutboxModel（SQLAlchemy Model）

| 屬性 | 內容 |
|------|------|
| **描述** | 在 `src/backend/domain/` 新增 `clinical_graph_outbox.py`，定義 `ClinicalGraphOutboxModel` |
| **依賴** | P3D-A2 |
| **負責角色** | backend-dev |
| **產出檔案** | `src/backend/domain/clinical_graph_outbox.py` |
| **預計工時** | 1.5h |
| **返工預案** | 欄位不符需求時修改 column 定義 |

**欄位設計**：
```python
class ClinicalGraphOutboxModel(DBBase):
    __tablename__ = "domain_clinical_graph_outbox"

    id = Column(CompatUUID, primary_key=True, default=_uuid)
    event_id = Column(String(64), unique=True, nullable=False, index=True)
    aggregate_type = Column(String(64), nullable=False, index=True)  # patient, recommendation, clinical_decision, tumor_board_consensus
    aggregate_id = Column(String(64), nullable=False, index=True)
    event_type = Column(String(64), nullable=False)  # patient.created, recommendation.created, etc.
    schema_version = Column(Integer, nullable=False, default=1)
    payload = Column(JSON, nullable=False)
    status = Column(String(32), nullable=False, default="pending", index=True)
    attempt_count = Column(Integer, nullable=False, default=0)
    last_error = Column(Text, nullable=True)
    available_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    processed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
```

**狀態列舉**：pending, processing, completed, failed, dead_letter

**索引**：
- `event_id` UNIQUE
- `aggregate_type + aggregate_id` 複合索引
- `status + available_at` 複合索引（供 Worker claim）

### P3D-B2：Migration 021

| 屬性 | 內容 |
|------|------|
| **描述** | 新增 migration 021，建立 `domain_clinical_graph_outbox` 表 |
| **依賴** | P3D-B1 |
| **負責角色** | backend-dev |
| **產出檔案** | `migrations/versions/021_phase3d_clinical_graph_outbox.py` |
| **預計工時** | 1.5h |
| **返工預案** | 索引/欄位調整 |

**Migration 驗證**：
- 020 → 021 upgrade
- 021 → 020 empty downgrade（資料存在時拒絕）
- 020 → 021 re-upgrade
- Indexes, Unique Constraints, JSON round-trip

### P3D-B3：ClinicalGraphEvent Schema DTO

| 屬性 | 內容 |
|------|------|
| **描述** | 在 `src/backend/schemas/`（或 `src/backend/domain/`）新增版本化 DTO `ClinicalGraphEvent`，包含 event_id, event_type, schema_version, aggregate_type, aggregate_id, occurred_at, correlation_id, causation_id, actor_id, payload |
| **依賴** | P3D-A2 |
| **負責角色** | backend-dev |
| **產出檔案** | `src/backend/schemas/clinical_graph_event.py`（若目錄不存在則建立） |
| **預計工時** | 1h |
| **返工預案** | schema_version 版本化處理 |

**Payload 最小化原則**：
- Patient：只包含 patient_id, display_name/pseudonym, sex, age_range, cancer_type
- Recommendation：只包含 recommendation_id, patient_id, drug_names, status
- ClinicalDecision：只包含 decision_id, patient_id, recommendation_id, decision_type, confidence
- TumorBoardConsensus：只包含 consensus_id, patient_id, recommendation_id, clinical_decision_id, consensus_status, consensus_score, specialties

**不允許包含**：password_hash, token, private keys, DB URL, 完整原始病歷自由文字

### P3D-B4：ClinicalGraphOutboxRepository

| 屬性 | 內容 |
|------|------|
| **描述** | 在 `src/backend/repositories/` 新增 `clinical_graph_outbox_repo.py`，提供 `create`, `get_by_event_id`, `claim_pending`, `mark_completed`, `mark_failed`, `mark_dead_letter`, `list_failed` |
| **依賴** | P3D-B1 |
| **負責角色** | backend-dev |
| **產出檔案** | `src/backend/repositories/clinical_graph_outbox_repo.py` |
| **預計工時** | 2h |
| **返工預案** | 調整 claim 邏輯以支援多 Worker |

**要求**：
- Repository 不得 commit、不得 rollback
- `claim_pending` 使用 `SELECT ... FOR UPDATE SKIP LOCKED`（Postgres）/ 相容替代（SQLite）
- 接受 `max_batch_size` 參數

---

## Phase C：AI-Kill-Cancer Service 層

### P3D-C1：ClinicalGraphEventService

| 屬性 | 內容 |
|------|------|
| **描述** | 在 `src/backend/services/` 新增 `clinical_graph_event_service.py`，封裝 Outbox 建立邏輯。提供 `create_event()` 方法：根據 aggregate_type 和 event_type 自動建立 payload，然後呼叫 Repository.create() |
| **依賴** | P3D-B3, P3D-B4 |
| **負責角色** | backend-dev |
| **產出檔案** | `src/backend/services/clinical_graph_event_service.py` |
| **預計工時** | 2h |
| **返工預案** | 調整 payload 映射邏輯 |

**設計**：
```python
class ClinicalGraphEventService:
    def __init__(self, db: AsyncSession):
        self._db = db
        self._repo = ClinicalGraphOutboxRepository(db)

    async def create_event(
        self,
        aggregate_type: str,
        aggregate_id: str,
        event_type: str,
        payload: dict,
        actor_id: str | None = None,
        correlation_id: str | None = None,
        causation_id: str | None = None,
    ) -> ClinicalGraphOutboxModel:
        # 建立 event_id, 繫結 Correlation/Causation ID
        # 寫入 Outbox（在同一個 session 中）
```

### P3D-C2：注入到 RecommendationService

| 屬性 | 內容 |
|------|------|
| **描述** | 修改 `RecommendationService.__init__()` 接受可選的 `ClinicalGraphEventService`，在 `create_recommendation()` 的 `_persist_recommendation()` 成功後（commit 前）寫入 Outbox Event |
| **依賴** | P3D-C1 |
| **負責角色** | backend-dev |
| **產出檔案** | `src/backend/services/recommendation_service.py` (修改) |
| **預計工時** | 1.5h |
| **返工預案** | 若 Outbox 寫入失敗，確保整個交易 rollback |

**修改點**：
- `__init__` 加入 `graph_event_service: ClinicalGraphEventService | None = None`
- `_persist_recommendation()` 完成後、`commit()` 前：
  ```python
  if self._graph_event_service:
      await self._graph_event_service.create_event(
          aggregate_type="recommendation",
          aggregate_id=recommendation_id,
          event_type="recommendation.created",
          payload=minimal_payload,
          actor_id=user_id,
      )
  ```

### P3D-C3：注入到 ClinicalDecisionService

| 屬性 | 內容 |
|------|------|
| **描述** | 同 C2，在 `create_decision()` 中寫入 Outbox Event |
| **依賴** | P3D-C1 |
| **負責角色** | backend-dev |
| **產出檔案** | `src/backend/services/clinical_decision_service.py` (修改) |
| **預計工時** | 1h |
| **返工預案** | — |

### P3D-C4：注入到 TumorBoardConsensusService

| 屬性 | 內容 |
|------|------|
| **描述** | 同 C2，在 `create_consensus()` 中寫入 Outbox Event |
| **依賴** | P3D-C1 |
| **負責角色** | backend-dev |
| **產出檔案** | `src/backend/services/tumor_board_service.py` (修改) |
| **預計工時** | 1h |
| **返工預案** | — |

---

## Phase D：KnowGraphGo Clinical Adapter

### P3D-D1：Clinical Ontology 定義

| 屬性 | 內容 |
|------|------|
| **描述** | 在 KnowGraphGo 中建立 `adapter/clinical/ontology.go`，定義 Entity Kinds 和 Relation Kinds 常數 |
| **依賴** | P3D-A1 |
| **負責角色** | backend-dev |
| **產出檔案** | `KnowGraphGo/adapter/clinical/ontology.go` |
| **預計工時** | 1.5h |
| **返工預案** | 新增/修改 Entity/Relation Kind |

**Entity Kinds**（本輪實作）：
- `entity_kind_patient` → "patient"
- `entity_kind_recommendation` → "recommendation"
- `entity_kind_clinical_decision` → "clinical_decision"
- `entity_kind_specialist_opinion` → "specialist_opinion"
- `entity_kind_specialty` → "specialty"
- `entity_kind_tumor_board_consensus` → "tumor_board_consensus"
- `entity_kind_evidence` → "evidence"
- `entity_kind_drug` → "drug"
- `entity_kind_variant` → "variant"

**Relation Kinds**：
- `relation_kind_has_variant` → "HAS_VARIANT"
- `relation_kind_recommends` → "RECOMMENDS"
- `relation_kind_for_patient` → "FOR_PATIENT"
- `relation_kind_supported_by` → "SUPPORTED_BY"
- `relation_kind_based_on` → "BASED_ON"
- `relation_kind_has_opinion` → "HAS_OPINION"
- `relation_kind_provided_by_specialty` → "PROVIDED_BY_SPECIALTY"
- `relation_kind_derived_from` → "DERIVED_FROM"

### P3D-D2：Clinical Domain Adapter

| 屬性 | 內容 |
|------|------|
| **描述** | 建立 `adapter/clinical/adapter.go`，實現以下介面方法：`RegisterOntology()`, `ValidateEvent()`, `MapEventToGraphDelta()`, `ApplyEvent()`, `Rebuild()`, `Verify()` |
| **依賴** | P3D-D1 |
| **負責角色** | backend-dev |
| **產出檔案** | `KnowGraphGo/adapter/clinical/adapter.go` |
| **預計工時** | 4h |
| **返工預案** | 調整 Event 映射邏輯 |

**設計要點**：
- 一個 Event → 一個 Graph Transaction
- Idempotent：相同 Event 重放不產生重複 Entity/Relation
- 使用 deterministic ID：`patient:{id}`, `recommendation:{id}`, `clinical_decision:{id}`, `consensus:{id}`, `opinion:{id}`, `drug:{normalized_name}`, `evidence:{id}`, `variant:{normalized}`, `specialty:{name}`
- Provenance 每個 Entity/Relation 都帶有：source_system="AI-Kill-Cancer", source_table, source_id, event_id, schema_version, created_at, updated_at, actor_id, correlation_id

**方法實現**：
```go
// RegisterOntology 向全局 Ontology 註冊 Clinical Entity/Relation Kinds
func (a *ClinicalAdapter) RegisterOntology(reg *ontology.Registry) error

// ValidateEvent 校驗輸入 JSON 事件格式
func (a *ClinicalAdapter) ValidateEvent(raw []byte) (*ClinicalEvent, error)

// MapEventToGraphDelta 將事件轉換為 Graph 變更集合
func (a *ClinicalAdapter) MapEventToGraphDelta(event *ClinicalEvent) (*GraphDelta, error)

// ApplyEvent 在單一 Graph Transaction 中應用事件
func (a *ClinicalAdapter) ApplyEvent(store *graph.Store, event *ClinicalEvent) error

// Rebuild 從 Domain Records 重建完整 Projection
func (a *ClinicalAdapter) Rebuild(store *graph.Store, records []DomainRecord) error

// Verify 驗證 Graph State
func (a *ClinicalAdapter) Verify(store *graph.Store) (*VerificationResult, error)
```

### P3D-D3：Clinical CLI Commands

| 屬性 | 內容 |
|------|------|
| **描述** | 在 `cmd/knowgraph/` 增加 `clinical_apply.go`, `clinical_rebuild.go`, `clinical_verify.go`，支援 stdin JSONL 輸入 |
| **依賴** | P3D-D2 |
| **負責角色** | backend-dev |
| **產出檔案** | `KnowGraphGo/cmd/knowgraph/clinical_apply.go`, `clinical_rebuild.go`, `clinical_verify.go` |
| **預計工時** | 3h |
| **返工預案** | CLI 參數調整 |

**命令設計**：
```
knowgraph clinical apply --input -       # 從 stdin 讀取 JSONL Event
knowgraph clinical apply --input file.jsonl  # 從檔案讀取
knowgraph clinical rebuild --from-date 2026-01-01  # 按日期重建
knowgraph clinical rebuild --full        # 完整重建
knowgraph clinical verify                # 驗證 Graph 完整性
```

### P3D-D4：KnowGraphGo 測試

| 屬性 | 內容 |
|------|------|
| **描述** | 撰寫 KnowGraphGo Clinical Adapter 的 Go 測試：Ontology Registration, Event Validation, Event Mapping, Apply Event Idempotency, Rebuild, Verify |
| **依賴** | P3D-D2, P3D-D3 |
| **負責角色** | backend-dev |
| **產出檔案** | `KnowGraphGo/adapter/clinical/adapter_test.go`, `cli_test.go` |
| **預計工時** | 3h |
| **返工預案** | 補充邊界案例測試 |

---

## Phase E：AI-Kill-Cancer Graph Client & Worker

### P3D-E1：ClinicalGraphClient / KnowGraphAdapter

| 屬性 | 內容 |
|------|------|
| **描述** | 在 `src/backend/adapters/` 新增 `knowgraph_adapter.py`，封裝對 KnowGraphGo CLI 的 subprocess 呼叫 |
| **依賴** | P3D-D3 |
| **負責角色** | backend-dev |
| **產出檔案** | `src/backend/adapters/knowgraph_adapter.py` |
| **預計工時** | 2h |
| **返工預案** | 調整 CLI 路徑/參數 |

**安全要求**：
- 使用 `subprocess.run([...], input=json_bytes, shell=False, timeout=...)`
- 禁止拼接未轉義 shell command
- 禁止把 JSON 直接放 command argument
- 禁止使用 `os.system`

### P3D-E2：ClinicalGraphProjectionWorker

| 屬性 | 內容 |
|------|------|
| **描述** | 在 `src/backend/workers/` 新增 `graph_projection_worker.py`，實現週期性 Worker：claim pending events → call adapter → mark completed/failed |
| **依賴** | P3D-B4, P3D-E1 |
| **負責角色** | backend-dev |
| **產出檔案** | `src/backend/workers/graph_projection_worker.py` |
| **預計工時** | 3h |
| **返工預案** | 調整 Worker 啟動方式 |

**單次執行流程**：
1. `claim_pending(batch_size=10)` → 得到 events
2. 對每個 event：序列化為 JSONL → 呼叫 `knowgraph clinical apply --input -`
3. 成功 → `mark_completed(event_id)`
4. 失敗 → `mark_failed(event_id, error)` + 設定 `available_at` 根據重試策略
5. 超過 max_attempts → `mark_dead_letter(event_id)`

### P3D-E3：Retry Policy

| 屬性 | 內容 |
|------|------|
| **描述** | 在 `src/backend/workers/` 或 `src/backend/config/` 定義 `GraphProjectionRetryPolicy`，設定重試間隔和最大次數 |
| **依賴** | P3D-E2 |
| **負責角色** | backend-dev |
| **產出檔案** | `src/backend/workers/retry_policy.py`（或在 worker 中內聯） |
| **預計工時** | 0.5h |
| **返工預案** | 調整間隔/次數 |

**重試間隔**：1 min → 5 min → 15 min → 1 hr → 6 hr
**最大重試次數**：5（之後進入 dead_letter）

### P3D-E4：Rebuild CLI

| 屬性 | 內容 |
|------|------|
| **描述** | 建立 `src/backend/cli/clinical_graph.py` 模塊，支援 `python -m src.backend.cli.clinical_graph rebuild` 命令 |
| **依賴** | P3D-E1, P3D-B3 |
| **負責角色** | backend-dev |
| **產出檔案** | `src/backend/cli/__init__.py`, `src/backend/cli/clinical_graph.py` |
| **預計工時** | 2h |
| **返工預案** | 參數調整 |

**參數**：
- `--patient-id`：僅重建特定患者
- `--from-date`：從指定日期後重建
- `--full`：完整重建（清空後重建）
- `--dry-run`：僅輸出預計操作

---

## Phase F：API 層

### P3D-F1：Graph Status API

| 屬性 | 內容 |
|------|------|
| **描述** | `GET /api/v1/clinical-graph/status` 回傳 Outbox 統計（total, pending, completed, failed, dead_letter） |
| **依賴** | P3D-B4 |
| **負責角色** | backend-dev |
| **產出檔案** | `src/backend/api/v1/clinical_graph.py` |
| **預計工時** | 1h |
| **返工預案** | 調整回傳欄位 |

### P3D-F2：Failed Events API

| 屬性 | 內容 |
|------|------|
| **描述** | `GET /api/v1/clinical-graph/failed-events` 回傳失敗事件列表（含 event_id, aggregate_type, attempt_count, last_error） |
| **依賴** | P3D-B4 |
| **負責角色** | backend-dev |
| **產出檔案** | `src/backend/api/v1/clinical_graph.py` (同上) |
| **預計工時** | 0.5h |
| **返工預案** | — |

### P3D-F3：Retry API

| 屬性 | 內容 |
|------|------|
| **描述** | `POST /api/v1/clinical-graph/retry/{event_id}` 重試指定事件（將狀態改為 pending，重置 attempt_count） |
| **依賴** | P3D-B4 |
| **負責角色** | backend-dev |
| **產出檔案** | `src/backend/api/v1/clinical_graph.py` (同上) |
| **預計工時** | 0.5h |
| **返工預案** | — |

### P3D-F4：Patient Thread Query API

| 屬性 | 內容 |
|------|------|
| **描述** | `GET /api/v1/clinical-graph/patient/{patient_id}/thread` 查詢患者的完整 Digital Thread |
| **依賴** | P3D-E1 |
| **負責角色** | backend-dev |
| **產出檔案** | `src/backend/api/v1/clinical_graph.py` (同上) |
| **預計工時** | 2h |
| **返工預案** | 調整 Graph Query 格式 |

**回傳格式**：
```json
{
  "patient_id": "...",
  "entities": [...],
  "relations": [...],
  "path": {
    "patient": {...},
    "recommendations": [...],
    "clinical_decisions": [...],
    "consensuses": [...],
    "opinions": [...]
  },
  "provenance": {...},
  "projection_status": "completed|pending|unavailable"
}
```

### P3D-F5：Recommendation Explain API

| 屬性 | 內容 |
|------|------|
| **描述** | `GET /api/v1/clinical-graph/recommendation/{recommendation_id}/explain` 使用 KnowGraphGo Explain 能力查詢推薦原因 |
| **依賴** | P3D-E1 |
| **負責角色** | backend-dev |
| **產出檔案** | `src/backend/api/v1/clinical_graph.py` (同上) |
| **預計工時** | 1.5h |
| **返工預案** | 調整 Explain 回傳格式 |

### P3D-F6：Consensus Explain API

| 屬性 | 內容 |
|------|------|
| **描述** | `GET /api/v1/clinical-graph/consensus/{consensus_id}/explain` 查詢 Consensus 形成原因 |
| **依賴** | P3D-E1 |
| **負責角色** | backend-dev |
| **產出檔案** | `src/backend/api/v1/clinical_graph.py` (同上) |
| **預計工時** | 1.5h |
| **返工預案** | — |

### P3D-F7：Router 整合

| 屬性 | 內容 |
|------|------|
| **描述** | 在 `src/backend/api/v1/router.py` 中註冊 `clinical_graph_router` |
| **依賴** | P3D-F1 ~ P3D-F6 |
| **負責角色** | backend-dev |
| **產出檔案** | `src/backend/api/v1/router.py` (修改) |
| **預計工時** | 0.5h |
| **返工預案** | — |

---

## Phase G：前端

### P3D-G1：ClinicalGraphPage + 路由

| 屬性 | 內容 |
|------|------|
| **描述** | 新增 `ClinicalGraphPage` 頁面，路由 `/clinical-graph`，支援輸入 patient_id 查詢 Digital Thread |
| **依賴** | P3D-F4 |
| **負責角色** | frontend-dev |
| **產出檔案** | `src/frontend/src/pages/ClinicalGraphPage.tsx`, `src/frontend/src/api/clinical_graph.ts`, `src/frontend/src/test/ClinicalGraphPage.test.tsx` |
| **預計工時** | 3h |
| **返工預案** | 調整 UI 展示方式 |

**功能**：
- 輸入 patient_id
- 顯示 Clinical Digital Thread（Timeline 方式）
- 顯示 Entity/Relation 數量
- 顯示 Recommendation → Decision → Consensus 路徑
- 顯示 Evidence/Provenance
- 顯示 Projection Status
- Loading/Error/Pending 狀態處理

**不做**：大型互動式力導向圖。使用 Timeline + Path cards + Expandable relation list。

**路由修改**：
- `src/frontend/src/App.tsx` 加入 `<Route path="/clinical-graph" element={<ClinicalGraphPage />} />`
- 導航欄加入「知識圖譜」連結

### P3D-G2：View in Knowledge Graph 連結

| 屬性 | 內容 |
|------|------|
| **描述** | 在 Recommendation Page、Clinical Decision Page、Tumor Board Consensus Page 新增「View in Knowledge Graph」連結 |
| **依賴** | P3D-G1 |
| **負責角色** | frontend-dev |
| **產出檔案** | `src/frontend/src/pages/RecommendationPage.tsx` (修改), `src/frontend/src/pages/ClinicalDecisionPage.tsx` (修改), `src/frontend/src/pages/TumorBoardConsensusPage.tsx` (修改) |
| **預計工時** | 1h |
| **返工預案** | — |

---

## Phase H：測試

### P3D-H1：Event Schema Tests

| 屬性 | 內容 |
|------|------|
| **描述** | 測試 ClinicalGraphEvent 序列化/反序列化、schema_version、敏感欄位排除、invalid event 拒絕 |
| **依賴** | P3D-B3 |
| **負責角色** | backend-dev |
| **產出檔案** | `tests/test_clinical_graph_event.py` |
| **預計工時** | 1h |
| **返工預案** | 補充邊界案例 |

### P3D-H2：Outbox Repository Tests

| 屬性 | 內容 |
|------|------|
| **描述** | 測試 create, unique event_id, claim_pending, mark_completed, mark_failed, dead_letter, concurrent claim |
| **依賴** | P3D-B4 |
| **負責角色** | backend-dev |
| **產出檔案** | `tests/test_clinical_graph_outbox_repo.py` |
| **預計工時** | 2h |
| **返工預案** | 補充 concurrent claim 測試 |

### P3D-H3：Service Transaction Tests

| 屬性 | 內容 |
|------|------|
| **描述** | 測試 Recommendation + Outbox same transaction, ClinicalDecision + Outbox same transaction, Consensus + Outbox same transaction, Outbox failure rollback |
| **依賴** | P3D-C2, P3D-C3, P3D-C4 |
| **負責角色** | backend-dev |
| **產出檔案** | `tests/test_clinical_graph_transaction.py` |
| **預計工時** | 2h |
| **返工預案** | 補充 rollback 場景 |

### P3D-H4：Adapter Tests（KnowGraphGo）

| 屬性 | 內容 |
|------|------|
| **描述** | (已涵蓋在 P3D-D4) 測試 Patient event → Entity, Recommendation event → Entities + Relations, Clinical Decision event → Relations, Consensus event → Opinions + Specialty Relations, Provenance preserved, Idempotent replay |
| **依賴** | P3D-D4 |
| **負責角色** | backend-dev |
| **產出檔案** | `KnowGraphGo/adapter/clinical/adapter_test.go` |
| **預計工時** | 包含在 D4 |
| **返工預案** | — |

### P3D-H5：Worker Tests

| 屬性 | 內容 |
|------|------|
| **描述** | 測試 Worker success, retry, dead letter, timeout, malformed adapter response |
| **依賴** | P3D-E2 |
| **負責角色** | backend-dev |
| **產出檔案** | `tests/test_clinical_graph_worker.py` |
| **預計工時** | 2h |
| **返工預案** | 補充 timeout/malformed 場景 |

### P3D-H6：Rebuild Tests

| 屬性 | 內容 |
|------|------|
| **描述** | 測試 empty graph, full rebuild, patient-only rebuild, repeat rebuild idempotent |
| **依賴** | P3D-E4 |
| **負責角色** | backend-dev |
| **產出檔案** | `tests/test_clinical_graph_rebuild.py` |
| **預計工時** | 1.5h |
| **返工預案** | 補充 idempotent 驗證 |

### P3D-H7：Query API Tests

| 屬性 | 內容 |
|------|------|
| **描述** | 測試 patient thread, recommendation explain, consensus explain, projection pending, not found |
| **依賴** | P3D-F4, P3D-F5, P3D-F6 |
| **負責角色** | backend-dev |
| **產出檔案** | `tests/test_clinical_graph_api.py` |
| **預計工時** | 2h |
| **返工預案** | — |

### P3D-H8：Digital Thread Integration

| 屬性 | 內容 |
|------|------|
| **描述** | 真實建立 Patient → Recommendation → Clinical Decision → Tumor Board Consensus → Opinions，執行 Projector 後從 KnowGraphGo 查回完整 Graph Path |
| **依賴** | P3D-H3, P3D-H5, P3D-H7 |
| **負責角色** | backend-dev |
| **產出檔案** | `tests/test_clinical_graph_digital_thread.py` |
| **預計工時** | 3h |
| **返工預案** | 若 KnowGraphGo CLI 不可用則 mock |

### P3D-H9：Restart Recovery

| 屬性 | 內容 |
|------|------|
| **描述** | App 1 建立 Domain Data + Outbox → Shutdown → App 2 啟動 Worker → 完成 Projection → Graph Query 可讀 |
| **依賴** | P3D-E2, P3D-F4 |
| **負責角色** | backend-dev |
| **產出檔案** | `tests/test_clinical_graph_restart.py` |
| **預計工時** | 2h |
| **返工預案** | — |

### P3D-H10：Frontend Tests

| 屬性 | 內容 |
|------|------|
| **描述** | 測試 route, patient search, thread rendering, projection pending, error state, View in Knowledge Graph links |
| **依賴** | P3D-G1, P3D-G2 |
| **負責角色** | frontend-dev |
| **產出檔案** | `src/frontend/src/test/ClinicalGraphPage.test.tsx` |
| **預計工時** | 1.5h |
| **返工預案** | — |

---

## Phase I：CI 與整合

### P3D-I1：AI-Kill-Cancer CI 更新

| 屬性 | 內容 |
|------|------|
| **描述** | 更新 `.github/workflows/ci.yml`，加入 Phase 3D 測試（Migration 021, Outbox, Worker, Restart, Digital Thread, Query API） |
| **依賴** | P3D-H1 ~ P3D-H9 |
| **負責角色** | devops |
| **產出檔案** | `.github/workflows/ci.yml` (修改) |
| **預計工時** | 1.5h |
| **返工預案** | 調整 CI Job 拆分 |

### P3D-I2：KnowGraphGo CI

| 屬性 | 內容 |
|------|------|
| **描述** | 為 KnowGraphGo 建立 GitHub Actions CI（go test ./..., go vet ./..., go build ./cmd/knowgraph, Clinical Adapter tests, CLI apply tests, Idempotency tests） |
| **依賴** | P3D-D4 |
| **負責角色** | devops |
| **產出檔案** | `KnowGraphGo/.github/workflows/ci.yml` |
| **預計工時** | 1.5h |
| **返工預案** | — |

### P3D-I3：Cross-repository Integration CI

| 屬性 | 內容 |
|------|------|
| **描述** | 在 AI-Kill-Cancer CI 中增加 cross-repo job：build KnowGraphGo CLI → AI-Kill-Cancer 產生 Event → CLI apply → CLI query/export → 驗證 Graph Path |
| **依賴** | P3D-I1, P3D-I2 |
| **負責角色** | devops |
| **產出檔案** | `.github/workflows/ci.yml` (修改) |
| **預計工時** | 2h |
| **返工預案** | 若 KnowGraphGo 倉庫不可用則 skip |

---

## Phase J：收尾

### P3D-J1：Step 4b 需求回歸檢查

| 屬性 | 內容 |
|------|------|
| **描述** | 逐條核對 `tasks/requirements.md` 原始需求與實際交付成果 |
| **依賴** | 所有開發任務完成 |
| **負責角色** | doc-writer |
| **產出檔案** | `tasks/regression-check-phase3D.md` |
| **預計工時** | 1h |
| **返工預案** | 若發現缺漏 → 返工循環 |

### P3D-J2：REVIEWER 評分

| 屬性 | 內容 |
|------|------|
| **描述** | REVIEWER 評分，檢查 15 項 Reviewer Gate 條件 |
| **依賴** | P3D-J1 |
| **負責角色** | reviewer |
| **產出檔案** | `tasks/reviews/review_phase3D_0.md` |
| **預計工時** | 1.5h |
| **返工預案** | 若 <95 分 → 返工循環（最多 5 輪） |

### P3D-J3：返工循環（如需要）

| 屬性 | 內容 |
|------|------|
| **描述** | 根據 REVIEWER 評分報告修正缺失，重新評分 |
| **依賴** | P3D-J2 |
| **負責角色** | planner → backend-dev/frontend-dev → reviewer |
| **產出檔案** | 逐輪修正 |
| **預計工時** | 視缺失而定 |
| **返工預案** | 每輪增加循環計數，最多 5 輪 |

### P3D-J4：總結報告 + Git Commit & Push

| 屬性 | 內容 |
|------|------|
| **描述** | 生成總結報告 tasks/summary-report-phase3D.md，執行兩個 Git Commit |
| **依賴** | P3D-J2（或 J3 後達標） |
| **負責角色** | doc-writer |
| **產出檔案** | `tasks/summary-report-phase3D.md` |
| **預計工時** | 1h |
| **返工預案** | — |

**Commit Messages**：
- AI-Kill-Cancer：`feat(phase3d): add clinical knowledge graph projection`
- KnowGraphGo：`feat(clinical): add AI-Kill-Cancer graph adapter`

---

## 完整任務依賴圖

```
P3D-A1 → P3D-A2 → P3D-A3
                    │
P3D-B1 → P3D-B2    │
P3D-B1 → P3D-B4    │
P3D-B3 ← P3D-A2 ───┤
                    │
P3D-C1 ← P3D-B3, P3D-B4
P3D-C2 ← P3D-C1, P3D-B3 (modifies recommendation_service.py)
P3D-C3 ← P3D-C1, P3D-B3 (modifies clinical_decision_service.py)
P3D-C4 ← P3D-C1, P3D-B3 (modifies tumor_board_service.py)
                    │
P3D-D1 ← P3D-A1    │
P3D-D2 ← P3D-D1    │
P3D-D3 ← P3D-D2    │
P3D-D4 ← P3D-D2, P3D-D3
                    │
P3D-E1 ← P3D-D3
P3D-E2 ← P3D-B4, P3D-E1
P3D-E3 ← P3D-E2
P3D-E4 ← P3D-E1, P3D-B3
                    │
P3D-F1 ← P3D-B4
P3D-F2 ← P3D-B4
P3D-F3 ← P3D-B4
P3D-F4 ← P3D-E1
P3D-F5 ← P3D-E1
P3D-F6 ← P3D-E1
P3D-F7 ← P3D-F1~F6
                    │
P3D-G1 ← P3D-F4
P3D-G2 ← P3D-G1
                    │
P3D-H1 ← P3D-B3
P3D-H2 ← P3D-B4
P3D-H3 ← P3D-C2~C4
P3D-H4 ← P3D-D4
P3D-H5 ← P3D-E2
P3D-H6 ← P3D-E4
P3D-H7 ← P3D-F4~F6
P3D-H8 ← P3D-H3, P3D-H5, P3D-H7
P3D-H9 ← P3D-E2, P3D-F4
P3D-H10 ← P3D-G1, P3D-G2
                    │
P3D-I1 ← P3D-H1~H9
P3D-I2 ← P3D-D4
P3D-I3 ← P3D-I1, P3D-I2
                    │
P3D-J1 ← 全部開發完成
P3D-J2 ← P3D-J1
P3D-J3 ← P3D-J2 (<95分時)
P3D-J4 ← P3D-J2/P3D-J3
```

---

## 檔案變更清單總覽

### AI-Kill-Cancer 新增檔案
| # | 檔案路徑 | Phase |
|---|----------|-------|
| 1 | `src/backend/domain/clinical_graph_outbox.py` | B1 |
| 2 | `migrations/versions/021_phase3d_clinical_graph_outbox.py` | B2 |
| 3 | `src/backend/schemas/__init__.py` | B3 |
| 4 | `src/backend/schemas/clinical_graph_event.py` | B3 |
| 5 | `src/backend/repositories/clinical_graph_outbox_repo.py` | B4 |
| 6 | `src/backend/services/clinical_graph_event_service.py` | C1 |
| 7 | `src/backend/adapters/knowgraph_adapter.py` | E1 |
| 8 | `src/backend/workers/__init__.py` | E2 |
| 9 | `src/backend/workers/graph_projection_worker.py` | E2 |
| 10 | `src/backend/workers/retry_policy.py` | E3 |
| 11 | `src/backend/cli/__init__.py` | E4 |
| 12 | `src/backend/cli/clinical_graph.py` | E4 |
| 13 | `src/backend/api/v1/clinical_graph.py` | F1~F6 |
| 14 | `src/frontend/src/pages/ClinicalGraphPage.tsx` | G1 |
| 15 | `src/frontend/src/api/clinical_graph.ts` | G1 |
| 16 | `tests/test_clinical_graph_event.py` | H1 |
| 17 | `tests/test_clinical_graph_outbox_repo.py` | H2 |
| 18 | `tests/test_clinical_graph_transaction.py` | H3 |
| 19 | `tests/test_clinical_graph_worker.py` | H5 |
| 20 | `tests/test_clinical_graph_rebuild.py` | H6 |
| 21 | `tests/test_clinical_graph_api.py` | H7 |
| 22 | `tests/test_clinical_graph_digital_thread.py` | H8 |
| 23 | `tests/test_clinical_graph_restart.py` | H9 |
| 24 | `src/frontend/src/test/ClinicalGraphPage.test.tsx` | H10 |

### AI-Kill-Cancer 修改檔案
| # | 檔案路徑 | 修改內容 | Phase |
|---|----------|----------|-------|
| 1 | `src/backend/services/recommendation_service.py` | 注入 ClinicalGraphEventService，在 _persist_recommendation 後寫 Outbox | C2 |
| 2 | `src/backend/services/clinical_decision_service.py` | 注入 ClinicalGraphEventService，在 create_decision 後寫 Outbox | C3 |
| 3 | `src/backend/services/tumor_board_service.py` | 注入 ClinicalGraphEventService，在 create_consensus 後寫 Outbox | C4 |
| 4 | `src/backend/api/v1/router.py` | 註冊 clinical_graph_router | F7 |
| 5 | `src/frontend/src/App.tsx` | 新增 /clinical-graph 路由、導航連結 | G1 |
| 6 | `src/frontend/src/pages/RecommendationPage.tsx` | 新增「View in Knowledge Graph」連結 | G2 |
| 7 | `src/frontend/src/pages/ClinicalDecisionPage.tsx` | 新增「View in Knowledge Graph」連結 | G2 |
| 8 | `src/frontend/src/pages/TumorBoardConsensusPage.tsx` | 新增「View in Knowledge Graph」連結 | G2 |
| 9 | `.github/workflows/ci.yml` | 加入 Phase 3D 測試和 Cross-repo CI | I1, I3 |

### KnowGraphGo 新增檔案
| # | 檔案路徑 | Phase |
|---|----------|-------|
| 1 | `adapter/clinical/ontology.go` | D1 |
| 2 | `adapter/clinical/adapter.go` | D2 |
| 3 | `adapter/clinical/clinical_event.go`（Event 結構定義） | D2 |
| 4 | `adapter/clinical/graph_delta.go`（GraphDelta 結構定義） | D2 |
| 5 | `cmd/knowgraph/clinical_apply.go` | D3 |
| 6 | `cmd/knowgraph/clinical_rebuild.go` | D3 |
| 7 | `cmd/knowgraph/clinical_verify.go` | D3 |
| 8 | `adapter/clinical/adapter_test.go` | D4 |
| 9 | `.github/workflows/ci.yml` | I2 |

---

## Reviewer Gate 檢查清單（15 項）

| # | 檢查項 | 驗證方式 |
|---|--------|----------|
| 1 | Postgres 是唯一 Source of Truth | 確認所有臨床資料只存在 Postgres |
| 2 | Outbox 與 Domain 同 Transaction | 檢查 Service 中 Outbox 寫入在 commit 前 |
| 3 | Graph failure 不影響 Domain Transaction | 確認 Worker 失敗不會 rollback Domain 交易 |
| 4 | Projection 可重試 | 確認 mark_failed 後可重新 claim |
| 5 | Dead Letter 可查 | 確認 list_failed 可列出 dead_letter 事件 |
| 6 | 同 Event 重放不產生重複 Entity/Relation | 確認 Adapter 使用 Idempotent Upsert |
| 7 | Provenance 完整 | 確認每個 Entity/Relation 都有 Provenance |
| 8 | Sensitive data 未投影 | 確認 Payload 不包含敏感欄位 |
| 9 | Patient Digital Thread 可查 | 確認 GET /patient/{id}/thread 回傳完整路徑 |
| 10 | Recommendation Explain 可查 | 確認 GET /recommendation/{id}/explain 可用 |
| 11 | Consensus Explain 可查 | 確認 GET /consensus/{id}/explain 可用 |
| 12 | Graph 可完整重建 | 確認 rebuild CLI 可清空後重建 |
| 13 | Python 未直接嵌入 Go Library | 確認只透過 subprocess CLI 呼叫 |
| 14 | KnowGraphGo Adapter 測試全綠 | 確認 go test ./... 通過 |
| 15 | Cross-repository Integration 全綠 | 確認 CI Job 中整合測試通過 |

---

## 風險與緩解

| 風險 | 機率 | 影響 | 緩解措施 |
|------|------|------|----------|
| KnowGraphGo 倉庫不可用 | 高 | 阻擋 D 系列任務 | 先建立專案骨架，後續再 push 到正確倉庫 |
| Outbox 與 Service 交易整合複雜 | 中 | 延遲 | 先寫測試釐清行為，再修改正式程式 |
| cross-repo CI 難以設定 | 中 | 延遲 | 先確保各自 CI 通過，cross-repo 作為獨立 job |
| Worker 多實例競爭 Outbox | 低 | 資料正確性 | 使用 SELECT FOR UPDATE SKIP LOCKED |
| Frontend 測試環境設定 | 低 | 延遲 | 沿用現有 vitest 設定 |
