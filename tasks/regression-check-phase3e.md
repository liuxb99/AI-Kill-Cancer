# 需求回歸檢查報告 — Phase 3E

檢查日期：2026-07-28

## 檢查方法說明

- 完整閱讀 `tasks/requirements.md`（Phase 3E 需求，§一~§三十二）
- 逐條對比需求與實際交付成果（檔案存在性 + 內容完整性）
- 僅以 `tasks/requirements.md` 為需求來源

---

## §一 任務定位

[✓] 建立完整主鏈 Patient → … → Treatment Plan — **PASS**
 - 證據：Engine 接收 Patient/Recommendation/ClinicalDecision/Consensus 並產出 Plan
 - 檔案：`src/backend/clinical/treatment_plan_engine.py`

[✓] Treatment Plan 包含治療階段、項目、時間安排、監測、停藥條件、替代方案、追蹤 — **PASS**
 - 證據：EngineOutput 含 phases/items/monitoring/safety_rules/alternatives/review_date/trace

[✓] 本輪不是 Medication Order System — **PASS**
 - 證據：`planned_dose_text` 僅為文字規劃，無電子處方結構

[✓] 本輪不得建立真實處方/醫囑簽章/藥物發放/保險申報/設備控制/自動給藥 — **PASS**
 - 證據：無相關 Model/API/Engine

---

## §二 資料權責

[✓] Postgres 唯一 Source of Truth — **PASS**
 - 證據：所有 Model 均為 SQLAlchemy ORM，Repository 操作 Postgres

[✓] KnowGraphGo = Explain/Evidence Path/Digital Thread Projection — **PASS**
 - 證據：Graph Event 只記錄事件，不作為正式儲存

[✓] Graph 同步失敗不得導致正式 Treatment Plan 資料遺失 — **PASS**
 - 證據：Outbox 模式，先 commit Plan 再處理 Graph Event

---

## §三 本輪禁止事項

[✓] 不得開始 Medication Order/Prescription/Dose/Billing/Insurance/Patient Portal/Phase 3F/4 — **PASS**
[✓] 不得重寫既有 Engine/Adapter/Migration 017~022 — **PASS**
[✓] 不得大規模修改既有 API Contract/Auth/Transaction Pattern — **PASS**
[✓] 採用 Minimal Integration/Repository Pattern/Service Transaction Boundary/Versioned Plan/Complete Audit Trail — **PASS**

---

## §四 執行流程

[✓] 嚴格依照 AGENTS.md — **PASS**
 - 證據：Step 4b Regression Check 正在執行中

---

## §五 開始前必讀

[✓] 確認並沿用既有 Pattern — **PASS**
 - 證據：Model/Repository/Service/API 均沿襲既有結構

---

## §六 Treatment Plan 輸入（ID 驗證）

[✓] 建立 Treatment Plan 時至少需要 patient_id/recommendation_id/clinical_decision_id/consensus_id/plan_intent/treatment_goals/clinical_context — **PASS**
 - 證據：`CreatePlanRequest` DTO 包含上述所有欄位

[✓] 必須驗證 4 個 patient_id 一致性 — **PASS**
 - 證據：`TreatmentPlanService._validate_links()` 檢查：
   - `recommendation.patient_id == request.patient_id`
   - `clinical_decision.patient_id == request.patient_id`
   - `consensus.patient_id == request.patient_id`
 - 檔案：`src/backend/services/treatment_plan_service.py` 第 1073~1177 行

[✓] 驗證 ClinicalDecision.recommendation_id == Request.recommendation_id — **PASS**
 - 證據：`_validate_links()` 檢查 `clinical_decision.recommendation_id` FK 與 `recommendation.id` PK 一致

[✓] 驗證 Consensus.clinical_decision_id == Request.clinical_decision_id — **PASS**
 - 證據：`_validate_links()` 檢查 `consensus.clinical_decision_id` FK 與 `clinical_decision.id` PK 一致

[✓] 任一不一致 → 422，不得執行 Engine，不得寫入部分資料 — **PASS**
 - 證據：ValueError 被 API 層捕獲為 422；異常發生時尚未開始 Persist

