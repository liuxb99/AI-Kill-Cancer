# Phase 3D Graph Correctness Hardening — 執行計劃

> 本計劃基於 `tasks/requirements.md`（23 章完整需求）與 `tasks/task-status.md`（17 項任務清單）制定。
> 場景：hardening（架構強化）— 修正既有功能的 Identity、Relations、Idempotency、Provenance、Query Consistency、Worker Correctness、Cross-repository Integration。
> 先前的 Phase 3D 審查僅 PARTIAL（≈60/100），Accepted NO，本次目標為 Reviewer ≥95。

---

## 一、任務總覽

| ID | 任務名稱 | 負責 Repository | 依賴 | 角色 |
|----|----------|----------------|------|------|
| **KG-01** | ClinicalIDFactory（UUIDv5, 固定 Namespace, 9 種 Entity ID + RelationID） | KnowGraphGo | 無 | knowgraphgo-dev |
| **KG-02** | Clinical Adapter 修正 — 建立真實 Target Entities + Relations + Provenance | KnowGraphGo | KG-01 | knowgraphgo-dev |
| **KG-03** | Idempotent Replay 測試 + 其他 Go 測試（14 項測試要求） | KnowGraphGo | KG-02 | knowgraphgo-dev / test-writer |
| **AKC-01** | Migration 022（Outbox 新增 correlation_id, causation_id, occurred_at, claim_token, processing_started_at, last_failed_at） | AI-Kill-Cancer | 無 | backend-logic |
| **AKC-02** | Event Payload 與真實模型同步（Recommendation/Decision/Consensus） | AI-Kill-Cancer | AKC-01 | backend-logic |
| **AKC-03** | Python ClinicalGraphIDFactory（ID 計算與 Go 一致）+ docs/clinical-graph-id-spec.md | AI-Kill-Cancer | KG-01（參考設計） | backend-logic |
| **AKC-04** | ClinicalGraphClient 非阻塞化（subprocess.run → asyncio.create_subprocess_exec） | AI-Kill-Cancer | 無 | backend-logic |
| **AKC-05** | Worker Transaction 修正（Claim→Processing→Result）+ Stale Recovery | AI-Kill-Cancer | AKC-01, AKC-04 | backend-logic |
| **AKC-06** | Failed Events 狀態一致性 + Status API 真實健康度 | AI-Kill-Cancer | AKC-05 | backend-logic |
| **AKC-07** | Explain Query 修正（不得將 Entity ID 當 Relation ID、確認真實路徑） | AI-Kill-Cancer | AKC-03, AKC-04 | backend-logic |
| **AKC-08** | CI 修正（KnowGraphGo SHA pin + Cross-repository Integration Test） | AI-Kill-Cancer | KG 完成 + AKC 完成 | devops |
| **INT-01** | 跨語言 ID Parity 測試（Python ID == Go ID） | 跨倉庫 | AKC-03, KG-01 | test-writer |
| **INT-02** | 跨倉庫 Integration Test（Digital Thread 完整路徑、Idempotency、Provenance） | 跨倉庫 | AKC-05, AKC-07, KG-03 | test-writer |
| **META-01** | Step 4b 需求回歸檢查 | — | 所有開發任務完成 | doc-writer |
| **META-02** | REVIEWER 評分 | — | META-01 | reviewer |
| **META-03** | 總結報告 + Git Commit & Push | 跨倉庫 | META-02 | doc-writer |

### 角色對應

| 角色 | 說明 |
|------|------|
| **knowgraphgo-dev** | Go 開發子代理，專注 KnowGraphGo 倉庫 |
| **backend-logic** | Python 後端開發子代理，專注 AI-Kill-Cancer 倉庫 |
| **test-writer** | 測試撰寫子代理，跨倉庫整合測試 |
| **devops** | CI 設定子代理 |
| **doc-writer** | 文檔與報告子代理 |
| **reviewer** | 評分子代理 |
| **planner** | 計劃子代理（本次） |

---

## 二、執行順序（Phase by Phase）

### 執行原則

1. **先 KnowGraphGo，後 AI-Kill-Cancer**：KG 完成後 push → 取得 SHA → AKC CI pin 該 SHA
2. **同一 Phase 內無依賴的任務可並行**
3. **每個任務完成後必須執行對應測試**
4. **Git 提交順序嚴格遵守：KnowGraphGo commit & push → AI-Kill-Cancer commit & push**

---

### Phase KG：KnowGraphGo 修正（先執行）

#### KG-01：ClinicalIDFactory（Deterministic ID）

| 屬性 | 內容 |
|------|------|
| **依賴** | 無 |
| **負責角色** | knowgraphgo-dev |
| **預估工時** | 2h |
| **主要檔案** | `adapter/clinical/id_factory.go`（新檔案） |

**詳細步驟**：

1. **建立檔案 `adapter/clinical/id_factory.go`**
   - 定義 `ClinicalIDFactory` struct，包含固定的 UUID Namespace（使用 UUIDv5）
   - Namespace UUID 必須固定且記錄於 `docs/clinical-graph-id-spec.md`
   - 實作以下方法：
     - `PatientID(patientID string) uuid.UUID`
     - `RecommendationID(recommendationID string) uuid.UUID`
     - `ClinicalDecisionID(decisionID string) uuid.UUID`
     - `ConsensusID(consensusID string) uuid.UUID`
     - `OpinionID(opinionID string) uuid.UUID`
     - `SpecialtyID(specialtyName string) uuid.UUID`
     - `DrugID(drugName string) uuid.UUID`
     - `EvidenceID(evidenceID string) uuid.UUID`
     - `VariantID(variantID string) uuid.UUID`
     - `RelationID(kind, fromID, toID string) uuid.UUID`

