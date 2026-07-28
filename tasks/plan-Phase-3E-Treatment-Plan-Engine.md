# Phase 3E Treatment Plan Engine V1 — 執行計劃

## 計劃總覽

本計劃將 **58 項子任務**（含 8 個 M、10 個 E、14 個 A、7 個 R、8 個 F、9 個 T、8 個 K、3 個 C）劃分為 **8 個執行批次**，每批次為可獨立交付的單元，嚴格依據任務依賴關係排序。

### 批次總覽

| Batch | 名稱 | 任務數 | 主責角色 | 預估工時 |
|-------|------|--------|---------|---------|
| 0 | Foundation — 基礎建設先行 | 15 (M-01~M-08 + R-01~R-07) | db-modeler, repositories | 48 人時 |
| 1 | Engine Core — 引擎核心 | 6 (E-01~E-04 + E-08~E-09) | backend-logic | 40 人時 |
| 2 | Service Layer — 服務層 | 4 (E-05~E-07 + E-10) | backend-logic | 40 人時 |
| 3 | API Layer — API 層 | 14 (A-01~A-14) | api-designer | 48 人時 |
| 4 | Frontend & Report — 前端與報告 | 8 (F-01~F-08) | frontend-logic | 48 人時 |
| 5 | KnowGraphGo — 圖形投影 | 8 (K-01~K-08) | knowgraphgo-dev | 40 人時 |
| 6 | Integration + CI — 集成測試與 CI | 12 (T-01~T-09 + C-01~C-03) | test-writer, devops | 48 人時 |
| 7 | Review & Finalize — 評審與提交 | 0 (評審與修正) | REVIEWER, PLANNER | 16 人時 |
| | **總計** | **58** | | **~328 人時** |

---

## Batch 0：Foundation（基礎建設先行）

**目標**：建立 6 張資料庫表、對應的 ORM Model、Repository 層及基礎測試，為後續所有批次提供資料存取基礎。

**依賴**：無（PLANNER 完成後即可啟動）

**主責角色**：db-modeler, repositories

### 任務詳情

---

#### M-01：建立 TreatmentPlanModel

| 項目 | 內容 |
|------|------|
| **角色** | db-modeler |
| **描述** | 建立 `TreatmentPlanModel`，包含 Requirements §九 全部欄位：id (UUID PK)、plan_id (unique)、version、patient_id (FK→patients)、recommendation_id (FK→recommendations)、clinical_decision_id (FK→clinical_decisions)、consensus_id (FK→tumor_board_consensus)、plan_status、plan_intent、treatment_goals (JSON)、summary、clinical_rationale、start_date、target_end_date、review_date、previous_plan_id、supersedes_plan_id、is_current、revision_reason、created_by (FK→users)、approved_by、approved_at、activated_at、paused_at、completed_at、cancelled_at、created_at、updated_at |
| **依賴** | 無 |
| **預計檔案** | `src/backend/domain/treatment_plan.py`（與 M-02~M-06 同檔案） |
| **驗收條件** | Model 定義完整，含所有欄位、FK、Index、relationship 指向子表；可與既有 Base 整合 |

---

#### M-02：建立 TreatmentPhaseModel

| 項目 | 內容 |
|------|------|
| **角色** | db-modeler |
| **描述** | 建立 `TreatmentPhaseModel`，包含 Requirements §十 全部欄位：id (UUID PK)、phase_id (unique)、plan_id (FK→treatment_plans)、phase_order、phase_type (enum：preparation/induction/primary_treatment/consolidation/maintenance/monitoring/follow_up/supportive_care)、name、description、planned_start、planned_end、duration_days、status、entry_criteria (JSON)、exit_criteria (JSON)、created_at、updated_at |
| **依賴** | M-01（依賴 plan_id FK） |
| **預計檔案** | `src/backend/domain/treatment_plan.py` |
| **驗收條件** | Model 含 FK→TreatmentPlanModel、cascade 設定、phase_type 約束 |

---

#### M-03：建立 TreatmentItemModel

| 項目 | 內容 |
|------|------|
| **角色** | db-modeler |
| **描述** | 建立 `TreatmentItemModel`，包含 Requirements §十一 全部欄位：id (UUID PK)、item_id (unique)、plan_id (FK)、phase_id (FK)、item_order、item_type (enum：medication/procedure/radiation/surgery/laboratory/imaging/monitoring/supportive_care/consultation/education)、name、description、drug_id、procedure_code、frequency、duration、route、planned_dose_text、priority、status、rationale、source_recommendation、created_at、updated_at |
| **依賴** | M-01, M-02（依賴 plan_id + phase_id FK） |
| **預計檔案** | `src/backend/domain/treatment_plan.py` |
| **驗收條件** | planned_dose_text 為 Text 類型（非處方）；item_type 使用 Enum；FK 正確 |

---

#### M-04：建立 TreatmentMonitoringModel

| 項目 | 內容 |
|------|------|
| **角色** | db-modeler |
| **描述** | 建立 `TreatmentMonitoringModel`，包含 Requirements §十二 全部欄位：id (UUID PK)、monitoring_id (unique)、plan_id (FK)、phase_id (FK)、item_id (FK)、monitoring_type (enum：laboratory/imaging/symptom/toxicity/response/vital_sign/medication_safety)、name、schedule、target_range (JSON)、warning_threshold (JSON)、critical_threshold (JSON)、action_if_abnormal、baseline_required、repeat_interval、responsible_specialty、created_at、updated_at |
| **依賴** | M-01, M-02, M-03 |
| **預計檔案** | `src/backend/domain/treatment_plan.py` |
| **驗收條件** | 含三個 FK 正確指向；monitoring_type 使用 Enum；JSON 欄位定義正確 |

---

#### M-05：建立 TreatmentSafetyRuleModel

| 項目 | 內容 |
|------|------|
| **角色** | db-modeler |
| **描述** | 建立 `TreatmentSafetyRuleModel`，包含 Requirements §十三 全部欄位：id (UUID PK)、rule_id (unique)、plan_id (FK)、phase_id (FK)、item_id (FK)、rule_type (enum：pause/stop/dose_review/urgent_review/switch_alternative/additional_test)、condition (JSON)、severity、recommended_action、requires_review、source、created_at |
| **依賴** | M-01, M-02, M-03 |
| **預計檔案** | `src/backend/domain/treatment_plan.py` |
| **驗收條件** | rule_type 使用 Enum；condition 為 JSON；requires_review 預設 True |

---

#### M-06：建立 TreatmentPlanTraceModel

| 項目 | 內容 |
|------|------|
| **角色** | db-modeler |
| **描述** | 建立 `TreatmentPlanTraceModel`，包含 Requirements §十七 全部欄位：id (UUID PK)、trace_id (unique)、plan_id (FK)、step_order、step_type、input_summary、output_summary、rule_ids (JSON)、evidence_ids (JSON)、created_at |
| **依賴** | M-01（依賴 plan_id FK） |
| **預計檔案** | `src/backend/domain/treatment_plan.py` |
| **驗收條件** | trace_id unique；plan_id FK→TreatmentPlanModel；rule_ids/evidence_ids 為 JSON list |

---

#### M-07：撰寫 Migration 023

