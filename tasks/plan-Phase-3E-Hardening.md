# Plan: Phase-3E-Hardening

> 依據 tasks/requirements.md 和現有程式碼分析，制定可執行的架構強化計劃。
> 核心原則：禁止新增功能，只修既有問題。

---

## 發現摘要（程式碼審查結論）

在制定任務前，已對整個代碼庫進行審查，確認以下問題：

| 問題 | 優先級 | 簡述 |
|------|--------|------|
| Versioning 設計錯誤 | P0-1 | `plan_id` 設了 `unique=True` 導致 revision 時產生新 plan_id；`revise_plan()` 生成新 UUID 而非沿用舊 plan_id |
| Treatment Item 欄位未持久化 | P0-2 | Service 的 `_persist_plan()` 未寫入 `drug_id`, `procedure_code`, `frequency`, `duration`, `route`, `planned_dose_text` |
| Monitoring 欄位未持久化 | P0-3 | Service 的 `_persist_plan()` 未寫入 `target_range`, `warning_threshold`, `critical_threshold`, `action_if_abnormal`, `responsible_specialty` |
| Trace 設計錯誤 | P0-4 | `trace_id` 有 UNIQUE 約束但缺少 `UNIQUE(trace_id, step_order)`；每個 step 生成新 trace_id 而非共用 |
| Phase Mapping 錯誤 | P1-1 | 所有 items 都分配給第一個 phase |
| Revision 缺少狀態檢查 | P1-2 | `revise_plan()` 未檢查 plan 狀態即允許 revision |
| Migration Gate 測試不足 | P1-3 | CI 中 023 downgrade 測試未真正驗證有資料/無資料情境 |

---

## 任務清單

### P0-1 Versioning（最高優先）

#### H-01: 修正模型 plan_id 唯一約束

| 欄位 | 值 |
|------|-----|
| **任務ID** | H-01 |
| **標題** | 修正 TreatmentPlanModel.plan_id 資料庫唯一約束 |
| **描述** | 目前 `TreatmentPlanModel.plan_id` 設有 `unique=True`，導致 GET /versions 只查得到自己。需移除 `plan_id` 的 UNIQUE，保留 `UniqueConstraint("plan_id", "version")` 作為複合唯一鍵。同步修改 Migration 023 的 schema 定義。 |
| **負責角色** | backend-logic |
| **前置任務** | 無 |
| **預計修改檔案** | `src/backend/domain/treatment_plan.py` (第32行移除 unique=True)、`migrations/versions/023_phase3e_treatment_plan_tables.py` (第41行移除 unique=True) |
| **驗收標準** | 編譯通過；同一 plan_id 可有多筆不同 version 的記錄 |

#### H-02: 修正 revise_plan 沿用相同 plan_id

| 欄位 | 值 |
|------|-----|
| **任務ID** | H-02 |
| **標題** | 修正 revise_plan 產生新 plan_id 的錯誤 |
| **描述** | 目前 `revise_plan()` 第657行生成新的 `new_plan_id = _uuid.uuid4().hex`，導致 revision 後 plan_id 改變。修正為沿用既有 `plan_id`，僅 version+1。 |
| **負責角色** | backend-logic |
| **前置任務** | H-01 |
| **預計修改檔案** | `src/backend/services/treatment_plan_service.py` (第657-658行) |
| **驗收標準** | revision 後 plan_id 不變，version 遞增 1；GET /versions 可看到 v1, v2, v3 |

#### H-03: Version Chain 測試

| 欄位 | 值 |
|------|-----|
| **任務ID** | H-03 |
| **標題** | 撰寫 Version Chain 測試 |
| **描述** | 新增測試驗證：建立 plan v1 → revise → v2 → revise → v3；GET /versions 回傳全部三個版本；plan_id 一致；version 分別為 1, 2, 3。 |
| **負責角色** | test-writer |
| **前置任務** | H-02 |
| **預計修改檔案** | `tests/backend/services/test_treatment_plan_service.py`、`tests/backend/api/test_treatment_plan_api.py` |
| **驗收標準** | 測試通過：v1→v2→v3 鏈條完整；GET /versions 回傳 3 筆且 plan_id 相同 |

---

### P0-2 Treatment Item Persistence

#### H-04: 補齊 Item 欄位持久化

| 欄位 | 值 |
|------|-----|
| **任務ID** | H-04 |
| **標題** | 在 Service _persist_plan 中補寫 Item 遺失欄位 |
| **描述** | 在 `_persist_plan()` 的 item 建立區塊（第833-847行）補上 `drug_id`, `procedure_code`, `frequency`, `duration`, `route`, `planned_dose_text` 六個欄位，資料來源為 `item_data`（Engine Output）。若引擎未產生則為 None，至少確保欄位被寫入資料庫。 |
| **負責角色** | backend-logic |
| **前置任務** | 無 |
| **預計修改檔案** | `src/backend/services/treatment_plan_service.py` (第833-847行) |
| **驗收標準** | 建立 plan 後 DB 中 domain_treatment_items 表包含上述六個欄位的值 |

