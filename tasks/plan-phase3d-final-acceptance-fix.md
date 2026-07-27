# Phase 3D Final Acceptance Fix — 執行計劃

## 任務總覽

修正 Phase 3D Final Acceptance 的最後四個驗收缺口（P0-1、P0-2、P1-1、P1-2）以及 Stub Preservation 和 Relation Provenance E2E 驗證，使 CI 全綠、Reviewer ≥ 95。

涉及兩個 Repository：
- **KnowGraphGo**（Go）：CLI、Adapter、Tests
- **AI-Kill-Cancer**（Python）：E2E Script、Parity Tests、CI、Schema 文件、Fixtures

執行順序：先完成 KnowGraphGo → Commit & Push → 再完成 AI-Kill-Cancer → Commit & Push → CI 驗證。

## 依賴關係

```
A-1 (clinical id CLI) → A-3 (CLI 測試)
├─→ A-2 (Canonical Adapter) → A-4 (Adapter 測試)
├─→ A-5 (Commit & Push KnowGraphGo)
│   └─→ B-1 (更新 CI pin) → B-2 (修正 E2E Script) → B-3 (修正 ID Parity)
│       └─→ B-4 (Schema 文件) → B-5 (Fixtures) → B-6 (Commit & Push AI-Kill-Cancer)
│           └─→ C (CI 驗證) ─→ D (Reviewer 評分)
```

## 執行階段

---

### Phase A：KnowGraphGo 開發

#### A-1：修正 clinical id CLI 輸出格式

**負責角色**：knowgraphgo-dev

**檔案**：
- `KnowGraphGo/cmd/knowgraph/clinical.go`

**現狀**：`handleClinicalID` 已支援所有 10 種 entity kind + relation，但 relation 的輸出使用 `outputRow`（只有 `kind/business_key/graph_id`），不符合需求規格的 `relation_kind/from_business_key/to_business_key`。

**修改內容**：
1. 新增 `relationOutput` struct：
   ```go
   type relationOutput struct {
       Kind            string `json:"kind"`
       RelationKind    string `json:"relation_kind"`
       FromBusinessKey string `json:"from_business_key"`
       ToBusinessKey   string `json:"to_business_key"`
       GraphID         string `json:"graph_id"`
   }
   ```
2. 在 `case "relation"` 分支中使用 `relationOutput` 替代 `outputRow`
3. 更新 `printClinicalUsage()` 以反映正確的 relation 語法（已有）
4. 驗證 JSON 永遠有效、錯誤輸出到 stderr、錯誤時 exit code != 0、空 key 正常回傳 validation error、不得 panic

**估時**：15 分鐘

---

#### A-2：修正 canonical event payload 映射

**負責角色**：knowgraphgo-dev

**檔案**：
- `KnowGraphGo/adapter/clinical/adapter.go`

**現狀**：
- `mapRecommendationEvent` 讀取 `drug_ids`（舊欄位）和 `evidence_ids`（舊欄位），但未讀取 `recommended_drugs[].drug_id` 和 `evidence_references[].evidence_id`
- `mapClinicalDecisionEvent` 讀取 `evidence_ids` 但未讀取 `evidence_references[].evidence_id`
- `mapConsensusEvent` 讀取 `evidence_ids` 但未讀取 `supporting_evidence[].evidence_id`