2. **Canonical Key 格式**（與 requirements.md 一致）：
   ```
   clinical:patient:{patient_id}
   clinical:recommendation:{recommendation_id}
   clinical:clinical_decision:{decision_id}
   clinical:consensus:{consensus_id}
   clinical:opinion:{opinion_id}
   clinical:specialty:{specialty_name}           # lowercase, trimmed
   clinical:drug:{drug_name}                      # lowercase, trimmed
   clinical:evidence:{evidence_id}
   clinical:variant:{variant_id}
   clinical:relation:{kind}:{from_id}:{to_id}
   ```

3. **Normalization 規則**：
   - 全部 lowercase
   - Trim whitespace
   - 空 ID 回傳 error
   - 使用 `uuid.NewSHA1(namespace, []byte(canonicalKey))`（Go 的 uuid.NewSHA1 對應 UUIDv5）

4. **禁止**：random UUID、database auto increment、event_id 作為 entity identity

5. **對應需求**：requirements.md §三（Deterministic ID 設計）

#### KG-02：Clinical Adapter 修正

| 屬性 | 內容 |
|------|------|
| **依賴** | KG-01 |
| **負責角色** | knowgraphgo-dev |
| **預估工時** | 4h |
| **主要檔案** | `adapter/clinical/adapter.go`（重寫）, `adapter/clinical/ontology.go`（修正）, `adapter/clinical/clinical_event.go`（修正） |

**詳細步驟**：

1. **修正 Ontology 定義**（`adapter/clinical/ontology.go`）
   - 確保 Entity Kinds 與 requirements.md 第四章一致
   - 確保 Relation Kinds 完整

2. **重寫 Adapter 的 `MapEventToGraphDelta()`**
   - Patient Event → Patient Entity（patient_id, display_name/pseudonym, sex, age_range, cancer_type, source_system, source_id）
   - Recommendation Event → Recommendation + Patient + Drug + Evidence Entities，Relation：FOR_PATIENT / RECOMMENDS / SUPPORTED_BY
   - Clinical Decision Event → ClinicalDecision + Patient + Recommendation + Evidence Entities，Relation：FOR_PATIENT / BASED_ON / SUPPORTED_BY
   - Tumor Board Consensus Event → Consensus + Patient + ClinicalDecision + SpecialistOpinion + Specialty + Evidence Entities，Relation：FOR_PATIENT / DERIVED_FROM / HAS_OPINION / PROVIDED_BY_SPECIALTY / SUPPORTED_BY

3. **GraphDelta 完整性規則**（requirements.md §五）：
   - 每個 Relation.From/To 必須在本次 Delta 中存在或可由 deterministic ID 對應既有節點
   - 所有 Relation 依賴的 Entity 全部加入本次 GraphDelta 作 Upsert

4. **Provenance 完整**（requirements.md §七）：
   - 每個 Entity Properties 保存：source_system, source_table, source_id, event_id, event_type, schema_version, actor_id, correlation_id, causation_id, occurred_at, aggregate_type, aggregate_id
   - 每個 Relation 也必須保存對應 Provenance
   - Evidence Entity 保存：evidence_id, source, citation, evidence_level, confidence

5. **使用 ClinicalIDFactory 取代隨機 ID**
   - 所有 Entity/Relation ID 改由 ClinicalIDFactory 產生
   - 不得再使用 `graph.NewEntityID()` / `graph.NewRelationID()`

6. **Idempotent Upsert**：
   - 相同 Event replay 不產生重複 Entity/Relation
   - Entity 已存在則 update properties，不新增第二個

#### KG-03：Go 測試（14 項測試要求）

| 屬性 | 內容 |
|------|------|
| **依賴** | KG-02 |
| **負責角色** | knowgraphgo-dev / test-writer |
| **預估工時** | 3h |
| **主要檔案** | `adapter/clinical/adapter_test.go`（新檔案）, `adapter/clinical/id_factory_test.go`（新檔案） |

**測試清單**（對應 requirements.md §十八）：

1. Deterministic ID golden tests（相同輸入→相同輸出，不同輸入→不同輸出）
2. Patient mapping test
3. Recommendation mapping test
4. ClinicalDecision mapping test
5. Consensus mapping test
6. Opinion mapping test
7. Specialty mapping test
8. Evidence mapping test
9. Drug mapping test
10. Relation target integrity test（所有 From/To 對應真實 Entity）
11. Duplicate replay test（相同 Event 重放兩次，Count 不變）
12. Updated event upsert test（created 後 updated → 同一 Entity，不新增）
13. Rebuild idempotency test（完整重建兩次，Entity/Relation 數量一致）
14. Provenance test（每個 Entity/Relation 都有完整 Provenance）
15. Unknown schema version rejection test
16. Sensitive payload rejection test

**驗收命令**：
```bash
cd KnowGraphGo
go test ./...          # 全部通過
go vet ./...           # 無警告
go build ./cmd/knowgraph  # 編譯成功
```

#### Phase KG 驗收條件

- [x] go test ./... 全部通過
- [x] go vet ./... 無警告
- [x] go build ./cmd/knowgraph 成功
- [x] ClinicalIDFactory 測試通過（golden tests）
- [x] Idempotent Replay 測試通過
- [x] Provenance 測試通過
- [x] Relation Integrity 測試通過
- [x] Git commit & push 完成
- [ ] Git commit message: `fix(clinical): make graph projection deterministic and idempotent`
- [ ] Push to origin/main → 取得 SHA

---

### Phase AKC：AI-Kill-Cancer 修正（後執行）

> 依賴 Phase KG 完成（需要 KnowGraphGo CLI SHA 進行跨倉庫測試）

#### AKC-01：Migration 022（Outbox Schema 補強）

| 屬性 | 內容 |
|------|------|
| **依賴** | 無 |
| **負責角色** | backend-logic |
| **預估工時** | 2h |
| **主要檔案** | `migrations/versions/022_phase3d_hardening_outbox_add_fields.py`（新檔案） |

**詳細步驟**：

1. **建立 Migration 022**（不得修改 Migration 021）
   - 新增欄位到既有 `domain_clinical_graph_outbox` 表：
     - `correlation_id`（String(64), nullable=True）
     - `causation_id`（String(64), nullable=True）
     - `occurred_at`（DateTime, nullable=False, default=func.now()）
     - `claim_token`（String(64), nullable=True, unique=True）
     - `processing_started_at`（DateTime, nullable=True）
     - `last_failed_at`（DateTime, nullable=True）

