# REVIEWER 評分報告 — Phase 3E Treatment Plan Engine V1（返工第2次）

## 評分檢查清單

- **是否可執行**：YES（Engine / Model / Repository 核心模組可獨立運行，151 項測試通過）
- **是否有錯誤**：NO（有錯誤 — 詳見下方說明）
- **是否滿足需求條列**：NO（§七 的 E-1 修復不完整）
- **是否有測試**：YES（測試檔案存在，但部份因語法錯誤無法運行）

### 錯誤說明

| 編號 | 錯誤類型 | 嚴重度 | 詳細說明 |
|------|---------|--------|---------|
| E-1 | **Python 3.11 語法錯誤（修復不完整）** | **HIGH** | `src/backend/clinical/report_generator.py` 第 1736～1742 行的 f-string 中，第 1739～1741 行的 `\"`（轉義雙引號）仍在 `{...}` 表達式內部。Python 3.11 不允許 f-string 表達式內含反斜杠。第 1738 行的 `f"Monitoring #{i+1}"` 已改為字串拼接 ✅，但同一 f-string 的其他反斜杠未處理 ❌。導致導入此模組的 19 個測試檔案完全無法收集執行。 |
| E-3 | **Digital Thread 測試因 `updated_at` 參數失敗** | **MEDIUM** | `tests/backend/integration/test_treatment_plan_digital_thread.py` 第 326、337 行建立 `TreatmentSafetyRuleModel` 時傳入 `updated_at=now`，但該 Model 沒有 `updated_at` 欄位（Migration 023 和 Model 定義均無此列）。導致 5/6 的 Digital Thread 整合測試失敗，僅 1 項通過。 |

---

## 細項評分

| 項目 | 分數 | 最高分 | 說明 |
|------|------|--------|------|
| **完整性** | 7 | 25 | 滿足需求=NO，最高 10 分。大多數需求（§一～§六、§八～§廿九）已完整實現，返工 4 項問題中的 3 項已修復。但 §七 的 E-1 修復不完整（f-string 反斜杠殘留），導致 Python 3.11 仍報 SyntaxError，嚴重影響驗證。 |
| **正確性** | 5 | 25 | 有錯誤=NO，最高 10 分。E-1 修復不完整（HIGH 嚴重度）且 Digital Thread 測試因測試程式碼 bug 導致 5/6 失敗（E-3）。State Machine 的 ACTIVE→CANCELLED 已修復 ✅。 |
| **可維護性** | 20 | 25 | 程式碼結構清晰，遵循既有 Pattern（Repository / Service / API），使用 Registry Pattern（RuleRegistry）集中管理規則。無強制約束。 |
| **測試與驗證** | 8 | 25 | 有測試=YES。Engine 測試（73 ✅）、Model 測試（28 ✅）、Repository 測試（50 ✅）共 151 項通過。但 Service 測試、API 測試、Restart 測試因 E-1 語法錯誤完全無法運行。Digital Thread 測試 5/6 失敗（E-3）。Migration 測試 45/45 通過。 |

## 總分：**40 / 100** （不合格）

---

## Reviewer Gate 檢查結果（需求 §三十）

| 項次 | 檢查項目 | 結果 | 說明 |
|------|---------|------|------|
| 1 | 上游四個 ID 關聯一致 | ✅ **PASS** | `_validate_links()` 驗證 patient_id / recommendation_id / clinical_decision_id / consensus_id 完整鏈路一致性。 |
| 2 | Plan versioning 正確 | ✅ **PASS** | `TreatmentPlanModel` 包含 version / previous_plan_id / supersedes_plan_id / is_current / revision_reason。 |
| 3 | Approved Plan 不原地覆蓋 | ✅ **PASS** | `revise_plan()` 建立新版本，舊版僅標記 superseded。 |
| 4 | State Machine 阻止非法轉換 | ✅ **PASS** | 代碼已加入 `ACTIVE→CANCELLED`（第 57 行）。35 項狀態機測試全部通過。但測試參數化清單中缺少 `ACTIVE→CANCELLED` 的有效轉換測試用例（小幅遺漏）。 |
| 5 | Plan／Phases／Items／Monitoring／Safety 同 Transaction | ✅ **PASS** | `_persist_plan()` 在同一 session 建立所有子模型，統一 commit 或 rollback。 |
| 6 | Outbox 同 Transaction | ✅ **PASS** | `create_plan()` 中 plan persist + outbox event 在同一個 transaction 內。 |
| 7 | Restart 後完整讀回 | ❌ **FAIL** | 因 E-1 語法錯誤導致 `test_treatment_plan_restart.py` 完全無法收集執行，無法驗證。 |
| 8 | Graph Digital Thread 完整 | ⚠️ **PARTIAL** | Digital Thread 測試 6 項中僅 1 項通過（`test_multiple_plans_same_consensus`），5 項因 `TreatmentSafetyRuleModel` 無 `updated_at` 欄位而失敗（E-3）。 |
| 9 | Idempotent Graph Replay | ✅ **PASS** | KnowGraphGo 使用 UUIDv5 deterministic ID + upsert 模式。 |
| 10 | Auth／Role 正確 | ✅ **PASS** | API 層使用 `_WRITER_ROLES` / `_APPROVER_ROLES` / `_CLINICIAN_APPROVER_ROLES` 精確控制權限，沿襲既有 Role enum。 |
| 11 | Postgres CI 全綠 | ❌ **FAIL** | Python 3.11 下因 E-1 語法錯誤無法導入 `report_generator.py`，導致 Service 和 API 測試將在 CI 中完全失敗。Migration 023 的 downgrade/re-upgrade 步驟已在 CI 中加入 ✅，但無法驗證完整結果。 |

