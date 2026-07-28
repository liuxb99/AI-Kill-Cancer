# REVIEWER 評分報告 — Phase 3E Treatment Plan Engine V1（返工第1次）

## 評分檢查清單

- **是否可執行**：YES（核心功能模組可以獨立運行，Engine / Model / Repository 測試通過）
- **是否有錯誤**：NO（有錯誤 — 詳見下方說明）
- **是否滿足需求條列**：NO（§七 State Machine 未完全實現需求規範）
- **是否有測試**：YES（測試檔案存在，但部分因語法錯誤無法運行）

### 錯誤說明

| 編號 | 錯誤類型 | 嚴重度 | 詳細說明 |
|------|---------|--------|---------|
| E-1 | **Python 3.11 語法錯誤** | **HIGH** | `src/backend/clinical/report_generator.py` 第 1738 行 `f"Monitoring #{i+1}"` 在 f-string 表達式中使用了反斜杠，Python 3.11 不支援（CI 使用 Python 3.11）。導致導入此模組時觸發 `SyntaxError`，進而使 Service 測試和 API 測試完全無法運行。 |
| E-2 | **State Machine 轉換缺失** | **MEDIUM** | `TreatmentPlanStateMachine.TRANSITIONS` 中 `ACTIVE → CANCELLED` 不存在。需求 §七 明確要求「任意非 completed → cancelled」，但當前實作中 active 狀態無法直接取消（需先 pause 才能 cancel）。 |

---

## 細項評分

| 項目 | 分數 | 最高分 | 說明 |
|------|------|--------|------|
| **完整性** | 9 | 25 | 滿足需求=NO，最高 10 分。絕大多數需求（§一～§六、§八～§廿九）已完整實現，返工 4 項問題已修復。但 §七 State Machine 中 `ACTIVE→CANCELLED` 轉換缺失，導致需求未完全滿足。 |
| **正確性** | 7 | 25 | 有錯誤=NO，最高 10 分。Python 3.11 語法錯誤（E-1）會導致 CI 中的 Service / API 測試完全失敗。State Machine 轉換缺口（E-2）是正確性問題。 |
| **可維護性** | 20 | 25 | 程式碼結構清晰，遵循既有 Pattern（Repository / Service / API），使用 Registry Pattern（RuleRegistry）集中管理規則，有完善 docstring 和 type hints。無強制約束。 |
| **測試與驗證** | 15 | 25 | 有測試=YES。Engine 測試（73 ✅）、Model 測試（28 ✅）、Repository 測試（50 ✅）全部通過，共 151 個測試通過。但 Service 測試和 API 測試因 Python 3.11 語法錯誤（E-1）完全無法運行。 |

## 總分：**51 / 100** （不合格）

---

## Reviewer Gate 檢查結果

| 項次 | 檢查項目 | 結果 | 說明 |
|------|---------|------|------|
| 1 | 上游四個 ID 關聯一致 | ✅ **PASS** | `_validate_links()` 驗證 patient_id、recommendation_id、clinical_decision_id、consensus_id 的完整鏈路一致性，任一不一致回傳 422。 |
| 2 | Plan versioning 正確 | ✅ **PASS** | TreatmentPlanModel 包含 version / previous_plan_id / supersedes_plan_id / is_current / revision_reason。`revise_plan()` 建立新版本並標記舊版為 superseded。 |
| 3 | Approved Plan 不原地覆蓋 | ✅ **PASS** | `revise_plan()` 建立新版本（version+1），舊版僅標記 superseded，內容不被修改。 |
| 4 | State Machine 阻止非法轉換 | ⚠️ **PARTIAL** | 多數非法轉換被正確阻擋（回傳 409）。但 `ACTIVE→CANCELLED` 不在 TRANSITIONS 表中，與需求 §七「任意非 completed → cancelled」不符。 |
| 5 | Plan／Phases／Items／Monitoring／Safety 同 Transaction | ✅ **PASS** | `_persist_plan()` 在同一 session 中建立所有子模型，統一 commit 或 rollback。 |
| 6 | Outbox 同 Transaction | ✅ **PASS** | `create_plan()` 中 plan persist + outbox event 在同一個 try block 後 commit。 |
| 7 | Restart 後完整讀回 | ✅ **PASS** | `test_treatment_plan_restart.py` 驗證 session1 建立 → session2 完整讀回 Plan / Phases / Items / Trace。 |
| 8 | Graph Digital Thread 完整 | ✅ **PASS** | `test_treatment_plan_digital_thread.py` 驗證完整鏈路。KnowGraphGo adapter 實作 5 Entity + 11 Relation。 |
| 9 | Idempotent Graph Replay | ✅ **PASS** | KnowGraphGo 使用 UUIDv5 deterministic ID + upsert 模式。 |
| 10 | Auth／Role 正確 | ✅ **PASS** | API 層使用 `_WRITER_ROLES` / `_APPROVER_ROLES` / `_CLINICIAN_APPROVER_ROLES` 精確控制權限，沿襲既有 Role enum。 |
| 11 | Postgres CI 全綠 | ⚠️ **PARTIAL** | 當前 CI 在 Python 3.11 環境下因 `report_generator.py` 的語法錯誤（E-1）無法導入，Service 和 API 測試將失敗。尚未在真實 Postgres 上驗證完整 CI 結果。 |