2. **Migration 驗證**：
   - 021 → 022 upgrade
   - 022 → 021 downgrade（若資料存在則拒絕）
   - 021 → 022 re-upgrade
   - 檢查新欄位可 null、可寫入、可讀取

3. **更新 Outbox Model**（`src/backend/domain/clinical_graph_outbox.py`）：
   - 加入新欄位定義
   - 更新 `__tablename__` 如有變更

4. **對應需求**：requirements.md §八、§十三

#### AKC-02：Event Payload 與真實模型同步

| 屬性 | 內容 |
|------|------|
| **依賴** | AKC-01 |
| **負責角色** | backend-logic |
| **預估工時** | 3h |
| **主要檔案** | `src/backend/services/recommendation_service.py`, `src/backend/services/clinical_decision_service.py`, `src/backend/services/tumor_board_service.py`（修正）|

**詳細步驟**：

逐一檢查三個 Service 的 Domain Model 欄位，確保 Event Payload 使用真實欄位，不是 placeholder/mock。

1. **RecommendationService**（`recommendation_service.py`）
   - Payload 必須包含：`recommendation_id`, `patient_id`, `recommended_drugs`（實際 drug list）, `evidence_references`（實際證據列表）, `rank/score`
   - 不得使用 `title`/`description` 等不存在或永遠為空的欄位

2. **ClinicalDecisionService**（`clinical_decision_service.py`）
   - Payload 必須包含：`decision_id`, `patient_id`, `recommendation_id`, `decision_type`, `rationale`, `evidence_references`, `contraindications`, `alternatives`
   - 確保 `evidence_references` 是真實資料，不是空陣列

3. **TumorBoardConsensusService**（`tumor_board_service.py`）
   - Payload 必須包含：`consensus_id`, `patient_id`, `clinical_decision_id`, `final_recommendation`, `consensus_status`, `consensus_score`, `supporting_evidence`, `specialist_opinions`, `participating_specialties`
   - 若 payload 缺少 `opinion_id` / `specialty` / `evidence_ids`，須在 Service 層補足

4. **對應需求**：requirements.md §九

#### AKC-03：Python ClinicalGraphIDFactory + ID 規格文件

| 屬性 | 內容 |
|------|------|
| **依賴** | KG-01（參考設計，非區塊） |
| **負責角色** | backend-logic |
| **預估工時** | 2h |
| **主要檔案** | `src/backend/domain/clinical_graph_id_factory.py`（新檔案）, `docs/clinical-graph-id-spec.md`（新檔案） |

**詳細步驟**：

1. **建立 `src/backend/domain/clinical_graph_id_factory.py`**
   - 使用 Python `uuid.uuid5(namespace, key)` 計算
   - 使用與 Go 相同的 UUID Namespace（硬編碼常數）
   - 實作與 KG-01 完全相同的 9 種 Entity ID + RelationID 方法
   - Normalization 規則與 Go 一致（lowercase + trim + 空值拒絕）

2. **建立 `docs/clinical-graph-id-spec.md`**
   - 定義 UUID namespace（hex 值）
   - Canonical key format（每種 Entity）
   - Normalization rules
   - UUID version（UUIDv5 = SHA1-based）
   - Relation key format
   - Python 與 Go implementation 的互通驗證說明

3. **對應需求**：requirements.md §十

#### AKC-04：ClinicalGraphClient 非阻塞化

| 屬性 | 內容 |
|------|------|
| **依賴** | 無 |
| **負責角色** | backend-logic |
| **預估工時** | 2h |
| **主要檔案** | `src/backend/adapters/knowgraph_adapter.py`（重寫） |

**詳細步驟**：

1. **將 `subprocess.run()` 改為 `asyncio.create_subprocess_exec()`**
   - `shell=False`
   - stdin pipe（傳入 JSONL）
   - stdout pipe（讀取結果）
   - stderr pipe（錯誤處理）
   - 支援 timeout（`asyncio.wait_for`）
   - process kill on timeout
   - return code validation
   - JSON parse validation

2. **新增測試**：
   - success scenario
   - non-zero exit
   - timeout
   - invalid JSON
   - CLI not found
   - large stdout

3. **對應需求**：requirements.md §十二

#### AKC-05：Worker Transaction 修正 + Stale Recovery

| 屬性 | 內容 |
|------|------|
| **依賴** | AKC-01, AKC-04 |
| **負責角色** | backend-logic |
| **預估工時** | 3h |
| **主要檔案** | `src/backend/workers/graph_projection_worker.py`（重寫） |

**詳細步驟**：

1. **Claim Transaction**：
   - `SELECT ... FOR UPDATE SKIP LOCKED`（PostgreSQL）/ 等價機制（SQLite）
   - status → 'processing'
   - 設定 `claim_token`（UUID）
   - 設定 `processing_started_at`
   - commit transaction

2. **External Work**（不持有 DB lock）：
   - 透過 ClinicalGraphClient 執行 CLI
   - 不持有任何 DB 連線鎖

3. **Result Transaction**：
   - 成功 → status = 'completed', `processed_at = now()`
   - 失敗 → status = 'failed', `last_failed_at = now()`, `last_error = error_msg`, `attempt_count += 1`
   - 若超過重試次數 → status = 'dead_letter'

4. **Stale Recovery**（requirements.md §十三）：
   - 啟動時掃描 status = 'processing' 且 `processing_started_at < now() - timeout` 的事件
   - 重置為 status = 'pending'
   - 清除 claim_token

5. **對應需求**：requirements.md §十三

#### AKC-06：Failed Events 狀態一致性 + Status API 真實健康度

| 屬性 | 內容 |
|------|------|
| **依賴** | AKC-05 |
| **負責角色** | backend-logic |
| **預估工時** | 2h |
| **主要檔案** | `src/backend/repositories/clinical_graph_outbox_repo.py`（修正）, `src/backend/api/v1/status.py`（修正） |