#### H-05: Item Persistence 測試

| 欄位 | 值 |
|------|-----|
| **任務ID** | H-05 |
| **標題** | 撰寫 Item Persistence 逐欄驗證測試 |
| **描述** | 新增測試，建立 plan 後直接查 DB，逐欄驗證 drug_id, procedure_code, frequency, duration, route, planned_dose_text 已被寫入且與 Engine Output 一致。 |
| **負責角色** | test-writer |
| **前置任務** | H-04 |
| **預計修改檔案** | `tests/backend/repositories/test_treatment_plan_repos.py`、`tests/backend/integration/test_treatment_plan_restart.py` |
| **驗收標準** | 測試通過，六個欄位逐欄驗證 |

---

### P0-3 Monitoring Persistence

#### H-06: 補齊 Monitoring 欄位持久化

| 欄位 | 值 |
|------|-----|
| **任務ID** | H-06 |
| **標題** | 在 Service _persist_plan 中補寫 Monitoring 遺失欄位 |
| **描述** | 在 `_persist_plan()` 的 monitoring 建立區塊（第859-870行）補上 `target_range`, `warning_threshold`, `critical_threshold`, `action_if_abnormal`, `responsible_specialty` 五個欄位，資料來源為 `m_data`（Engine Output）。 |
| **負責角色** | backend-logic |
| **前置任務** | 無 |
| **預計修改檔案** | `src/backend/services/treatment_plan_service.py` (第859-870行) |
| **驗收標準** | 建立 plan 後 DB 中 domain_treatment_monitoring 表包含上述五個欄位的值 |

#### H-07: Monitoring Persistence 測試

| 欄位 | 值 |
|------|-----|
| **任務ID** | H-07 |
| **標題** | 撰寫 Monitoring Persistence 逐欄驗證測試 |
| **描述** | 新增測試，建立 plan 後查 DB，逐欄驗證 target_range, warning_threshold, critical_threshold, action_if_abnormal, responsible_specialty 已被寫入。 |
| **負責角色** | test-writer |
| **前置任務** | H-06 |
| **預計修改檔案** | `tests/backend/integration/test_treatment_plan_restart.py`、`tests/backend/integration/test_treatment_plan_digital_thread.py` |
| **驗收標準** | 測試通過，五個欄位逐欄驗證 |

---

### P0-4 Trace

#### H-08: 修正 Trace 模型唯一約束

| 欄位 | 值 |
|------|-----|
| **任務ID** | H-08 |
| **標題** | 修正 TreatmentPlanTraceModel.trace_id 唯一約束為 UNIQUE(trace_id, step_order) |
| **描述** | 目前 `trace_id` 有 `unique=True`，導致同一個 plan 的多個 trace steps 無法共用 trace_id。需移除 `trace_id` 的 UNIQUE，改為 `UniqueConstraint("trace_id", "step_order")`，同步修改 Migration 023。 |
| **負責角色** | backend-logic |
| **前置任務** | 無 |
| **預計修改檔案** | `src/backend/domain/treatment_plan.py` (第300行移除 unique=True，新增 UniqueConstraint)、`migrations/versions/023_phase3e_treatment_plan_tables.py` (第159行移除 unique=True，新增 UniqueConstraint) |
| **驗收標準** | 同一 trace_id 可有多筆不同 step_order 的記錄 |

#### H-09: 修正 Trace steps 共用 trace_id

| 欄位 | 值 |
|------|-----|
| **任務ID** | H-09 |
| **標題** | 修正 _persist_plan 中每個 step 生成新 trace_id 的錯誤 |
| **描述** | 目前 `_persist_plan()` 第897行對每個 step 生成新的 `step_trace_id`，應改為所有 step 共用外部傳入的 `trace_id`（此 trace_id 已在 create_plan/revise_plan 中生成）。 |
| **負責角色** | backend-logic |
| **前置任務** | H-08 |
| **預計修改檔案** | `src/backend/services/treatment_plan_service.py` (第897-898行) |
| **驗收標準** | 所有 trace steps 使用相同的 trace_id；step_order 遞增；查詢時可依 trace_id 取回所有 steps |

#### H-10: Trace 測試

| 欄位 | 值 |
|------|-----|
| **任務ID** | H-10 |
| **標題** | 撰寫 Trace 正確性測試 |
| **描述** | 新增測試驗證：建立 plan 後所有 trace steps 共用同一個 trace_id；step_order 連續不重複；UNIQUE(trace_id, step_order) 約束有效；Restart 後 trace 資料完整讀回。 |
| **負責角色** | test-writer |
| **前置任務** | H-09 |
| **預計修改檔案** | `tests/backend/integration/test_treatment_plan_restart.py`、`tests/backend/integration/test_treatment_plan_digital_thread.py` |
| **驗收標準** | 測試通過：trace_id 一致、step_order 連續、restart 後資料完整 |