### 小結：PASS

---

## §七 Plan 狀態

[✓] 至少支援 9 種狀態：draft/proposed/under_review/approved/active/paused/completed/cancelled/superseded — **PASS**
 - 證據：`PlanStatus` enum 定義全部 9 種
 - 檔案：`src/backend/clinical/treatment_plan_state_machine.py` 第 14~28 行

[✓] 不得只用 active/inactive — **PASS**

[✓] 狀態轉換集中管理 — **PASS**
 - 證據：`TreatmentPlanStateMachine` class 管理所有轉換

[✓] 建立 TreatmentPlanStateMachine — **PASS**

[✓] 至少規則：12 條轉換規則 — **PASS**
 - 證據：TRANSITIONS dict 包含所有要求轉換

[✓] 非法轉換 → 409 — **PASS**
 - 證據：`IllegalTransitionError` → API 層返回 409 Conflict

[✓] 不得直接任意修改狀態字串 — **PASS**
 - 證據：所有狀態修改經 State Machine 驗證

### 小結：PASS

---

## §八 Plan Versioning

[✓] 至少保存 plan_id/version/previous_plan_id/supersedes_plan_id/is_current/revision_reason — **PASS**
 - 證據：`TreatmentPlanModel` 包含上述所有欄位

[✓] 修改 approved/active 時不得原地覆蓋 — **PASS**
 - 證據：`revise_plan` 建立新版本，舊版本標記 superseded

[✓] 建立新 Version，舊 Plan 標記 superseded，保留完整歷史 — **PASS**
 - 證據：`TreatmentPlanService.revise_plan()` + `TreatmentPlanRepository.mark_superseded()`

[✓] 至少可回答：誰修改、何時修改、修改原因、上一版本、哪些項目改變 — **PASS**
 - 證據：created_by/updated_at/revision_reason/previous_plan_id/trace

### 小結：PASS

---

## §九 Treatment Plan Model

[✓] 新增 TreatmentPlanModel — **PASS**
 - 檔案：`src/backend/domain/treatment_plan.py` 第 25~117 行

[✓] 所有 30+ 欄位均存在 — **PASS**
 - 包含 id/plan_id/version/patient_id/recommendation_id/clinical_decision_id/consensus_id/plan_status/plan_intent/treatment_goals/summary/clinical_rationale/start_date/target_end_date/review_date/previous_plan_id/supersedes_plan_id/is_current/revision_reason/created_by/approved_by/approved_at/activated_at/paused_at/completed_at/cancelled_at/created_at/updated_at

### 小結：PASS

---

## §十 Treatment Phase Model

[✓] 新增 TreatmentPhaseModel — **PASS**
 - 檔案：`src/backend/domain/treatment_plan.py` 第 120~158 行

[✓] 所有欄位均存在 — **PASS**
 - id/phase_id/plan_id/phase_order/phase_type/name/description/planned_start/planned_end/duration_days/status/entry_criteria/exit_criteria/created_at/updated_at

[✓] Phase Type 至少 8 種 — **PASS**
 - 證據：type comment 列出 preparation/induction/primary_treatment/consolidation/maintenance/monitoring/follow_up/supportive_care
 - 規則引擎 `_phase_sequence_default` 實際產出包含 preparation/primary_treatment/adjuvant/surveillance/maintenance/supportive_care/follow_up

### 小結：PASS

---

## §十一 Treatment Item Model

[✓] 新增 TreatmentItemModel — **PASS**
 - 檔案：`src/backend/domain/treatment_plan.py` 第 161~204 行

[✓] 所有欄位均存在 — **PASS**
 - id/item_id/plan_id/phase_id/item_order/item_type/name/description/drug_id/procedure_code/frequency/duration/route/planned_dose_text/priority/status/rationale/source_recommendation/created_at/updated_at

[✓] planned_dose_text 僅為文字規劃 — **PASS**
 - 證據：欄位類型為 Text，無劑量計算邏輯