**詳細步驟**：

1. **Failed Events 狀態一致性**（requirements.md §十四）：
   - `mark_failed()` 將事件設為 'failed'（不是 'pending'）
   - 統一定義 status 列舉：`pending` / `processing` / `failed` / `completed` / `dead_letter`
   - `claim_pending` 查 `status IN ('pending', 'failed') AND available_at <= now()`

2. **Status API 真實健康度**（requirements.md §十五）：
   - 不得固定回傳 `{"status": "operational"}`
   - 必須結合以下指標決定整體狀態：
     - Outbox pending/failed/dead_letter 數量
     - CLI availability（knowgraph clinical verify）
     - last completed projection time
     - oldest pending event age
     - stale processing count
   - 狀態等級：`operational` / `degraded` / `unavailable`
   - 回傳格式範例：
     ```json
     {
       "status": "degraded",
       "checks": {
         "outbox_pending": 5,
         "outbox_failed": 2,
         "outbox_dead_letter": 0,
         "cli_available": true,
         "last_projection": "2026-06-05T12:00:00Z",
         "oldest_pending_age_seconds": 300,
         "stale_processing_count": 1
       }
     }
     ```

#### AKC-07：Explain Query 修正

| 屬性 | 內容 |
|------|------|
| **依賴** | AKC-03, AKC-04 |
| **負責角色** | backend-logic |
| **預估工時** | 2h |
| **主要檔案** | `src/backend/api/v1/clinical_graph.py`（修正） |

**詳細步驟**：

1. **不得把 Entity ID 當 Relation ID**：
   - 檢查 Explain Query 的 CLI command 參數
   - 確保傳入的是正確的 Entity ID（透過 ClinicalGraphIDFactory 計算）
   - 確認 CLI query 使用的是實體 ID 而非 relation ID

2. **Recommendation Explain**：
   - 至少找到：Patient / Recommendation / Drug / Evidence / Clinical Decision
   - 路徑必須是真實的 Graph Path，不是 mock

3. **Consensus Explain**：
   - 至少找到：ClinicalDecision / Consensus / Opinions / Specialties / Evidence

4. **Projection 狀態判定**：
   - 不得只因 CLI 回傳 success 就標記 `projection_status = connected`
   - 必須確認 entities 或 path 非空

5. **對應需求**：requirements.md §十一

#### AKC-08：CI 修正

| 屬性 | 內容 |
|------|------|
| **依賴** | Phase KG 完成（需要 SHA）+ AKC 其他任務完成 |
| **負責角色** | devops |
| **預估工時** | 2h |
| **主要檔案** | `.github/workflows/ci.yml`（修正） |

**詳細步驟**：

1. **CI KnowGraphGo SHA pin**（requirements.md §十六）：
   - 使用 Phase KG push 後取得的實際 SHA
   - 不得使用 `ref: master` 或浮動 branch
   - 修改 CI 中 checkout KnowGraphGo 的步驟

2. **Cross-repository Integration Test**（requirements.md §十七）：
   - Build CLI（`go build ./cmd/knowgraph`）
   - 建立臨時 SQLite Graph DB
   - AI-Kill-Cancer 產生 Event（patient.created → recommendation.created → clinical_decision.created → tumor_board_consensus.created）
   - CLI apply
   - 再次 apply（測試 idempotency）
   - CLI query（測試 Digital Thread）
   - 驗證：所有 Relation Target 存在、無 orphan relation、相同 Event 重放後 Count 不變、Provenance 可讀

#### Phase AKC 驗收條件

- [x] Migration 022 upgrade/downgrade/re-upgrade 測試通過
- [x] Event Payload 使用真實 Domain Model 欄位（非 placeholder）
- [x] Python ClinicalGraphIDFactory ID == Go ClinicalIDFactory ID（跨語言測試）
- [x] ClinicalGraphClient async 非阻塞測試通過
- [x] Worker Transaction 測試（claim → processing → result）通過
- [x] Stale Recovery 測試通過
- [x] Failed Events API 可見
- [x] Status API 回傳真實健康度
- [x] Recommendation Explain 找到真實路徑
- [x] Consensus Explain 找到真實路徑
- [x] CI pin KnowGraphGo SHA

---

### Phase INT：跨倉庫驗證

#### INT-01：跨語言 ID Parity 測試

| 屬性 | 內容 |
|------|------|
| **依賴** | AKC-03, KG-01 |
| **負責角色** | test-writer |
| **預估工時** | 1.5h |
| **主要檔案** | `tests/test_clinical_graph_id_parity.py`（新檔案） |

**測試內容**：
- 至少測試 9 種 Entity ID：patient / recommendation / decision / consensus / opinion / specialty / drug / evidence / variant
- 測試 Relation ID
- 執行方式：Python 端呼叫 `ClinicalGraphIDFactory` 產生的 ID，Go 端編譯小工具輸出 ID，比對兩者是否一致
- 邊界案例：空字串、特殊字元、Unicode、大寫輸入

#### INT-02：跨倉庫 Integration Test

| 屬性 | 內容 |
|------|------|
| **依賴** | AKC-05, AKC-07, KG-03 |
| **負責角色** | test-writer |
| **預估工時** | 3h |
| **主要檔案** | `tests/test_cross_repo_integration.py`（新檔案） |

**測試內容**（requirements.md §十七）：

1. **Build CLI**：
   - `go build -o knowgraph-cli ./cmd/knowgraph`（KnowGraphGo）
   - 取得 CLI binary path

2. **建立臨時 SQLite Graph DB**：
   - `knowgraph-cli clinical init --db /tmp/test_graph.db`

3. **AI-Kill-Cancer 產生 Events**（按順序）：
   - patient.created
   - recommendation.created
   - clinical_decision.created
   - tumor_board_consensus.created

4. **CLI apply 每個 Event**：
   - `echo '<jsonl>' | knowgraph-cli clinical apply --db /tmp/test_graph.db`