---

### P1-1 Phase Mapping

#### H-11: 修正 Item 到 Phase 的分配邏輯

| 欄位 | 值 |
|------|-----|
| **任務ID** | H-11 |
| **標題** | 修正所有 items 都分配給第一個 phase 的錯誤 |
| **描述** | 目前 `_persist_plan()` 第828-830行將所有 items 分配給 `first_phase`。需依 item_type 或 Engine Output 中的 phase_type 映射，將 item 分配到對應的 phase。如果 Engine Output 的 item 中沒有 phase 資訊，則依循以下規則：medication items → primary_treatment phase；preparation items → preparation phase；依此類推。 |
| **負責角色** | backend-logic |
| **前置任務** | H-01 |
| **預計修改檔案** | `src/backend/services/treatment_plan_service.py` (第825-849行) |
| **驗收標準** | 各 item 分配到正確的 phase，而非全部擠在第一個 phase |

#### H-12: Phase Mapping 測試

| 欄位 | 值 |
|------|-----|
| **任務ID** | H-12 |
| **標題** | 撰寫 Phase Mapping 測試 |
| **描述** | 新增測試驗證：建立含多個 phase 的 plan 後，各 item 的 phase_id 指向正確的 phase（非全部指向第一個 phase）。 |
| **負責角色** | test-writer |
| **前置任務** | H-11 |
| **預計修改檔案** | `tests/backend/services/test_treatment_plan_service.py`、`tests/backend/integration/test_treatment_plan_digital_thread.py` |
| **驗收標準** | 測試通過：items 分佈在多個 phases 中，分配邏輯正確 |

---

### P1-2 Revision Policy

#### H-13: 實作 RevisionPolicy 狀態檢查

| 欄位 | 值 |
|------|-----|
| **任務ID** | H-13 |
| **標題** | 新增 RevisionPolicy 限制 revision 允許的狀態 |
| **描述** | 建立 RevisionPolicy 類別（或靜態方法），在 `revise_plan()` 開頭檢查當前 plan 的 `plan_status`。只允許 `approved`(approved)、`active`(active)、`paused`(paused) 狀態進行 revision。draft、cancelled、completed、superseded 狀態應拋出 `IllegalTransitionError`（HTTP 409）。 |
| **負責角色** | backend-logic |
| **前置任務** | H-02 |
| **預計修改檔案** | `src/backend/services/treatment_plan_service.py` (在 revise_plan 方法開頭新增狀態檢查) |
| **驗收標準** | approved/active/paused → 可 revision；draft/cancelled/completed/superseded → 回傳 HTTP 409 |

#### H-14: Revision Policy 測試

| 欄位 | 值 |
|------|-----|
| **任務ID** | H-14 |
| **標題** | 撰寫 Revision Policy 測試 |
| **描述** | 新增測試驗證每個狀態的 revision 行為：approved/active/paused 成功；draft/cancelled/completed/superseded 返回 409。 |
| **負責角色** | test-writer |
| **前置任務** | H-13 |
| **預計修改檔案** | `tests/backend/services/test_treatment_plan_service.py`、`tests/backend/api/test_treatment_plan_api.py` |
| **驗收標準** | 測試通過：允許/禁止狀態的行為正確 |

---

### P1-3 Migration Gate

#### H-15: 修正 CI Migration 023 測試流程

| 欄位 | 值 |
|------|-----|
| **任務ID** | H-15 |
| **標題** | 修正 CI 中 Migration 023 downgrade/upgrade 測試 |
| **描述** | 目前 CI 第177-183行只做 `downgrade 023 → upgrade 023`，未真正測試 023 的 downgrade 保護。需改為：head → 022 → 023 → head。並新增有資料時 023 downgrade 必須失敗、空資料時 023 downgrade 必須成功的測試。 |
| **負責角色** | backend-logic |
| **前置任務** | 無 |
| **預計修改檔案** | `.github/workflows/ci.yml` (第177-183行) |
| **驗收標準** | CI 執行：head→022→023→head 成功；有資料時 023 downgrade 失敗 |

#### H-16: Migration 023 Gate 測試

| 欄位 | 值 |
|------|-----|
| **任務ID** | H-16 |
| **標題** | 撰寫 Migration 023 閘道測試 |
| **描述** | 在 `tests/test_migration.py` 中新增 TestMigration023 類別，測試：head→022→023→head 遷移鏈；有資料時 023 downgrade 拋出 IrreversibleMigrationError；空資料時 023 downgrade 成功。 |
| **負責角色** | test-writer |
| **前置任務** | H-15 |
| **預計修改檔案** | `tests/test_migration.py` (新增 TestMigration023 類別) |
| **驗收標準** | 測試通過：三種情境皆驗證 |

