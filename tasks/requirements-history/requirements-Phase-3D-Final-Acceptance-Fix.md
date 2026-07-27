# AI-Kill-Cancer × KnowGraphGo — Phase 3D Final Acceptance Fix

AI-Kill-Cancer Repository：

```text
https://github.com/liuxb99/AI-Kill-Cancer
```

AI-Kill-Cancer Branch：

```text
master
```

AI-Kill-Cancer Base Commit：

```text
fea2c02aa75def0b5e48fd821a6b8a77d24c1407
```

KnowGraphGo Repository：

```text
https://github.com/liuxb99/KnowGraphGo
```

KnowGraphGo Branch：

```text
main
```

KnowGraphGo Base Commit：

```text
d6fa05a7d13ec3d51473c737ab4ebe3482ac2950
```

目前審查結果：

```text
Phase 3D Final Acceptance：PARTIAL
ChatGPT Review：86/100
Accepted：NO
Ready for Treatment Plan：NO
```

本輪唯一目標：

```text
修正最後四個驗收缺口
```

不得新增功能。

不得重構 Outbox。

不得修改已驗收的 Clinical Domain 功能。

不得開始 Treatment Plan。

---

# 一、工作方式

依兩個 Repository 各自既有流程執行。

一次完成。

不要中途回報。

完成兩個 Repository、Commit、Push、GitHub Actions 後一次回報。

本輪只允許修改：

## KnowGraphGo

```text
Clinical CLI
Clinical Adapter payload mapping
Clinical tests
```

## AI-Kill-Cancer

```text
Cross-repository E2E script
ID parity tests
CI workflow
Canonical event schema／fixtures（必要時）
```

---

# 二、P0-1：真正實作 `clinical id` CLI

目前 Python 測試會執行：

```text
knowgraph clinical id patient P001
```

但 KnowGraphGo 的 CLI 只支援：

```text
apply
rebuild
verify
```

必須在 KnowGraphGo 正式新增：

```text
knowgraph clinical id <kind> <business-key>
```

至少支援：

```text
patient
recommendation
decision
consensus
opinion
specialty
drug
evidence
variant
```

以及 Relation：

```text
knowgraph clinical id relation <relation-kind> <from-business-key> <to-business-key>
```

---

## Entity CLI 回傳格式

例如：

```bash
knowgraph clinical id patient P001
```

必須輸出：

```json
{
  "kind": "patient",
  "business_key": "P001",
  "graph_id": "02fe1d2a-da12-5f27-a5ff-01d5ded671a5"
}
```

Relation：

```bash
knowgraph clinical id relation FOR_PATIENT REC-001 P001
```

回傳：

```json
{
  "kind": "relation",
  "relation_kind": "FOR_PATIENT",
  "from_business_key": "REC-001",
  "to_business_key": "P001",
  "graph_id": "..."
}
```

要求：

```text
JSON 永遠有效
錯誤輸出到 stderr
錯誤時 exit code != 0
空 ID 正常回傳 validation error
不得 panic
```

同步更新 CLI Usage。

---

## CLI 測試

新增 Go CLI tests：

```text
每一種 Entity Kind
Relation
大小寫／空白正規化
空 key
未知 kind
參數不足
JSON schema
Exit code
```

不得只測 `ClinicalIDFactory`。

必須測真正的 CLI handler。

---

# 三、P0-2：統一 Event Payload Schema

目前 AI-Kill-Cancer E2E 傳入：

```text
recommended_drugs
evidence_references
supporting_evidence
specialist_opinions
```

但 Go Adapter 主要讀取：

```text
drug_ids
evidence_ids
```

兩邊契約不一致。

必須定義一份正式 Canonical Schema。

建議以 AI-Kill-Cancer 的正式 Domain Payload 為準：

## Recommendation Event

```json
{
  "recommendation_id": "REC-001",
  "patient_id": "P001",
  "title": "Recommendation",
  "recommended_drugs": [
    {
      "drug_id": "DRUG-001",
      "drug_name": "Olaparib",
      "rank": 1,
      "score": 0.95
    }
  ],
  "evidence_references": [
    {
      "evidence_id": "EV-001",
      "citation": "Study XYZ",
      "evidence_level": "high",
      "confidence": 0.9
    }
  ]
}
```

## Clinical Decision Event

```json
{
  "decision_id": "DC-001",
  "patient_id": "P001",
  "recommendation_id": "REC-001",
  "decision_type": "APPROVED",
  "description": "Clinical decision",
  "rationale": "Based on evidence",
  "evidence_references": [
    {
      "evidence_id": "EV-001",
      "citation": "Study XYZ"
    }
  ]
}
```

