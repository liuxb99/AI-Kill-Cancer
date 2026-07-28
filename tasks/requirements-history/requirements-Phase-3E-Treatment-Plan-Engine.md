# Phase 3E：Treatment Plan Engine V1

Repository：

```
https://github.com/liuxb99/AI-Kill-Cancer
```

Branch：

```
master
```

Base Commit：

```
a366b2936893729f3b9aa43ad38c532b3bd2a410
```

Knowledge Graph Repository：

```
https://github.com/liuxb99/KnowGraphGo
```

Pinned KnowGraphGo Commit：

```
950dd86926891789380381cb28f233ee007fe7b4
```

目前已驗收：

```
Phase 3A：Drug Recommendation Engine
Phase 3B：Clinical Decision Engine
Phase 3C：Tumor Board Consensus Engine
Phase 3D：Clinical Knowledge Graph Adapter
```

本輪開始：

```
Phase 3E
Treatment Plan Engine V1
```

---

# 一、任務定位

建立完整主鏈：

```
Patient
↓
Drug Recommendation
↓
Clinical Decision
↓
Tumor Board Consensus
↓
Treatment Plan
```

Treatment Plan 必須將已核准的臨床決策與 Tumor Board Consensus 轉換為：

```
可執行的治療階段
治療項目
時間安排
監測要求
停藥／暫停條件
替代方案
追蹤要求
```

本輪不是 Medication Order System。

本輪不得建立：

```
真實處方
醫囑簽章
藥物發放
保險申報
醫療設備控制
自動給藥
```

Treatment Plan 只能是：

```
Clinical Planning / Decision Support
```

不得宣稱取代醫師判斷。

---

# 二、資料權責

必須遵守：

```
Postgres
= 唯一 Source of Truth

KnowGraphGo
= Explain
= Evidence Path
= Digital Thread Projection
= 可重建查詢層
```

不得：

```
從 Knowledge Graph 直接修改 Treatment Plan
把 KnowGraphGo 當正式 Plan Storage
依賴 Graph 才能完成 Plan Transaction
```

Graph 同步失敗不得導致正式 Treatment Plan 資料遺失。

---

# 三、本輪禁止事項

不得開始：

```
Medication Order
Prescription
Dose Administration
Billing
Insurance
Patient Portal
Phase 3F
Phase 4
```

不得重寫：

```
Recommendation Engine
Clinical Decision Engine
Tumor Board Engine
Knowledge Graph Adapter
Migration 017～022
```

不得大規模修改：

```
AGENTS.md
既有 API Contract
既有 Auth 架構
既有 Transaction Pattern
```

採：

```
Minimal Integration
Repository Pattern
Service Transaction Boundary
Versioned Plan
Complete Audit Trail
```

---

# 四、執行流程

嚴格依照 `AGENTS.md`：

```
Step 0A
↓
Step 0B
↓
Scene Identification
↓
Planner
↓
Workflow Update
↓
Batch Execution
↓
Step 4b Regression Check
↓
Reviewer
↓
Summary
↓
Git Commit
↓
Git Push
```

不要中途回報。

全部完成、測試、CI、Reviewer、Push 後一次回報。

---

# 五、開始前必讀

完整閱讀：

```
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

src/backend/clinical/recommendation_engine.py
src/backend/clinical/clinical_decision_engine.py
src/backend/clinical/tumor_board_engine.py

src/backend/clinical_graph/
src/backend/services/clinical_graph_event_service.py

src/frontend/src/pages/RecommendationPage.tsx
src/frontend/src/pages/ClinicalDecisionPage.tsx
src/frontend/src/pages/TumorBoardConsensusPage.tsx
src/frontend/src/pages/ClinicalGraphPage.tsx

migrations/versions/017*
migrations/versions/018*
migrations/versions/019*
migrations/versions/020*
migrations/versions/021*
migrations/versions/022*

.github/workflows/ci.yml
```

確認並沿用：

```
Model Pattern
Repository Pattern
Service Pattern
Transaction Boundary
API Error Format
Auth／Role Pattern
Audit Pattern
Outbox Pattern
Frontend Route Pattern
Postgres CI Pattern
```

不得另建第二套架構。

---

# 六、Treatment Plan 輸入

建立 Treatment Plan 時至少需要：

