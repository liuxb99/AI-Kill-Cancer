# PTC MVP Data Pipeline

## Goal

先把甲狀腺乳突癌資料鏈路完整跑通，不在第一輪追求全欄位、全資料源或完整臨床知識庫。

最小可驗收鏈路：

```text
TCGA-THCA public data
        ↓
PTC Importer
        ↓
PostgreSQL canonical tables
        ↓
Clinical Graph Outbox
        ↓
KnowGraphGo PTC Adapter
        ↓
GraphDelta apply
        ↓
Path Query
        ↓
Replay count unchanged
```

PostgreSQL 是唯一 Source of Truth；KnowGraphGo 是可重建的查詢投影。

---

## First Slice Scope

第一輪只處理：

```text
1 個資料源：TCGA-THCA / GDC public data
1 個癌種：Papillary Thyroid Carcinoma
3 類資料：Case、Variant、Outcome
1 條圖譜鏈：Case → Variant → Gene → PTC
```

暫不處理：

```text
原始 FASTQ / BAM
受控存取資料
完整 RNA-seq pipeline
西藥全庫
科學中藥全庫
完整交互作用
臨床推薦引擎修改
```

---

## Minimal PostgreSQL Model

### PTCResearchCase

```text
id
case_id
source_dataset
source_project
sex
age_range
pathologic_stage
t_status
n_status
m_status
vital_status
days_to_last_follow_up
days_to_death
created_at
updated_at
```

### PTCVariant

```text
id
variant_id
case_id
gene
chromosome
position
reference
alternate
variant_type
classification
source_record_id
created_at
```

### PTCOutcome

```text
id
outcome_id
case_id
outcome_type
outcome_value
observed_at
source_record_id
created_at
```

### ImportBatch

```text
id
batch_id
source_dataset
source_version
started_at
completed_at
status
record_count
error_count
checksum
```

---

## Import Flow

新增：

```text
src/backend/importers/ptc_tcga/
```

至少包含：

```text
downloader.py
parser.py
normalizer.py
service.py
schemas.py
```

流程：

```text
下載 GDC 公開 clinical + mutation 資料
        ↓
保存 raw manifest 與 checksum
        ↓
解析成 canonical records
        ↓
同一 Transaction 寫入 Case / Variant / Outcome
        ↓
同一 Transaction 寫入 Outbox events
        ↓
commit
```

失敗時整批 rollback，或依 batch chunk 原子提交；不得出現資料已寫入但 Outbox 不存在。

---

## Canonical Events

### ptc_case.created

```json
{
  "event_type": "ptc_case.created",
  "aggregate_type": "ptc_research_case",
  "aggregate_id": "TCGA-CASE-ID",
  "schema_version": "1.0",
  "payload": {
    "case_id": "TCGA-CASE-ID",
    "disease": "papillary_thyroid_carcinoma",
    "stage": "stage_i",
    "sex": "female",
    "source_dataset": "TCGA-THCA"
  }
}
```

### ptc_variant.observed

```json
{
  "event_type": "ptc_variant.observed",
  "aggregate_type": "ptc_variant",
  "aggregate_id": "TCGA-CASE-ID:BRAF:V600E",
  "schema_version": "1.0",
  "payload": {
    "case_id": "TCGA-CASE-ID",
    "gene": "BRAF",
    "variant": "V600E",
    "classification": "somatic",
    "source_dataset": "TCGA-THCA"
  }
}
```

### ptc_outcome.recorded

```json
{
  "event_type": "ptc_outcome.recorded",
  "aggregate_type": "ptc_outcome",
  "aggregate_id": "TCGA-CASE-ID:FOLLOWUP",
  "schema_version": "1.0",
  "payload": {
    "case_id": "TCGA-CASE-ID",
    "outcome_type": "follow_up",
    "outcome_value": "alive",
    "source_dataset": "TCGA-THCA"
  }
}
```

所有事件必須包含：

```text
event_id
event_type
aggregate_type
aggregate_id
schema_version
occurred_at
source_system
source_dataset
source_record_id
correlation_id
```

---

## KnowGraphGo Projection

新增獨立 Adapter：

```text
adapter/ptc/
```

### Entities

```text
PTCResearchCase
PapillaryThyroidCarcinoma
Variant
Gene
ClinicalOutcome
```

### Relations

```text
PTCResearchCase ─HAS_DISEASE→ PapillaryThyroidCarcinoma
PTCResearchCase ─HAS_VARIANT→ Variant
Variant ─AFFECTS_GENE→ Gene
PTCResearchCase ─HAS_OUTCOME→ ClinicalOutcome
```

每個 Entity 與 Relation 必須保留：

```text
event_id
event_type
source_system
source_dataset
source_record_id
occurred_at
correlation_id
```

### Deterministic IDs

```text
ptc:case:{source_dataset}:{case_id}
ptc:variant:{source_dataset}:{case_id}:{gene}:{variant}
ptc:gene:{hgnc_symbol}
ptc:outcome:{source_dataset}:{case_id}:{outcome_type}
```

使用 UUIDv5，重複匯入不得增加節點或關係數量。

---

## End-to-End Acceptance Test

建立：

```text
scripts/ptc_cross_repo_e2e.py
```

測試固定使用小型 fixture：

```text
3 個病例
5 個變異
3 個 Gene
3 個 Outcome
```

必須驗證：

```text
1. 匯入資料到 PostgreSQL
2. Outbox events 建立成功
3. KnowGraphGo CLI apply 成功
4. Path Query 成功
5. Replay 同一批 events
6. Entity count 不增加
7. Relation count 不增加
8. Properties 可更新
```

必要 Path：

```text
Case → Disease
Case → Variant → Gene
Case → Outcome
```

---

## First Delivery

第一個交付只需要：

```text
Migration
4 個 canonical models
Importer
Outbox events
KnowGraphGo PTC adapter
Deterministic IDs
Cross-repository E2E
PostgreSQL CI
```

完成這條鏈後，再依序增加：

```text
Drug
Treatment
Clinical Trial
Publication Evidence
Scientific Chinese Medicine
Drug-Herb Interaction
```

不得在第一批同時展開所有資料源與所有實體。

---

## Acceptance Gate

只有全部通過才算鏈路完成：

```text
TCGA fixture import：PASS
PostgreSQL persistence：PASS
Outbox atomicity：PASS
KnowGraphGo apply：PASS
Path query：PASS
Idempotent replay：PASS
Restart recovery：PASS
PostgreSQL CI：PASS
```

第一輪目標不是醫療推薦，而是建立一條可重建、可追溯、可持續擴充的 PTC 資料投影鏈路。