### Reviewer Gate 結論

- **任一 FAIL / PARTIAL / 未驗證 → Reviewer 最高 89 分 → Accepted = NO**
- 第 4 項 PARTIAL + 第 11 項 PARTIAL → **Accepted = NO**
- → **Ready for Next Phase = NO**

---

## 需求逐條評審摘要

### §一 任務定位 — PASS
完整主鏈 Patient → … → Treatment Plan 已建立。Engine 接收 Patient/Recommendation/ClinicalDecision/Consensus 並產出完整 Plan。非 Medication Order System。

### §二 資料權責 — PASS
Postgres 唯一 Source of Truth。Graph 同步失敗不會導致正式資料遺失（Outbox 模式）。

### §三 本輪禁止事項 — PASS
未建立 Medication Order / Prescription / Billing 等。未重寫既有 Engine / Migration 017~022。

### §四 執行流程 — PASS
遵循 AGENTS.md 執行流程。

### §五 開始前必讀 — PASS
沿襲既有 Model / Repository / Service / API Pattern。

### §六 Treatment Plan 輸入（ID 驗證） — PASS
`_validate_links()` 完整驗證 4 個 patient_id 一致性 + CD→Rec FK + Consensus→CD FK。不一致回傳 422。

### §七 Plan 狀態（State Machine） — **PARTIAL ⚠️**
- 9 種狀態：✅ 全部定義
- 12 條轉換規則：⚠️ **ACTIVE→CANCELLED 缺失**（需求要求「任意非 completed → cancelled」）
- 非法轉換 → 409：✅
- 不得直接修改狀態字串：✅

### §八 Plan Versioning — PASS
完整實作版本化：version / previous_plan_id / supersedes_plan_id / is_current / revision_reason。可追溯誰修改、何時修改、修改原因。

### §九 Treatment Plan Model — PASS
`TreatmentPlanModel` 包含所有 30+ 欄位，符合需求規範。

### §十 Treatment Phase Model — PASS
`TreatmentPhaseModel` 包含所有欄位，Phase Type 支援 8 種。

### §十一 Treatment Item Model — PASS
`TreatmentItemModel` 包含所有欄位，`planned_dose_text` 僅為文字規劃，Item Type 支援 10 種。

### §十二 Monitoring Model — PASS
`TreatmentMonitoringModel` 包含所有欄位，monitoring_type 支援 7 種。

### §十三 Stop/Pause Criteria（SafetyRule） — PASS
`TreatmentSafetyRuleModel` 包含所有欄位，Rule Type 支援 6 種。所有規則標記 `requires_review: True`，不自動執行停藥。

### §十四 Alternative Plan — PASS ✅（返工修復）
- ✅ `TreatmentPlanModel` 新增 `alternative_options` JSON 欄位
- ✅ Migration 024 新增欄位
- ✅ `_persist_plan()` 存入 alternatives
- ✅ `_model_to_response()` 從 DB 讀取 alternatives

### §十五 Engine — PASS
`TreatmentPlanEngine` 為 pure domain logic，無 DB 操作/API 呼叫/commit。輸入輸出符合規範。

### §十六 Rule Set — PASS
`TreatmentPlanRuleSet` + `RuleRegistry` 實現 Registry Pattern，集中管理規則，無散落 if/elif。

### §十七 Calculation Trace — PASS
11 步驟完整追蹤（0~10），每步含 step_order / step_type / input_summary / output_summary / rule_ids / evidence_ids。

### §十八 Migration 023 — PASS
6 張表，含 Foreign Keys / Indexes / Unique Constraints / Cascade / Upgrade / Empty Downgrade / Re-upgrade。有資料時 downgrade 被阻擋。