```
patient_id
recommendation_id
clinical_decision_id
consensus_id
plan_intent
treatment_goals
clinical_context
```

必須驗證：

```
Recommendation.patient_id
==
ClinicalDecision.patient_id
==
Consensus.patient_id
==
Request.patient_id
```

並驗證：

```
ClinicalDecision.recommendation_id
==
Request.recommendation_id
```

以及：

```
Consensus.clinical_decision_id
==
Request.clinical_decision_id
```

任一不一致：

```
422
```

不得執行 Engine。

不得寫入部分資料。

---

# 七、Plan 狀態

至少支援：

```
draft
proposed
under_review
approved
active
paused
completed
cancelled
superseded
```

不得只用：

```
active / inactive
```

狀態轉換必須集中管理。

建立：

```
TreatmentPlanStateMachine
```

至少規則：

```
draft → proposed
proposed → under_review
under_review → approved
approved → active
active → paused
paused → active
active → completed
任意非 completed → cancelled
approved／active → superseded
```

非法狀態轉換：

```
409
```

不得直接任意修改狀態字串。

---

# 八、Plan Versioning

Treatment Plan 必須版本化。

至少保存：

```
plan_id
version
previous_plan_id
supersedes_plan_id
is_current
revision_reason
```

修改已 approved／active 的 Plan 時：

```
不得原地覆蓋
```

必須：

```
建立新 Version
舊 Plan 標記 superseded
保留完整歷史
```

至少可回答：

```
誰修改？
何時修改？
修改原因？
上一版本是什麼？
哪些項目改變？
```

---

# 九、Treatment Plan Model

新增正式 Model：

```
TreatmentPlanModel
```

至少欄位：

```
id
plan_id
version
patient_id
recommendation_id
clinical_decision_id
consensus_id

plan_status
plan_intent
treatment_goals
summary
clinical_rationale

start_date
target_end_date
review_date

previous_plan_id
supersedes_plan_id
is_current
revision_reason

created_by
approved_by
approved_at
activated_at
paused_at
completed_at
cancelled_at

created_at
updated_at
```

---

# 十、Treatment Phase Model

新增：

```
TreatmentPhaseModel
```

至少：

```
id
phase_id
plan_id
phase_order
phase_type
name
description
planned_start
planned_end
duration_days
status
entry_criteria
exit_criteria
created_at
updated_at
```

Phase Type 至少：

```
preparation
induction
primary_treatment
consolidation
maintenance
monitoring
follow_up
supportive_care
```

---

# 十一、Treatment Item Model

新增：

```
TreatmentItemModel
```

至少：

```
id
item_id
plan_id
phase_id
item_order
item_type
name
description
drug_id
procedure_code
frequency
duration
route
planned_dose_text
priority
status
rationale
source_recommendation
created_at
updated_at
```

注意：

```
planned_dose_text
```

只能是治療規劃文字，不得成為可直接執行的電子處方。

Item Type 至少：

```
medication
procedure
radiation
surgery
laboratory
imaging
monitoring
supportive_care
consultation
education
```

---

# 十二、Monitoring Model

新增：

```
TreatmentMonitoringModel
```

至少：

```
id
monitoring_id
plan_id
phase_id
item_id

monitoring_type
name
schedule
target_range
warning_threshold
critical_threshold
action_if_abnormal

baseline_required
repeat_interval
responsible_specialty

created_at
updated_at
```

至少支援：

```
laboratory
imaging
symptom
toxicity
response
vital_sign
medication_safety
```

---

# 十三、Stop／Pause Criteria

新增：

```
TreatmentSafetyRuleModel
```

至少：

```
id
rule_id
plan_id
phase_id
item_id

rule_type
condition
severity
recommended_action
requires_review
source
created_at
```

Rule Type：

```
pause
stop
dose_review
urgent_review
switch_alternative
additional_test
```

不得由系統自動執行停藥。

只能輸出：

```
Clinical Review Required
```

---

# 十四、Alternative Plan

Treatment Plan 必須可保存：

```
alternative_options
```

至少包括：

```
alternative_id
name
reason
trigger_condition
source_recommendation_id
priority
```

當：

```
contraindication
treatment failure
toxicity
patient preference
resource limitation
```

發生時，可提供替代方案供醫師審查。