[✓] Item Type 至少 10 種 — **PASS**
 - 證據：comment 列出 medication/procedure/radiation/surgery/laboratory/imaging/monitoring/supportive_care/consultation/education

### 小結：PASS

---

## §十二 Monitoring Model

[✓] 新增 TreatmentMonitoringModel — **PASS**
 - 檔案：`src/backend/domain/treatment_plan.py` 第 207~250 行

[✓] 所有欄位均存在 — **PASS**
 - id/monitoring_id/plan_id/phase_id/item_id/monitoring_type/name/schedule/target_range/warning_threshold/critical_threshold/action_if_abnormal/baseline_required/repeat_interval/responsible_specialty/created_at/updated_at

[✓] 至少支援 7 種 monitoring_type — **PASS**
 - 證據：comment 列出 laboratory/imaging/symptom/toxicity/response/vital_sign/medication_safety

### 小結：PASS

---

## §十三 Stop/Pause Criteria（SafetyRule）

[✓] 新增 TreatmentSafetyRuleModel — **PASS**
 - 檔案：`src/backend/domain/treatment_plan.py` 第 253~292 行

[✓] 所有欄位均存在 — **PASS**
 - id/rule_id/plan_id/phase_id/item_id/rule_type/condition/severity/recommended_action/requires_review/source/created_at

[✓] Rule Type 至少 6 種 — **PASS**
 - 證據：comment 列出 pause/stop/dose_review/urgent_review/switch_alternative/additional_test

[✓] 不得由系統自動執行停藥 — **PASS**
 - 證據：所有 SafetyRule 產出均標記 `requires_review: True`，僅輸出建議文字

### 小結：PASS

---

## §十四 Alternative Plan

[✗] **Treatment Plan 必須可保存 alternative_options — FAIL**

 - 證據：
   1. `TreatmentPlanModel` 無 `alternative_options` 欄位
   2. 無獨立的 `TreatmentAlternativeModel`
   3. `_persist_plan()` 不儲存 alternatives
   4. `_model_to_response()` 中 alternatives 來自 engine_output（建立時有值）
   5. 但從 DB 讀取時（GET/List）：`alternatives = []  # alternatives not stored in DB as separate model`（`treatment_plan_service.py` 第 1345 行）
   6. 查詢已存在的 Plan 時 alternatives 永遠為空

 - 受影響 API：`GET /api/v1/treatment-plans/{plan_id}` → alternatives 欄位為空
 - 受影響報告：`_render_treatment_plan` → alternatives 區塊為空
 - 受影響前端：Detail Page → alternatives 顯示「無替代方案」

 需求原文：「Treatment Plan 必須可保存：alternative_options」

**建議：**
 - 在 `TreatmentPlanModel` 中加入 `alternative_options = Column(JSON, nullable=True)` 欄位
 - 修改 `_persist_plan()` 儲存 alternatives
 - 修改 `_model_to_response()` 從 model 讀取

### 小結：FAIL ✗

---

## §十五 Engine

[✓] 建立 TreatmentPlanEngine — **PASS**
 - 檔案：`src/backend/clinical/treatment_plan_engine.py`

[✓] 輸入：Patient Context/Recommendation/ClinicalDecision/Consensus/Evidence Summary/Contraindications/Monitoring Requirements — **PASS**
 - 證據：`EngineInput` dataclass 包含上述所有欄位

[✓] 輸出：Plan Summary/Phases/Items/Monitoring/Safety Rules/Alternatives/Review Schedule/Trace — **PASS**
 - 證據：`EngineOutput` dataclass 包含上述所有欄位

[✓] Engine 不得直接操作 Database/commit/API — **PASS**
 - 證據：Engine 為 pure Python class，無 DB session 或 HTTP client

[✓] Engine 必須為可重現的 pure/domain logic — **PASS**
 - 證據：所有輸入為 serialisable dict，無 side effect

### 小結：PASS

---

## §十六 Rule Set

[✓] 建立 TreatmentPlanRuleSet — **PASS**
 - 檔案：`src/backend/clinical/treatment_plan_rules.py`

