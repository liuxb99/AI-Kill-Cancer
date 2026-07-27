# AI-Kill-Cancer — Phase 3C：Tumor Board Consensus Engine

Repository：

```text
https://github.com/liuxb99/AI-Kill-Cancer
```

Branch：

```text
master
```

Base Commit：

```text
5b2c658
```

已正式驗收：

```text
Phase 3A：Accepted
Phase 3B：Accepted
```

本輪開始：

```text
Phase 3C
Tumor Board Consensus Engine
```

---

# 一、任務定位

本輪建立：

```text
Clinical Decision
↓
Multi-specialty Opinions
↓
Consensus Calculation
↓
Tumor Board Consensus
```

本輪是一個完整、可獨立驗收的模組。

不得同時開始：

```text
Treatment Plan
Medication Order
Guideline Execution
Follow-up Plan
Phase 3D
Phase 4
```

不得重寫已驗收的：

```text
Drug Recommendation Engine
Clinical Decision Engine
Recommendation Persistence
Clinical Decision Persistence
既有 Trace 架構
```

採用：

```text
Minimal Integration
Repository Pattern
Service Transaction Boundary
Postgres Source of Truth
Complete Digital Thread
```

---

# 二、執行流程

嚴格依照 `AGENTS.md`：

```text
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

全部完成後一次回報。

---

# 三、開始前必讀

完整閱讀：

```text
AGENTS.md
tasks/requirements.md

src/backend/domain/recommendation.py
src/backend/domain/clinical_decision.py

src/backend/repositories/recommendation_repo.py
src/backend/repositories/clinical_decision_repo.py

src/backend/services/recommendation_service.py
src/backend/services/clinical_decision_service.py

src/backend/clinical/recommendation_engine.py
src/backend/clinical/clinical_decision_engine.py

src/backend/api/v1/recommendation.py
src/backend/api/v1/clinical_decision.py

src/frontend/src/pages/RecommendationPage.tsx
src/frontend/src/pages/ClinicalDecisionListPage.tsx
src/frontend/src/pages/ClinicalDecisionPage.tsx
src/frontend/src/App.tsx

migrations/versions/017*
migrations/versions/018*
migrations/versions/019*

tests/test_recommendation*
tests/test_clinical_decision*
tests/test_api_clinical_decision.py
tests/test_migration.py
```

先確認專案現有：

```text
Model Pattern
Repository Pattern
Service Pattern
Transaction Boundary
API Error Schema
Authentication Pattern
Audit Trail Pattern
Migration Pattern
Frontend Route Pattern
Postgres CI Pattern
```

不得自行建立第二套架構。

---

# 四、核心目標

建立：

```text
Tumor Board Consensus Engine
```

輸入至少包含：

```text
patient_id
recommendation_id
clinical_decision_id
specialist_opinions
meeting_context
```

輸出至少包含：

```text
consensus_id
consensus_status
consensus_score
final_recommendation
supporting_rationale
dissenting_opinions
unresolved_questions
required_follow_up
participating_specialties
created_by
created_at
trace_id
```

---

# 五、專科意見模型

每一筆 Specialist Opinion 至少包含：

```text
specialty
participant_id
position
confidence
rationale
supporting_evidence
contraindications
preferred_option
alternative_option
requires_more_information
```

建議 specialty 支援：

```text
medical_oncology
surgical_oncology
radiation_oncology
pathology
radiology
genomics
pharmacy
nursing
palliative_care
```

不得把 Specialty 寫死在大量 `if/elif` 中。

應使用：

```text
Enum
Registry
Rule Configuration
```

---

# 六、Consensus 狀態

至少支援：

```text
unanimous
strong_consensus
majority_consensus
split_decision
insufficient_information
deferred
```

不得只用：

```text
PASS / FAIL
```

Consensus 必須根據：

```text
有效意見數
支持比例
反對比例
專科權重
信心值
Contraindication
Evidence Strength
```

計算。

---

# 七、Consensus 計算規則

建立正式、可測試的計算模型。

建議：

```text
Opinion Weight
=
Specialty Weight
×
Confidence Weight
×
Evidence Weight
```

至少產生：

```text
support_score
oppose_score
abstain_score
consensus_ratio
confidence_score
```

Consensus 狀態可參考：

```text
100% 支持
→ unanimous