| 項目 | 內容 |
|------|------|
| **角色** | db-modeler |
| **描述** | 撰寫 Alembic Migration `023_phase3e_treatment_plan_tables.py`，建立 6 張表：`domain_treatment_plans`、`domain_treatment_phases`、`domain_treatment_items`、`domain_treatment_monitoring`、`domain_treatment_safety_rules`、`domain_treatment_plan_traces`。含 Foreign Keys（CASCADE/SET NULL 依需求）、Indexes（plan_id、patient_id、status 等查詢熱點）、Unique Constraints（plan_id, phase_id, item_id, monitoring_id, rule_id, trace_id）、Version Constraints（plan_id + version unique）、Cascade delete（plan→phases/items/monitoring/safety/trace）、Upgrade / 空資料 Downgrade / Re-upgrade |
| **依賴** | M-01~M-06（Model 定義完成） |
| **預計檔案** | `migrations/versions/023_phase3e_treatment_plan_tables.py` |
| **驗收條件** | `alembic upgrade head` 成功；`alembic downgrade -1`（空表時）成功；`alembic upgrade head` re-upgrade 成功；有正式資料時 downgrade 阻擋 |

---

#### M-08：Model 測試

| 項目 | 內容 |
|------|------|
| **角色** | db-modeler |
| **描述** | 撰寫 Model 單元測試：relations（Plan→Phases/Items/Monitoring/Safety/Trace cascade）、versioning（plan_id+version unique）、unique constraints（各 *_id 欄位）、cascade delete（刪除 Plan 時子表自動刪除）、JSON round-trip（goals/conditions 等 JSON 欄位寫入讀回正確） |
| **依賴** | M-01~M-06（Model 定義完成） |
| **預計檔案** | `tests/backend/models/test_treatment_plan_models.py` |
| **驗收條件** | 全部測試通過；cascade 行為驗證通過；JSON round-trip 通過 |

---

#### R-01：建立 TreatmentPlanRepository

| 項目 | 內容 |
|------|------|
| **角色** | repositories |
| **描述** | 建立 `TreatmentPlanRepository`，繼承 `BaseRepository[TreatmentPlanModel]`，實作：create、get_by_id、get_by_plan_id、get_current_by_patient_id（is_current=True）、list_by_patient_id（分頁）、list_versions（同一 plan_id 所有版本）、count_by_patient_id、mark_superseded（舊版 is_current=False + supersedes_plan_id 指向新版）。**不得 commit / rollback / 吞 Exception** |
| **依賴** | M-01（TreatmentPlanModel 定義完成） |
| **預計檔案** | `src/backend/repositories/treatment_plan_repo.py` |
| **驗收條件** | 所有方法實作完成；get_current_by_patient_id 回傳最新 is_current=True 版本；mark_superseded 正確更新版本鏈 |

---

#### R-02：建立 TreatmentPhaseRepository

| 項目 | 內容 |
|------|------|
| **角色** | repositories |
| **描述** | 建立 `TreatmentPhaseRepository`，繼承 `BaseRepository[TreatmentPhaseModel]`，實作：create、create_many（批量寫入 phases）、list_by_plan_id、delete_by_plan_id（rollback helper，僅限未提交交易中使用） |
| **依賴** | M-02 |
| **預計檔案** | `src/backend/repositories/treatment_plan_repo.py`（與 R-01 同檔案） |
| **驗收條件** | create_many 支援 bulk insert；delete_by_plan_id 正確刪除指定 plan 的所有 phases |

---

#### R-03：建立 TreatmentItemRepository

| 項目 | 內容 |
|------|------|
| **角色** | repositories |
| **描述** | 建立 `TreatmentItemRepository`，繼承 `BaseRepository[TreatmentItemModel]`，實作：create、create_many、list_by_plan_id、delete_by_plan_id |
| **依賴** | M-03 |
| **預計檔案** | `src/backend/repositories/treatment_plan_repo.py` |
| **驗收條件** | 同 R-02 模式 |

---

#### R-04：建立 TreatmentMonitoringRepository

| 項目 | 內容 |
|------|------|
| **角色** | repositories |
| **描述** | 建立 `TreatmentMonitoringRepository`，繼承 `BaseRepository[TreatmentMonitoringModel]`，實作：create、create_many、list_by_plan_id、delete_by_plan_id |
| **依賴** | M-04 |
| **預計檔案** | `src/backend/repositories/treatment_plan_repo.py` |
| **驗收條件** | 同 R-02 模式 |

---

#### R-05：建立 TreatmentSafetyRuleRepository

| 項目 | 內容 |
|------|------|
| **角色** | repositories |
| **描述** | 建立 `TreatmentSafetyRuleRepository`，繼承 `BaseRepository[TreatmentSafetyRuleModel]`，實作：create、create_many、list_by_plan_id、delete_by_plan_id |
| **依賴** | M-05 |
| **預計檔案** | `src/backend/repositories/treatment_plan_repo.py` |
| **驗收條件** | 同 R-02 模式 |

---

#### R-06：建立 TreatmentPlanTraceRepository

| 項目 | 內容 |
|------|------|
| **角色** | repositories |
| **描述** | 建立 `TreatmentPlanTraceRepository`，繼承 `BaseRepository[TreatmentPlanTraceModel]`，實作：create、create_many、list_by_plan_id、delete_by_plan_id |
| **依賴** | M-06 |
| **預計檔案** | `src/backend/repositories/treatment_plan_repo.py` |
| **驗收條件** | 同 R-02 模式 |

---

#### R-07：Repository 測試

| 項目 | 內容 |
|------|------|
| **角色** | repositories |
| **描述** | 撰寫 Repository 整合測試（使用測試資料庫）：create（單筆與批量）、get（by_id / by_plan_id）、list（分頁）、pagination（skip/limit 正確）、versions（list_versions 回傳正確順序）、current plan（get_current_by_patient_id）、mark_superseded（版本鏈正確） |
| **依賴** | R-01~R-06 |
| **預計檔案** | `tests/backend/repositories/test_treatment_plan_repos.py` |
| **驗收條件** | 全部測試通過；pagination 邊界值正確；mark_superseded 不影響其他 plan |

---

## Batch 1：Engine Core（引擎核心）

**目標**：建立 TreatmentPlan 的領域邏輯核心 — RuleSet（規則集）、StateMachine（狀態機）、Engine（引擎）、CalculationTrace（計算追蹤）及對應單元測試。

**依賴**：Batch 0 完成（Model + Repository 可用於測試輔助）

**主責角色**：backend-logic

### 任務詳情

---

#### E-01：建立 TreatmentPlanRuleSet

| 項目 | 內容 |
|------|------|
| **角色** | backend-logic |
| **描述** | 建立 `TreatmentPlanRuleSet` — 集中管理所有治療計畫產生規則，使用 Registry + Rule Object + Configuration 模式。涵蓋：Plan generation thresholds（何時需要哪些 phase）、Required monitoring（依治療類型決定監測項目）、Phase sequencing（phase_order 與 phase_type 順序規則）、Review intervals（review_date 計算邏輯）、Safety escalation（severity 對應的 recommended_action）、Alternative selection（trigger_condition → alternative priority）。**不得使用大量 if/elif 散落規則** |
| **依賴** | 無（可獨立開發，引用 enum） |
| **預計檔案** | `src/backend/clinical/treatment_plan_rules.py` |
| **驗收條件** | 規則集中登記；每條規則有唯一 ID；可獨立測試；不直接操作 DB |

---

#### E-02：建立 TreatmentPlanStateMachine