---

### 整合驗證

#### H-17: 整合驗證

| 欄位 | 值 |
|------|-----|
| **任務ID** | H-17 |
| **標題** | 全部編譯通過 + 全部測試通過 + CI 完整通過 |
| **描述** | 執行完整測試套件：ruff lint、pytest 全量測試（含 unit/integration）、CI 模擬。確保無編譯錯誤、無測試失敗、無 CI 失敗。 |
| **負責角色** | backend-logic + test-writer |
| **前置任務** | H-01 ~ H-16 全部完成 |
| **預計修改檔案** | 無（僅執行驗證） |
| **驗收標準** | `pytest -v --tb=short` 全量通過；`ruff check src/ tests/` 通過 |

---

## 依賴關係圖

```
H-01 (模型約束) ──→ H-02 (revise plan_id) ──→ H-03 (Version Chain 測試)
                                                  │
H-01 ──→ H-11 (Phase Mapping) ──→ H-12 (Phase Mapping 測試)
                │
H-02 ──→ H-13 (Revision Policy) ──→ H-14 (Revision Policy 測試)
                │
H-04 (Item 持久化) ──→ H-05 (Item Persistence 測試)
                │
H-06 (Monitoring 持久化) ──→ H-07 (Monitoring Persistence 測試)
                │
H-08 (Trace 約束) ──→ H-09 (Trace trace_id) ──→ H-10 (Trace 測試)
                │
H-15 (CI Migration) ──→ H-16 (Migration Gate 測試)
                │
全部 ──→ H-17 (整合驗證)
```

**執行順序建議（依優先級）：**

1. **P0 批次**（可並行的獨立修復）：
   - H-01（模型約束）→ H-02（revise plan_id）→ H-03（測試）
   - H-04（Item 持久化）→ H-05（測試）
   - H-06（Monitoring 持久化）→ H-07（測試）
   - H-08（Trace 約束）→ H-09（Trace trace_id）→ H-10（測試）

2. **P1 批次**：
   - H-11（Phase Mapping）→ H-12（測試）
   - H-13（Revision Policy）→ H-14（測試）
   - H-15（CI Migration）→ H-16（測試）

3. **最終**：
   - H-17（整合驗證）

---

## 返工預案

每個任務完成後由 reviewer 評分。若某任務評分不合格：

### 輕度不合格（評分 < 7 但有明確修正方向）
1. reviewer 提供具體修改建議
2. 原負責角色在同一任務 ID 下重新修改
3. 修改後重新提交 reviewer 評分
4. 此過程最多重複 2 輪，若仍不合格則升級

### 中度不合格（評分 < 5 或邏輯錯誤）
1. 標記該任務為 `rework` 狀態
2. 查明根本原因（可能是前置任務有問題）
3. 若為前置任務問題 → 修復前置任務後重新執行
4. 若為本任務問題 → 由原負責角色重新實作
5. 重新評分

### 重度不合格（架構設計錯誤、影響其他任務）
1. 立即暫停該任務及其所有下游依賴任務
2. 召集（planner + backend-logic + reviewer）三方會審
3. 確定修正方案，必要時更新本計劃文檔
4. 從受影響的最上游任務開始重新執行
5. 所有下游任務需重新驗證

### 常見返工情境及對策

| 情境 | 對策 |
|------|------|
| 測試遺漏某個欄位驗證 | 補寫該斷言，重新提交 |
| 修改導致另一測試失敗 | 鎖定回歸範圍，修正衝突後重新提交 |
| CI 中 Migration 測試腳本錯誤 | 修正 CI yaml，重新觸發 |
| Revision Policy 狀態判斷遺漏 | 補齊所有狀態的枚舉檢查 |
| Phase Mapping 分配邏輯不完整 | 補齊 item_type → phase_type 映射表 |

---

## 附註

### 預計新增/修改測試數量

| 測試類別 | 預計新增數 |
|----------|-----------|
| Version Chain tests | 3-5 |
| Item Persistence tests | 3-5 |
| Monitoring Persistence tests | 3-5 |
| Trace tests | 3-5 |
| Phase Mapping tests | 2-3 |
| Revision Policy tests | 4-6 |
| Migration Gate tests | 3-4 |
| **總計** | **21-33** |

### Git 完成條件

1. 全部編譯通過（`ruff check src/ tests/` + Python 導入無誤）
2. 全部測試通過（`pytest -v --tb=short`）
3. 完整 CI 通過（GitHub Actions）
4. Git Commit + Git Push

### 最終回報內容

- Commit SHA
- GitHub Actions 狀態
- 新增測試數
- 修復項目清單（7 項架構問題）
- 修改檔案清單