## Consensus Event

```json
{
  "consensus_id": "CON-001",
  "patient_id": "P001",
  "clinical_decision_id": "DC-001",
  "final_recommendation": "Approve Olaparib",
  "consensus_status": "strong_consensus",
  "consensus_score": 0.92,
  "supporting_evidence": [
    {
      "evidence_id": "EV-001"
    }
  ],
  "specialist_opinions": [
    {
      "opinion_id": "OP-001",
      "specialist": "Dr. Smith",
      "specialty": "medical_oncology",
      "content": "Agree"
    }
  ],
  "participating_specialties": [
    "medical_oncology"
  ]
}
```

---

## Go Adapter 要求

Go Adapter 必須直接解析這些正式欄位：

```text
recommended_drugs[].drug_id
evidence_references[].evidence_id
supporting_evidence[].evidence_id
specialist_opinions[]
```

可以保留舊欄位作向後相容：

```text
drug_ids
evidence_ids
```

但正式 E2E 必須使用 Canonical Schema。

不得只修改 E2E 腳本去迎合舊 Adapter，卻不符合 AI-Kill-Cancer 真實 Event Service。

---

## Schema 文件

新增：

```text
docs/clinical-graph-event-schema-v1.md
```

至少定義：

```text
event envelope
patient payload
recommendation payload
clinical decision payload
consensus payload
normalization
required fields
optional fields
sensitive fields forbidden
```

Python Event Service、Go Adapter 與 E2E fixture 必須以同一 schema 為準。

---

# 四、P1-1：Path 測試必須驗證真實內容

目前 E2E 只做：

```python
stdout, rc = query_path(...)
assert rc == 0
```

這不足。

必須改成 JSON Query，解析實際內容。

如果 KnowGraphGo Query CLI 目前不支援 JSON，補上：

```text
--json query path
```

或使用既有 JSON 輸出契約。

至少驗證：

```text
path found = true
nodes 非空
edges 非空
起點 ID 正確
終點 ID 正確
Relation Kind 正確
```

---

## 路徑方向

正式 Graph Relation 是：

```text
Recommendation → Patient
ClinicalDecision → Recommendation
Consensus → ClinicalDecision
```

因此 E2E 查詢必須使用正確方向，或明確確認 Query 是無向。

建議直接驗證實際 Relation：

```text
Recommendation ─FOR_PATIENT→ Patient
ClinicalDecision ─BASED_ON→ Recommendation
Consensus ─DERIVED_FROM→ ClinicalDecision
```

不要用名稱相反但語義不清楚的：

```text
Patient → Recommendation
Recommendation → Decision
Decision → Consensus
```

除非 Query API 明確回傳反向 traversal，且測試驗證 direction。

---

## Path Test 至少確認

```text
Recommendation → Patient：
包含 FOR_PATIENT

ClinicalDecision → Recommendation：
包含 BASED_ON

Consensus → ClinicalDecision：
包含 DERIVED_FROM
```

以及：

```text
Recommendation → Drug：
包含 RECOMMENDS

Recommendation → Evidence：
包含 SUPPORTED_BY

Consensus → Opinion：
包含 HAS_OPINION

Opinion → Specialty：
包含 PROVIDED_BY_SPECIALTY
```

不能只確認任意 Path 存在。

---

# 五、P1-2：Count Query 失敗必須直接 Fail

目前 `query_count()` 失敗時回傳：

```json
{
  "entities": 0,
  "relations": 0
}
```

這會導致兩次查詢都失敗時：

```text
0 == 0
```

錯誤判定冪等 PASS。

必須改成：

```text
check command non-zero
→ raise / exit test failure

JSON parse failure
→ raise / exit test failure

必要欄位不存在
→ raise / exit test failure
```

並驗證：

```text
entities > 0
relations > 0
```

---

## Replay 驗收

第一次 apply 後：

```text
entity_count > 0
relation_count > 0
```

第二次 replay 後：

```text
entity_count 完全相同
relation_count 完全相同
```

此外必須檢查 CLI apply 結果：

第一次：

```text
created > 0
```

第二次：

```text
created = 0
updated > 0
```

若 Importer 回傳欄位可取得，應直接 assert。

---

# 六、Stub Preservation 真實驗證

目前 Go unit test 有 Stub 測試，但 Cross-repository E2E 也必須驗證。

流程：

```text
patient.created
→ display_name = ANON
→ sex = F
→ age_range = 40-50
→ cancer_type = BRCA

recommendation.created
→ 會附帶 Patient stub

再查 Patient Entity
```

必須確認：