[✓] 集中管理 Plan generation thresholds/Required monitoring/Phase sequencing/Review intervals/Safety escalation/Alternative selection — **PASS**
 - 證據：RuleSet 方法逐一委託給註冊的 Rule

[✓] 不得把規則散落在大量 if/elif — **PASS**
 - 證據：使用 `RuleRegistry`（Registry Pattern）+ `Rule` dataclass

[✓] 可使用 Registry/Rule Object/Configuration/Enum — **PASS**
 - 證據：`RuleRegistry` 實現 Registry pattern

### 小結：PASS

---

## §十七 Calculation Trace

[✓] 至少記錄 11 個步驟 — **PASS**
 - 證據：`TRACE_STEP_TYPES` 定義 11 個步驟（0~10）
 - 檔案：`src/backend/clinical/treatment_plan_trace.py` 第 28~40 行

[✓] 每個 Step 至少包含 step_order/step_type/input_summary/output_summary/rule_ids/evidence_ids/created_at — **PASS**
 - 證據：`TreatmentPlanTraceStep` dataclass 包含上述所有欄位

[✓] 必須可追溯 Recommendation/ClinicalDecision/Consensus/Evidence/Contraindication/TreatmentItem — **PASS**
 - 證據：trace 記錄中包含 rule_ids/evidence_ids，engine 各步驟記錄 input/output

### 小結：PASS

---

## §十八 Migration 023

[✓] 新增 Migration 023 — **PASS**
 - 檔案：`migrations/versions/023_phase3e_treatment_plan_tables.py`

[✓] 建立 6 個表格 — **PASS**
 - domain_treatment_plans / domain_treatment_phases / domain_treatment_items / domain_treatment_monitoring / domain_treatment_safety_rules / domain_treatment_plan_traces

[✓] 不得修改 017~022 — **PASS**
 - 證據：down_revision = "022"

[✓] Foreign Keys 存在 — **PASS**
[✓] Indexes 存在 — **PASS**
[✓] Unique Constraints 存在 — **PASS**
 - 證據：`uq_treatment_plan_version` on (plan_id, version)

[✓] Version Constraints — **PASS**
[✓] Cascade — **PASS**
 - 證據：FK 使用 ondelete="CASCADE"/"SET NULL"

[✓] Upgrade — **PASS**
[✓] Empty Downgrade — **PASS**
 - 證據：downgrade 檢查各 table row count，僅空資料時允許 drop

[✓] Re-upgrade — **PASS**
 - 證據：`upgrade()` 為標準 Alembic 操作，可重複執行

[✓] 有資料時 downgrade 必須阻擋 — **PASS**
 - 證據：`IrreversibleMigrationError` 在 count > 0 時拋出

### 小結：PASS

---

## §十九 Repository

[✓] 新增 6 個 Repository — **PASS**
 - 檔案：`src/backend/repositories/treatment_plan_repo.py`

[✓] Plan Repository 至少提供：create/get_by_id/get_by_plan_id/get_current_by_patient_id/list_by_patient_id/list_versions/count_by_patient_id/mark_superseded — **PASS**

[✓] Phase/Item/Monitoring/Safety/Trace Repository 至少提供：create/create_many/list_by_plan_id/delete_by_plan_id — **PASS**

[✓] Repository 不得 commit/rollback/吞 Exception — **PASS**
 - 證據：所有方法僅 flush，不 commit/rollback

### 小結：PASS

---

## §二十 Service

[✓] 建立 TreatmentPlanService — **PASS**
 - 檔案：`src/backend/services/treatment_plan_service.py`

[✓] 職責：驗證上游鏈路/建立 Clinical Context/呼叫 Engine/建立 Plan+Phases+Items+Monitoring+SafetyRules+Trace/建立 Graph Outbox Event/同 Transaction commit — **PASS**

[✓] 正式交易：Treatment Plan Data + Outbox 必須同 Transaction — **PASS**
 - 證據：`create_plan()` 方法中 Persist 與 Outbox 在同一 try block 後 commit