5. **再次 apply 全部 Events**（測試 Idempotency）：
   - Entity/Relation 數量不增加
   - ID 完全一致

6. **CLI query 驗證 Digital Thread**：
   - `knowgraph-cli clinical query-patient --id <patient_id> --db /tmp/test_graph.db`
   - 驗證所有 Relation Target 存在
   - 無 orphan relation
   - Provenance 完整

7. **驗收條件**：
   - 所有 Relation Target 存在（無 dangling reference）
   - 無 orphan relation
   - 相同 Event 重放後 Count 不變
   - Provenance 可讀且完整
   - Python ID == Go ID

---

### Phase META：收尾

#### META-01：Step 4b 需求回歸檢查

| 屬性 | 內容 |
|------|------|
| **依賴** | 所有開發任務完成 |
| **負責角色** | doc-writer |
| **預估工時** | 1h |
| **產出檔案** | `tasks/regression-check-phase3d-harden.md` |

**步驟**：
1. 獨立子代理重新讀取 `tasks/requirements.md`
2. 逐條核對原始需求（23 章）與實際交付成果
3. 記錄每條需求的驗證結果
4. 若發現缺漏 → 直接進入返工循環（不進入 REVIEWER）

#### META-02：REVIEWER 評分

| 屬性 | 內容 |
|------|------|
| **依賴** | META-01 |
| **負責角色** | reviewer |
| **預估工時** | 1.5h |
| **產出檔案** | `tasks/reviews/review_phase3d-hardening_<循環次數>.md` |

**評分規則**（遵循 AGENTS.md §Step 5）：
- 逐項確認 20 項 Reviewer Gate 條件（requirements.md §二十一）
- 以下任一未完成則滿足需求=NO、Reviewer 最高 89：
  - Deterministic ID
  - Relation Integrity
  - Idempotency
  - Digital Thread
  - Cross-language ID parity
  - Cross-repository integration
- 目標：總分 ≥ 95

#### META-03：總結報告 + Git Commit & Push

| 屬性 | 內容 |
|------|------|
| **依賴** | META-02（或返工後達標） |
| **負責角色** | doc-writer |
| **預估工時** | 1h |
| **產出檔案** | `tasks/summary-report-phase3d-hardening.md` |

**Git Commit Messages**：
- KnowGraphGo：`fix(clinical): make graph projection deterministic and idempotent`
- AI-Kill-Cancer：`fix(phase3d): harden graph identity projection and worker`

**提交順序**：
1. KnowGraphGo commit → push origin/main → 取得 SHA
2. AI-Kill-Cancer CI pin 該 SHA
3. AI-Kill-Cancer commit → push origin/master

**完成後回報**（requirements.md §二十三）：
- KnowGraphGo SHA
- AI-Kill-Cancer SHA
- Deterministic ID Algorithm
- UUID Namespace
- Python/Go ID Parity 結果
- Entity/Relation Kinds
- Orphan Relation Count
- Idempotency Results
- Digital Thread Paths
- Provenance Fields
- Migration 022 驗證
- Worker Correctness
- Async Result
- Status API 狀態
- Explain Results
- 測試結果
- CI Run IDs
- Reviewer Score

**最終判定**：Phase 3D Graph Correctness Hardening：PASS / PARTIAL / FAIL

---

## 三、每個任務的詳細執行步驟

### KG-01：ClinicalIDFactory

```
1. 建立 adapter/clinical/id_factory.go
   a. 定義固定的 UUID Namespace（常數）
   b. 定義 9 個 Entity ID 方法
   c. 定義 RelationID 方法
   d. 定義 normalizeKey() 輔助函數（lowercase + trim + 空值檢查）
   e. 定義 canonicalKey() 輔助函數（組合 key format）
2. 建立 adapter/clinical/id_factory_test.go
   a. Golden test：固定輸入→固定輸出
   b. Collision test：不同 Entity Kind 不得碰撞
   c. 空值 rejection test
   d. 大小寫標準化 test
3. 執行 go test ./adapter/clinical/ -run IdFactory -v
4. 執行 go vet ./adapter/clinical/...
```

### KG-02：Clinical Adapter 修正

```
1. 修正 adapter/clinical/ontology.go
   a. 確認 Entity Kinds 完整（9 種）
   b. 確認 Relation Kinds 完整（8 種）
2. 重寫 adapter/clinical/adapter.go
   a. MapEventToGraphDelta() — 4 種 Event Type 映射
   b. ApplyEvent() — Idempotent Upsert
   c. ValidateEvent() — Schema Version / Sensitive Data
3. 建立 adapter/clinical/clinical_event.go（Event 結構）
   a. ClinicalEvent struct（對應 Outbox Event JSON）
   b. Provenance struct
4. 建立 adapter/clinical/graph_delta.go（GraphDelta 結構）
5. 執行 go test ./adapter/clinical/ -v
```

### KG-03：Go 測試

```
1. 撰寫 adapter/clinical/adapter_test.go
   a. TestPatientMapping
   b. TestRecommendationMapping
   c. TestClinicalDecisionMapping
   d. TestConsensusMapping
   e. TestRelationTargetIntegrity
   f. TestDuplicateReplayIdempotent
   g. TestUpdatedEventUpsert
   h. TestRebuildIdempotency
   i. TestProvenance
   j. TestUnknownSchemaVersionRejection
   k. TestSensitivePayloadRejection
2. 執行 go test ./... -v
3. 執行 go vet ./...
4. 執行 go build ./cmd/knowgraph
```

### AKC-01：Migration 022

```
1. 建立 migrations/versions/022_phase3d_hardening_outbox_add_fields.py
   a. upgrade()：ALTER TABLE domain_clinical_graph_outbox ADD COLUMN ...
   b. downgrade()：DROP COLUMN ...（若資料存在則拒絕）
2. 更新 src/backend/domain/clinical_graph_outbox.py
   a. 加入新欄位
   b. 更新 __init__ 與欄位定義
3. 撰寫測試 test_migration_022.py
   a. upgrade
   b. downgrade
   c. re-upgrade
   d. 欄位 round-trip
4. 執行 pytest tests/test_migration_022.py -v
```