| 項目 | 內容 |
|------|------|
| **角色** | backend-logic |
| **描述** | 建立 `TreatmentPlanStateMachine` — 管理 9 種狀態（draft / proposed / under_review / approved / active / paused / completed / cancelled / superseded）之間的合法轉換。至少支援：draft→proposed、proposed→under_review、under_review→approved、approved→active、active→paused、paused→active、active→completed、任意非 completed→cancelled、approved/active→superseded。非法轉換引發 `IllegalTransitionError`（API 層映射為 409）。**不得直接修改 status 字串** |
| **依賴** | 無（可獨立開發） |
| **預計檔案** | `src/backend/clinical/treatment_plan_state_machine.py` |
| **驗收條件** | 所有合法轉換成功；所有非法轉換拋出明確錯誤；狀態枚舉定義完整；可查詢當前狀態的合法下一狀態列表 |

---

#### E-03：建立 TreatmentPlanEngine

| 項目 | 內容 |
|------|------|
| **角色** | backend-logic |
| **描述** | 建立 `TreatmentPlanEngine` — Pure domain logic 引擎，不接受 DB session / API 依賴。輸入：Patient Context（from recommendation / decision）、Recommendation、Clinical Decision、Tumor Board Consensus、Evidence Summary、Contraindications、Monitoring Requirements。輸出：Plan Summary、Treatment Phases（含順序與時程）、Treatment Items（依 phase 分組）、Monitoring Items（依 phase/item 綁定）、Safety Rules（停藥/暫停條件）、Alternatives（備選方案）、Review Schedule（review_date 建議）、Trace（10 步驟追蹤）。使用 RuleSet 驅動決策 |
| **依賴** | E-01（TreatmentPlanRuleSet） |
| **預計檔案** | `src/backend/clinical/treatment_plan_engine.py` |
| **驗收條件** | 相同輸入產生相同輸出（deterministic）；不操作 DB / commit / API；輸出結構完整包含所有要求欄位；可處理 missing consensus / empty evidence / contraindication 情境 |

---

#### E-04：建立 CalculationTrace

| 項目 | 內容 |
|------|------|
| **角色** | backend-logic |
| **描述** | 實作 Engine 內部的 10 步驟計算追蹤：0 load_context、1 validate_links、2 extract_consensus、3 identify_treatment_goals、4 build_phases、5 build_treatment_items、6 build_monitoring、7 build_safety_rules、8 build_alternatives、9 finalize_plan、10 prepare_persistence。每步記錄：step_order、step_type、input_summary、output_summary、rule_ids（引用 RuleSet 中的規則 ID）、evidence_ids（引用證據 ID）、created_at。可追溯每項 Recommendation / Clinical Decision / Consensus / Evidence / Contraindication 產生的 Treatment Item |
| **依賴** | E-03（與 Engine 深度整合） |
| **預計檔案** | `src/backend/clinical/treatment_plan_engine.py`（與 E-03 同檔案，或 `src/backend/clinical/treatment_plan_trace.py`） |
| **驗收條件** | 每個 Engine 執行產生完整 trace；step_order 連續；可重建引擎決策路徑 |

---

#### E-08：Engine 測試

| 項目 | 內容 |
|------|------|
| **角色** | backend-logic |
| **描述** | 撰寫 Engine 單元測試（9 cases）：valid plan generation（正常流程）、phase ordering（phase_order 正確）、monitoring generation（依 treatment type 產生對應 monitoring）、safety rule generation（contraindication 觸發 safety rule）、alternative generation（有替代方案時正確輸出）、missing consensus（consensus 為空時處理）、contraindication handling（禁忌症情境）、empty evidence（無證據時降級處理）、deterministic output（相同輸入 2 次輸出完全一致） |
| **依賴** | E-03, E-04 |
| **預計檔案** | `tests/backend/clinical/test_treatment_plan_engine.py` |
| **驗收條件** | 全部 9 個 case 通過；deterministic 測試驗證輸出不變 |

---

#### E-09：State Machine 測試

| 項目 | 內容 |
|------|------|
| **角色** | backend-logic |
| **描述** | 撰寫 State Machine 測試：覆蓋全部合法轉換（至少 9 條）與全部非法轉換（例如 draft→approved 直接跳躍、completed→active、cancelled→active 等） |
| **依賴** | E-02 |
| **預計檔案** | `tests/backend/clinical/test_treatment_plan_state_machine.py` |
| **驗收條件** | 所有合法轉換通過；所有非法轉換拋出 IllegalTransitionError |

---

## Batch 2：Service Layer（服務層）

**目標**：建立 TreatmentPlanService — 交易邊界管理者，串接 Engine + Repositories + Outbox，實現完整的事務性 Plan 建立流程與版本管理。

**依賴**：Batch 0 + Batch 1（Engine、Repositories、Model 皆就緒）

**主責角色**：backend-logic

### 任務詳情

---

#### E-05：建立 TreatmentPlanService

| 項目 | 內容 |
|------|------|
| **角色** | backend-logic |
| **描述** | 建立 `TreatmentPlanService` — 交易邊界控制器。職責：①驗證上游 4 ID 一致性（patient_id 跨 Recommendation / Clinical Decision / Consensus / Request 一致 + recommendation_id / clinical_decision_id 鏈路一致），不一致回傳 422；②建立 Clinical Context；③呼叫 TreatmentPlanEngine 產生 Plan；④透過 Repositories 建立 Plan / Phases / Items / Monitoring / Safety Rules / Trace（同一個 Transaction）；⑤透過 ClinicalGraphEventService 建立 Outbox Event（同一個 Transaction）；⑥任一 Persistence 失敗全部 rollback；⑦Graph 後續失敗不得 rollback Treatment Plan（由 Outbox 重試） |
| **依賴** | E-01~E-04（Engine + RuleSet + StateMachine + Trace）、R-01~R-06（Repositories）、M-01~M-06（Models） |
| **預計檔案** | `src/backend/services/treatment_plan_service.py` |
| **驗收條件** | 完整 transaction boundary：Plan 寫入失敗時 rollback 不留髒資料；Outbox 在同一 transaction 寫入；4 ID 不一致拋 422；成功時回傳完整 Plan DTO |

---

#### E-06：實作 Plan Versioning 邏輯

| 項目 | 內容 |
|------|------|
| **角色** | backend-logic |
| **描述** | 實作 Plan 版本化機制：建立新 Plan 時 version=1；修改已 approved/active 的 Plan（revise）時：舊 Plan is_current=False + supersedes_plan_id→新 Plan + revision_reason 記錄原因；新 Plan version+1、previous_plan_id→舊 Plan、is_current=True。完整保留歷史版本（誰修改 / 何時修改 / 修改原因 / 上一版本 / 哪些項目改變）。版本化邏輯內建於 Service 或獨立的 `PlanVersionManager` |
| **依賴** | E-05（Service 主體） |
| **預計檔案** | `src/backend/services/treatment_plan_service.py`（與 E-05 同檔案） |
| **驗收條件** | 初次建立 version=1；revise 後新舊版本鏈正確；get_current_by_patient_id 只回傳 is_current=True 版本；list_versions 回傳完整版本歷史 |

---

#### E-07：實作 Graph Outbox Event

| 項目 | 內容 |
|------|------|
| **角色** | backend-logic |
| **描述** | 在 `src/backend/schemas/clinical_graph_event.py` 新增 GraphAggregateType.TREATMENT_PLAN 與 7 種 GraphEventType（treatment_plan.created / updated / approved / activated / paused / completed / superseded）。在 Service 中相應 lifecycle hook 呼叫 ClinicalGraphEventService.create_event()，Payload 包含：plan_id / version / patient_id / recommendation_id / clinical_decision_id / consensus_id / status / goals / phases（摘要）/ items（摘要）/ monitoring（摘要）/ safety_rules（摘要）/ alternatives。Payload 不得含密碼、Token、完整病歷 |
| **依賴** | E-05（Service 中的 lifecycle hooks） |
| **預計檔案** | `src/backend/schemas/clinical_graph_event.py`（修改）、`src/backend/services/treatment_plan_service.py`（整合呼叫） |
| **驗收條件** | 新 event types 註冊成功；Plan 建立/狀態變更時正確寫入 Outbox；Payload 不含敏感欄位；validate_payload_sensitive_fields 通過 |