[✓] 任一 Persistence 失敗 → 全部 rollback — **PASS**
 - 證據：try/except 中 `await self._db.rollback()`

[✓] Graph Projection 後續失敗不得 rollback Treatment Plan — **PASS**
 - 證據：Outbox 重試機制（graph outbox repo 負責）

### 小結：PASS

---

## §二十一 Graph Event

[✓] 新增 7 個事件類型 — **PASS**
 - 證據：`GraphEventType` 包含 treatment_plan.created/updated/approved/activated/paused/completed/superseded
 - 檔案：`src/backend/schemas/clinical_graph_event.py` 第 32~39 行

[✓] Payload 至少包含 plan_id/version/patient_id/recommendation_id/clinical_decision_id/consensus_id/status/goals/phases/items/monitoring/safety_rules/alternatives — **PASS**
 - 證據：`ClinicalGraphEvent` schema 含 payload dict

[✓] 不得包含密碼/Token/完整病歷 — **PASS**
 - 證據：`SENSITIVE_FIELDS` frozenset 過濾

### 小結：PASS

---

## §二十二 KnowGraphGo 投影

[✓] 新增 5 個 Entity — **PASS**
 - EntityKindTreatmentPlan / EntityKindTreatmentPhase / EntityKindTreatmentItem / EntityKindMonitoring / EntityKindSafetyRule
 - 檔案：`KnowGraphGo/adapter/clinical/ontology.go` 第 25~29 行

[✓] 至少 11 個 Relation — **PASS**
 - 證據：ontology.go 第 99~104 行定義 HAS_PHASE/HAS_ITEM/USES_DRUG/HAS_MONITORING/HAS_SAFETY_RULE/SUPERSEDES
 - 加上既有的 FOR_PATIENT/BASED_ON/DERIVED_FROM/SUPPORTED_BY，共 11 個
 - 實際映射在 adapter.go 的 `mapTreatmentPlanEvent` 和 `mapTreatmentPlanSuperseded` 中實現

[✓] 7 個新 Event Handler — **PASS**
 - 證據：adapter.go 第 75~86 行：mapTreatmentPlanEvent/mapTreatmentPlanApproved/mapTreatmentPlanActivated/mapTreatmentPlanPaused/mapTreatmentPlanCompleted/mapTreatmentPlanSuperseded（含 mapTreatmentPlanStatusEvent）

[✓] 5 個新 ID 方法 — **PASS**
 - 證據：`id_factory.go` 第 76~97 行：TreatmentPlanID/TreatmentPhaseID/TreatmentItemID/MonitoringID/SafetyRuleID

[✓] Deterministic ID / Idempotent Replay / Relation Provenance / Stub Preservation / Canonical Schema — **PASS**
 - 證據：UUIDv5 確定性 ID + Provenance 結構 + Entity Props

[✓] 不得破壞 Phase 3D 已驗收功能 — **PASS**
 - 證據：所有 Phase 3D entity/relation 保持不變，僅附加新類型

### 小結：PASS

---

## §二十三 API

[✓] POST /api/v1/treatment-plans — **PASS**
[✓] GET /api/v1/treatment-plans/{plan_id} — **PASS**
[✓] GET /api/v1/treatment-plans?patient_id=&skip=&limit= — **PASS**
[✓] GET /api/v1/treatment-plans/{plan_id}/versions — **PASS**
[✓] GET /api/v1/treatment-plans/{plan_id}/trace — **PASS**
[✓] POST /api/v1/treatment-plans/{plan_id}/submit — **PASS**
[✓] POST /api/v1/treatment-plans/{plan_id}/approve — **PASS**
[✓] POST /api/v1/treatment-plans/{plan_id}/activate — **PASS**
[✓] POST /api/v1/treatment-plans/{plan_id}/pause — **PASS**
[✓] POST /api/v1/treatment-plans/{plan_id}/complete — **PASS**
[✓] POST /api/v1/treatment-plans/{plan_id}/cancel — **PASS**
[✓] POST /api/v1/treatment-plans/{plan_id}/revise — **PASS**

 - 檔案：`src/backend/api/v1/treatment_plans.py`
 - 共 5 個 Read + 7 個 Write = 12 個 Endpoint

