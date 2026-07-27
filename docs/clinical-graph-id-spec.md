# Clinical Graph ID Specification

> **跨语言确定性 ID 生成规范**
>
> 确保 Go (KnowGraphGo) 与 Python (AI-Kill-Cancer) 为相同输入生成完全一致的 UUID。

---

## 1. UUID Namespace

所有 Clinical Graph ID 使用固定的 UUIDv5 Namespace：

```
a7b4e5c2-8d9f-4a3b-8c1d-6e9f2a7b3c5d
```

该 Namespace 在 KnowGraphGo 的 `adapter/clinical/id_factory.go` 中定义为 `ClinicalNamespace`，
Python 端在 `src/backend/clinical_graph/id_factory.py` 中定义为 `CLINICAL_NAMESPACE`。

> **注意**：此 Namespace 是 Clinical 领域专用，与 DNS / URL / OID 等标准 Namespace 不同，
> 确保跨领域 UUIDv5 不冲突。

---

## 2. UUID 版本

使用 **UUIDv5**（基于 SHA-1 哈希的确定性 UUID）。

- Go：`uuid.NewSHA1(ClinicalNamespace, []byte(canonical))`
- Python：`uuid.uuid5(CLINICAL_NAMESPACE, canonical)`

相同输入 → 相同输出。适用于事件溯源重播、跨服务引用。

---

## 3. 输入规范化 (Normalization)

所有原始键值在构造 canonical key 之前必须规范化：

| 规则 | 描述 |
|------|------|
| Trim | 去除首尾空白字符（`TrimSpace` / `strip()`） |
| Lowercase | 转为小写（`ToLower` / `lower()`） |

**Go 实现：**

```go
strings.TrimSpace(strings.ToLower(input))
```

**Python 实现：**

```python
input.strip().lower()
```

---

## 4. Entity ID Canonical Key 格式

```
clinical:{entity_kind}:{normalized_id}
```

| 组成部分 | 说明 |
|----------|------|
| `clinical:` | 固定领域前缀 |
| `{entity_kind}` | 实体种类名称（全小写，见下方对照表） |
| `:` | 分隔符 |
| `{normalized_id}` | 经规范化后的业务主键 |

### Entity Kind / Prefix 对照表

| Entity Kind | Prefix | Go 方法 | Python 方法 |
|-------------|--------|---------|-------------|
| Patient | `patient` | `PatientID(patientID)` | `patient_id(patient_id)` |
| Recommendation | `recommendation` | `RecommendationID(recommendationID)` | `recommendation_id(rid)` |
| Clinical Decision | `decision` | `ClinicalDecisionID(decisionID)` | `clinical_decision_id(did)` |
| Tumor Board Consensus | `consensus` | `ConsensusID(consensusID)` | `consensus_id(cid)` |
| Specialist Opinion | `opinion` | `OpinionID(opinionID)` | `opinion_id(oid)` |
| Specialty | `specialty` | `SpecialtyID(specialty)` | `specialty_id(s)` |
| Drug | `drug` | `DrugID(drugID)` | `drug_id(did)` |
| Evidence | `evidence` | `EvidenceID(evidenceID)` | `evidence_id(eid)` |
| Variant | `variant` | `VariantID(variantID)` | `variant_id(vid)` |

### 示例

```
输入: patient_id = "P12345"
规范化: "p12345"
canonical key: "clinical:patient:p12345"
UUIDv5: 2e8f1c4a-...

输入: recommendation_id = "REC-001"
规范化: "rec-001"
canonical key: "clinical:recommendation:rec-001"
UUIDv5: 7b3d9f1e-...
```

---

## 5. Relation ID Canonical Key 格式

```
clinical:relation:{normalized_kind}:{normalized_from_key}:{normalized_to_key}
```

| 组成部分 | 说明 |
|----------|------|
| `clinical:relation:` | 固定关系前缀 |
| `{normalized_kind}` | 关系种类（规范化后） |
| `{normalized_from_key}` | 起点实体业务键（规范化后） |
| `{normalized_to_key}` | 终点实体业务键（规范化后） |

### 示例

```
输入: kind="treats", from_key="DRUG001", to_key="COND001"
规范化: kind="treats", from="drug001", to="cond001"
canonical key: "clinical:relation:treats:drug001:cond001"
UUIDv5: 5a8c2e3d-...
```

---

## 6. 跨语言一致性要求

### 6.1 生产要求

Go 和 Python 实现必须满足：

1. **相同输入 → 相同输出**：使用相同的 CLINICAL_NAMESPACE、相同的 canonical key 格式、
   相同的规范化规则、相同的 UUIDv5 算法。
2. **跨语言可互换**：Go 生成的 ID 可被 Python 端用于查询，反之亦然。
3. **确定性**：只要输入不变，每次调用返回相同 ID（无随机成分）。

### 6.2 验证测试（建议）

```python
# Python 端验证示例
from src.backend.clinical_graph.id_factory import ClinicalGraphIDFactory

def test_patient_id_deterministic():
    pid1 = ClinicalGraphIDFactory.patient_id("P12345")
    pid2 = ClinicalGraphIDFactory.patient_id("P12345")
    assert pid1 == pid2, "ID must be deterministic"

def test_normalization():
    pid1 = ClinicalGraphIDFactory.patient_id("ABC")
    pid2 = ClinicalGraphIDFactory.patient_id(" abc ")
    assert pid1 == pid2, "Must normalize trim+lowercase"
```

```go
// Go 端验证示例
import "github.com/liuxb99/knowgraphgo/adapter/clinical"

func TestDeterministic(t *testing.T) {
    factory := &clinical.ClinicalIDFactory{}
    id1 := factory.PatientID("P12345")
    id2 := factory.PatientID("P12345")
    if id1 != id2 {
        t.Error("ID must be deterministic")
    }
}
```

### 6.3 跨语言一致性测试

应至少一个测试用例用相同的输入在 Go 和 Python 两端运行，断言输出的 UUID 相同。

| 输入 | Go 方法 | Python 方法 | 预期 UUID |
|------|---------|-------------|-----------|
| `"P001"` | `PatientID("P001")` | `patient_id("P001")` | (运行确定) |
| `"REC-001"` | `RecommendationID("REC-001")` | `recommendation_id("REC-001")` | (运行确定) |
| `"C001"` | `ConsensusID("C001")` | `consensus_id("C001")` | (运行确定) |
| `("treats","DRUG1","DISEASE1")` | `RelationID("treats","DRUG1","DISEASE1")` | `relation_id("treats","DRUG1","DISEASE1")` | (运行确定) |

> 具体 UUID 值需在集成环境中运行一次后固化到测试断言中。

---

## 7. 参考实现

| 语言 | 文件路径 | 关键类型 |
|------|----------|----------|
| Go | `KnowGraphGo/adapter/clinical/id_factory.go` | `ClinicalIDFactory` |
| Python | `AI-Kill-Cancer/src/backend/clinical_graph/id_factory.py` | `ClinicalGraphIDFactory` |

---

## 8. 变更历史

| 日期 | 变更 | 作者 |
|------|------|------|
| 2025-07-01 | 初始版本 | AKC-03 |