---

#### E-10：Service 測試

| 項目 | 內容 |
|------|------|
| **角色** | backend-logic |
| **描述** | 撰寫 Service 整合測試（13 cases）：success（完整流程）、patient mismatch（4 ID 不一致）、recommendation mismatch、decision mismatch、consensus mismatch、created_by（正確記錄建立者）、transaction rollback（Plan 寫入失敗全部回滾）、phase failure（phase 寫入失敗回滾）、item failure、trace failure、outbox failure（Outbox 失敗不影響 Plan）、revision（版本化正確）、approval（狀態轉換正確） |
| **依賴** | E-05, E-06, E-07 |
| **預計檔案** | `tests/backend/services/test_treatment_plan_service.py` |
| **驗收條件** | 全部 13 個 case 通過；transaction rollback 驗證不留髒資料 |

---

## Batch 3：API Layer（API 層）

**目標**：建立 12 個 API Endpoints（5 查詢 + 7 狀態操作）+ Permission 檢查 + API 測試。

**依賴**：Batch 2（Service + StateMachine 就緒）

**主責角色**：api-designer

### 任務詳情

---

#### A-01：POST /api/v1/treatment-plans

| 項目 | 內容 |
|------|------|
| **角色** | api-designer |
| **描述** | 建立 Plan API：接受 JSON body（patient_id / recommendation_id / clinical_decision_id / consensus_id / plan_intent / treatment_goals 等），呼叫 TreatmentPlanService.create_plan()。4 ID 不一致回傳 422；成功回傳 201 + PlanResponse |
| **依賴** | E-05（Service） |
| **預計檔案** | `src/backend/api/v1/treatment_plans.py` |
| **驗收條件** | 201 成功建立；422 ID 不一致；500 異常處理 |

---

#### A-02：GET /api/v1/treatment-plans/{plan_id}

| 項目 | 內容 |
|------|------|
| **角色** | api-designer |
| **描述** | 取得單一 Plan 詳細資料（含 Phases/Items/Monitoring/Safety Rules/Trace/Alternatives） |
| **依賴** | E-05（Service 提供 get_plan） |
| **預計檔案** | `src/backend/api/v1/treatment_plans.py` |
| **驗收條件** | 200 回傳完整資料；404 不存在的 plan_id；403 無權限 |

---

#### A-03：GET /api/v1/treatment-plans

| 項目 | 內容 |
|------|------|
| **角色** | api-designer |
| **描述** | List Plans 支援分頁：`?patient_id=&skip=&limit=`。依 patient_id 篩選，回傳列表 + 總數 |
| **依賴** | R-01（Repository 的 list_by_patient_id / count_by_patient_id） |
| **預計檔案** | `src/backend/api/v1/treatment_plans.py` |
| **驗收條件** | 正確分頁；skip/limit 邊界處理；無結果回傳空列表 |

---

#### A-04：GET /api/v1/treatment-plans/{plan_id}/versions

| 項目 | 內容 |
|------|------|
| **角色** | api-designer |
| **描述** | 取得指定 plan_id 的所有版本歷史 |
| **依賴** | R-01（list_versions） |
| **預計檔案** | `src/backend/api/v1/treatment_plans.py` |
| **驗收條件** | 回傳版本列表（依 version desc）；無版本時回傳空列表 |

---

#### A-05：GET /api/v1/treatment-plans/{plan_id}/trace

| 項目 | 內容 |
|------|------|
| **角色** | api-designer |
| **描述** | 取得 Plan 的計算追蹤記錄（10 步驟 trace） |
| **依賴** | R-06（TraceRepository） |
| **預計檔案** | `src/backend/api/v1/treatment_plans.py` |
| **驗收條件** | 回傳 trace steps（依 step_order 排序） |

---

#### A-06：POST /api/v1/treatment-plans/{plan_id}/submit

| 項目 | 內容 |
|------|------|
| **角色** | api-designer |
| **描述** | Submit Plan：draft → proposed。呼叫 StateMachine.transition(plan, "submit")。非法轉換回傳 409 |
| **依賴** | E-02（StateMachine）、E-05（Service 封裝） |
| **預計檔案** | `src/backend/api/v1/treatment_plans.py` |
| **驗收條件** | 200 成功；409 非法轉換 |

---

#### A-07：POST /api/v1/treatment-plans/{plan_id}/approve

| 項目 | 內容 |
|------|------|
| **角色** | api-designer |
| **描述** | Approve Plan：under_review → approved。限 Approver/Admin 角色 |
| **依賴** | E-02, E-05, A-13（Permission） |
| **預計檔案** | `src/backend/api/v1/treatment_plans.py` |
| **驗收條件** | 200 成功（含 approved_by / approved_at 記錄）；403 權限不足；409 非法轉換 |

---

#### A-08：POST /api/v1/treatment-plans/{plan_id}/activate

| 項目 | 內容 |
|------|------|
| **角色** | api-designer |
| **描述** | Activate Plan：approved → active。限 Clinician/Approver 角色 |
| **依賴** | E-02, E-05, A-13 |
| **預計檔案** | `src/backend/api/v1/treatment_plans.py` |
| **驗收條件** | 200 成功（含 activated_at）；403/409 錯誤處理 |

---

#### A-09：POST /api/v1/treatment-plans/{plan_id}/pause

| 項目 | 內容 |
|------|------|
| **角色** | api-designer |
| **描述** | Pause Plan：active → paused。限 Clinician/Approver 角色 |
| **依賴** | E-02, E-05, A-13 |
| **預計檔案** | `src/backend/api/v1/treatment_plans.py` |
| **驗收條件** | 200 成功（含 paused_at）；403/409 錯誤處理 |

---

#### A-10：POST /api/v1/treatment-plans/{plan_id}/complete

| 項目 | 內容 |
|------|------|
| **角色** | api-designer |
| **描述** | Complete Plan：active → completed。限 Clinician/Approver 角色 |
| **依賴** | E-02, E-05, A-13 |
| **預計檔案** | `src/backend/api/v1/treatment_plans.py` |
| **驗收條件** | 200 成功（含 completed_at）；403/409 錯誤處理 |

---

#### A-11：POST /api/v1/treatment-plans/{plan_id}/cancel

| 項目 | 內容 |
|------|------|
| **角色** | api-designer |
| **描述** | Cancel Plan：任意非 completed 狀態 → cancelled。非法轉換回傳 409 |
| **依賴** | E-02, E-05 |
| **預計檔案** | `src/backend/api/v1/treatment_plans.py` |
| **驗收條件** | 200 成功（含 cancelled_at）；409 已 completed 不可 cancel |

---

#### A-12：POST /api/v1/treatment-plans/{plan_id}/revise

| 項目 | 內容 |
|------|------|
| **角色** | api-designer |
| **描述** | Revise Plan：approved/active → superseded + 建立新版本（version+1）。呼叫 Service.revise_plan()。新 Plan 回傳 201 |
| **依賴** | E-05, E-06（Versioning） |
| **預計檔案** | `src/backend/api/v1/treatment_plans.py` |
| **驗收條件** | 舊 Plan is_current=False + superseded；新 Plan 建立成功；版本鏈完整 |

---

#### A-13：Permission 檢查