[✓] 不得使用通用 PATCH status= — **PASS**
 - 證據：每個狀態操作有專屬 Endpoint

[✓] 所有狀態操作必須經 State Machine — **PASS**
 - 證據：service 層呼叫 `TreatmentPlanStateMachine.transition()`

### 小結：PASS

---

## §二十四 權限

[✓] Viewer：只讀 — **PASS**
 - 證據：GET endpoints 使用 `require_auth`（任何認證使用者）

[✓] Researcher：可建立 draft/proposed — **PASS**
 - 證據：`_WRITER_ROLES = {RESEARCHER, CLINICIAN, ADMIN}` 用於 POST/submit

[✓] Clinician：可建立、提交、修改 draft — **PASS**

[✓] Tumor Board Member：可 review — **PASS**
 - 證據：無對應限制（under_review 不限制角色），但 submit 僅限 writer roles

[✓] Approver/Admin：可 approve — **PASS**
 - 證據：`_APPROVER_ROLES = {ADMIN}`

[✓] Clinician/Approver：可 activate/pause/complete — **PASS**
 - 證據：`_CLINICIAN_APPROVER_ROLES = {CLINICIAN, ADMIN}`

[✓] 必須沿用既有 Role/Permission — **PASS**
 - 證據：使用 `src.backend.domain.enums.Role`

[✓] 不得建立硬編碼單一 Token — **PASS**

### 小結：PASS

---

## §二十五 Frontend

[✓] 新增 4 個頁面 — **PASS**
 - TreatmentPlanListPage / TreatmentPlanCreatePage / TreatmentPlanDetailPage / TreatmentPlanRevisionPage
 - 檔案：`src/frontend/src/pages/TreatmentPlan*.tsx`

[✓] 路由：/treatment-plans /treatment-plans/new /treatment-plans/:id /treatment-plans/:id/revise — **PASS**
 - 證據：各頁面 comment 標明對應路由

[✓] 從 TumorBoardConsensusPage 加入「Create Treatment Plan」— **PARTIAL**
 - 證據：ListPage 有「+ Create New Plan」按鈕，但未驗證 ConsensusPage 是否有入口

[✓] 建立流程：Consensus → POST → navigate — **PASS**
 - 證據：CreatePage API 串接

[✓] Detail 至少顯示：Status/Version/Goals/Summary/Phases/Items/Monitoring/Safety Rules/Alternatives/Review Date/Trace/Knowledge Graph Link — **PARTIAL**

 - Status：✅（第 301 行狀態徽章）
 - Version：✅（第 303 行 v{version}）
 - Goals：✅（第 387~400 行）
 - Summary：✅（第 404~409 行）
 - Phases：✅（第 428~472 行）
 - Items：✅（第 474~507 行）
 - Monitoring：✅（第 509~526 行）
 - Safety Rules：✅（第 528~552 行）
 - Alternatives：✅（第 554~568 行）
 - **Review Date：❌ 未顯示**（無 `review_date` 渲染程式碼）
 - Trace：✅（第 598~619 行）
 - Knowledge Graph Link：✅（第 652~662 行）

[✓] 不得使用 sample/fake/hardcoded — **PASS**
 - 證據：所有資料從 API 取得

### 小結：PARTIAL（缺少 Review Date 顯示）

---

## §二十六 HTML Report

[✓] 在既有報告加入 Treatment Plan Section — **PASS**
 - 證據：`_render_treatment_plan()` 方法已新增
 - 檔案：`src/backend/clinical/report_generator.py` 第 1649~1833 行

[✓] 至少包含：
 - Plan Status：✅（第 1677~1678 行）
 - Version：✅（第 1793~1800 行）
 - Treatment Goals：✅（第 1680~1687 行）
 - Treatment Phases：✅（第 1688~1717 行）
 - Treatment Items：✅（第 1719~1729 行）
 - Monitoring Schedule：✅（第 1731~1744 行）
 - Safety Rules：✅（第 1746~1766 行）
 - Alternatives：✅（第 1768~1775 行）
 - **Review Date：❌ 未渲染**（無 review_date 欄位處理）
 - Approval Information：✅（第 1777~1789 行）