不得自動切換 Treatment。

---

# 十五、Engine

建立：

```
TreatmentPlanEngine
```

輸入：

```
Patient Context
Recommendation
Clinical Decision
Tumor Board Consensus
Evidence Summary
Contraindications
Monitoring Requirements
```

輸出：

```
Plan Summary
Treatment Phases
Treatment Items
Monitoring Items
Safety Rules
Alternatives
Review Schedule
Trace
```

Engine 不得：

```
直接操作 Database
直接 commit
直接呼叫 API
```

Engine 必須為可重現的 pure/domain logic。

---

# 十六、Rule Set

建立：

```
TreatmentPlanRuleSet
```

集中管理：

```
Plan generation thresholds
Required monitoring
Phase sequencing
Review intervals
Safety escalation
Alternative selection
```

不得把規則散落在大量 `if/elif`。

可使用：

```
Registry
Rule Object
Configuration
Enum
```

---

# 十七、Calculation Trace

至少記錄：

```
0 load_context
1 validate_links
2 extract_consensus
3 identify_treatment_goals
4 build_phases
5 build_treatment_items
6 build_monitoring
7 build_safety_rules
8 build_alternatives
9 finalize_plan
10 prepare_persistence
```

每個 Step 至少：

```
step_order
step_type
input_summary
output_summary
rule_ids
evidence_ids
created_at
```

必須可追溯：

```
哪一項 Recommendation
哪一項 Clinical Decision
哪一項 Consensus
哪些 Evidence
哪些 Contraindication
產生哪個 Treatment Item
```

---

# 十八、Migration 023

新增：

```
Migration 023
```

建立至少：

```
domain_treatment_plans
domain_treatment_phases
domain_treatment_items
domain_treatment_monitoring
domain_treatment_safety_rules
domain_treatment_plan_traces
```

不得修改：

```
017～022
```

要求：

```
Foreign Keys
Indexes
Unique Constraints
Version Constraints
Cascade
Upgrade
Empty Downgrade
Re-upgrade
```

若已有 Treatment Plan 正式資料：

```
downgrade 必須阻擋
不得刪除正式資料
```

空資料時：

```
允許 downgrade
```

---

# 十九、Repository

新增：

```
TreatmentPlanRepository
TreatmentPhaseRepository
TreatmentItemRepository
TreatmentMonitoringRepository
TreatmentSafetyRuleRepository
TreatmentPlanTraceRepository
```

至少提供：

## Plan

```
create
get_by_id
get_by_plan_id
get_current_by_patient_id
list_by_patient_id
list_versions
count_by_patient_id
mark_superseded
```

## Phase／Item／Monitoring／Safety／Trace

```
create
create_many
list_by_plan_id
delete_by_plan_id（僅限未提交交易中的 rollback helper）
```

Repository 規則：

```
不得 commit
不得 rollback
不得吞 Exception
```

---

# 二十、Service

建立：

```
TreatmentPlanService
```

職責：

```
驗證上游鏈路
建立 Clinical Context
呼叫 Engine
建立 Plan
建立 Phases
建立 Items
建立 Monitoring
建立 Safety Rules
建立 Trace
建立 Graph Outbox Event
同一 Transaction commit
```

正式交易：

```
Treatment Plan Data
+
Treatment Plan Outbox
```

必須同 Transaction。

任一 Persistence 失敗：

```
全部 rollback
```

Graph Projection 後續失敗：

```
不得 rollback Treatment Plan
由 Outbox 重試
```

---

# 二十一、Graph Event

新增事件：

```
treatment_plan.created
treatment_plan.updated
treatment_plan.approved
treatment_plan.activated
treatment_plan.paused
treatment_plan.completed
treatment_plan.superseded
```

Payload 至少：

```
plan_id
version
patient_id
recommendation_id
clinical_decision_id
consensus_id
status
goals
phases
items
monitoring
safety_rules
alternatives
```

不得包含：

```
密碼
Token
完整自由文字病歷
未授權敏感附件
```

---

# 二十二、KnowGraphGo 投影

在既有 Clinical Adapter 中加入：

```
TreatmentPlan Entity
TreatmentPhase Entity
TreatmentItem Entity
Monitoring Entity
SafetyRule Entity
```

Relation 至少：