| 項目 | 內容 |
|------|------|
| **角色** | api-designer |
| **描述** | 實作權限矩陣（沿用既有 Auth/Role 架構，不另建第二套）：Viewer（唯讀 GET）、Researcher（可 POST draft/proposed）、Clinician（可建立、submit、修改 draft）、Tumor Board Member（可 review/approve 流程中的 under_review→approved？實際 approve 限 Approver/Admin）、Approver/Admin（可 approve）、Clinician+Approver（可 activate/pause/complete）。使用既有 `require_auth` / `require_role` decorator。Permission 失敗回傳 403 |
| **依賴** | A-01~A-12（API endpoints 需加上 permission check） |
| **預計檔案** | `src/backend/api/v1/treatment_plans.py`（permission decorator 整合） |
| **驗收條件** | 每支 API 有對應 permission 檢查；非法角色操作回傳 403；Permission 檢查在 State Machine 之前執行 |

---

#### A-14：API 測試

| 項目 | 內容 |
|------|------|
| **角色** | api-designer |
| **描述** | 撰寫 API 整合測試（20 cases）：POST（成功/422）、GET（200/404）、List（分頁）、Versions（版本歷史）、Trace（計算追蹤）、Submit（200/409）、Approve（200/403/409）、Activate、Pause、Complete、Cancel、Revise、401（未認證）、403（權限不足）、404（不存在）、409（非法狀態轉換）、422（ID不一致）、500 generic error handling |
| **依賴** | A-01~A-13 |
| **預計檔案** | `tests/backend/api/test_treatment_plan_api.py` |
| **驗收條件** | 全部 20 個 case 通過；HTTP status code 正確；error message 格式一致 |

---

## Batch 4：Frontend & Report（前端與報告）

**目標**：建立 4 個前端頁面 + 路由 + Consensus 頁面整合 + HTML Report 擴充 + 前端測試。

**依賴**：Batch 3（API 就緒）

**主責角色**：frontend-logic

### 任務詳情

---

#### F-01：建立 TreatmentPlanListPage

| 項目 | 內容 |
|------|------|
| **角色** | frontend-logic |
| **描述** | 建立 `TreatmentPlanListPage` — 列出 Plans（分頁列表、狀態篩選、每筆顯示 Status / Version / Goals摘要 / Created Date）。點選 row 導航至 Detail 頁面。空狀態顯示「尚無治療計畫」 |
| **依賴** | A-03（GET /api/v1/treatment-plans） |
| **預計檔案** | `src/frontend/src/pages/TreatmentPlanListPage.tsx` |
| **驗收條件** | 分頁正常；狀態篩選正確；空狀態顯示；Loading spinner 或 Skeleton |

---

#### F-02：建立 TreatmentPlanCreatePage

| 項目 | 內容 |
|------|------|
| **角色** | frontend-logic |
| **描述** | 建立 `TreatmentPlanCreatePage` — 選擇 Consensus（從 Tumor Board Consensus 列表挑選），填寫 plan_intent / treatment_goals 等必要欄位，點擊「建立 Plan」→ POST → 取得 plan_id → navigate("/treatment-plans/{plan_id}")。**不得使用 fake/hardcoded 資料** |
| **依賴** | A-01（POST API） |
| **預計檔案** | `src/frontend/src/pages/TreatmentPlanCreatePage.tsx` |
| **驗收條件** | 選擇 Consensus 流程正確；POST 成功後跳轉；表單驗證（必填欄位）；錯誤訊息顯示 |

---

#### F-03：建立 TreatmentPlanDetailPage

| 項目 | 內容 |
|------|------|
| **角色** | frontend-logic |
| **描述** | 建立 `TreatmentPlanDetailPage` — 顯示完整 Plan 詳情：Status（含 badge）、Version、Goals、Summary、Phases（accordion 展開各 phase 的 items）、Items（表格）、Monitoring Schedule、Safety Rules（高亮 requires_review=True 的項目）、Alternatives（列表）、Review Date、Trace（時間軸或步驟列表）、Knowledge Graph Link（連至 ClinicalGraphPage 的查詢路徑）。支援狀態操作按鈕（Submit / Approve / Activate / Pause / Complete / Cancel / Revise），依權限顯示 |
| **依賴** | A-02（GET detail）、A-06~A-12（狀態 API） |
| **預計檔案** | `src/frontend/src/pages/TreatmentPlanDetailPage.tsx` |
| **驗收條件** | 所有區塊正確顯示；狀態按鈕依 status 顯示/隱藏；操作後即時更新狀態 |

---

#### F-04：建立 TreatmentPlanRevisionPage

| 項目 | 內容 |
|------|------|
| **角色** | frontend-logic |
| **描述** | 建立 `TreatmentPlanRevisionPage` — 基於當前 Plan 建立新版本（revise）。載入原 Plan 資料為預設值，允許修改 treatment_goals / summary 等欄位。提交時呼叫 POST revise API，成功後 navigate 到新版本 Detail 頁 |
| **依賴** | A-12（Revise API） |
| **預計檔案** | `src/frontend/src/pages/TreatmentPlanRevisionPage.tsx` |
| **驗收條件** | 預設載入原 Plan 資料；修改後正確呼叫 revise；跳轉至新版本 |

---

#### F-05：路由設定

| 項目 | 內容 |
|------|------|
| **角色** | frontend-logic |
| **描述** | 在 Router 中加入 4 條新路由：`/treatment-plans`（ListPage）、`/treatment-plans/new`（CreatePage）、`/treatment-plans/:id`（DetailPage）、`/treatment-plans/:id/revise`（RevisionPage）。加入 Sidebar/Navigation 選單 |
| **依賴** | F-01~F-04（頁面建立完成） |
| **預計檔案** | `src/frontend/src/App.tsx` 或 Router 設定檔 |
| **驗收條件** | 4 條路由正確註冊；導航正常；404 無匹配路由時顯示缺省頁 |

---

#### F-06：TumorBoardConsensusPage 加入「Create Treatment Plan」按鈕

| 項目 | 內容 |
|------|------|
| **角色** | frontend-logic |
| **描述** | 在 `TumorBoardConsensusPage` 的已批准 Consensus 卡片/明細中加入「Create Treatment Plan」按鈕。流程：點擊 → navigates to `/treatment-plans/new?consensus_id=xxx`（CreatePage 預選該 Consensus） |
| **依賴** | F-02（CreatePage 就緒） |
| **預計檔案** | `src/frontend/src/pages/TumorBoardConsensusPage.tsx`（修改） |
| **驗收條件** | 僅 approved/active consensus 顯示按鈕；點擊後正確帶入 consensus_id |

---

#### F-07：HTML Report 加入 Treatment Plan Section

| 項目 | 內容 |
|------|------|
| **角色** | frontend-logic |
| **描述** | 在既有 Report Generator（`src/backend/clinical/report_generator.py`）中新增 Treatment Plan Section。至少顯示：Plan Status、Version、Treatment Goals、Treatment Phases（表格）、Treatment Items（依 phase 分組）、Monitoring Schedule（時間表樣式）、Safety Rules（警示樣式）、Alternatives、Review Date、Approval Information（approved_by / approved_at）。**不得重寫整個 Report Generator** |
| **依賴** | A-02（獲取 Plan 完整資料） |
| **預計檔案** | `src/backend/clinical/report_generator.py`（修改） |
| **驗收條件** | Report 包含 Treatment Plan 區塊；樣式與既有報告一致；無 Plan 時該區塊隱藏 |

---

#### F-08：Frontend 測試