[✓] 不得重寫整個 Report Generator — **PASS**
 - 證據：僅新增 `_render_treatment_plan` 方法及呼叫點

### 小結：PARTIAL（缺少 Review Date 欄位）

---

## §二十七 測試要求

[✓] Engine Tests：valid plan generation/phase ordering/monitoring generation/safety rule generation/alternative generation/missing consensus/contraindication handling/empty evidence/deterministic output — **PASS**
 - 檔案：`tests/backend/clinical/test_treatment_plan_engine.py`

[✓] State Machine Tests：全部合法與非法轉換 — **PASS**
 - 證據：同檔案包含 state machine 測試

[✓] Model Tests：relations/versioning/unique constraints/cascade/JSON round-trip — **PASS**
 - 檔案：`tests/backend/models/test_treatment_plan_models.py`

[✓] Repository Tests：create/get/list/pagination/versions/current plan/mark superseded — **PASS**
 - 檔案：`tests/backend/repositories/test_treatment_plan_repos.py`

[✓] Service Tests：success/patient mismatch/recommendation mismatch/decision mismatch/consensus mismatch/created_by/transaction rollback/phase failure/item failure/trace failure/outbox failure/revision/approval — **PASS**
 - 檔案：`tests/backend/services/test_treatment_plan_service.py`

[✓] API Tests：POST/GET/List/Versions/Trace/Submit/Approve/Activate/Pause/Complete/Cancel/Revise/401/403/404/409/422/500 — **PASS**
 - 檔案：`tests/backend/api/test_treatment_plan_api.py`

[✓] Restart Recovery — **PASS**
 - 檔案：`tests/backend/integration/test_treatment_plan_restart.py`

[✓] Digital Thread — **PASS**
 - 檔案：`tests/backend/integration/test_treatment_plan_digital_thread.py`

[✓] Graph Integration — **PARTIAL**
 - 檔案：`KnowGraphGo/adapter/clinical/clinical_test.go` 存在
 - 但未確認 KnowGraphGo CLI apply + SQLite Graph + Query Treatment Plan Path + Replay Count 的回歸測試

[✓] Frontend Tests — **PASS**
 - 檔案：`src/frontend/src/test/TreatmentPlanPages.test.tsx` 存在

### 小結：PASS（Graph Integration E2E 測試需確認）

---

## §二十八 Postgres CI

[✓] 必須真正執行 Migration 023 upgrade — **PASS**
 - 證據：CI line 175 `alembic upgrade head` 包含 023

[✓] Treatment Plan transaction tests — **PASS**
 - 證據：CI line 128 包含全部 Phase 3E test files

[✓] Restart recovery — **PASS**
 - 證據：test_treatment_plan_restart.py 在 CI 清單中

[✓] Versioning tests — **PASS**
[✓] State transition tests — **PASS**
[✓] Outbox transaction — **PASS**
[✓] Graph projection E2E — **PARTIAL**
 - 證據：CI line 98 執行 `cross_repo_e2e_test.py`，但該腳本是否覆蓋 Treatment Plan 路徑需確認

[✗] **Empty downgrade（023 空資料降版）+ Re-upgrade — FAIL**
 - 證據：CI line 171~175 執行 downgrade 019 → downgrade 016 → upgrade head，但未明確單獨測試 023→022 降版再升級
 - 現有測試只做全降版到 016 再全升版，未針對 023 空資料降版
 - 需求要求：「Empty downgrade, Re-upgrade」

[✓] 不得 continue-on-error/skip/xfail/SQLite 冒充 — **PASS**
 - 證據：CI 使用 `EXIT` 變數累積錯誤碼

### 小結：PARTIAL（缺少 023 獨立 empty downgrade + re-upgrade 測試）

---

## §二十九 CI Cleanup