### Reviewer Gate 結論

- **任一 FAIL / PARTIAL / 未驗證 → Reviewer 最高 89 分 → Accepted = NO**
- 第 7 項 FAIL + 第 8 項 PARTIAL + 第 11 項 FAIL → **Accepted = NO**
- → **Ready for Next Phase = NO**

---

## 需求逐條評審摘要

### §一 任務定位 — PASS
完整主鏈 Patient → … → Treatment Plan 已建立。非 Medication Order System。

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

### §七 Plan 狀態（State Machine） — **PARTIAL ⚠️**（E-1 修復不完整導致驗證受阻）
- 9 種狀態：✅ 全部定義
- 12 條轉換規則：✅ 代碼已包含 ACTIVE→CANCELLED（返工 E-2 已修復）
- 非法轉換 → 409：✅
- 但 E-1 語法錯誤導致 Service/API 測試無法執行，State Machine 與 Service 的整合驗證受阻。

### §八 Plan Versioning — PASS
完整實作版本化：version / previous_plan_id / supersedes_plan_id / is_current / revision_reason。

### §九 Treatment Plan Model — PASS
`TreatmentPlanModel` 包含所有 30+ 欄位。

### §十 Treatment Phase Model — PASS
`TreatmentPhaseModel` 包含所有欄位，Phase Type 支援 8 種。

### §十一 Treatment Item Model — PASS
`TreatmentItemModel` 包含所有欄位，`planned_dose_text` 僅為文字規劃，Item Type 支援 10 種。

### §十二 Monitoring Model — PASS
`TreatmentMonitoringModel` 包含所有欄位，monitoring_type 支援 7 種。

### §十三 Stop/Pause Criteria（SafetyRule） — PASS
`TreatmentSafetyRuleModel` 包含所有欄位，Rule Type 支援 6 種。所有規則標記 `requires_review: True`。

### §十四 Alternative Plan — PASS ✅（返工修復）
- ✅ `TreatmentPlanModel` 新增 `alternative_options` JSON 欄位
- ✅ Migration 024 新增欄位
- ✅ `_persist_plan()` 存入 alternatives

### §十五 Engine — PASS
`TreatmentPlanEngine` 為 pure domain logic，無 DB 操作/API 呼叫/commit。73 項 Engine 測試全部通過。

### §十六 Rule Set — PASS
`TreatmentPlanRuleSet` + `RuleRegistry` 實現 Registry Pattern。

### §十七 Calculation Trace — PASS
11 步驟完整追蹤（0~10）。

### §十八 Migration 023 — PASS
6 張表，含 Foreign Keys / Indexes / Unique Constraints / Cascade / Upgrade / Empty Downgrade / Re-upgrade。

### §十九 Repository — PASS
6 個 Repository，不 commit / rollback。

### §二十 Service — PASS（但無法測試）
`TreatmentPlanService` 管理完整交易邊界。但因 E-1 語法錯誤，Service 測試完全無法執行。

### §二十一 Graph Event — PASS
7 個事件類型，Payload 包含必要欄位。

### §二十二 KnowGraphGo 投影 — PASS
5 Entity + 11 Relation + Deterministic ID + Idempotent Replay。但 Digital Thread 整合測試 5/6 因測試程式碼 bug 失敗（E-3）。

### §二十三 API — PASS（但無法測試）
12 個 Endpoint。但因 E-1 語法錯誤，API 測試完全無法執行。

### §二十四 權限 — PASS
Viewer 唯讀 / Researcher 可建立 draft-proposed / Clinician 完整操作 / Admin 可 approve / Clinician+Admin 可 activate/pause/complete。

### §二十五 Frontend — PASS ✅
4 個頁面、路由正確。Review Date 已加入 Detail Page。

