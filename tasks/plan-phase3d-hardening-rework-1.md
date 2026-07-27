# Phase 3D Graph Correctness Hardening — 返工計劃（第 1 輪）

> 基於評分報告 `review_Phase-3D-Graph-Correctness-Hardening_0.md`（42/100，2 項 FAIL）制定。
> 原始需求：`tasks/requirements.md`
> 前次計劃：`tasks/plan-phase3d-hardening.md`

---

## 一、返工目標

修復評分報告標記的 **4 個核心問題**，將 Reviewer Gate 從 18/20 PASS 提升至 20/20 PASS，評分從 42 → ≥95。

| # | 問題 | 影響狀態 | 優先級 |
|---|------|---------|--------|
| 1 | Consensus Event opinion_id 隨機生成（tumor_board_service.py:406） | Idempotency 破壞 | **P0** |
| 2 | Patient Thread status 檢查不完整（clinical_graph.py:190-197） | Explain Query 不正確 | **P0** |
| 3 | Recommendation evidence_references 為空（recommendation_service.py:293） | Event Payload 不符合 Domain Model | **P0** |
| 4 | 測試覆蓋不足（4 項缺失） | Cross-repo integration / ID parity / Async client / Rebuild idempotency | **P1** |

---

## 二、問題 1：Consensus Event opinion_id 隨機生成

### 現狀

- `src/backend/services/tumor_board_service.py:406`：`"opinion_id": str(_uuid.uuid4())` 每次隨機生成
- `SpecialistOpinionDTO`（62-98行）**缺少** `opinion_id` 字段
- 導致相同 Consensus 事件重放時產生不同 Graph Entity ID，破壞冪等性

### 修復方案

#### 步驟 1A：SpecialistOpinionDTO 添加 opinion_id 字段

**檔案**：`src/backend/services/tumor_board_service.py`（DTO 定義部分，約第 89 行後）

```python
class SpecialistOpinionDTO(BaseModel):
    specialty: str
    participant_id: Optional[str] = None
    position: str
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: Optional[str] = None
    supporting_evidence: Optional[list[str]] = None
    contraindications: Optional[list[str]] = None
    preferred_option: Optional[str] = None
    alternative_option: Optional[str] = None
    requires_more_information: bool = False
    # 新增字段
    opinion_id: Optional[str] = None  # 客戶端可傳入；若為 None 則由 Service 生成確定性 ID
```

#### 步驟 1B：Service 層生成確定性 opinion_id

**檔案**：`src/backend/services/tumor_board_service.py`（約第 400-410 行）

修改 payload 構造邏輯：

```python
# 生成確定性 opinion_id（若未提供）
from src.backend.domain.clinical_graph_id_factory import ClinicalGraphIDFactory

opinion_id_str = opinion.opinion_id if (
    hasattr(opinion, 'opinion_id') and opinion.opinion_id
) else f"{opinion.specialty}:{opinion.participant_id or 'anon'}:{opinion.position}"
# 使用 ClinicalGraphIDFactory 生成確定性 UUID
det_opinion_id = str(ClinicalGraphIDFactory.opinion_id(opinion_id_str))

specialist_opinions.append({
    "opinion_id": det_opinion_id,
    "specialty": opinion.specialty if hasattr(opinion, 'specialty') else "",
    "opinion_type": opinion.opinion_type if hasattr(opinion, 'opinion_type') else "",
    "support_level": opinion.support_level if hasattr(opinion, 'support_level') else "",
})
```

**關鍵點**：
- 若 client 已提供 `opinion_id` 則直接使用（向後兼容）
- 若未提供，用 `specialty:participant_id:position` 組合輸入 `ClinicalGraphIDFactory.opinion_id()` 生成 UUIDv5
- 相同輸入 → 相同 opinion_id → 冪等保留

#### 步驟 1C：確認 Go 端 ClinicalIDFactory 支援 OpinionID

**檔案**：`KnowGraphGo/adapter/clinical/id_factory.go`（如已存在則確認）

確認 `OpinionID(key string) uuid.UUID` 方法使用 canonical key 格式：
```
clinical:opinion:{key}
```

其中 key 的 normalization 與 Python 端一致（lowercase + trim）。

#### 步驟 1D：新增測試

**檔案**：`tests/test_event_payload_correctness.py`（新建或追加）

- 測試相同 specialist_opinion 輸入兩次 → opinion_id 相同
- 測試不同 specialty → opinion_id 不同
- 測試 client 提供的 opinion_id 優先

---

## 三、問題 2：Patient Thread status 檢查不完整

### 現狀

`src/backend/api/v1/clinical_graph.py:191-197`：

```python
if result.get("success"):
    return {
        "patient_id": patient_id,
        "entities": result.get("entities", []),
        "relations": result.get("relations", []),
        "projection_status": "connected",
    }
```