| 項目 | 內容 |
|------|------|
| **角色** | frontend-logic |
| **描述** | 撰寫前端測試：routes（4 條路由渲染正確頁面）、create（表單驗證 + POST 流程）、detail（所有區塊渲染 + 狀態按鈕）、state actions（每個狀態操作按鈕觸發正確 API）、revision（載入 + 修改 + 跳轉）、empty state（無資料時顯示缺省提示）、error state（API 錯誤顯示錯誤訊息）、permissions（按鈕依角色顯示/隱藏） |
| **依賴** | F-01~F-07 |
| **預計檔案** | `src/frontend/src/__tests__/TreatmentPlanPages.test.tsx` |
| **驗收條件** | 全部測試通過；使用 React Testing Library；模擬 API 呼叫 |

---

## Batch 5：KnowGraphGo Graph Projection（圖形投影）

**目標**：在 KnowGraphGo 既有 Clinical Adapter 中加入 Treatment Plan 相關 Entity + Relation，實現 Deterministic ID / Idempotent Replay / Relation Provenance / Stub Preservation。

**依賴**：Batch 2（Outbox Event Schema 確定）

**主責角色**：knowgraphgo-dev

**注意**：此 Batch 操作 KnowGraphGo 倉庫，完成後先推 KnowGraphGo commit，取得 SHA 後回 CI 固定。

### 任務詳情

---

#### K-01：建立 TreatmentPlan Entity

| 項目 | 內容 |
|------|------|
| **角色** | knowgraphgo-dev |
| **描述** | 在 KnowGraphGo Clinical Adapter 中建立 `TreatmentPlan` Entity。欄位：plan_id / version / patient_id / recommendation_id / clinical_decision_id / consensus_id / status / goals / summary / alternatives（JSON）。使用 Canonical Schema + Deterministic ID（基於 plan_id + version 計算） |
| **依賴** | 無（KnowGraphGo 既有 Adapter 架構） |
| **預計檔案** | KnowGraphGo repo: `entities/treatment_plan.go`（路徑依實際專案結構） |
| **驗收條件** | Entity 註冊成功；Deterministic ID 計算正確 |

---

#### K-02：建立 TreatmentPhase Entity

| 項目 | 內容 |
|------|------|
| **角色** | knowgraphgo-dev |
| **描述** | 建立 `TreatmentPhase` Entity。欄位：phase_id / plan_id / phase_order / phase_type / name / status。Deterministic ID |
| **依賴** | K-01 |
| **預計檔案** | KnowGraphGo repo: `entities/treatment_phase.go` |
| **驗收條件** | Entity 註冊成功；ID 確定性驗證 |

---

#### K-03：建立 TreatmentItem Entity

| 項目 | 內容 |
|------|------|
| **角色** | knowgraphgo-dev |
| **描述** | 建立 `TreatmentItem` Entity。欄位：item_id / plan_id / phase_id / item_order / item_type / name / status。Deterministic ID |
| **依賴** | K-01, K-02 |
| **預計檔案** | KnowGraphGo repo: `entities/treatment_item.go` |
| **驗收條件** | 同 K-02 |

---

#### K-04：建立 Monitoring Entity

| 項目 | 內容 |
|------|------|
| **角色** | knowgraphgo-dev |
| **描述** | 建立 `Monitoring` Entity。欄位：monitoring_id / plan_id / monitoring_type / name / schedule。Deterministic ID |
| **依賴** | K-01 |
| **預計檔案** | KnowGraphGo repo: `entities/monitoring.go` |
| **驗收條件** | 同 K-02 |

---

#### K-05：建立 SafetyRule Entity

| 項目 | 內容 |
|------|------|
| **角色** | knowgraphgo-dev |
| **描述** | 建立 `SafetyRule` Entity。欄位：rule_id / plan_id / rule_type / condition / severity。Deterministic ID |
| **依賴** | K-01 |
| **預計檔案** | KnowGraphGo repo: `entities/safety_rule.go` |
| **驗收條件** | 同 K-02 |

---

#### K-06：建立 11 種 Relation

| 項目 | 內容 |
|------|------|
| **角色** | knowgraphgo-dev |
| **描述** | 建立 11 種 Relation：① TreatmentPlan ─FOR_PATIENT→ Patient、② ─BASED_ON→ TumorBoardConsensus、③ ─DERIVED_FROM→ ClinicalDecision、④ ─HAS_PHASE→ TreatmentPhase、⑤ TreatmentPhase ─HAS_ITEM→ TreatmentItem、⑥ TreatmentItem ─SUPPORTED_BY→ Evidence、⑦ ─USES_DRUG→ Drug、⑧ TreatmentPlan ─HAS_MONITORING→ Monitoring、⑨ ─HAS_SAFETY_RULE→ SafetyRule、⑩ ─SUPERSEDES→ TreatmentPlan（自參照）。每條 Relation 含 Provenance 資訊 |
| **依賴** | K-01~K-05（所有 Entity 就緒） |
| **預計檔案** | KnowGraphGo repo: `relations/treatment_plan_relations.go` |
| **驗收條件** | 11 條 relation 全部定義；relation 方向正確；provenance 欄位填寫 |

---

#### K-07：Idempotent Replay + Stub Preservation

| 項目 | 內容 |
|------|------|
| **角色** | knowgraphgo-dev |
| **描述** | 實作：Deterministic ID（確保同一資料多次 replay 產生相同 entity ID）、Idempotent Replay（重複 apply 不新增重複節點/邊）、Relation Provenance（每條 relation 記錄來源 event_id）、Stub Preservation（當目標 entity 尚未建立時先建立 stub，避免 graph 不一致）、Canonical Schema（Entity 結構符合同一規範） |
| **依賴** | K-06 |
| **預計檔案** | KnowGraphGo repo（功能整合於 adapter / worker） |
| **驗收條件** | 重複 apply 不增加 entity 數量；stub 在目標 entity 建立後自動解析；provenance 可追溯至 outbox event |

---

#### K-08：Graph Integration 測試

| 項目 | 內容 |
|------|------|
| **角色** | knowgraphgo-dev |
| **描述** | 撰寫完整 Graph Integration 測試：Treatment Plan Outbox → KnowGraphGo CLI apply → SQLite Graph Database → Query Treatment Plan Path（Patient→...→TreatmentPlan→Phase→Item）→ Replay Count 不增加。驗證 Digital Thread 完整可追溯 |
| **依賴** | K-01~K-07 |
| **預計檔案** | KnowGraphGo repo: `tests/treatment_plan_graph_test.go` |
| **驗收條件** | Outbox→Graph 流程完整；Digital Thread 路徑正確；Idempotent replay 驗證通過 |

---

## Batch 6：Integration Tests + CI（集成測試與 CI 更新）

**目標**：撰寫完整的集成測試套件（Restart Recovery、Digital Thread、Frontend）並更新 CI 配置（清理舊步驟、加入 Postgres CI Gate、固定 KnowGraphGo SHA）。

**依賴**：Batch 0~5 全部完成

**主責角色**：test-writer, devops

### 任務詳情

---

#### T-01：Engine 正式測試套件

| 項目 | 內容 |
|------|------|
| **角色** | test-writer |
| **描述** | 撰寫完整的 Engine 測試套件（9 cases），覆蓋 E-08 已涵蓋範圍並補充邊界情境。可能與 E-08 合併或以更全面的方式重新組織。9 cases：valid plan generation / phase ordering / monitoring generation / safety rule generation / alternative generation / missing consensus / contraindication handling / empty evidence / deterministic output |
| **依賴** | E-03（Engine） |
| **預計檔案** | `tests/backend/clinical/test_treatment_plan_engine.py`（與 E-08 合併或獨立） |
| **驗收條件** | 全部 9 個 case 通過 |