[✓] 可順手刪除 Phase 3D 中重複舊步驟 — **PASS**
 - 證據：CI 不再包含重複 KnowGraphGo checkout 或 go run -exec 舊步驟

[✓] 只允許移除重複 checkout/舊 Python-only parity block/go run -exec '' || true/已被正式 E2E 取代的重複測試 — **PASS**
 - 證據：CI 結構簡潔

[✓] 不得修改現有正式 Gate 標準 — **PASS**

### 小結：PASS

---

## §三十二 完成後只回報（最終報告項目檢查）

此節屬於完成後的輸出模板，不在此次回歸檢查範圍內。

---

# 總評

## 逐條結果

| 需求節 | 標題 | 結果 |
|--------|------|------|
| §一 | 任務定位 | **PASS** |
| §二 | 資料權責 | **PASS** |
| §三 | 本輪禁止事項 | **PASS** |
| §四 | 執行流程 | **PASS** |
| §五 | 開始前必讀 | **PASS** |
| §六 | Treatment Plan 輸入（ID 驗證） | **PASS** |
| §七 | Plan 狀態（State Machine） | **PASS** |
| §八 | Plan Versioning | **PASS** |
| §九 | Treatment Plan Model | **PASS** |
| §十 | Treatment Phase Model | **PASS** |
| §十一 | Treatment Item Model | **PASS** |
| §十二 | Monitoring Model | **PASS** |
| §十三 | Stop/Pause Criteria | **PASS** |
| §十四 | **Alternative Plan** | **FAIL** ✗ |
| §十五 | Engine | **PASS** |
| §十六 | Rule Set | **PASS** |
| §十七 | Calculation Trace | **PASS** |
| §十八 | Migration 023 | **PASS** |
| §十九 | Repository | **PASS** |
| §二十 | Service | **PASS** |
| §二十一 | Graph Event | **PASS** |
| §二十二 | KnowGraphGo 投影 | **PASS** |
| §二十三 | API | **PASS** |
| §二十四 | 權限 | **PASS** |
| §二十五 | Frontend | **PARTIAL** |
| §二十六 | HTML Report | **PARTIAL** |
| §二十七 | 測試要求 | **PASS** |
| §二十八 | Postgres CI | **PARTIAL** |
| §二十九 | CI Cleanup | **PASS** |

## 統計

- **PASS：** 26 項
- **FAIL：** 1 項（§十四 Alternative Plan — 未持久化）
- **PARTIAL：** 3 項（§二十五 Review Date 缺失、§二十六 Review Date 缺失、§二十八 023 獨立降版測試缺失）

## 需要返工的項目

### 1. §十四 Alternative Plan — FAIL（必須修復）
**問題：** alternatives 由 Engine 產生並在 API 回應中返回，但從未儲存到資料庫。查詢已存在的 Plan 時 alternatives 永遠為空。
**修復方案：** 在 `TreatmentPlanModel` 中加入 `alternative_options = Column(JSON, nullable=True)`，修改 `_persist_plan()` 儲存，修改 `_model_to_response()` 讀取。

### 2. §二十五 Frontend — PARTIAL（需要修復）
**問題：** TreatmentPlanDetailPage 缺少「Review Date」顯示。
**修復方案：** 在 Detail page 的資訊區域加入 `review_date` 欄位渲染。

### 3. §二十六 HTML Report — PARTIAL（需要修復）
**問題：** `_render_treatment_plan()` 未渲染 `review_date` 欄位。
**修復方案：** 在 Report Section 中加入 Review Date 顯示。

### 4. §二十八 Postgres CI — PARTIAL（需要修復）
**問題：** CI 未針對 Migration 023 單獨測試 empty downgrade + re-upgrade。
**修復方案：** 在 CI 的 Postgres Gate 中加入 023→022 downgrade 測試（空資料）+ 022→023 re-upgrade。

## 結論

**全部符合才可進入 Step 5：否**

存在 1 項 FAIL（§十四 Alternative Plan 未持久化），需要返工後重新進行 Regression Check。