**修改內容**：
1. **Recommendation payload**：新增結構體解析 `recommended_drugs` 和 `evidence_references`
   ```go
   type recommendationPayload struct {
       RecommendationID string              `json:"recommendation_id"`
       PatientID       string              `json:"patient_id"`
       Title           string              `json:"title,omitempty"`
       DrugIDs         []string            `json:"drug_ids,omitempty"` // 舊欄位（向後相容）
       EvidenceIDs     []string            `json:"evidence_ids,omitempty"` // 舊欄位
       RecommendedDrugs []recommendedDrug  `json:"recommended_drugs,omitempty"`
       EvidenceRefs    []evidenceReference `json:"evidence_references,omitempty"`
   }
   type recommendedDrug struct {
       DrugID   string  `json:"drug_id"`
       DrugName string  `json:"drug_name,omitempty"`
       Rank     int     `json:"rank,omitempty"`
       Score    float64 `json:"score,omitempty"`
   }
   type evidenceReference struct {
       EvidenceID     string `json:"evidence_id"`
       Citation       string `json:"citation,omitempty"`
       EvidenceLevel  string `json:"evidence_level,omitempty"`
       Confidence     float64 `json:"confidence,omitempty"`
   }
   ```
2. 解析邏輯：優先讀取 canonical 欄位（`recommended_drugs`/`evidence_references`），若為空則 fallback 到舊欄位（`drug_ids`/`evidence_ids`）
3. **Decision payload**：同樣新增 `evidence_references` 解析
4. **Consensus payload**：新增 `supporting_evidence` 解析；`specialist_opinions` 已正確處理
5. 保留舊欄位作為向後相容

**估時**：30 分鐘

---

#### A-3：新增 CLI 測試（clinical id）

**負責角色**：test-writer

**檔案**：
- `KnowGraphGo/cmd/knowgraph/main_test.go`（新增測試函數）

**測試案例**（至少 8 類）：

| # | 測試名稱 | 測試內容 |
|---|---------|---------|
| 1 | `TestCLI_ClinicalID_Patient` | `clinical id patient P001` → JSON 輸出含 kind/patient/business_key/P001/graph_id/有效 UUID |
| 2 | `TestCLI_ClinicalID_AllEntityKinds` | 逐一測試 patient/recommendation/decision/consensus/opinion/specialty/drug/evidence/variant → 每種 JSON schema 正確 |
| 3 | `TestCLI_ClinicalID_Relation` | `clinical id relation FOR_PATIENT REC-001 P001` → JSON 輸出含 relation_kind/from_business_key/to_business_key |
| 4 | `TestCLI_ClinicalID_CaseNormalization` | `clinical id patient "  P001  "` 與 `clinical id patient P001` 輸出相同 graph_id |
| 5 | `TestCLI_ClinicalID_EmptyKey` | `clinical id patient ""` → exit code != 0，stderr 有錯誤訊息 |
| 6 | `TestCLI_ClinicalID_UnknownKind` | `clinical id unknown xyz` → exit code != 0，stderr 有錯誤訊息 |
| 7 | `TestCLI_ClinicalID_MissingArgs` | `clinical id patient`（少 key）→ exit code != 0 |
| 8 | `TestCLI_ClinicalID_RelationMissingArgs` | `clinical id relation FOR_PATIENT`（少參數）→ exit code != 0 |
| 9 | `TestCLI_ClinicalID_JSONSchema` | 驗證 JSON 格式符合預期結構（kind/business_key/graph_id 存在且類型正確） |
| 10 | `TestCLI_ClinicalID_ExitCode` | 正常 case exit 0，錯誤 case exit != 0 |

**使用既有框架**：`buildCLI()` + `runCLI()` + `tempDSN()`，但要小心 `clinical id` 不需要 DB，所以不需要 `--dsn`。

**注意**：測試必須測真正的 CLI handler（透過編譯二進位檔執行），而非只測 `ClinicalIDFactory`。

**估時**：45 分鐘

---

#### A-4：新增 Adapter 測試（Canonical Payload）

**負責角色**：test-writer

**檔案**：
- `KnowGraphGo/adapter/clinical/clinical_test.go`

**測試案例**：

