# Review Report: Phase-3E-Hardening

> 評分代理：REVIEWER
> 評分日期：2026-07-29
> 狀態：✅ 合格

---

## 1. 評分檢查清單

| 檢查項 | 結果 | 說明 |
|--------|------|------|
| **是否可執行** | **YES** | 全部程式碼無語法錯誤，模組導入完整，無循環依賴 |
| **是否有錯誤** | **YES（無錯誤）** | 程式碼邏輯正確，無編譯/運行錯誤 |
| **是否滿足需求條列** | **YES** | 7 項架構問題（P0-1~P1-3）全部修復 |
| **是否有測試或滿足審美** | **YES** | 新增 21-33 個測試，逐欄驗證行為 |

---

## 2. 細項評分

| 細項 | 分數 | 說明 |
|------|------|------|
| **完整性** (0-25) | **25** | 7 項需求全部完整實現：Versioning 設計修正、Treatment Item 6 欄位持久化、Monitoring 5 欄位持久化、Trace 共用 trace_id、Phase Mapping 分配邏輯、Revision Policy 狀態檢查、Migration Gate 完整測試鏈 |
| **正確性** (0-25) | **25** | 所有程式碼邏輯正確：plan_id 不再唯一而是 UNIQUE(plan_id,version)；revise_plan 沿用原 plan_id；trace steps 共用同一 trace_id；phase 分配使用 phase_type 映射；RevisionPolicy 正確限制允許/禁止狀態；Migration 023 正確保護有資料時不允許 downgrade |
| **可維護性** (0-25) | **22** | 程式碼結構清晰，有適當註解和型別提示。Phase Mapping 的 fallback 邏輯清楚。RevisionPolicy 使用集合比較直觀。略低分原因：_persist_plan 方法長度較長（約 175 行），但由於其負責 6 種子模型的持久化，可接受。持續改善建議：可將 Phase mapping 邏輯提取為獨立方法。 |
| **測試與驗證** (0-25) | **25** | 測試覆蓋完整，包含單元測試（service/API）和整合測試（restart/digital thread/migration）。Version chain 驗證 v1→v2→v3 鏈條及 GET /versions 回傳 3 筆。Item/Monitoring 逐欄驗證 6+5=11 個欄位。Trace 驗證共用 trace_id、step_order 連續。Revision Policy 驗證 7 種狀態（3 允許 + 4 禁止）。Migration Gate 驗證 3 種情境（鏈條/有資料/空資料）。 |

**總分：25 + 25 + 22 + 25 = 97 分** ✅ **合格**（≥ 90）

---

## 3. 逐條需求對照審查結果

### P0-1 Versioning（最高優先）

| 需求 | 狀態 | 證據 |
|------|------|------|
| Database PK(id) 每個版本不同 | ✅ | `TreatmentPlanModel.id = Column(CompatUUID, primary_key=True, default=_uuid)` - 每筆記錄獨立 UUID |
| Business plan_id 所有版本固定 | ✅ | `plan_id = Column(String(64), nullable=False, index=True)` 無 unique；`UniqueConstraint("plan_id", "version")` 複合唯一 |
| version 使用 1, 2, 3... 遞增 | ✅ | `version = Column(Integer, default=1, nullable=False)`；revise_plan 中 `new_version = current_model.version + 1` |
| Migration：移除 plan_id UNIQUE，保留 UNIQUE(plan_id, version) | ✅ | 023 migration: `sa.Column("plan_id", sa.String(64), nullable=False, index=True)` 無 unique；`sa.UniqueConstraint("plan_id", "version", name="uq_plan_id_version")` |
| revision：沿用舊 plan_id，version+1，不得產生新的 plan_id | ✅ | revise_plan 第 669 行：`new_plan_id = plan_id`（直接沿用）；`new_version = current_model.version + 1` |
| 重新補齊：Version tests、Repository tests、API tests | ✅ | service `test_version_chain`、API `test_version_chain`、model `test_different_versions_allowed` / `test_plan_id_version_unique` |
| 驗證：GET versions 必須一次看到 v1, v2, v3 | ✅ | service test 第 551-557 行：assert len(results)==3, versions 為 3,2,1, plan_id 皆相同 |

### P0-2 Treatment Item Persistence

| 需求 | 狀態 | 證據 |
|------|------|------|
| 補齊 drug_id, procedure_code, frequency, duration, route, planned_dose_text 持久化 | ✅ | `_persist_plan` 第 863-868 行：全部六個欄位從 `item_data.get()` 寫入 `TreatmentItemModel` |
| Restart Recovery 後不得遺失 | ✅ | `test_restart_recovery_full_plan` 第 380-407 行：逐欄驗證 medication 和 procedure 的六個欄位在 restart 後正確 |
| 新增 Persistence tests、Restart tests，逐欄驗證 | ✅ | Restart test 涵蓋逐欄驗證；model test `test_create_all_fields` 驗證模型建立 |

### P0-3 Monitoring Persistence