```
TreatmentPlan ─FOR_PATIENT→ Patient
TreatmentPlan ─BASED_ON→ TumorBoardConsensus
TreatmentPlan ─DERIVED_FROM→ ClinicalDecision
TreatmentPlan ─HAS_PHASE→ TreatmentPhase
TreatmentPhase ─HAS_ITEM→ TreatmentItem
TreatmentItem ─SUPPORTED_BY→ Evidence
TreatmentItem ─USES_DRUG→ Drug
TreatmentPlan ─HAS_MONITORING→ Monitoring
TreatmentPlan ─HAS_SAFETY_RULE→ SafetyRule
TreatmentPlan ─SUPERSEDES→ TreatmentPlan
```

必須維持：

```
Deterministic ID
Idempotent Replay
Relation Provenance
Stub Preservation
Canonical Schema
```

不得破壞 Phase 3D 已驗收功能。

---

# 二十三、API

新增：

```
POST /api/v1/treatment-plans
GET /api/v1/treatment-plans/{plan_id}
GET /api/v1/treatment-plans?patient_id=&skip=&limit=
GET /api/v1/treatment-plans/{plan_id}/versions
GET /api/v1/treatment-plans/{plan_id}/trace
```

狀態操作：

```
POST /api/v1/treatment-plans/{plan_id}/submit
POST /api/v1/treatment-plans/{plan_id}/approve
POST /api/v1/treatment-plans/{plan_id}/activate
POST /api/v1/treatment-plans/{plan_id}/pause
POST /api/v1/treatment-plans/{plan_id}/complete
POST /api/v1/treatment-plans/{plan_id}/cancel
POST /api/v1/treatment-plans/{plan_id}/revise
```

不得使用通用：

```
PATCH status=<任意字串>
```

所有狀態操作必須經 State Machine。

---

# 二十四、權限

至少：

```
Viewer：
只讀

Researcher：
可建立 draft／proposed

Clinician：
可建立、提交、修改 draft

Tumor Board Member：
可 review

Approver／Admin：
可 approve

Clinician／Approver：
可 activate／pause／complete
```

必須沿用既有 Role／Permission。

不得建立硬編碼單一 Token。

---

# 二十五、Frontend

新增：

```
TreatmentPlanListPage
TreatmentPlanCreatePage
TreatmentPlanDetailPage
TreatmentPlanRevisionPage
```

路由：

```
/treatment-plans
/treatment-plans/new
/treatment-plans/:id
/treatment-plans/:id/revise
```

從：

```
TumorBoardConsensusPage
```

加入：

```
Create Treatment Plan
```

建立流程：

```
Consensus
↓
POST Treatment Plan
↓
取得 plan_id
↓
navigate("/treatment-plans/{plan_id}")
```

Detail 至少顯示：

```
Status
Version
Goals
Summary
Phases
Items
Monitoring
Safety Rules
Alternatives
Review Date
Trace
Knowledge Graph Link
```

不得使用：

```
sample
fake plan
hardcoded production response
```

---

# 二十六、HTML Report

在既有報告加入：

```
Treatment Plan Section
```

至少：

```
Plan Status
Version
Treatment Goals
Treatment Phases
Treatment Items
Monitoring Schedule
Safety Rules
Alternatives
Review Date
Approval Information
```

不得重寫整個 Report Generator。

---

# 二十七、測試要求

## Engine Tests

至少：

```
valid plan generation
phase ordering
monitoring generation
safety rule generation
alternative generation
missing consensus
contraindication handling
empty evidence
deterministic output
```

## State Machine Tests

全部合法與非法轉換。

## Model Tests

```
relations
versioning
unique constraints
cascade
JSON round-trip
```

## Repository Tests

```
create
get
list
pagination
versions
current plan
mark superseded
```

## Service Tests

```
success
patient mismatch
recommendation mismatch
decision mismatch
consensus mismatch
created_by
transaction rollback
phase failure
item failure
trace failure
outbox failure
revision
approval
```

## API Tests

```
POST
GET
List
Versions
Trace
Submit
Approve
Activate
Pause
Complete
Cancel
Revise
401
403
404
409
422
500 generic
```

## Restart Recovery

```
App 1 建立 Plan
Shutdown
App 2 GET Plan／Phases／Items／Trace
```