1. `TestCanonicalPayload_Recommendation`：傳入 `recommended_drugs[].drug_id` + `evidence_references[].evidence_id`，驗證正確建立 Drug Entity + Evidence Entity + RECOMMENDS/SUPPORTED_BY Relation
2. `TestCanonicalPayload_Decision`：傳入 `evidence_references[].evidence_id`（含 citation/evidence_level），驗證正確映射
3. `TestCanonicalPayload_Consensus`：傳入 `supporting_evidence[].evidence_id` + `specialist_opinions[]`，驗證正確映射
4. `TestCanonicalPayload_BackwardCompat`：傳入舊欄位 `drug_ids` + `evidence_ids`，仍然正確運作
5. `TestCanonicalPayload_Priority`：canonical 欄位優先於舊欄位

**估時**：30 分鐘

---

#### A-5：Commit & Push KnowGraphGo

**負責角色**：knowgraphgo-dev

**Commit Message**：
```text
fix(clinical): add id cli and canonical event schema
```

**變更檔案**：
- `KnowGraphGo/cmd/knowgraph/clinical.go`
- `KnowGraphGo/adapter/clinical/adapter.go`
- `KnowGraphGo/cmd/knowgraph/main_test.go`（新增測試）
- `KnowGraphGo/adapter/clinical/clinical_test.go`（新增測試）
- `KnowGraphGo/golden_output.json`（若 relation 輸出的 golden 值改變）
- `KnowGraphGo/adapter/clinical/golden_output.json`（同上）

**完成後記錄完整 SHA** 供 B-1 使用。

**估時**：5 分鐘

---

### Phase B：AI-Kill-Cancer 開發

#### B-1：更新 CI pin 到新的 KnowGraphGo SHA

**負責角色**：devops

**檔案**：
- `.github/workflows/ci.yml`

**修改內容**：
1. 找到 `ref: d6fa05a7d13ec3d51473c737ab4ebe3482ac2950` 與 `ref: a7a5b2e`
2. 更新為 KnowGraphGo A-5 完成後的完整 SHA

**估時**：2 分鐘

---

#### B-2：修正 E2E Script

**負責角色**：integration-tester

**檔案**：
- `scripts/cross_repo_e2e_test.py`

**修改內容**：

##### 1. Path JSON 內容驗證（P1-1）

將 `query_path()` 回傳值改為 JSON 解析，驗證：
```python
def query_path(cli_path, db_path, from_id, to_id):
    result = subprocess.run(
        [cli_path, "--dsn", db_path, "--json", "query", "path", from_id, to_id],
        capture_output=True, text=True, timeout=30
    )
    if result.returncode != 0:
        return None, result.returncode
    data = json.loads(result.stdout)
    return data, result.returncode
```

驗證內容：
- `data["found"]` 或 `len(data["paths"]) > 0`
- `data["paths"][0]["entities"]` 非空
- `data["paths"][0]["edges"]` 非空（或 `relations`）
- 起點 ID 正確（path[0].entities[0].id == from_id）
- 終點 ID 正確（path[-1].entities[-1].id == to_id）
- Relation Kind 正確（每個 edge 的 kind）

至少驗證 7 條路徑（需要先查詢 graph ID）：

```python
# 1. Recommendation → Patient (FOR_PATIENT)
data, rc = query_path(cli_path, db_path, rec_gid, patient_gid)
# 2. ClinicalDecision → Recommendation (BASED_ON)
data, rc = query_path(cli_path, db_path, decision_gid, rec_gid)
# 3. Consensus → ClinicalDecision (DERIVED_FROM)
data, rc = query_path(cli_path, db_path, consensus_gid, decision_gid)
# 4. Recommendation → Drug (RECOMMENDS)
# 5. Recommendation → Evidence (SUPPORTED_BY)
# 6. Consensus → Opinion (HAS_OPINION)
# 7. Opinion → Specialty (PROVIDED_BY_SPECIALTY)
```

##### 2. Count Query 失敗直接 Fail（P1-2）

