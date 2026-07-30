# Phase 3F-0 返工第 2 次需求回歸檢查報告

> **檢查日期**：2026-07-30  
> **對照計劃**：`tasks/plan-outbox-eventid-r2.md`  
> **受檢版本**：返工第 2 次（Outbox event_id 修復）  
> **檢查重點**：Outbox event_id 修復是否正確  

---

## 1. Production 修正確認

| 檢查項 | 結果 | 說明 |
|--------|:----:|------|
| `treatment_plan_service.py` 的 `_create_outbox_event()` 已傳入 `event_id=str(_uuid.uuid4())` | ✅ PASS | 於 L1024 加入 `event_id=str(_uuid.uuid4())`，與既有 `ClinicalGraphEventService` 的 UUID 產生方式一致 |
| 所有呼叫路徑皆經由同一 `_create_outbox_event()` 方法 | ✅ PASS | `create_plan()`、`approve_plan()`、`revise_plan()` 三路徑皆呼叫同一方法，一次修復全面涵蓋 |
| `ClinicalGraphOutboxRepository.create()` 無需修改 | ✅ PASS | Repository 接受 `**kwargs` 並傳遞給 Model，無需變更 |
| `ClinicalGraphOutboxModel.event_id` 欄位定義正確 | ✅ PASS | `Column(String(64), unique=True, nullable=False, index=True)` — 與既有 schema 一致 |

**判定：✅ 全部 PASS**

---

## 2. 測試修正確認

| 檢查項 | 結果 | 說明 |
|--------|:----:|------|
| `FixedOutboxRepository` class 已移除 | ✅ PASS | 自 `test_success_path_red.py` 完整刪除，無殘留 wrapper |
| 成功路徑測試改用真實 `ClinicalGraphOutboxRepository` | ✅ PASS | `test_success_path_red.py` 的 `outbox_repo` 注入改為真實 Repository |
| 因缺 `event_id` 而預期失敗的測試已移除 | ✅ PASS | 不再需要此類測試，因為 production 層已正確提供 `event_id` |
| 測試未遮蔽 production contract | ✅ PASS | 無任何測試 wrapper 取代或補充 production 應產生的欄位 |

**判定：✅ 全部 PASS**

---

## 3. 測試結果

| 測試套件 | 數量 | 結果 |
|----------|:----:|:----:|
| Atomicity tests（`tests/backend/atomicity/`） | **5/5** | ✅ 全部 PASS |
| Backend tests（`tests/` + `tests/backend/`） | **273/273** | ✅ 全部 PASS |
| **合計** | **278/278** | **✅ 全部通過** |

### Atomicity 測試覆蓋情境

| 測試檔案 | 情境 | 結果 |
|---------|------|:----:|
| `test_success_path_red.py` | Service 成功路徑單次 commit，Outbox event_id 正確產生 | ✅ |
| `test_outbox_atomicity.py` | Outbox + 業務資料同交易原子性（4 種情境） | ✅ |
| `test_atomicity_flow_a.py` | Patient + CancerCase 跨 Repository 原子性 | ✅ |
| `test_atomicity_flow_b.py` | Treatment Plan 完整流程原子性 | ✅ |
| `test_base_repository_atomicity.py` | BaseRepository flush-only 原子性 | ✅ |

**判定：✅ 全部 PASS**

---

## 4. Outbox Contract Gate

| 檢查項 | 結果 | 說明 |
|--------|:----:|------|
| `event_id` 在 production service 中正確產生 | ✅ PASS | `_create_outbox_event()` 使用 `str(_uuid.uuid4())` 產生唯一值，非由測試或 wrapper 補入 |
| 無測試 wrapper 遮蔽 | ✅ PASS | `FixedOutboxRepository` 已完全移除，測試直接使用真實 `ClinicalGraphOutboxRepository` |
| 所有呼叫路徑皆經過同一 `_create_outbox_event()` 方法 | ✅ PASS | `create_plan()` → `_create_outbox_event()` ✅; `approve_plan()` → `_create_outbox_event()` ✅; `revise_plan()` → `_create_outbox_event()` ✅ |
| 不符合此 contract 的測試已不存在 | ✅ PASS | 因缺 `event_id` 而預期失敗的測試已移除，不再遮蔽 contract 缺口 |

### 呼叫路徑覆蓋驗證

```
TreatmentPlanService
├── create_plan()
│   └── _create_outbox_event() → event_id=str(_uuid.uuid4()) ✅
├── approve_plan()
│   └── _create_outbox_event() → event_id=str(_uuid.uuid4()) ✅
└── revise_plan()
    └── _create_outbox_event() → event_id=str(_uuid.uuid4()) ✅
```

**判定：✅ PASS（Outbox Contract Gate 已完全符合）**

---

## 5. 總評判定

| 檢查大項 | 項數 | ✅ PASS |
|---------|:----:|:-------:|
| Production 修正確認 | 4 | 4 |
| 測試修正確認 | 4 | 4 |
| 測試結果 | 2 | 2 |
| Outbox Contract Gate | 4 | 4 |
| **合計** | **14** | **14 ✅** |

> **最終判定：✅ 回歸檢查全部 PASS**
>
> 14/14 項全部通過。Outbox event_id 修復正確：
> - Production 層已在 `_create_outbox_event()` 中傳入 `event_id=str(_uuid.uuid4())`
> - 測試層已移除 `FixedOutboxRepository` wrapper，使用真實 Repository
> - 278/278 測試全部通過
> - 所有呼叫路徑（create_plan / approve_plan / revise_plan）皆經由同一 `_create_outbox_event()` 方法
> - 無任何殘留遮蔽或 contract 缺口

---

*報告結束 — 由子代理根據程式碼審查與測試結果產出。*