>= 80% 加權支持
→ strong_consensus

>= 60% 加權支持
→ majority_consensus

支持與反對接近
→ split_decision

有效資料不足
→ insufficient_information

需要補資料或重新討論
→ deferred
```

實際 Threshold 必須集中放在：

```text
ConsensusRuleSet
```

不得散落在 Engine 中。

---

# 八、P0 資料一致性

建立 Consensus 前必須驗證：

```text
Recommendation.patient_id
==
ClinicalDecision.patient_id
==
Request.patient_id
```

還必須驗證：

```text
ClinicalDecision.recommendation_id
==
Request.recommendation_id
```

任一不一致：

```text
422
```

不得執行 Engine。

不得建立：

```text
Consensus
Consensus Trace
Opinion Records
```

資料庫不得殘留部分資料。

---

# 九、Audit Trail

authenticated user 必須一路寫入：

```text
API
↓
Service
↓
TumorBoardConsensusModel.created_by
```

每一筆 Specialist Opinion 若有 participant_id，也必須保存。

不得全部寫：

```text
NULL
```

必須可回答：

```text
誰建立 Tumor Board Consensus？
哪些專科參與？
誰提出哪一個意見？
何時建立？
```

---

# 十、Database Models

新增正式 Model。

建議至少包括：

## TumorBoardConsensusModel

```text
id
consensus_id
patient_id
recommendation_id
clinical_decision_id
consensus_status
consensus_score
final_recommendation
supporting_rationale
dissenting_opinions
unresolved_questions
required_follow_up
participating_specialties
created_by
created_at
updated_at
```

## TumorBoardOpinionModel

```text
id
consensus_id / consensus_uuid
specialty
participant_id
position
confidence
rationale
supporting_evidence
contraindications
preferred_option
alternative_option
requires_more_information
created_at
```

## TumorBoardConsensusTraceModel

```text
id
trace_id
consensus_id
step_order
step_type
input_summary
output_summary
created_at
```

關聯至少應為：

```text
Patient
↓
Recommendation
↓
Clinical Decision
↓
Tumor Board Consensus
↓
Specialist Opinions
↓
Consensus Trace
```

---

# 十一、Migration 020

新增：

```text
Migration 020
```

不得修改：

```text
017
018
019
```

Migration 必須建立：

```text
domain_tumor_board_consensus
domain_tumor_board_opinions
domain_tumor_board_consensus_traces
```

要求：

```text
Foreign Keys 正確
Indexes 正確
Unique Constraints 正確
Cascade 行為正確
upgrade 正確
downgrade 正確
re-upgrade 正確
```

若 Trace 使用同一 `trace_id` 多 Step，必須一開始就使用：

```text
UNIQUE(trace_id, step_order)
```

不得再次犯 Phase 3B 的單欄唯一錯誤。

---

# 十二、Repository

新增：

```text
TumorBoardConsensusRepository
TumorBoardOpinionRepository
TumorBoardConsensusTraceRepository
```

至少提供：

## Consensus Repository

```text
create
get_by_id
get_by_uuid
list_by_patient_id
list_by_clinical_decision_id
count_by_patient_id
```

## Opinion Repository

```text
create
create_many
list_by_consensus_id
```

## Trace Repository

```text
create
create_many
get_by_consensus_id
get_by_trace_id
```

規則：

```text
Repository 不得 commit
Repository 不得 rollback
Repository 不得吞 Exception
```

Transaction 由 Service 管理。

---

# 十三、Service

建立：

```text
TumorBoardConsensusService
```

職責：

```text
驗證 Patient / Recommendation / Clinical Decision 關聯
整理 Specialist Opinions
執行 Consensus Engine
建立 Consensus Model
建立 Opinion Models
建立 Trace Models
同一 Transaction 寫入
Commit
回傳 DTO
```

失敗時：

```text
rollback
raise
API generic error
Database 無部分資料
```

不得：

```text
Persistence failure 仍回傳成功
```

---

# 十四、Consensus Trace

至少記錄以下 Step：

```text
0 load_context
1 validate_links
2 normalize_opinions
3 calculate_weights
4 calculate_consensus
5 resolve_dissent
6 finalize_consensus
7 prepare_persistence
```

每個 Step 必須有：

```text
step_order
step_type
input_summary
output_summary
```

至少可追溯：

```text
每一個 Specialty Opinion
每一個 Weight
Support / Oppose Score
Consensus Ratio
Dissent
Final Decision
```

不得只存一個總結果 JSON。

---

# 十五、API

新增：

```text
POST /api/v1/tumor-board-consensus
GET /api/v1/tumor-board-consensus/{consensus_id}
GET /api/v1/tumor-board-consensus?patient_id=&skip=&limit=
```

可視需要增加：

```text
GET /api/v1/tumor-board-consensus/{consensus_id}/opinions
GET /api/v1/tumor-board-consensus/{consensus_id}/trace
```

但不得擴大到 Phase 3D。

分頁限制：

```text
skip >= 0
1 <= limit <= 100
```

錯誤處理：

```text
404：不存在
422：資料關聯錯誤或輸入錯誤
500：固定 generic message
```

不得將以下內容回傳 Client：

```text
Exception
SQL
Stack Trace
Internal Path
Database URL
```

---

# 十六、Frontend

新增：

```text
TumorBoardConsensusListPage
TumorBoardConsensusPage
```

正式接入：

```text
App.tsx
Router
Navigation
```

路由建議：

```text
/tumor-board
/tumor-board/:id
```

列表頁至少支援：

```text
輸入 patient_id
查詢 Consensus
顯示 status
顯示 score
顯示 specialties
顯示 created_at
進入 Detail
```

Detail Page 至少顯示：

```text
Consensus Status
Consensus Score
Final Recommendation
Supporting Rationale
Dissenting Opinions
Unresolved Questions
Required Follow-up
Specialist Opinions
Trace Summary
```

不得使用：

```text
sample
fake id
hardcoded data
mock production response
```

---

# 十七、建立入口

必須建立一個真實建立 Consensus 的流程。

可以放在：

```text
ClinicalDecisionPage
```

新增：

```text
建立 Tumor Board Consensus
```

流程：

```text
Clinical Decision
↓
填入 Specialist Opinions
↓
POST Consensus
↓
取得 consensus_id
↓
navigate("/tumor-board/{consensus_id}")
```

不得只有 GET Detail Page，卻沒有任何正式建立入口。

---

# 十八、HTML Report

在既有報告中新增：

```text
Tumor Board Consensus Section
```

至少包含：

```text
Consensus Status
Consensus Score
Participating Specialties
Final Recommendation
Supporting Rationale
Dissenting Opinions
Unresolved Questions
Required Follow-up
```

不得重寫整個 Report Generator。

---

# 十九、測試要求

## Engine Tests

至少驗證：

```text
unanimous
strong_consensus
majority_consensus
split_decision
insufficient_information
deferred
specialty weighting
confidence weighting
contraindication impact
dissent extraction
```

## Model Tests

```text
Model creation
Relations
Cascade
JSON round-trip
Unique constraints
```

## Repository Tests

```text
create
get
list
count
create_many
pagination
not found
```

## Service Tests

```text
successful consensus
patient mismatch
recommendation mismatch
clinical decision mismatch
created_by persistence
transaction rollback
opinion persistence failure
trace persistence failure
commit failure
```

## API Tests

```text
POST success
GET success
List empty
List one
Pagination
401
404
422
500 generic
```

## Digital Thread Test

必須驗證：

```text
Patient
↓
Recommendation
↓
Clinical Decision
↓
Tumor Board Consensus
↓
Opinions
↓
Trace
```

全部可從 Database 還原。

## Restart Recovery Test

```text
App 1
POST Consensus
GET Consensus
Shutdown
App 2
GET Consensus
Opinions
Trace
```

## Frontend Tests

```text
List route
Detail route
Navigation
Create form
POST API
Redirect
Empty state
Error state
```

## Migration Tests

```text
019 → 020 upgrade
020 → 019 downgrade
019 → 020 re-upgrade
FK
Index
Unique
Multiple Trace Steps
```

---

# 二十、真實 Postgres Gate

Phase 3C 的 Migration、Transaction、Digital Thread 與 Restart Recovery 必須在 GitHub Actions Postgres service 上執行。

不得只使用：

```text
SQLite create_all
```

正式驗收至少需要：

```text
Alembic upgrade head
Tumor Board transaction tests
Digital Thread tests
Restart Recovery
Alembic downgrade 020→019
Alembic re-upgrade 019→020
```

CI 未通過：

```text
Reviewer 最高 89
Phase 3C = PARTIAL
Ready for Next Phase = NO
```

---

# 二十一、禁止事項

禁止：

```text
使用 dict 或 memory cache 作正式 Storage
Mock Repository 代替 Integration Test
手工 session.add 冒充 API 鏈路
跳過 Postgres Test
xfail 核心測試
刪除失敗測試
降低 Coverage
修改已驗收 Migration 017/018/019
修改 Phase 3A / Phase 3B 核心功能
修改 AGENTS.md
修改 Vercel
開始 Treatment Plan
開始 Phase 3D
```

---

# 二十二、Commit Scope

只能包含：

```text
Tumor Board Consensus Engine
Rules
Models
Migration 020
Repositories
Service
API
Frontend
Report Section
Tests
Workflow
Review
Summary
```

不得混入其他功能。

---

# 二十三、Reviewer Gate

Reviewer 必須逐條確認：

```text
[ ] Recommendation、Clinical Decision、Patient 關聯一致
[ ] created_by 寫入
[ ] Opinions 全部持久化
[ ] Consensus Trace 多 Step 持久化
[ ] Transaction All-or-Nothing
[ ] API POST/GET/List 可用
[ ] Frontend List/Detail/Create 可用
[ ] Digital Thread 可還原
[ ] Restart 後可讀
[ ] Migration 020 upgrade/downgrade/re-upgrade
[ ] Postgres CI 全綠
```

任一項：

```text
FAIL
PARTIAL
未驗證
```

則：

```text
滿足需求 = NO
Reviewer 最高 89
Ready for Next Phase = NO
```

Reviewer 必須：

```text
>=95
```

才可標記 Phase 3C 完成。

---

# 二十四、Git 要求

完成後建立單一主要 Commit：

```text
feat(phase3c): add tumor board consensus engine
```

若 GitHub Actions 發現真實問題，允許追加聚焦修復 Commit，但不得混入其他階段。

推送：

```text
origin/master
```

禁止：

```text
force push
rebase master
只提交 workflow 記錄
```

---

# 二十五、完成後只回報

不要描述中間過程。

全部完成、測試、CI、Reviewer、Commit、Push 後，只輸出：

```text
Commit SHA

Files Changed

Migration 020
New Tables
New Models
New Repositories
New Service
Consensus Engine
Consensus Rule Set

POST API
GET API
List API
Opinions API
Trace API

Frontend List Route
Frontend Detail Route
Frontend Create Flow
Report Section

Patient Link Validation
Recommendation Link Validation
Clinical Decision Link Validation
created_by Audit

Opinion Persistence
Consensus Persistence
Trace Persistence
Transaction Rollback
Restart Recovery
Digital Thread

Migration Upgrade
Migration Downgrade
Migration Re-upgrade

Backend Tests
Frontend Tests
Postgres Integration Tests
CI Run ID
CI Result

requirements.md additions
requirements.md deletions

Git Status
Push Result
Reviewer Score
```

最後輸出：

```text
Phase 3C：
PASS / PARTIAL / FAIL

Accepted：
YES / NO

Ready for ChatGPT GitHub Review：
YES / NO

Ready for Phase 3D：
YES / NO
```

只有全部要求完成、Postgres CI 全綠、Reviewer ≥95 時，才允許：

```text
Phase 3C Accepted：YES
Ready for Phase 3D：YES
```

推送後停止。

不要自行開始 Phase 3D。