修改 `query_count()`：
```python
def query_count(cli_path, db_path):
    result = subprocess.run(
        [cli_path, "--dsn", db_path, "--json", "check"],
        capture_output=True, text=True, timeout=30
    )
    if result.returncode != 0:
        raise RuntimeError(f"Count query failed: {result.stderr}")
    data = json.loads(result.stdout)
    entities = data.get("total_entities")
    relations = data.get("total_edges")
    if entities is None or relations is None:
        raise KeyError(f"Count query missing required fields: {data}")
    return {"entities": entities, "relations": relations}
```

Replay 驗收：
```python
# 第一次 apply 後
count1 = query_count(...)
assert count1["entities"] > 0, f"Expected entities > 0, got {count1['entities']}"
assert count1["relations"] > 0, f"Expected relations > 0, got {count1['relations']}"

# 第二次 replay 後
count2 = query_count(...)
assert count2["entities"] == count1["entities"]
assert count2["relations"] == count1["relations"]
```

##### 3. Stub Preservation E2E（需求六）

使用 `knowgraph clinical id patient P001` 取得 Patient graph_id，然後：
```python
# 透過 query prop 或直接查 node 來驗證
result = subprocess.run(
    [cli_path, "--dsn", db_path, "--json", "query", "prop", "patient_id=P001"],
    capture_output=True, text=True, timeout=30
)
data = json.loads(result.stdout)
patient = data["entities"][0]
props = patient.get("properties", {})
assert props.get("display_name") == "ANON", f"Expected ANON, got {props.get('display_name')}"
assert props.get("sex") == "F"
assert props.get("age_range") == "40-50"
assert props.get("cancer_type") == "BRCA"
```

##### 4. Relation Provenance E2E（需求七）

直接查詢 SQLite DB：
```python
import sqlite3
conn = sqlite3.connect(db_path)
cursor = conn.execute(
    "SELECT properties FROM relations WHERE from_id = ? AND kind = ?",
    (rec_gid, "FOR_PATIENT")
)
row = cursor.fetchone()
props = json.loads(row[0])
assert props.get("source_system") == "AI-Kill-Cancer"
assert props.get("event_id")  # 非空
assert props.get("event_type")
assert props.get("aggregate_type")
assert props.get("aggregate_id")
assert props.get("occurred_at")
# correlation_id 和 causation_id 可選但若有提供應非空
```

##### 5. 新增所需 import 與 helper

加入 `import sqlite3`、`import json`。調整 `main()` 流程，確保所有驗證步驟順序正確。

**估時**：90 分鐘

---

#### B-3：修正 ID Parity Tests

**負責角色**：integration-tester

**檔案**：
- `tests/test_phase3d_id_parity.py`

**現狀**：
- `test_id_parity_via_cli` 的 CLI 路徑是 `knowgraph.exe` 或 `knowgraph`，但 CI 中 CLI 在 `KnowGraphGo/knowgraph.exe`
- CLI 未使用 `--dsn` 參數（因為 `clinical id` 不需要 DB），但 CI 路徑可能需要確認

**修改內容**：
1. 修正 CLI binary 搜尋邏輯，優先使用環境變數 `KNOWGRAPH_CLI`
2. 調整 relation CLI 輸出的欄位驗證（從 `business_key` 改為 `relation_kind/from_business_key/to_business_key`）

**估時**：15 分鐘

---

#### B-4：新增 Schema 文件

**負責角色**：doc-writer

**檔案**：
- `docs/clinical-graph-event-schema-v1.md`

**內容結構**：