---

#### T-02：State Machine 正式測試套件

| 項目 | 內容 |
|------|------|
| **角色** | test-writer |
| **描述** | 撰寫完整的 State Machine 測試套件，覆蓋全部合法與非法轉換。可能與 E-09 合併 |
| **依賴** | E-02 |
| **預計檔案** | `tests/backend/clinical/test_treatment_plan_state_machine.py`（與 E-09 合併） |
| **驗收條件** | 所有轉換測試通過 |

---

#### T-03：Model 正式測試套件

| 項目 | 內容 |
|------|------|
| **角色** | test-writer |
| **描述** | 完整的 Model 測試套件（relations / versioning / unique constraints / cascade / JSON round-trip）。可能與 M-08 合併 |
| **依賴** | M-01~M-06 |
| **預計檔案** | `tests/backend/models/test_treatment_plan_models.py`（與 M-08 合併） |
| **驗收條件** | 全部通過 |

---

#### T-04：Repository 正式測試套件

| 項目 | 內容 |
|------|------|
| **角色** | test-writer |
| **描述** | 完整的 Repository 測試（create / get / list / pagination / versions / current plan / mark superseded）。可能與 R-07 合併 |
| **依賴** | R-01~R-06 |
| **預計檔案** | `tests/backend/repositories/test_treatment_plan_repos.py`（與 R-07 合併） |
| **驗收條件** | 全部通過 |

---

#### T-05：Service 正式測試套件

| 項目 | 內容 |
|------|------|
| **角色** | test-writer |
| **描述** | 完整的 Service 測試（13 cases）。可能與 E-10 合併 |
| **依賴** | E-05 |
| **預計檔案** | `tests/backend/services/test_treatment_plan_service.py`（與 E-10 合併） |
| **驗收條件** | 全部通過 |

---

#### T-06：API 正式測試套件

| 項目 | 內容 |
|------|------|
| **角色** | test-writer |
| **描述** | 完整的 API 測試（20 cases）。可能與 A-14 合併 |
| **依賴** | A-01~A-13 |
| **預計檔案** | `tests/backend/api/test_treatment_plan_api.py`（與 A-14 合併） |
| **驗收條件** | 全部通過 |

---

#### T-07：Restart Recovery 測試

| 項目 | 內容 |
|------|------|
| **角色** | test-writer |
| **描述** | 撰寫 Restart Recovery 測試：App 1 建立 Treatment Plan（含 Phases/Items/Monitoring/Safety/Trace）→ 模擬 Shutdown（session 關閉）→ App 2 使用新 session GET Plan／Phases／Items／Trace → 確認資料完整讀回。驗證 Postgres 持久化正確性 |
| **依賴** | Batch 0~3 全部完成（需完整 CRUD 流程） |
| **預計檔案** | `tests/backend/integration/test_treatment_plan_restart.py` |
| **驗收條件** | Shutdown 前後資料一致；所有關聯子表正確讀回 |

---

#### T-08：Digital Thread 測試

| 項目 | 內容 |
|------|------|
| **角色** | test-writer |
| **描述** | 撰寫 Digital Thread 測試：Patient → Recommendation → Clinical Decision → Tumor Board Consensus → Treatment Plan → Phase → Item，完整鏈路可從 Patient 一路追溯到 Item。驗證每個環節的 ID 鏈路一致 |
| **依賴** | Batch 0~5 全部完成（需完整鏈路） |
| **預計檔案** | `tests/backend/integration/test_treatment_plan_digital_thread.py` |
| **驗收條件** | 完整鏈路可追溯；每個 hop 的 ID 一致 |

---

#### T-09：Frontend 整合測試

| 項目 | 內容 |
|------|------|
| **角色** | test-writer |
| **描述** | 撰寫 Frontend 整合測試（可能與 F-08 合併）：routes / create / detail / state actions / revision / empty state / error state / permissions |
| **依賴** | F-01~F-07 |
| **預計檔案** | `src/frontend/src/__tests__/TreatmentPlanPages.test.tsx`（與 F-08 合併） |
| **驗收條件** | 全部通過 |

---

#### C-01：CI Cleanup

| 項目 | 內容 |
|------|------|
| **角色** | devops |
| **描述** | 清理 Phase 3D 中已被正式 CI-01~CI-05 取代的重複舊步驟：重複 checkout KnowGraphGo（保留一個）、舊 Python-only parity block（已由正式測試取代）、`go run -exec '' || true` 容錯模式（已由正式 gate 取代）、已被正式 E2E 取代的重複測試步驟。**最小清理原則，不修改現有正式 Gate 標準** |
| **依賴** | 無（可並行執行） |
| **預計檔案** | `.github/workflows/ci.yml` |
| **驗收條件** | CI 配置簡潔；既有 gate 不受影響；清理後 CI 仍全綠 |

---

#### C-02：Postgres CI Gate

| 項目 | 內容 |
|------|------|
| **角色** | devops |
| **描述** | 在 CI 中加入 Postgres CI Gate，真正執行（不得 continue-on-error / skip / xfail / SQLite 冒充）：Migration 023 upgrade、Treatment Plan transaction tests、Restart recovery、Versioning tests、State transition tests、Outbox transaction、Graph projection E2E、Empty downgrade、Re-upgrade。確認 CI 使用真實 Postgres 服務 |
| **依賴** | Batch 0~6 全部測試通過 |
| **預計檔案** | `.github/workflows/ci.yml` |
| **驗收條件** | CI 中 Postgres job 全部綠色；migration upgrade/downgrade/re-upgrade 驗證 |

---

#### C-03：KnowGraphGo CI pin

| 項目 | 內容 |
|------|------|
| **角色** | devops |
| **描述** | Batch 5 完成後取得 KnowGraphGo commit SHA，在 CI 中固定 checkout 該 pinned SHA 而非 main/HEAD，確保 CI 可重複 |
| **依賴** | K-01~K-08（KnowGraphGo 修改完成） |
| **預計檔案** | `.github/workflows/ci.yml`（更新 checkout ref） |
| **驗收條件** | CI checkout 指定 SHA；SHA 存在於 KnowGraphGo remote |

---

## Batch 7：Review & Finalize（評審與提交）

**目標**：Reviewer 全面驗收、必要修復、Git Commit & Push。確保 Reviewer 評分 ≥ 95。

**依賴**：Batch 0~6 全部完成且測試通過

**主責角色**：REVIEWER, PLANNER

### 任務詳情

---

#### R-Review：Reviewer 全面驗收

| 項目 | 內容 |
|------|------|
| **角色** | REVIEWER |
| **描述** | 依據 Requirements §三十 Reviewer Gate 逐項檢查：上游 4 ID 關聯一致、Plan versioning 正確、Approved Plan 不原地覆蓋、State Machine 阻止非法轉換、Plan＋Phases＋Items＋Monitoring＋Safety 同 Transaction、Outbox 同 Transaction、Restart 後完整讀回、Graph Digital Thread 完整、Idempotent Graph Replay、Auth/Role 正確、Postgres CI 全綠。任一 FAIL / PARTIAL / 未驗證 → 最高 89 分 → 返工 |
| **依賴** | Batch 0~6 全部完成 |
| **預計檔案** | 無（檢查所有交付物） |
| **驗收條件** | Reviewer 評分 ≥ 95 |

---

#### R-Fix：返工修正