### AKC-02：Event Payload 同步

```
1. 檢查 RecommendationService
   a. 找出 _persist_recommendation() 的實際欄位
   b. 更新 Outbox payload 使用真實欄位
2. 檢查 ClinicalDecisionService
   a. 找出 create_decision() 的實際欄位
   b. 更新 Outbox payload
3. 檢查 TumorBoardConsensusService
   a. 找出 create_consensus() 的實際欄位
   b. 更新 Outbox payload
   c. 補足 opinion_id / specialty / evidence_ids
4. 撰寫測試 test_event_payload_correctness.py
   a. Recommendation payload 欄位正確
   b. Decision payload 欄位正確
   c. Consensus payload 欄位正確
   d. 無 placeholder/title/description 等虛假欄位
```

### AKC-03：Python ClinicalGraphIDFactory

```
1. 建立 src/backend/domain/clinical_graph_id_factory.py
   a. UUID_NAMESPACE 常數（與 Go 相同 hex 值）
   b. ClinicalGraphIDFactory 類別
   c. 9 種 Entity ID 方法 + relation_id()
   d. normalize() 與 canonical_key() 輔助函數
2. 建立 docs/clinical-graph-id-spec.md
   a. UUID Namespace 規格
   b. Canonical Key Format 表
   c. Normalization Rules
   d. UUID Version 說明
   e. 跨語言互通驗證方式
3. 撰寫測試 test_clinical_graph_id_factory.py
   a. 與 Go golden test 相同的輸入
   b. 空值拒絕
   c. 大小寫標準化
```

### AKC-04：ClinicalGraphClient 非阻塞化

```
1. 重寫 src/backend/adapters/knowgraph_adapter.py
   a. 將 subprocess.run() 改為 asyncio.create_subprocess_exec()
   b. 實作 _run_cli() helper
   c. 支援 timeout
   d. 支援 process kill
   e. return code + JSON parse validation
2. 撰寫測試 test_clinical_graph_client_async.py
   a. test_success
   b. test_non_zero_exit
   c. test_timeout
   d. test_invalid_json
   e. test_cli_not_found
   f. test_large_stdout
```

### AKC-05：Worker Transaction 修正

```
1. 重寫 src/backend/workers/graph_projection_worker.py
   a. _claim_events()：SELECT FOR UPDATE SKIP LOCKED → status=processing
   b. _process_event()：呼叫 ClinicalGraphClient（不持有 DB lock）
   c. _complete_event()：成功→completed，失敗→failed/dead_letter
2. 新增 Stale Recovery
   a. _recover_stale_events()：processing 超過 timeout → pending
3. 更新 Outbox Repository
   a. claim_pending()：支援 SKIP LOCKED
   b. mark_processing()：設定 claim_token + processing_started_at
   c. mark_completed() / mark_failed()
4. 撰寫測試 test_worker_transaction.py
   a. test_claim_process_complete
   b. test_stale_recovery
   c. test_concurrent_claim
   d. test_max_retry_dead_letter
```

### AKC-06：Failed Events + Status API

```
1. 修正 Outbox Repository
   a. mark_failed() → status='failed'（不是 pending）
   b. claim_pending() → WHERE status IN ('pending','failed')
2. 修正 Status API
   a. 收集健康度指標
   b. 決定整體狀態
   c. 回傳詳細 checks
3. 撰寫測試
   a. test_failed_event_visibility
   b. test_status_api_health
   c. test_status_api_degraded
```

### AKC-07：Explain Query 修正

```
1. 修正 clinical_graph.py 中的 Explain 端點
   a. Recommendation Explain：使用 ClinicalGraphIDFactory 計算正確 ID
   b. Consensus Explain：同上
   c. 確認 CLI query 結果 entities 非空
   d. 回傳真實路徑而非 mock
2. 撰寫測試
   a. test_recommendation_explain_real_path
   b. test_consensus_explain_real_path
   c. test_projection_status_non_empty
```

### AKC-08：CI 修正

```
1. 修改 .github/workflows/ci.yml
   a. KnowGraphGo checkout → 使用 pin SHA（非浮動 branch）
   b. 新增 cross-repo integration job
   c. build CLI → 建立 SQLite DB → apply events → verify
2. 撰寫跨倉庫 CI 測試腳本
   a. scripts/cross_repo_integration_test.sh（或 .py）
```

---

## 四、依賴圖