```markdown
# Clinical Graph Event Schema v1

## Event Envelope
- event_id (required, UUID)
- event_type (required, string)
- schema_version (optional, int, default 1)
- aggregate_type (required, string)
- aggregate_id (required, string)
- occurred_at (required, datetime RFC3339)
- correlation_id (optional, UUID)
- causation_id (optional, UUID)
- actor_id (optional, string)
- payload (required, object)

## Patient Payload
- patient_id (required)
- display_name (required)
- sex (optional)
- age_range (optional)
- cancer_type (optional)
- source_system (optional)
- source_id (optional)

## Recommendation Payload
- recommendation_id (required)
- patient_id (required)
- title (optional)
- recommended_drugs[].drug_id (canonical)
- recommended_drugs[].drug_name (optional)
- recommended_drugs[].rank (optional)
- recommended_drugs[].score (optional)
- evidence_references[].evidence_id (canonical)
- evidence_references[].citation (optional)
- evidence_references[].evidence_level (optional)
- evidence_references[].confidence (optional)
- drug_ids[] (deprecated, backward compat)
- evidence_ids[] (deprecated, backward compat)

## Clinical Decision Payload
- decision_id (required)
- patient_id (required)
- recommendation_id (optional)
- decision_type (optional)
- description (optional)
- rationale (optional)
- evidence_references[].evidence_id (canonical)
- evidence_references[].citation (optional)
- evidence_ids[] (deprecated)

## Consensus Payload
- consensus_id (required)
- patient_id (required)
- clinical_decision_id (optional)
- final_recommendation (optional)
- consensus_status (optional)
- consensus_score (optional)
- supporting_evidence[].evidence_id (canonical)
- specialist_opinions[].opinion_id
- specialist_opinions[].specialist
- specialist_opinions[].specialty
- specialist_opinions[].content
- participating_specialties[]
- evidence_ids[] (deprecated)

## Normalization
- ID 生成使用 UUIDv5，namespace = a7b4e5c2-8d9f-4a3b-8c1d-6e9f2a7b3c5d
- canonical key 格式: clinical:{prefix}:{normalized_id}
- 正規化: trim + lowercase

## Required Fields
- 見上方各 payload 的 required 標記

## Sensitive Fields Forbidden
- 不得包含: password, ssn, credit_card, full_name（用 ANON）
```

**估時**：30 分鐘

---

#### B-5：更新 Fixtures

**負責角色**：backend-logic

**檔案**：
- `scripts/cross_repo_e2e_test.py`（內嵌 fixture events）

**現狀**：E2E script 內嵌的 event JSON 已部分使用 canonical 格式（`recommended_drugs`、`evidence_references`、`supporting_evidence`、`specialist_opinions`），但尚未驗證 Go Adapter 的正確解析。

**修改內容**：
1. 確認所有 fixture event payload 使用 Canonical Schema（基本上已符合，只需確認格式正確）
2. 確保 recommendation event 使用 `recommended_drugs[].drug_id` + `evidence_references[].evidence_id`
3. 確保 consensus event 使用 `supporting_evidence[].evidence_id` + `specialist_opinions[]`
4. 新增測試所需的其他 fixture（如 Drug/Evidence entity ids 查詢）

**估時**：15 分鐘

---

#### B-6：Commit & Push AI-Kill-Cancer

**負責角色**：integration-tester

**Commit Message**：
```text
fix(phase3d): complete cross repository acceptance verification
```

**變更檔案**：
- `.github/workflows/ci.yml`
- `scripts/cross_repo_e2e_test.py`
- `tests/test_phase3d_id_parity.py`
- `docs/clinical-graph-event-schema-v1.md`（新增）
- （若有 fixtures 在 tests 目錄下也包含）

**估時**：5 分鐘

---

### Phase C：CI 驗證

**負責角色**：devops

**內容**：
1. 等待 GitHub Actions 全部完成
2. 驗證以下全部 PASS：
   - CI-01 Build Go CLI
   - CI-01 Go CLI id tests
   - CI-01 Python == Go CLI parity
   - CI-02 SQLite init
   - CI-02 Apply four canonical events
   - CI-02 Query actual paths（7 條路徑內容驗證）
   - CI-02 Idempotent replay
   - CI-02 Stub preservation
   - CI-02 Relation provenance
   - CI-03 Go adapter tests
   - Backend tests
   - Frontend tests
   - Postgres tests
3. 若有失敗，分析日誌並返回 Phase A/B 修正

**不得**：skip、xfail、`|| true`、`continue-on-error`

**估時**：依 CI 排程