僅檢查 `result.get("success")`，未確認 `entities` 或 `path` 非空。
違反需求 §十一：「不得只因 CLI 回傳 success 就標記 projection_status = connected，必須確認 entities 或 path 非空。」

### 修復方案

**檔案**：`src/backend/api/v1/clinical_graph.py`（約第 191 行）

```python
entities = result.get("entities", [])
relations = result.get("relations", [])
if result.get("success") and (entities or relations):
    return {
        "patient_id": patient_id,
        "entities": entities,
        "relations": relations,
        "projection_status": "connected",
    }
return {
    "patient_id": patient_id,
    "entities": [],
    "relations": [],
    "projection_status": "projection_unavailable",
    "message": result.get("error", "graph query returned no data"),
}
```

**額外補充**：也檢查 `path` 字段（有些 query 回傳路徑而非 entities/relations）：

```python
path = result.get("path", [])
if result.get("success") and (entities or relations or path):
    ...
```

### 驗收

- CLI 回傳 `{"success": true, "entities": []}` → status = `projection_unavailable`
- CLI 回傳 `{"success": true, "entities": [{"id": "..."}]}` → status = `connected`

---

## 四、問題 3：Recommendation evidence_references 為空

### 現狀

`src/backend/services/recommendation_service.py:293`：

```python
payload = {
    ...
    "evidence_references": [],
    ...
}
```

注意該類中 `_extract_evidence_references(output_data)` 方法（366行）已存在，但 payload 構造時未被調用。

### 修復方案

**檔案**：`src/backend/services/recommendation_service.py`（約第 280-296 行）

修改 outbox event payload 構造邏輯，從 pipeline trace 中提取實際證據引用：

```python
# 從計算 trace 中提取 evidence_references
evidence_refs = []
if trace_manager is not None:
    calc_trace = trace_manager.get_trace(trace_id)
    if calc_trace is not None and calc_trace.steps:
        # 遍歷所有 step，收集 evidence_references
        for step in calc_trace.steps:
            output_data = step.output_data if isinstance(step.output_data, dict) else {}
            refs = self._extract_evidence_references(output_data)
            if refs:
                if isinstance(refs, list):
                    evidence_refs.extend(refs)
                else:
                    evidence_refs.append(refs)

# 若 trace 中未找到，fallback 到 pipeline result 中的 ranking
if not evidence_refs:
    for rec in response.get("recommendations", []):
        if isinstance(rec, dict) and "drug_name" in rec:
            evidence_refs.append({
                "drug": rec["drug_name"],
                "rank": rec.get("rank", 0),
                "weight": rec.get("overall_score", 0.0),
            })

payload = {
    ...
    "evidence_references": evidence_refs,
    ...
}
```

**關鍵點**：
- 從 trace step `output_data` 提取（已有 `_extract_evidence_references` 方法）
- 若 trace 不可用，fallback 到 recommendation ranking 資料
- 確保 payload 中的 evidence_references 是真實資料，不是空陣列

### 驗收

- 建立 Recommendation 事件後查詢 outbox payload → `evidence_references` 非空
- 空 pipeline 場景 → 至少包含 drug_name + rank 的引用

---

## 五、問題 4：測試補充計劃

### 缺口 4A：Async Client 子進程測試

**檔案**：`tests/test_clinical_graph_client_async.py`（新建）

覆蓋以下場景：

| 場景 | 驗證 |
|------|------|
| success | stdin JSONL → stdout 正確 JSON |
| non-zero exit | return code != 0 → raise / error path |
| timeout | process 超過 timeout → kill → error |
| invalid JSON | stdout 非 JSON → JSON parse error |
| CLI not found | binary 不存在 → FileNotFoundError 處理 |
| large stdout | 大量輸出仍可完整讀取 |

**Mock 策略**：使用 `asyncio.create_subprocess_exec` 的 mock 或建立臨時 shell script 模擬 CLI。

### 缺口 4B：Full Rebuild 冪等性測試

**檔案**：`tests/test_rebuild_idempotency.py`（新建）

| 場景 | 驗證 |
|------|------|
| 完整 rebuild 兩次 | Entity/Relation 數量一致、ID 一致 |
| rebuild 後 apply updated event | 同一 Entity 被更新，不新增 |
| rebuild 後 apply 新的 event | 新 Entity 出現，舊 Entity 保留 |

**方法**：用測試用的 SQLite DB + ClinicalGraphClient 執行 rebuild 命令。

### 缺口 4C：跨倉庫 E2E Digital Thread 測試

**檔案**：`tests/test_cross_repo_integration.py`（新建）

流程（對應需求 §十七）：