```
                    ┌────────────────────────────────────────────────┐
                    │              Phase KG (KnowGraphGo)            │
                    │                                                │
                    │  KG-01: ClinicalIDFactory (無依賴)             │
                    │       ↓                                       │
                    │  KG-02: Adapter 修正 (依賴 KG-01)              │
                    │       ↓                                       │
                    │  KG-03: Go 測試 (依賴 KG-02)                   │
                    │       ↓                                       │
                    │  push origin/main → 取得 SHA                  │
                    └─────────────────────┬──────────────────────────┘
                                          │ SHA pin
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Phase AKC (AI-Kill-Cancer)                               │
│                                                                             │
│  AKC-01 ──┐                                                                │
│  (Migration 022)                                                            │
│            │                                                                │
│  AKC-04 ──┤──→ AKC-05 ──→ AKC-06 ──→ AKC-08                                │
│  (Non-block Client)   │  (Worker TX)  │(Status API)   (CI PIN)             │
│                       │               │                                     │
│  AKC-02 ──────────────┤               │                                     │
│  (Payload Sync)       │               │                                     │
│                       │               │                                     │
│  AKC-03 ──────────────┴──→ AKC-07                                         │
│  (Python ID Factory)      (Explain)                                         │
│       │                                                                     │
│       └──→ INT-01 (ID Parity)                                               │
│                                                                             │
│  AKC-05 ──→ INT-02 (Cross-repo Integration)                                │
│  AKC-07 ──┘                                                                │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Phase INT (跨倉庫驗證)                                   │
│                                                                             │
│  INT-01: ID Parity Test (依賴 AKC-03, KG-01)                               │
│  INT-02: Cross-repo Integration (依賴 AKC-05, AKC-07, KG-03)              │
│                                                                             │
│  可與 AKC-08 CI 修正合併執行                                                │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Phase META (收尾)                                        │
│                                                                             │
│  META-01: Step 4b 需求回歸 (依賴全部開發完成)                               │
│       ↓                                                                    │
│  META-02: REVIEWER 評分 (依賴 META-01)                                     │
│       ↓ (若 <95 分，返工循環)                                              │
│  META-03: 總結報告 + Git Commit & Push (依賴 META-02)                      │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 並行策略

| 可並行任務 | 說明 |
|-----------|------|
| KG-01 + AKC-01 | 分屬不同 Repository，無依賴關係 |
| KG-02 + AKC-04 | Adapter 修正與 Client 非阻塞化無依賴 |
| AKC-01 + AKC-02 + AKC-04 | Migration 022、Payload 同步、Client 非阻塞化三者無依賴 |
| INT-01 可與 AKC-07 並行 | ID Parity 測試與 Explain 修正無依賴 |
| META-02 與 META-03 順序 | 不可並行 |

---

## 五、返工預案

### 觸發條件

REVIEWER 總分 < 95 分，或任一核心需求未通過（Deterministic ID / Relation Integrity / Idempotency / Digital Thread / Cross-language ID parity / Cross-repository integration）。

### 返工流程

```
循環次數 = 0