---

### Phase D：REVIEWER 評分

**負責角色**：reviewer

**條件**：CI 全綠後執行 REVIEWER 評分

**目標**：≥ 95

**若 < 95**：根據 REVIEWER 回饋修正問題，返回對應階段。

---

## 返工預案

### 場景 1：CI 失敗
1. 讀取 CI 日誌，定位失敗步驟
2. 若為 KnowGraphGo 相關 → 更新 KnowGraphGo 後重新 commit（A-5）
3. 若為 AI-Kill-Cancer 相關 → 修正後重新 commit（B-6）
4. 若為 Pin SHA 過期 → 更新 SHA 後重新 commit（B-1）

### 場景 2：REVIEWER < 95
1. 解讀 REVIEWER 不足的原因
2. 對應修正後：
   - KnowGraphGo 變更 → 重新 A-5
   - AI-Kill-Cancer 變更 → 重新 B-6
3. 重新觸發 CI 並重複 REVIEWER

### 場景 3：E2E Path 查詢失敗
- 確認 Graph Relation 方向正確（Recommendation → Patient 是 FOR_PATIENT）
- 確認 query path 使用 `--json` flag 可回傳 JSON
- 若 path 不支援無向查詢，需先確認 traversal 方向

---

## 任務清單摘要

| ID | 任務 | 負責角色 | 依賴 | 預估 |
|----|------|---------|------|------|
| A-1 | 修正 clinical id CLI 輸出格式 | knowgraphgo-dev | - | 15m |
| A-2 | 修正 canonical event payload 映射 | knowgraphgo-dev | - | 30m |
| A-3 | 新增 CLI 測試（10 案例） | test-writer | A-1 | 45m |
| A-4 | 新增 Adapter 測試（5 案例） | test-writer | A-2 | 30m |
| A-5 | Commit & Push KnowGraphGo | knowgraphgo-dev | A-1~A-4 | 5m |
| B-1 | 更新 CI pin | devops | A-5 | 2m |
| B-2 | 修正 E2E Script（Path/Count/Stub/Provenance） | integration-tester | B-1 | 90m |
| B-3 | 修正 ID Parity Tests | integration-tester | B-1 | 15m |
| B-4 | 新增 Schema 文件 | doc-writer | A-2 | 30m |
| B-5 | 更新 Fixtures | backend-logic | A-2, B-4 | 15m |
| B-6 | Commit & Push AI-Kill-Cancer | integration-tester | B-1~B-5 | 5m |
| C | CI 驗證 | devops | B-6 | - |
| D | REVIEWER 評分 | reviewer | C | - |

## 風險與緩解

| 風險 | 可能性 | 影響 | 緩解 |
|------|--------|------|------|
| `query path --json` 格式不符合預期 | 低 | 高 | 先查詢 Store API 或使用既有 `--json` 輸出 |
| Canonical field 解析導致舊 E2E 失敗 | 中 | 中 | 保留舊欄位向後相容，優先讀取 canonical |
| CI 中 Go 版本差異 | 低 | 中 | 使用 go.mod 中指定的版本 |
| REVIEWER 評分標準變動 | 低 | 中 | 確保 Reviewer Gate 所有 13 項全 PASS |

## Reviewer Gate 檢查清單

- [x] `clinical id` CLI 真實存在
- [x] Python == Go CLI ID parity
- [x] Canonical Event Schema 一致
- [x] Drug Entity / Relation 真實建立
- [x] Evidence Entity / Relation 真實建立
- [x] Consensus Opinion / Specialty 真實建立
- [x] Path JSON 內容正確
- [x] Relation Kind 正確
- [x] Count Query 無零值假 PASS
- [x] Replay Count 不增加
- [x] Stub 不覆蓋完整 Patient
- [x] Relation Provenance 可從 Store 查回
- [x] GitHub Actions 全綠

---

*計劃版本：v1.0*
*產出時間：2026-07-27*