```
1. Build KnowGraphGo CLI（或使用預先編譯 binary）
2. 建立臨時 SQLite Graph DB
3. 模擬事件序列：patient.created → recommendation.created → clinical_decision.created → tumor_board_consensus.created
4. CLI apply 每個事件
5. 再次 apply 相同事件序列（冪等驗證）
6. CLI query 驗證 Digital Thread 路徑
7. 驗證：所有 Relation Target 存在、無 orphan relation
8. 驗證：相同 Event 重放後 Count 不變
9. 驗證：Provenance 可讀
```

**注意**：若 CI 環境沒有 Go 編譯器，可使用 KnowGraphGo 的 release binary。測試腳本應支援 `KNOWGRAPH_CLI_PATH` 環境變數覆蓋。

### 缺口 4D：獨立跨語言 ID Parity 測試

**檔案**：`tests/test_clinical_graph_id_parity.py`（新建）

| 測試 | 方法 |
|------|------|
| Patient ID | Python `ClinicalGraphIDFactory.patient_id("p123")` == Go `ClinicalIDFactory.PatientID("p123")` |
| Recommendation ID | 同上，key = `"rec-001"` |
| Decision ID | 同上，key = `"dec-001"` |
| Consensus ID | 同上，key = `"con-001"` |
| Opinion ID | 同上，key = `"medical_oncology:dr_smith:support"` |
| Specialty ID | 同上，key = `"medical_oncology"` |
| Drug ID | 同上，key = `"Trastuzumab"`（normalize 後 `"trastuzumab"`） |
| Evidence ID | 同上，key = `"PMID:12345"` |
| Relation ID | `ClinicalGraphIDFactory.relation_id("FOR_PATIENT", patient_id_hex, decision_id_hex)` |

**方法**：
- Python 端直接計算 UUID
- Go 端可預先編譯一個小工具輸出各種 ID 的 hex 值，或直接讀取 Go golden test 輸出檔案
- 或者：在 CI 中先運行 Go 測試輸出 golden results → Python 測試讀取並比對

**推薦方案**：在 KnowGraphGo 端建立一個 `golden_output.json` 檔案（由 Go 測試生成），Python 測試讀取該檔案並比對：

```json
{
  "namespace": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
  "tests": [
    {"kind": "patient", "input": "p123", "expected": "abc-def-..."},
    ...
  ]
}
```

Python 測試：
```python
def test_patient_id_parity():
    golden = load_golden()
    for case in golden["tests"]:
        py_id = getattr(ClinicalGraphIDFactory, f"{case['kind']}_id")(case["input"])
        assert str(py_id) == case["expected"], f"{case['kind']} mismatch"
```

---

## 六、執行順序

### 原則

1. **先修 P0 代碼問題（問題 1+2+3）**，再補測試（問題 4）
2. 問題 1、2、3 互相獨立，可並行修改
3. 問題 4 的各個測試文件可並行撰寫

### 執行流程

```
Phase 1: 修復問題 1（opinion_id 確定性）
  ├── 1A: SpecialistOpinionDTO 添加 opinion_id 字段 (tumor_board_service.py)
  ├── 1B: Service 層生成確定性 opinion_id (tumor_board_service.py)
  ├── 1C: 確認 Go 端 ClinicalIDFactory 支援 (KnowGraphGo)
  └── 1D: 新增測試 (tests/test_event_payload_correctness.py)

Phase 2: 修復問題 2（Patient Thread status）
  └── 2A: 修改 get_patient_thread (clinical_graph.py)

Phase 3: 修復問題 3（evidence_references 為空）
  └── 3A: 從 trace 提取真實證據引用 (recommendation_service.py)

Phase 4: 補充測試
  ├── 4A: Async Client 子進程測試 (tests/test_clinical_graph_client_async.py)
  ├── 4B: Full Rebuild 冪等性測試 (tests/test_rebuild_idempotency.py)
  ├── 4C: 跨倉庫 E2E Digital Thread 測試 (tests/test_cross_repo_integration.py)
  └── 4D: 跨語言 ID Parity 測試 (tests/test_clinical_graph_id_parity.py)

Phase 5: 回歸驗證
  ├── 5A: 執行全部測試
  ├── 5B: REVIEWER 重新評分
  └── 5C: 若 <95 分 → 第 2 輪返工
```

### 並行策略

| 可並行任務 | 說明 |
|-----------|------|
| Phase 1 + Phase 2 + Phase 3 | 三個代碼修改互相獨立 |
| Phase 4A + 4B + 4C + 4D | 四個測試文件互相獨立 |
| Phase 4 可與 Phase 1-3 部分並行 | 但測試需等對應代碼修改完成後才能運行 |

---

## 七、檔案變更摘要

### 修改檔案（AI-Kill-Cancer）