### §十九 Repository — PASS
6 個 Repository，Plan 提供 8 種方法，其餘提供 create / create_many / list_by_plan_id / delete_by_plan_id。不 commit / rollback。

### §二十 Service — PASS
`TreatmentPlanService` 管理完整交易邊界。Plan Data + Outbox 同 Transaction。任一失敗全部 rollback。

### §二十一 Graph Event — PASS
7 個事件類型，Payload 包含必要欄位，過濾敏感資料。

### §二十二 KnowGraphGo 投影 — PASS
5 Entity + 11 Relation + Deterministic ID + Idempotent Replay + Relation Provenance + Stub Preservation。不破壞 Phase 3D 功能。

### §二十三 API — PASS
12 個 Endpoint（5 Read + 7 Write）。狀態操作經 State Machine，無通用 PATCH status=。

### §二十四 權限 — PASS
Viewer 唯讀 / Researcher 可建立 draft-proposed / Clinician 完整操作 / Admin 可 approve / Clinician+Admin 可 activate/pause/complete。沿用既有 Role。

### §二十五 Frontend — PASS ✅（返工修復）
4 個頁面、路由正確。Review Date 已加入 Detail Page（第 590~593 行）。Create 流程正常。

### §二十六 HTML Report — PASS ✅（返工修復）
Treatment Plan Section 已加入，含所有必要欄位（包括 Review Date）。

### §二十七 測試要求 — **PARTIAL ⚠️**
- Engine Tests（73 ✅）/ State Machine Tests（全部 ✅）/ Model Tests（28 ✅）/ Repository Tests（50 ✅）— 通過
- **Service Tests** — **因 Python 3.11 語法錯誤（E-1）無法運行**
- **API Tests** — **因 Python 3.11 語法錯誤（E-1）無法運行**
- Restart Recovery ✅ / Digital Thread ✅ / Frontend Tests ✅

### §二十八 Postgres CI — **PARTIAL ⚠️**
- Migration 023 upgrade ✅ / 023 empty downgrade + re-upgrade ✅（返工修復）
- 但 Python 3.11 語法錯誤（E-1）將導致 Service / API 測試在 CI 中失敗

### §二十九 CI Cleanup — PASS
已移除 Phase 3D 重複步驟。

---

## 總評

| 項目 | 結果 |
|------|------|
| **Accepted** | **NO** |
| **Ready for Next Phase** | **NO** |
| **Reviewer Score** | **51/100**（< 95，不合格） |

### 必須修復的關鍵問題

#### 1. [HIGH] Python 3.11 語法錯誤 — `report_generator.py`
**位置**：`src/backend/clinical/report_generator.py:1738`
**問題**：`f"Monitoring #{i+1}"` 中 f-string 表達式使用反斜杠，Python 3.11 不支援。
**修復**：改為 `"Monitoring #" + str(i+1)` 或 `f"Monitoring {chr(35)}{i+1}"`。
**影響**：導致 Service 測試、API 測試完全無法運行，CI 將失敗。

#### 2. [MEDIUM] State Machine 缺少 ACTIVE → CANCELLED
**位置**：`src/backend/clinical/treatment_plan_state_machine.py:56`
**問題**：`PlanStatus.ACTIVE: [PlanStatus.PAUSED, PlanStatus.COMPLETED, PlanStatus.SUPERSEDED]` 中缺少 `PlanStatus.CANCELLED`。
**修復**：在 ACTIVE 的允許轉換列表中加入 `PlanStatus.CANCELLED`。
**影響**：需求 §七 未完全滿足，Reviewer Gate 第 4 項 PARTIAL。

### 已成功修復的返工項目（4 項）

| 原問題 | 狀態 |
|--------|------|
| §十四 Alternative Plan 未持久化 | ✅ 已修復（Migration 024 + Service 修改） |
| §二十五 Frontend 缺少 Review Date | ✅ 已修復（DetailPage 加入 review_date 顯示） |
| §二十六 HTML Report 缺少 Review Date | ✅ 已修復（report_generator 渲染 review_date） |
| §二十八 CI 缺少 023 empty downgrade | ✅ 已修復（CI 加入 downgrade 023 + upgrade 023 步驟） |

---

> **結論**：Phase 3E Treatment Plan Engine V1 的核心功能完整、架構優秀，但存在 **Python 3.11 語法錯誤**（高優先級）和 **State Machine 轉換缺口**（中優先級），導致 Reviewer Score 僅 51/100，未達合格標準（>=90）及 Reviewer Gate 標準（>=95）。需要返工修復上述 2 個問題後重新評分。