```text
display_name 仍是 ANON
sex 仍是 F
age_range 仍是 40-50
cancer_type 仍是 BRCA
```

不得只驗證 Entity Count 不變。

---

# 七、Relation Provenance E2E 驗證

至少從 SQLite Graph 查回一條 Relation，確認 Properties 包含：

```text
source_system
event_id
event_type
aggregate_type
aggregate_id
correlation_id（若有）
causation_id（若有）
occurred_at
```

驗證：

```text
Recommendation → Patient
或
Consensus → Decision
```

不得只依 Go unit test。

---

# 八、CI 修正順序

先完成 KnowGraphGo：

```text
clinical id CLI
Canonical Payload Adapter
CLI tests
Adapter tests
```

建立 Commit：

```text
fix(clinical): add id cli and canonical event schema
```

推送到：

```text
origin/main
```

取得完整 SHA。

然後 AI-Kill-Cancer：

```text
更新 CI pin 到新的 KnowGraphGo SHA
修正 E2E Script
修正 parity tests
新增 schema 文件／fixtures
```

建立 Commit：

```text
fix(phase3d): complete cross repository acceptance verification
```

推送到：

```text
origin/master
```

---

# 九、GitHub Actions 必須真正執行

最新版 AI-Kill-Cancer CI 必須成功執行：

```text
CI-01 Build Go CLI
CI-01 Go CLI id tests
CI-01 Python == Go CLI parity
CI-02 SQLite init
CI-02 Apply four canonical events
CI-02 Query actual paths
CI-02 Idempotent replay
CI-02 Stub preservation
CI-02 Relation provenance
CI-03 Go adapter tests
Backend tests
Frontend tests
Postgres tests
```

不得：

```text
skip
xfail
|| true
continue-on-error
只看 exit code 不看輸出
```

---

# 十、禁止事項

不得：

```text
新增 Treatment Plan
新增其他 API
改 Outbox 架構
改 Recommendation／Decision／Consensus 核心
改 Migration 017～022
降低 CI 標準
刪除失敗測試
忽略錯誤
```

不得再修改或提交：

```text
AGENTS.md
```

---

# 十一、Reviewer Gate

以下全部 PASS 才可完成：

```text
[ ] `clinical id` CLI 真實存在
[ ] Python == Go CLI ID parity
[ ] Canonical Event Schema 一致
[ ] Drug Entity / Relation 真實建立
[ ] Evidence Entity / Relation 真實建立
[ ] Consensus Opinion / Specialty 真實建立
[ ] Path JSON 內容正確
[ ] Relation Kind 正確
[ ] Count Query 無零值假 PASS
[ ] Replay Count 不增加
[ ] Stub 不覆蓋完整 Patient
[ ] Relation Provenance 可從 Store 查回
[ ] GitHub Actions 全綠
```

任一項：

```text
FAIL
PARTIAL
PENDING
```

則：

```text
滿足需求 = NO
Reviewer 最高 89
Phase 3D = PARTIAL
Ready for Treatment Plan = NO
```

Reviewer 必須：

```text
>=95
```

才可結案。

---

# 十二、完成後只回報

```text
KnowGraphGo Final Commit SHA
AI-Kill-Cancer Final Commit SHA

Clinical ID CLI
Supported ID Kinds
Relation ID CLI

Canonical Schema Version
Recommendation Payload Mapping
Decision Payload Mapping
Consensus Payload Mapping

Python / Go CLI Parity Tests
Go CLI Tests

E2E SQLite DB
Canonical Events Applied
Entity Count First Apply
Relation Count First Apply
Entity Count Replay
Relation Count Replay

Recommendation → Patient
Recommendation → Drug
Recommendation → Evidence
Decision → Recommendation
Consensus → Decision
Consensus → Opinion
Opinion → Specialty

Stub Preservation
Relation Provenance Fields

KnowGraphGo Tests
AI-Kill-Cancer Backend Tests
Frontend Tests
Postgres Tests
Cross-repository E2E Tests

KnowGraphGo CI Run ID
AI-Kill-Cancer CI Run ID
CI Conclusions

Failed Required Steps
Skipped Required Steps

Git Status
Push Results
Reviewer Score
```

最後輸出：

```text
Phase 3D Final Acceptance：
PASS / PARTIAL / FAIL

Phase 3D Accepted：
YES / NO

Ready for ChatGPT GitHub Review：
YES / NO

Ready for Treatment Plan：
YES / NO
```

只有所有驗收與 CI 全綠、Reviewer ≥95，才允許：

```text
Phase 3D Accepted：YES
Ready for Treatment Plan：YES
```

推送後停止。

不得自行開始 Treatment Plan。