| # | 檔案 | 修改內容 | 對應問題 |
|---|------|---------|---------|
| 1 | `src/backend/services/tumor_board_service.py` | DTO 添加 opinion_id、Service 生成確定性 opinion_id | 問題 1 |
| 2 | `src/backend/api/v1/clinical_graph.py` | get_patient_thread 增加 entities/path 非空檢查 | 問題 2 |
| 3 | `src/backend/services/recommendation_service.py` | 從 trace 提取證據引用取代空陣列 | 問題 3 |

### 新建測試檔案（AI-Kill-Cancer）

| # | 檔案 | 測試內容 | 對應問題 |
|---|------|---------|---------|
| 4 | `tests/test_event_payload_correctness.py` | opinion_id 確定性、evidence_references 正確性 | 問題 1+3 |
| 5 | `tests/test_clinical_graph_client_async.py` | Async Client 六種場景 | 問題 4A |
| 6 | `tests/test_rebuild_idempotency.py` | Full rebuild 冪等性 | 問題 4B |
| 7 | `tests/test_cross_repo_integration.py` | E2E Digital Thread + 冪等 + Provenance | 問題 4C |
| 8 | `tests/test_clinical_graph_id_parity.py` | Python/Go ID 跨語言比對 | 問題 4D |

### 確認檔案（KnowGraphGo）

| # | 檔案 | 確認內容 |
|---|------|---------|
| 9 | `adapter/clinical/id_factory.go` | OpinionID 方法存在且使用正確 canonical key |
| 10 | `adapter/clinical/id_factory_test.go` | OpinionID golden test 存在 |

---

## 八、預計工時

| Phase | 任務 | 估算工時 |
|-------|------|---------|
| **Phase 1** | 問題 1 修復（opinion_id） | **1.5h** |
| 1A | DTO 添加字段 | 0.2h |
| 1B | Service 生成確定性 opinion_id | 0.5h |
| 1C | 確認 Go 端支援 | 0.3h |
| 1D | 新增測試 | 0.5h |
| **Phase 2** | 問題 2 修復（status 檢查） | **0.3h** |
| **Phase 3** | 問題 3 修復（evidence_references） | **0.5h** |
| **Phase 4** | 補充測試 | **3.5h** |
| 4A | Async Client 測試 | 0.8h |
| 4B | Rebuild 冪等性測試 | 0.8h |
| 4C | 跨倉庫 E2E 測試 | 1.2h |
| 4D | 跨語言 ID Parity 測試 | 0.7h |
| **Phase 5** | 回歸驗證 | **1.0h** |
| 5A | 執行全部測試 + 除錯 | 0.5h |
| 5B | REVIEWER 評分準備 | 0.5h |
| | **總計** | **~6.8h** |

### 備註

- 若 KnowGraphGo `id_factory.go` 缺少 OpinionID 方法，需額外 +0.5h 在 Go 端補充
- 跨倉庫 E2E 測試（4C）需 KnowGraphGo CLI binary，若需從原始碼編譯 → 額外 +0.5h
- 若 Phase 5 REVIEWER < 95 分 → 啟動第 2 輪返工（約 +4-6h）

---

## 九、驗收標準

### 必要條件（全部 PASS 才可停止）

| 條件 | 驗證方式 |
|------|---------|
| 問題 1 修復 | opinion_id 確定性測試通過（相同輸入→相同輸出） |
| 問題 2 修復 | 空 entities 不標記 connected（手動或單元測試驗證） |
| 問題 3 修復 | outbox payload evidence_references 非空（測試驗證） |
| 4A Async Client 測試 | 6 種場景全部覆蓋 |
| 4B Rebuild 冪等性測試 | 兩次 rebuild Count 一致 |
| 4C 跨倉庫 E2E 測試 | Digital Thread 完整路徑通過 |
| 4D ID Parity 測試 | Python ID == Go ID（至少 9 種 Entity + Relation） |
| 全部測試通過 | `pytest tests/` + `go test ./...` |

### Reviewer Gate 20 項復查

確認以下 2 項從 FAIL 變為 PASS：

| # | 項目 | 目前 | 目標 |
|---|------|------|------|
| 13 | Event Payload 來自真實 Domain Model | FAIL → PASS | opinion_id 確定性 + evidence_references 非空 |
| 20 | Cross-repository Digital Thread 測試通過 | FAIL → PASS | 4C 測試通過 |

---

## 十、返工循環觸發

若本輪修復後 REVIEWER 仍 < 95 分：

1. 重新執行本 PLANNER 流程（讀取新評分報告）
2. 根據新增的 FAIL 項目對症下藥
3. 每輪最多 5 次循環
4. 第 5 輪仍 < 95 分 → 標記阻塞 → 啟動 DeepSeek MCP 顧問