| 需求 | 狀態 | 證據 |
|------|------|------|
| 補齊 target_range, warning_threshold, critical_threshold, action_if_abnormal, responsible_specialty 持久化 | ✅ | `_persist_plan` 第 893-897 行：全部五個欄位從 `m_data.get()` 寫入 `TreatmentMonitoringModel` |
| 重新補 Restart tests、Digital Thread tests，逐欄驗證 | ✅ | Restart test `test_monitoring_persistence_columns` 第 474-509 行；Digital thread test `test_monitoring_columns_persisted` 第 720-762 行 |

### P0-4 Trace

| 需求 | 狀態 | 證據 |
|------|------|------|
| 改成一個 Plan 共用同一 trace_id | ✅ | `_persist_plan` 第 927 行：`step_trace_id = trace_id`（所有 step 共用外部傳入的 trace_id） |
| 使用 step_order 區分每一步 | ✅ | `step_order=step_data.get("step_order", 0)` - 每個 step 有不同的 step_order |
| Database：UNIQUE(trace_id, step_order)，不得使用 UNIQUE(trace_id) | ✅ | model 第 298-300 行：`UniqueConstraint("trace_id", "step_order", name="uq_trace_step")`；trace_id 無 unique=True |
| 重新補 Trace tests、Restart tests | ✅ | Restart test `test_trace_correctness` 第 511+ 行；Digital thread test `test_trace_correctness` 第 764-817 行 |

### P1-1 Phase Mapping

| 需求 | 狀態 | 證據 |
|------|------|------|
| 必須真正依 phase_type 或 Engine Output 分配 Item 到對應 Phase | ✅ | `_persist_plan` 第 838-849 行：使用 `item_data.get("phase_type") or item_data.get("item_type")` 查找 phase_dicts 匹配 phase |
| 新增 Phase mapping tests | ✅ | `TestPhaseMapping` class：`test_items_mapped_to_correct_phase`（3 個 item→3 個不同 phase）、`test_items_without_phase_type_fallback_to_first_phase` |

### P1-2 Revision Policy

| 需求 | 狀態 | 證據 |
|------|------|------|
| 建立 RevisionPolicy | ✅ | revise_plan 第 657-666 行：`allowed_statuses = {PlanStatus.APPROVED, PlanStatus.ACTIVE, PlanStatus.PAUSED}`，不在集合中則拋出 `IllegalTransitionError` |
| 至少限制允許的狀態：approved、active、paused | ✅ | 三個狀態皆在 allowed_statuses 中 |
| 禁止的狀態：draft、cancelled、completed、superseded | ✅ | 測試覆蓋全部四個禁止狀態（service test + API test） |
| 非法操作返回 HTTP 409 | ✅ | API test 驗證 4 個禁止狀態皆回傳 409 |

### P1-3 Migration Gate

| 需求 | 狀態 | 證據 |
|------|------|------|
| 改成真正測：head → 022 → 023 → head | ✅ | CI 第 177-184 行：`downgrade 022` → `upgrade 023` → `upgrade head`；test_migration.py `test_upgrade_chain_head_to_022_to_023` 完整驗證鏈條及 table 存在性 |
| 有資料時 023 downgrade 必須失敗 | ✅ | `test_downgrade_023_with_data_raises_irreversible`：插入資料後 downgrade 拋出 `IrreversibleMigrationError` |
| 空資料時 023 downgrade 必須成功 | ✅ | `test_downgrade_023_empty_db_succeeds`：空表時 downgrade 成功，六個 table 全部移除 |

---

## 4. 缺漏/問題清單

| # | 類型 | 描述 | 嚴重度 |
|---|------|------|--------|
| 1 | ✅ 已滿足 | 無重大缺漏 | — |
| 2 | 💡 建議 | `_persist_plan` 方法長度約 175 行，建議將 Phase mapping 邏輯提取為獨立方法以提升可維護性 | 建議 |

**無未完成需求、無核心缺失、無 Mock/Stub/Fake 替代正式路徑。**

---

## 5. 總結

Phase-3E-Hardening 任務完整修復了 7 項架構問題（4 項 P0 + 3 項 P1）：

- **P0-1 Versioning**：修正 plan_id 唯一約束 → UNIQUE(plan_id,version)，revise 沿用同 plan_id，version+1
- **P0-2 Treatment Item Persistence**：補齊 drug_id, procedure_code, frequency, duration, route, planned_dose_text 六個欄位
- **P0-3 Monitoring Persistence**：補齊 target_range, warning_threshold, critical_threshold, action_if_abnormal, responsible_specialty 五個欄位
- **P0-4 Trace**：改為共用 trace_id，UNIQUE(trace_id, step_order)
- **P1-1 Phase Mapping**：依 phase_type/item_type 正確分配 item 到對應 phase
- **P1-2 Revision Policy**：限制 revision 僅允許 approved/active/paused 狀態
- **P1-3 Migration Gate**：完整 head→022→023→head 測試鏈 + 有資料/空資料 downgrade 測試

**總分 97/100 → 合格 ✅**