do {
  1. PLANNER(resume) 讀取評分報告，重新規劃
     輸入：原始需求 + 本計劃 + 評分報告
     輸出：修正後的計劃，針對缺失項目對症下藥

  2. 開發子代理(resume) 按新計劃重新執行
     輸入：修正後的計劃
     輸出：修正後的交付檔案

  3. REVIEWER 重新評分
     循環次數 + 1
     報告命名：review_phase3d-hardening_<循環次數>.md

} while (總分 < 95 && 循環次數 < 5)
```

### 常見缺失與修正指引

| 缺失類型 | 典型原因 | 修正策略 |
|----------|---------|----------|
| Deterministic ID 不一致 | Python 與 Go normalization 差異 | 統一 normalize 邏輯，使用同一份 golden test vector |
| Relation Integrity 失敗 | Target Entity 未加入 GraphDelta | 確保 MapEventToGraphDelta 將所有相依 Entity 加入 Delta |
| Idempotency 失敗 | Upsert 邏輯不正確 | 檢查 key-based upsert（Entity ID 相同則 update，不 insert）|
| Digital Thread 不完整 | Explain Query 缺少某種 Entity | 確認 Recommendation Explain 找到 5 種 Entity、Consensus Explain 找到 6 種 |
| Provenance 不完整 | Entity/Relation 缺少部分欄位 | 逐一比對 requirements.md §七 的欄位清單 |
| Python/Go ID Parity 失敗 | Key format 或 normalization 不同 | 統一使用 docs/clinical-graph-id-spec.md 作為 source of truth |
| Cross-repo CI 失敗 | CI 中 KnowGraphGo checkout 失敗 | 確認 SHA 正確、cache 策略、build 步驟 |
| Worker Transaction 錯誤 | Claim 與 Result 不在同一 transaction | 確保 claim 使用 FOR UPDATE SKIP LOCKED，processing 不持有 lock |
| Status API 固定回傳 | 未實作健康檢查邏輯 | 實作 Outbox + CLI + last projection 等指標 |

### 最終結果判定

- 循環次數 < 5 且 ≥ 95 分 → Phase 3D Hardening 完成 ✅
- 循環次數 ≥ 5 且仍 < 95 分 → 標記「阻塞⚠️ → 啟動 DeepSeek MCP 顧問，DeepSeek 介入後最多再修 2 輪，若仍 <95 分，才標記需真人人工決策」

---

## 六、時間估算

| Phase | 任務 | 估算工時 | 備註 |
|-------|------|---------|------|
| **KG** | KG-01 ClinicalIDFactory | 2h | |
| | KG-02 Adapter 修正 | 4h | 最複雜的單一任務 |
| | KG-03 Go 測試 | 3h | 14+ 項測試 |
| | *KG 小計* | *9h* | |
| **AKC** | AKC-01 Migration 022 | 2h | |
| | AKC-02 Payload 同步 | 3h | 需檢查 3 個 Service |
| | AKC-03 Python ID Factory + Spec | 2h | |
| | AKC-04 Client 非阻塞化 | 2h | |
| | AKC-05 Worker Transaction | 3h | 含 Stale Recovery |
| | AKC-06 Failed Events + Status API | 2h | |
| | AKC-07 Explain Query | 2h | |
| | AKC-08 CI 修正 | 2h | 含 Cross-repo CI |
| | *AKC 小計* | *18h* | |
| **INT** | INT-01 ID Parity | 1.5h | |
| | INT-02 Cross-repo Integration | 3h | |
| | *INT 小計* | *4.5h* | |
| **META** | META-01 Step 4b 回歸檢查 | 1h | |
| | META-02 REVIEWER 評分 | 1.5h | |
| | META-03 總結報告 + Commit | 1h | |
| | *META 小計* | *3.5h* | |
| | **總計** | **35h** | |
| | *返工循環（每輪）* | *+6~10h* | 視缺失範圍而定 |

### 時間備註

- 開發時間採 Pessimistic Estimate（包含測試與除錯）
- 若 KnowGraphGo 與 AI-Kill-Cancer 可並行開發（KG + AKC 同步），實際 wall clock 可縮短
- Migration 022 測試（upgrade/downgrade/re-upgrade）約佔 0.5h
- Cross-repo CI debug 時間可能較長（CI 環境與本機差異）
- REVIEWER 首次評分若 <95，返工循環每輪約 6-10h

---

## 附錄 A：檔案變更完整清單

### KnowGraphGo 新增檔案

| # | 路徑 | 說明 |
|---|------|------|
| 1 | `adapter/clinical/id_factory.go` | ClinicalIDFactory（UUIDv5 Deterministic ID） |
| 2 | `adapter/clinical/id_factory_test.go` | ID Factory 測試 |

### KnowGraphGo 修改檔案

| # | 路徑 | 修改內容 |
|---|------|----------|
| 1 | `adapter/clinical/ontology.go` | 修正 Entity/Relation Kinds（如有缺失） |
| 2 | `adapter/clinical/adapter.go` | 全面重寫：使用 ClinicalIDFactory、真實 Target Entities、完整 Provenance、Idempotent Upsert |
| 3 | `adapter/clinical/clinical_event.go` | 新增 Provenance struct、完整欄位 |
| 4 | `adapter/clinical/adapter_test.go` | 新增 14+ 項測試 |

### AI-Kill-Cancer 新增檔案

| # | 路徑 | 說明 |
|---|------|------|
| 1 | `migrations/versions/022_phase3d_hardening_outbox_add_fields.py` | Migration 022 |
| 2 | `src/backend/domain/clinical_graph_id_factory.py` | Python ClinicalGraphIDFactory |
| 3 | `docs/clinical-graph-id-spec.md` | ID 規格文件 |
| 4 | `tests/test_migration_022.py` | Migration 022 測試 |
| 5 | `tests/test_event_payload_correctness.py` | Payload 正確性測試 |
| 6 | `tests/test_clinical_graph_id_factory.py` | ID Factory 測試（含跨語言 golden tests） |
| 7 | `tests/test_clinical_graph_client_async.py` | Async Client 測試 |
| 8 | `tests/test_worker_transaction.py` | Worker Transaction 測試 |
| 9 | `tests/test_status_api_health.py` | Status API 健康度測試 |
| 10 | `tests/test_clinical_graph_id_parity.py` | 跨語言 ID Parity 測試（INT-01） |
| 11 | `tests/test_cross_repo_integration.py` | 跨倉庫 Integration Test（INT-02） |

### AI-Kill-Cancer 修改檔案

| # | 路徑 | 修改內容 |
|---|------|----------|
| 1 | `src/backend/domain/clinical_graph_outbox.py` | 新增欄位（correlation_id, causation_id, occurred_at, claim_token, processing_started_at, last_failed_at） |
| 2 | `src/backend/services/recommendation_service.py` | Event Payload 使用真實欄位 |
| 3 | `src/backend/services/clinical_decision_service.py` | Event Payload 使用真實欄位 |
| 4 | `src/backend/services/tumor_board_service.py` | Event Payload 使用真實欄位 |
| 5 | `src/backend/adapters/knowgraph_adapter.py` | subprocess.run → asyncio.create_subprocess_exec |
| 6 | `src/backend/workers/graph_projection_worker.py` | Claim→Processing→Result Transaction + Stale Recovery |
| 7 | `src/backend/repositories/clinical_graph_outbox_repo.py` | mark_failed 狀態修正、claim_pending 含 failed |
| 8 | `src/backend/api/v1/clinical_graph.py` | Explain Query 修正 |
| 9 | `src/backend/api/v1/status.py` | 真實健康度指標 |
| 10 | `.github/workflows/ci.yml` | KnowGraphGo SHA pin + Cross-repo Integration |

---

## 附錄 B：Reviewer Gate 檢查清單（20 項）

對應 requirements.md §二十一：

| # | 檢查項 | 核心需求 | 驗證方式 |
|---|--------|---------|----------|
| 1 | Entity ID deterministic | ✅ | golden test：相同輸入→相同輸出 |
| 2 | Relation ID deterministic | ✅ | golden test |
| 3 | Same Event replay idempotent | ✅ | 重放兩次，Count 不變 |
| 4 | created→updated 不重複 | ✅ | 先 created 再 updated，Entity 被更新不新增 |
| 5 | 所有 Relation Target 存在 | ✅ | GraphDelta 完整性檢查 |
| 6 | Patient→Recommendation 正確 | ✅ | Digital Thread 路徑驗證 |
| 7 | Recommendation→Drug/Evidence 正確 | ✅ | Explain Query 驗證 |
| 8 | Decision→Recommendation 正確 | ✅ | Explain Query 驗證 |
| 9 | Consensus→Decision 正確 | ✅ | Explain Query 驗證 |
| 10 | Consensus→Opinion→Specialty 正確 | ✅ | Explain Query 驗證 |
| 11 | Python ID == Go ID | ✅ | 跨語言 ID Parity 測試 |
| 12 | Provenance 完整 | ✅ | 每個 Entity/Relation 檢查 Provenance 欄位 |
| 13 | Event Payload 來自真實 Domain Model | ✅ | Service 層 payload 欄位比對 |
| 14 | async subprocess 不阻塞 | ✅ | Async Client 測試 |
| 15 | Worker 不長時間持有 DB lock | ✅ | Claim→Release→Result 三段 transaction |
| 16 | stale processing 可恢復 | ✅ | Stale Recovery 測試 |
| 17 | failed events API 可見 | ✅ | Status API 含 failed count |
| 18 | Status API 反映 CLI 真實狀態 | ✅ | Status API 整合多項指標 |
| 19 | CI pin KnowGraphGo SHA | ✅ | CI 使用固定 SHA 而非 branch |
| 20 | Cross-repository Digital Thread 測試通過 | ✅ | INT-02 測試通過 |

**核心需求（任一未完成 → Reviewer 最高 89）**：
- Deterministic ID
- Relation Integrity
- Idempotency
- Digital Thread
- Cross-language ID parity
- Cross-repository integration

---

> 本計劃由 PLANNER 子代理產出，輸入為 `tasks/requirements.md` 與 `tasks/task-status.md`。
> 執行時請嚴格遵循 AGENTS.md 的工作流程與本計劃的執行順序。