## Digital Thread

必須可還原：

```
Patient
→ Recommendation
→ Clinical Decision
→ Consensus
→ Treatment Plan
→ Phase
→ Item
```

## Graph Integration

真正：

```
Treatment Plan Outbox
→ KnowGraphGo CLI apply
→ SQLite Graph
→ Query Treatment Plan Path
→ Replay Count 不增加
```

## Frontend

```
routes
create
detail
state actions
revision
empty state
error state
permissions
```

---

# 二十八、Postgres CI

必須真正執行：

```
Migration 023 upgrade
Treatment Plan transaction tests
Restart recovery
Versioning tests
State transition tests
Outbox transaction
Graph projection E2E
Empty downgrade
Re-upgrade
```

不得：

```
continue-on-error
skip
xfail
SQLite 冒充 Postgres
```

---

# 二十九、CI Cleanup

本輪可順手刪除 Phase 3D 中已被正式 CI-01～CI-05 取代的重複舊步驟，但必須是最小清理。

只允許移除：

```
重複 checkout KnowGraphGo
舊的 Python-only parity block
go run -exec '' || true
已被正式 E2E 取代的重複測試
```

不得修改現有正式 Gate 標準。

---

# 三十、Reviewer Gate

Reviewer 必須確認：

```
[ ] 上游四個 ID 關聯一致
[ ] Plan versioning 正確
[ ] Approved Plan 不原地覆蓋
[ ] State Machine 阻止非法轉換
[ ] Plan／Phases／Items／Monitoring／Safety 同 Transaction
[ ] Outbox 同 Transaction
[ ] Restart 後完整讀回
[ ] Graph Digital Thread 完整
[ ] Idempotent Graph Replay
[ ] Auth／Role 正確
[ ] Postgres CI 全綠
```

任一：

```
FAIL
PARTIAL
未驗證
```

則：

```
Reviewer 最高 89
Accepted = NO
Ready for Next Phase = NO
```

Reviewer 必須：

```
>=95
```

---

# 三十一、Git Commit

主要 Commit：

```
feat(phase3e): add treatment plan engine
```

KnowGraphGo 若有修改：

```
feat(clinical): add treatment plan graph projection
```

先推 KnowGraphGo，取得 SHA。

AI-Kill-Cancer CI pin 該 SHA。

允許追加聚焦修復 Commit。

禁止：

```
force push
rebase
修改舊 Migration
開始下一階段
```

---

# 三十二、完成後只回報

```
AI-Kill-Cancer Commit SHA
KnowGraphGo Commit SHA

Migration 023
New Tables
New Models
New Repositories
TreatmentPlanEngine
TreatmentPlanRuleSet
TreatmentPlanStateMachine

Plan Versioning
Revision Flow
Approval Flow
Activation Flow
Pause Flow
Completion Flow

POST API
GET API
List API
Versions API
Trace API
State APIs

Frontend Routes
Create Flow
Detail Page
Revision Page
Report Section

Patient Validation
Recommendation Validation
Decision Validation
Consensus Validation
created_by Audit
approved_by Audit

Plan Persistence
Phase Persistence
Item Persistence
Monitoring Persistence
Safety Rule Persistence
Trace Persistence
Outbox Persistence
Transaction Rollback
Restart Recovery

Treatment Plan Graph Projection
Digital Thread Path
Idempotent Replay
Relation Provenance
Stub Preservation

Backend Tests
Frontend Tests
Postgres Tests
Graph E2E Tests

AI-Kill-Cancer CI Run ID
KnowGraphGo CI Run ID
CI Conclusions

Failed Required Steps
Skipped Required Steps
Git Status
Push Results
Reviewer Score
```

最後：

```
Phase 3E Treatment Plan Engine：
PASS / PARTIAL / FAIL

Accepted：
YES / NO

Ready for ChatGPT GitHub Review：
YES / NO

Ready for Next Phase：
YES / NO
```

只有：

```
Versioning：PASS
State Machine：PASS
Transaction：PASS
Restart：PASS
Graph Digital Thread：PASS
Postgres CI：PASS
Reviewer >=95
```

才允許：

```
Accepted：YES
Ready for Next Phase：YES
```

推送後停止。

不得自行開始 Medication Order 或下一階段。