| 項目 | 內容 |
|------|------|
| **角色** | PLANNER + 相關角色 |
| **描述** | 若 Reviewer 評分 < 95 或發現 FAIL/PARTIAL，PLANNER 啟動返工循環。相關角色進行修正，修正後重新提交 Reviewer 評分。最多 5 輪返工 |
| **依賴** | Reviewer 反饋 |
| **預計檔案** | 依修正範圍而定 |
| **驗收條件** | Reviewer 確認問題已解決；評分 ≥ 95 |

---

#### R-Commit：Git Commit & Push

| 項目 | 內容 |
|------|------|
| **角色** | PLANNER |
| **描述** | 主要 Commit：`feat(phase3e): add treatment plan engine`。若 KnowGraphGo 有修改：先推 KnowGraphGo（`feat(clinical): add treatment plan graph projection`），取得 SHA，更新 CI pin，再推 AI-Kill-Cancer。允許追加聚焦修復 Commit。禁止 force push / rebase / 修改舊 Migration / 開始下一階段 |
| **依賴** | Reviewer ≥ 95 |
| **預計檔案** | 全部 |
| **驗收條件** | 兩個倉庫成功推送；CI 觸發；無 force push |

---

## 返工預案（Rework Scenarios）

| # | 失敗情境 | 觸發條件 | 處理方式 | 涉及 Batch |
|---|---------|---------|---------|-----------|
| 1 | **Migration 023 upgrade 失敗** | `alembic upgrade head` 在 CI 或本地失敗 | 檢查 Model 欄位型別（JSON / UUID / Enum）、FK 參照表名、Index 命名是否與既有 Migration 相容；修正後執行 downgrade（空資料）+ re-upgrade 驗證。若已有正式資料則撰寫資料遷移步驟 | Batch 0 |
| 2 | **Engine 輸出不確定性** | 相同輸入 2 次執行產生不同 Plan 輸出 | 檢查 Engine 中是否有 `random`、`datetime.utcnow()`、外部 API 呼叫、session 依賴等非確定性來源。改為注入所有時間/隨機依賴。在測試中增加 `deterministic_output` case 鎖定 seed | Batch 1 |
| 3 | **Service Transaction 資料不一致** | Plan 寫入成功但 Phase/Item/Monitoring 遺失，或 Outbox 未寫入 | 確認 Repositories 均未自行 `commit()`（僅 `db.add`）。Service 層使用 `async with db.begin()` 或手動 `commit()` 一次涵蓋所有寫入。測試中驗證：任一子表寫入失敗 → 全部 rollback（檢查資料庫無對應 plan 記錄） | Batch 2 |
| 4 | **Restart Recovery 部分遺失** | App 重啟後查詢 Plan 取得成功但 Phase/Items/Trace 為空 | 檢查 Model 中 `relationship` 的 `cascade="all, delete-orphan"` 設定是否正確。確認 Repository `get_by_plan_id` 使用 `selectinload` 或 `joinedload` 載入關聯。驗證 FK 正確指向且 cascade 寫入 | Batch 0, 2 |
| 5 | **Graph Deterministic ID 碰撞** | 多次 replay 產生不同 Graph Entity ID 或重複節點 | 檢查 ID 計算邏輯是否納入所有必要欄位（plan_id + version + entity type）。確保 upsert 邏輯使用 `ON CONFLICT` 而非先刪後插。測試 idempotent replay：同一 outbox apply 2 次，entity count 不變 | Batch 5 |
| 6 | **API Permission 繞過** | 低權限角色（Viewer）可執行狀態操作（approve/activate） | 逐一比對 Requirements §二十四 權限矩陣。確認每個 API endpoint 的 `Depends(require_role)` 裝飾器正確設置。測試中增加 403 case 覆蓋每種權限邊界 | Batch 3 |
| 7 | **Postgres CI Gate 紅燈** | CI 中 migration 或 transaction 測試在真實 Postgres 上失敗 | 檢查 SQL dialect 相容性（避免 SQLite-only 語法如 `JSON` 類型差異）。確認 CI 服務名稱 / 環境變數（POSTGRES_HOST/USER/PASSWORD/DB）正確。Migration 中使用 `sa.Text()` 替代 `sa.JSON()` 若 driver 不支援。確認 downgrade 在空資料時可執行 | Batch 6 |
| 8 | **Frontend API 接續失敗** | 前端呼叫狀態 API 後 UI 未即時更新 | 檢查前端在狀態操作成功後是否重新 fetch GET detail API。使用 React Query 或 `useEffect` 依賴 `plan_id` 自動重取。確認 error handling 顯示 Toast/Snackbar 提示 | Batch 4 |
| 9 | **Reviewer 評分 < 95** | Reviewer 發現未完成需求、有錯誤、缺少測試 | PLANNER 啟動返工循環：列出所有 FAIL/PARTIAL 項目 → 指派對應角色修正 → 修正完成後重新 CI → REVIEWER 重新評分。最多 5 輪。若 5 輪仍 < 95，升級至專案負責人 | Batch 7 |
| 10 | **KnowGraphGo CI pin SHA 不存在** | CI checkout pinned SHA 時 remote 無此 commit | 確認 KnowGraphGo push 成功且 remote 已更新。若需更新 pinned SHA，重新 push KnowGraphGo 取得新 SHA → 更新 AI-Kill-Cancer CI 配置中的 ref | Batch 5, 6 |

---

## 依賴圖摘要

```
Batch 0 Foundation
  └─ M-01~M-06 (Model) → M-07 (Migration) → M-08 (Test)
  └─ R-01~R-06 (Repo) → R-07 (Test)
        │
        ▼
Batch 1 Engine Core
  └─ E-01 (RuleSet) + E-02 (StateMachine) → E-03 (Engine) → E-04 (Trace)
  └─ E-08 (Engine Test) + E-09 (SM Test)
        │
        ▼
Batch 2 Service Layer
  └─ E-05 (Service) → E-06 (Versioning) → E-07 (Outbox)
  └─ E-10 (Service Test)
        │
        ▼
Batch 3 API Layer
  └─ A-01~A-05 (Query APIs) + A-06~A-12 (State APIs) + A-13 (Permission)
  └─ A-14 (API Test)
        │
        ├──────────────────┐
        ▼                  ▼
Batch 4 Frontend      Batch 5 KnowGraphGo
  └─ F-01~F-07          └─ K-01~K-07 (Entity+Relation)
  └─ F-08 (Test)         └─ K-08 (Integration Test)
        │                  │
        └──────┬───────────┘
               ▼
        Batch 6 Integration + CI
          └─ T-01~T-09 (Tests)
          └─ C-01~C-03 (CI)
               │
               ▼
        Batch 7 Review & Finalize
          └─ Reviewer → Fix → Commit → Push
```

---

## 備註

1. **角色切換**：每批次完成後，PLANNER 應確認該批次所有任務的驗收條件已滿足，再啟動下一批次。
2. **批次獨立性**：每個 Batch 的交付物應可在對應環境（如 staging branch）獨立驗證。
3. **測試策略**：單元測試由開發角色在批次內完成（E-08/E-09/E-10/M-08/R-07/A-14/F-08/K-08）；集成測試（T-07/T-08）與 CI 配置在 Batch 6 統一處理，避免重複工作。
4. **KnowGraphGo 優先級**：Batch 5 需與 Batch 4 並行開發，因 KnowGraphGo 為獨立倉庫，不阻塞其他批次。
5. **CI Cleanup 可提前**：C-01（CI Cleanup）無依賴，可在 Batch 0 啟動同時提前執行。
6. **所有檔案路徑為預估**，實際實現時應遵循專案既有命名慣例與目錄結構。