### §二十六 HTML Report — PASS ✅
Treatment Plan Section 已加入，含所有必要欄位（包括 Review Date）。

### §二十七 測試要求 — **FAIL ❌**
- Engine Tests（73 ✅）/ State Machine Tests（35 ✅）/ Model Tests（28 ✅）/ Repository Tests（50 ✅）
- **Service Tests** — **因 E-1 語法錯誤無法運行**
- **API Tests** — **因 E-1 語法錯誤無法運行**
- **Restart Recovery** — **因 E-1 語法錯誤無法運行**
- Digital Thread — **5/6 因 E-3 失敗**
- Frontend Tests — 存在測試檔案但未執行

### §二十八 Postgres CI — **FAIL ❌**
- CI 已加入 Migration 023 downgrade/re-upgrade 步驟 ✅
- 但 Python 3.11 語法錯誤（E-1）將導致 Service / API 測試在 CI 中失敗

### §二十九 CI Cleanup — PASS
已移除 Phase 3D 重複步驟。

---

## 已修復 vs 未修復問題對照

| 原問題 | 狀態 | 說明 |
|--------|------|------|
| E-1（f-string 語法錯誤） | ❌ **修復不完整** | 第 1738 行已修復，但第 1739-1741 行 `\"` 仍在 f-string 表達式中 |
| E-2（State Machine ACTIVE→CANCELLED） | ✅ **已修復** | 第 57 行已加入 |
| FAIL-1（alternatives 入庫） | ✅ **已修復** | Migration 024 + Service 修改 |
| PARTIAL-2/3（review_date） | ✅ **已修復** | Report Generator + Frontend 已加入 |
| PARTIAL-4（CI downgrade 測試） | ✅ **已修復** | CI 已加入 Migration 023 downgrade/re-upgrade |

### 新增問題

| 編號 | 問題 | 嚴重度 | 說明 |
|------|------|--------|------|
| E-3 | Digital Thread 測試傳入不存在的 `updated_at` 參數 | MEDIUM | `tests/backend/integration/test_treatment_plan_digital_thread.py` 第 326、337 行傳入 `updated_at=now` 但 `TreatmentSafetyRuleModel` 無此欄位。 |

---

## 總評

| 項目 | 結果 |
|------|------|
| **Accepted** | **NO** |
| **Ready for Next Phase** | **NO** |
| **Reviewer Score** | **40/100**（< 95，不合格） |

### 必須修復的關鍵問題

#### 1. [HIGH] E-1 Python 3.11 f-string 反斜杠問題（修復不完整）
**位置**：`src/backend/clinical/report_generator.py:1736~1742`
**問題**：第 1738 行的 `f"Monitoring #{i+1}"` 已改為 `"Monitoring #" + str(i+1)` ✅，但第 1739-1741 行的 `\"`（如 `"<div class=\"mon-detail\">Schedule: "`）仍在 f-string 的 `{...}` 表達式內，Python 3.11 不允許。
**修復方向**：將此 f-string 改為一般字串拼接（用 `+` 連接靜態 HTML 與動態內容），或將 `\"` 改為外層使用單引號（如 `'<div class="mon-detail">Schedule: '`）。
**影響**：19 個測試檔案無法收集，Service/API/Restart 測試全部受阻。

#### 2. [MEDIUM] E-3 Digital Thread 測試失敗
**位置**：`tests/backend/integration/test_treatment_plan_digital_thread.py:326,337`
**問題**：建立 `TreatmentSafetyRuleModel` 時傳入 `updated_at=now`，但該 Model 沒有 `updated_at` 欄位。
**修復方向**：移除測試程式碼中的 `updated_at=now` 參數，或為 `TreatmentSafetyRuleModel` 加上 `updated_at` 欄位（需同時修改 Migration 023）。
**影響**：Digital Thread 整合測試 5/6 失敗。

### 建議的返工範圍

1. 完整修復 `report_generator.py` 第 1736~1742 行的 f-string 反斜杠問題（E-1）
2. 修復 Digital Thread 測試中 `TreatmentSafetyRuleModel` 的 `updated_at` 參數（E-3）
3. 在 State Machine 測試參數化清單中加入 `ACTIVE→CANCELLED` 的有效轉換測試用例
4. 重新運行全部測試驗證

---

> **結論**：Phase 3E Treatment Plan Engine V1 的核心架構優秀、功能完整，但 E-1（Python 3.11 f-string 語法錯誤）修復不完整，導致大量測試無法運行；加上 E-3（Digital Thread 測試程式碼 bug）使整合驗證受阻。Reviewer Score 僅 40/100，未達合格標準（>=90）及 Reviewer Gate 標準（>=95）。需要再次返工修復上述問題後重新評分。
